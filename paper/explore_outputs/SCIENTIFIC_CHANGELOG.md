# Scientific changelog

## 2026-07-21 — candidate paper bundle v1

- Froze the anonymous research snapshot using file-level digests and recorded
  the exact fixture hashes.
- Re-ran deterministic and timed evaluator paths; did not hand-edit metrics.
- Framed the work as a system and executable protocol paper rather than a novel
  model or real-world effectiveness result.
- Added stateless and oracle-category popularity comparisons already implemented
  by the repository evaluator; no new comparator behavior was introduced.
- Preserved the validity warning that three candidates/category make Hit@3 and
  Recall@3 non-discriminative.
- Audited primary literature and separated claim support from explanation
  faithfulness, pseudonymization from anonymity, and repeatability from
  independent reproduction.
- Added original architecture, request lifecycle, evaluation, and ranking SVG
  workflows; the first three are embedded in the IEEE PDF.
- Documented two implementation semantics precisely: clarification may ask
  multiple configured missing slots, and min/max hard gates apply when the
  corresponding catalog spec is present.
- No model training, metric mutation, production deployment, user study, or
  external benchmark was executed.

## Lane-isolation deviation

The explore skill normally requires an isolated branch/worktree. The current
research existed as an uncommitted repository patch; a worktree from HEAD would
not contain it. To avoid silently evaluating the wrong system, the work was
restricted to the new `paper/` artifact namespace and no implementation file
was changed. This deviation is explicit and prevents the present output from
being represented as a fully governed experimental branch.

## 2026-07-21 — adversarial claim audit and submission revision

- Three independent read-only reviews checked scientific claims, source
  quality, submission mechanics, and the rendered PDF.
- Removed `Multi-Agent` from the title because the experiment does not
  compare orchestration; retained the role-scoped architecture as an explicitly
  unevaluated system component.
- Defined the evaluated unit as deterministic open-loop final-turn replay and
  distinguished evaluator fallback (legacy `escalate` label) from production
  human handoff.
- Corrected runtime claims: optional snapshot manifests check hash/counts but
  the runtime accepts manifest-free snapshots; persistence consists of separate
  writes; trajectory export is awaited; free-form Lead finalization has no
  runtime claim verifier.
- Replaced reproducibility language with same-team functional repeatability,
  disclosed the legacy recognized-claim denominator name, and printed exact
  supports in the result table.
- Added a Vietnamese trace, artifact-availability section, explicit evaluator
  command, and limitations for category coverage, weak P@1 cases, missing
  single-agent baseline, and one-pass timing.
- Rebuilt the three embedded workflows with at least 8 pt effective text and
  corrected data/control arrows.
- Re-ran the deterministic and timed evaluator artifacts and the full isolated
  repository verification suite; the latter passed outside the filesystem
  sandbox because sandboxed worker-thread wakeups prevent `aiosqlite` from
  progressing.
