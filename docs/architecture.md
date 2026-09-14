# Mark Map architecture

Target shape for the Professional Agents track. Diagram: [architecture.svg](architecture.svg).

Three views, one product:

1. **Request architecture** — Browser → App Runner → FastAPI. Human writes (`PATCH` cell) and agent writes (`POST /desk/run`, EventBridge `/sweep`) meet in the JSON store. Parent/student reads never include `teacher_brief`.
2. **Multi-agent desk** — **Desk Runner** is the Strands orchestrator on Bedrock. Five specialists do the work: Ingest, Mapper, Score Clerk, Analyser, Brief Writer. A **policy gate** cancels `write_mark`, `unlock_brief`, `set_question_chapter` before they run.
3. **Agent loop** — Bedrock Converse → `tool_use` → `BeforeToolCall` hook → Python system of record → `tool_result` → model, until stop. Canonical tools: `list_incomplete_rows` → `class_hotspots` → `write_student_briefs` → `run_desk_nags`.

Invariant: empty ≠ 0. The teacher still fills the yellow cell. A desk run exists only because tools ran.

The published demo uses this same loop with a scripted model until AWS authorizes Bedrock invoke.
