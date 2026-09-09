"""Strands multi-agent desk. Specialists wrap analyser tools. Desk delegates."""

from __future__ import annotations

from typing import Any

from . import config, store, tools

DESK_PROMPT = """
You are the Mark Map desk runner for Kavita Sharma, Class 10-B Mathematics.

You do not invent marks. You do not publish a brief for an incomplete row.
You do not talk about personality, potential, or mental health.

Specialists (call them, do not recompute numbers yourself):
- ingest_clerk — load demo paper / ingest text+CSV
- paper_mapper — question-to-chapter map; teacher corrections
- score_clerk — incomplete rows
- analyser — one student, class hotspots
- brief_writer — teacher vs family brief (will refuse if a cell is empty)

When asked to run the desk:
1. Call score_clerk for incomplete rolls.
2. Call analyser for class hotspots.
3. Call run_desk_nags.
4. Summarise alerts in one short paragraph for the teacher.
""".strip()

INGEST_PROMPT = "You ingest papers, CSVs, and student-report screenshots. Call load_demo_midterm_2, ingest_paper_and_marks, or ingest_screenshot_report. Split Term 1 and Midterm. Never invent rows."
MAPPER_PROMPT = "You map questions to chapters. [Chapter] in the paper wins. Flag needs_review. Teacher corrections go through set_question_chapter."
SCORE_PROMPT = "You attach marks to questions. Empty cells stay empty. List incomplete rolls. Never fill a blank with zero or a guess."
ANALYSER_PROMPT = "You report marks × chapter × time from analyse_student and class_hotspots. No psychology."
BRIEF_PROMPT = "You write two briefs from write_student_briefs. If blocked, say so. Family brief has no PTM phrasing."


def _model():
    from strands.models import BedrockModel

    return BedrockModel(
        model_id=config.BEDROCK_MODEL_ID,
        region_name=config.AWS_REGION,
        temperature=0.2,
        streaming=False,
    )


def _agent(system_prompt: str, agent_tools: list):
    from strands import Agent

    return Agent(
        model=_model(),
        system_prompt=system_prompt,
        tools=agent_tools,
        callback_handler=None,
    )


def _as_tool(agent, name: str, description: str):
    if hasattr(agent, "as_tool"):
        return agent.as_tool(name=name, description=description)
    from strands import tool as strands_tool

    @strands_tool(name=name, description=description)
    def _run(query: str) -> str:
        """Delegate to a specialist agent."""
        return str(agent(query))

    return _run


def build_desk():
    ingest = _agent(
        INGEST_PROMPT,
        [tools.load_demo_midterm_2, tools.ingest_paper_and_marks, tools.ingest_screenshot_report],
    )
    mapper = _agent(MAPPER_PROMPT, [tools.map_current_paper, tools.set_question_chapter])
    score = _agent(SCORE_PROMPT, [tools.list_incomplete_rows, tools.blank_ravi_q9])
    analyse = _agent(ANALYSER_PROMPT, [tools.analyse_student, tools.class_hotspots])
    brief = _agent(BRIEF_PROMPT, [tools.write_student_briefs])
    desk = _agent(
        DESK_PROMPT,
        [
            _as_tool(ingest, "ingest_clerk", "Load demo Midterm 2 or ingest a paper + marks CSV."),
            _as_tool(mapper, "paper_mapper", "Show or correct the question-to-chapter map."),
            _as_tool(score, "score_clerk", "List incomplete mark rows. Clear a cell for the guardrail demo."),
            _as_tool(analyse, "analyser", "Per-student chapter analysis and class hotspots."),
            _as_tool(brief, "brief_writer", "Teacher PTM brief and family brief. Blocked if marks are missing."),
            tools.run_desk_nags,
        ],
    )
    return desk


def run_desk_agent(prompt: str | None = None) -> dict[str, Any]:
    if not config.strands_enabled():
        from . import desk

        result = desk.run_desk()
        result["note"] = (
            "Deterministic desk. Add AWS credentials and Bedrock model access "
            "to run the Strands orchestrator."
        )
        return result

    message = prompt or (
        "Run the desk for Midterm 2. Check incomplete scripts, class hotspots, "
        "and PTM readiness. Use your specialists. Do not invent marks."
    )
    desk_agent = build_desk()
    response = desk_agent(message)
    text = str(response)
    store.agent_log("desk_orchestrator", text[:2000], {"mode": "strands"})
    from . import desk

    alerts = desk.compute_alerts()
    store.update(lambda s: s.__setitem__("alerts", alerts))
    return {
        "alerts": alerts,
        "strands": True,
        "mode": "strands",
        "summary": text,
        "model": config.BEDROCK_MODEL_ID,
    }


def run_prompt(prompt: str) -> dict[str, Any]:
    return run_desk_agent(prompt)
