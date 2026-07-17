# Progress Log — SalePilot

## Current Verified State

- Repository root: `/home/vananh/Homeworks/hackathon_base`
- Standard startup path: `./init.sh` then backend `uvicorn` + frontend `npm run dev`
- Standard verification path: `./scripts/verify.sh`
- Current highest-priority unfinished feature: `dash-001` (dashboard browser evidence)
- Current blocker: none for local refrigerator + MCP smoke

## Session Log

### Session 001

- Date: 2026-07-17
- Goal: Scaffold multi-agent SalePilot base for VAIC SME track (CSKH/Sales + Zalo stub)
- Completed:
  - Backend Lead + sub-agents, tools, offline multi-agent path
  - API chat/leads/products/outbox/zalo webhook
  - Frontend home/chat/dashboard
  - Seed data (products/FAQ), docs
  - Harness pack (AGENTS.md, feature_list, init, progress)
- Verification run:
  - `python -m scripts.seed_db` + `ingest_kb`
  - Offline `run_agent` with catalog+knowledge tools
  - HTTP `/health` + `/chat` smoke
- Evidence captured:
  - Historical base scaffold chat returned a furniture demo reply; current product domain is refrigerator category_code=38.
- Commits: (none required yet)
- Files or artifacts updated: entire scaffold under `backend/`, `frontend/`, `docs/`
- Known risk or unresolved issue:
  - Historical base scaffold catalog search was generic; current refrigerator verification is recorded in Session 005.
  - No automated pytest suite yet (`verify-001`)
  - Frontend not e2e tested in headless browser this session
- Next best step: mark chat/multi-agent features with evidence; implement `verify-001` pytest smoke or `deploy-001` when ready

### Session 002

- Date: 2026-07-17
- Goal: Nested AGENTS context + skill catalog wiring (host-agnostic patterns)
- Completed:
  - Progressive context: `backend/AGENTS.md`, `frontend/AGENTS.md`
  - Product skill registry loads `skills/*/SKILL.md` into Lead prompt
  - Removed third-party agent product branding from docs
- Verification run: `./scripts/verify.sh` after skill loader change
- Next best step: deploy or browser e2e

### Session 003

- Date: 2026-07-17
- Goal: Super-agent core into product runtime (memory, skills activate, parallel, gateway, sandbox, fetch, scheduler, trajectory)
- Completed: modules under agent/memory, skills tools+writer, sandbox, web, trajectory, gateway, scheduler; APIs /memory /runs /jobs; dashboard panels; verify extended
- Verification run: `./scripts/verify.sh` PASS (agents, memory phone, sandbox deny, trajectory run_id)
- Next best step: `deploy-001` or UI browser evidence

### Session 004

- Date: 2026-07-17
- Goal: Add a local TypeScript stdio MCP server and backend contract for SalePilot.
- Branch: `feature/salepilot-mcp` (derived from `feature/product-advisor-dmx`; `main` and `dev` remain base-only).
- Completed:
  - Added FastAPI `/mcp` catalog, comparison, recommendation, FAQ, and consent-gated lead endpoints.
  - Extracted shared CRM lead persistence so the agent tool and MCP endpoint use the same write path.
  - Added `mcp/` TypeScript server using the stable MCP SDK v1, Zod schemas, structured output, pagination, timeouts, and actionable errors.
  - Added six tools: product search/detail/compare/recommendation, FAQ search, and explicit-consent lead creation.
  - Added `mcp/README.md`, ten read-only `mcp/evaluations.xml` cases, and a backend API contract smoke.
- Verification run:
  - `./scripts/verify.sh` PASS, including MCP endpoint smoke and protected lead write check.
  - `cd mcp && npm run build && SALEPILOT_API_BASE_URL=http://127.0.0.1:8000 npm run smoke` PASS (six tools).
  - Isolated SQLite backend with matching write tokens: positive lead creation smoke PASS.
  - `cd mcp && npm audit --omit=dev` reports `found 0 vulnerabilities`.
- Known risk or unresolved issue:
  - Lead creation is intentionally unavailable until a unique `MCP_WRITE_TOKEN` is configured in the backend and passed as `SALEPILOT_MCP_WRITE_TOKEN` to the local client.
- Next best step: configure a local MCP client using `mcp/README.md`, or record frontend browser evidence for `dash-001`.

### Session 005

- Date: 2026-07-17
- Goal: Migrate SalePilot from AC/base demo catalog to the supplied Google Sheet refrigerator tab.
- Branch: `feature/refrigerator-catalog` (derived from `feature/salepilot-mcp`; `main` and `dev` remain base-only).
- Completed:
  - Imported the public `Tủ Lạnh` sheet (`gid=1924624295`, `category_code=38`) into `backend/data/products.json`.
  - Added deterministic importer `backend/scripts/import_refrigerators.py` and source contract doc `backend/data/PRODUCT_SOURCE.md`.
  - Reworked catalog search, compare, need extraction, recommendations, order drafts, MCP API/client, offline agent, prompts, FAQ, frontend copy, and docs for refrigerators.
  - Preserved all 1,692 SKUs as searchable data; recommendation uses only the 252 rows with current price.
  - Added guardrails for absent source stock: no stock claims, stock questions route to FAQ/knowledge.
  - Fixed review findings: hard budgets are enforced, unaccented budget text and decimal dimensions parse, equal price rows are not treated as discounts, external-water search works, order qty is validated, `/products` invalid pagination returns 422, and frontend session IDs are per browser session without hydration mismatch.
- Verification run:
  - `python -m scripts.import_refrigerators` PASS; snapshot SHA-256 `e4a8df9d43e33b058fb68d322ab7ff40b0c0318b775518f0bfc0c55f132e9b2a`.
  - `./scripts/verify.sh` PASS with refrigerator, hard-budget, stock FAQ, order-validation, memory, sandbox, and MCP API checks.
  - `./init.sh` PASS after the migration.
  - `cd frontend && npm run build` PASS.
  - `cd mcp && npm run build && SALEPILOT_API_BASE_URL=http://127.0.0.1:8000 npm run smoke && npm audit --omit=dev` PASS.
  - Browser `/chat` desktop/mobile verified with console clean, `POST /chat` 200, top-3 refrigerator reply, and Agent Trace visible. Screenshots: `/tmp/opencode/salepilot-refrigerator-chat.png`, `/tmp/opencode/salepilot-refrigerator-chat-mobile.png`.
- Known risk or unresolved issue:
  - The source sheet has no stock column and no product-name column; display names are derived and stock must be checked outside SalePilot.
  - `mcp/evaluations.xml` answers are tied to the checked-in snapshot; rerun/update evaluations if the sheet snapshot changes.
- Next best step: commit and push `feature/refrigerator-catalog`, then resume `dash-001` browser evidence or deployment work.
