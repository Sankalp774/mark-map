# Amazon Bedrock — connect the desk

Target production brain: Strands `BedrockModel` → **Converse** on `bedrock-runtime`. No long-term Bedrock API keys. App Runner should use an **instance role**.

Do not set `MARKMAP_DESK_MODEL=bedrock` until this is true:

```bash
aws bedrock get-foundation-model-availability \
  --region us-west-2 \
  --model-id amazon.nova-lite-v1:0 \
  --query authorizationStatus \
  --output text
```

Expected: `AUTHORIZED`. This account has returned `NOT_AUTHORIZED` (then `ValidationException: Operation not allowed` on Converse) for Nova, Llama, Mistral, and Claude. That is an **account hold**, not a missing IAM tick. Support must flip it.

When it is `AUTHORIZED`:

## 1. Ping

```bash
aws bedrock-runtime converse \
  --region us-west-2 \
  --model-id amazon.nova-lite-v1:0 \
  --messages '[{"role":"user","content":[{"text":"pong"}]}]' \
  --inference-config '{"maxTokens":32}'
```

Claude Sonnet 4.6 (after the Anthropic first-use form): `us.anthropic.claude-sonnet-4-6` or on-demand `anthropic.claude-sonnet-4-6`.

## 2. Credentials

Local: `aws login` (or `AWS_PROFILE`) — not a Bedrock bearer key.

```bash
export AWS_PROFILE=mark-map-agent   # or your profile
export AWS_REGION=us-west-2
```

Hosted: instance role. Policy: [iam-bedrock.json](iam-bedrock.json).

## 3. Run the desk on Bedrock

`.env`:

```bash
MARKMAP_DESK_MODEL=bedrock
MARKMAP_DISABLE_BEDROCK=0
AWS_REGION=us-west-2
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6
# or: BEDROCK_MODEL_ID=amazon.nova-lite-v1:0
```

```bash
./scripts/run-bedrock.sh
```

Health must show `"backend":"bedrock"` before App Runner. Hosting steps: [deploy.md](deploy.md).

## Honest status

Until AWS authorizes invoke, the published demo uses the built-in desk model (same tools). Optional laptop brains: [lmstudio-ollama-mlx.md](lmstudio-ollama-mlx.md). Do not fabricate a Bedrock trace.
