"""Generate visualizations for DMX product data — agent design insights."""
import json
from pathlib import Path
from collections import Counter
from statistics import median
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


# ── prep ──────────────────────────────────────────────────────
cats = Counter(item.get("category_name") for item in data if item.get("category_name"))
brands = Counter(item.get("brand") for item in data if item.get("brand"))
prices_clean = [parse_num(item.get("Giá khuyến mãi")) for item in data]
prices_clean = [p for p in prices_clean if p is not None]
gross_clean = [parse_num(item.get("Giá gốc")) for item in data]
gross_clean = [p for p in gross_clean if p is not None]
ratings_clean = [parse_num(item.get("rating_vote")) for item in data]
ratings_clean = [p for p in ratings_clean if p is not None]
sold_clean = [parse_num(item.get("quantity_sold")) for item in data]
sold_clean = [p for p in sold_clean if p is not None]

discounts = []
for item in data:
    g = parse_num(item.get("Giá gốc"))
    p = parse_num(item.get("Giá khuyến mãi"))
    if g and p and g > 0:
        discounts.append((g - p) / g * 100)

# ── matplotlib imports ────────────────────────────────────────
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "figure.dpi": 150,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
    "savefig.facecolor": "white",
})

COLORS = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
          "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]


def save(fig, name):
    fig.savefig(OUT_DIR / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  Saved: {name}")


# ── 1. Category treemap (bar chart) ───────────────────────────
fig, ax = plt.subplots(figsize=(14, 7))
top_cats = cats.most_common(15)
names = [c[0][:30] for c in top_cats]
counts = [c[1] for c in top_cats]
bars = ax.barh(range(len(names)), counts, color=COLORS * 2)
ax.set_yticks(range(len(names)))
ax.set_yticklabels(names, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("Số lượng sản phẩm")
ax.set_title("Top 15 danh mục sản phẩm — DMX")
for i, (c, n) in enumerate(zip(counts, names)):
    ax.text(c + 30, i, f"{c:,}", va="center", fontsize=8)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
fig.tight_layout()
save(fig, "01_categories.png")

# ── 2. Price distribution (log scale) ─────────────────────────
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

# log histogram
bins_log = np.logspace(np.log10(max(1, min(prices_clean))), np.log10(max(prices_clean)), 50)
ax1.hist(prices_clean, bins=bins_log, color=COLORS[0], edgecolor="white", alpha=0.85)
ax1.set_xscale("log")
ax1.set_xlabel("Giá khuyến mãi (VNĐ, log scale)")
ax1.set_ylabel("Số sản phẩm")
ax1.set_title("Phân bố giá — log scale")
ax1.axvline(median(prices_clean), color="red", linestyle="--", linewidth=1.5, label=f"Median = {median(prices_clean):,.0f}đ")
ax1.legend(fontsize=8)

#2, cumulative
sorted_prices = sorted(prices_clean)
cum_frac = np.arange(1, len(sorted_prices) + 1) / len(sorted_prices)
ax2.plot(sorted_prices, cum_frac * 100, color=COLORS[1], linewidth=2)
ax2.set_xscale("log")
ax2.set_xlabel("Giá khuyến mãi (VNĐ, log scale)")
ax2.set_ylabel("Tỷ lệ tích lũy (%)")
ax2.set_title("CDF giá sản phẩm")
ax2.axhline(50, color="red", linestyle="--", linewidth=1, alpha=0.6)
ax2.axvline(median(prices_clean), color="red", linestyle="--", linewidth=1, alpha=0.6)
ax2.grid(True, alpha=0.3)
fig.tight_layout()
save(fig, "2_price_distribution.png")

# ── 3. Rating distribution ────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
rating_bins = np.arange(2.0, 5.1, 0.1)
ax.hist(ratings_clean, bins=rating_bins, color=COLORS[2], edgecolor="white", alpha=0.85)
ax.set_xlabel("Rating (sao)")
ax.set_ylabel("Số sản phẩm")
ax.set_title("Phân bố rating sản phẩm")
ax.axvline(median(ratings_clean), color="red", linestyle="--", linewidth=1.5, label=f"Median = {median(ratings_clean):.1f}")
ax.legend(fontsize=9)
fig.tight_layout()
save(fig, "3_rating_distribution.png")

# ── 4. Sold distribution ──────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
ax.hist(sold_clean, bins=50, color=COLORS[3], edgecolor="white", alpha=0.85)
ax.set_xlabel("Số lượng đã bán")
ax.set_ylabel("Số sản phẩm")
ax.set_title("Phân bố quantity_sold")
ax.axvline(median(sold_clean), color="red", linestyle="--", linewidth=1.5, label=f"Median = {median(sold_clean):.0f}")
ax.legend(fontsize=9)
fig.tight_layout()
save(fig, "4_sold_distribution.png")

# ── 5. Discount distribution ──────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
ax.hist(discounts, bins=40, color=COLORS[4], edgecolor="white", alpha=0.85)
ax.set_xlabel("Mức giảm giá (%)")
ax.set_ylabel("Số sản phẩm")
ax.set_title("Phân bố mức giảm giá (Giá gốc → Giá khuyến mãi)")
ax.axvline(median(discounts), color="red", linestyle="--", linewidth=1.5, label=f"Median = {median(discounts):.1f}%")
ax.legend(fontsize=9)
fig.tight_layout()
save(fig, "5_discount_distribution.png")

# ── 6. Price vs Sold scatter ──────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 7))
pts = []
for item in data:
    p = parse_num(item.get("Giá khuyến mãi"))
    s = parse_num(item.get("quantity_sold"))
    if p and s and p > 0:
        pts.append((p, s))
px = [t[0] for t in pts]
py = [t[1] for t in pts]
ax.scatter(px, py, s=3, alpha=0.3, c=COLORS[0])
ax.set_xscale("log")
ax.set_xlabel("Giá khuyến mãi (VNĐ, log scale)")
ax.set_ylabel("Số lượng đã bán")
ax.set_title("Giá vs Số lượng bán (scatter)")
ax.grid(True, alpha=0.3)
fig.tight_layout()
save(fig, "6_price_vs_sold.png")

# ── 7. Category × median price ────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 7))
cat_price = {}
for item in data:
    c = item.get("category_name")
    p = parse_num(item.get("Giá khuyến mãi"))
    if c and p:
        cat_price.setdefault(c, []).append(p)
cat_med = [(c, median(ps)) for c, ps in cat_price.items() if len(ps) >= 10]
cat_med.sort(key=lambda x: -x[1])
top_cat_med = cat_med[:20]
names2 = [c[0][:30] for c in top_cat_med]
meds = [c[1] for c in top_cat_med]
bars = ax.barh(range(len(meds)), meds, color=COLORS[:len(meds)])
ax.set_yticks(range(len(names2)))
ax.set_yticklabels(names2, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("Median giá khuyến mãi (VNĐ)")
ax.set_title("Top 20 danh mục theo median giá")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
for i, v in enumerate(meds):
    ax.text(v + 500_000, i, f"{v:,.0f}đ", va="center", fontsize=7)
fig.tight_layout()
save(fig, "7_category_median_price.png")

# ── 8. Spec coverage heatmap-style bar ────────────────────────
fig, ax = plt.subplots(figsize=(12, 6))
spec_keys = Counter()
for item in data:
    spec = item.get("spec_product")
    if isinstance(spec, dict):
        for k in spec:
            spec_keys[k] += 1
top_specs = spec_keys.most_common(20)
snames = [s[0][:35] for s in top_specs]
scounts = [s[1] for s in top_specs]
bars = ax.barh(range(len(scounts)), scounts, color=COLORS[:len(scounts)])
ax.set_yticks(range(len(snames)))
ax.set_yticklabels(snames, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("Số sản phẩm có spec này")
ax.set_title("Top 20 spec keys — độ phủ dữ liệu kỹ thuật")
for i, v in enumerate(scounts):
    ax.text(v + 30, i, f"{v:,} ({100*v/len(data):.0f}%)", va="center", fontsize=7)
fig.tight_layout()
save(fig, "8_spec_coverage.png")

# ── 9. Brand concentration ────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 6))
top_brands = brands.most_common(20)
bnames = [b[0][:25] for b in top_brands]
bcounts = [b[1] for b in top_brands]
bars = ax.barh(range(len(bcounts)), bcounts, color=COLORS[:len(bcounts)])
ax.set_yticks(range(len(bnames)))
ax.set_yticklabels(bnames, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("Số sản phẩm")
ax.set_title("Top 20 thương hiệu")
for i, v in enumerate(bcounts):
    ax.text(v + 5, i, f"{v:,}", va="center", fontsize=8)
fig.tight_layout()
save(fig, "9_brands.png")

# ── 10. Data completeness radar ───────────────────────────────
fig, ax = plt.subplots(figsize=(8, 6))
fields = [
    ("Giá khuyến mãi", len(prices_clean)),
    ("Giá gốc", len(gross_clean)),
    ("Rating", len(ratings_clean)),
    ("Quantity sold", len(sold_clean)),
    ("Brand", sum(1 for item in data if item.get("brand"))),
    ("Category", sum(1 for item in data if item.get("category_name"))),
    ("Spec (dict)", sum(1 for item in data if isinstance(item.get("spec_product"), dict))),
    ("Màu sắc", sum(1 for item in data if item.get("màu sắc") and str(item.get("màu sắc")).strip())),
    ("Promotion text", sum(1 for item in data if item.get("promotion") and str(item.get("promotion")).strip())),
    ("Outstanding", sum(1 for item in data if item.get("outstanding") and str(item.get("outstanding")).strip())),
    ("Bảo hành", sum(1 for item in data if item.get("chính sách bảo hành") and str(item.get("chính sách bảo hành")).strip())),
    ("Phụ kiện", sum(1 for item in data if item.get("Phụ kiện đi kèm") and str(item.get("Phụ kiện đi kèm")).strip())),
]
fnames = [f[0] for f in fields]
fvals = [100 * f[1] / len(data) for f in fields]
bars = ax.barh(range(len(fvals)), fvals, color=COLORS[:len(fvals)])
ax.set_yticks(range(len(fnames)))
ax.set_yticklabels(fnames, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("% sản phẩm có dữ liệu")
ax.set_title("Data completeness — độ đầy đủ từng trường")
for i, v in enumerate(fvals):
    ax.text(v + 0.5, i, f"{v:.0f}%", va="center", fontsize=8)
ax.set_xlim(0, 110)
fig.tight_layout()
save(fig, "10_data_completeness.png")

print("\nAll charts saved to:", OUT_DIR)
print("Done.")