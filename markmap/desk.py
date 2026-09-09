"""Desk runner — alerts when nobody is chatting."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from . import analyser, store


def hours_until_ptm(state: dict[str, Any] | None = None) -> float | None:
    state = state or store.load()
    raw = state.get("ptm_at")
    if not raw:
        return None
    when = datetime.fromisoformat(raw)
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    delta = (when - datetime.now(timezone.utc)).total_seconds() / 3600
    return round(delta, 1)


def compute_alerts(state: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    state = state or store.load()
    alerts: list[dict[str, Any]] = []
    hours = hours_until_ptm(state)
    papers = sorted(
        state["papers"].values(),
        key=lambda p: p.get("date") or "",
        reverse=True,
    )
    papers = papers[:1]
    if not papers:
        alerts.append(
            {
                "level": "amber",
                "code": "no_paper",
                "text": "No paper on the desk yet. Load demo Midterm 2 or ingest a paper + CSV.",
            }
        )
        return alerts

    for paper in papers:
        rows = list((state["rows"].get(paper["id"]) or {}).values())
        incomplete = [row for row in rows if not row.get("complete")]
        n = len(rows)
        ready = n - len(incomplete)
        review = [q for q in paper["questions"] if q.get("needs_review")]
        hotspots = analyser.class_hotspots(paper, rows)
        leaked = [h for h in hotspots if h.get("leaked")]

        if incomplete:
            rolls = ", ".join(row["roll"] for row in incomplete)
            alerts.append(
                {
                    "level": "red",
                    "code": "incomplete_scripts",
                    "paper_id": paper["id"],
                    "text": f"{len(incomplete)} scripts incomplete — briefs blocked",
                    "rolls": [row["roll"] for row in incomplete],
                    "detail": rolls,
                }
            )
        if hours is not None:
            ready_txt = f"{ready}/{n} ready" if n else "no rows"
            when = "soon" if hours <= 0 else f"in {hours:g} hours"
            alerts.append(
                {
                    "level": "amber" if incomplete else "green",
                    "code": "ptm_window",
                    "paper_id": paper["id"],
                    "text": f"PTM {when}, {ready_txt}",
                    "hours": hours,
                }
            )
        if review:
            qlist = ", ".join(f"Q{q['number']}" for q in review)
            alerts.append(
                {
                    "level": "amber",
                    "code": "needs_review",
                    "paper_id": paper["id"],
                    "text": f"{len(review)} question tag needs review ({qlist})",
                    "questions": [q["id"] for q in review],
                }
            )
        if leaked:
            top = leaked[0]
            alerts.append(
                {
                    "level": "green",
                    "code": "hotspot",
                    "paper_id": paper["id"],
                    "text": (
                        f"Class hotspot Q{top['number']} {top['chapter']} — "
                        f"mean {top['percent']}%"
                    ),
                    "question_id": top["question_id"],
                }
            )
    return alerts


def run_desk() -> dict[str, Any]:
    state = store.load()
    alerts = compute_alerts(state)

    def _mut(s: dict[str, Any]) -> None:
        s["alerts"] = alerts

    store.update(_mut)
    store.audit("run_desk", {"n": len(alerts)})
    return {
        "alerts": alerts,
        "strands": False,
        "mode": "deterministic",
        "summary": _summary(alerts),
    }


def _summary(alerts: list[dict[str, Any]]) -> str:
    if not alerts:
        return "Desk is clear."
    return " ".join(a["text"] + "." for a in alerts)
