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
            chapter, source, needs_review = tag, "paper_tag", False
        else:
            chapter, source, needs_review = _guess_chapter(prompt)
        questions.append(
            {
                "id": f"q{number}",
                "number": number,
                "max_marks": max_marks,
                "chapter": chapter,
                "prompt": prompt,
                "source": source,
                "needs_review": needs_review,
            }
        )
    questions.sort(key=lambda q: q["number"])
    return questions


def _guess_chapter(prompt: str) -> tuple[str, str, bool]:
    blob = f" {prompt.lower()} "
    scores: dict[str, int] = {}
    for chapter, words in CHAPTER_KEYWORDS.items():
        scores[chapter] = sum(1 for word in words if word in blob)
    best = max(scores, key=lambda k: scores[k])
    if scores[best] <= 0:
        return "Untagged", "none", True
    return best, "keyword", True


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
                return
        raise KeyError(f"Unknown question {question_id}")

    store.update(_mut)
    store.audit("fix_tag", {"paper_id": paper_id, "question_id": question_id, "chapter": chapter})
    state = store.load()
    return resolve_paper(state, paper_id)


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
            }
        )
    hotspots.sort(key=lambda h: (h["percent"], h["number"]))
    return hotspots


def year_line(roll: str, state: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    state = state or store.load()
    points = []
    papers = sorted(
        state["papers"].values(),
        key=lambda p: (_section_rank(p), p.get("date") or "", p.get("id") or ""),
    )
    for paper in papers:
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
    hotspots = class_hotspots(paper, list((state["rows"].get(paper_id) or {}).values()))
    return {
        "paper": _public_paper(paper),
        "row": row,
        "analysis": analysis,
        "hotspots": hotspots,
        "year": year_line(roll, state),
        "brain": brain_graph(paper, row, analysis, hotspots),
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
    }


def _section_rank(paper: dict[str, Any]) -> int:
    section = paper.get("section") or paper.get("id") or ""
    order = {item["id"]: i for i, item in enumerate(config.SECTIONS)}
    return order.get(section, 50)


def resolve_paper(state: dict[str, Any], paper_id: str) -> dict[str, Any] | None:
    pid = config.resolve_paper_id(paper_id)
    return state["papers"].get(pid) or state["papers"].get(paper_id)


def student_sections(roll: str, state: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Term 1 and Midterm as separate report blocks, same roll."""
    from . import briefs

    state = state or store.load()
    blocks = []
    for spec in config.SECTIONS:
        paper = resolve_paper(state, spec["paper_id"])
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
        if row:
            cell = row.get("cells", {}).get(question["id"])
            if cell is not None and question["max_marks"]:
                ratio = cell / question["max_marks"]
                band = _band(ratio)
        nodes.append(
            {
                "id": qid,
                "label": f"Q{question['number']}",
                "kind": "question",
                "band": band,
                "leaked": question["id"] in leaked,
                "addressed": question["id"] in addressed,
                "bonus": bonus_map.get(question["id"]) or 0,
                "question_id": question["id"],
                "number": question["number"],
                "chapter": chapter,
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
