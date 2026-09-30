# Implementation Plan: SalePilot-R cho RIVF 2026 Track 2

## Overview

Chuyển SalePilot từ một hackathon chatbot/demo thành một **hybrid AI decision-support system** cho tư vấn sản phẩm điện máy bằng tiếng Việt. Hệ thống phải giúp khách đưa ra quyết định dưới các ràng buộc thực tế (ngân sách, kích thước, diện tích, công suất, tính năng), hỏi ngược khi thiếu thông tin, chỉ dùng dữ liệu có provenance, và biết từ chối khi không đủ bằng chứng.

Đây là hướng phù hợp với RIVF 2026 Track 2: **AI Applications**, cụ thể là AI-based decision support, explainable AI in applications, real-world deployment, và challenges of scaling/integration. Bài báo không nên tuyên bố một mô hình nền tảng mới hoặc gọi mọi đường chạy là multi-agent. Đóng góp có thể kiểm chứng nên là một pipeline **constraint-first, evidence-grounded, hybrid agentic** cho ngữ cảnh bán lẻ Việt Nam. CFP tham chiếu: <https://rivf2026.org/call-for-papers.html>.

Theo CFP tại thời điểm lập plan: bài bằng tiếng Anh, IEEE A4, tối đa 6 trang, deadline dự kiến **2026-07-31**. Ngày hiện tại là 2026-07-23, nên kế hoạch có critical path 8 ngày và một cổng go/no-go về quyền sử dụng dữ liệu.

## Track 2 Alignment

| Chủ đề Track 2 | Cách SalePilot-R liên hệ | Bằng chứng phải tạo |
|---|---|---|
| AI for real-world applications | Tư vấn mua hàng theo catalog/policy bằng tiếng Việt qua Web Chat; Zalo/MCP là integration seams hiện có nhưng không nằm trong evaluation claim mặc định | Web API demo end-to-end, deployment manifest, latency/load report |
| AI-based decision support | Parse need, hỏi slot còn thiếu, lọc constraint cứng, xếp hạng top-3 và trade-off | Benchmark, baselines, constraint violation rate; judged-pool nDCG chỉ khi Task 11 enabled |
| Explainable/interpretable AI | Mỗi đề xuất có constraint status, score components, nguồn SKU/row/snapshot và lý do loại ứng viên | Structured decision contract, human faithfulness evaluation |
| Deployment-oriented AI prototype | Offline fallback, API, Mongo/Postgres/snapshot, Docker, channel integration | Clean-start run, `/health`, p50/p95, failure report; không gọi là observed production deployment |
| Scaling/integration challenges | Category registry, repository abstraction, additive Chat API contract, request-scoped trace; MCP/Zalo regression-only nếu không mở rộng scope | Contract tests, concurrency test, catalog version manifest |

## Research Framing

### Working title

**Constraint-First Grounding for Explainable Vietnamese Retail Decision Support: A Hybrid Agentic System**

### Research questions and hypotheses

- **RQ1:** Category-aware need extraction plus fail-closed constraint ranking có cải thiện category/slot accuracy và hard-constraint satisfaction so với keyword/filter và price-popularity baselines không?
- **RQ2:** Evidence-linked explanations có cải thiện factuality, usefulness và faithfulness của lời giải thích so với chỉ trả top-3 hoặc prose của LLM không?
- **RQ3:** Hybrid routing (deterministic path cho quyết định có cấu trúc, agent path cho câu hỏi mơ hồ/policy) có giữ latency và reliability phù hợp triển khai thực tế không?
- **H1:** Proposed system có constraint violation rate thấp hơn mọi baseline và không làm tăng tỷ lệ abstention không hợp lý quá ngưỡng đã chốt.
- **H2 (conditional):** Nếu human-study gate được duyệt trước implementation freeze, structured evidence và score decomposition tăng điểm explanation faithfulness so với condition giữ nguyên ranking/word budget nhưng ẩn evidence.
- **H3:** Offline/fast path được đo đối chiếu với product target p95 recommendation dưới 3 giây và compare dưới 5 giây trên môi trường đã ghi rõ; không đạt target vẫn là một kết quả nghiên cứu hợp lệ.

### Claims không được phép suy diễn

- Không gọi `used_agents` là bằng chứng của nhiều LLM agent nếu đường chạy thực tế là Python rule engine hoặc fast path.
- Không gọi `match_score` hiện tại là xác suất hoặc confidence nếu chưa calibration.
- Không so sánh model/provider khác nhau khi catalog, prompt, budget và execution mode không được cố định.
- Không phát hành catalog, policy text hoặc trajectory raw nếu chưa có quyền sử dụng và cơ chế loại PII.
- Không dùng conversion/giảm chi phí như kết quả nghiên cứu nếu chưa có user study hoặc production counterfactual hợp lệ.

## Current-State Baseline

Static audit đã thực hiện, chưa chạy `init.sh` hoặc `scripts/verify.sh` để giữ đúng plan mode vì các script tạo database, leads, memories và trajectories.

Các blocker phải xử lý trước benchmark:

- `README.md`, `claude-progress.md` và `verify.sh` mô tả catalog workbook 8.746 SKU/14 ngành với code cũ, trong khi `backend/app/catalog/categories.py` hiện mô tả crawl khác, nhiều category code khác và có hỗ trợ laptop.
- `backend/app/config.py` ưu tiên Postgres, `repository.py` có fallback Mongo/snapshot, nhưng `backend/data/catalog_snapshot.json` và workbook nguồn không có trong checkout; `products.json` là thế hệ tủ lạnh cũ.
- `import_spec_catalog.py` và `categories.normalize_product()` hiện không cùng signature/schema.
- `scripts/verify.sh` có assertion mâu thuẫn với registry hiện tại, nên pass/fail hiện chưa phải evidence khoa học.
- `run_bag.py` dùng mutable global, có nguy cơ trộn trace giữa concurrent requests.
- `trajectory/export.py` lưu raw user text, external ID và memory; chưa có model/catalog/prompt/version/latency metadata.
- `catalog_domain.py` hard-code source là MongoDB ở một số response dù repository có nhiều backend.
- Chưa có held-out benchmark, baseline công bằng, aggregate metrics, confidence interval, human evaluation hoặc paper artifact.
- Quyền tái sử dụng workbook, crawl và policy corpus cho publication chưa được chứng minh trong repository.

## Architecture Decisions

1. **Một canonical catalog version:** Experiments pin một deterministically serialized snapshot và normalized hash. Postgres/Mongo chỉ là mirrors/deployment backends và phải báo cùng dataset identity khi được dùng; không trộn crawl, workbook và refrigerator legacy.
2. **Hybrid thay vì LLM-only:** Rule/parser/ranker xử lý constraint và provenance; LLM chỉ xử lý diễn đạt hoặc intent mơ hồ. Paper mô tả đúng execution mode.
3. **Fail-closed cho constraint cứng:** Spec thiếu không được tính là đạt. Kết quả phải ghi `unknown` hoặc abstain, không âm thầm bỏ qua giới hạn.
4. **Contract additive:** Thêm trường `decision` có version vào `ChatResponse`; giữ các trường cũ (`reply`, `trace`, `used_agents`, `run_id`) để không phá frontend/MCP hiện tại.
5. **Experiment runner ngoài production path:** Baselines, seed, repeat, scoring và thống kê nằm dưới `experiments/`; production code chỉ expose những seam cần thiết để chọn execution mode và thu metadata.
6. **Benchmark độc lập với implementation:** Query, expected slots, hard constraints và expected action được đóng băng trước khi chạy hệ thống; không dùng output của engine để tự tạo ground truth.
7. **Privacy boundary rõ ràng:** Benchmark chỉ dùng synthetic/pseudonymous IDs; research export redacts PII; CRM, memory và raw trajectory không được coi là dữ liệu nghiên cứu mặc định.
8. **Offline-first reproducibility:** Không có API key vẫn chạy được proposed system và các baseline deterministic. LLM condition nếu không có key phải ghi `unavailable`, không thay bằng kết quả tưởng tượng.

## Dependency Graph

```text
Data rights + research protocol
    |
    v
Canonical snapshot + raw/normalized hashes
    |
    v
Dev benchmark schema --> common evaluator --> isolated telemetry
                                               |
                                               v
                              baseline/proposed tracer pilot
                                               |
                                               v
                              sealed test custody record
                              (awaiting code freeze)
                                               |
                    +--------------------------+------------------+
                    |                                             |
                    v                                             v
       fail-closed decision contract                  implementation/runtime API
                    |                                             |
                    +--------------------------+
                                               |
                                               v
                            final code/condition freeze
                                               |
                    +--------------------------+------------------+
                    |                          |                 |
                    v                          v                 v
             optional blinded human      release inputs ->   local deployment/
             study                        predictions ->      load evidence
                                          labels -> stats          |
                    +--------------------------+----------------+
                                               v
                                      IEEE paper/repro pack
```

## Scope and Priority

### P0: Must complete for a defensible RIVF submission

Tasks 1-9 và 12-14: rights/data gate, canonical runtime, tracer pilot, sealed benchmark, evaluator, at least two baselines, privacy-safe metadata, provenance contract, statistics, local deployment evidence và paper.

### P1: Complete if the critical path is green

Task 10 UI polish, Task 11 human study khi rater/power gate green, public URL/production hardening ngoài local scope của Task 13, và LLM baseline nếu chưa có provider/budget cố định.

### Stop conditions

- Nếu không có written permission hoặc một alternative rights-cleared dataset trước Checkpoint 1, không được viết claim publication trên challenge data. Chuyển thành internal prototype plan hoặc thay dataset.
- Nếu canonical catalog không tái tạo được từ clean environment, không chạy full experiment; chỉ giữ pilot để debug.
- Nếu không có raters theo protocol trước implementation freeze, hủy H2/Task 11 trước khi chạy test; Task 12 vẫn chạy objective metrics và paper không có human-effect claim.
- Không public deploy khi các endpoint chứa lead/memory/run/outbox còn chưa có access control; local measurement không được mô tả là production-secure deployment.

### Feasibility verdict

Kế hoạch trước deadline 2026-07-31 là **conditional/high-risk**, không phải estimate đảm bảo. Chỉ proceed nếu ngay trong 2026-07-23 đã có canonical source, data custodian, quyền publication rõ ràng và ít nhất một người viết paper song song với engineering. Mặc định tắt Task 10 và Task 11; chỉ bật lại khi P0 ahead of schedule.

Hard go/no-go dates:

- Task 2 chưa green cuối 2026-07-24: không target kỳ nộp này.
- Tracer pilot Task 6 chưa green cuối 2026-07-26: không mở full benchmark.
- Seal record và Chat decision API chưa green trưa 2026-07-28: không chạy test.
- Prediction/result hashes chưa frozen trưa 2026-07-29: không nộp paper với số liệu chưa kiểm chứng.
- 2026-07-31 là upload buffer theo cutoff/timezone được recheck, không phải ngày thêm feature.

## Eight-Day Critical Path

| Date | Critical work | Exit condition |
|---|---|---|
| 2026-07-23 | Task 1, xin quyền dữ liệu và chốt protocol/related-work gap | Rights gate green hoặc fallback dataset được chọn |
| 2026-07-24 | Task 2, đồng thời tuyển/brief annotators | Canonical import, fallback và smoke pass |
| 2026-07-25 | Tasks 3-4 | Dev schema/evaluator tracer fixtures pass |
| 2026-07-26 | Tasks 5-6 | Safe telemetry và end-to-end tracer pilot pass |
| 2026-07-27 | Task 7; chuẩn bị Task 13 song song | Seal record ở trạng thái `awaiting_code_freeze` |
| 2026-07-28 | Tasks 8-9; Task 11 chỉ khi gate green | Decision API và optional human pool sẵn sàng |
| 2026-07-29 | Task 12; Task 10 chỉ khi critical path green | One-shot test tables, CIs và error analysis frozen |
| 2026-07-30 | Hoàn tất Tasks 13-14 và author review | IEEE PDF/reproducibility pack submission-ready |
| 2026-07-31 | Buffer, final verification và EDAS upload trước live cutoff | Submission receipt và archived hashes; không thêm feature |

Paper outline, related work và methods draft bắt đầu từ Task 1 và được cập nhật hằng ngày; Task 14 chỉ khóa nội dung theo frozen results.

## Task List

### Phase 0: Research and Data Foundation

## Task 1: Freeze research protocol and data-rights gate

**Description:** Ghi rõ research questions, hypotheses, primary/secondary metrics, baselines, split, execution modes, privacy boundary và quyền sử dụng dữ liệu. Đăng ký một feature `rivf-001` sau khi con người duyệt plan, nhưng vẫn tuân thủ rule chỉ có một feature `in_progress`.

**Acceptance criteria:**
- [ ] `docs/RIVF_TRACK2_PROTOCOL.md` định nghĩa scope-dependent title/RQs, primary endpoint, causal controls, sample-size/target-CI rationale, baselines, exclusions, human-study go/no-go, related-work gap và originality/concurrent-submission gate trước benchmark.
- [ ] `docs/DATASET_CARD.md` và `experiments/manifest.json` có asset-level rights matrix cho catalog, policy, scenarios, derived labels và outputs; ghi raw-source hash, permission/derivative-release decision, PII policy và trạng thái normalized hash đang chờ Task 2.
- [ ] `scripts/validate_research_manifest.py` fail khi thiếu hash, rights status, split seed hoặc có path ngoài repo không được khai báo.

**Verification:**
- [ ] `python scripts/validate_research_manifest.py experiments/manifest.json` exits 0 cho manifest hợp lệ và non-zero cho fixture thiếu quyền/hash.
- [ ] Human review xác nhận bằng văn bản canonical dataset được phép dùng cho submission; nếu chưa, ghi `BLOCKED` và không chạy full experiment.
- [ ] `git diff --check` pass sau khi tài liệu được duyệt.

**Dependencies:** None.

**Files likely touched:**
- `docs/RIVF_TRACK2_PROTOCOL.md`
- `docs/DATASET_CARD.md`
- `experiments/manifest.json`
- `scripts/validate_research_manifest.py`
- `feature_list.json`

**Estimated scope:** Medium: 3-5 files.

## Task 2: Reconcile one canonical catalog pipeline

**Description:** Chọn generation được phép sử dụng và tạo một canonical, deterministically serialized snapshot cho experiments. Database parity và deployment backend được đo riêng ở Task 13; Task này chỉ cần một nguồn nghiên cứu tái lập được.

**Acceptance criteria:**
- [ ] Importer và `normalize_product()` dùng cùng input contract; canonical sorting/serialization tạo ổn định `raw_source_hash` và `normalized_catalog_hash` cùng counts/schema version trong manifest.
- [ ] Experiment profile pin `catalog_backend=snapshot`; refrigerator/workbook/crawl legacy không được load ngầm và claim scope tự thu hẹp theo category thực có trong manifest.
- [ ] `verify.sh` không còn assertion mâu thuẫn giữa laptop/unsupported/category codes và có deterministic snapshot smoke độc lập với cloud database.

**Verification:**
- [ ] Từ `backend/`, `python -m scripts.import_spec_catalog --excel <authorized-catalog>` tạo manifest/hash đúng expected values.
- [ ] `./scripts/verify.sh` pass với experiment snapshot trong offline environment.
- [ ] Hai clean imports cho cùng normalized hash, category counts và representative SKU set; một byte/order mutation có expected hash change.

**Dependencies:** Task 1.

**Files likely touched:**
- `backend/scripts/import_spec_catalog.py`
- `backend/app/catalog/categories.py`
- `backend/app/catalog/repository.py`
- `experiments/manifest.json`
- `scripts/verify.sh`

**Estimated scope:** Medium: 3-5 files.

### Checkpoint: Data Foundation

- [ ] Human duyệt rights/data gate.
- [ ] Canonical catalog import và fallback reproducible.
- [ ] `./scripts/verify.sh` pass từ clean/isolated environment.
- [ ] Chưa viết hoặc chạy paper result nếu một mục trên còn thiếu.

### Phase 1: Independent Benchmark and Evaluation

## Task 3: Define benchmark contract and tracer pilot

**Description:** Tạo benchmark JSONL độc lập với engine và một pilot nhỏ đủ đi xuyên suốt từ episode đến metric. Pilot chỉ là development data; full test labels chưa được mở cho implementation.

**Acceptance criteria:**
- [ ] Schema có `episode_id`, turns, category, expected slots, per-constraint `hardness`/`missing_policy`, expected action, accepted clarification intents, response branches, max turns, allowed evidence và difficulty.
- [ ] Pilot có 16-24 episode dev, gồm tối thiểu 4 category thực có trong manifest, multi-turn, no-diacritic/typo, impossible constraint, unsupported và stock/policy cases.
- [ ] Validator phát hiện duplicate ID, PII, category ngoài manifest, overlap với `need_scenarios.json`/verify fixtures và system-generated SKU labels.

**Verification:**
- [ ] `python scripts/validate_benchmark.py experiments/benchmark/dev.jsonl --manifest experiments/manifest.json` exits 0.
- [ ] Validator in distribution theo category, action, hardness, single/multi-turn và split seed.
- [ ] Manual review ít nhất 8 episode xác nhận branch responses/accepted clarification intents không lấy từ implementation output.

**Dependencies:** Task 2.

**Files likely touched:**
- `experiments/benchmark/schema.json`
- `experiments/benchmark/dev.jsonl`
- `experiments/benchmark/dev_annotations.jsonl`
- `experiments/benchmark/ANNOTATION.md`
- `scripts/validate_benchmark.py`

**Estimated scope:** Medium: 3-5 files.

## Task 4: Build common evaluator and frozen metric implementation

**Description:** Xây evaluator dùng chung cho tracer pilot và mọi condition sau đó. Multi-turn scoring phải dùng cùng user-response map, accepted-question equivalence và turn budget; ranking metrics chỉ tính trên judged pool.

**Acceptance criteria:**
- [ ] Evaluator tính category accuracy, slot micro-F1, clarification success/turns, hard-constraint violation rate, abstention precision/recall, evidence correctness và p50/p95; nDCG@3 chỉ bật khi có graded judged labels.
- [ ] Output JSONL có `system_id`, `episode_id`, `condition`, `run_index`, `catalog_hash`, `execution_mode`, prediction, latency, state-isolation ID và errors; không silently drop failures.
- [ ] Fixture tests chứng minh hard/soft/missing policies, shared multi-turn budget và unjudged ranking items không bị tính là relevant.

**Verification:**
- [ ] `python -m experiments.evaluate.runner --input experiments/fixtures/results.jsonl --labels experiments/benchmark/dev_annotations.jsonl` tạo aggregate expected.
- [ ] `python -m unittest experiments.evaluate.test_metrics` pass với hand-calculated fixtures.
- [ ] Chạy evaluator hai lần trên cùng raw input cho cùng aggregate hash và cùng clarification outcome.

**Dependencies:** Task 3.

**Files likely touched:**
- `experiments/evaluate/schemas.py`
- `experiments/evaluate/metrics.py`
- `experiments/evaluate/runner.py`
- `scripts/evaluate.py`
- `experiments/evaluate/test_metrics.py`

**Estimated scope:** Medium: 3-5 files.

### Checkpoint: Benchmark Contract

- [ ] Dev schema, annotation semantics and evaluator result schema are compatible.
- [ ] Multi-turn user-response map and hard/soft/missing policy fixtures pass.
- [ ] No full test input/label is visible to implementation yet.

## Task 5: Make experiment execution request-scoped and privacy-safe

**Description:** Tạo một experiment runtime seam duy nhất trước khi có pilot result. Deterministic systems gọi pure domain functions; condition cần `run_agent` chạy trong isolated subprocess/temp database và không đi qua gateway/channel endpoints.

**Acceptance criteria:**
- [ ] `run_bag` là request/task-scoped; concurrent runs không trộn trace, final reply, active skills hoặc subagent results.
- [ ] `experiments/runtime.py` không gọi gateway/CRM/outbox/scheduler cho deterministic conditions; full-agent condition dùng temp DB, redirected trajectory dir, scheduler disabled, unique namespace và disposable process.
- [ ] Runtime record có commit + source-bundle/diff hash, catalog/model/prompt/config metadata; export redact PII và scan result, redirected trajectories cùng temp DB before disposal.

**Verification:**
- [ ] Stress test 20-50 concurrent offline runs chứng minh trace/result đúng namespace và không có cross-run SKU/reply.
- [ ] Chạy cùng pilot theo hai condition order/repeat order và chứng minh không có state carry-over; PII scan result/redirected trajectory/temp DB pass.
- [ ] `./scripts/verify.sh` và trajectory read-back pass sau khi isolation thay đổi.

**Dependencies:** Tasks 2 và 4.

**Files likely touched:**
- `backend/app/agent/run_bag.py`
- `backend/app/agent/trajectory/export.py`
- `experiments/runtime.py`
- `experiments/telemetry.py`
- `experiments/test_runtime.py`

**Estimated scope:** Medium: 3-5 files.

## Task 6: Add controlled systems and run tracer pilot

**Description:** Expose execution conditions có thể lặp lại trên cùng dev pilot, sau khi evaluator và telemetry an toàn. Proposed system được gọi là hybrid constraint-first; multi-agent/LLM là condition riêng.

**Acceptance criteria:**
- [ ] Common adapter chạy được tối thiểu `B0_price_popularity`, `B1_lexical_filter`, và `S_hybrid_constraint`; `B2_single_agent` chỉ chạy khi provider/key có thật và ghi unavailable nếu thiếu.
- [ ] Nếu H2 active, `S_hybrid_no_evidence` là ablation bắt buộc, giữ nguyên ranking/prose budget nhưng ẩn evidence; no-memory/no-clarification được khai báo trước nếu dùng.
- [ ] Mỗi condition/repeat dùng fresh state, unique pseudonymous IDs, cùng catalog/turn budget/timeout, order được randomize, và ghi model/provider/prompt/seed/route.

**Verification:**
- [ ] `python scripts/run_pilot.py --config experiments/conditions.json --split dev` tạo common JSONL cho mọi condition khả dụng.
- [ ] Chạy condition theo hai thứ tự và deterministic repeat cho cùng decision/result hash; không có state carry-over.
- [ ] Pilot report hiển thị rõ unavailable/error thay vì imputing điểm và có một end-to-end data-to-metric trace.

**Dependencies:** Tasks 4-5.

**Files likely touched:**
- `experiments/systems.py`
- `experiments/baselines.py`
- `experiments/conditions.json`
- `backend/app/agent/graph.py`
- `scripts/run_pilot.py`

**Estimated scope:** Medium: 3-5 files.

### Checkpoint: Tracer Bullet

- [ ] Dev episode đi qua proposed và hai baseline đến aggregate metric trước khi full benchmark được annotate.
- [ ] Trace, state, catalog hash và privacy scan pass.
- [ ] Clarification branch và hard/soft/missing policy đã được review trên pilot.

## Task 7: Register a sealed held-out benchmark

**Description:** Sau tracer pilot, custodian mở rộng benchmark theo sample-size/target-CI rationale và giữ raw test inputs/labels ngoài implementation tree. Repository chỉ nhận seal record/hashes, đủ để Tasks 8-9 tiếp tục mà không nhìn test data.

**Acceptance criteria:**
- [ ] Kích thước và phân tầng category/difficulty/multi-turn được suy ra từ target CI hoặc minimum detectable effect; scope claim tự thu hẹp nếu canonical catalog có ít category.
- [ ] Objective labels có hai annotator/adjudication nếu gate green; fallback một annotator + independent audit được predeclare và không dùng để claim inter-rater agreement.
- [ ] `SEAL_RECORD.json` ghi input/label hashes, schema, counts/distribution, overlap/PII audit, annotation status và chain-of-custody; raw files không tồn tại trong workspace.

**Verification:**
- [ ] `python scripts/validate_benchmark_seal.py experiments/benchmark/SEAL_RECORD.json --manifest experiments/manifest.json` pass với trạng thái `awaiting_code_freeze`.
- [ ] Custodian chạy validator/agreement trên private workspace và ký summary/hash; repository validator phát hiện seal thiếu hash, audit hoặc release order.
- [ ] Release protocol bắt buộc: code/condition hash -> release inputs -> prediction hash -> release labels -> score; không có đường tắt đọc labels.

**Dependencies:** Tasks 3, 4 và 6.

**Files likely touched:**
- `experiments/benchmark/SEAL_RECORD.json`
- `experiments/benchmark/ANNOTATION.md`
- `docs/DATASET_CARD.md`
- `scripts/validate_benchmark_seal.py`
- `scripts/score_annotation_agreement.py`

**Estimated scope:** Medium: 3-5 files.

### Checkpoint: Benchmark Freeze

- [ ] Test inputs và labels không lộ trước implementation tuning; custodian chỉ release raw inputs sau code/condition hash, rồi release labels sau prediction hash.
- [ ] Không có overlap với existing scenarios, verify strings hoặc prompt examples.
- [ ] Human-study gate và ranking judged-pool policy được chốt trước full run.

### Phase 2: Evidence-Grounded Product Slice

## Task 8: Define fail-closed decision domain contract

**Description:** Tách kết quả quyết định có cấu trúc khỏi prose reply ngay tại domain layer. Contract nội bộ này chuẩn hóa constraint status, score components và provenance trước khi thay đổi runtime hoặc public API.

**Acceptance criteria:**
- [ ] `DecisionResult` có schema version, parsed need, missing slots, candidate/rejection counts, top-3, source manifest/hash và disclaimer.
- [ ] Production `Slot`/need model map mỗi constraint sang explicit `hardness` và `missing_policy` (`exclude`, `clarify`, `abstain`, hoặc `allow_unknown`) từ protocol; top-3 item có matched/violated/unknown status, score components, reason và SKU/row provenance.
- [ ] Source label lấy từ repository/manifest thực tế; không còn chuỗi MongoDB cố định khi source là Postgres/snapshot.

**Verification:**
- [ ] Từ `backend/`, `python -m unittest tests.test_decision_contract` pass với complete, impossible-budget, missing-spec và unsupported fixtures.
- [ ] Golden JSON fixture validate được bằng schema version và không chứa prose-only field bắt buộc.
- [ ] Existing `recommend_top3` regression tests vẫn pass hoặc được migrate với documented contract change.

**Dependencies:** Tasks 6 và 7.

**Files likely touched:**
- `backend/app/agent/decision.py`
- `backend/app/agent/catalog_domain.py`
- `backend/app/catalog/categories.py`
- `backend/tests/test_decision_contract.py`

**Estimated scope:** Medium: 3-5 files.

## Task 9: Propagate decision through runtime and Chat API

**Description:** Truyền `DecisionResult` qua offline, fast-path và full-agent recommendation paths của `/chat` và `/chat/stream` mà không parse lại prose. MCP/Zalo giữ behavior cũ và chỉ cần regression không vỡ, không được tính vào decision-contract claim.

**Acceptance criteria:**
- [ ] `/chat` và `/chat/stream` ở offline/fast/full-agent modes trả cùng `decision` schema; non-recommendation path trả `null`/không có field, không dựng decision từ reply text.
- [ ] `ChatResponse` thêm optional `decision` và giữ nguyên semantics của `reply`, `trace`, `used_agents`, `run_id`; tool result không bị truncate trước khi tạo decision.
- [ ] Response và trajectory/research record có cùng decision hash, execution mode và catalog hash.

**Verification:**
- [ ] Từ `backend/`, `python -m unittest tests.test_chat_decision_api` pass cho sync chat, SSE stream, offline, fast, full-agent stub và non-recommendation fixtures.
- [ ] OpenAPI thể hiện additive field; một legacy client fixture chỉ đọc `reply` vẫn pass.
- [ ] HTTP smoke xác nhận decision hash/provenance khớp trajectory cho representative query.

**Dependencies:** Tasks 7-8.

**Files likely touched:**
- `backend/app/agent/graph.py`
- `backend/app/agent/offline.py`
- `backend/app/agent/tools/catalog.py`
- `backend/app/api/chat.py`
- `backend/tests/test_chat_decision_api.py`

**Estimated scope:** Medium: 3-5 files.

### Checkpoint: Safe Decision Contract

- [ ] Domain fixtures chứng minh hard constraints fail-closed và provenance đúng source.
- [ ] Offline/fast/full recommendation paths dùng cùng schema version.
- [ ] API change additive và response/trajectory hashes khớp nhau.

## Task 10: Ship evidence-first chat UI slice

**Description:** Hiển thị cho người dùng tại sao top-3 được chọn, giới hạn nào đã đáp ứng/chưa biết, và nguồn dữ liệu nào cần kiểm tra lại. UI chỉ render decision từ server, không tự suy luận số liệu.

**Acceptance criteria:**
- [ ] Desktop và mobile hiển thị top-3 evidence card, matched/unknown constraints, trade-off và source snapshot/version bên cạnh Agent Trace.
- [ ] Unsupported, no-match và stock-unknown có trạng thái riêng, không tạo cảm giác còn hàng hoặc chắc chắn giả.
- [ ] Existing chat history/session flow và customer-facing Vietnamese copy không bị phá; UI không hiển thị PII/internal prompt và API base không hard-code production host ngoài plan.

**Verification:**
- [ ] `cd frontend && npm run build` pass.
- [ ] Browser check với một recommendation, một missing-slot question và một unsupported query; console/network không có lỗi.
- [ ] Manual mobile viewport check xác nhận card không overflow và evidence có keyboard/accessibility labels.

**Dependencies:** Task 9.

**Files likely touched:**
- `frontend/lib/api.ts`
- `frontend/app/chat/page.tsx`
- `frontend/components/DecisionEvidence.tsx`
- `frontend/app/globals.css`

**Estimated scope:** Medium: 3-5 files.

### Checkpoint: Evidence-First User Flow

- [ ] Một query tiếng Việt đi từ parse need đến decision JSON, prose reply và UI evidence.
- [ ] Hard constraint, unknown spec, unsupported request và stock disclaimer đều có regression test.
- [ ] Concurrent trace và research export không lẫn dữ liệu.
- [ ] Browser check pass trên desktop/mobile.

### Phase 3: Human Evaluation and Empirical Results

## Task 11: Run blinded relevance and explanation-faithfulness study

**Description:** Tạo pooled evaluation trên một tập test nhỏ nhưng có chất lượng: các annotator đánh giá relevance của pooled candidates/top recommendations, tính đúng nguồn, usefulness và faithfulness của explanation mà không biết system nào sinh ra output.

**Acceptance criteria:**
- [ ] Cỡ pool, số rater và phân tầng được lấy từ power/target-CI rationale của Task 1; nếu gate disabled thì task được hủy có chủ đích trước test, không để dependency treo.
- [ ] Khi enabled, pool hợp nhất top-3 từ mọi condition khả dụng, randomize/blind system label, có cùng rubric/word budget và condition `S_hybrid_no_evidence`; hai Vietnamese domain raters chấm relevance, factual/source correctness, faithfulness và preference.
- [ ] Protocol/rubric hash khớp bản frozen từ Task 1; ghi consent, compensation/role, agreement/adjudication, unjudged-item policy và không chứa PII.

**Verification:**
- [ ] `python scripts/score_human_eval.py experiments/benchmark/relevance.jsonl` tạo score, agreement và adjudication report.
- [ ] Synthetic fixture test kiểm tra rater IDs không lộ system condition và source claim sai bị đánh dấu.
- [ ] Human review xác nhận output pool không dùng candidate ngoài catalog manifest.

**Dependencies:** Tasks 6, 7 và 9, chỉ khi human-study gate trong Task 1 là `enabled`.

**Files likely touched:**
- `docs/HUMAN_EVAL_PROTOCOL.md`
- `experiments/benchmark/relevance.jsonl`
- `experiments/evaluate/human.py`
- `scripts/score_human_eval.py`
- `experiments/evaluate/test_human.py`

**Estimated scope:** Medium: 3-5 files.

## Task 12: Execute full experiment and statistical analysis

**Description:** Chạy test split frozen cho all available conditions, sau đó tạo aggregate results có confidence intervals và error taxonomy. Phân tích phải được quyết định trước, không cherry-pick query/category.

**Acceptance criteria:**
- [ ] Deterministic conditions chạy ít nhất một lần; stochastic LLM conditions chạy tối thiểu ba repeats hoặc được ghi unavailable vì budget/key; nếu Task 11 disabled thì không báo human/nDCG claim.
- [ ] Báo cáo có bootstrap 95% CI, paired comparison, effect size, category/difficulty breakdown, failure/timeout count, route/fallback coverage và error taxonomy.
- [ ] `CHAIN_OF_CUSTODY.json` ghi final code/condition/source hashes, input release, prediction hash, label release và scoring order; aggregate artifacts không có secret/PII hoặc unmarked post-hoc rerun.

**Verification:**
- [ ] Sau code/condition freeze, `python scripts/run_rivf_experiment.py --config experiments/manifest.json --inputs <custodian-test-inputs> --predict-only` khóa prediction hash trước label release hoặc tạo failure report đầy đủ.
- [ ] Sau custodian release, `python scripts/summarize_results.py experiments/results/raw --labels <sealed-labels>` tạo bảng đúng protocol và cùng aggregate hash khi chạy lại.
- [ ] Independent reviewer kiểm tra mọi con số trong paper đều truy được về raw episode/result.

**Dependencies:** Tasks 5, 7 và 9; Task 11 chỉ là optional input khi human gate enabled.

**Files likely touched:**
- `experiments/run.py`
- `experiments/stats.py`
- `scripts/run_rivf_experiment.py`
- `scripts/summarize_results.py`
- `experiments/results/CHAIN_OF_CUSTODY.json`

**Estimated scope:** Medium: 3-5 files.

### Checkpoint: Empirical Evidence

- [ ] Có ít nhất một bảng so sánh proposed với hai baseline trên test split frozen.
- [ ] Có CI/effect size, không chỉ một điểm trung bình.
- [ ] Có human evaluation hoặc limitation statement nếu study chưa đủ điều kiện.
- [ ] Error analysis kiểm tra riêng hard constraints, unsupported/stock hallucination và missing data.

### Phase 4: Deployment and Paper

## Task 13: Produce real-world deployment and scaling evidence

**Description:** Làm cho local deployment tái lập được và đo đúng các yêu cầu ứng dụng: health/readiness, fallback, concurrency và latency. Không dùng public URL như bằng chứng duy nhất.

**Acceptance criteria:**
- [ ] Clean local stack dùng service DNS/health dependency đúng, không cần cloud secret cho offline path; `/health` trả catalog source/version/hash và dependency status.
- [ ] Workload mix, warm-up, sample count, concurrency levels, cold/warm cache, DB mode, hardware và percentile method được freeze; p50/p95, throughput, error rate, route/fallback coverage được báo.
- [ ] Recommendation/compare p95 targets (<3s/<5s) được ghi là product target pass/fail, không phải điều kiện để che giấu một kết quả H3 âm; concurrent requests không trộn trace và log không chứa raw PII.

**Verification:**
- [ ] `docker compose config` pass với sanitized `.env`; `docker compose up --build` khởi động healthy.
- [ ] `curl -s http://127.0.0.1:8000/health` và chat/compare smoke pass.
- [ ] `python experiments/load_test.py --config experiments/manifest.json` tạo p50/p95/error report; nếu không đạt target phải ghi nguyên nhân và mitigation.

**Dependencies:** Tasks 2, 5 và 9.

**Files likely touched:**
- `docker-compose.yml`
- `.env.example`
- `backend/app/config.py`
- `backend/app/main.py`
- `experiments/load_test.py`

**Estimated scope:** Medium: 3-5 files.

## Task 14: Create IEEE paper and reproducibility pack

**Description:** Viết bài tiếng Anh theo IEEEtran A4 tối đa 6 trang, dùng đúng kết quả đã frozen. Bài phải có data statement, ethics/limitations, deployment details và reproducibility path kể cả khi source data không được phép phát hành.

**Acceptance criteria:**
- [ ] `paper/main.tex` có abstract, related work, system/method, benchmark, baselines, metrics, results, error analysis, deployment, limitations/ethics và conclusion; mọi claim gắn với RQ/evidence.
- [ ] `docs/REPRODUCIBILITY.md` chỉ dẫn clean run, manifest/hash, exact commands, environment versions, restricted-data procedure và expected artifacts.
- [ ] `docs/LIMITATIONS_AND_ETHICS.md` nêu data rights, privacy, no-stock limitation, annotator protocol, external validity và không imply retailer endorsement.

**Verification:**
- [ ] `latexmk -pdf -halt-on-error paper/main.tex` pass với `IEEEtran` và A4.
- [ ] `pdfinfo paper/main.pdf` xác nhận không quá 6 trang; references/figures/tables compile và không tràn.
- [ ] Author checklist đối chiếu từng claim với raw hash, xác nhận originality/no prior publication/no concurrent submission/all-author approval, recheck EDAS cutoff/timezone, và kiểm tra không có dữ liệu/secret bị phát hành.

**Dependencies:** Tasks 12 và 13.

**Files likely touched:**
- `paper/main.tex`
- `paper/references.bib`
- `paper/README.md`
- `docs/REPRODUCIBILITY.md`
- `docs/LIMITATIONS_AND_ETHICS.md`

**Estimated scope:** Medium: 3-5 files.

### Checkpoint: Submission Ready

- [ ] Full verification: backend smoke, frontend build, benchmark validator, evaluator, deployment/load report.
- [ ] Paper <= 6 pages, English, IEEE A4, references complete.
- [ ] Data permission/alternative dataset and privacy statement đã được author duyệt.
- [ ] Public artifact chỉ chứa code, manifest, derived labels/results được phép phát hành; restricted data có hướng dẫn riêng.
- [ ] Originality, no-prior-publication, no-concurrent-submission, all-author approval, EDAS cutoff/timezone, PDF và source package được kiểm tra lại trên live CFP trước 2026-07-31.

## Parallelization Opportunities

- Sau Task 2, Task 3 (benchmark authoring) và phần chuẩn bị local Compose của Task 13 có thể làm song song; load measurement phải chờ Task 7.
- Task 4 evaluator và việc chuẩn bị annotation rubric trong Task 3 có thể review song song; Task 6 phải chờ evaluator và telemetry.
- Task 8 decision domain chỉ làm sau tracer pilot và sealed-label procedure của Task 7; Task 9 phải chờ cả hai.
- Task 10 UI chỉ làm sau Task 9 API contract; không tạo một response shape riêng ở frontend.
- Task 11 human study và Task 13 deployment có thể đo song song sau khi code/condition freeze và telemetry an toàn.
- Không parallelize thay đổi importer/schema, public API contract hoặc conditions manifest; đây là shared state và phải merge tuần tự.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Không có quyền publication cho challenge/crawl/policy data | High | Task 1 là hard gate; xin written permission hoặc thay bằng dataset rights-cleared; không phát hành raw data. |
| Ba thế hệ catalog đang lệch nhau | High | Chọn một canonical manifest/hash, sửa importer trước benchmark, legacy không được fallback ngầm. |
| Không có annotator/domain expert đủ thời gian | High | Objective-label gate và human-faithfulness gate tách riêng; hủy Task 11 trước test nếu không đủ rater, không dựng claim thay thế. |
| LLM nondeterminism, API cost hoặc downtime | Medium | Offline baseline bắt buộc, fixed model/config, repeats, ghi unavailable thay vì impute. |
| Missing spec làm lọt sản phẩm không thỏa constraint | High | Fail-closed, tách `unknown` khỏi `satisfied`, test impossible/missing-spec. |
| Raw PII lọt vào trajectory/result | High | Synthetic IDs, redaction scan, consent flag, retention/deletion policy, không dùng production chat làm benchmark. |
| p95 không đạt yêu cầu ứng dụng | Medium | Đo trước paper, giữ fast/offline path, cache/version catalog, báo trade-off thay vì giấu số liệu. |
| Scope 8 ngày quá lớn | High | P0 critical path, checkpoint go/no-go, cắt UI/public URL/LLM baseline trước khi cắt data/evaluator/paper evidence. |
| Reviewer xem đây chỉ là glue code | Medium | Đóng góp phải nằm ở constraint-first representation, evidence contract và controlled empirical comparison; liên hệ related work rõ ràng. |

## Open Questions

- Người sở hữu dataset có cho phép sử dụng kết quả và code cho bài IEEE/RIVF, và có cho phép phát hành derived benchmark không?
- Canonical source sẽ là workbook 14 ngành đã mô tả trong progress log, refrigerator snapshot, hay một dataset rights-cleared khác? Ai cung cấp file/hash bất biến?
- Có ít nhất hai người đánh giá tiếng Việt hiểu domain để gán slot và chấm explanation không?
- Có API key/ngân sách/model cố định cho condition single-agent LLM không? Nếu không, paper có chấp nhận chỉ báo cáo deterministic baselines không?
- Có cần public deployment URL cho mục tiêu RIVF, hay local reproducible deployment evidence là đủ?
- Ai duyệt research protocol, asset-level rights gate, human-study go/no-go và final claims trước khi nộp?

## Definition of Done

Một implementation chỉ được xem là hoàn tất khi:

1. User-visible flow hỏi đúng slot, lọc constraint fail-closed, trả evidence/provenance và abstain trung thực.
2. Benchmark độc lập, evaluator, baseline và statistical report chạy lại được trên một catalog manifest/hash.
3. Trace request-scoped, research export không PII, model/data/config metadata đầy đủ.
4. `./init.sh`, `./scripts/verify.sh`, deployment/load checks và frontend build nếu Task 10 được bật có evidence thực tế.
5. Paper <= 6 trang và mọi claim truy được tới raw result hoặc được ghi là limitation.
6. `feature_list.json` và `claude-progress.md` được cập nhật sau implementation checkpoints, với evidence chứ không chỉ code presence.
