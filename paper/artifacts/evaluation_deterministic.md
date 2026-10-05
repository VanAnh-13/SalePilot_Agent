# SalePilot offline evaluation

Dataset: `salepilot-scenarios-v1` (`8` scenarios, SHA-256 `2e69892d8e127bc4e73747d545bb973425be950844315f9907f03ef9c8f8dda0`).
Catalog: `salepilot-synthetic-v1` (`24` synthetic products, SHA-256 `f3d5803344c320f5c6e1cb52c586f1d9c93af0015c1d57194aa77059b8817b4e`).

> **Validity warning:** Synthetic-v1 is a functional fixture, not an external effectiveness benchmark. Hit@3 and Recall@3 are non-discriminative when a category has at most three candidates. Do not use these synthetic-v1 scores alone to claim real-world recommendation efficacy.

| System | Category acc. | Action acc. | Hard constraints | P@1 | Hit@3 | Recall@3 | nDCG@3 | Clarify/escalate proxy | Limited claim fidelity | Claim support | Mean latency (ms) | P95 latency (ms) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `stateful_need` | 1.000 | 1.000 | 0.889 | 1.000 | 1.000 | 1.000 | 0.948 | 1.000 | 1.000 | 27 | 0.000 | 0.000 |
| `stateless_last_turn` | 0.429 | 0.500 | 0.222 | 0.333 | 0.333 | 0.333 | 0.307 | 1.000 | 1.000 | 9 | 0.000 | 0.000 |
| `popularity_oracle_category` | 1.000 | 0.875 | 0.778 | 0.667 | 1.000 | 1.000 | 0.683 | 0.500 | n/a | 0 | 0.000 | 0.000 |

The popularity baseline receives the gold category but ignores user constraints. Latency covers local parsing and ranking only; no network or LLM call is used.
Action accuracy is the three-way exact match over all gold recommend/clarify/escalate scenarios.
Clarify/escalate proxy accuracy is computed only on gold clarify/escalate scenarios; recommendation cases are excluded from that denominator.

Limited claim fidelity checks only recognized `trong ngân sách`, configured `phù hợp <range slot>`, and `ngoài dải <range slot>` claims against structured need/catalog fields. It is not a human judgment of explanation quality, completeness, usefulness, or fluency.

This file is generated from the versioned fixtures; rerun the evaluator rather than editing measured values.
