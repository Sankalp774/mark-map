# Mark Map

**Track: Professional Agents — Agents for Humans (AWS / Strands)**

A class operations desk. Paper + marks in. Chapter map and two briefs out. Empty cells stay empty. The Strands agent runs the desk by calling tools; Python owns every number.

> We analyse the page. We do not grade unseen scripts.

Named desk: **Kavita Sharma**, Class 10-B Mathematics, Greenfield Public School. Named student: **Ravi Mehta**.

## Guardrails

- Empty / `NA` / `-` is **missing**, not zero
- No brief until the row is complete
- Family pane never receives the teacher brief or PTM wording
- No personality, “potential”, or mental-health claims
- The agent cannot write a mark; the teacher can

`GET /api/health` prints `eval.invented_marks` and `eval.leaked_teacher_briefs`. Both should be `0`. `make eval` is the same gate.

## Run locally

Python 3.10+. Tesseract is optional (`brew install tesseract`).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make demo
```

Open http://127.0.0.1:8080 — password `demo`.

```bash
make test
make eval
```

## Demo accounts

| Door | Email |
|---|---|
| Teacher | `teacher@markmap.demo` |
| Student | `ravi@markmap.demo` |
| Parent | `parent.ravi@markmap.demo` |

Also 10-A: `ira@markmap.demo` / `parent.ira@markmap.demo`.

The six video beats are in [docs/demo.md](docs/demo.md).

## What the agent can and cannot do

Live list: `GET /api/policy`.

**Run desk** always goes through one Strands `Agent`. Tools:

| Tool | What it does |
|---|---|
| `list_incomplete_rows` | Observe empty cells |
| `class_hotspots` | Observe leaked questions |
| `write_student_briefs` | Draft teacher + family briefs (refuses if a cell is empty) |
| `run_desk_nags` | Teacher fill-marks task or class reteach proposal |

`write_mark`, `unlock_brief`, and `set_question_chapter` are cancelled by a `BeforeToolCall` hook before they run. The teacher fills a yellow empty cell on the Student pane (`PATCH /api/papers/{id}/students/{roll}/cells/{qid}`).

Without AWS keys the same loop uses a **scripted** local model. With keys, Claude Sonnet on Bedrock in `us-west-2`.

```bash
cp .env.example .env
# AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_REGION=us-west-2
```

Cron / EventBridge: `POST /api/desk/sweep` with header `X-Markmap-Secret`.

## Limits

- Synthetic class, not a school MIS
- No auto-grading of handwritten answers
- OCR optional; if Tesseract is missing, the sample screenshot is labelled **embedded sample text**
- Demo accounts only. Set `MARKMAP_SECRET` and `MARKMAP_ENV=production` before a public listen
- Store is one JSON file (atomic replace). A hosted demo is ephemeral unless you mount a volume
- Live URL and video: not published yet

## Architecture

See [docs/architecture.md](docs/architecture.md) and [docs/architecture.svg](docs/architecture.svg).

Browser → FastAPI → analyser.py + JSON store. Strands desk agent calls `@tools`. It never writes a mark.

## License

MIT. Sample papers and CSVs are in `data/samples/`.
