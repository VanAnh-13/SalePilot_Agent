# Frozen evaluation contract

## Inputs

- Scenarios: `backend/evaluation/data/scenarios_v1.jsonl`
  - 8 scenarios; SHA-256
    `2e69892d8e127bc4e73747d545bb973425be950844315f9907f03ef9c8f8dda0`
- Catalog: `backend/evaluation/data/catalog_synthetic_v1.json`
  - 24 products; SHA-256
    `f3d5803344c320f5c6e1cb52c586f1d9c93af0015c1d57194aa77059b8817b4e`
- Companion manifests are mandatory and loader-validated.

## Systems

- `stateful_need`: accumulate all turns, then act/rank.
- `stateless_last_turn`: retain only the final turn; same parser/ranker.
- `popularity_oracle_category`: receive gold category, ignore constraints, rank
  by sold/rating/price/SKU.

## Outputs and metrics

All systems emit one normalized prediction per scenario. Metrics are category
accuracy, three-way action accuracy, hard-constraint satisfaction, P@1,
Hit@3, Recall@3, nDCG@3, clarify/fallback proxy accuracy, mechanically verified
over recognized claims, and local parse/rank latency. The artifact's legacy
`supported_claims` key is the recognized-claim denominator, not a count of
independently supported explanations.

## Frozen command

```bash
cd backend
.venv/bin/python -m evaluation.cli \
  --json-out ../paper/artifacts/evaluation_deterministic.json \
  --markdown-out ../paper/artifacts/evaluation_deterministic.md \
  --deterministic-latency
```

Remove `--deterministic-latency` only for the separate timed artifact.

## Validity contract

- Candidate count equals three for every category; Hit@3 and Recall@3 are
  non-discriminative for the target/popularity systems.
- Labels are developer-authored, not independent human judgments.
- No confidence interval is calculated on eight fixed cases.
- The evaluator's scope warning is part of the result, not optional prose.
- Results may support same-team functional repeatability and fixture ablation
  sensitivity only. The JSON tier name `functional_reproducibility` is an
  internal identifier, not evidence of independent reproduction.
- Turns are replayed open-loop and only one final prediction is scored; no
  interactive question policy or production human handoff is evaluated.
