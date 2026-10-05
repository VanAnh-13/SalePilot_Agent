# Spec: RIVF 2026 Track 2 — Scope A + Deployment Evidence

Status: confirmed by owner (2026-07-25)  
Deadline: **2026-08-31** (extended per CFP update at rivf2026.org; was 2026-07-31)  
Active feature: `rivf-001`

## Objective

Produce a reproducible IEEE-RIVF Track 2 submission for SalePilot as a
**constraint-first grounded decision-support system** with:

1. Canonical DMX catalog evidence chain
2. Sealed experiment results for B0 / B1 / S_hybrid + one pinned B2 LLM condition
3. Public deployment smoke + latency evidence on owner-operated URLs
4. IEEE A4 ≤6-page paper whose claims trace only to frozen artifacts

## Confirmed intent

| Field | Value |
|---|---|
| Outcome | Track 2 package with auditable evidence chain |
| Users | RIVF reviewers; public SalePilot demo users |
| Why now | Submission target 2026-08-31 (extended per CFP update) |
| Success | Manifest ready; sealed DMX results; public health+chat smoke; paper claims match artifacts |
| Constraint | `C:\Downloads\DMX_product\products_detail.xlsx` is canonical source |
| Deployment | Reuse `sale-pilot-agent.vercel.app` + `optivisionlab.fit-haui.edu.vn`; owner deploys manually |
| B2 | Provider-agnostic runner; each sealed report pins exactly one provider/model |
| Out of scope | Evidence-first UI (Task 10), human study (Task 11), multi-provider comparison tables |

## Canonical data contract

| Field | Value |
|---|---|
| Source family | `dmx_crawl_products_detail` |
| Canonical raw source | repo-relative `products_detail.xlsx` (gitignored; staged from owner Downloads pack) |
| Companion JSON | optional engineering aid only; not publication hash source |
| Research snapshot | `backend/data/research/catalog_dmx_snapshot.json` |
| Experiment backend | `snapshot` |
| Registry | crawl registry (`SALEPILOT_CATALOG_REGISTRY=crawl`) |
| Rights | `owner_confirmed_publication` (owner confirmed 2026-07-25) |

## Conditions

Required primary sealed comparison:

- `B0_price_popularity`
- `B1_lexical_filter`
- `S_hybrid_constraint`
- `B2_llm_single_agent` — **removed from custody 2026-08-01**: prediction file contained wrong provider, repeat=0 (spec requires ≥3). B2 excluded from paper primary comparison.

Human study gate: **disabled**.

## Public deployment contract

| Role | URL |
|---|---|
| Frontend | `https://sale-pilot-agent.vercel.app` |
| Backend | `https://optivisionlab.fit-haui.edu.vn` |

Owner performs deploy. Agent prepares handoff checklist and collects evidence only after `/health` returns 200.

Current observed state at intent freeze: frontend serves SalePilot; backend `/health` returned 502. Do not claim healthy public deployment until re-verified.

## Commands

```bash
# Scope guard
python scripts/validate_agent_scope.py
python scripts/validate_agent_scope.py --feature-id rivf-001 --check-files <paths>

# Slice 1 — DMX research import + manifest
# Stage source once (owner machine):
#   copy C:\Downloads\DMX_product\products_detail.xlsx -> repo root products_detail.xlsx
cd backend
python -m scripts.import_dmx_research --snapshot-only --confirm-publication-rights
cd ..
python scripts/validate_research_manifest.py experiments/manifest.json
python scripts/validate_research_manifest.py --self-test

# Unit tests (Docker or local venv)
cd backend && python -m unittest tests.test_import_dmx_research

# Later slices
python scripts/run_pilot.py --split dev
python scripts/collect_deployment_evidence.py --url https://optivisionlab.fit-haui.edu.vn
python scripts/run_llm_baseline.py --help
```

## Project structure (this workstream)

```text
docs/RIVF_TRACK2_SCOPE_SPEC.md     # this spec
docs/RIVF_TRACK2_PROTOCOL.md       # research protocol (DMX-updated)
docs/DATASET_CARD.md               # asset rights + hashes
docs/DEPLOYMENT_HANDOFF.md         # owner manual deploy steps
docs/REPRODUCIBILITY.md            # clean rerun instructions
backend/scripts/import_dmx_research.py
backend/tests/test_import_dmx_research.py
backend/data/research/catalog_dmx_snapshot.json   # gitignored derived
products_detail.xlsx                              # gitignored raw source
experiments/manifest.json
experiments/conditions.json
experiments/benchmark/                            # sealed later
scripts/run_llm_baseline.py
scripts/collect_deployment_evidence.py
paper/main.tex
```

## Code style

Match existing research importers:

- deterministic sort keys before snapshot write
- canonical JSON: `ensure_ascii=False, sort_keys=True, separators=(",", ":")` + trailing newline
- fail-closed rights / path mismatch
- no secrets in repo; env vars only for B2 keys

## Testing strategy

| Layer | What |
|---|---|
| Unit | synthetic mini xlsx → deterministic snapshot hash; rights fail-closed |
| Manifest | self-test + strict ready validation after real import |
| Experiment | existing evaluator unittests remain green; sealed run later |
| Deployment | collector against public URL after owner deploy |
| Paper | claims must cite frozen result hashes only |

## Boundaries

**Always**

- Keep WIP = 1 (`rivf-001`)
- Edit only `allowed_files`
- Keep offline deterministic path working without API keys
- Separate engineering fixture (70 SKU) from publication catalog
- Record verification evidence before marking slices done

**Ask first**

- Protected paths (`backend/app/main.py`, `docker-compose.yml`, `AGENTS.md`, …)
- Changing public domains
- Committing large derived snapshots
- Enabling human study

**Never**

- Commit `.env`, API keys, raw customer trajectories
- Claim fixture pilot numbers as sealed DMX results
- Claim healthy public deployment while backend 502
- Average multiple LLM providers into one B2 score

## Success criteria

1. `validate_research_manifest.py experiments/manifest.json` exits 0 with `status=ready`
2. `raw_source_hash` matches staged `products_detail.xlsx` bytes
3. `normalized_catalog_hash` matches research snapshot bytes
4. Synthetic DMX importer unittest PASS
5. Sealed experiment artifacts exist for B0/B1/S_hybrid (+ pinned B2 or documented unavailable with owner-approved exception — default: required)
6. Public `/health` 200 + chat smoke + collector JSON recorded
7. Paper abstract/results only state numbers present in frozen artifacts
8. Scope guard session check PASS for edited files

## Implementation order

1. **Slice 1** — DMX import + manifest ready (this session target)
2. **Slice 2** — Sealed test + full experiment runner/statistics
3. **Slice 3** — Multi-provider B2 pin contract
4. **Slice 4** — Deployment handoff + evidence collection
5. **Slice 5** — Paper claim alignment

## Open questions (non-blocking for Slice 1)

- Exact B2 provider/model pin for the sealed report (owner configures secret locally)
- When owner will restore backend public URL from 502
