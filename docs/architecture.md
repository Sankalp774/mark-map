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
        └── Strands desk orchestrator  (when Bedrock is configured)
              agents-as-tools:
                ingest clerk → paper mapper → score clerk
                analyser → brief writer → run_desk_nags
              Amazon Bedrock  Claude Sonnet
```

**Rule:** the model classifies, tags, drafts, and nags. Python owns marks, completeness, and “do not publish.”

Optional later: AgentCore Runtime around the same FastAPI process. Not required to score Technical Implementation if the Strands loop above is live.
