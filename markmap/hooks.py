"""Cancel forbidden tools before they run."""

from __future__ import annotations

from . import policy, store

TOOL_ACTIONS = {
    "write_mark": "alter_marks",
    "unlock_brief": "unlock_incomplete_briefs",
    "set_question_chapter": "change_chapter_without_approval",
}


class PolicyHook:
    def register_hooks(self, registry) -> None:
        from strands.hooks.events import BeforeToolCallEvent

        registry.add_callback(BeforeToolCallEvent, self.before_tool)

    def before_tool(self, event) -> None:
        name = (event.tool_use or {}).get("name")
        action = TOOL_ACTIONS.get(name or "")
        if not action:
            return
        reason = policy.refuse(action)["reason"]
        event.cancel_tool = reason
        store.agent_log("refuse", f"{name}: {reason}", {"tool": name, "action": action})
