"""One Strands desk agent. Tools do the work; the model only chooses which to call."""

from __future__ import annotations

import os
from typing import Any

from . import config, store, tools
from .hooks import PolicyHook

DESK_PROMPT = """
You are the Mark Map desk runner for Kavita Sharma.

Python owns marks, percents, completeness, and the brief gate. You only call tools.

When asked to run the desk:
1. Call list_incomplete_rows.
2. Call class_hotspots.
3. Call write_student_briefs for roll 17 (it will refuse if a cell is empty — that is the gate).
4. Call run_desk_nags for this class. That is the observe → plan → act cycle (teacher task or class reteach proposal).
5. Then stop. Summarise what the tools returned. Do not invent marks. Do not unlock a blocked brief.

You cannot: alter marks, invent empty cells, confirm a guessed chapter tag, send teacher notes to parents, unlock a blocked brief, or assign a grade. Those tools refuse.
""".strip()

DESK_TOOLS = [
    tools.list_incomplete_rows,
    tools.class_hotspots,
    tools.write_student_briefs,
    tools.run_desk_nags,
    tools.map_current_paper,
    tools.analyse_student,
    tools.write_mark,
    tools.unlock_brief,
    tools.set_question_chapter,
]


def _model():
    backend = config.model_backend()
    if backend == "bedrock":
        from strands.models import BedrockModel

        return BedrockModel(
            model_id=config.BEDROCK_MODEL_ID,
            region_name=config.AWS_REGION,
            temperature=0.2,
            streaming=False,
        )
    if backend == "ollama":
        from strands.models.ollama import OllamaModel

        return OllamaModel(
            host=config.OLLAMA_HOST,
            model_id=config.OLLAMA_MODEL_ID,
            temperature=0.2,
        )
    if backend == "mlx":
        if config.omlx_endpoint_up():
            from strands.models.openai import OpenAIModel

            return OpenAIModel(
                client_args={
                    "api_key": os.getenv("MARKMAP_MLX_API_KEY", "local"),
                    "base_url": config.MLX_BASE_URL,
                },
                model_id=config.MLX_MODEL_ID,
                params={"temperature": 0.2, "max_tokens": 1024},
            )
        from strands.models.ollama import OllamaModel

        return OllamaModel(
            host=config.OLLAMA_HOST,
            model_id=config.OLLAMA_MODEL_ID,
            temperature=0.2,
        )
    from .desk_model import DeskModel

    return DeskModel()


def build_desk():
    from strands import Agent
    from strands.handlers.callback_handler import null_callback_handler

    return Agent(
        model=_model(),
        system_prompt=DESK_PROMPT,
        tools=DESK_TOOLS,
        hooks=[PolicyHook()],
        callback_handler=null_callback_handler,
    )


def run_desk_agent(prompt: str | None = None, class_id: str | None = None) -> dict[str, Any]:
    class_id = class_id or config.DEFAULT_CLASS_ID
    backend = config.model_backend()
    message = prompt or (
        f"Run the desk for class {class_id}. "
        "Call list_incomplete_rows, class_hotspots, write_student_briefs for roll 17, "
        "then run_desk_nags. Do not invent marks. Do not unlock blocked briefs."
    )
    agent = build_desk()
    response = agent(message)
    text = str(response)
    called = _tools_called(agent)
    refused = [
        e
        for e in (store.load().get("agent_log") or [])
        if e.get("kind") == "refuse"
    ][-8:]
    store.agent_log("desk_orchestrator", text[:2000], {"mode": backend, "tools": called})
    cycle = _latest_cycle(class_id)
    last = {
        "at": (cycle or {}).get("at"),
        "observed": ((cycle or {}).get("observe") or {}),
        "did": called,
        "refused": [{"tool": e.get("extra", {}).get("tool"), "text": e.get("text")} for e in refused],
        "waiting": next(
            (s["text"] for s in ((cycle or {}).get("steps") or []) if s.get("phase") == "wait"),
            None,
        ),
        "summary": text,
        "mode": backend,
    }

    def _mut(state: dict[str, Any]) -> None:
        state["last_desk_run"] = last

    store.update(_mut)
    return {
        "alerts": (cycle or {}).get("alerts") or store.load().get("alerts") or [],
        "strands": True,
        "mode": backend,
        "cycle": cycle,
        "summary": text,
        "tools_called": called,
        "refused": last["refused"],
        "last_run": last,
        "model": config.desk_model_id(backend),
    }


def run_prompt(prompt: str) -> dict[str, Any]:
    return run_desk_agent(prompt)


def _tools_called(agent) -> list[str]:
    names: list[str] = []
    for message in getattr(agent, "messages", []) or []:
        if message.get("role") != "assistant":
            continue
        for block in message.get("content") or []:
            use = block.get("toolUse")
            if use and use.get("name"):
                names.append(use["name"])
    return names


def _latest_cycle(class_id: str) -> dict[str, Any] | None:
    cycles = [c for c in (store.load().get("desk_cycles") or []) if c.get("class_id") == class_id]
    return cycles[-1] if cycles else None
