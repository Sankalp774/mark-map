"""Demo Class 10-B. Ravi is the named student. Q9 is the class leak."""

from __future__ import annotations

import csv
import io
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from . import analyser, config, store

STUDENTS: list[tuple[str, str]] = [
    ("01", "Ananya Shah"),
    ("02", "Kabir Iyer"),
    ("03", "Diya Nair"),
    ("04", "Arjun Patel"),
    ("05", "Meera Joshi"),
    ("06", "Ishaan Reddy"),
    ("07", "Sara Khan"),
    ("08", "Vikram Bose"),
    ("09", "Zara Ali"),
    ("10", "Rohan Desai"),
    ("11", "Neha Kulkarni"),
    ("12", "Aditya Rao"),
    ("13", "Priya Menon"),
    ("14", "Kunal Gupta"),
    ("15", "Aisha Rahman"),
    ("16", "Dev Sharma"),
    ("17", "Ravi Mehta"),
    ("18", "Sneha Pillai"),
    ("19", "Yash Jain"),
    ("20", "Fatima Noor"),
    ("21", "Harsh Vardhan"),
    ("22", "Lavanya Iyer"),
    ("23", "Mohit Agarwal"),
    ("24", "Nisha Bansal"),
    ("25", "Omkar Kulkarni"),
    ("26", "Pooja Singh"),
    ("27", "Reyansh Kapoor"),
    ("28", "Tanvi Ghosh"),
    ("29", "Uday Chauhan"),
    ("30", "Veda Srinivasan"),
]

INCOMPLETE_ROLLS = {"04", "11", "28"}

# Midterm 2 Ravi: weak Linear Equations, leak on Q9.
RAVI_M2 = {
    "q1": 3,
    "q2": 4,
    "q3": 2,
    "q4": 3,
    "q5": 5,
    "q6": 6,
    "q7": 7,
    "q8": 6,
    "q9": 3,
    "q10": 16,
}

# Midterm 1 Ravi: same weak chapter, slightly lower overall.
RAVI_M1 = {
    "q1": 3,
    "q2": 3,
    "q3": 2,
    "q4": 2,
    "q5": 5,
    "q6": 5,
    "q7": 6,
    "q8": 6,
    "q9": 4,
    "q10": 14,
}

QUESTION_IDS = [f"q{i}" for i in range(1, 11)]


def _read_paper(name: str) -> str:
    return (config.SAMPLES_DIR / name).read_text(encoding="utf-8")


def _clamp(value: float, lo: float, hi: float) -> int:
    return int(max(lo, min(hi, round(value))))


def _generate_row(
    roll: str,
    name: str,
    questions: list[dict[str, Any]],
    rng: random.Random,
    ravi_cells: dict[str, int],
    q9_cap: int,
    incomplete: bool,
) -> dict[str, Any]:
    cells: dict[str, float | None] = {}
    hero_ok = bool(ravi_cells) and all(q["id"] in ravi_cells for q in questions)
    if hero_ok:
        for q in questions:
            cells[q["id"]] = float(ravi_cells[q["id"]])
    else:
        for q in questions:
            qid = q["id"]
            max_m = q["max_marks"]
            if qid == "q9":
                cells[qid] = float(_clamp(rng.uniform(2, min(q9_cap, max_m)), 0, max_m))
            elif q["chapter"] == "Linear Equations":
                cells[qid] = float(_clamp(max_m * rng.uniform(0.45, 0.85), 0, max_m))
            elif q["chapter"] in {"Triangles", "Trigonometry", "Polynomials"}:
                cells[qid] = float(_clamp(max_m * rng.uniform(0.65, 0.98), 0, max_m))
            else:
                cells[qid] = float(_clamp(max_m * rng.uniform(0.55, 0.95), 0, max_m))
    missing: list[str] = []
    if incomplete:
        blank = "q9" if "q9" in cells else questions[-1]["id"]
        cells[blank] = None
        missing = [blank]
    return {
        "roll": roll,
        "name": name,
        "cells": cells,
        "complete": len(missing) == 0,
        "missing": missing,
    }


CLASS_A_STUDENTS: list[tuple[str, str]] = [
    ("01", "Ira Bose"),
    ("02", "Neil Kapoor"),
    ("03", "Aanya Gill"),
    ("04", "Vivaan Shah"),
    ("05", "Myra Khanna"),
    ("06", "Arnav Joshi"),
    ("07", "Kiara Nair"),
    ("08", "Reyansh Pal"),
    ("09", "Anvi Das"),
    ("10", "Shaurya Jain"),
    ("11", "Diya Bedi"),
    ("12", "Kabir Malhotra"),
]

CLASS_9C_STUDENTS: list[tuple[str, str]] = [
    ("01", "Om Sen"),
    ("02", "Tara Iyer"),
    ("03", "Yug Patel"),
    ("04", "Inaaya Khan"),
    ("05", "Aarav Kulkarni"),
    ("06", "Sana Reddy"),
    ("07", "Ishaan Bhat"),
    ("08", "Mira Rao"),
    ("09", "Dev Menon"),
    ("10", "Zoya Ali"),
]

SCIENCE_TERM = """Greenfield Public School
Class 9-C  Science  Term 1
Date: 10 Jul 2026    Max marks: 80

Q1 (8 marks) [Matter]
State the characteristics of particles of matter.

Q2 (8 marks) [Matter]
Differentiate between solids, liquids and gases with one example each.

Q3 (12 marks) [Cell]
Draw a plant cell and label five parts.

Q4 (12 marks) [Cell]
Write the functions of nucleus and mitochondria.

Q5 (20 marks) [Tissues]
Explain meristematic tissue and name two types.

Q6 (20 marks) [Tissues]
Compare xylem and phloem.
"""

SCIENCE_MID = """Greenfield Public School
Class 9-C  Science  Midterm
Date: 2 Sep 2026    Max marks: 80

Q1 (8 marks) [Motion]
Define uniform and non-uniform motion.

Q2 (8 marks) [Motion]
A car moves 100 m in 5 s. Find its speed.

Q3 (12 marks) [Force]
State Newton's first law of motion.

Q4 (12 marks) [Force]
Give two examples of balanced and unbalanced forces.

Q5 (20 marks) [Gravitation]
State the universal law of gravitation.

Q6 (20 marks)
Explain why a sheet of paper falls slower than a pebble. Mention air resistance.
"""


def build_rows(
    questions: list[dict[str, Any]],
    *,
    seed: int,
    ravi_cells: dict[str, int],
    q9_cap: int,
    incomplete_rolls: set[str],
    students: list[tuple[str, str]] | None = None,
    hero_roll: str = "17",
) -> dict[str, dict[str, Any]]:
    rng = random.Random(seed)
    rows = {}
    for roll, name in students or STUDENTS:
        cells_for_hero = ravi_cells if roll == hero_roll else {}
        row = _generate_row(
            roll,
            name,
            questions,
            rng,
            cells_for_hero,
            q9_cap,
            roll in incomplete_rolls,
        )
        rows[roll] = row
    return rows


def rows_to_csv(rows: dict[str, dict[str, Any]], questions: list[dict[str, Any]]) -> str:
    qids = [q["id"] for q in questions]
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["roll", "name", *qids])
    for roll in sorted(rows):
        row = rows[roll]
        cells = []
        for qid in qids:
            value = row["cells"].get(qid)
            cells.append("" if value is None else int(value) if float(value).is_integer() else value)
        writer.writerow([roll, row["name"], *cells])
    return buf.getvalue()


def write_sample_csvs() -> None:
    config.SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    m1_questions = analyser.map_paper(_read_paper("midterm1_paper.txt"))
    m2_questions = analyser.map_paper(_read_paper("midterm2_paper.txt"))
    m1_rows = build_rows(
        m1_questions, seed=1, ravi_cells=RAVI_M1, q9_cap=8, incomplete_rolls=set()
    )
    m2_rows = build_rows(
        m2_questions, seed=2, ravi_cells=RAVI_M2, q9_cap=6, incomplete_rolls=INCOMPLETE_ROLLS
    )
    m2_blank = build_rows(
        m2_questions, seed=2, ravi_cells=RAVI_M2, q9_cap=6, incomplete_rolls={"17"}
    )
    (config.SAMPLES_DIR / "midterm1_marks.csv").write_text(
        rows_to_csv(m1_rows, m1_questions), encoding="utf-8"
    )
    (config.SAMPLES_DIR / "midterm2_marks.csv").write_text(
        rows_to_csv(m2_rows, m2_questions), encoding="utf-8"
    )
    (config.SAMPLES_DIR / "midterm2_marks_ravi_q9_blank.csv").write_text(
        rows_to_csv(m2_blank, m2_questions), encoding="utf-8"
    )


def demo_users() -> list[dict[str, Any]]:
    return [
        {
            "email": "teacher@markmap.demo",
            "name": "Kavita Sharma",
            "role": "teacher",
            "class_id": "10-B",
            "class_ids": [c["id"] for c in config.CLASSES],
            "password": config.DEMO_PASSWORD,
        },
        {
            "email": "ravi@markmap.demo",
            "name": "Ravi Mehta",
            "role": "student",
            "roll": "17",
            "class_id": "10-B",
            "password": config.DEMO_PASSWORD,
        },
        {
            "email": "parent.ravi@markmap.demo",
            "name": "Parent of Ravi Mehta",
            "role": "parent",
            "roll": "17",
            "class_id": "10-B",
            "password": config.DEMO_PASSWORD,
        },
        {
            "email": "ira@markmap.demo",
            "name": "Ira Bose",
            "role": "student",
            "roll": "01",
            "class_id": "10-A",
            "password": config.DEMO_PASSWORD,
        },
        {
            "email": "parent.ira@markmap.demo",
            "name": "Parent of Ira Bose",
            "role": "parent",
            "roll": "01",
            "class_id": "10-A",
            "password": config.DEMO_PASSWORD,
        },
    ]


def ingest_paper(
    *,
    paper_id: str,
    title: str,
    date: str,
    paper_text: str,
    csv_text: str,
    replace_rows: bool = True,
    section: str | None = None,
    source: str = "demo",
    class_id: str = "10-B",
    subject: str | None = None,
    class_name: str | None = None,
) -> dict[str, Any]:
    paper_id = config.resolve_paper_id(paper_id)
    questions = analyser.map_paper(paper_text)
    if not questions:
        raise ValueError("No questions found. Use lines like: Q1 (4 marks) [Polynomials]")
    rows_list = analyser.parse_marks_csv(csv_text, questions)
    rows = {row["roll"]: row for row in rows_list}
    max_total = sum(q["max_marks"] for q in questions)
    section = section or paper_id
    class_name = class_name or class_id
    subject = subject or config.SCHOOL["subject"]

    def _mut(state: dict[str, Any]) -> None:
        state["papers"][paper_id] = {
            "id": paper_id,
            "title": title,
            "section": section,
            "source": source,
            "class_id": class_id,
            "subject": subject,
            "class_name": class_name,
            "date": date,
            "max_total": max_total,
            "paper_text": paper_text,
            "questions": questions,
        }
        if replace_rows or paper_id not in state["rows"]:
            state["rows"][paper_id] = rows
        else:
            state["rows"][paper_id].update(rows)
        if not state.get("users"):
            state["users"] = demo_users()
        if not state.get("ptm_at"):
            state["ptm_at"] = (datetime.now(timezone.utc) + timedelta(hours=18)).isoformat()
        state["school"] = dict(config.SCHOOL)

    store.update(_mut)
    store.audit("ingest", {"paper_id": paper_id, "n_questions": len(questions), "n_rows": len(rows)})
    return {
        "paper_id": paper_id,
        "n_questions": len(questions),
        "n_rows": len(rows),
        "needs_review": [q["id"] for q in questions if q["needs_review"]],
        "incomplete": [r["roll"] for r in rows_list if not r["complete"]],
    }


def ensure_classes(state: dict[str, Any]) -> None:
    state.setdefault("classes", {})
    for item in config.CLASSES:
        state["classes"].setdefault(item["id"], dict(item))
    for paper in (state.get("papers") or {}).values():
        paper.setdefault("class_id", config.DEFAULT_CLASS_ID)
    for collection in ("broadcasts", "tasks", "calendar", "threads", "interventions"):
        for item in state.get(collection) or []:
            item.setdefault("class_id", config.DEFAULT_CLASS_ID)


def seed_sister_classes() -> None:
    """10-A Mathematics and 9-C Science so the teacher can switch classes."""
    q1 = analyser.map_paper(_read_paper("midterm1_paper.txt"))
    q2 = analyser.map_paper(_read_paper("midterm2_paper.txt"))
    a1 = build_rows(
        q1, seed=11, ravi_cells={}, q9_cap=8, incomplete_rolls=set(),
        students=CLASS_A_STUDENTS, hero_roll="",
    )
    a2 = build_rows(
        q2, seed=12, ravi_cells={}, q9_cap=6, incomplete_rolls={"03"},
        students=CLASS_A_STUDENTS, hero_roll="",
    )
    ingest_paper(
        paper_id="10-A:term-1", title="Term 1", date="2026-07-14",
        paper_text=_read_paper("midterm1_paper.txt"), csv_text=rows_to_csv(a1, q1),
        section="term-1", source="demo", class_id="10-A", class_name="10-A",
        subject="Mathematics",
    )
    ingest_paper(
        paper_id="10-A:midterm", title="Midterm", date="2026-09-05",
        paper_text=_read_paper("midterm2_paper.txt"), csv_text=rows_to_csv(a2, q2),
        section="midterm", source="demo", class_id="10-A", class_name="10-A",
        subject="Mathematics",
    )
    s1q = analyser.map_paper(SCIENCE_TERM)
    s2q = analyser.map_paper(SCIENCE_MID)
    s1 = build_rows(
        s1q, seed=21, ravi_cells={}, q9_cap=8, incomplete_rolls=set(),
        students=CLASS_9C_STUDENTS, hero_roll="",
    )
    s2 = build_rows(
        s2q, seed=22, ravi_cells={}, q9_cap=6, incomplete_rolls={"04"},
        students=CLASS_9C_STUDENTS, hero_roll="",
    )
    ingest_paper(
        paper_id="9-C:term-1", title="Term 1", date="2026-07-10",
        paper_text=SCIENCE_TERM, csv_text=rows_to_csv(s1, s1q),
        section="term-1", source="demo", class_id="9-C", class_name="9-C",
        subject="Science",
    )
    ingest_paper(
        paper_id="9-C:midterm", title="Midterm", date="2026-09-02",
        paper_text=SCIENCE_MID, csv_text=rows_to_csv(s2, s2q),
        section="midterm", source="demo", class_id="9-C", class_name="9-C",
        subject="Science",
    )


def migrate_legacy_ids(state: dict[str, Any]) -> None:
    mapping = {"midterm-1": "term-1", "midterm-2": "midterm"}
    titles = {"term-1": "Term 1", "midterm": "Midterm"}
    for old, new in mapping.items():
        if old in state.get("papers", {}) and new not in state["papers"]:
            paper = state["papers"].pop(old)
            paper["id"] = new
            paper["section"] = new
            paper["title"] = titles[new]
            state["papers"][new] = paper
        if old in state.get("rows", {}) and new not in state["rows"]:
            state["rows"][new] = state["rows"].pop(old)
    ensure_classes(state)


def load_demo_midterm_2() -> dict[str, Any]:
    write_sample_csvs()
    from . import ocr

    ocr.generate_ravi_report_png()
    m1 = ingest_paper(
        paper_id="term-1",
        title="Term 1",
        date="2026-07-12",
        paper_text=_read_paper("midterm1_paper.txt"),
        csv_text=(config.SAMPLES_DIR / "midterm1_marks.csv").read_text(encoding="utf-8"),
        section="term-1",
        source="demo",
        class_id="10-B",
        class_name="10-B",
        subject="Mathematics",
    )
    m2 = ingest_paper(
        paper_id="midterm",
        title="Midterm",
        date="2026-09-04",
        paper_text=_read_paper("midterm2_paper.txt"),
        csv_text=(config.SAMPLES_DIR / "midterm2_marks.csv").read_text(encoding="utf-8"),
        section="midterm",
        source="demo",
        class_id="10-B",
        class_name="10-B",
        subject="Mathematics",
    )
    store.update(ensure_classes)
    seed_sister_classes()
    from . import desk, workspace

    workspace.seed_defaults()
    desk.run_desk()
    return {"term_1": m1, "midterm": m2}


def load_ravi_q9_blank() -> dict[str, Any]:
    write_sample_csvs()
    state = store.load()
    if analyser.resolve_paper(state, "midterm") is None:
        load_demo_midterm_2()
    csv_text = (config.SAMPLES_DIR / "midterm2_marks_ravi_q9_blank.csv").read_text(
        encoding="utf-8"
    )
    paper = analyser.resolve_paper(store.load(), "midterm")
    rows_list = analyser.parse_marks_csv(csv_text, paper["questions"])
    ravi = next(row for row in rows_list if row["roll"] == "17")

    def _mut(s: dict[str, Any]) -> None:
        s["rows"][paper["id"]]["17"] = ravi

    store.update(_mut)
    store.audit("blank_q9", {"roll": "17", "paper_id": paper["id"]})
    from . import desk

    desk.run_desk()
    return ravi


def reset_store() -> None:
    store.save(store.default_state())
    store.update(lambda s: s.__setitem__("users", demo_users()))
