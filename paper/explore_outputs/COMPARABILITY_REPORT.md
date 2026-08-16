# Comparability report

## Fair comparisons in the current artifact

| Comparison | Why it is interpretable | Remaining limitation |
|---|---|---|
| Stateful vs stateless last turn | Same fixture, parser, ranker, output schema, and metrics; only earlier-turn state is removed. | Only four multi-turn recommend cases; scenarios were co-developed with rules. |
| Stateful vs popularity/oracle category | Same catalog/output/metrics; baseline is granted category and ignores constraints. | It is not a learned CRS, single-agent tool system, or published-system reproduction. |
| Deterministic vs timed evaluator output | Same predictions and metric implementation. | Timing is a single local parse/rank run, excluding all end-to-end components. |

## Comparisons explicitly prohibited

- No numeric comparison with Hybrid-MACRS, InteRecAgent, ReAct, AutoGen, RAG,
  AgentBench, ReDial, or any cited paper: tasks, data, metrics, and systems differ.
- No SOTA, novelty, real-world deployment, conversion, revenue, satisfaction,
  or generalization claim.
- No explanation-faithfulness claim from the mechanical catalog claim check.
- No anonymity, legal-compliance, or prompt-injection-resistance guarantee.
- No claim of independent reproduction from a same-team local verifier.

## Required stronger comparators for a later paper revision

1. Single-agent/tool-only orchestration with the same prompt and tool budget.
2. Retrieval/ranking baseline tuned on a grouped development set.
3. Larger non-oracle popularity and semantic-retrieval comparators.
4. External human labels and CRS-Que-derived user constructs.
5. Paired conversation-level intervals and error analysis by category/action.
