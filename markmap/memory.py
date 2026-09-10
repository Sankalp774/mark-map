"""Longitudinal student memory: chapter % over time + intervention outcomes."""

from __future__ import annotations

from typing import Any

from . import analyser, config, store


def chapter_series(roll: str, class_id: str | None = None, state: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    state = state or store.load()
    class_id = class_id or config.DEFAULT_CLASS_ID
    papers = sorted(
        analyser.papers_for_class(state, class_id),
        key=lambda p: (p.get("date") or "", p.get("id") or ""),
    )
    series = []
    for paper in papers:
        row = (state["rows"].get(paper["id"]) or {}).get(roll)
        if not row or not row.get("complete"):
            continue
        analysis = analyser.analyse_row(paper, row)
        series.append(
            {
                "paper_id": paper["id"],
                "title": paper.get("title"),
                "date": paper.get("date"),
                "percent": analysis["percent"],
                "chapters": {c["name"]: c["percent"] for c in analysis["chapters"]},
                "weak": analysis["weak"],
                "losses": analysis["losses"][:3],
            }
        )
    return series


def student_memory(roll: str, class_id: str | None = None, state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or store.load()
    class_id = class_id or config.DEFAULT_CLASS_ID
    series = chapter_series(roll, class_id, state)
    name = None
    for paper in analyser.papers_for_class(state, class_id):
        row = (state["rows"].get(paper["id"]) or {}).get(roll)
        if row:
            name = row.get("name")
            break
    chapters: dict[str, list[dict[str, Any]]] = {}
    for point in series:
        for chapter, percent in (point.get("chapters") or {}).items():
            chapters.setdefault(chapter, []).append(
                {
                    "title": point["title"],
                    "paper_id": point["paper_id"],
                    "percent": percent,
                    "date": point["date"],
                }
            )
    trends = []
    for chapter, points in chapters.items():
        if len(points) < 2:
            trends.append(
                {
                    "chapter": chapter,
                    "from": points[0]["percent"] if points else None,
                    "to": points[-1]["percent"] if points else None,
                    "delta": 0,
                    "points": points,
                }
            )
            continue
        delta = round(points[-1]["percent"] - points[0]["percent"], 1)
        trends.append(
            {
                "chapter": chapter,
                "from": points[0]["percent"],
                "to": points[-1]["percent"],
                "delta": delta,
                "points": points,
            }
        )
    trends.sort(key=lambda t: t["delta"])
    interventions = [
        i
        for i in (state.get("interventions") or [])
        if i.get("roll") == roll and (i.get("class_id") or config.DEFAULT_CLASS_ID) == class_id
    ]
    latest = series[-1] if series else None
    remaining = None
    if latest and latest.get("losses"):
        remaining = latest["losses"][0]
    return {
        "roll": roll,
        "name": name,
        "class_id": class_id,
        "series": series,
        "trends": trends,
        "interventions": interventions[-12:],
        "remaining": remaining,
        "readout": _readout(name or roll, trends, interventions, remaining),
    }


def _readout(name: str, trends: list[dict[str, Any]], interventions: list[dict[str, Any]], remaining: dict[str, Any] | None) -> str:
    measured = [i for i in interventions if i.get("status") == "measured" and i.get("outcome")]
    bits = []
    if measured:
        last = measured[-1]
        outcome = last["outcome"]
        delta = outcome.get("delta")
        bits.append(
            f"{name} improved {last.get('chapter')} by {delta} points after "
            f"{last.get('proposal') or 'the previous intervention'}."
        )
    elif trends:
        worst = trends[0]
        if worst.get("delta", 0) < 0:
            bits.append(
                f"{name}'s {worst['chapter']} fell {abs(worst['delta'])} points "
                f"({worst['from']}% → {worst['to']}%)."
            )
        elif worst.get("to") is not None:
            bits.append(f"{name}'s weakest chapter now is {worst['chapter']} at {worst['to']}%.")
    if remaining:
        bits.append(
            f"Remaining leak: Q{remaining['number']} {remaining['chapter']} "
            f"({_n(remaining['got'])}/{_n(remaining['max'])}). "
            "Do not repeat a generic drill if word problems are the leftover gap."
        )
    return " ".join(bits) if bits else f"No longitudinal file for {name} yet."


def _n(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value)


def class_strategy(paper_id: str, class_id: str | None = None, state: dict[str, Any] | None = None) -> dict[str, Any]:
    """Dominant class gap vs scattered individual leaks."""
    state = state or store.load()
    class_id = class_id or config.DEFAULT_CLASS_ID
    paper = analyser.resolve_paper(state, paper_id, class_id)
    if not paper:
        raise KeyError("Unknown paper")
    rows = list((state["rows"].get(paper["id"]) or {}).values())
    complete = [row for row in rows if row.get("complete")]
    n = len(complete)
    gaps = []
    for question in paper["questions"]:
        qid = question["id"]
        lost_rolls = []
        for row in complete:
            cell = row["cells"].get(qid)
            if cell is None:
                continue
            if cell < float(question["max_marks"]):
                lost_rolls.append(row["roll"])
        affected = len(lost_rolls)
        share = (affected / n) if n else 0
        gaps.append(
            {
                "question_id": qid,
                "number": question["number"],
                "chapter": question["chapter"],
                "affected": affected,
                "n": n,
                "share": round(share * 100, 1),
                "rolls": lost_rolls,
                "dominant": share >= 0.40,
            }
        )
    gaps.sort(key=lambda g: (-g["affected"], g["number"]))
    top = gaps[0] if gaps else None
    if top and top["dominant"]:
        recommendation = {
            "kind": "class_reteach",
            "question_id": top["question_id"],
            "chapter": top["chapter"],
            "affected": top["affected"],
            "leverage": (
                f"Q{top['number']} {top['chapter']} is the dominant class gap "
                f"({top['affected']}/{top['n']} students lost marks). "
                "A 15-minute re-teach is higher leverage than assigning "
                "individual drills to every affected roll."
            ),
        }
    elif top:
        recommendation = {
            "kind": "individual",
            "question_id": top["question_id"],
            "chapter": top["chapter"],
            "affected": top["affected"],
            "leverage": (
                f"Losses are scattered. Q{top['number']} {top['chapter']} "
                f"touched {top['affected']}/{top['n']} students — treat as individual work."
            ),
        }
    else:
        recommendation = {
            "kind": "none",
            "leverage": "No complete scripts, so no class strategy yet.",
        }
    return {
        "paper_id": paper["id"],
        "title": paper.get("title"),
        "n": n,
        "gaps": gaps[:6],
        "recommendation": recommendation,
    }
