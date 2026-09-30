# Limitations and Ethics — SalePilot-R

## Data rights

- Canonical catalog is owner-authorized DMX crawl (`products_detail.xlsx`).
- Raw catalog bytes are gitignored; paper releases aggregates, hashes, and code.
- No retailer endorsement is implied by using public-facing product fields.

## Privacy

- Benchmark IDs are synthetic.
- Research exports forbid raw trajectories, phones, and emails.
- Deployment logs used for evidence must be redacted before sharing.

## Scientific limitations

- Sealed test is developer-authored (40 episodes), not dual-annotated field data.
- Open-loop final-turn scoring does not evaluate multi-turn question utility.
- B1 and S_hybrid currently share the same need parser; primary differentiation is ranking / hard-constraint handling.
- B2 LLM baseline requires an owner-pinned provider key; without it the condition is reported `unavailable`.
- Public deployment evidence is independent of catalog readiness; a 502 backend blocks public claims.

## Safety / product limitations

- No realtime stock; systems must not claim availability.
- Prices are snapshot-time only.
- Offline deterministic path is the reproducible research core; LLM phrasing is optional product UX.

## Human study

- Disabled for the 2026-07-31 package. No faithfulness/nDCG human claims.
