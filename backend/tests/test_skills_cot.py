"""Cross-tests for the CoT skill guidance.

Two goals:
  (1) Well-formedness — every SKILL.md parses, targets only real agents/tools,
      fits the injection cap, and no longer carries the stale refrigerator-only /
      "delegate → catalog" guidance that predates the flattened tool surface.
  (2) Grounding — the deterministic engine behaves the way the CoT scripts tell
      the agent it will (ask-back when a slot/budget is missing; top-3 when the
      need is complete; out-of-scope detection; comparison). This keeps the
      agent's reasoning aligned with what actually happens at runtime.

Run inside the backend container (needs langgraph deps + PostgreSQL):
    docker compose exec -T backend python -m tests.test_skills_cot
Also importable by pytest (each test_* is arg-less and self-contained).
"""

from __future__ import annotations

import re

from app.agent.catalog_domain import compare, extract_need_from_text, recommend_top3
from app.agent.skills.loader import list_skills
from app.catalog import repository
from app.catalog.crawl_categories import detect_category, detect_unsupported

# The agent surface the CoT scripts are allowed to reference.
VALID_AGENTS = {"lead", "catalog", "knowledge", "crm", "order", "escalation"}
# delegate() now targets ONLY these sub-agents (catalog/knowledge are direct).
VALID_DELEGATE_TARGETS = {"crm", "order", "escalation"}
# Lead-injected body cap: lead_node injects body[:6000], so longer bodies get
# silently truncated mid-CoT.
BODY_CAP = 6000
DEEP_CATEGORY_NAMES = ["điện thoại", "laptop", "tivi", "tai nghe", "máy lạnh", "tủ lạnh", "máy giặt", "máy hút bụi"]


# --------------------------------------------------------------------------- #
# Group 1 — well-formedness of the CoT skills
# --------------------------------------------------------------------------- #

def test_skills_parse_and_have_frontmatter():
    skills = list_skills()
    assert len(skills) >= 5, f"expected ≥5 skills, got {len(skills)}"
    for s in skills:
        assert s.name, f"skill missing name: {s.path}"
        assert s.description, f"skill '{s.name}' missing description"
        assert s.body.strip(), f"skill '{s.name}' has empty body"


def test_agents_are_valid():
    for s in list_skills():
        assert s.agents, f"skill '{s.name}' declares no agents"
        for a in s.agents:
            assert a in VALID_AGENTS, f"skill '{s.name}' references unknown agent '{a}'"


def test_body_within_injection_cap():
    for s in list_skills():
        assert len(s.body) <= BODY_CAP, (
            f"skill '{s.name}' body is {len(s.body)} chars (> {BODY_CAP}); "
            f"it will be truncated mid-CoT when injected"
        )


def test_no_stale_delegate_to_catalog_or_knowledge():
    # catalog/knowledge are now called directly by the lead — the CoT must not
    # tell the agent to delegate to them (the old refrigerator skills did).
    for s in list_skills():
        low = s.body.lower()
        assert "→ catalog" not in low, f"skill '{s.name}' still delegates → catalog"
        assert "→ knowledge" not in low, f"skill '{s.name}' still delegates → knowledge"
        assert 'delegate("catalog"' not in low, f"skill '{s.name}' delegates to catalog"
        assert 'delegate("knowledge"' not in low, f"skill '{s.name}' delegates to knowledge"
        # delegate_many was removed from the lead tool surface.
        assert "delegate_many" not in low, f"skill '{s.name}' references removed delegate_many"


def test_delegate_targets_are_valid():
    pat = re.compile(r'delegate\(\s*["\']([a-z_]+)["\']')
    for s in list_skills():
        for target in pat.findall(s.body):
            assert target in VALID_DELEGATE_TARGETS, (
                f"skill '{s.name}' delegates to '{target}' (only {VALID_DELEGATE_TARGETS} allowed)"
            )


def test_skills_are_multi_category_not_fridge_only():
    corpus = " ".join(s.body.lower() for s in list_skills())
    mentioned = [c for c in DEEP_CATEGORY_NAMES if c in corpus]
    assert len(mentioned) >= 4, (
        f"CoT skills look fridge-centric; only mention {mentioned}. "
        f"Guidance should span multiple categories."
    )


# --------------------------------------------------------------------------- #
# Group 2 — the CoT decision points match the real engine behaviour
# --------------------------------------------------------------------------- #

# Each scenario encodes a decision the CoT scripts prescribe.
_SCENARIOS = [
    # msg, category, need_more, must_have_priorities, note
    ("tủ lạnh gia đình 4 người dưới 15 triệu tiết kiệm điện", "tu_lanh", False, ["tiet_kiem_dien"]),
    ("cần máy lạnh tầm 12 triệu", "may_lanh", True, []),                 # missing area (primary slot) → ask-back
    ("tư vấn điện thoại chơi game", "dien_thoai", True, []),             # missing budget → ask-back
    ("điện thoại chơi game pin trâu dưới 12 triệu", "dien_thoai", False, ["pin_trau", "choi_game"]),
    ("laptop văn phòng dưới 15 triệu", "laptop", False, []),
    ("tivi 55 inch 4k dưới 20 triệu", "tivi", False, []),
    ("máy giặt cửa trước 9kg dưới 12 triệu", "may_giat", False, []),
    ("nồi cơm điện gia đình 4 người dưới 2 triệu", "noi_com_dien", False, []),  # generic category still works
]


def test_cot_scenarios_route_and_recommend():
    repository.load()
    for msg, cat, need_more, must_prios in _SCENARIOS:
        need = extract_need_from_text(msg)
        assert need.get("category") == cat, (
            f"[{msg}] expected category={cat}, got {need.get('category')}"
        )
        for p in must_prios:
            assert p in (need.get("priority") or []), f"[{msg}] expected priority '{p}' in {need.get('priority')}"

        rec = recommend_top3(need)
        assert bool(rec.get("need_more")) == need_more, (
            f"[{msg}] expected need_more={need_more}, got {rec.get('need_more')} (ask={rec.get('ask')})"
        )
        if need_more:
            assert rec.get("ask"), f"[{msg}] need_more but no clarifying question provided"
        else:
            assert len(rec.get("top3") or []) >= 1, f"[{msg}] complete need but no top3 returned"


def test_may_lanh_askback_mentions_area():
    # need_discovery CoT says máy lạnh's primary slot is room area (m²).
    rec = recommend_top3(extract_need_from_text("cần máy lạnh tầm 12 triệu"))
    assert rec.get("need_more") is True
    joined = " ".join(rec.get("ask") or [])
    assert "m²" in joined or "m2" in joined, f"máy lạnh ask-back should request area; got {rec.get('ask')}"


def test_out_of_scope_is_detected():
    # handoff / honesty: things the catalog does not carry must be flagged, not
    # forced into a wrong category.
    msg = "tư vấn mua xe máy tay ga dưới 40 triệu"
    assert detect_category(msg) is None, "xe máy should not map to a product category"
    assert detect_unsupported(msg) is not None, "xe máy should be flagged out-of-scope"


def test_compare_two_skus_same_category():
    # compare_products CoT: pick ≥2 SKUs in one category and compare with trade-offs.
    repository.load()
    docs = repository.by_category("tu_lanh")
    assert len(docs) >= 2, "need ≥2 tủ lạnh SKUs to test comparison"
    skus = [str(d["sku"]) for d in docs[:2]]
    res = compare(skus)
    assert res.get("ok") is True, f"compare failed: {res.get('error')}"
    assert len(res.get("items") or []) == 2
    assert res.get("tradeoffs"), "comparison should produce trade-off lines"


# --------------------------------------------------------------------------- #
# Group 3 — the requirement-specific skills exist and the engine backs their claims
# --------------------------------------------------------------------------- #

def test_requirement_skills_present():
    names = {s.name for s in list_skills()}
    for required in ("advisory_playbook", "explain_specs_plainly", "grounding_guardrail", "vietnamese_input"):
        assert required in names, f"missing requirement-critical skill '{required}'"


def test_i1_aircon_flagship_example():
    # The exact ideal-solution example from requirements.md I1.
    repository.load()
    need = extract_need_from_text("máy lạnh dưới 20 triệu cho phòng 18m² tiết kiệm điện, ít ồn")
    assert need.get("category") == "may_lanh"
    assert need.get("budget_vnd") == 20_000_000
    assert need.get("area_m2") in (18, 18.0), f"expected area 18m², got {need.get('area_m2')}"
    for p in ("tiet_kiem_dien", "chay_em"):
        assert p in (need.get("priority") or []), f"expected priority '{p}'"
    rec = recommend_top3(need)
    assert not rec.get("need_more") and (rec.get("top3") or []), "complete need → should return top3"


def test_no_fabrication_on_impossible_budget():
    # Anti-hallucination: an impossible budget must NOT yield a fabricated top-3.
    repository.load()
    rec = recommend_top3(extract_need_from_text("tủ lạnh gia đình 4 người dưới 500 nghìn"))
    assert not (rec.get("ok") and rec.get("top3")), (
        "engine should not fabricate a match under an impossible budget"
    )
    # Honest response: either ask for more, or an explicit no-match message.
    assert rec.get("need_more") or rec.get("message"), "should respond honestly, not fabricate"


def test_recommend_disclaimer_mentions_stock():
    # grounding_guardrail: results must carry the no-realtime-stock disclaimer.
    repository.load()
    rec = recommend_top3(extract_need_from_text("tủ lạnh gia đình 4 người dưới 15 triệu"))
    assert "tồn kho" in (rec.get("disclaimer") or ""), f"disclaimer should mention tồn kho: {rec.get('disclaimer')}"


def test_vietnamese_no_diacritics_and_abbrev():
    # vietnamese_input: no-diacritics + "12tr" + "18m2" must still be understood.
    need = extract_need_from_text("can mua may lanh phong ngu 18m2 tam 12tr chay em")
    assert need.get("category") == "may_lanh", f"got {need.get('category')}"
    assert need.get("budget_vnd") == 12_000_000, f"got {need.get('budget_vnd')}"
    assert need.get("area_m2") in (18, 18.0), f"got {need.get('area_m2')}"


# --------------------------------------------------------------------------- #
# Standalone runner (no pytest dependency)
# --------------------------------------------------------------------------- #

def _run() -> int:
    tests = sorted(
        (name, fn) for name, fn in globals().items()
        if name.startswith("test_") and callable(fn)
    )
    passed = failed = 0
    print(f"Running {len(tests)} cross-tests for CoT skills\n" + "=" * 52)
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {name}\n        {e}")
            failed += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ERROR {name}: {type(e).__name__}: {e}")
            failed += 1
    print("=" * 52)
    print(f"  {passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run())
