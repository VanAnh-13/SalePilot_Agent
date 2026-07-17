#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "==> verify: imports + offline multi-agent smoke"

# shellcheck disable=SC1091
if [ -f backend/.venv/bin/activate ]; then
  source backend/.venv/bin/activate
fi

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
    ext = f"verify-refrigerator-{uuid.uuid4().hex[:10]}"
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
    assert "catalog" in agents or "tủ lạnh" in reply.lower() or "top 3" in reply.lower(), (
        f"expected refrigerator recommendation; agents={agents} reply={reply[:240]}"
    )
    assert "recommend" in str(tools) or "search" in str(tools) or "lít" in reply.lower(), (
        f"expected catalog content; tools={tools} reply={reply[:200]}"
    )
    assert "máy lạnh" not in reply.lower(), reply[:300]

    from app.agent.catalog_domain import (
        compare,
        extract_need_from_text,
        load_products,
        recommend_top3,
        reload_products,
        search,
    )
    reload_products()
    products = load_products()
    assert len(products) == 1692, len(products)
    assert all(p.get("category_code") == 38 for p in products)
    assert sum(bool(p.get("has_current_price")) for p in products) == 252
    need = extract_need_from_text("Gia đình 4 người dưới 15 triệu, ngăn đá dưới, ngang tối đa 70 cm, tiết kiệm điện")
    assert need.get("household_size") == 4 and need.get("max_width_cm") == 70, need
    rec = recommend_top3(need)
    assert rec.get("ok") and len(rec.get("top3") or []) == 3, rec
    assert all(
        x.get("price_vnd")
        and x["price_vnd"] <= 15_000_000
        and x.get("category_code") == 38
        and x.get("width_cm") <= 70
        for x in rec["top3"]
    ), rec
    no_budget_match = recommend_top3({"household_size": 4, "budget_vnd": 1_000_000})
    assert not no_budget_match.get("ok") and not no_budget_match.get("top3"), no_budget_match
    plain_need = extract_need_from_text("gia dinh 4 nguoi duoi 15 trieu, ngang 69.5 cm")
    assert plain_need.get("budget_vnd") == 15_000_000, plain_need
    assert plain_need.get("max_width_cm") == 69.5, plain_need
    water_results = search(
        query="external water dispenser",
        household_size=6,
        style="Side by Side",
        priced_only=True,
        limit=None,
    )
    assert water_results and all(x.get("external_water_dispenser") is True for x in water_results)
    equal_discount = [
        p["sku"]
        for p in products
        if p.get("original_price_vnd")
        and p.get("original_price_vnd") == p.get("sale_price_vnd")
    ][:2]
    assert len(equal_discount) == 2
    assert not any("(0đ)" in item for item in compare(equal_discount).get("tradeoffs", []))

    from scripts.import_refrigerators import _number

    assert _number("10.990.000") == 10_990_000
    assert _number("10,990,000") == 10_990_000
    assert _number("1.234,5 kg") == 1234.5
    print("OK refrigerator snapshot", len(products), "priced=252")
    print("OK recommend_top3", [x["sku"] for x in rec["top3"]])
    print("OK agents=", sorted(agents))
    print("OK tools=", tools)
    print("OK reply_snip=", reply[:160].replace("\n", " | "))
    print("OK run_id=", r.get("run_id"))
    print("OK memory_phone=", (r.get("memory") or {}).get("phone"))

    # sandbox
    from app.agent.sandbox.shell import run_sandbox_command

    s = await run_sandbox_command("date")
    assert s.get("ok") or s.get("stdout") is not None, s
    deny = await run_sandbox_command("rm -rf /")
    assert deny.get("ok") is False, deny
    print("OK sandbox allow/deny")

    # memory recall second turn
    r2 = await run_agent(
        "Mình cần tư vấn tủ lạnh tiếp",
        channel="web",
        external_id=ext,
        customer_name="Verify",
    )
    mem2 = r2.get("memory") or {}
    assert mem2.get("phone") == "0909999888" or "0909999888" in (r2.get("memory_summary") or ""), mem2
    print("OK memory persistence")

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


asyncio.run(main())
print("==> verify: PASS")
PY

python -m scripts.verify_mcp
