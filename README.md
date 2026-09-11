# Mark Map

**Track: Professional Agents — Agents for Humans (AWS / Strands)**

Paper + marksheet in. Chapter map + year-round pane out. PTM briefs stay blocked until every mark cell is filled.

> We analyse the page, we do not grade unseen scripts.

Named desk: **Kavita Sharma**, Class 10-B Mathematics, Greenfield Public School. Named student: **Ravi Mehta**.

## What it does

A teacher pastes a question paper and a marks CSV, or drops a **screenshot of a student report**. Mark Map maps each question to a chapter (`[Chapter]` on the paper wins; otherwise a keyword guess flagged `needs_review`). Term 1 and Midterm stay in **separate sections**. Analysis includes an Obsidian-style local graph (`[[Linear Equations]]` ↔ questions). It attaches scores, refuses to invent empty cells, and writes two briefs from the same facts:

- **Teacher brief** — PTM talking points
- **Family brief** — same numbers, calmer, no staff asides

Student and parent logins see the family pane only. A **Run desk** job nags when scripts are incomplete or PTM is close — it runs when nobody is chatting.

## Demo (the video path)

Three doors, password `demo` for all:

| Door | Email |
|---|---|
| Teacher | `teacher@markmap.demo` |
| Student | `ravi@markmap.demo` |
| Parent | `parent.ravi@markmap.demo` |

1. Teacher → **Load demo Term 1 + Midterm**
2. Tabs: Term 1 | Midterm. Question map on Midterm: Linear Equations, Polynomials, Triangles, Trigonometry, Statistics (Q10 needs review)
3. Open **Ravi**: weak Linear Equations, leak on Q9. Local graph shows `[[Linear Equations]]` ← Q3, Q4, Q9
4. Class hotspot **Q9**
5. Log in as Ravi — Term 1 section and Midterm section, family brief, no PTM phrasing
6. Log in as parent — same two sections + year line
7. **Ingest → Read sample screenshot** — OCR preview of Term 1 + Midterm, image on the page
8. **Local graph** — click Q9 → Address Q9 (task to student) or +1/+2 bonus (never fills an empty cell)
9. **Requests** — all parents, all students, or a personal task to one roll
10. **Calendar** — next test date + syllabus, visible on student/parent panes
11. Student/parent → **Ask the desk** FAQ chips (Q9, next test, tasks, brief)

## Run locally

Python 3.10+. Tesseract is optional but enables live screenshot OCR (`brew install tesseract`).

```bash
cd mark-map
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m markmap
```

Open http://127.0.0.1:8080

```bash
pytest
```

## Strands + Bedrock

The demo path above is **deterministic** (`analyser.py` owns numbers). That is intentional: marks must not drift.

When AWS credentials and Bedrock model access are present, **Run desk** creates a real Strands orchestrator. Specialists are agents-as-tools wrapping the same Python functions:

| Agent | Tools |
|---|---|
| Ingest clerk | `load_demo_midterm_2`, `ingest_paper_and_marks` |
| Paper mapper | `map_paper` / `set_question_chapter` |
| Score clerk | `list_incomplete_rows` |
| Analyser | `analyse_student`, `class_hotspots` |
| Brief writer | `write_student_briefs` |
| Desk runner | `run_desk_nags` + the specialists |

```bash
cp .env.example .env
# set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION=us-west-2
# enable Claude Sonnet on Bedrock (inference profile us.anthropic.claude-sonnet-4-6)
```

`GET /api/health` reports `strands_enabled` and the agent permission boundary (`can` / `cannot`). Guessed chapter tags carry a confidence score and stay `needs_review` until the teacher confirms them. Run desk writes a visible trace (checked completeness → blocked briefs → teacher task) so the loop is inspectable.

Do **not** file the $50 credits form twice. The code is one-time; redeem it on the Paid plan in Billing → Credits.

## Architecture

See [docs/architecture.md](docs/architecture.md).

Browser → FastAPI → analyser.py + JSON store. Strands desk agent (Bedrock) delegates; it never writes a mark.

## Guardrails

- Empty / `NA` / `-` in the CSV is **missing**, not zero
- No brief until the row is complete
- No personality, “potential”, or mental-health claims
- Family pane never receives `teacher_brief`

## What this is not

- Auto-grading handwritten answers
- A school MIS
- A chatbot you babysit

## License

MIT. Sample papers and CSVs are in `data/samples/`.
