# Refrigerator catalog source

- Workbook: `Spec_cate_gia.xlsx`
- Google Sheet ID: `1EjYJxHmYPZJsUrpxXjkUgThioqBH4KgW`
- Tab: `Tủ Lạnh`
- GID: `1924624295`
- Category filter: `category_code = 38`
- Import command: `python -m scripts.import_refrigerators`

`products.json` is the checked-in offline snapshot used by SalePilot. The importer keeps every refrigerator SKU from the selected tab and preserves non-empty source cells in each product's `specs` object.

The source contains 1,692 refrigerator SKUs. Only rows with `giá khuyến mãi` or `giá gốc` receive `price_vnd`; recommendation ranking excludes rows without a current price. Missing stock is not converted to zero and SalePilot does not claim availability because the sheet has no stock column.

`name` is a deterministic display label assembled from source-backed brand, style, usable capacity, and model code because this tab does not contain a product-name column.
