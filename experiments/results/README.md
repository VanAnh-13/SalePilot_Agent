# Experiment results

Runtime outputs (`*.jsonl`, score dumps) are gitignored.

Regenerate pilot evidence:

```bash
python scripts/build_experiment_fixture_catalog.py --install-snapshot
# pin hash must match experiments/conditions.json catalog.sha256
CATALOG_BACKEND=snapshot PYTHONPATH=backend:. python scripts/run_pilot.py --split dev
PYTHONPATH=backend:. python -m experiments.evaluate.runner \
  --input experiments/results/pilot_dev.jsonl \
  --labels experiments/benchmark/dev.jsonl \
  --out experiments/results/pilot_dev_scores.json
# scores are per-condition under aggregates.<condition>
```

Publication experiments require the authorized workbook and a ready research manifest, not only the engineering fixture.
