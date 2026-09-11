"""Deterministic marks × chapter × time. The model does not own these numbers."""

from __future__ import annotations

import csv
import io
import re
from typing import Any

from . import config, store

HEADER_RE = re.compile(
    r"^Q\s*(\d+)\s*[\.)]?\s*\((\d+)\s*marks?\)\s*(?:\[([^\]]+)\])?\s*$",
    re.IGNORECASE,
)

CHAPTER_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Polynomials": (
        "polynomial",
        "zeroes",
        "zeros of",
        "factor theorem",
        "remainder theorem",
        "quotient",
    ),
    "Linear Equations": (
        "linear equation",
        "pair of linear",
        "simultaneous",
        "two variables",
        "hostel charges",
        "cost of food per day",
        "sum of two numbers",
    ),
    "Triangles": (
        "triangle",
        "similar",
        "parallel to bc",
        "thales",
        "pythagoras",
        "vertical pole",
        "casts a shadow",
    ),
    "Trigonometry": (
        "sin ",
        "cos ",
        "tan ",
        "trigonometr",
        "angle of",
        "kite is flying",
        "string makes an angle",
    ),
    "Statistics": (
        "mean",
        "median",
        "mode",
        "frequency",
        "histogram",
        "class interval",
        "the following table",
    ),
}

FORBIDDEN_CLAIMS = (
    "potential",
    "personality",
    "anxious",
    "adhd",
    "lazy",
    "gifted",
    "mental health",
    "depressed",
    "bright student",
    "weak student",
    "slow learner",
    "intelligence",
)


def map_paper(paper_text: str) -> list[dict[str, Any]]:
    """Split a paper into Q1–Qn with max marks and a chapter tag.

    A [Chapter] tag on the question line wins. Otherwise keyword guess.
    Untagged or guessed questions are marked needs_review.
    """
    lines = [line.rstrip() for line in paper_text.replace("\r\n", "\n").split("\n")]
    headers: list[tuple[int, int, int, str | None]] = []
    for i, line in enumerate(lines):
        match = HEADER_RE.match(line.strip())
        if match:
            number = int(match.group(1))
            max_marks = int(match.group(2))
            tag = match.group(3).strip() if match.group(3) else None
            headers.append((i, number, max_marks, tag))

    questions: list[dict[str, Any]] = []
    for idx, (line_no, number, max_marks, tag) in enumerate(headers):
        end = headers[idx + 1][0] if idx + 1 < len(headers) else len(lines)
        prompt = "\n".join(lines[line_no + 1 : end]).strip()
        if tag:
            chapter, source, needs_review, confidence = tag, "paper_tag", False, 1.0
        else:
            chapter, source, needs_review, confidence = _guess_chapter(prompt)
        questions.append(
            {
                "id": f"q{number}",
                "number": number,
                "max_marks": max_marks,
                "chapter": chapter,
                "prompt": prompt,
                "source": source,
                "needs_review": needs_review,
                "confidence": confidence,
            }
        )
    questions.sort(key=lambda q: q["number"])
    return questions


def _guess_chapter(prompt: str) -> tuple[str, str, bool, float]:
    blob = f" {prompt.lower()} "
    scores: dict[str, int] = {}
    for chapter, words in CHAPTER_KEYWORDS.items():
        scores[chapter] = sum(1 for word in words if word in blob)
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    best, hits = ranked[0]
    second = ranked[1][1] if len(ranked) > 1 else 0
    if hits <= 0:
        return "Untagged", "none", True, 0.0
    raw = min(0.92, 0.48 + 0.16 * hits)
    if second > 0 and second >= hits:
        raw -= 0.22
    confidence = round(max(0.35, raw), 2)
    return best, "keyword", True, confidence


def parse_marks_csv(csv_text: str, questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach CSV cells to question ids. Empty / NA / '-' is missing, never zero."""
    qids = [q["id"] for q in questions]
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    if not reader.fieldnames:
        raise ValueError("Marks CSV has no header row.")
    fields = [f.strip().lower() for f in reader.fieldnames]
    reader.fieldnames = fields

    rows: list[dict[str, Any]] = []
    for raw in reader:
        if not raw:
            continue
        roll = str(raw.get("roll") or "").strip()
        name = str(raw.get("name") or "").strip()
        if not roll:
            continue
        cells: dict[str, float | None] = {}
        missing: list[str] = []
        for qid in qids:
            value = raw.get(qid)
            parsed = _parse_cell(value)
            cells[qid] = parsed
            if parsed is None:
                missing.append(qid)
        rows.append(
            {
                "roll": roll.zfill(2) if roll.isdigit() else roll,
                "name": name,
                "cells": cells,
                "complete": len(missing) == 0,
                "missing": missing,
            }
        )
    return rows


def _parse_cell(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.upper() in {"NA", "N/A", "-", "NULL", "NONE"}:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number


def set_question_chapter(paper_id: str, question_id: str, chapter: str) -> dict[str, Any]:
    chapter = chapter.strip()
    if not chapter:
        raise ValueError("Chapter cannot be empty.")

    def _mut(state: dict[str, Any]) -> None:
        paper = resolve_paper(state, paper_id)
        if not paper:
            raise KeyError(f"Unknown paper {paper_id}")
        paper_id_real = paper["id"]
        paper = state["papers"][paper_id_real]
        for question in paper["questions"]:
            if question["id"] == question_id:
                question["chapter"] = chapter
                question["source"] = "teacher"
                question["needs_review"] = False
                question["confidence"] = 1.0
                return
        raise KeyError(f"Unknown question {question_id}")

    store.update(_mut)
    store.audit("fix_tag", {"paper_id": paper_id, "question_id": question_id, "chapter": chapter})
    state = store.load()
    return resolve_paper(state, paper_id)


def set_cell(paper_id: str, roll: str, question_id: str, value: Any, *, teacher: str) -> dict[str, Any]:
    """Teacher writes one mark. Agents cannot call this."""
    parsed = _parse_cell(value)
    if parsed is None:
        raise ValueError("Mark is empty. We do not invent marks.")
    applied: dict[str, Any] = {}

    def _mut(state: dict[str, Any]) -> None:
        paper = resolve_paper(state, paper_id)
        if not paper:
            raise KeyError(f"Unknown paper {paper_id}")
        pid = paper["id"]
        row = (state["rows"].get(pid) or {}).get(roll)
        if not row:
            raise KeyError(f"Unknown roll {roll}")
        question = next((q for q in paper["questions"] if q["id"] == question_id), None)
        if not question:
            raise KeyError(f"Unknown question {question_id}")
        if parsed < 0 or parsed > float(question["max_marks"]):
            raise ValueError(f"Mark must be between 0 and {question['max_marks']}.")
        old = row["cells"].get(question_id)
        row["cells"][question_id] = parsed
        missing = [qid for qid, cell in row["cells"].items() if cell is None]
        row["missing"] = missing
        row["complete"] = len(missing) == 0
        applied.update(
            {
                "paper_id": pid,
                "roll": roll,
                "question_id": question_id,
                "old": old,
                "new": parsed,
                "teacher": teacher,
                "complete": row["complete"],
            }
        )

    store.update(_mut)
    store.audit("fill_cell", applied)
    return applied


def analyse_row(paper: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    questions = {q["id"]: q for q in paper["questions"]}
    got = 0.0
    max_total = 0.0
    chapter_got: dict[str, float] = {}
    chapter_max: dict[str, float] = {}
    losses: list[dict[str, Any]] = []

    for qid, question in questions.items():
        max_marks = float(question["max_marks"])
        max_total += max_marks
        cell = row["cells"].get(qid)
        chapter = question["chapter"] or "Untagged"
        chapter_max[chapter] = chapter_max.get(chapter, 0) + max_marks
        if cell is None:
            continue
        got += cell
        chapter_got[chapter] = chapter_got.get(chapter, 0) + cell
        lost = max_marks - cell
        if lost > 0:
            losses.append(
                {
                    "question_id": qid,
                    "number": question["number"],
                    "chapter": chapter,
                    "got": cell,
                    "max": max_marks,
                    "lost": lost,
                }
            )

    losses.sort(key=lambda item: (-item["lost"], item["number"]))
    chapters = []
    for name in chapter_max:
        cmax = chapter_max[name]
        cgot = chapter_got.get(name, 0.0)
        percent = (cgot / cmax) if cmax else 0.0
        chapters.append(
            {
                "name": name,
                "got": cgot,
                "max": cmax,
                "percent": round(percent * 100, 1),
                "band": _band(percent),
            }
        )
    chapters.sort(key=lambda c: c["percent"])

    percent = (got / max_total) if max_total else 0.0
    return {
        "roll": row["roll"],
        "name": row["name"],
        "paper_id": paper["id"],
        "title": paper.get("title"),
        "got": got,
        "max": max_total,
        "percent": round(percent * 100, 1),
        "complete": bool(row.get("complete")),
        "missing": list(row.get("missing") or []),
        "chapters": chapters,
        "cells": [
            {
                "id": q["id"],
                "number": q["number"],
                "got": row["cells"].get(q["id"]),
                "max": q["max_marks"],
                "empty": row["cells"].get(q["id"]) is None,
            }
            for q in paper["questions"]
        ],
        "losses": losses,
        "strong": [c["name"] for c in chapters if c["band"] == "strong"],
        "ok": [c["name"] for c in chapters if c["band"] == "ok"],
        "weak": [c["name"] for c in chapters if c["band"] == "weak"],
    }


def class_hotspots(paper: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    complete = [row for row in rows if row.get("complete")]
    if not complete:
        return []
    hotspots = []
    n = len(complete)
    for question in paper["questions"]:
        qid = question["id"]
        total = 0.0
        for row in complete:
            cell = row["cells"].get(qid)
            if cell is None:
                continue
            total += cell
        avg = total / n
        percent = (avg / question["max_marks"]) if question["max_marks"] else 0.0
        lost = 0.0
        affected_rolls: list[str] = []
        for row in complete:
            cell = row["cells"].get(qid)
            if cell is None:
                continue
            lost += max(0.0, float(question["max_marks"]) - float(cell))
            if question["max_marks"] and (cell / question["max_marks"]) < 0.50:
                affected_rolls.append(row["roll"])
        hotspots.append(
            {
                "question_id": qid,
                "number": question["number"],
                "chapter": question["chapter"],
                "avg": round(avg, 2),
                "max": question["max_marks"],
                "percent": round(percent * 100, 1),
                "n": n,
                "leaked": percent < 0.50,
                "lost": round(lost, 1),
                "affected": len(affected_rolls),
                "affected_rolls": affected_rolls,
            }
        )
    hotspots.sort(key=lambda h: (h["percent"], h["number"]))
    return hotspots


def year_line(roll: str, state: dict[str, Any] | None = None, class_id: str | None = None) -> list[dict[str, Any]]:
    state = state or store.load()
    class_id = class_id or config.DEFAULT_CLASS_ID
    points = []
    papers = sorted(
        state["papers"].values(),
        key=lambda p: (_section_rank(p), p.get("date") or "", p.get("id") or ""),
    )
    # Keep the year line inside one class — Ravi is 10-B, Ira is 10-A.
    for paper in papers:
        if class_id and (paper.get("class_id") or config.DEFAULT_CLASS_ID) != class_id:
            continue
        row = (state["rows"].get(paper["id"]) or {}).get(roll)
        if not row:
            continue
        analysis = analyse_row(paper, row)
        points.append(
            {
                "paper_id": paper["id"],
                "title": paper.get("title"),
                "section": paper.get("section") or paper["id"],
                "date": paper.get("date"),
                "percent": analysis["percent"] if analysis["complete"] else None,
                "complete": analysis["complete"],
                "got": analysis["got"] if analysis["complete"] else None,
                "max": analysis["max"],
                "weak": analysis["weak"],
                "strong": analysis["strong"],
            }
        )
    return points


def student_bundle(paper_id: str, roll: str, state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or store.load()
    paper = resolve_paper(state, paper_id)
    if not paper:
        raise KeyError("Unknown paper")
    row = (state["rows"].get(paper["id"]) or {}).get(roll)
    if not row:
        raise KeyError("Unknown roll")
    analysis = analyse_row(paper, row)
    hotspots = class_hotspots(paper, list((state["rows"].get(paper["id"]) or {}).values()))
    return {
        "paper": _public_paper(paper),
        "row": row,
        "analysis": analysis,
        "hotspots": hotspots,
        "year": year_line(roll, state, paper.get("class_id")),
        "brain": brain_graph(paper, row, analysis, hotspots),
        "memory": _student_memory(roll, paper.get("class_id") or config.DEFAULT_CLASS_ID, state),
    }


def class_bundle(paper_id: str, state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or store.load()
    paper = resolve_paper(state, paper_id)
    if not paper:
        raise KeyError("Unknown paper")
    rows = list((state["rows"].get(paper["id"]) or {}).values())
    rows_sorted = sorted(rows, key=lambda r: r["roll"])
    analyses = [analyse_row(paper, row) for row in rows_sorted]
    ready = sum(1 for row in rows if row.get("complete"))
    return {
        "paper": _public_paper(paper),
        "counts": {
            "n": len(rows),
            "ready": ready,
            "incomplete": len(rows) - ready,
            "needs_review": sum(1 for q in paper["questions"] if q.get("needs_review")),
        },
        "hotspots": class_hotspots(paper, rows),
        "roster": analyses,
    }


def _public_paper(paper: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": paper["id"],
        "title": paper.get("title"),
        "section": paper.get("section") or paper["id"],
        "subject": paper.get("subject"),
        "class_name": paper.get("class_name"),
        "date": paper.get("date"),
        "max_total": paper.get("max_total"),
        "questions": paper.get("questions") or [],
        "source": paper.get("source"),
        "class_id": paper.get("class_id") or config.DEFAULT_CLASS_ID,
    }


def _section_rank(paper: dict[str, Any]) -> int:
    section = paper.get("section") or paper.get("id") or ""
    order = {item["id"]: i for i, item in enumerate(config.SECTIONS)}
    return order.get(section, 50)


def resolve_paper(state: dict[str, Any], paper_id: str, class_id: str | None = None) -> dict[str, Any] | None:
    pid = config.resolve_paper_id(paper_id)
    if ":" in pid:
        return state["papers"].get(pid)
    if class_id and class_id != config.DEFAULT_CLASS_ID:
        keyed = f"{class_id}:{pid}"
        if keyed in state["papers"]:
            return state["papers"][keyed]
    paper = state["papers"].get(pid) or state["papers"].get(paper_id)
    if paper and class_id and paper.get("class_id") not in {None, class_id}:
        return None
    return paper


def papers_for_class(state: dict[str, Any], class_id: str | None) -> list[dict[str, Any]]:
    class_id = class_id or config.DEFAULT_CLASS_ID
    out = []
    for paper in state["papers"].values():
        if (paper.get("class_id") or config.DEFAULT_CLASS_ID) == class_id:
            out.append(paper)
    return out


def student_sections(roll: str, state: dict[str, Any] | None = None, class_id: str | None = None) -> list[dict[str, Any]]:
    """Term 1 and Midterm as separate report blocks, same roll."""
    from . import briefs

    state = state or store.load()
    class_id = class_id or config.DEFAULT_CLASS_ID
    blocks = []
    for spec in config.SECTIONS:
        paper = resolve_paper(state, spec["paper_id"], class_id)
        if not paper:
            continue
        row = (state["rows"].get(paper["id"]) or {}).get(roll)
        if not row:
            continue
        bundle = student_bundle(paper["id"], roll, state)
        payload = briefs.write_briefs(bundle["analysis"], bundle["year"])
        blocks.append(
            {
                "section": spec["id"],
                "title": spec["title"],
                **bundle,
                "briefs": payload,
            }
        )
    return blocks


def brain_graph(
    paper: dict[str, Any],
    row: dict[str, Any] | None,
    analysis: dict[str, Any] | None,
    hotspots: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Obsidian-style local graph: student ↔ chapters ↔ questions."""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    backlinks: dict[str, list[str]] = {}

    paper_id = paper["id"]
    paper_label = paper.get("title") or paper_id
    nodes.append(
        {
            "id": f"paper:{paper_id}",
            "label": paper_label,
            "kind": "paper",
            "band": "ok",
        }
    )

    leaked = {h["question_id"] for h in (hotspots or []) if h.get("leaked")}
    chapter_band = {c["name"]: c["band"] for c in (analysis or {}).get("chapters") or []}
    chapter_got: dict[str, float] = {}
    chapter_max: dict[str, float] = {}
    chapter_hardest: dict[str, float] = {}
    chapters_seen: set[str] = set()
    addressed = set((row or {}).get("addressed") or [])
    bonus_map = (row or {}).get("bonus") or {}

    if row and analysis:
        nodes.append(
            {
                "id": f"student:{row['roll']}",
                "label": analysis.get("name") or row.get("name") or row["roll"],
                "kind": "student",
                "band": "ok" if analysis.get("complete") else "weak",
                "got": analysis.get("got"),
                "max": analysis.get("max"),
            }
        )
        edges.append(
            {
                "source": f"student:{row['roll']}",
                "target": f"paper:{paper_id}",
                "kind": "sat",
            }
        )

    for question in paper.get("questions") or []:
        chapter = question.get("chapter") or "Untagged"
        cid = f"chapter:{chapter}"
        qid = f"q:{question['id']}"
        if chapter not in chapters_seen:
            chapters_seen.add(chapter)
            nodes.append(
                {
                    "id": cid,
                    "label": f"[[{chapter}]]",
                    "kind": "chapter",
                    "band": chapter_band.get(chapter, "ok"),
                    "wikilink": chapter,
                }
            )
            edges.append({"source": f"paper:{paper_id}", "target": cid, "kind": "contains"})
            if row and analysis and chapter in (analysis.get("weak") or []):
                edges.append(
                    {
                        "source": f"student:{row['roll']}",
                        "target": cid,
                        "kind": "weak",
                    }
                )
            elif row and analysis and chapter in (analysis.get("strong") or []):
                edges.append(
                    {
                        "source": f"student:{row['roll']}",
                        "target": cid,
                        "kind": "strong",
                    }
                )
        band = "weak" if question["id"] in leaked else chapter_band.get(chapter, "ok")
        empty = False
        cell = None
        max_marks = float(question.get("max_marks") or 0)
        chapter_max[chapter] = chapter_max.get(chapter, 0) + max_marks
        chapter_hardest[chapter] = max(chapter_hardest.get(chapter, 0), max_marks)
        if row:
            cell = row.get("cells", {}).get(question["id"])
            empty = cell is None
            if cell is not None:
                chapter_got[chapter] = chapter_got.get(chapter, 0) + float(cell)
            if cell is not None and max_marks:
                ratio = cell / max_marks
                band = _band(ratio)
        hot = next((h for h in (hotspots or []) if h.get("question_id") == question["id"]), None)
        nodes.append(
            {
                "id": qid,
                "label": f"Q{question['number']}",
                "kind": "question",
                "band": band,
                "empty": empty,
                "leaked": question["id"] in leaked,
                "addressed": question["id"] in addressed,
                "bonus": bonus_map.get(question["id"]) or 0,
                "question_id": question["id"],
                "number": question["number"],
                "chapter": chapter,
                "max_marks": question.get("max_marks"),
                "got": None if empty else cell,
                "confidence": question.get("confidence"),
                "needs_review": bool(question.get("needs_review")),
                "source": question.get("source"),
                "affected": (hot or {}).get("affected"),
                "lost": (hot or {}).get("lost"),
                "class_percent": (hot or {}).get("percent"),
                "class_n": (hot or {}).get("n"),
            }
        )
        edges.append({"source": cid, "target": qid, "kind": "asks"})
        backlinks.setdefault(chapter, []).append(f"Q{question['number']}")
        if row:
            edges.append(
                {
                    "source": f"student:{row['roll']}",
                    "target": qid,
                    "kind": "scored",
                }
            )

    for node in nodes:
        if node.get("kind") != "chapter":
            continue
        name = node.get("wikilink") or ""
        node["got"] = chapter_got.get(name)
        node["max"] = chapter_max.get(name)
        node["hardest"] = chapter_hardest.get(name)

    return {"nodes": nodes, "edges": edges, "backlinks": backlinks}


def _band(percent: float) -> str:
    if percent >= config.STRONG_AT:
        return "strong"
    if percent >= config.OK_AT:
        return "ok"
    return "weak"


def contains_forbidden(text: str) -> bool:
    blob = text.lower()
    return any(word in blob for word in FORBIDDEN_CLAIMS)


def _student_memory(roll: str, class_id: str, state: dict[str, Any]) -> dict[str, Any]:
    from . import memory

    return memory.student_memory(roll, class_id, state)
