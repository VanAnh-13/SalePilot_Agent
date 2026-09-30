# SalePilot-R Task Checklist

Một task chỉ được đánh dấu hoàn tất khi **tất cả** acceptance criteria và verification trong `tasks/plan.md` pass; các dòng dưới đây chỉ là execution index, không thay thế plan.

## Plan Gate

- [x] Human duyệt working title, RQ/H1-H3 và P0/P1 scope.
- [x] Human xác nhận quyền dùng canonical catalog/policy data cho RIVF hoặc chọn fallback rights-cleared.
- [x] Canonical source, custodian, paper owner và hard go/no-go dates được xác nhận; mặc định Task 10-11 off.
- [x] Sau khi duyệt mới đăng ký `rivf-001` là feature duy nhất `in_progress` trong `feature_list.json`.

## Phase 0: Data Foundation

- [x] **Task 1: Freeze research protocol and data-rights gate**
  - Dependencies: none
  - Verification: `python scripts/validate_research_manifest.py experiments/manifest.json --allow-blocked`; `python scripts/validate_research_manifest.py --self-test`
  - Evidence: protocol, dataset card, owner publication confirmation
  - Note: 2026-07-25 pivot — canonical source is DMX `products_detail.xlsx` (workbook path retired)
- [x] **Task 2: Reconcile one canonical catalog pipeline**
  - Dependencies: Task 1
  - Verification: `tests.test_import_dmx_research` PASS (4); full DMX import → manifest strict ready
  - Evidence: `import_dmx_research.py`; snapshot 13716 products / 118 cats; raw sha256 `39a03b03…`; norm sha256 `e2afdf38…`
  - Note: engineering fixture 70 SKU remains for hermetic pilot only

## Checkpoint A: Data Foundation

- [x] Rights/data gate is green (DMX source staged + hashed; strict manifest ready).
- [x] Engineering catalog path reproducible via fixture snapshot.
- [x] Crawl registry isolated; legacy products.json not canonical experiment source.

## Phase 1: Benchmark and Evaluation

- [x] **Task 3: Define benchmark contract and tracer pilot**
  - Dependencies: Task 2
  - Verification: `python scripts/validate_benchmark.py experiments/benchmark/dev.jsonl` PASS (20 episodes)
  - Evidence: schema + dev.jsonl multi-category / multi-turn / unsupported / FAQ / impossible budget
- [x] **Task 4: Build common evaluator and frozen metric implementation**
  - Dependencies: Task 3
  - Verification: `python -m unittest experiments.evaluate.test_metrics` PASS; runner scores pilot JSONL per condition
  - Evidence: condition-aware runner; label-grounded hard constraints; true micro slot F1 + pooled violation rate

## Checkpoint B0: Benchmark Contract

- [x] Dev schema, annotation semantics and evaluator result schema are compatible.
- [x] Hard/soft/missing policy fixtures pass in metrics tests.
- [x] Full sealed test labels not yet created (dev only).

- [~] **Task 5: Make experiment execution request-scoped and privacy-safe**
  - Dependencies: Tasks 2, 4
  - Verification: `tests.test_run_bag_isolation` PASS (ContextVar)
  - Evidence: request-scoped run_bag; full temp-DB experiment runtime still pending
- [x] **Task 6: Add controlled systems and run tracer pilot**
  - Dependencies: Tasks 4-5
  - Verification: `CATALOG_BACKEND=snapshot python scripts/run_pilot.py --split dev` PASS on fixture with catalog pin
  - Evidence: B0/B1/S_hybrid JSONL; S_hybrid/B1 cat=0.95 act=0.95 slot_micro_f1=0.9841 hard_violation=0.0; B0 hard_violation=0.0755 (baseline)

## Checkpoint B1: Tracer Bullet

- [x] Dev episode reaches two baselines and proposed system through aggregate metrics.
- [~] Trace/state isolation partial (run_bag done; full experiment privacy runtime pending).
- [x] Hard/soft/missing policy and clarification branches exercised on pilot.

- [x] **Task 7: Register a sealed held-out benchmark**
  - Dependencies: Tasks 3, 4, 6
  - Verification: `python scripts/validate_benchmark_seal.py` PASS; dev/test validators PASS
  - Evidence: DMX-aligned dev=20 + test=40; SEAL_RECORD inputs/file hashes; CHAIN_OF_CUSTODY after sealed run
  - Note: labels colocated in JSONL; inputs_sha256 isolates turns for custody audit

## Checkpoint B2: Benchmark Freeze

- [x] Sealed test registered against ready DMX catalog hash `e2afdf38…`.
- [x] No dev/test episode_id overlap; schema + category allowlist validated.
- [x] Human-study gate remains disabled.

## Phase 2: Evidence-First Product

- [x] **Task 8: Define fail-closed decision domain contract**
  - Dependencies: Tasks 6-7
  - Verification: `python -m unittest tests.test_decision_contract` PASS
  - Evidence: `decision.py` schema v1, provenance, score components, hard missing exclude in scoring
- [~] **Task 9: Propagate decision through runtime and Chat API**
  - Dependencies: Tasks 7-8
  - Verification: offline + catalog tool + run_bag + fast-path + full-graph return/SSE done + trajectory JSON + gateway meta; live HTTP smoke still pending
  - Evidence: `decision.py` evidence fields; `tests.test_decision_propagation` PASS; wiring in `chat.py`, `offline.py`, `graph.py`, `tools/catalog.py`, `trajectory/export.py`, `gateway.py`, `runs.py`

## Checkpoint C1: Safe Decision Contract

- [x] Domain fixtures prove hard constraints are fail-closed / no fabricated impossible-budget top3.
- [x] Offline/fast/full paths can emit decision (full path via recommend tool → run_bag).
- [ ] API/trajectory decision hash parity under live HTTP still pending.

- [ ] **Task 10: Ship evidence-first chat UI slice**
  - Dependencies: Task 9
  - Verification: `cd frontend && npm run build`; browser desktop/mobile check
  - Evidence: screenshot/video or browser report with source/constraint cards

## Checkpoint C2: Evidence-First User Flow

- [ ] Vietnamese query produces structured decision plus grounded reply.
- [ ] Hard constraints, unknowns, unsupported and stock-unknown states are visible and tested.
- [ ] Trace and research export are concurrency-safe and PII-safe.

## Phase 3: Empirical Results

- [ ] **Task 11: Run blinded relevance and explanation-faithfulness study (conditional)**
  - Dependencies: Tasks 6, 7, 9, and human-study gate enabled
  - Verification: `python scripts/score_human_eval.py experiments/benchmark/relevance.jsonl`
  - Evidence: blinded pool/source checks, frozen rubric, agreement/adjudication report or an explicit pre-test cancellation record
- [x] **Task 12: Execute full experiment and statistical analysis**
  - Dependencies: Tasks 5, 7, 9; Task 11 is optional input when enabled
  - Verification: sealed deterministic + B2 scored; bootstrap 95% CI artifact
  - Evidence: `exp_test_scores.json`, `llm_baseline_test_scores.json`, `exp_test_bootstrap.json`, `CHAIN_OF_CUSTODY.json`

## Checkpoint D: Empirical Evidence

- [x] Proposed vs baselines table exists (B0/B1/S + B2).
- [x] Bootstrap 95% CIs reported for sealed deterministic metrics.
- [x] Human study disabled with explicit limitation.
- [x] Paper numbers map to frozen result/custody hashes.

## Phase 4: Deployment and Submission

- [~] **Task 13: Produce real-world deployment and scaling evidence**
  - Dependencies: Tasks 2, 5, 9
  - Partial: handoff doc + collector + public FE 200 / BE 502 evidence JSON
  - Remaining: owner restores backend health; recollect p50/p95
- [~] **Task 14: Create IEEE paper and reproducibility pack**
  - Dependencies: Tasks 12-13
  - Partial: main.tex claims aligned to sealed DMX + B2; REPRODUCIBILITY + LIMITATIONS docs
  - Remaining: PDF compile check if TeX available; EDAS final metadata

## Final Checkpoint: RIVF Submission Ready

- [ ] `./init.sh` pass.
- [ ] `./scripts/verify.sh` pass.
- [ ] Frontend production build pass when Task 10 is included; otherwise the P1 UI deferral is recorded.
- [ ] Code/evaluator are reproducible without secrets; full-result reproduction declares the authorized custodian-held input/label package and matching hashes.
- [ ] Data rights, privacy, limitations and no-endorsement statements are approved.
- [ ] Paper is English, IEEE A4, no more than 6 pages, and ready for EDAS by 2026-07-31.
- [ ] Originality, no-prior-publication, no-concurrent-submission, all-author approval, EDAS cutoff and timezone are rechecked against the live CFP.
- [ ] `feature_list.json` and `claude-progress.md` contain dated verification evidence.

## Cut Order If Time Runs Short

- [ ] Keep Tasks 1-9 and 12-14 as the minimum defensible paper path; run Task 11 only when its gate is green.
- [ ] Cut public URL polish before cutting benchmark, evaluator, provenance or statistics.
- [ ] Report LLM baseline as unavailable rather than replacing it with an undocumented provider.
- [ ] If rights or independent labels fail, stop the RIVF claim and label the result an internal prototype instead of submitting unsupported evidence.
