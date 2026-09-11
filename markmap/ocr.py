"""Screenshot → paper + marks. Tesseract when present; PNG text chunk as fallback."""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from typing import Any

from . import analyser, config, seed, store

SECTION_SPLIT = re.compile(r"^\s*SECTION\s+(Term\s*1|Midterm)\s*$", re.I | re.M)
Q_LINE = re.compile(
    r"Q\s*(\d+)\s*[\.)]?\s*\((\d+)\s*marks?\)\s*(?:\[([^\]]+)\])?\s*(?:(\d+)\s*/\s*(\d+))?",
    re.I,
)
TOTAL_RE = re.compile(r"TOTAL\s+(\d+)\s*/\s*(\d+)", re.I)
ROLL_RE = re.compile(r"Roll\s*[:#]?\s*(\d+)", re.I)
NAME_RE = re.compile(r"Name\s*[:#]?\s*([A-Za-z][A-Za-z .'-]+)", re.I)
MARKMAP_META = "markmap_kind"


def tesseract_available() -> bool:
    try:
        import pytesseract
        from shutil import which

        return which("tesseract") is not None or bool(pytesseract.get_tesseract_version())
    except Exception:
        return False


def extract_text(image_bytes: bytes) -> tuple[str, str]:
    """Return (text, engine). engine is tesseract | png-meta | empty."""
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps

    img = Image.open(io.BytesIO(image_bytes))
    if img.mode not in {"RGB", "L"}:
        img = img.convert("RGB")
    meta = ""
    if hasattr(img, "text"):
        meta = (img.text or {}).get(MARKMAP_META) or (img.text or {}).get("markmap_text") or ""
    ocr = ""
    if tesseract_available():
        try:
            import pytesseract

            work = img.convert("L")
            if min(work.size) < 900:
                work = work.resize((work.width * 2, work.height * 2))
            work = ImageOps.autocontrast(work)
            work = ImageEnhance.Contrast(work).enhance(1.6)
            work = work.filter(ImageFilter.SHARPEN)
            ocr = pytesseract.image_to_string(work, config="--psm 6")
            if header_count(ocr) < 3:
                alt = pytesseract.image_to_string(work, config="--psm 4")
                if header_count(alt) > header_count(ocr):
                    ocr = alt
        except Exception:
            ocr = ""
    text = (ocr or "").strip()
    meta_text = meta.strip()
    if meta_text.startswith("kind:"):
        meta_text = ""
    if _looks_like_report(text) and ROLL_RE.search(text) and NAME_RE.search(text):
        return text, "tesseract"
    if meta_text:
        return meta_text, "png-meta"
    if text:
        return text, "tesseract"
    return "", "empty"


def _looks_like_report(text: str) -> bool:
    if not text:
        return False
    if SECTION_SPLIT.search(text) and Q_LINE.search(text):
        return True
    return bool(header_count(text) >= 3)


def header_count(text: str) -> int:
    return len(Q_LINE.findall(text))


HEADER_COUNT = header_count


def parse_report(text: str) -> dict[str, Any]:
    """Split a student report screenshot into Term 1 / Midterm blocks."""
    cleaned = text.replace("§", "S").replace("|", " ")
    roll_m = ROLL_RE.search(cleaned)
    name_m = NAME_RE.search(cleaned)
    roll = roll_m.group(1).zfill(2) if roll_m else None
    name = name_m.group(1).strip() if name_m else None
    parts = SECTION_SPLIT.split(cleaned)
    text = cleaned
    # split keeps the section title as groups: [preamble, 'Term 1', body, 'Midterm', body, ...]
    sections: list[dict[str, Any]] = []
    if len(parts) >= 3:
        i = 1
        while i + 1 < len(parts):
            title = parts[i].strip()
            body = parts[i + 1]
            sections.append(_parse_section_body(title, body, roll, name))
            i += 2
    elif Q_LINE.search(text):
        sections.append(_parse_section_body("Midterm", text, roll, name))
    return {
        "roll": roll,
        "name": name,
        "sections": [s for s in sections if s["questions"]],
        "raw": text,
    }


def _parse_section_body(title: str, body: str, roll: str | None, name: str | None) -> dict[str, Any]:
    section_id = "term-1" if re.search(r"term\s*1", title, re.I) else "midterm"
    nice = "Term 1" if section_id == "term-1" else "Midterm"
    questions = []
    cells: dict[str, float | None] = {}
    paper_lines = [f"{config.SCHOOL['name']}", f"Class 10-B  Mathematics  {nice}", ""]
    for match in Q_LINE.finditer(body):
        number = int(match.group(1))
        max_marks = int(match.group(2))
        tag = match.group(3).strip() if match.group(3) else None
        got = float(match.group(4)) if match.group(4) is not None else None
        qid = f"q{number}"
        chapter = f" [{tag}]" if tag else ""
        paper_lines.append(f"Q{number} ({max_marks} marks){chapter}")
        paper_lines.append("")
        questions.append({"id": qid, "number": number, "max_marks": max_marks, "chapter": tag})
        cells[qid] = got
    paper_text = "\n".join(paper_lines)
    mapped = analyser.map_paper(paper_text)
    qids = [q["id"] for q in mapped] or [q["id"] for q in questions]
    missing = [qid for qid in qids if cells.get(qid) is None]
    csv_text = _one_row_csv(roll or "17", name or "Unknown", qids, cells)
    return {
        "section": section_id,
        "title": nice,
        "paper_id": section_id,
        "paper_text": paper_text,
        "csv_text": csv_text,
        "questions": mapped or questions,
        "cells": cells,
        "roll": roll,
        "name": name,
        "complete": len(missing) == 0 and bool(qids),
        "missing": missing,
    }


def _one_row_csv(roll: str, name: str, qids: list[str], cells: dict[str, float | None]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["roll", "name", *qids])
    row = []
    for qid in qids:
        value = cells.get(qid)
        row.append("" if value is None else int(value) if float(value).is_integer() else value)
    writer.writerow([roll, name, *row])
    return buf.getvalue()


def read_and_maybe_ingest(image_bytes: bytes) -> dict[str, Any]:
    text, engine = extract_text(image_bytes)
    parsed = parse_report(text) if text else {"roll": None, "name": None, "sections": [], "raw": text}
    if not parsed.get("sections"):
        return {
            "ok": False,
            "engine": engine,
            "engine_label": "embedded sample text" if engine == "png-meta" else engine,
            "text": text,
            "error": "No Term 1 / Midterm questions found. Use a report that lists SECTION Term 1 and SECTION Midterm with Q1 (4 marks) 3/4 lines.",
            "sections": [],
            "roll": parsed.get("roll"),
            "name": parsed.get("name"),
        }
    state = store.load()
    if analyser.resolve_paper(state, "midterm") is None:
        seed.load_demo_midterm_2()
    result = ingest_parsed_report(parsed, source="screenshot")
    roll = result.get("roll") or parsed.get("roll") or "17"
    return {
        "ok": True,
        "engine": engine,
        "engine_label": "embedded sample text" if engine == "png-meta" else engine,
        "text": text,
        "error": None,
        **result,
        "roll": roll,
        "name": parsed.get("name"),
        "preview": [
            {
                "title": block["title"],
                "section": block["section"],
                "complete": block["complete"],
                "cells": block["cells"],
            }
            for block in parsed["sections"]
        ],
        "sections": analyser.student_sections(roll),
    }


def ingest_parsed_report(parsed: dict[str, Any], *, source: str = "screenshot") -> dict[str, Any]:
    ingested = []
    dates = {"term-1": "2026-07-12", "midterm": "2026-09-04"}
    for block in parsed.get("sections") or []:
        state = store.load()
        existing = analyser.resolve_paper(state, block["paper_id"])
        if existing:
            rows_list = analyser.parse_marks_csv(block["csv_text"], existing["questions"])
            overlay = {row["roll"]: row for row in rows_list}

            def _mut(s: dict[str, Any], paper_id=existing["id"], rows=overlay) -> None:
                s["rows"].setdefault(paper_id, {}).update(rows)

            store.update(_mut)
            ingested.append(
                {
                    "paper_id": existing["id"],
                    "overlay_rolls": list(overlay),
                    "n_questions": len(existing["questions"]),
                }
            )
        else:
            result = seed.ingest_paper(
                paper_id=block["paper_id"],
                title=block["title"],
                date=dates.get(block["section"], "2026-09-04"),
                paper_text=block["paper_text"],
                csv_text=block["csv_text"],
                replace_rows=False,
                section=block["section"],
                source=source,
            )
            ingested.append(result)
    from . import desk

    desk.run_desk()
    store.audit("screenshot_ingest", {"n": len(ingested), "roll": parsed.get("roll")})
    return {"ingested": ingested, "roll": parsed.get("roll"), "name": parsed.get("name")}


def generate_ravi_report_png(path: Path | None = None) -> Path:
    """High-contrast student report covering Term 1 and Midterm — made to OCR."""
    from PIL import Image, ImageDraw, ImageFont
    from PIL.PngImagePlugin import PngInfo

    seed.write_sample_csvs()
    term_q = analyser.map_paper((config.SAMPLES_DIR / "midterm1_paper.txt").read_text())
    mid_q = analyser.map_paper((config.SAMPLES_DIR / "midterm2_paper.txt").read_text())
    text = render_report_text("17", "Ravi Mehta", term_q, seed.RAVI_M1, mid_q, seed.RAVI_M2)
    path = path or (config.SAMPLES_DIR / "ravi_report.png")
    font = _font(28)
    small = _font(22)
    lines = text.splitlines()
    width = 1100
    line_h = 36
    height = 80 + line_h * len(lines)
    img = Image.new("RGB", (width, height), "#fffdf8")
    draw = ImageDraw.Draw(img)
    y = 36
    for line in lines:
        use = font if line.startswith("SECTION") or line.startswith("GREENFIELD") else small
        fill = "#b45309" if line.startswith("SECTION") else "#1c1917"
        draw.text((48, y), line, font=use, fill=fill)
        y += line_h
    info = PngInfo()
    info.add_text(MARKMAP_META, text)
    info.add_text("markmap_kind", "ravi-report")
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", pnginfo=info)
    (config.SAMPLES_DIR / "ravi_report.txt").write_text(text, encoding="utf-8")
    return path


def render_report_text(
    roll: str,
    name: str,
    term_questions: list[dict[str, Any]],
    term_cells: dict[str, int],
    mid_questions: list[dict[str, Any]],
    mid_cells: dict[str, int],
) -> str:
    lines = [
        config.SCHOOL["name"].upper(),
        "MARK MAP STUDENT REPORT",
        f"Class {config.SCHOOL['class_name']} {config.SCHOOL['subject']}",
        f"Name {name}",
        f"Roll {roll}",
        "",
        *_section_lines("Term 1", term_questions, term_cells),
        "",
        *_section_lines("Midterm", mid_questions, mid_cells),
    ]
    return "\n".join(lines)


def _section_lines(title: str, questions: list[dict[str, Any]], cells: dict[str, int]) -> list[str]:
    lines = [f"SECTION {title}"]
    total = 0
    max_total = 0
    for q in questions:
        got = int(cells[q["id"]])
        max_m = int(q["max_marks"])
        total += got
        max_total += max_m
        tag = f" [{q['chapter']}]" if q.get("chapter") and q.get("source") == "paper_tag" else (
            f" [{q['chapter']}]" if q.get("chapter") and q["chapter"] != "Untagged" else ""
        )
        # Q10 on midterm has no paper tag in the source paper.
        if q["id"] == "q10" and title == "Midterm":
            tag = ""
        lines.append(f"Q{q['number']} ({max_m} marks){tag} {got}/{max_m}")
    lines.append(f"TOTAL {total}/{max_total}")
    return lines


def _font(size: int):
    from PIL import ImageFont

    candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()
