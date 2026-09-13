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

The same Strands loop can use three brains. Tests always use **scripted**.

| `MARKMAP_DESK_MODEL` | Brain |
|---|---|
| `scripted` | Deterministic local stand-in (no LLM; `make test` / `make eval`) |
| `mlx` | Any OpenAI-compatible local server. Default: **LM Studio** at `http://192.168.31.64:1234/v1` with `qwen2.5-coder-7b-instruct-mlx@8bit`. Also works with oMLX (`:8000`) or Homebrew Ollama (MLX-backed on Apple silicon) if LM Studio is down. |
| `ollama` | Ollama on `http://127.0.0.1:11434` (`llama3.2` by default) |
| `bedrock` | Claude or Nova on Amazon Bedrock via `strands.models.BedrockModel` |

```bash
cp .env.example .env
# LM Studio: start the local server, load a tool-capable instruct model, then:
# MARKMAP_DESK_MODEL=mlx
# MARKMAP_MLX_BASE_URL=http://192.168.31.64:1234/v1
# MARKMAP_MLX_MODEL=qwen2.5-coder-7b-instruct-mlx@8bit
```

`GET /api/health` reports `backend` and `model`. If the local server is down, the desk falls back to **scripted**. Gemma is a poor fit for this desk (weak tool calling). Prefer Qwen 2.5 Instruct.

### Amazon Bedrock status (honest)

The Strands agent is **wired for Bedrock**. Invoke is **not live**.

AWS account `966132822353` (classic, `us-west-2` / `us-east-1`) and project **Stack of Dreams** (`499567237743`) both return:

```text
authorizationStatus: NOT_AUTHORIZED
ValidationException: Operation not allowed
```

That is an **account-level Bedrock authorization hold**, not a missing IAM policy and not a missing model-access tick. We checked Amazon Nova Micro/Lite/2 Lite, Llama 3, Mistral, and Claude Sonnet 4.6 in us-east-1, us-west-2, ap-south-2, ap-southeast-1, and eu-west-1. Models **list**. **Converse / InvokeModel fail.** Root credentials do not change it. A Bedrock API key does not change it. Nova is not a Marketplace subscribe model; the Anthropic first-use form is a separate later step for Claude only.

A Support case was opened. Until AWS sets `authorizationStatus` to `AUTHORIZED`, this repo runs the **same Strands tools** on LM Studio (or scripted in CI). No model trace is fabricated as Bedrock. When AWS unblocks invoke, set `MARKMAP_DESK_MODEL=bedrock` (and `MARKMAP_DISABLE_BEDROCK=0`). Do not host App Runner until `/api/health` shows `"backend":"bedrock"`.

Cron / EventBridge: `POST /api/desk/sweep` with header `X-Markmap-Secret`.

## Limits

- Synthetic class, not a school MIS
- No auto-grading of handwritten answers
- OCR optional; if Tesseract is missing, the sample screenshot is labelled **embedded sample text**
- Demo accounts only. Set `MARKMAP_SECRET` and `MARKMAP_ENV=production` before a public listen
- Store is one JSON file (atomic replace). A hosted demo is ephemeral unless you mount a volume
- Live public URL: not published yet (waiting on Bedrock authorization before App Runner)
- Demo video: not published yet

## Architecture

See [docs/architecture.md](docs/architecture.md) and [docs/architecture.svg](docs/architecture.svg).

Browser → FastAPI → analyser.py + JSON store. Strands desk agent calls `@tools`. It never writes a mark. The model is LM Studio today; Bedrock when AWS authorizes invoke.

## License

MIT. Sample papers and CSVs are in `data/samples/`.
