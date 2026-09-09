"""Live class operations: broadcasts, tasks, calendar, bonus, address-issue."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from . import analyser, store


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def snapshot(user: dict[str, Any] | None = None) -> dict[str, Any]:
    state = store.load()
    roll = (user or {}).get("roll")
    role = (user or {}).get("role")
    tasks = list(state.get("tasks") or [])
    broadcasts = list(state.get("broadcasts") or [])
    if role in {"student", "parent"} and roll:
        tasks = [t for t in tasks if t.get("roll") in {None, roll, "*"}]
        audiences = {"students", "all"}
        if role == "parent":
            audiences.add("parents")
        else:
            audiences.add("students")
        broadcasts = [b for b in broadcasts if b.get("audience") in audiences or b.get("roll") == roll]
    return {
        "tasks": sorted(tasks, key=lambda t: t.get("at") or "", reverse=True)[:40],
        "broadcasts": sorted(broadcasts, key=lambda b: b.get("at") or "", reverse=True)[:40],
        "calendar": sorted(state.get("calendar") or [], key=lambda c: c.get("date") or ""),
        "interventions": [
            i
            for i in (state.get("interventions") or [])
            if role == "teacher" or i.get("roll") == roll
        ][-40:],
        "queries": [
            q
            for q in (state.get("queries") or [])
            if role == "teacher" or q.get("roll") == roll
        ][-20:],
    }


def seed_defaults() -> None:
    def _mut(state: dict[str, Any]) -> None:
        if not state.get("calendar"):
            state["calendar"] = [
                {
                    "id": "cal-term-exam",
                    "title": "Term examination",
                    "date": "2026-09-28",
                    "syllabus": (
                        "Linear Equations (word problems, hostel-charges type), "
                        "Triangles (similarity), Statistics (mean and median)."
                    ),
                    "at": _now(),
                }
            ]

    store.update(_mut)


def broadcast(*, audience: str, title: str, body: str, teacher: str) -> dict[str, Any]:
    audience = audience.strip().lower()
    if audience not in {"parents", "students", "all"}:
        raise ValueError("Audience must be parents, students, or all.")
    title = title.strip()
    body = body.strip()
    if not title or not body:
        raise ValueError("Title and body are required.")
    item = {
        "id": _id("bc"),
        "audience": audience,
        "title": title,
        "body": body,
        "teacher": teacher,
        "at": _now(),
    }

    def _mut(state: dict[str, Any]) -> None:
        state.setdefault("broadcasts", []).append(item)
        state["broadcasts"] = state["broadcasts"][-80:]

    store.update(_mut)
    store.audit("broadcast", {"audience": audience, "id": item["id"]})
    return item


def assign_task(
    *,
    roll: str,
    title: str,
    body: str,
    teacher: str,
    due: str | None = None,
    question_id: str | None = None,
    paper_id: str | None = None,
) -> dict[str, Any]:
    roll = roll.strip()
    title = title.strip()
    body = body.strip()
    if not title or not body:
        raise ValueError("Task title and body are required.")
    if roll not in {"*", "all"}:
        _require_roll(roll)
    item = {
        "id": _id("task"),
        "roll": None if roll in {"*", "all"} else roll,
        "title": title,
        "body": body,
        "due": due or None,
        "status": "open",
        "question_id": question_id,
        "paper_id": paper_id or "midterm",
        "teacher": teacher,
        "at": _now(),
    }

    def _mut(state: dict[str, Any]) -> None:
        state.setdefault("tasks", []).append(item)
        state["tasks"] = state["tasks"][-120:]

    store.update(_mut)
    store.audit("task", {"roll": item["roll"], "id": item["id"]})
    return item


def complete_task(task_id: str, roll: str | None = None) -> dict[str, Any]:
    found: dict[str, Any] = {}

    def _mut(state: dict[str, Any]) -> None:
        for task in state.get("tasks") or []:
            if task["id"] != task_id:
                continue
            if roll and task.get("roll") not in {None, roll}:
                raise PermissionError("Not your task.")
            task["status"] = "done"
            task["done_at"] = _now()
            found.update(task)
            return
        raise KeyError("Unknown task")

    store.update(_mut)
    return found


def schedule_test(*, title: str, date: str, syllabus: str, teacher: str) -> dict[str, Any]:
    title = title.strip()
    date = date.strip()
    syllabus = syllabus.strip()
    if not title or not date or not syllabus:
        raise ValueError("Title, date, and syllabus are required.")
    item = {
        "id": _id("cal"),
        "title": title,
        "date": date,
        "syllabus": syllabus,
        "teacher": teacher,
        "at": _now(),
    }

    def _mut(state: dict[str, Any]) -> None:
        state.setdefault("calendar", []).append(item)

    store.update(_mut)
    store.audit("calendar", {"id": item["id"], "date": date})
    return item


def add_bonus(*, paper_id: str, roll: str, question_id: str, extra: float, teacher: str) -> dict[str, Any]:
    extra = float(extra)
    if extra <= 0:
        raise ValueError("Bonus must be a positive number.")
    applied: dict[str, Any] = {}

    def _mut(state: dict[str, Any]) -> None:
        paper = analyser.resolve_paper(state, paper_id)
        if not paper:
            raise KeyError("Unknown paper")
        row = (state["rows"].get(paper["id"]) or {}).get(roll)
        if not row:
            raise KeyError("Unknown roll")
        cell = row["cells"].get(question_id)
        if cell is None:
            raise ValueError("Cannot add bonus to an empty cell. We do not invent marks.")
        question = next((q for q in paper["questions"] if q["id"] == question_id), None)
        if not question:
            raise KeyError("Unknown question")
        cap = float(question["max_marks"])
        awarded = min(extra, cap - float(cell))
        if awarded <= 0:
            raise ValueError("That cell is already at maximum marks.")
        row["cells"][question_id] = float(cell) + awarded
        bonus = row.setdefault("bonus", {})
        bonus[question_id] = float(bonus.get(question_id) or 0) + awarded
        applied.update(
            {
                "roll": roll,
                "question_id": question_id,
                "from": cell,
                "to": row["cells"][question_id],
                "awarded": awarded,
            }
        )
        state.setdefault("interventions", []).append(
            {
                "id": _id("int"),
                "kind": "bonus",
                "paper_id": paper["id"],
                "roll": roll,
                "question_id": question_id,
                "awarded": awarded,
                "teacher": teacher,
                "at": _now(),
            }
        )

    store.update(_mut)
    store.audit("bonus", applied)
    return applied


def address_issue(
    *,
    paper_id: str,
    roll: str,
    question_id: str,
    teacher: str,
    note: str = "",
) -> dict[str, Any]:
    state = store.load()
    paper = analyser.resolve_paper(state, paper_id)
    if not paper:
        raise KeyError("Unknown paper")
    question = next((q for q in paper["questions"] if q["id"] == question_id), None)
    if not question:
        raise KeyError("Unknown question")
    chapter = question.get("chapter") or "this chapter"
    number = question.get("number")
    note = note.strip() or (
        f"Address Q{number} ({chapter}): practise the same pattern before the term exam. "
        "Do not skip working."
    )
    item = {
        "id": _id("int"),
        "kind": "address",
        "paper_id": paper["id"],
        "roll": roll,
        "question_id": question_id,
        "chapter": chapter,
        "note": note,
        "teacher": teacher,
        "at": _now(),
    }

    def _mut(s: dict[str, Any]) -> None:
        s.setdefault("interventions", []).append(item)
        row = (s["rows"].get(paper["id"]) or {}).get(roll)
        if row is not None:
            flagged = row.setdefault("addressed", [])
            if question_id not in flagged:
                flagged.append(question_id)

    store.update(_mut)
    task = assign_task(
        roll=roll,
        title=f"Address Q{number} · {chapter}",
        body=note,
        teacher=teacher,
        question_id=question_id,
        paper_id=paper["id"],
    )
    store.audit("address", {"roll": roll, "question_id": question_id})
    return {"intervention": item, "task": task}


def _require_roll(roll: str) -> None:
    state = store.load()
    for rows in (state.get("rows") or {}).values():
        if roll in rows:
            return
    raise KeyError(f"Unknown roll {roll}")
