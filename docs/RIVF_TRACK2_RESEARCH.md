# RIVF 2026 Track 2 — nghiên cứu CFP và đối chiếu SalePilot

Ngày kiểm tra nguồn: **2026-07-24** (Asia/Saigon)

Phạm vi nguồn: chỉ dùng trang chính thức RIVF 2026 và cổng EDAS được RIVF liên kết.

> **Cập nhật 2026-07-26:** CFP được fetch lại và đối chiếu — danh sách 7 track, tên và 6 nhóm chủ đề của Track 2 "AI Applications", giới hạn 6 trang IEEE A4 tiếng Anh, cổng EDAS N35414 và các mốc 2026-07-31 / 2026-10-15 / 2026-11-11 đều **không đổi**. Các blocker khoa học ở mục 5 đã thay đổi trạng thái sau pivot nguồn dữ liệu 2026-07-25 (DMX `products_detail.xlsx` thay cho workbook `Spec_cate_gia.xlsx`); xem chú thích trạng thái ngay trong mục 5. Kết quả sealed 40 episode nằm ở `experiments/results/exp_test_scores.json` và đã khớp với bảng trong `paper/main.tex` (5 trang).
>
> **Cập nhật 2026-08-01:** Fetch lại trực tiếp `https://rivf2026.org/call-for-papers.html`. Trang chính thức hiện ghi **"Paper Submission Deadline (Extended): ~~July 31, 2026~~ August 31, 2026"** — deadline đã dời sang **2026-08-31**. Đây là thay đổi thật, xảy ra sau lần kiểm tra 2026-07-26 ở trên (lần đó xác nhận mốc "không đổi" — chính xác tại đúng thời điểm đó). Danh sách track/chủ đề, giới hạn trang, và cổng EDAS N35414 vẫn không đổi so với lần kiểm tra trước. Bảng ở mục 3 và câu ở mục 7 bên dưới đã cập nhật theo mốc mới; nội dung 2026-07-24/07-26 phía trên được giữ nguyên làm hồ sơ kiểm chứng lịch sử.

## Kết luận ngắn

SalePilot **phù hợp Track 2 nếu được trình bày như một công trình nghiên cứu ứng dụng AI có đánh giá thực nghiệm**, không phải như một bản mô tả sản phẩm hoặc một demo multi-agent. Hướng khớp nhất là:

> **Hệ hỗ trợ ra quyết định bán lẻ tiếng Việt theo ràng buộc, có bằng chứng và cơ chế fail-closed, được đánh giá đối chứng trên dữ liệu cố định.**

Ba chủ đề Track 2 mà hướng này khớp trực tiếp là hệ hỗ trợ ra quyết định dựa trên AI, khả năng giải thích của AI trong ứng dụng, và triển khai/tích hợp hệ thống AI trong thực tế. Bán lẻ không nằm trong danh sách lĩnh vực minh họa của CFP, nhưng danh sách chủ đề được công bố là không đóng; do đó không cần đổi SalePilot sang y tế, giáo dục hay một lĩnh vực khác để đủ điều kiện. Nguồn: [RIVF 2026 Call for Papers](https://rivf2026.org/call-for-papers.html).

Repo đã có nền móng nghiên cứu đúng hướng, nhưng **chưa có kết quả đủ điều kiện đưa vào paper**: nguồn workbook chính thức còn thiếu, manifest đang `blocked`, benchmark hiện tại là dev set trên engineering fixture, và chưa có sealed test. Vì vậy các số pilot hiện có chỉ nên dùng để kiểm tra pipeline, không dùng làm kết luận khoa học.

## 1. Track 2 chính thức

Tên chính xác của track là **“2. AI Applications”**. CFP liệt kê sáu nhóm chủ đề sau:

1. Ứng dụng AI trong y tế, giáo dục, tài chính, nông nghiệp, giao thông và đô thị thông minh.
2. Đưa hệ thống AI vào vận hành trong bối cảnh thực tế.
3. Hệ hỗ trợ ra quyết định dựa trên AI.
4. Khả năng giải thích và diễn giải của AI trong ứng dụng.
5. AI phục vụ lợi ích xã hội.
6. Các thách thức khi mở rộng quy mô và tích hợp giải pháp AI.

Đây là bản dịch sát nghĩa từ danh sách chính thức; CFP nói các chủ đề là không giới hạn ở danh sách này. Nguồn: [RIVF 2026 Call for Papers — Conference Topics](https://rivf2026.org/call-for-papers.html).

Track chairs được công bố cho AI Applications là ZengChang Qin (VinUniversity), Ce Zhang (University of Sheffield), và Nguyen Thanh Hong (University of Oregon). Nguồn: [RIVF 2026 Committee — Track Chairs](https://rivf2026.org/committee.html).

## 2. Loại đóng góp mà CFP chấp nhận

CFP mời **bài nghiên cứu nguyên gốc**. Trang hiện tại không tách riêng full paper, short paper, demo paper, system paper hay industry paper; vì vậy lựa chọn an toàn là chuẩn bị một bài nghiên cứu đầy đủ, có câu hỏi nghiên cứu, phương pháp, đối chứng, dữ liệu, metric, kết quả và giới hạn.

Đối với SalePilot, loại đóng góp hợp track nhất là một **empirical AI application/system paper** với ba lớp đóng góp:

- **Phương pháp:** biểu diễn nhu cầu và ràng buộc theo ngành hàng; ràng buộc cứng được xử lý fail-closed khi dữ liệu thiếu; định tuyến lai giữa lõi quyết định xác định và agent cho truy vấn mơ hồ/chính sách.
- **Khả năng giải thích:** mỗi đề xuất gắn với SKU, nguồn/dòng dữ liệu, catalog hash, thành phần điểm và trạng thái ràng buộc; evaluator kiểm tra lại bằng dữ liệu thay vì tin lời giải thích do mô hình sinh.
- **Bằng chứng thực nghiệm:** so sánh với baseline giá/phổ biến và lexical/filter trên cùng catalog, split và turn budget; báo cáo vi phạm ràng buộc cứng, abstention, category accuracy, slot micro-F1, latency và failure modes.

Đây là **khuyến nghị đối chiếu**, không phải danh mục loại paper được RIVF công bố.

## 3. Yêu cầu paper, submission và mốc thời gian

| Hạng mục | Yêu cầu đang công bố |
|---|---|
| Ngôn ngữ | Tiếng Anh |
| Định dạng | PDF, chuẩn IEEE, khổ A4 |
| Độ dài | Tối đa 6 trang |
| LaTeX | `\documentclass[conference,a4paper]{IEEEtran}` và `\pdfminorversion=6` |
| Tính nguyên gốc | Chưa từng xuất bản và không đồng thời được xem xét ở nơi khác |
| Cổng nộp | [EDAS conference N35414](https://edas.info/N35414) |
| Hạn nộp paper | ~~2026-07-31~~ → **2026-08-31** (gia hạn, xác nhận trực tiếp trên CFP 2026-08-01) — tentative |
| Thông báo chấp nhận | **2026-10-15** — tentative |
| Camera-ready | **2026-11-11** — tentative |
| Hội nghị | **2026-12-18 đến 2026-12-20**, VinUniversity, Hà Nội |

Nguồn cho toàn bộ yêu cầu và các mốc trên: [RIVF 2026 Call for Papers](https://rivf2026.org/call-for-papers.html); địa điểm và ngày hội nghị cũng được xác nhận trên [trang chủ RIVF 2026](https://rivf2026.org/).

Các lưu ý quan trọng:

- CFP ghi các deadline là **tentative** và không công bố giờ đóng cổng hoặc múi giờ. Phải kiểm tra lại EDAS và CFP ngay trước khi nộp.
- Tính từ ngày kiểm tra nguồn 2026-07-24, hạn paper đang công bố chỉ còn 7 ngày theo lịch; scope paper cần được khóa ngay.
- CFP nói tối đa 6 trang, trong khi trang đăng ký có một dòng phí trang vượt mức. Không nên suy diễn rằng có thể nộp quá 6 trang; chỉ vượt giới hạn nếu EDAS hoặc ban tổ chức xác nhận bằng văn bản.
- Paper được chấp nhận phải được trình bày. Trang đăng ký nêu ít nhất một tác giả của mỗi paper được nhận phải đăng ký và trình bày để paper được đưa vào proceedings và gửi tới IEEE Xplore; CFP cũng cảnh báo paper không được trình bày có thể bị loại khỏi phân phối sau hội nghị. Nguồn: [RIVF 2026 Registration](https://rivf2026.org/registration.html) và [Call for Papers](https://rivf2026.org/call-for-papers.html).
- Cách diễn đạt an toàn về xuất bản là: paper được chấp nhận và trình bày sẽ vào proceedings và được **submitted** tới IEEE Xplore cùng các cơ sở A&I; CFP còn đặt điều kiện proceedings phải qua chuẩn kiểm tra chất lượng IEEE. Không nên viết rằng việc xuất hiện trên IEEE Xplore đã được bảo đảm vô điều kiện.
- CFP hiện không nêu review ẩn danh hay không, references có nằm trong 6 trang hay không, supplementary material, AI-use policy, hoặc thời điểm khóa metadata. Các điểm này phải được xác minh trên EDAS hoặc qua `rivf2026@vinuni.edu.vn`, không tự giả định.

## 4. Đối chiếu Track 2 với SalePilot hiện tại

| Chủ đề Track 2 | Mức khớp | Bằng chứng hiện có trong repo | Điều còn thiếu để thành claim paper |
|---|---:|---|---|
| Hỗ trợ ra quyết định dựa trên AI | **Rất mạnh** | Protocol đã đặt hard-constraint violation làm endpoint chính; benchmark có các action `recommend`, `clarify`, `compare`, `faq`, `abstain`. Xem [protocol](./RIVF_TRACK2_PROTOCOL.md) và [benchmark schema](../experiments/benchmark/schema.json). | Sealed test trên catalog được phép sử dụng; so sánh thống kê với baseline; phân tích abstention và lỗi. |
| Explainable/interpretable AI | **Mạnh về cơ chế** | Decision contract xuất evidence fields, provenance, score components, constraint status và decision hash. Xem [decision contract](../backend/app/agent/decision.py). | Nếu claim “giải thích hữu ích/dễ hiểu”, cần human study hoặc rubric phù hợp. Nếu không có, chỉ claim traceability/evidence correctness. |
| Triển khai AI trong thực tế | **Khá** | Có FastAPI, Next.js, kênh Web, agent graph, offline path và nhiều backend catalog; xem [architecture](./ARCHITECTURE.md). | Cần workload cố định, p50/p95, route/fallback coverage, failure recovery và môi trường tái lập. Không gọi local smoke là triển khai production. |
| Mở rộng và tích hợp AI | **Khá** | Registry theo ngành hàng, multi-backend catalog và agent/tool integration đã có. | Đo scale theo số SKU/ngành/truy vấn; kiểm tra độ ổn định khi dữ liệu thiếu/thay backend; không lấy số lượng component làm bằng chứng scale. |
| Các lĩnh vực ứng dụng được nêu đích danh | **Không trực tiếp** | SalePilot là bán lẻ điện máy/công nghệ. | Không cần đổi domain: dùng phạm vi không đóng của CFP và neo paper vào decision support/deployment/explainability. |
| AI for social good | **Yếu/chưa có** | Chưa có protocol hay outcome xã hội được đo. | Không dùng claim này trừ khi có đối tượng thụ hưởng, metric và đánh giá thật. |

### Vì sao không nên lấy “multi-agent” làm novelty chính

Kiến trúc Lead + specialist là phần triển khai hữu ích, nhưng chỉ mô tả agent orchestration chưa tạo thành một đóng góp nghiên cứu đủ mạnh. Paper nên đặt novelty ở **constraint-first grounded decision support** và chứng minh bằng metric độc lập. Multi-agent/hybrid routing là cơ chế hệ thống giúp xử lý truy vấn mơ hồ, chính sách và fallback; nó chỉ trở thành claim nếu có ablation hoặc so sánh rõ với single-agent/LLM condition.

### Framing đề xuất

Tên làm việc hiện tại trong repo đã đúng hướng:

> **Constraint-First Grounding for Explainable Vietnamese Retail Decision Support: A Hybrid Agentic System**

Câu đóng góp trung tâm nên gần với:

> Chúng tôi đề xuất và đánh giá một hệ hỗ trợ quyết định bán lẻ tiếng Việt kết hợp trích xuất nhu cầu theo ngành với xếp hạng fail-closed theo ràng buộc, đồng thời xuất bằng chứng có thể kiểm tra cho từng đề xuất.

Nên tránh các claim sau nếu chưa có bằng chứng bổ sung:

- “triển khai thực tế/production” chỉ từ Docker hoặc HTTP smoke;
- “giải thích tốt hơn cho người dùng” nếu chưa có study/ablation;
- “multi-agent tốt hơn” nếu không có đối chứng;
- “không vi phạm ràng buộc” từ dev fixture nhỏ;
- “14 ngành hàng” trong kết quả paper khi canonical workbook chưa được nhập và hash;
- tồn kho thời gian thực hoặc endorsement của nhà bán lẻ.

## 5. Đánh giá mức sẵn sàng của repo

### Đã có, dùng được làm nền

- Protocol đã đóng băng RQ, hypotheses, endpoint, baseline và controls: [RIVF_TRACK2_PROTOCOL.md](./RIVF_TRACK2_PROTOCOL.md).
- Dataset card đã mô tả quyền sử dụng, missingness, PII và unlock criteria: [DATASET_CARD.md](./DATASET_CARD.md).
- Research manifest tách nguồn canonical khỏi fixture kỹ thuật và yêu cầu hash: [experiments/manifest.json](../experiments/manifest.json).
- Dev benchmark có 20 episode tiếng Việt và schema versioned: [dev.jsonl](../experiments/benchmark/dev.jsonl), [schema.json](../experiments/benchmark/schema.json).
- Ba condition đã được mã hóa: `B0_price_popularity`, `B1_lexical_filter`, `S_hybrid_constraint`: [conditions.json](../experiments/conditions.json), [run_pilot.py](../scripts/run_pilot.py).
- Metric ràng buộc dùng label làm nguồn sự thật và kiểm lại dữ liệu sản phẩm: [metrics.py](../experiments/evaluate/metrics.py).
- Pilot chứng minh pipeline chạy được, nhưng chỉ trên 20 dev episode và engineering fixture: [pilot_dev_scores.json](../experiments/results/pilot_dev_scores.json).

### Blocker khoa học (trạng thái cập nhật 2026-07-26)

1. ~~[Manifest](../experiments/manifest.json) vẫn là `blocked`~~ — **Đã xử lý 2026-07-25:** manifest strict `ready` với nguồn DMX `products_detail.xlsx`, raw sha256 `39a03b03…`, normalized sha256 `e2afdf38…`.
2. [Dataset card](./DATASET_CARD.md) xác nhận fixture không phải nguồn publication — **vẫn đúng**; fixture chỉ dùng cho pilot kỹ thuật, kết quả paper lấy từ DMX snapshot.
3. ~~Chưa có sealed test set/custody record~~ — **Đã xử lý:** sealed test 40 episode (`SEAL_RECORD.json`), one-shot evaluation (`exp_test_scores.json`) và `CHAIN_OF_CUSTODY.json`. Lưu ý custody record chưa pin code revision/conditions hash; giới hạn này đã được khai trong paper.
4. **Còn nguyên trên sealed test:** `B1_lexical_filter` và `S_hybrid_constraint` vẫn hòa nhau ở mọi aggregate (0 violation / 99 checks mỗi bên); chỉ B0 bị phân giải (10/117). Paper vì vậy chỉ claim lợi ích của explicit constraint filtering so với B0, không claim S\_hybrid vượt B1.
5. ~~Bootstrap không ước lượng pooled metrics~~ — **Đã xử lý 2026-07-26:** `scripts/summarize_results.py --pooled-bootstrap` resample theo episode và tính lại pooled metrics mỗi resample (paired, seed 20260723, n\_boot 10000); artifact `exp_test_bootstrap_pooled.json` được hash trong custody record. Paired difference B0−S\_hybrid = 0.0855, 95% CI [0.010, 0.167], loại trừ 0; paper báo cáo các CI này.
6. **Còn:** chưa có đánh giá đủ để claim lợi ích của explanation hoặc multi-agent; paper giới hạn ở traceability và đã khai human study là future work.

## 6. Thay đổi cần ưu tiên để “match Track 2”

### P0 — bắt buộc cho paper nghiên cứu

1. **Mở khóa nguồn dữ liệu chính thức**
   - Đặt workbook được phép sử dụng vào đúng path.
   - Import xác định, ghi raw/normalized hashes, chạy manifest strict.
   - Chỉ phát hành aggregates/labels theo quyền đã ghi; không đưa raw catalog vào paper artifact nếu không được phép.

2. **Khóa thiết kế đánh giá**
   - Giữ endpoint chính là hard-constraint violation rate.
   - Hoàn thiện sealed test có phân tầng theo ngành và độ khó; không sửa query/label sau khi nhìn kết quả.
   - Dùng cùng catalog hash, timeout, turn budget và split cho mọi condition.

3. **Làm baseline đủ phân giải**
   - B0: price/popularity không hiểu constraint.
   - B1: lexical extraction + filter/rank, độc lập với proposed method.
   - Proposed: category-aware extraction + fail-closed constraint semantics + hybrid routing.
   - Kiểm tra không dùng chung quá nhiều logic đến mức B1 và proposed trở thành cùng một hệ dưới tên khác.

4. **Chạy evaluation cuối một lần sau freeze**
   - Báo cáo số episode và số constraint được kiểm, violation rate, abstention, category/action accuracy, slot micro-F1, latency và CI.
   - Công bố cả kết quả âm, unknown/missing và failure cases.

5. **Viết paper theo cấu trúc research**
   - Problem/motivation → related work/gap → method → experimental setup → results → error analysis → limitations/ethics.
   - Tiếng Anh, IEEE A4, không quá 6 trang theo CFP hiện tại.

### P1 — làm claim Track 2 mạnh hơn

1. **Explainability:** thêm ablation cùng ranking nhưng ẩn evidence. Nếu không kịp human study, đánh giá evidence correctness/coverage tự động và hạ claim xuống “traceable explanations”.
2. **Deployment/integration:** benchmark p50/p95, throughput vừa đủ, timeout/fallback, offline/no-key path, catalog-backend parity và failure injection trên workload cố định.
3. **Hybrid routing:** đo route accuracy/coverage và so sánh chi phí-latency-reliability với single-agent condition nếu có key, ngân sách và số lần lặp hợp lệ; nếu không, ghi `unavailable`.
4. **Reproducibility:** khóa environment, seed, catalog hash, code revision, condition config và prediction hash trong artifact.

## 7. Quyết định scope thực tế

Với hạn paper đang hiển thị là **2026-08-31** (gia hạn, xác nhận 2026-08-01 — xem cập nhật đầu file), scope khả thi nhất là:

- một contribution chính: **fail-closed constraint grounding cho Vietnamese retail decision support**;
- một evaluation chính: hard-constraint violation trên sealed test;
- hai baseline xác định;
- explanation được giới hạn ở evidence correctness/traceability nếu human study chưa sẵn sàng;
- deployment claim được giới hạn ở prototype/reproducible system evidence, không phải production impact.

Không nên đồng thời cố chứng minh mọi thứ: multi-agent superiority, explainability effect, scale, social good và production deployment. Một claim chính có benchmark chặt sẽ khớp Track 2 tốt hơn nhiều claim chưa đủ bằng chứng.

## Nguồn chính thức

- [RIVF 2026 Call for Papers](https://rivf2026.org/call-for-papers.html)
- [RIVF 2026 home page](https://rivf2026.org/)
- [RIVF 2026 Committee](https://rivf2026.org/committee.html)
- [RIVF 2026 Registration](https://rivf2026.org/registration.html)
- [RIVF 2026 EDAS submission portal](https://edas.info/N35414)
