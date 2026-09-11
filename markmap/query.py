"""Student/parent ask-desk. Answers only from marks, calendar, and tasks."""

from __future__ import annotations

from typing import Any

from . import analyser, briefs, store, workspace

FAQS = [
    {
        "id": "q9",
        "label": "Why were marks lost on Q9?",
        "hint": "Hotspot and your score on the hostel-charges question",
    },
    {
        "id": "linear",
        "label": "How do we work on Linear Equations?",
        "hint": "Chapter band + any open task",
    },
    {
        "id": "next-test",
        "label": "When is the next test, and what is the syllabus?",
        "hint": "Teacher calendar",
    },
    {
        "id": "brief",
        "label": "Is the family brief ready?",
        "hint": "Blocked if any cell is empty",
    },
    {
        "id": "tasks",
        "label": "What tasks are open for me?",
        "hint": "Address-Q9 and teacher assignments",
    },
    {
        "id": "hotspot",
        "label": "Was Midterm Q9 hard for the whole class?",
        "hint": "Class mean, not a personal judgement",
    },
    {
        "id": "bonus",
        "label": "Did the teacher add bonus marks?",
        "hint": "Only recorded bonus, never invented",
    },
]


def answer(*, question: str, user: dict[str, Any], faq_id: str | None = None) -> dict[str, Any]:
    question = (question or "").strip()
    faq_id = faq_id or _match_faq(question)
    roll = user.get("roll")
    if not roll:
        raise PermissionError("Only student and parent accounts can ask the desk.")
    snap = workspace.snapshot(user)
    mid = None
    term = None
    try:
        mid = analyser.student_bundle("midterm", roll)
    except KeyError:
        mid = None
    try:
        term = analyser.student_bundle("term-1", roll)
    except KeyError:
        term = None
    text = _compose(faq_id, question, user, snap, mid, term)
    item = {
        "id": f"ask-{len(store.load().get('queries') or []) + 1}",
        "roll": roll,
        "role": user.get("role"),
        "email": user.get("email"),
        "question": question,
        "faq_id": faq_id,
        "answer": text,
        "at": workspace._now(),
    }

    def _mut(state: dict[str, Any]) -> None:
        state.setdefault("queries", []).append(item)
        state["queries"] = state["queries"][-40:]

    store.update(_mut)
    return {"faq_id": faq_id, "answer": text, "faqs": FAQS}


def _match_faq(question: str) -> str | None:
    blob = question.lower()
    if "q9" in blob or "hostel" in blob:
        return "q9"
    if "linear" in blob:
        return "linear"
    if "syllabus" in blob or "next test" in blob or "when is" in blob:
        return "next-test"
    if "brief" in blob or "ptm" in blob:
        return "brief"
    if "task" in blob or "homework" in blob:
        return "tasks"
    if "class" in blob or "hotspot" in blob or "everyone" in blob:
        return "hotspot"
    if "bonus" in blob:
        return "bonus"
    return None


def _compose(faq_id: str | None, question: str, user: dict[str, Any], snap: dict[str, Any], mid, term) -> str:
    name = (mid or term or {}).get("analysis", {}).get("name") or user.get("name")
    if faq_id == "q9" and mid:
        a = mid["analysis"]
        q9 = next((loss for loss in a["losses"] if loss["number"] == 9), None)
        if not a["complete"]:
            return "The Midterm row is incomplete, so we will not discuss Q9 as a finished score. Fill the empty cell first."
        if not q9:
            return f"{name} did not lose marks on Q9 on the Midterm paper we have."
        return (
            f"Midterm Q9 ({q9['chapter']}) scored {_n(q9['got'])}/{_n(q9['max'])}, "
            f"a loss of {_n(q9['lost'])} marks. "
            "It is a pair of linear equations in a hostel-charges word problem. "
            "That is a marks fact, not a comment on ability."
        )
    if faq_id == "linear" and mid:
        a = mid["analysis"]
        band = next((c for c in a["chapters"] if c["name"] == "Linear Equations"), None)
        open_tasks = [t for t in snap["tasks"] if t.get("status") != "done" and "Linear" in (t.get("title") or "")]
        line = (
            f"Linear Equations on Midterm is {band['percent']}% ({band['band']})."
            if band
            else "No Linear Equations chapter is on file yet."
        )
        if open_tasks:
            line += " Open task: " + open_tasks[0]["title"] + "."
        else:
            line += " No address-task is open. The teacher can assign one from the local graph."
        return line
    if faq_id == "next-test":
        cal = snap["calendar"]
        if not cal:
            return "No next test is on the class calendar yet."
        nxt = cal[-1]
        return f"{nxt['title']} is scheduled for {nxt['date']}. Syllabus: {nxt['syllabus']}"
    if faq_id == "brief":
        target = mid or term
        if not target:
            return "No paper is on file, so there is no brief."
        payload = briefs.write_briefs(target["analysis"], target["year"])
        if payload["blocked"]:
            return payload["reason"]
        return "The family brief is ready. The teacher brief is not shown on this pane."
    if faq_id == "tasks":
        open_tasks = [t for t in snap["tasks"] if t.get("status") != "done"]
        if not open_tasks:
            return "No open tasks."
        return "Open tasks: " + "; ".join(t["title"] for t in open_tasks[:5]) + "."
    if faq_id == "hotspot" and mid:
        hot = (mid.get("hotspots") or [None])[0]
        if not hot:
            return "No class hotspot is computed yet."
        return (
            f"Class hotspot is Q{hot['number']} {hot['chapter']} — mean {hot['percent']}% "
            f"across {hot['n']} complete scripts. This is a section leak, not a private remark."
        )
    if faq_id == "bonus" and mid:
        bonus = (mid.get("row") or {}).get("bonus") or {}
        if not bonus:
            return "No bonus has been recorded on this row."
        bits = [f"{qid.upper()} +{_n(val)}" for qid, val in bonus.items()]
        return "Recorded bonus: " + ", ".join(bits) + ". Empty cells were not filled."
    if mid and mid["analysis"].get("complete"):
        a = mid["analysis"]
        return (
            f"{name} Midterm {a['percent']}% ({_n(a['got'])}/{_n(a['max'])}). "
            f"Weak: {', '.join(a['weak']) or 'none'}. "
            "Ask a FAQ chip if you need a specific cell. We do not invent marks."
        )
    if question:
        return (
            "I don't know from this marksheet. "
            "Answers come from marks, calendar, and open tasks only — not a live agent. "
            "Try a FAQ chip: Q9, next test, tasks, or the family brief."
        )
    return "Choose a FAQ chip. Answers are from the marksheet only."


def _n(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value)
