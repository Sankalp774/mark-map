"""Briefs are filled from analyser facts. Incomplete rows stay blocked."""

from __future__ import annotations

from typing import Any

from . import analyser

FAMILY_BANNED = (
    "ptm",
    "talking point",
    "tell the parent",
    "between you and me",
    "staff aside",
    "don't mention",
    "do not mention",
    "raise it in the meeting",
)


def write_briefs(analysis: dict[str, Any], year: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if not analysis.get("complete"):
        missing = ", ".join(q.upper() for q in analysis.get("missing") or [])
        reason = (
            f"Brief blocked — {missing or 'one or more cells'} empty. "
            "Fill the marksheet. We do not invent marks."
        )
        return {
            "blocked": True,
            "reason": reason,
            "teacher": None,
            "family": None,
        }

    teacher = _teacher_brief(analysis, year or [])
    family = _family_brief(analysis, year or [])
    teacher = _scrub(teacher, family=False)
    family, leak = _family_or_block(family)
    if leak:
        return {
            "blocked": True,
            "reason": "Family brief blocked — staff wording leaked. We do not silently delete it.",
            "teacher": teacher,
            "family": None,
        }
    return {
        "blocked": False,
        "reason": None,
        "teacher": teacher,
        "family": family,
    }


def _teacher_brief(a: dict[str, Any], year: list[dict[str, Any]]) -> str:
    weak = ", ".join(a["weak"]) or "none"
    strong = ", ".join(a["strong"]) or "none"
    top = a["losses"][:3]
    loss_txt = (
        "; ".join(
            f"Q{item['number']} {item['chapter']} {int(item['got']) if item['got'] == int(item['got']) else item['got']}/{int(item['max'])} (−{int(item['lost']) if item['lost'] == int(item['lost']) else item['lost']})"
            for item in top
        )
        or "none"
    )
    year_txt = _year_clause(a, year, staff=True)
    return (
        f"PTM talking points — {a['name']}, roll {a['roll']}, {a['title']}, "
        f"{_score(a['got'])}/{_score(a['max'])} ({a['percent']}%).\n\n"
        f"Lead with: {weak} is the leak. Biggest mark losses: {loss_txt}.\n\n"
        f"Keep: {strong}.\n\n"
        f"{year_txt}\n\n"
        "Do not invent a missing mark. Stay on chapters and marks. "
        "Ask for targeted practice on the weak chapter before term."
    )


def _family_brief(a: dict[str, Any], year: list[dict[str, Any]]) -> str:
    weak = ", ".join(a["weak"]) or "no chapter below the weak line"
    strong = ", ".join(a["strong"]) or "no chapter above the strong line yet"
    top = a["losses"][:2]
    if top:
        loss_txt = " Most marks lost on " + " and ".join(
            f"Q{item['number']} in {item['chapter']} ({_score(item['got'])}/{_score(item['max'])})"
            for item in top
        ) + "."
    else:
        loss_txt = ""
    year_txt = _year_clause(a, year, staff=False)
    return (
        f"{a['name']} scored {_score(a['got'])}/{_score(a['max'])} ({a['percent']}%) "
        f"on {a['title']} Mathematics.\n\n"
        f"Strongest chapters: {strong}.\n"
        f"Needs work: {weak}.{loss_txt}\n\n"
        f"{year_txt}"
    ).strip()


def _year_clause(a: dict[str, Any], year: list[dict[str, Any]], staff: bool) -> str:
    complete = [p for p in year if p.get("complete") and p.get("percent") is not None]
    if len(complete) < 2:
        return "Only one complete paper on the year line so far." if staff else "This is the first complete paper on file this year."
    prev = complete[-2]
    now = a["percent"]
    delta = round(now - prev["percent"], 1)
    if delta > 0:
        drift = f"up {delta} points from {prev['title']} ({prev['percent']}%)"
    elif delta < 0:
        drift = f"down {abs(delta)} points from {prev['title']} ({prev['percent']}%)"
    else:
        drift = f"level with {prev['title']} ({prev['percent']}%)"
    if staff:
        return f"Year line: {drift}. Same weak chapters to watch: {', '.join(a['weak']) or 'none'}."
    return f"Compared with {prev['title']}, this paper is {drift}."


def _score(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return str(value)


def _scrub(text: str, family: bool) -> str:
    if analyser.contains_forbidden(text):
        raise ValueError("Brief attempted a personality or mental-health claim.")
    return text.strip()


def _family_or_block(text: str) -> tuple[str | None, list[str]]:
    if analyser.contains_forbidden(text):
        raise ValueError("Brief attempted a personality or mental-health claim.")
    lowered = text.lower()
    hits = [word for word in FAMILY_BANNED if word in lowered]
    if hits:
        return None, hits
    return text.strip(), []
