#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Baseline smoke must be deterministic and work without database credentials.
export CATALOG_BACKEND=snapshot
export CATALOG_SNAPSHOT="$ROOT_DIR/experiments/fixtures/catalog_dev_fixture.json"
export SALEPILOT_CATALOG_REGISTRY=workbook
# shellcheck disable=SC1091
# Support both POSIX venvs (Linux/Mac/Docker: .venv/bin/activate) and Windows
# venvs (.venv/Scripts/activate) — python -m venv lays these out differently
# per platform, and this script must work on both (2026-08-01: previously
# only checked bin/activate, so it silently fell through to system Python on
# Windows and failed with ModuleNotFoundError instead of using backend/.venv).
if [ -f backend/.venv/bin/activate ]; then
  source backend/.venv/bin/activate
elif [ -f backend/.venv/Scripts/activate ]; then
  source backend/.venv/Scripts/activate
fi

# Use Python's own tempfile/pathlib (not bash mktemp -d) to create the temp
# dir: on Windows under git-bash, `mktemp -d` returns an MSYS-virtual POSIX
# path (e.g. /tmp/tmp.XXXX) that native-Windows Python/sqlite3 cannot open,
# causing "unable to open database file" (2026-08-01). tempfile.mkdtemp()
# always returns a path the SAME interpreter can use, and Path.as_posix()
# renders it with forward slashes that both bash and SQLAlchemy's sqlite URL
# parser accept on either platform (3 slashes + drive letter on Windows, 4
# slashes for an absolute Unix path).
VERIFY_TMP_DIR="$(python -c "import tempfile; from pathlib import Path; print(Path(tempfile.mkdtemp()).as_posix())")"
trap 'rm -rf "$VERIFY_TMP_DIR"' EXIT
export DATABASE_URL="sqlite+aiosqlite:///$VERIFY_TMP_DIR/verify.db"

echo "==> verify: imports + offline multi-agent smoke (multi-category catalog)"

cd "$ROOT_DIR/backend"
mkdir -p data

python - <<'PY'
import asyncio
import json
import uuid

from app.agent.graph import run_agent
from app.db.session import init_db


async def main() -> None:
    await init_db()

    # ---------------- Catalog: pinned engineering fixture ----------------
    from app.catalog import repository
    from app.agent.catalog_domain import (
        compare,
        extract_need_from_text,
        recommend_top3,
        search,
    )

    count = repository.reload()
    counts = repository.category_counts()
    assert count == 70, count
    assert len(counts) == 14, sorted(counts)
    assert counts["tu_lanh"]["total"] == 5 and counts["tu_lanh"]["priced"] == 5, counts["tu_lanh"]
    assert counts["may_lanh"]["total"] == 5, counts["may_lanh"]
    print(f"OK catalog source={repository.source()} products={count} categories={len(counts)}")

    # ---------------- Refrigerator deep rules (regression) ----------------
    need = extract_need_from_text(
        "Gia đình 4 người dưới 15 triệu, ngăn đá dưới, ngang tối đa 70 cm, tiết kiệm điện"
    )
    assert need.get("category") == "tu_lanh", need
    assert need.get("household_size") == 4 and need.get("max_width_cm") == 70, need
    assert need.get("budget_vnd") == 15_000_000, need
    assert "tiet_kiem_dien" in need.get("priority", []), need
    rec = recommend_top3(need)
    assert rec.get("ok") and len(rec.get("top3") or []) == 3, rec
    assert all(
        x.get("price_vnd")
        and x["price_vnd"] <= 15_000_000
        and x.get("category_code") == 38
        and x.get("width_cm") <= 70
        for x in rec["top3"]
    ), rec["top3"]
    no_budget_match = recommend_top3({"category": "tu_lanh", "household_size": 4, "budget_vnd": 1_000_000})
    assert not no_budget_match.get("ok") and not no_budget_match.get("top3"), no_budget_match
    plain_need = extract_need_from_text("gia dinh 4 nguoi duoi 15 trieu, tu lanh ngang 69.5 cm")
    assert plain_need.get("budget_vnd") == 15_000_000, plain_need
    assert plain_need.get("max_width_cm") == 69.5, plain_need
    ask = recommend_top3({"category": "tu_lanh"})
    assert ask.get("need_more") and ask.get("ask"), ask
    scoped = search(query="fixture", category="tu_lanh", priced_only=True, limit=5)
    assert scoped and all(x.get("category_code") == 38 for x in scoped), scoped[:2]
    print("OK refrigerator rules", [x["sku"] for x in rec["top3"]])

    # ---------------- Per-category deep rules ----------------
    ac = recommend_top3(extract_need_from_text("Cần máy lạnh cho phòng 20m2, tầm 12 triệu, chạy êm, inverter"))
    assert ac.get("ok") and ac.get("category") == "may_lanh", ac.get("category")
    assert all(x["price_vnd"] <= 12_000_000 for x in ac["top3"]), ac["top3"]
    assert all(
        x.get("area_min") is None or (x["area_min"] <= 20 and (x.get("area_max") or 99) >= 20)
        for x in ac["top3"]
    ), ac["top3"]

    washer = recommend_top3(extract_need_from_text("Nhà 5 người cần máy giặt cửa trước 9kg dưới 15 triệu có sấy"))
    assert washer.get("ok") and washer.get("category") == "may_giat", washer.get("category")

    watch = recommend_top3(extract_need_from_text("Đồng hồ thông minh dưới 3 triệu, nghe gọi, theo dõi sức khỏe"))
    assert watch.get("ok") and watch.get("category") == "dong_ho", watch.get("category")
    assert all(x.get("has_call") for x in watch["top3"]), watch["top3"]

    tablet = recommend_top3(extract_need_from_text("Máy tính bảng dưới 8 triệu, pin trâu, có lắp sim"))
    assert tablet.get("ok") and tablet.get("category") == "may_tinh_bang", tablet.get("category")
    assert all(x.get("has_sim") for x in tablet["top3"]), tablet["top3"]

    heater = recommend_top3(extract_need_from_text("Máy nước nóng trực tiếp dưới 3 triệu"))
    assert heater.get("ok") and heater.get("category") == "may_nuoc_nong", heater.get("category")

    # compare stays inside one category and yields trade-offs
    cmp_result = compare([x["sku"] for x in ac["top3"][:2]])
    assert cmp_result.get("ok") and cmp_result.get("tradeoffs"), cmp_result
    assert not any("(0đ)" in item for item in cmp_result.get("tradeoffs", []))
    print("OK per-category rules: may_lanh, may_giat, dong_ho, may_tinh_bang, may_nuoc_nong")

    # ---------------- Offline multi-agent flow ----------------
    ext = f"verify-catalog-{uuid.uuid4().hex[:10]}"
    r = await run_agent(
        "Gia đình 4 người, dưới 15 triệu, cần tủ lạnh inverter ngăn đá dưới, ngang tối đa 70 cm. SĐT 0909999888",
        channel="web",
        external_id=ext,
        customer_name="Verify",
    )
    agents = set(r.get("used_agents") or [])
    tools = r.get("used_tools") or []
    reply = r.get("reply") or ""
    assert "lead" in agents, f"expected lead in {agents}"
    assert "catalog" in agents, f"expected catalog in {agents}"
    assert "recommend" in str(tools) or "search" in str(tools), tools
    assert "máy lạnh" not in reply.lower(), reply[:300]
    print("OK agents=", sorted(agents))
    print("OK reply_snip=", reply[:160].replace("\n", " | "))
    print("OK run_id=", r.get("run_id"))

    ac_run = await run_agent(
        "Cần máy lạnh cho phòng 20m2 tầm 12 triệu, chạy êm",
        channel="web",
        external_id=f"verify-ac-{uuid.uuid4().hex[:10]}",
        customer_name="Verify",
    )
    assert "catalog" in set(ac_run.get("used_agents") or []), ac_run.get("used_agents")
    assert "máy lạnh" in (ac_run.get("reply") or "").lower(), ac_run.get("reply", "")[:200]
    print("OK offline multi-category chat (may_lanh)")

    # Multi-turn need accumulation: follow-up budget answer keeps PC context.
    follow_ext = f"verify-followup-{uuid.uuid4().hex[:10]}"
    turn1 = await run_agent("tôi muốn mua 1 chiếc PC", channel="web", external_id=follow_ext)
    assert "ngân sách" in (turn1.get("reply") or "").lower(), turn1.get("reply", "")[:200]
    turn2 = await run_agent("giá khoảng 10tr", channel="web", external_id=follow_ext)
    assert "ram" in (turn2.get("reply") or "").lower(), turn2.get("reply", "")[:300]
    turn3 = await run_agent("RAM 16 GB", channel="web", external_id=follow_ext)
    reply3 = (turn3.get("reply") or "").lower()
    assert "máy tính để bàn" in reply3 and "top 3" in reply3, turn3.get("reply", "")[:300]
    turn4 = await run_agent("còn màn hình thì sao, 27 inch", channel="web", external_id=follow_ext)
    assert "màn hình" in (turn4.get("reply") or "").lower(), turn4.get("reply", "")[:300]
    print("OK multi-turn need accumulation (PC → budget → RAM → switch to monitor)")

    # Guardrail: unsupported product (laptop) must not default to fridge; negation respected.
    from app.agent.catalog_domain import detect_category, detect_negated_categories

    assert detect_category("lap tôi ko phải tủ lạnh") is None
    assert "tu_lanh" in detect_negated_categories("lap tôi ko phải tủ lạnh")
    switch_cat = detect_category("không phải tủ lạnh, tôi cần máy giặt")
    assert switch_cat and switch_cat.slug == "may_giat", switch_cat
    no_cat_ask = recommend_top3({"budget_vnd": 20_000_000})
    assert no_cat_ask.get("need_more") and "nhóm hàng nào" in no_cat_ask["ask"][0], no_cat_ask
    lap_ext = f"verify-laptop-{uuid.uuid4().hex[:10]}"
    lap_run = await run_agent(
        "tư vấn cho tôi 1 cái laptop giá khoảng 20tr", channel="web", external_id=lap_ext
    )
    lap_reply = lap_run.get("reply") or ""
    assert "chưa có ngành hàng laptop" in lap_reply, lap_reply[:200]
    assert "tủ lạnh sát nhu cầu" not in lap_reply, lap_reply[:200]
    print("OK unsupported guardrail (laptop) + negation handling")

    # ---------------- Sandbox ----------------
    # Sandbox is safe-by-default (sandbox_enabled=False): the smoke test
    # opts in explicitly, mirroring how a deployment would enable it.
    import os as _os

    _os.environ["SANDBOX_ENABLED"] = "true"
    from app.config import get_settings as _gs

    _gs.cache_clear()
    from app.agent.sandbox.shell import run_sandbox_command

    s = await run_sandbox_command("date")
    assert s.get("ok") or s.get("stdout") is not None, s
    deny = await run_sandbox_command("rm -rf /")
    assert deny.get("ok") is False, deny
    _os.environ.pop("SANDBOX_ENABLED", None)
    _gs.cache_clear()
    print("OK sandbox allow/deny")

    # ---------------- Memory ----------------
    r2 = await run_agent(
        "Mình cần tư vấn tủ lạnh tiếp",
        channel="web",
        external_id=ext,
        customer_name="Verify",
    )
    mem2 = r2.get("memory") or {}
    assert mem2.get("phone") == "0909999888" or "0909999888" in (r2.get("memory_summary") or ""), mem2
    print("OK memory persistence")

    # ---------------- Stock guardrail + order validation ----------------
    from app.agent.offline import run_offline_multi_agent
    from app.agent.tools.order import create_order_draft

    stock_reply = await run_offline_multi_agent(
        "Bảng có biết tủ lạnh còn hàng không?",
        channel="web",
        external_id=f"verify-stock-{uuid.uuid4().hex[:10]}",
    )
    assert "knowledge" in (stock_reply.get("used_agents") or []), stock_reply
    assert "tồn kho" in (stock_reply.get("reply") or "").lower(), stock_reply
    invalid_item = json.loads(await create_order_draft.ainvoke({"items_json": "[null]"}))
    invalid_qty = json.loads(
        await create_order_draft.ainvoke(
            {"items_json": json.dumps([{"sku": rec["top3"][0]["sku"], "qty": 11}])}
        )
    )
    assert invalid_item.get("error") and invalid_qty.get("error")
    print("OK stock FAQ routing + order validation")

    # ---------------- Importer number parsing ----------------
    from app.catalog import normalize as N

    assert N.number("10.990.000") == 10_990_000
    assert N.number("10,990,000") == 10_990_000
    assert N.number("1.234,5 kg") == 1234.5
    assert N.area_range("Từ 30 - 40m² (từ 80 đến 120m³)") == (30, 40)
    assert N.area_range("Dưới 15m² (từ 30 đến 45m³)") == (None, 15)
    assert N.people_range("Trên 5 người") == (6, None)
    print("OK normalize helpers")


asyncio.run(main())
print("==> verify: PASS")
PY

python -m scripts.verify_mcp
