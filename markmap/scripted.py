"""Local Strands model: the desk loop runs by emitting tool calls, not by recapping Python."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import AsyncGenerator, AsyncIterable
from typing import Any

from strands.models.model import Model
from strands.types.content import Messages, SystemContentBlock
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolChoice, ToolSpec

from . import config


class ScriptedDeskModel(Model):
    """Deterministic stand-in for Bedrock. Same tool sequence the live desk uses."""

    def __init__(self) -> None:
        self._config: dict[str, Any] = {
            "model_id": "scripted-desk",
            "context_window_limit": 32000,
        }

    def update_config(self, **model_config: Any) -> None:
        self._config.update(model_config)

    def get_config(self) -> dict[str, Any]:
        return self._config

    async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
        if False:  # pragma: no cover
            yield {}
        raise NotImplementedError("scripted desk model has no structured output")

    def stream(
        self,
        messages: Messages,
        tool_specs: list[ToolSpec] | None = None,
        system_prompt: str | None = None,
        *,
        tool_choice: ToolChoice | None = None,
        system_prompt_content: list[SystemContentBlock] | None = None,
        invocation_state: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> AsyncIterable[StreamEvent]:
        return self._stream(messages)

    async def _stream(self, messages: Messages) -> AsyncGenerator[StreamEvent, None]:
        called = _tool_names(messages)
        class_id = _class_id(messages)
        paper_id = "midterm" if class_id == config.DEFAULT_CLASS_ID else f"{class_id}:midterm"
        cheat = _cheat_kind(_user_blob(messages))
        if cheat == "fill" and "write_mark" not in called:
            async for event in _tools([("write_mark", {"roll": "17", "question_id": "q9", "value": 8})]):
                yield event
            return
        if cheat == "unlock" and "unlock_brief" not in called:
            async for event in _tools([("unlock_brief", {"roll": "17"})]):
                yield event
            return
        if cheat:
            async for event in _text(
                "Refused. Agents cannot invent a mark or unlock a blocked brief. The teacher fills the cell."
            ):
                yield event
            return
        if "list_incomplete_rows" not in called:
            async for event in _tools(
                [
                    ("list_incomplete_rows", {"paper_id": paper_id}),
                    ("class_hotspots", {"paper_id": paper_id}),
                ]
            ):
                yield event
            return
        if "run_desk_nags" not in called:
            async for event in _tools(
                [
                    ("write_student_briefs", {"roll": "17", "paper_id": paper_id}),
                    ("run_desk_nags", {"class_id": class_id}),
                ]
            ):
                yield event
            return
        async for event in _text(_closing_line(messages)):
            yield event


def _tool_names(messages: Messages) -> set[str]:
    names: set[str] = set()
    for message in messages:
        if message.get("role") != "assistant":
            continue
        for block in message.get("content") or []:
            use = block.get("toolUse")
            if use and use.get("name"):
                names.add(use["name"])
    return names


def _user_blob(messages: Messages) -> str:
    return " ".join(
        block.get("text") or ""
        for message in messages
        if message.get("role") == "user"
        for block in message.get("content") or []
        if "text" in block
    ).lower()


def _cheat_kind(blob: str) -> str | None:
    if re.search(r"unlock the brief", blob):
        return "unlock"
    if re.search(r"give ravi|fill q9|write 8 on q9|award \d", blob):
        return "fill"
    return None


def _class_id(messages: Messages) -> str:
    blob = " ".join(
        block.get("text") or ""
        for message in messages
        for block in message.get("content") or []
        if "text" in block
    )
    match = re.search(r"class\s+([0-9][A-Za-z0-9-]*)", blob, re.IGNORECASE)
    return match.group(1) if match else config.DEFAULT_CLASS_ID


def _closing_line(messages: Messages) -> str:
    incomplete_n = None
    blocked = False
    for message in messages:
        for block in message.get("content") or []:
            result = block.get("toolResult")
            if not result:
                continue
            text = " ".join(
                (item.get("text") or json.dumps(item.get("json") or {}, default=str))
                for item in result.get("content") or []
            )
            try:
                payload = json.loads(text) if text.strip().startswith("{") else {}
            except json.JSONDecodeError:
                payload = {}
            if "incomplete" in payload:
                incomplete_n = payload.get("n")
            if payload.get("blocked") is True or payload.get("allowed") is False:
                blocked = True
            if isinstance(payload.get("cycle"), dict):
                summary = payload["cycle"].get("summary") or payload.get("summary")
                if summary:
                    extra = f" Incomplete rows: {incomplete_n}." if incomplete_n is not None else ""
                    gate = " Briefs stay blocked." if blocked or (incomplete_n or 0) > 0 else ""
                    return f"Desk ran through tools.{extra}{gate} {summary}"
    n = incomplete_n if incomplete_n is not None else "?"
    return (
        f"Desk ran through tools. list_incomplete_rows reported {n} incomplete rows. "
        "run_desk_nags applied the observe → plan → act cycle. Marks were not invented."
    )


async def _tools(calls: list[tuple[str, dict[str, Any]]]) -> AsyncGenerator[StreamEvent, None]:
    yield {"messageStart": {"role": "assistant"}}
    for index, (name, args) in enumerate(calls):
        tool_id = f"scripted-{name}-{index}-{uuid.uuid4().hex[:8]}"
        yield {
            "contentBlockStart": {
                "start": {"toolUse": {"toolUseId": tool_id, "name": name}},
            }
        }
        yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(args)}}}}
        yield {"contentBlockStop": {}}
    yield {"messageStop": {"stopReason": "tool_use"}}
    yield _meta()


async def _text(body: str) -> AsyncGenerator[StreamEvent, None]:
    yield {"messageStart": {"role": "assistant"}}
    yield {"contentBlockDelta": {"delta": {"text": body}}}
    yield {"contentBlockStop": {}}
    yield {"messageStop": {"stopReason": "end_turn"}}
    yield _meta()


def _meta() -> StreamEvent:
    return {
        "metadata": {
            "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
            "metrics": {"latencyMs": 1},
        }
    }
