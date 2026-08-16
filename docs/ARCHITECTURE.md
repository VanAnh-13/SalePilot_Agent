# Architecture — SalePilot × Điện Máy Xanh

## Product

AI **so sánh & tư vấn điện máy – công nghệ theo nhu cầu thật** trên 14 ngành hàng:
need discovery theo ngành → catalog rank → trade-off → top 3.
Guardrail: numbers only from tools; never infer stock.

## Modules

| Module | Role |
|--------|------|
| **Lead** | `delegate` / `finalize` + need loop (nhận diện ngành + hỏi ngược) |
| **Catalog facade** | `app/agent/catalog_domain.py` — stable import surface cho API, tools, memory và evaluator |
| **Catalog queries** | `app/agent/catalog_queries.py` — public product shape, search/filter và compare |
| **Recommendation policy** | `app/agent/recommendation.py` — need extraction, follow-up, hard constraints, ranking và explanation |
| **Consultation** | `app/agent/consultation.py` — rank một lần và đóng gói recommendation + decision evidence dùng chung cho các serving route |
| **Category model** | `app/catalog/category_model.py` — dataclasses, generic factory và `CategoryRegistry` lookup/detection dùng chung |
| **Category adapters** | `app/catalog/categories.py` (workbook) và `crawl_categories.py` (crawl) — declarations + normalization riêng từng nguồn |
| **Runtime registry selector** | `app/catalog/registry.py` — chọn adapter qua `SALEPILOT_CATALOG_REGISTRY`, re-export stable registry interface |
| **Repository** | `app/catalog/repository.py` — MongoDB primary, in-memory cache, snapshot fallback |
| **Knowledge** | FAQ policy |
| **CRM / Escalation** | lead + human handoff |
| **Channel bus** | web (+ Zalo stub) via gateway |

## Critical path

```text
User → gateway → run_agent
                  ├─ clear recommendation → consult → recommend_top3 → build_decision
                  ├─ no API key           → offline → consult → same decision contract
                  └─ ambiguous / policy    → LangGraph tools
                                             ↓
                                      Vietnamese reply + trace/evidence
```

`consult()` giữ một `ConsultationResult` gồm need, recommendation và decision.
Route không gọi lại ranking engine khi cần lưu trajectory hoặc trả decision evidence.

## Data

- **MongoDB `salepilot.products`** — nguồn chính: 8.746 SKU, 14 ngành (`category_code` 30/36/38/39/40/41/49/72/73/75/115/116/137/139)
- `scripts/import_spec_catalog.py` — importer đọc `Spec_cate_gia.xlsx`, chuẩn hóa qua registry, upsert Mongo + ghi snapshot
- `data/catalog_snapshot.json` — fallback offline khi Mongo tắt
- `data/faq.json` — guidance + giới hạn nguồn (không có tồn kho)
- `data/need_scenarios.json` — tình huống nhu cầu mẫu

## Document shape (MongoDB)

```json
{
  "sku": "...", "category": "may_lanh", "category_code": 36,
  "brand": "...", "name": "<derived>",
  "price_original_vnd": 0, "price_sale_vnd": 0, "price_vnd": 0,
  "has_current_price": true, "gift_promotion": "...",
  "norm": { "<spec chuẩn hóa theo ngành: area_min/max, noise_db, load_kg, ram_gb...>" },
  "specs": { "<cột gốc tiếng Việt>" },
  "search_text": "...", "source": "spec_cate_gia.xlsx:<sheet>", "source_row": 2
}
```

## Thêm ngành hàng mới

1. Chọn đúng adapter nguồn: `categories.py` cho workbook hoặc `crawl_categories.py` cho crawl.
2. Thêm `Category(...)` (aliases, specs, slots, priorities, trade-offs); chỉ thêm primitive dùng chung vào `category_model.py`.
3. Chạy importer tương ứng và contract/regression tests. Engine, tools, API và offline path nhận category qua stable runtime registry.
