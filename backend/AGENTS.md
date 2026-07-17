# Backend context (SalePilot)

Loaded by coding agents when working under `backend/`.

## Stack

- Python 3.12+ (Docker image `python:3.12-slim`)
- FastAPI + Uvicorn
- LangGraph multi-agent: Lead (`delegate` / `finalize`) + catalog | knowledge | crm | order | escalation
- SQLAlchemy async + SQLite (`data/salepilot.db`)
- Offline path: `app/agent/offline.py` (no API key)
- Skills: `app/agent/skills/*/SKILL.md` (loaded into Lead prompt catalog)

## Commands

```bash
cd backend
source .venv/bin/activate   # or: python3 -m venv .venv && pip install -r requirements.txt
python -m scripts.seed_db
python -m scripts.ingest_kb
uvicorn app.main:app --reload --port 8000
python -m scripts.simulate_zalo --text "Gia đình 4 người cần tủ lạnh dưới 15 triệu"
```

From repo root: `./scripts/verify.sh`

## Layout

| Path | Role |
|------|------|
| `app/main.py` | FastAPI app |
| `app/agent/graph.py` | Lead LangGraph |
| `app/agent/lead_tools.py` | `delegate`, `finalize` |
| `app/agent/subagents/` | Isolated specialists |
| `app/agent/tools/` | Business tools |
| `app/agent/skills/` | Portable product skills |
| `app/channels/zalo/` | Webhook + Mock OA client |
| `app/api/` | chat, leads, products, outbox |
| `data/products.json`, `data/faq.json` | Refrigerator snapshot + guidance |
| `scripts/import_refrigerators.py` | Refresh category-code-38 snapshot from Google Sheet |

## Rules

- Keep offline multi-agent working without keys.
- Sub-agents: tool whitelist only; return short summaries to Lead.
- Do not invent prices or stock — use catalog tools; the source has no stock column.
- After changes: run `./scripts/verify.sh` from repo root.
