# Mark Map architecture

```
Browser (teacher / student / parent)
        │
        ▼
   FastAPI  (auth cookie, three roles)
        │
        ├── Deterministic core (owns state and numbers)
        │     analyser.py  map_paper / parse_marks_csv / analyse_row / class_hotspots
        │     briefs.py    teacher vs family; blocked if any cell empty
        │     desk.py      incomplete scripts + PTM window
        │     data/markmap.json
        │
        └── Strands desk agent  (always — scripted, LM Studio / Ollama, or Bedrock)
              Agent(...) calls @tools:
                list_incomplete_rows → class_hotspots
                → write_student_briefs → run_desk_nags
              scripted-desk  or  local OpenAI-compatible LLM  or  Amazon Bedrock
              (Bedrock invoke is currently unauthorized by AWS on this account)
```

**Rule:** a desk run happens only because the agent called tools. Python owns marks, completeness, and “do not publish.” The model does not recap a cycle Python already finished.

Diagram: [architecture.svg](architecture.svg).

Cron: `POST /api/desk/sweep` with `X-Markmap-Secret`. Optional later: AgentCore `{ "action": "sweep" }` on the same tools — after the local loop, not instead of it.
