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

from app.agent.graph import run_agent
from app.db.session import init_db


async def main() -> None:
    await init_db()
    ext = "verify-script"
    r = await run_agent(
        "Phòng ngủ 12m2, dưới 10 triệu, muốn êm và tiết kiệm điện. SĐT 0909999888",
        channel="web",
        external_id=ext,
        customer_name="Verify",
    )
    agents = set(r.get("used_agents") or [])
    tools = r.get("used_tools") or []
    reply = r.get("reply") or ""
    assert "lead" in agents, f"expected lead in {agents}"
    assert "catalog" in agents or "AC-" in reply or "máy lạnh" in reply.lower() or "top 3" in reply.lower(), (
        f"expected AC recommend; agents={agents} reply={reply[:240]}"
    )
    assert "AC-" in reply or "recommend" in str(tools) or "search" in str(tools) or "triệu" in reply.lower(), (
        f"expected catalog content; tools={tools} reply={reply[:200]}"
    )

    from app.agent.catalog_domain import recommend_top3, extract_need_from_text, reload_products
    reload_products()
    need = extract_need_from_text("Phòng 12m2 dưới 10 triệu êm tiết kiệm điện")
    rec = recommend_top3(need)
    assert rec.get("ok") and len(rec.get("top3") or []) >= 1, rec
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
        "Mình cần tư vấn tiếp",
        channel="web",
        external_id=ext,
        customer_name="Verify",
    )
    mem2 = r2.get("memory") or {}
    assert mem2.get("phone") == "0909999888" or "0909999888" in (r2.get("memory_summary") or ""), mem2
    print("OK memory persistence")


asyncio.run(main())
print("==> verify: PASS")
PY
