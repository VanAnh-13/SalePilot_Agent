# Deployment Handoff — RIVF Track 2 public evidence

Owner deploys manually. Agent collects evidence only after `/health` returns 200.

## Authorized targets

| Role | URL |
|------|-----|
| Frontend | https://sale-pilot-agent.vercel.app |
| Backend | https://optivisionlab.fit-haui.edu.vn |

Observed at 2026-07-25 intent freeze: frontend served SalePilot; backend `/health` returned **502**.

## Backend checklist (owner)

1. Deploy current backend image/code with env:
   - `CATALOG_BACKEND` = `postgres` or `snapshot`
   - DB / Mongo URLs as needed
   - `CORS_ORIGINS` includes `https://sale-pilot-agent.vercel.app`
   - Do **not** commit secrets
2. Confirm:
   ```bash
   curl -sS https://optivisionlab.fit-haui.edu.vn/health
   ```
   Expect HTTP 200 and a `catalog` object.
3. Smoke chat:
   ```bash
   curl -sS -X POST https://optivisionlab.fit-haui.edu.vn/chat \
     -H "Content-Type: application/json" \
     -d "{\"message\":\"tủ lạnh dưới 15 triệu\",\"external_id\":\"deploy-smoke\",\"channel\":\"web\"}"
   ```

## Frontend checklist (owner)

1. Deploy Next.js with:
   ```bash
   NEXT_PUBLIC_API_URL=https://optivisionlab.fit-haui.edu.vn
   ```
2. Open https://sale-pilot-agent.vercel.app/chat and send one Vietnamese need query.
3. Confirm reply renders (Agent Trace optional for this evidence pack).

## Evidence collection (after health is green)

From repo root:

```bash
python scripts/collect_deployment_evidence.py \
  --url https://optivisionlab.fit-haui.edu.vn \
  --frontend-url https://sale-pilot-agent.vercel.app \
  --chat-requests 20 \
  --output experiments/results/deployment_evidence_public.json
```

Local Docker (not a substitute for public claim):

```bash
python scripts/collect_deployment_evidence.py \
  --url http://127.0.0.1:8000 \
  --output experiments/results/deployment_evidence_local.json
```

## Rollback

1. Redeploy previous known-good backend/frontend artifacts.
2. Re-run `/health` + one `/chat` smoke.
3. Keep failed evidence JSON for the paper limitations section if public URL remains down.

## Paper claim rule

- Public deployment claims require `deployment_evidence_public.json` with health status 200.
- Local-only measurements must be labeled local prototype, not observed public production.
