# Local brains — LM Studio, Ollama, MLX

The desk is always a **Strands** `Agent`. These backends only change the model. Tools and the policy hook stay the same.

`GET /api/health` must show `"backend":"mlx"` or `"backend":"ollama"` before you expect tokens in LM Studio / Ollama.

If the local server is down, Mark Map **falls back to the built-in desk model**. That is intentional.

Prefer a small **instruct** model (Llama 3.2 3B, Qwen 2.5 Instruct). Skip reasoning models (R1) for Run desk.

---

## LM Studio (OpenAI-compatible)

LM Studio’s local server is the `mlx` backend in this repo.

1. In LM Studio: load an instruct model → **Developer** → **Start server**.
2. Confirm the API root (usually `http://127.0.0.1:1234` or a LAN IP). Models list:

   ```bash
   curl -s http://127.0.0.1:1234/v1/models
   ```

3. Copy the **exact** `id` of the loaded model.
4. In `.env`:

   ```bash
   MARKMAP_DESK_MODEL=mlx
   MARKMAP_DISABLE_BEDROCK=1
   MARKMAP_MLX_BASE_URL=http://127.0.0.1:1234/v1
   MARKMAP_MLX_MODEL=llama-3.2-3b-instruct
   ```

   LAN example: `MARKMAP_MLX_BASE_URL=http://192.168.31.64:1234/v1`

5. Restart `python -m markmap`. Watch tokens in LM Studio. Watch tools in Mark Map’s desk trace.

Or:

```bash
./scripts/run-lmstudio.sh
```

Override host/model:

```bash
MARKMAP_MLX_BASE_URL=http://192.168.31.64:1234/v1 \
MARKMAP_MLX_MODEL=llama-3.2-3b-instruct \
./scripts/run-lmstudio.sh
```

---

## Ollama (MLX-backed on Apple silicon)

Homebrew `ollama` on this Mac links **mlx / mlx-c**. That is the `ollama` backend.

```bash
brew install ollama
brew services start ollama
ollama pull llama3.2
curl -s http://127.0.0.1:11434/api/tags
```

`.env`:

```bash
MARKMAP_DESK_MODEL=ollama
MARKMAP_DISABLE_BEDROCK=1
OLLAMA_HOST=http://127.0.0.1:11434
MARKMAP_OLLAMA_MODEL=llama3.2
```

```bash
./scripts/run-ollama.sh
```

---

## oMLX / mlx_lm.server

If `omlx serve … --port 8000` (or `mlx_lm.server`) is up, the same `mlx` backend talks OpenAI `/v1`:

```bash
MARKMAP_DESK_MODEL=mlx
MARKMAP_MLX_BASE_URL=http://127.0.0.1:8000/v1
MARKMAP_MLX_MODEL=<id from GET /v1/models>
```

If that URL is down, `MARKMAP_DESK_MODEL=mlx` uses **Ollama** when it is running (Apple MLX path).

---

## Which file does what

| Env | Code |
|---|---|
| `MARKMAP_DESK_MODEL=mlx` | `strands.models.openai.OpenAIModel` if `/v1/models` answers; else `OllamaModel` |
| `MARKMAP_DESK_MODEL=ollama` | `strands.models.ollama.OllamaModel` |
| `MARKMAP_DESK_MODEL=desk` | `DeskModel` (demo / tests / Docker) |

Bedrock is a **separate** file: [bedrock.md](bedrock.md).
