# Catalog source — Điện Máy Xanh crawl

## Primary (runtime)

- Local pack: `C:\Downloads\DMX_product\`
- Products: `products_detail.json` (~13.7k SKU, 118 categories)
- Policies: `chinh_sach_*.md`, `dieu-khoang-su-dung.md`, `noi_quy_cua_hang.md`, `chat_luong_phuc_vu.md`
- Optional spreadsheet: `products_detail.xlsx`
- Chat sample (not ingested by default): `chat_history_buy_product.json`

### Import

```bash
# from backend/ (Docker mounts C:\Downloads\DMX_product -> /data)
python -m scripts.import_products_detail --json /data/products_detail.json --snapshot-only
python -m scripts.import_policies --src /data
python -m scripts.etl_to_postgres --source snapshot --skip-specs   # Neon/cloud
```

- Snapshot: `backend/data/catalog_snapshot.json`
- FAQ/KB: `backend/data/faq.json` + `backend/data/policies/`
- Normalized DMX rows retain `source_row`; Postgres mirrors the same provenance field.
- Registry: `app/catalog/crawl_categories.py` (deep: điện thoại, laptop, tivi, tai nghe, máy lạnh, tủ lạnh code **1943**, máy giặt, máy hút bụi)

### Runtime backend

- `CATALOG_BACKEND=postgres` → Neon cloud (primary when loaded)
- Fallback: Mongo → snapshot

The RIVF workbook importer is isolated from this runtime path: it writes
`backend/data/research/catalog_workbook_snapshot.json` and the dedicated
`research_catalog_workbook_products` collection.

## Legacy / research-only

- Refrigerator Google Sheet / `products.json` — historical fridge-only path
- Workbook `Spec_cate_gia.xlsx` + `app/catalog/categories.py` — RIVF 14-ngành experiment path (not the live DMX catalog)
