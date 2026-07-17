# SalePilot — Multi-Agent SME Sales (VAIC 2026)

**SalePilot** — multi-agent AI **so sánh & tư vấn tủ lạnh theo nhu cầu thật** từ Google Sheet `category_code=38` (VAIC · Điện Máy Xanh · Năng suất SME).

**Stack:** FastAPI + LangGraph · Next.js · catalog domain (rank/compare/top3) · memory · dashboard

## Architecture (short)

```
Web chat → Lead Agent
             ├─ Catalog (search / compare / recommend_top3)
             ├─ Knowledge (hướng dẫn chọn tủ + giới hạn nguồn)
             ├─ CRM (SĐT / lead)
             └─ Escalation (người)
```

Need loop: household size/capacity + budget + style/dimensions → top 3 + trade-off. The sheet has no stock column, so SalePilot never claims availability.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md).

## Local MCP server

`mcp/` contains the local stdio SalePilot MCP server for catalog search, comparison, top-3 recommendations, FAQ lookup, and consent-gated CRM lead creation. See [mcp/README.md](mcp/README.md).

## Agent harness

This repo includes a **coding-agent harness** (instructions · tools · environment · state · feedback):

| File | Purpose |
|------|---------|
| `AGENTS.md` | Operating rules for coding agents |
| `feature_list.json` | Feature tracker + evidence |
| `claude-progress.md` | Session log / verified state |
| `init.sh` | Install + baseline verify |
| `scripts/verify.sh` | Offline multi-agent smoke |
| `session-handoff.md` / `clean-state-checklist.md` | Session close-out |
| `docs/HARNESS.md` | Map + patterns + lecture links |
| `backend/AGENTS.md` / `frontend/AGENTS.md` | Progressive context (subdir maps) |

Pattern from [Learn Harness Engineering](https://walkinglabs.github.io/learn-harness-engineering/en/).

## Quick start

```bash
cp .env.example .env
# optional: OPENAI_API_KEY

cd backend && source .venv/bin/activate  # or python3 -m venv .venv && pip install -r requirements.txt
python -m scripts.seed_db && python -m scripts.ingest_kb
uvicorn app.main:app --reload --port 8000

# Terminal B
cd frontend && npm install && npm run dev
```

Open http://localhost:3000 → **Tư vấn**

```bash
# from repo root
./scripts/verify.sh
```

### Docker

```bash
cp .env.example .env
docker compose up --build
```

### Simulate Zalo

```bash
# backend running on :8000
cd backend && source .venv/bin/activate
python -m scripts.simulate_zalo --text "Gia đình 4 người cần tủ lạnh dưới 15 triệu, ngang tối đa 70 cm"
```

## Demo script

See [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md).

## VAIC deliverables checklist

- [ ] Presentation slides  
- [ ] Demo video ≤ 5 min  
- [ ] Public GitHub  
- [ ] Live deployed URL  
- [ ] Project description  
- [ ] AI collaboration log  

## License

MIT — hackathon scaffold.
