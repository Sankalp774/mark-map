# Mark Map — target architecture

This is the **intended production shape** for the Professional Agents submission: a Strands desk on **Amazon Bedrock**, with Python as the system of record. The laptop **scripted** / LM Studio brains are stand-ins for the same loop, not a different product.

Diagram: [architecture.svg](architecture.svg).

## Invariants

- Empty cell ≠ 0. Briefs stay `blocked` until every cell in the row has a recorded mark.
- The model does not write marks. The teacher `PATCH`es a yellow cell.
- `family_brief` is a different template from `teacher_brief`. Parent/student doors never receive PTM talking points.
- Eval gates: `invented_marks = 0`, `leaked_teacher_briefs = 0`.
- A desk run **happened** only if Strands called tools. Python does not pre-run the cycle and then ask the model to narrate it.

## Layers

| Layer | What | AWS / code |
|---|---|---|
| L1 Principals | Teacher, student, parent | Cookie session, role filter |
| L2 Edge | Always-on HTTPS + scheduled sweep | **App Runner** container; **EventBridge** → `POST /api/desk/sweep` |
| L3 FastAPI | Human writes vs agent writes vs reads | `markmap/main.py` |
| L4 Loop vs SoR | Strands `Agent` vs analyser/briefs/desk/store | `agents.py` + Python modules |
| L5 Hardening | Tool cancel + IAM | `PolicyHook` + instance role → Bedrock Converse |

## Agentic loop (Strands)

```
BedrockModel.converse
    → tool_use list_incomplete_rows | class_hotspots
      | write_student_briefs | run_desk_nags
    → tool_result (Python)
    → model
    until stop
```

`PolicyHook` on `BeforeToolCallEvent` cancels `write_mark`, `unlock_brief`, `set_question_chapter` **before** the function body runs.

Target model: `us.anthropic.claude-sonnet-4-6` (Converse, `us-west-2`). Fallback on-demand: `amazon.nova-lite-v1:0`. No Bedrock long-term API keys; App Runner **instance role** calls `bedrock:InvokeModel` on foundation-model and inference-profile ARNs.

Optional later, same tools: AgentCore Runtime `POST /invocations` `{ "action": "sweep" }`. That is a host for the loop, not a second agent.

## Picture reports

OCR is **Tesseract + Python**, not the foundation model. The agent never “sees” the scan as pixels for grading.

## Implementation vs this drawing

The code already implements L1, L3, L4 (tools + hook + kernel) and the sweep route. L2 App Runner and live Bedrock invoke are the remaining AWS cutover: account `authorizationStatus` must be `AUTHORIZED` before health is `"backend":"bedrock"`. Until then the **same** Strands tools run as `scripted` (or LM Studio) so the desk is demoable without fabricating a Bedrock trace.
