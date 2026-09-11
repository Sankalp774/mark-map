"""Explicit action boundary. Python enforces it; the model only narrates."""

from __future__ import annotations

from typing import Any

CAN = (
    "inspect_marks",
    "inspect_chapters",
    "identify_incomplete",
    "create_teacher_tasks",
    "draft_family_briefs",
    "prepare_parent_requests",
    "recommend_interventions",
    "read_calendar",
    "summarize_trends",
    "narrate_desk_cycle",
)

CANNOT = (
    "alter_marks",
    "invent_missing_marks",
    "change_chapter_without_approval",
    "send_teacher_notes_to_parents",
    "modify_historical_results",
    "unlock_incomplete_briefs",
    "assign_grades",
)

REASONS = {
    "alter_marks": "Marks are owned by the CSV and the teacher. Agents do not write cells.",
    "invent_missing_marks": "Empty / NA / dash stays missing. Zero is not a guess.",
    "change_chapter_without_approval": "Guessed tags stay needs_review until the teacher confirms them on the map.",
    "send_teacher_notes_to_parents": "Family pane never receives teacher_brief or staff asides.",
    "modify_historical_results": "Term 1 numbers stay as ingested. Later papers do not rewrite them.",
    "unlock_incomplete_briefs": "A brief stays blocked while any cell on that row is empty.",
    "assign_grades": "The desk reports percents. It does not assign grades.",
}


def allowed(action: str) -> bool:
    return action in CAN and action not in CANNOT


def refuse(action: str, extra: str = "") -> dict[str, Any]:
    reason = REASONS.get(action, "This action is outside the desk permission boundary.")
    if extra:
        reason = f"{reason} {extra}".strip()
    return {
        "allowed": False,
        "action": action,
        "reason": reason,
    }


def public() -> dict[str, Any]:
    return {
        "can": list(CAN),
        "cannot": list(CANNOT),
        "rule": "Python establishes reality. Agents operate within it.",
    }
