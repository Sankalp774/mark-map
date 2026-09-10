"""Intervention propose → approve → assign → measure."""

from __future__ import annotations

from typing import Any

from . import analyser, config, store, workspace


def propose(
    *,
    class_id: str,
    kind: str,
    chapter: str,
    proposal: str,
    paper_id: str,
    question_id: str | None = None,
    roll: str | None = None,
    rolls: list[str] | None = None,
    code: str | None = None,
) -> dict[str, Any] | None:
    state = store.load()
    code = code or f"{kind}:{paper_id}:{question_id or chapter}:{roll or 'class'}"
    existing = [
        i
        for i in (state.get("interventions") or [])
        if i.get("code") == code and i.get("status") in {"proposed", "approved", "assigned", "completed", "measured"}
    ]
    if existing:
        return None
    paper = analyser.resolve_paper(state, paper_id, class_id)
    baseline = None
    if roll and paper:
        row = (state["rows"].get(paper["id"]) or {}).get(roll)
        if row and row.get("complete"):
            analysis = analyser.analyse_row(paper, row)
            ch = next((c for c in analysis["chapters"] if c["name"] == chapter), None)
            baseline = {
                "paper_id": paper["id"],
                "percent": ch["percent"] if ch else analysis["percent"],
            }
    item = {
        "id": workspace._id("intv"),
        "code": code,
        "class_id": class_id,
        "kind": kind,
        "status": "proposed",
        "chapter": chapter,
        "question_id": question_id,
        "roll": roll,
        "rolls": rolls or ([roll] if roll else []),
        "proposal": proposal,
        "paper_id": paper_id,
        "baseline": baseline,
        "outcome": None,
        "at": workspace._now(),
    }

    def _mut(s: dict[str, Any]) -> None:
        s.setdefault("interventions", []).append(item)
        s["interventions"] = s["interventions"][-80:]

    store.update(_mut)
    store.audit("propose_intervention", {"id": item["id"], "kind": kind})
    return item


def approve(intervention_id: str, teacher: str) -> dict[str, Any]:
    found: dict[str, Any] = {}

    def _mut(state: dict[str, Any]) -> None:
        for item in state.get("interventions") or []:
            if item["id"] != intervention_id:
                continue
            if item.get("status") != "proposed":
                found.update(item)
                return
            item["status"] = "approved"
            item["approved_at"] = workspace._now()
            item["teacher"] = teacher
            found.update(item)
            return
        raise KeyError("Unknown intervention")

    store.update(_mut)
    if found.get("status") == "approved" and not found.get("assigned_at"):
        _assign(found, teacher)
        found = next(
            i for i in store.load().get("interventions") or [] if i["id"] == intervention_id
        )
    return found


def _assign(item: dict[str, Any], teacher: str) -> None:
    class_id = item.get("class_id") or config.DEFAULT_CLASS_ID
    if item.get("kind") == "class_reteach":
        workspace.broadcast(
            audience="students",
            title=f"Re-teach: {item.get('chapter')}",
            body=item.get("proposal") or "Class re-teach on the dominant gap.",
            teacher=teacher,
            class_id=class_id,
        )
        workspace.assign_task(
            roll="*",
            title=f"Class drill · {item.get('chapter')}",
            body=item.get("proposal") or "",
            teacher=teacher,
            question_id=item.get("question_id"),
            paper_id=item.get("paper_id"),
            class_id=class_id,
        )
    else:
        workspace.assign_task(
            roll=item.get("roll") or "*",
            title=f"Practice · {item.get('chapter')}",
            body=item.get("proposal") or "",
            teacher=teacher,
            question_id=item.get("question_id"),
            paper_id=item.get("paper_id"),
            class_id=class_id,
        )

    def _mut(state: dict[str, Any]) -> None:
        for row in state.get("interventions") or []:
            if row["id"] == item["id"]:
                row["status"] = "assigned"
                row["assigned_at"] = workspace._now()

    store.update(_mut)


def measure_due(class_id: str) -> list[dict[str, Any]]:
    """If a later paper exists after baseline, record chapter delta."""
    state = store.load()
    papers = sorted(
        analyser.papers_for_class(state, class_id),
        key=lambda p: (p.get("date") or "", p.get("id") or ""),
    )
    measured = []
    for item in list(state.get("interventions") or []):
        if (item.get("class_id") or config.DEFAULT_CLASS_ID) != class_id:
            continue
        if item.get("status") not in {"assigned", "completed", "approved"}:
            continue
        baseline = item.get("baseline") or {}
        base_id = baseline.get("paper_id")
        later = [p for p in papers if base_id and p["id"] != base_id and (p.get("date") or "") >= _paper_date(papers, base_id)]
        later = [p for p in later if p["id"] != base_id]
        if not later:
            continue
        nxt = later[0]
        roll = item.get("roll")
        if not roll:
            continue
        row = (state["rows"].get(nxt["id"]) or {}).get(roll)
        if not row or not row.get("complete"):
            continue
        analysis = analyser.analyse_row(nxt, row)
        ch = next((c for c in analysis["chapters"] if c["name"] == item.get("chapter")), None)
        now_pct = ch["percent"] if ch else analysis["percent"]
        before = baseline.get("percent")
        delta = round(now_pct - before, 1) if before is not None else None
        outcome = {
            "paper_id": nxt["id"],
            "title": nxt.get("title"),
            "percent": now_pct,
            "delta": delta,
        }

        def _mut(s: dict[str, Any], iid=item["id"], out=outcome) -> None:
            for row_i in s.get("interventions") or []:
                if row_i["id"] == iid:
                    row_i["status"] = "measured"
                    row_i["outcome"] = out

        store.update(_mut)
        measured.append({**item, "status": "measured", "outcome": outcome})
    return measured


def _paper_date(papers: list[dict[str, Any]], paper_id: str) -> str:
    for paper in papers:
        if paper["id"] == paper_id:
            return paper.get("date") or ""
    return ""


def effectiveness(chapter: str, class_id: str) -> dict[str, Any]:
    state = store.load()
    rows = [
        i
        for i in (state.get("interventions") or [])
        if i.get("chapter") == chapter
        and i.get("status") == "measured"
        and (i.get("class_id") or config.DEFAULT_CLASS_ID) == class_id
        and i.get("outcome")
    ]
    wins = [i for i in rows if (i["outcome"].get("delta") or 0) > 0]
    return {
        "chapter": chapter,
        "n": len(rows),
        "helped": len(wins),
        "line": (
            f"This {chapter} intervention improved {len(wins)}/{len(rows)} measured students."
            if rows
            else f"No measured {chapter} interventions yet."
        ),
    }


def seed_ravi_history() -> None:
    """Term 1 Linear Equations drill, measured against Midterm."""
    state = store.load()
    if any(i.get("code") == "individual:term-1:Linear Equations:17" for i in (state.get("interventions") or [])):
        return
    paper = analyser.resolve_paper(state, "term-1", "10-B")
    mid = analyser.resolve_paper(state, "midterm", "10-B")
    if not paper or not mid:
        return
    row_t = (state["rows"].get(paper["id"]) or {}).get("17")
    row_m = (state["rows"].get(mid["id"]) or {}).get("17")
    if not row_t or not row_m:
        return
    a_t = analyser.analyse_row(paper, row_t)
    a_m = analyser.analyse_row(mid, row_m)
    ch_t = next((c for c in a_t["chapters"] if c["name"] == "Linear Equations"), None)
    ch_m = next((c for c in a_m["chapters"] if c["name"] == "Linear Equations"), None)
    if not ch_t or not ch_m:
        return
    item = {
        "id": "intv-ravi-le-t1",
        "code": "individual:term-1:Linear Equations:17",
        "class_id": "10-B",
        "kind": "individual",
        "status": "measured",
        "chapter": "Linear Equations",
        "question_id": "q9",
        "roll": "17",
        "rolls": ["17"],
        "proposal": "3 practice questions on pair-of-linear-equations (not word problems yet)",
        "paper_id": "term-1",
        "baseline": {"paper_id": "term-1", "percent": ch_t["percent"]},
        "outcome": {
            "paper_id": "midterm",
            "title": "Midterm",
            "percent": ch_m["percent"],
            "delta": round(ch_m["percent"] - ch_t["percent"], 1),
        },
        "at": "2026-07-20T00:00:00+00:00",
        "assigned_at": "2026-07-20T00:00:00+00:00",
    }

    def _mut(s: dict[str, Any]) -> None:
        s.setdefault("interventions", []).append(item)

    store.update(_mut)
