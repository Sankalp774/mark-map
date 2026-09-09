"""Live class operations: broadcasts, tasks, calendar, bonus, address-issue."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from . import analyser, config, store


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def _in_class(item: dict[str, Any], class_id: str) -> bool:
    return (item.get("class_id") or config.DEFAULT_CLASS_ID) == class_id


def snapshot(user: dict[str, Any] | None = None, class_id: str | None = None) -> dict[str, Any]:
    state = store.load()
    roll = (user or {}).get("roll")
    role = (user or {}).get("role")
    class_id = class_id or (user or {}).get("class_id") or config.DEFAULT_CLASS_ID
    tasks = [t for t in (state.get("tasks") or []) if _in_class(t, class_id)]
    broadcasts = [b for b in (state.get("broadcasts") or []) if _in_class(b, class_id)]
    calendar = [c for c in (state.get("calendar") or []) if _in_class(c, class_id)]
    threads = [t for t in (state.get("threads") or []) if _in_class(t, class_id)]
    if role in {"student", "parent"} and roll:
        tasks = [t for t in tasks if t.get("roll") in {None, roll, "*"}]
        audiences = {"students", "all", "parents"} if role == "parent" else {"students", "all"}
        broadcasts = [b for b in broadcasts if b.get("audience") in audiences or b.get("roll") == roll]
        threads = [t for t in threads if t.get("roll") == roll]
    unread = _unread(role, roll, broadcasts, threads)
    return {
        "class_id": class_id,
        "tasks": sorted(tasks, key=lambda t: t.get("at") or "", reverse=True)[:40],
        "broadcasts": sorted(broadcasts, key=lambda b: b.get("at") or "", reverse=True)[:40],
        "calendar": sorted(calendar, key=lambda c: c.get("date") or ""),
        "threads": sorted(threads, key=lambda t: t.get("updated_at") or t.get("at") or "", reverse=True)[:40],
        "unread": unread,
        "interventions": [
            i
            for i in (state.get("interventions") or [])
            if _in_class(i, class_id) and (role == "teacher" or i.get("roll") == roll)
        ][-40:],
        "queries": [
            q
            for q in (state.get("queries") or [])
            if (role == "teacher" or q.get("roll") == roll)
        ][-20:],
    }


def _unread(role: str | None, roll: str | None, broadcasts: list, threads: list) -> int:
    n = 0
    if role in {"student", "parent"} and roll:
        for b in broadcasts:
            acks = b.get("acks") or []
            if not any(a.get("roll") == roll and a.get("role") == role for a in acks):
                n += 1
        for t in threads:
            msgs = t.get("messages") or []
            if msgs and msgs[-1].get("role") == "teacher":
                n += 1
    elif role == "teacher":
        for b in broadcasts:
            n += len(b.get("replies") or [])
        for t in threads:
            msgs = t.get("messages") or []
            if msgs and msgs[-1].get("role") != "teacher":
                n += 1
    return n


def seed_defaults() -> None:
    def _mut(state: dict[str, Any]) -> None:
        from . import seed as seedmod

        seedmod.ensure_classes(state)
        if not any(_in_class(c, "10-B") for c in (state.get("calendar") or [])):
            state.setdefault("calendar", []).append(
                {
                    "id": "cal-term-exam",
                    "class_id": "10-B",
                    "title": "Term examination",
                    "date": "2026-09-28",
                    "syllabus": (
                        "Linear Equations (word problems, hostel-charges type), "
                        "Triangles (similarity), Statistics (mean and median)."
                    ),
                    "at": _now(),
                }
            )

    store.update(_mut)


def broadcast(*, audience: str, title: str, body: str, teacher: str, class_id: str = "10-B") -> dict[str, Any]:
    audience = audience.strip().lower()
    if audience not in {"parents", "students", "all"}:
        raise ValueError("Audience must be parents, students, or all.")
    title = title.strip()
    body = body.strip()
    if not title or not body:
        raise ValueError("Title and body are required.")
    item = {
        "id": _id("bc"),
        "class_id": class_id,
        "audience": audience,
        "title": title,
        "body": body,
        "teacher": teacher,
        "replies": [],
        "acks": [],
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
    class_id: str = "10-B",
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
        "class_id": class_id,
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


def schedule_test(*, title: str, date: str, syllabus: str, teacher: str, class_id: str = "10-B") -> dict[str, Any]:
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
        "class_id": class_id,
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
        class_id=paper.get("class_id") or config.DEFAULT_CLASS_ID,
    )
    store.audit("address", {"roll": roll, "question_id": question_id})
    return {"intervention": item, "task": task}


def _require_roll(roll: str) -> None:
    state = store.load()
    for rows in (state.get("rows") or {}).values():
        if roll in rows:
            return
    raise KeyError(f"Unknown roll {roll}")


def reply_broadcast(*, broadcast_id: str, user: dict[str, Any], body: str) -> dict[str, Any]:
    body = body.strip()
    if not body:
        raise ValueError("Reply cannot be empty.")
    reply = {
        "id": _id("rp"),
        "role": user["role"],
        "name": user["name"],
        "roll": user.get("roll"),
        "body": body,
        "at": _now(),
    }
    found: dict[str, Any] = {}

    def _mut(state: dict[str, Any]) -> None:
        for item in state.get("broadcasts") or []:
            if item["id"] != broadcast_id:
                continue
            item.setdefault("replies", []).append(reply)
            found.update(item)
            return
        raise KeyError("Unknown request")

    store.update(_mut)
    store.audit("reply", {"broadcast_id": broadcast_id, "role": user["role"]})
    return reply


def ack_broadcast(*, broadcast_id: str, user: dict[str, Any]) -> dict[str, Any]:
    ack = {
        "role": user["role"],
        "name": user["name"],
        "roll": user.get("roll"),
        "at": _now(),
    }

    def _mut(state: dict[str, Any]) -> None:
        for item in state.get("broadcasts") or []:
            if item["id"] != broadcast_id:
                continue
            acks = item.setdefault("acks", [])
            if any(a.get("roll") == ack["roll"] and a.get("role") == ack["role"] for a in acks):
                return
            acks.append(ack)
            return
        raise KeyError("Unknown request")

    store.update(_mut)
    return ack


def thread_message(*, class_id: str, roll: str, user: dict[str, Any], body: str) -> dict[str, Any]:
    body = body.strip()
    if not body:
        raise ValueError("Message cannot be empty.")
    if user["role"] != "teacher" and user.get("roll") != roll:
        raise PermissionError("Not your thread.")
    msg = {
        "id": _id("msg"),
        "role": user["role"],
        "name": user["name"],
        "roll": user.get("roll"),
        "body": body,
        "at": _now(),
    }
    thread_out: dict[str, Any] = {}

    def _mut(state: dict[str, Any]) -> None:
        threads = state.setdefault("threads", [])
        thread = next(
            (t for t in threads if t.get("class_id") == class_id and t.get("roll") == roll),
            None,
        )
        if not thread:
            thread = {
                "id": _id("th"),
                "class_id": class_id,
                "roll": roll,
                "messages": [],
                "at": _now(),
            }
            threads.append(thread)
        thread["messages"].append(msg)
        thread["updated_at"] = _now()
        thread_out.update(thread)

    store.update(_mut)
    store.audit("thread", {"roll": roll, "class_id": class_id})
    return {"thread": thread_out, "message": msg}
