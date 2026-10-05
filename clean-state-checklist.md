# Clean State Checklist — SalePilot

Re-verify every item each session before marking complete.

## Core System

- [ ] Backend starts cleanly: `uv run uvicorn app.main:app --port 8000`
- [ ] Frontend starts cleanly: `cd frontend && npm run dev`
- [ ] `/health` returns 200
- [ ] `/chat` smoke: basic query returns valid response
- [ ] `bash scripts/verify.sh` passes (offline multi-agent smoke)
- [ ] Backend tests pass: `uv run python -m unittest discover -s tests` (40/40)

## Catalog

- [ ] `data/catalog_snapshot.json` present (13,754 products)
- [ ] `data/spec_index.json` present (1,348 spec keys)
- [ ] `data/faq.json` present (106 KB chunks with metadata)
- [ ] Catalog loads from snapshot when DB unavailable

## Data Pipeline (re-run when DMX data changes)

```bash
# From backend/
python -m scripts.import_dmx_products --src <DMX_SRC_DIR>
python -m scripts.import_policies --src <DMX_SRC_DIR>
python -m scripts.import_chat_trajectories --src <DMX_SRC_DIR>
python -m scripts.extract_tool_schemas --src <DMX_SRC_DIR>
```

Or set `DMX_SRC_DIR` in `.env` and run without `--src`.

## Research Artifacts

- [ ] `data/trajectories/dmx_chat/` — 10 anonymized conversations
- [ ] `data/research/dmx_tool_schemas.json` — 7 tools, 56 calls
- [ ] `data/research/intent_test_cases.json` — 56 test cases
- [ ] `data/catalog_stats.json` — product statistics

## Code Quality

- [ ] No hardcoded OS-specific paths in any `.py` file
- [ ] No secrets committed (`.env` gitignored)
- [ ] Frontend TypeScript: `npx tsc --noEmit` — 0 errors
- [ ] Scope guard: `python scripts/validate_agent_scope.py` passes

## Paper (IEEE RIVF 2026, deadline: 2026-08-31)

- [ ] `paper/main.tex` compiles without errors
- [ ] Dataset statistics match `data/catalog_stats.json`
- [ ] Author block filled in
- [ ] Page count ≤ 6
