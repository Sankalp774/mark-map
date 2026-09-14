# Deploy Mark Map — Bedrock, then AWS

Account: `966132822353`. Region: **us-west-2**. Intended model: `us.anthropic.claude-sonnet-4-6` or on-demand Nova (`amazon.nova-lite-v1:0` / `amazon.nova-2-lite-v1:0`).

**Current blocker (2026-09-14):** this account is **not authorized** to invoke Bedrock. `get-foundation-model-availability` returns `authorizationStatus: NOT_AUTHORIZED`. `converse` returns `ValidationException: Operation not allowed` for Nova, Llama, Mistral, and Claude, in every Region we tried. IAM is not the issue (tested as root). Until AWS Support flips the account to `AUTHORIZED`, run the desk locally (`MARKMAP_DESK_MODEL=mlx` → LM Studio, or `desk` for tests). Do **not** create App Runner while health is not `"backend":"bedrock"`.

Do the phases in order after that hold lifts.

## Phase 1 — Bedrock on this Mac

### 1. Open the right account and region

Console top-right must be account **966132822353**. Region menu: **US West (Oregon) / us-west-2**.

### 2. Turn on the Claude model

1. Open [Bedrock model catalog](https://us-west-2.console.aws.amazon.com/bedrock/home?region=us-west-2#/model-catalog)
2. Find **Claude Sonnet 4.6** (Anthropic). If the console lists it as Sonnet 4.5 / 4.6, pick the Sonnet 4.6 inference profile.
3. Enable / request access if the button is there. Wait until status is **Access granted**.
4. Optional check: Bedrock → **Chat / Text playground** → same model → send `ping`. You should get a reply. If this fails, the app will fail too.

### 3. IAM user for the app (not root keys)

1. [IAM → Users → Create user](https://us-west-2.console.aws.amazon.com/iam/home#/users)
2. Name: `markmap-desk`
3. Access: **Programmatic access** only. Do **not** tick AWS Console access.
4. Permissions → **Attach policies directly** is empty. After create: user → **Add inline policy** → JSON → paste `docs/iam-bedrock.json` → name `MarkMapBedrockInvoke` → Create.
5. Security credentials → **Create access key** → Use case **Application running outside AWS** → Create.
6. Copy **Access key ID** and **Secret access key** once. The secret is not shown again.

### 4. Budget so credits cannot silently run out

[Budgets](https://us-west-2.console.aws.amazon.com/billing/home#/budgets) → Create budget → **Cost budget** → $10/month → email yourself. Credits still apply; this is the alarm.

### 5. Put keys on this Mac

In Terminal:

```bash
cd /path/to/mark-map
cp .env.example .env
```

Edit `.env`:

```
AWS_REGION=us-west-2
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6
MARKMAP_DISABLE_BEDROCK=0
```

Never commit `.env`. Never paste the secret into GitHub or chat if you can avoid it.

### 6. Restart and prove Bedrock

```bash
# stop old server if needed, then:
source .venv/bin/activate
python -m markmap
```

```bash
curl -s http://127.0.0.1:8080/api/health
```

You want `"backend":"bedrock"` and `"model":"us.anthropic.claude-sonnet-4-6"`.  
If it still says `desk`, the keys are missing or `MARKMAP_DISABLE_BEDROCK=1`.

Then in the app: teacher door → Load class → **Run desk**. Desk log should mention `desk_orchestrator` and the Bedrock model. First call can take 10–20s.

## Phase 2 — Host on AWS App Runner

Use **App Runner + GitHub + instance role**. The running service then calls Bedrock with a role, not with keys in env.

### 7. IAM role for App Runner

1. IAM → Roles → Create role
2. Trusted entity: **AWS service** → use case **App Runner** (or custom trust for `tasks.apprunner.amazonaws.com` and `build.apprunner.amazonaws.com` if the wizard needs it)
3. If App Runner is not in the list: Custom trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "tasks.apprunner.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

4. Name: `markmap-apprunner`
5. Add the same inline policy as `docs/iam-bedrock.json`

### 8. Create the App Runner service

1. [App Runner](https://us-west-2.console.aws.amazon.com/apprunner/home?region=us-west-2#/services)
2. Create service → **Source code repository** → GitHub → connect `Sankalp774/mark-map` → branch `main`
3. Deployment: **Manual** until the demo is stable
4. Configuration: **Use a Dockerfile** (the repo has one; it installs Tesseract)
5. Port: **8080**
6. Instance: 1 vCPU / 2 GB is enough for the demo
7. Instance role: `markmap-apprunner`
8. Environment variables:

| Key | Value |
|---|---|
| `PORT` | `8080` |
| `AWS_REGION` | `us-west-2` |
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-sonnet-4-6` |
| `MARKMAP_DISABLE_BEDROCK` | `0` |
| `MARKMAP_ENV` | `production` |
| `MARKMAP_SECRET` | a long random string (not `markmap-demo-secret`) |

Do **not** put `AWS_ACCESS_KEY_ID` here if the instance role is attached.

9. Health check: HTTP `/api/health`
10. Create. Wait for **Running**. Copy the default `*.awsapprunner.com` URL.

The store is the JSON file inside the container. A restart wipes the class. That is fine for the hackathon: login → Reset demo → Load class. Say so on Devpost.

### 9. Smoke the live URL

```bash
curl -s https://YOUR-ID.us-west-2.awsapprunner.com/api/health
```

Expect `backend: bedrock`. Then teacher / Ravi / parent doors, password `demo`. Run the six beats in `docs/demo.md`.

Put that URL on the Devpost submission as the live demo.

## Phase 3 — Submission extras (after the URL works)

- Record the six beats (≤ 5 min)
- builder.aws.com post, title contains **Agents for Humans**
- AgentCore `{ "action": "sweep" }` is optional. Do not start it until Bedrock + App Runner work.

## If something fails

| Symptom | Likely cause |
|---|---|
| `backend: desk` | No keys / role, or `MARKMAP_DISABLE_BEDROCK=1` |
| `AccessDeniedException` on Run desk | Model access not granted, or IAM policy missing inference-profile |
| `ValidationException` / unknown model | Wrong `BEDROCK_MODEL_ID` for this account; pick the ID from the Bedrock console |
| App Runner build fail | Dockerfile needs Docker configuration, not Python runtime |
| App Runner 401/crash on boot | `MARKMAP_ENV=production` with default `MARKMAP_SECRET` |
| Credits not moving | Usage is Bedrock in **us-west-2**; check Billing → Credits |
