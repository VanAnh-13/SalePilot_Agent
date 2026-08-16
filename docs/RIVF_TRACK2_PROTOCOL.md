# RIVF 2026 Track 2 Research Protocol

**Track:** AI Applications  
**Venue:** IEEE-RIVF 2026, VinUniversity, Hanoi, 18–20 Dec 2026  
**CFP:** https://rivf2026.org/call-for-papers.html  
**EDAS Submission:** https://edas.info/N35414

---

## Track 2 Topics Addressed

| Topic from CFP | SalePilot Coverage |
|---|---|
| AI-based decision support systems | Constraint-first need extraction + fail-closed ranking |
| Explainable and interpretable AI in applications | Decision contract: constraint status, score decomposition, provenance |
| Real-world deployment of AI systems | Docker Compose, multi-backend fallback, health endpoint |
| Challenges in scaling and integrating AI solutions | 14-category registry, Postgres→MongoDB→snapshot chain, channel abstraction |

---

## Research Questions

**RQ1:** Does a functional Vietnamese benchmark detect hard-constraint failures
when the same parser and ranker run without explicit constraint enforcement?

**RQ2:** Under a price-popularity comparator, does constraint-aware ordering
change hard-constraint satisfaction metrics?

**RQ3:** Does a real-world multi-backend deployment maintain acceptable latency
(p95 < 2s) under repeated appliance consultation queries?

---

## Evaluation Design

### Benchmark
- **60 developer-authored Vietnamese episodes** (20 dev + 40 sealed test) covering 11+ categories
- All episodes are **single-turn** — no multi-turn episodes are present
- Includes: no-diacritics Vietnamese, impossible budget, negation + category switch,
  unsupported category, FAQ query, clarification, abstention

### Conditions
| ID | Description | Script |
|---|---|---|
| `B0_price_popularity` | Price + popularity sort, no constraints | `scripts/run_pilot.py` |
| `B1_lexical_filter` | Lexical keyword filter + constraint checking | `scripts/run_pilot.py` |
| `S_hybrid_constraint` | Typed state + constraint-first ranker (proposed) | `scripts/run_pilot.py` |
| `B2_llm_single_agent` | Single-agent LLM baseline (FPT/DeepSeek-V4-Flash) | `scripts/run_llm_baseline.py` |

### Catalog
- **Primary experiment:** DMX crawl snapshot (13,716 products / 118 categories), hash-pinned in `experiments/manifest.json`
- **Dev/engineering fixture:** 70 SKU / 14 categories — used for pilot runs only, not publication source
- **Production:** DMX crawl via Neon Postgres (`CATALOG_BACKEND=postgres`)

---

## Verified Results (Session 012 — 2026-07-26)

> **Custody note (2026-08-01):** the B2 rows below are the actual Session-012 pilot run, which used provider `meta_ai/muse-spark-1.1` — this does **not** match the `B2_llm_single_agent` row's pinned provider in the Conditions table above (`FPT/DeepSeek-V4-Flash`). The sealed **test**-split B2 prediction file was later found to have a provider/hash mismatch versus its own custody record, and repeat=0 (spec requires ≥3); it was removed from custody on 2026-08-01 and B2 is excluded from the paper's primary comparison. See `experiments/results/CHAIN_OF_CUSTODY.json`. The numbers below are retained only as the historical pilot record and must not be cited as current, reproducible, or FPT/DeepSeek results.
>
> **Dev-split re-run (2026-08-01):** the owner supplied real `meta_ai/muse-spark-1.1` credentials and `scripts/run_llm_baseline.py --split dev` was re-run end-to-end (repeat=1) after the pin-corruption bug above was fixed. Fresh, independently-scored results (`experiments/results/llm_baseline_dev_scores.json`, via `experiments/evaluate/runner.py`): category_accuracy 0.95, action_accuracy 0.65, slot_micro_f1 0.9836, hard_constraint_violation_rate 0.0 (0/42 checked) — see `experiments/conditions.json`'s `llm_baseline` block for full detail. These numbers **differ** from the Session-012 dev row below (notably 0 violations here vs. 0.231 there), which is expected: the two runs used different code, and the Session-012 numbers were never independently re-verifiable in the first place. This dev-split re-run is a pipeline/custody verification with repeat=1, not a new sealed artifact meeting the spec's ≥ 3-repeats bar — B2 remains excluded from the paper's primary comparison either way.

### Dev split (20 episodes / 70-product engineering fixture)

| System | Cat. Acc. | Act. Acc. | Slot µF1 | Hard Viol. | Constraints Checked |
|---|---|---|---|---|---|
| S_hybrid_constraint | 0.950 | **0.700** | **0.984** | **0.000** | 33 |
| B1_lexical_filter | 0.950 | **0.700** | **0.984** | **0.000** | 33 |
| B0_price_popularity | 0.950 | 0.650 | **0.984** | 0.125 | 40 |
| B2_LLM (Meta Muse-Spark-1.1) | 1.000$^\dagger$ | 0.650 | 0.000 | 0.231 | 39 |

$^\dagger$B2 Cat.=1.0 is artifact: True when both expected and predicted category are None (FAQ/abstain).

### Test split (40 episodes / 70-product engineering fixture) — sealed

| System | Cat. Acc. | Act. Acc. | Slot µF1 | Hard Viol. | Constraints Checked |
|---|---|---|---|---|---|
| **S_hybrid_constraint** | **0.950** | 0.475 | **0.961** | **0.000** | 37 |
| **B1_lexical_filter** | **0.950** | 0.475 | **0.961** | **0.000** | 37 |
| B0_price_popularity | **0.950** | **0.550** | **0.961** | 0.177 | 62 |
| B2_LLM (Meta Muse-Spark-1.1) | 0.950 | **0.550** | 0.991$^\ddagger$ | 0.254 | 59 |

$^\ddagger$B2 Slot µF1=0.991 includes only extracted budget values (52 TP, 1 FP, 0 FN). B2 emits no typed slots on 14 FAQ/abstain episodes, inflating micro aggregate.

**Evidence files:**
- `experiments/results/pilot_dev.jsonl` — dev raw predictions
- `experiments/results/pilot_dev_scores.json` — dev scored aggregates
- `experiments/results/pilot_test.jsonl` — test raw predictions
- `experiments/results/pilot_test_scores.json` — test scored aggregates
- `experiments/results/llm_baseline_test.jsonl` — **removed 2026-08-01** (custody mismatch; see `CHAIN_OF_CUSTODY.json`); replaced by marker file `experiments/results/llm_baseline_test.unavailable.json`
- `experiments/manifest.json` — validated (status=ready, DMX catalog 13,716 products)
- `experiments/benchmark/SEAL_RECORD.json` — seal record

---

## Evaluation Commands

```bash
# 1. Install engineering fixture as catalog snapshot
cp experiments/fixtures/catalog_dev_fixture.json backend/data/catalog_snapshot.json

# 2. Run deterministic pilot
python scripts/run_pilot.py --split dev

# 3. Score results
python -m experiments.evaluate.runner \
  --input experiments/results/pilot_dev.jsonl \
  --labels experiments/benchmark/dev.jsonl \
  --out experiments/results/pilot_dev_scores.json

# 4. Validate research manifest
python scripts/validate_research_manifest.py experiments/manifest.json

# 5. Run LLM baseline (optional — requires META_API_KEY)
# export META_API_KEY=<key>
# python scripts/run_llm_baseline.py --split dev

# 6. Collect deployment evidence (requires backend running)
# python scripts/collect_deployment_evidence.py --url http://localhost:8000
```

---

## Pre-Submission Checklist

- [ ] Confirm RIVF 2026 submission deadline (check rivf2026.org)
- [ ] Confirm blind review policy (single vs double blind)
- [ ] Recompile `paper/main.pdf` from updated `paper/main.tex`
- [ ] Verify paper is exactly 6 pages A4, PDF 1.6
- [ ] Run deployment evidence collection from public URL
- [ ] Add B2 LLM baseline results to paper Table 1
- [ ] Complete human study annotation (see `docs/HUMAN_STUDY_PROTOCOL.md`)
- [ ] Add human study CRS-Que results to paper Section V
- [ ] Verify all 4 figures embedded correctly
- [ ] Check all 26 citations compile in BibTeX
- [ ] Update AI-assistance disclosure if needed
- [ ] Confirm no simultaneous submission to other venues
- [ ] Create supplementary artifact archive (evaluator + fixtures)
- [ ] Upload to EDAS: https://edas.info/N35414

---

## File Manifest (Key Research Files)

```
paper/
  main.tex             ← LaTeX source (Track 2 aligned, real metrics)
  ref.bib              ← 26 audited references
  main.pdf             ← Compiled draft (recompile needed after edits)
  figures/             ← 4 PNG figures (system architecture, workflows)
  artifacts/           ← Deterministic evaluator outputs + hashes
  SOURCE_LEDGER.md     ← Audited DOI per citation

experiments/
  manifest.json        ← Research manifest (status=ready, validated)
  conditions.json      ← 3 deterministic + 1 optional (LLM) conditions
  benchmark/dev.jsonl  ← 20-episode Vietnamese benchmark
  fixtures/catalog_dev_fixture.json  ← 70 SKU engineering fixture
  results/
    pilot_dev.jsonl        ← Raw predictions (20 episodes × 3 conditions)
    pilot_dev_scores.json  ← Scored aggregates

scripts/
  run_pilot.py                   ← Deterministic pilot runner
  run_llm_baseline.py            ← B2 LLM baseline runner
  collect_deployment_evidence.py ← Deployment latency measurements
  validate_research_manifest.py  ← Manifest validator

docs/
  HUMAN_STUDY_PROTOCOL.md        ← CRS-Que annotation protocol
  RIVF_TRACK2_PROTOCOL.md        ← This file
```
