# Session Handoff — SalePilot

## Verified Now

- What is currently working: refrigerator catalog advisor from Google Sheet `Tủ Lạnh` category_code=38; offline multi-agent chat; `/health`, `/chat`, `/products`, `/mcp`; frontend chat; local MCP stdio server
- What verification actually ran: `./init.sh`; `./scripts/verify.sh`; frontend build; MCP build/smoke/audit; HTTP chat and stock FAQ smokes; browser desktop/mobile chat verification

## Changed This Session

- Code or behavior added: deterministic refrigerator importer, 1,692-SKU snapshot, refrigerator ranking/search/compare/order logic, stock-source guardrails, MCP refrigerator contract/evaluations, frontend refrigerator chat copy
- Infrastructure or harness changes: stronger `scripts/verify.sh` coverage for hard budgets, source constraints, stock FAQ routing, order validation, and MCP API contract

## Broken Or Unverified

- Known defect: none blocking local refrigerator/MCP smoke
- Unverified path: dashboard browser evidence, production deploy
- Risk for the next session: sheet refresh can change evaluation answers; rerun importer and update MCP evaluation expected values if source prices/specs change

## Next Best Step

- Highest-priority unfinished feature: `dash-001`
- Why it is next: dashboard UI still needs fresh browser evidence after refrigerator migration
- What counts as passing: evidence in `feature_list.json`
- What must not change during that step: multi-agent graph contracts (`delegate`/`finalize`)

## Commands

- Startup: `./init.sh`
- Verification: `./scripts/verify.sh`
- Focused debug: `cd backend && source .venv/bin/activate && python -m scripts.simulate_zalo --text "Gia đình 4 người cần tủ lạnh dưới 15 triệu"`
