# Dataset Card — SalePilot-R (RIVF Track 2)

Last updated: 2026-08-01  
Gate status: **READY** — primary experiment uses the DMX snapshot (13,716 products / 118 categories, hash-pinned in `experiments/manifest.json`). Engineering fixture (70 SKU / 14 categories) is **dev/pilot only** and must not be used for sealed claims. Production DMX catalog hosted in Neon Postgres.


## Motivation

Support a constraint-first Vietnamese retail decision-support evaluation on an
owner-authorized multi-category appliance/electronics catalog crawl.

## Canonical catalog decision

| Field | Value |
|---|---|
| Chosen source family | DMX crawl (`products_detail.xlsx`) |
| Owner confirmation (publication) | Confirmed 2026-07-25 (replace missing `Spec_cate_gia.xlsx`) |
| File present in workspace | Staged as repo-root `products_detail.xlsx` (gitignored) |
| Expected path | `products_detail.xlsx` |
| Raw source hash | `39a03b0390673f102ef69335f9594f06ad4b0eb13d8e9c00fd5e33f833f35666` (confirmed in `experiments/manifest.json`, re-verified 2026-08-01) |
| Normalized catalog hash | `e2afdf38ed2df5599611e6f8285643f727e2c06c721b1a055b7baeea797df15c` (confirmed in `experiments/manifest.json`, re-verified 2026-08-01) |
| Schema version | `salepilot-catalog-v1` |
| Experiment backend | `snapshot` |
| Category registry | crawl registry |

## Asset-level rights matrix

| Asset | Path / origin | Research use | Derivative release | Status |
|---|---|---|---|---|
| Catalog source | `products_detail.xlsx` (from `C:\Downloads\DMX_product\`) | Owner-confirmed for RIVF paper use | Derived labels/results only; raw xlsx not committed | owner_confirmed_publication |
| Research snapshot | `backend/data/research/catalog_dmx_snapshot.json` | Canonical experiment catalog | Aggregates/hashes; snapshot gitignored | derived_ready after import |
| Engineering fixture | `experiments/fixtures/catalog_dev_fixture.json` | Dev/pilot only; not publication source | May publish fixture | available_local |
| Policy corpus | `backend/data/policies/*`, `backend/data/faq.json` | Stock/policy guardrail evaluation | Summaries/metrics only | owner_confirmed_publication |
| Need scenarios seed | `backend/data/need_scenarios.json` | Dev inspiration only | Synthetic rewrites OK | available_local |
| Legacy workbook path | `Spec_cate_gia.xlsx` | Superseded; do not use for sealed claims | N/A | retired_missing |
| Trajectories / CRM / memory | runtime DB | Not research data | Never publish raw | excluded |

## PII policy

- No real customer identifiers in benchmark episodes
- Experiment exports must redact phone/email patterns
- Raw trajectories, conversations, leads, and memory are excluded from research release
- Public artifacts may include code, manifests, aggregates, and hashes only

## Missingness and known limitations

- Source has no realtime stock column; systems must abstain from availability claims
- Prices/promotions are snapshot-time only
- Category coverage claims must match the normalized DMX catalog actually imported
- Fixture pilot metrics (70 SKU) are engineering-only and must not be reported as sealed results
- Public deployment health is independent of catalog readiness

## Unlock criteria for Checkpoint A

- [x] Stage authorized `products_detail.xlsx` at repo root
- [x] Run `cd backend && python -m scripts.import_dmx_research --snapshot-only --confirm-publication-rights`
- [x] Confirm `raw_source_hash` and `normalized_catalog_hash` in `experiments/manifest.json` — both present, see table above
- [x] `python scripts/validate_research_manifest.py experiments/manifest.json` exits 0 (strict) — re-verified 2026-08-01: `OK research manifest status=ready allow_blocked=False`

Checkpoint A is satisfied as of 2026-08-01; the "Gate status: READY" line at the top of this card is backed by the four checks above.

## Contact / custody

- Data custodian: project owner
- Research protocol owner: implementation agent + project owner
- Seal/release authority: project owner
