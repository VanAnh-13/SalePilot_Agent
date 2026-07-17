# Architecture — SalePilot × Điện Máy Xanh

## Product

AI **so sánh & tư vấn tủ lạnh theo nhu cầu thật**: need discovery → catalog rank → trade-off → top 3. Guardrail: numbers only from tools; never infer stock.

## Modules

| Module | Role |
|--------|------|
| **Lead** | `delegate` / `finalize` + need loop |
| **Catalog domain** | `search`, `compare`, `recommend_top3` |
| **Knowledge** | FAQ policy |
| **CRM / Escalation** | lead + human handoff |
| **Channel bus** | web (+ Zalo stub) via gateway |

## Critical path

User → gateway → run_agent (or offline) → catalog/knowledge tools → Vietnamese reply

## Data

- `data/products.json` — offline snapshot of all 1,692 `category_code=38` refrigerator SKUs
- `scripts/import_refrigerators.py` — deterministic public Google Sheet importer
- `data/PRODUCT_SOURCE.md` — source and normalization assumptions
- `data/faq.json` — refrigerator guidance and explicit source limitations
- `data/need_scenarios.json` — refrigerator need cases
