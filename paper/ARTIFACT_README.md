# SalePilot anonymous evaluation artifact

> **IMPORTANT — Supplement does NOT reproduce the current paper (added 2026-08-01):**
> This supplement reproduces the **legacy 8-scenario / 24-product synthetic evaluation**
> from an earlier research prototype.  The **current paper** (RIVF 2026 Track 2) reports
> results from **40 sealed episodes over 13,716 real DMX products** across 118 categories.
> **No number in the published paper can be reproduced from this supplement alone.**
> The artifact manifest shows **28/32 hash drift** between this supplement and the
> current repository state.
>
> To reproduce the current paper results, use the `experiments/` directory in the
> main repository (see "Current experiment reproduction" below).

This supplement reproduces the **same-team functional repeatability** results
reported in an earlier SalePilot prototype paper. It is not an external
effectiveness benchmark and does not execute the Lead orchestrator, LLM,
databases, channel gateway, persistence lifecycle, or user interface.

## Current experiment reproduction

To reproduce the results reported in the current RIVF 2026 Track 2 paper,
use the `experiments/` directory in the main repository:

```bash
# From the repository root (requires Python 3.12+):
python -m venv .venv
.venv/bin/pip install -r backend/requirements.txt

# Re-run the deterministic evaluator (B0/B1/S_hybrid, no LLM needed):
python scripts/summarize_results.py --rescore

# Verify hashes against chain of custody:
python -c "
import hashlib, pathlib
for name in ['exp_test_predictions.jsonl', 'exp_test_scores.json',
             'exp_test_bootstrap.json', 'exp_test_bootstrap_pooled.json']:
    p = pathlib.Path('experiments/results') / name
    if p.exists():
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        print(f'{name}: {h}')
"
# Compare output with experiments/results/CHAIN_OF_CUSTODY.json
```

The sealed predictions, scores, bootstrap artifacts, and chain-of-custody
record are all present in `experiments/results/`.

## Legacy supplement: frozen inputs

- Scenarios: `backend/evaluation/data/scenarios_v1.jsonl` (8 cases), SHA-256
  `2e69892d8e127bc4e73747d545bb973425be950844315f9907f03ef9c8f8dda0`
- Catalog: `backend/evaluation/data/catalog_synthetic_v1.json` (24 products),
  SHA-256
  `f3d5803344c320f5c6e1cb52c586f1d9c93af0015c1d57194aa77059b8817b4e`
- Both inputs require their companion manifest files.

## Legacy supplement: run

Use Python 3.12 in a virtual environment. From the extracted archive root:

```bash
python -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
cd backend
.venv/bin/python -m evaluation.cli \
  --json-out ../paper/artifacts/evaluation_deterministic.json \
  --markdown-out ../paper/artifacts/evaluation_deterministic.md \
  --deterministic-latency
.venv/bin/python -m unittest tests.test_evaluation
```

The deterministic command requires no API key, database, network request, or
proprietary catalog. Compare regenerated digests with
`paper/artifacts/artifact_manifest.json`.

## Interpretation boundary

- Turns are replayed open-loop; only the final prediction is scored.
- `stateful_need` and `stateless_last_turn` execute only deterministic
  extraction, state merge, action normalization, and ranking.
- The legacy output label `escalate` means evaluator fallback/out-of-scope; it
  is not proof that a production human-handoff tool ran.
- In `limited_claim_fidelity`, the legacy key `supported_claims` is the count of
  recognized claims (the denominator), while `verified_claims` is the
  numerator.
- Three products per category make Hit@3 and Recall@3 non-discriminative.
- The labels are developer-authored and do not support real-world efficacy,
  generalization, human explanation quality, or multi-agent superiority.

The archive intentionally excludes `.env`, credentials, databases, customer
records, caches, and generated virtual environments.