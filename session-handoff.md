# Session Handoff — SalePilot

## Current State (2026-08-06)

### What is working
- Multi-agent chat: Lead + sub-agents (catalog, knowledge, order, crm, escalation)
- Full DMX catalog imported: **13,754 products / 119 categories / 436 brands**
- Spec index: **1,348 unique spec keys** (dynamic, no hardcoded list)
- Knowledge base: **106 FAQ chunks** with smart chunking + metadata tags
- Trajectories: **10 anonymized conversations** / 56 tool calls / 7 tool schemas
- Vietnamese NLP: abbreviation expansion integrated into recommendation engine
- API: `/health`, `/chat`, `/products`, `/mcp` working offline
- Frontend: Next.js chat + dashboard (TypeScript 0 errors)
- Paper: `paper/main.tex` — IEEE RIVF 2026 (deadline 2026-08-31)

### Architecture (SOLID, no hardcoded paths)

```
DMX_SRC_DIR (.env)
    └── scripts/shared.py::resolve_dmx_src()   ← single resolve point
            ├── import_dmx_products.py          → catalog_snapshot.json + spec_index.json
            ├── import_products_detail.py       → MongoDB (optional)
            ├── import_policies.py              → faq.json (SmartChunker)
            ├── import_chat_trajectories.py     → data/trajectories/dmx_chat/
            └── extract_tool_schemas.py         → data/research/

app/catalog/spec_index.py    → SpecIndex (SRP, data-driven)
app/rag/chunker.py           → SmartChunker + ChunkMetadataExtractor (SRP/OCP)
app/rag/store.py             → Scorer class + search_policy() (metadata-aware)
app/nlp/                     → ViNormalizer, AbbreviationRegistry, EntityExtractor
app/dmx/                     → ChatParser, Anonymizer, TrajectoryWriter
```

### Key config
- `DMX_SRC_DIR` — path to DMX data directory (set in `.env`)
- `CATALOG_BACKEND=snapshot` — offline mode (no DB needed)
- `CATALOG_BACKEND=postgres` — production (Neon PostgreSQL)

## Commands

```bash
# Start backend
cd backend && uv run uvicorn app.main:app --reload --port 8000

# Start frontend
cd frontend && npm run dev

# Full verification
bash scripts/verify.sh

# Backend tests
cd backend && uv run python -m unittest discover -s tests

# Re-import DMX data (set DMX_SRC_DIR in .env first)
cd backend
python -m scripts.import_dmx_products
python -m scripts.import_policies
python -m scripts.import_chat_trajectories
python -m scripts.extract_tool_schemas

# Dry run (no files written)
python -m scripts.import_dmx_products --dry-run
```

## Next Best Step

1. **Paper**: Add Section IV Dataset Analysis to `paper/main.tex`
   - Use stats from `data/catalog_stats.json`
   - Figures already generated in previous session
   - Page budget: shorten Sections II, III.4, III.5 to stay ≤ 6 pages
   - Fill in author block before EDAS submission (deadline 2026-08-31)

2. **Backend**: Update `app/config.py` `catalog_snapshot` default to point at
   `catalog_snapshot.json` (already generated) and verify `/products` endpoint
   returns 13,754 products in offline mode.

3. **Tests**: Add unit tests for `SpecIndex`, `SmartChunker`, `ViNormalizer`
   to increase test coverage from 40 to ~50 tests.

## Known Gaps

- `init.sh` has POSIX-only venv activation (protected file, not edited)
- Production `/health` — not verified this session (deployment task)
- No browser evidence for dashboard UI
- Paper author block still placeholder
