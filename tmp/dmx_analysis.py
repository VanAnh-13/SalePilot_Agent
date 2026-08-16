"""Analyze DMX product data and produce visualizations for agent design insights."""
import json
from pathlib import Path
from collections import Counter
from statistics import median, mean, stdev
import math

SRC = Path(r"C:\Downloads\DMX_product\products_detail.json")
OUT_DIR = Path(__file__).resolve().parent / "dmx_output"
OUT_DIR.mkdir(exist_ok=True)

data = json.loads(SRC.read_text(encoding="utf-8"))


def parse_num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


# ── basic stats ──────────────────────────────────────────────
cats = Counter(item.get("category_name") for item in data if item.get("category_name"))
brands = Counter(item.get("brand") for item in data if item.get("brand"))
prices = [parse_num(item.get("Giá khuyến mãi")) for item in data]
gross = [parse_num(item.get("Giá gốc")) for item in data]
ratings = [parse_num(item.get("rating_vote")) for item in data]
sold = [parse_num(item.get("quantity_sold")) for item in data]
prices_clean = [p for p in prices if p is not None]
gross_clean = [p for p in gross if p is not None]
ratings_clean = [p for p in ratings if p is not None]
sold_clean = [p for p in sold if p is not None]

print("=" * 60)
print("DMX PRODUCT DATA — SUMMARY")
print("=" * 60)
print(f"Total rows:           {len(data):,}")
print(f"Unique categories:    {len(cats)}")
print(f"Unique brands:        {len(brands)}")
print(f"Products with price:  {len(prices_clean):,}")
print(f"Products with rating: {len(ratings_clean):,}")
print(f"Products with sold:   {len(sold_clean):,}")

print("\n--- Top 10 categories ---")
for k, v in cats.most_common(10):
    print(f"  {k}: {v:,}")

print("\n--- Top 10 brands ---")
for k, v in brands.most_common(10):
    print(f"  {k}: {v:,}")

print("\n--- Price (promo) stats ---")
print(f"  min={min(prices_clean):,.0f}  median={median(prices_clean):,.0f}  max={max(prices_clean):,.0f}")
print(f"  mean={sum(prices_clean)/len(prices_clean):,.0f}  stdev={stdev(prices_clean):,.0f}")

print("\n--- Price buckets (promo) ---")
buckets = [
    (0, 500_000), (500_000, 2_000_000), (2_000_000, 5_000_000),
    (5_000_000, 10_000_000), (10_000_000, 20_000_000), (20_000_000, 50_000_000),
    (50_000_000, float("inf")),
]
for lo, hi in buckets:
    cnt = sum(1 for p in prices_clean if lo <= p < hi)
    label = f"{lo/1e6:.1f}-{hi/1e6:.1f}M" if hi != float("inf") else f">={lo/1e6:.1f}M"
    print(f"  {label}: {cnt:,} ({100*cnt/len(prices_clean):.1f}%)")

print("\n--- Rating stats ---")
print(f"  count={len(ratings_clean):,}  min={min(ratings_clean):.1f}  median={median(ratings_clean):.1f}  max={max(ratings_clean):.1f}")

print("\n--- Quantity sold stats ---")
print(f"  count={len(sold_clean):,}  min={min(sold_clean):.0f}  median={median(sold_clean):.0f}  max={max(sold_clean):.0f}")

# ── discount analysis ────────────────────────────────────────
discounts = []
for item in data:
    g = parse_num(item.get("Giá gốc"))
    p = parse_num(item.get("Giá khuyến mãi"))
    if g and p and g > 0:
        discounts.append((g - p) / g * 100)
if discounts:
    print("\n--- Discount % stats ---")
    print(f"  count={len(discounts):,}  min={min(discounts):.1f}%  median={median(discounts):.1f}%  max={max(discounts):.1f}%")

# ── spec analysis ─────────────────────────────────────────────
spec_keys = Counter()
for item in data:
    spec = item.get("spec_product")
    if isinstance(spec, dict):
        for k in spec:
            spec_keys[k] += 1
    elif isinstance(spec, str) and spec.strip():
        spec_keys["_raw_string"] += 1

print("\n--- Spec keys coverage ---")
for k, v in spec_keys.most_common(15):
    print(f"  {k}: {v:,} ({100*v/len(data):.1f}%)")

# ── color analysis ────────────────────────────────────────────
color_counter = Counter()
for item in data:
    c = item.get("màu sắc")
    if c and isinstance(c, str) and c.strip():
        color_counter[c.strip()] += 1
print("\n--- Top colors ---")
for k, v in color_counter.most_common(10):
    print(f"  {k}: {v:,}")

# ── promotion / outstanding ───────────────────────────────────
promo_counter = Counter()
outstanding_counter = Counter()
for item in data:
    p = item.get("promotion")
    o = item.get("outstanding")
    if p and isinstance(p, str) and p.strip():
        promo_counter["has_promotion"] += 1
    if o and isinstance(o, str) and o.strip():
        outstanding_counter["has_outstanding"] += 1
print(f"\nHas promotion text: {promo_counter.get('has_promotion',0):,}")
print(f"Has outstanding text: {outstanding_counter.get('has_outstanding',0):,}")

# ── online only ───────────────────────────────────────────────
online = sum(1 for item in data if item.get("onlineSaleOnly"))
print(f"Online sale only: {online:,} ({100*online/len(data):.1f}%)")

# ── warranty ──────────────────────────────────────────────────
warranty_counter = Counter()
for item in data:
    w = item.get("chính sách bảo hành")
    if w and isinstance(w, str) and w.strip():
        warranty_counter["has_warranty"] += 1
print(f"Has warranty text: {warranty_counter.get('has_warranty',0):,}")

# ── accessories ───────────────────────────────────────────────
acc_counter = Counter()
for item in data:
    a = item.get("Phụ kiện đi kèm")
    if a and isinstance(a, str) and a.strip():
        acc_counter["has_accessories"] += 1
print(f"Has accessories text: {acc_counter.get('has_accessories',0):,}")

# ── sample rows ───────────────────────────────────────────────
print("\n--- Sample 5 rows ---")
for item in data[:5]:
    name = item.get("tên sản phẩm", "")[:60]
    print(f"  {name}")
    print(f"    cat={item.get('category_name')}  brand={item.get('brand')}  gross={item.get('Giá gốc')}  promo={item.get('Giá khuyến mãi')}  sold={item.get('quantity_sold')}  rating={item.get('rating_vote')}")

print("\nDone.")