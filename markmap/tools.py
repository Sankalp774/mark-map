"""Python tools the Strands specialists call. Numbers stay in analyser.py."""

from __future__ import annotations

import json
from typing import Any

from . import analyser, briefs, config, desk, seed, store

try:
    from strands import tool as strands_tool
except ImportError:  # pragma: no cover - demo still runs without the SDK
    def strands_tool(fn=None, **_kwargs):
        def wrap(func):
            return func

        return wrap if fn is None else wrap(fn)


def _dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


@strands_tool
def load_demo_midterm_2() -> str:
    """Load seeded Term 1 + Midterm papers and marks into the store."""
    result = seed.load_demo_midterm_2()
    store.agent_log("ingest_clerk", "Loaded demo Term 1 + Midterm.")
    return _dumps(result)


@strands_tool
def ingest_paper_and_marks(paper_text: str, csv_text: str, title: str = "Uploaded paper") -> str:
    """Ingest a question paper (plain text) and a marks CSV (roll,name,q1,q2,...)."""
    paper_id = title.lower().replace(" ", "-")[:40] or "uploaded"
    result = seed.ingest_paper(
        paper_id=paper_id,
        title=title,
        date="2026-09-04",
        paper_text=paper_text,
        csv_text=csv_text,
    )
    store.agent_log("ingest_clerk", f"Ingested {title}.")
    return _dumps(result)


@strands_tool
def map_current_paper(paper_id: str = "midterm") -> str:
    """Return the question-to-chapter map for a paper already in the store."""
    paper = store.load()["papers"].get(paper_id)
    if not paper:
        return _dumps({"error": f"Unknown paper {paper_id}"})
    return _dumps({"paper_id": paper_id, "questions": paper["questions"]})


@strands_tool
def set_question_chapter(paper_id: str, question_id: str, chapter: str) -> str:
    """Teacher correction for a chapter tag. Use when the map is unsure."""
    paper = analyser.set_question_chapter(paper_id, question_id, chapter)
    return _dumps({"paper_id": paper_id, "questions": paper["questions"]})


@strands_tool
def list_incomplete_rows(paper_id: str = "midterm") -> str:
    """List rolls with empty mark cells. Briefs stay blocked for these rows."""
    rows = list((store.load()["rows"].get(paper_id) or {}).values())
    incomplete = [
        {"roll": r["roll"], "name": r["name"], "missing": r["missing"]}
        for r in rows
        if not r.get("complete")
    ]
    return _dumps({"paper_id": paper_id, "incomplete": incomplete, "n": len(incomplete)})


@strands_tool
def analyse_student(roll: str, paper_id: str = "midterm") -> str:
    """Marks × chapter for one roll. Does not invent missing marks."""
    try:
        bundle = analyser.student_bundle(paper_id, roll)
    except KeyError as exc:
        return _dumps({"error": str(exc)})
    return _dumps(
        {
            "analysis": bundle["analysis"],
            "year": bundle["year"],
        }
    )


@strands_tool
def class_hotspots(paper_id: str = "midterm") -> str:
    """Questions the section leaked, sorted hardest first."""
    try:
        bundle = analyser.class_bundle(paper_id)
    except KeyError as exc:
        return _dumps({"error": str(exc)})
    return _dumps({"paper_id": paper_id, "hotspots": bundle["hotspots"], "counts": bundle["counts"]})


@strands_tool
def write_student_briefs(roll: str, paper_id: str = "midterm") -> str:
    """Teacher PTM brief + family brief from analyser facts. Blocked if any cell is empty."""
    try:
        bundle = analyser.student_bundle(paper_id, roll)
    except KeyError as exc:
        return _dumps({"error": str(exc)})
    payload = briefs.write_briefs(bundle["analysis"], bundle["year"])
    return _dumps(payload)


@strands_tool
def run_desk_nags() -> str:
    """Compute incomplete-script and PTM-window alerts. Safe to run when nobody is chatting."""
    result = desk.run_desk()
    store.agent_log("desk_runner", result["summary"])
    return _dumps(result)


@strands_tool
def blank_ravi_q9() -> str:
    """Demo guardrail: clear Ravi's Q9 so his brief is blocked."""
    row = seed.load_ravi_q9_blank()
    store.agent_log("score_clerk", "Ravi Q9 cleared. Brief blocked.")
    return _dumps({"roll": row["roll"], "missing": row["missing"], "complete": row["complete"]})


@strands_tool
def ingest_screenshot_report() -> str:
    """Read the demo student-report screenshot and split Term 1 vs Midterm."""
    from . import ocr

    path = ocr.generate_ravi_report_png()
    text, engine = ocr.extract_text(path.read_bytes())
    parsed = ocr.parse_report(text)
    result = ocr.ingest_parsed_report(parsed, source="screenshot")
    store.agent_log("ingest_clerk", f"Screenshot report via {engine}.")
    return _dumps({"engine": engine, **result})


PYTHON_TOOLS = [
    load_demo_midterm_2,
    ingest_paper_and_marks,
    ingest_screenshot_report,
    map_current_paper,
    set_question_chapter,
    list_incomplete_rows,
    analyse_student,
    class_hotspots,
    write_student_briefs,
    run_desk_nags,
    blank_ravi_q9,
]


def health() -> dict[str, Any]:
    return {
        "strands_sdk": _strands_importable(),
        "strands_enabled": config.strands_enabled(),
        "model": config.BEDROCK_MODEL_ID if config.strands_enabled() else None,
        "region": config.AWS_REGION,
        "ocr": _ocr_ready(),
    }


def _strands_importable() -> bool:
    try:
        import strands  # noqa: F401

        return True
    except ImportError:
        return False


def _ocr_ready() -> bool:
    try:
        from . import ocr

        return ocr.tesseract_available()
    except Exception:
        return False
