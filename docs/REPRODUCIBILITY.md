# Reproducibility — SalePilot-R (RIVF 2026 Track 2)

## Frozen research identity

| Artifact | Path / value |
|----------|----------------|
| Protocol | `docs/RIVF_TRACK2_PROTOCOL.md` |
| Scope spec | `docs/RIVF_TRACK2_SCOPE_SPEC.md` |
| Manifest | `experiments/manifest.json` (`status=ready`) |
| Canonical source | `products_detail.xlsx` (gitignored; owner-staged) |
| Research snapshot | `backend/data/research/catalog_dmx_snapshot.json` |
| Catalog hash | see `catalog.normalized_catalog_hash` in manifest |
| Seal record | `experiments/benchmark/SEAL_RECORD.json` |
| Sealed scores | `experiments/results/exp_test_scores.json` |
| Custody | `experiments/results/CHAIN_OF_CUSTODY.json` |

## Clean rerun (deterministic conditions)

```bash
# 1) Scope + manifest
python scripts/validate_agent_scope.py
python scripts/validate_research_manifest.py experiments/manifest.json

# 2) If snapshot missing, re-import (requires staged xlsx)
cd backend
python -m scripts.import_dmx_research --snapshot-only --confirm-publication-rights
cd ..

# 3) Seal + benchmark gates
python scripts/validate_benchmark_seal.py experiments/benchmark/SEAL_RECORD.json
python scripts/validate_benchmark.py experiments/benchmark/dev.jsonl
python scripts/validate_benchmark.py experiments/benchmark/test.jsonl

# 4) Sealed experiment (B0/B1/S_hybrid)
python scripts/run_rivf_experiment.py --split test

# 5) Table
python scripts/summarize_results.py experiments/results/exp_test_scores.json
```

## B2 LLM baseline (optional until key is pinned)

```bash
# Resolve pin without calling the network
python scripts/run_llm_baseline.py --dry-run-config

# Configure exactly one provider (example: OpenAI-compatible)
# setx LLM_API_BASE "https://api.openai.com/v1"
# setx LLM_API_KEY  "<secret>"
# setx LLM_MODEL    "gpt-4o-mini"

python scripts/run_llm_baseline.py --split test --repeats 3 --provider openai
```

Without a key, use `--allow-unavailable` to emit an explicit unavailable report
instead of failing the rest of the package.

## Deployment evidence

See `docs/DEPLOYMENT_HANDOFF.md`. Public claims require a 200 `/health` on the
owner-operated backend URL.

## Non-goals for bit-identical LLM runs

Temperature is fixed at 0.0, but provider-side nondeterminism can remain.
Report provider, base URL, model id, key fingerprint, and prediction hash.
