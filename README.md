# SalePilot-R

**SalePilot-R** là research prototype hỗ trợ quyết định mua sắm điện máy bằng tiếng Việt. Hệ thống trích xuất nhu cầu theo ngành hàng, xử lý ràng buộc cứng theo nguyên tắc fail-closed, đề xuất top 3 kèm trade-off và xuất bằng chứng có thể kiểm tra lại cho từng quyết định.

Project được định vị cho [RIVF 2026 Track 2 — AI Applications](https://rivf2026.org/call-for-papers.html), tập trung vào:

- AI-based decision support;
- explainable/interpretable AI qua constraint status, SKU provenance và decision hash;
- real-world deployment/integration qua FastAPI, Next.js, Web/Zalo stub, offline path và nhiều catalog backend.

Đây chưa phải tuyên bố về hệ thống production, hiệu quả thương mại hay ưu thế của kiến trúc multi-agent. Đóng góp nghiên cứu đang được kiểm chứng là **constraint-first grounding cho Vietnamese retail decision support**.

## Trạng thái nghiên cứu

| Hạng mục | Trạng thái |
|---|---|
| Protocol, RQ, baselines, privacy/data-rights gate | Có |
| Decision contract + provenance/hash | Có |
| Dev benchmark + evaluator + engineering pilot | Có, chỉ dùng kiểm tra pipeline |
| Canonical publication dataset | Có — DMX `products_detail.xlsx` (13.716 SKU / 118 categories), manifest strict `ready`, raw sha256 `39a03b03…`, normalized sha256 `e2afdf38…` |
| Sealed test + one-shot evaluation | Có — 40 episode sealed (`experiments/benchmark/SEAL_RECORD.json`), one-shot scored (`experiments/results/exp_test_scores.json`) với `CHAIN_OF_CUSTODY.json`; pooled paired bootstrap 95% CI (`exp_test_bootstrap_pooled.json`, 2026-07-26) được báo cáo trong paper |
| Deployment/load evidence | Một phần — public frontend HTTP 200, backend health HTTP 502 (2026-07-25); claim giới hạn ở prototype |
| IEEE paper tối đa 6 trang | Có — `paper/main.pdf` 5 trang, IEEEtran `conference,a4paper`, `\pdfminorversion=6`; còn EDAS metadata và recheck CFP trước khi nộp |

Không dùng kết quả trên `experiments/fixtures/catalog_dev_fixture.json` làm kết luận khoa học; fixture chỉ phục vụ pilot kỹ thuật hermetic. Kết quả đưa vào paper lấy từ sealed test 40 episode trên DMX snapshot đã pin hash (strict manifest, seal record và chain of custody đều hợp lệ từ 2026-07-25).

Đọc trước:

- [Nghiên cứu CFP và đối chiếu Track 2](docs/RIVF_TRACK2_RESEARCH.md)
- [Research protocol](docs/RIVF_TRACK2_PROTOCOL.md)
- [Dataset card](docs/DATASET_CARD.md)
- [Implementation plan](tasks/plan.md)

## Luồng quyết định

```text
Web / Zalo stub
       |
       v
Vietnamese need extraction
       |
       v
Missing-slot clarification
       |
       v
Fail-closed hard constraints
       |
       v
Top-3 ranking + trade-offs
       |
       +--> Evidence: constraint status, SKU/source row, catalog hash
       |
       +--> Agent route for ambiguous or policy questions
```

Các specialist hiện có: `catalog`, `knowledge`, `crm`, `order`, `escalation`. Offline path vẫn hoạt động không cần API key. Web và Zalo stub là hai channel trong scope; không tự mở rộng sang channel khác.

### Ranh giới backend

Các import nghiệp vụ hiện tại vẫn đi qua `backend/app/agent/catalog_domain.py`.
Đây là facade tương thích; implementation được chia theo trách nhiệm:

- `app/catalog/category_model.py`: model và `CategoryRegistry` dùng chung;
- `app/catalog/categories.py` / `crawl_categories.py`: adapter khai báo và normalize riêng cho workbook / crawl;
- `app/agent/catalog_queries.py`: product read model, search, filter và compare;
- `app/agent/recommendation.py`: trích xuất nhu cầu, follow-up, hard constraint và ranking;
- `app/agent/consultation.py`: chạy recommendation một lần rồi đóng gói decision evidence dùng chung cho fast-path và offline route.

Khi thêm behavior mới, sửa module sở hữu ở trên và giữ `catalog_domain.py` ổn định cho API, tool, memory và evaluator đang sử dụng.

## Hai profile dữ liệu

- **Runtime profile:** catalog backend cấu hình bằng Postgres, MongoDB hoặc snapshot. Đây là đường chạy sản phẩm/prototype.
- **Research profile:** snapshot cố định bởi manifest và SHA-256. Đây là đường duy nhất được dùng cho experiment sau khi data-rights gate chuyển sang `ready`.

Hai profile không được trộn ngầm. `/health` công bố backend, số sản phẩm, số category và catalog hash đang được tải.

## Quick start

### Baseline hermetic

```bash
./init.sh
./scripts/verify.sh
```

Baseline dùng engineering fixture cục bộ, temp SQLite và offline path; không cần cloud secret. Trên Windows cần Bash/WSL hoặc chạy qua container Linux.

### Full stack

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8000/health`
- Chat API: `POST http://localhost:8000/chat`

### Canonical research import

Nguồn canonical từ 2026-07-25 là DMX `products_detail.xlsx` (đặt tại repo root, gitignored); đường `Spec_cate_gia.xlsx`/`import_spec_catalog` đã retired cho mục đích nghiên cứu. Chỉ chạy khi đã có file được phép sử dụng:

```bash
cd backend
python -m scripts.import_dmx_research \
  --excel ../products_detail.xlsx \
  --snapshot-only \
  --confirm-publication-rights

cd ..
python scripts/validate_research_manifest.py experiments/manifest.json
```

Không commit workbook, raw catalog, `.env`, production conversations, CRM/memory hoặc raw trajectories.

## Verification

```bash
# Research gates
python scripts/validate_research_manifest.py --self-test
python scripts/validate_research_manifest.py experiments/manifest.json
python scripts/validate_benchmark.py experiments/benchmark/dev.jsonl
python scripts/validate_benchmark.py experiments/benchmark/test.jsonl
python scripts/validate_benchmark_seal.py

# Evaluator
python -m unittest experiments.evaluate.test_metrics

# Engineering pilot only
python scripts/run_pilot.py --split dev
python -m experiments.evaluate.runner \
  --input experiments/results/pilot_dev.jsonl \
  --labels experiments/benchmark/dev.jsonl \
  --out experiments/results/pilot_dev_scores.json

# Product smoke
./scripts/verify.sh

# Frontend
cd frontend
npm run build
```

## Project map

| Path | Vai trò |
|---|---|
| `backend/` | FastAPI, deterministic decision core, LangGraph orchestration |
| `frontend/` | Next.js chat, decision evidence, Agent Trace, dashboard |
| `experiments/` | Manifest, benchmark, conditions, evaluator, results |
| `docs/` | Track research, protocol, dataset card, architecture |
| `tasks/` | Critical path và checklist submission |
| `feature_list.json` | Feature state và verification evidence |
| `claude-progress.md` | Verified session log |

## Submission constraints

Theo CFP (xác nhận trực tiếp từ rivf2026.org ngày **2026-08-01**): paper phải là đóng góp nguyên gốc, viết bằng tiếng Anh, PDF chuẩn IEEE khổ A4, tối đa 6 trang; deadline submission đã được **gia hạn từ 2026-07-31 sang 2026-08-31** (trang CFP hiện ghi "Paper Submission Deadline (Extended): ~~July 31, 2026~~ August 31, 2026") qua [EDAS N35414](https://edas.info/N35414); notification 2026-10-15, camera-ready 2026-11-11. Phải kiểm tra lại CFP/EDAS trước khi upload vì các mốc đang được ghi là tentative.

## License

MIT cho phần code trong repository. Quyền với catalog, policy corpus, benchmark derivative và experiment output được quản lý riêng trong [Dataset Card](docs/DATASET_CARD.md) và `experiments/manifest.json`.
