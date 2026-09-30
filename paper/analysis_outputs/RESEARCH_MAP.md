# Research map

## Frozen object of study

- Current research: anonymous snapshot identified by the file-level digests in
  `paper/artifacts/artifact_manifest.json`.
- Task: Vietnamese multi-turn appliance decision support.
- Current evidence: eight functional scenarios and 24 synthetic products.
- Current tier: **functional repeatability only**; no external efficacy evidence.

## Research questions

1. Can the fixture expose loss of earlier-turn constraints in a last-turn-only
   ablation using the same parser/ranker?
2. Does constraint-aware ordering behave differently from an oracle-category
   popularity comparator on the frozen cases?
3. Are identity, provenance, side-effect, privacy, and evaluation boundaries
   explicit and executable in the implementation snapshot?

## Evidence graph

```text
versioned scenarios + catalog manifests
                 │
                 ▼
 target ── stateless ablation ── popularity/oracle-category
                 │
                 ▼
 normalized predictions → transparent metrics → scope warning
                 │
                 ├── supports: deterministic functional behavior
                 └── does not support: real-world efficacy / SOTA / UX
```

## Candidate contribution statement

SalePilot is positioned as a candidate systems/protocol contribution combining
typed multi-turn need state, deterministic constraint-aware ranking,
role-restricted orchestration, provenance, lifecycle controls, and an executable
validity gate. The source audit does not establish global novelty.

## Next scientific gate

Run an independently annotated external benchmark with larger candidate pools,
grouped conversation splits, paired uncertainty intervals, and a separate
human evaluation. Until then, every performance result remains descriptive.
