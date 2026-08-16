# Kiểm toán trích dẫn cho bản thảo SalePilot

**Ngày kiểm toán:** 2026-07-26

> **Addendum 2026-07-26 (sau kiểm toán):** bản sửa "acceptance strengthening" thêm 1 entry mới `hanley1983zero` (Hanley & Lippman-Hand, *If Nothing Goes Wrong, Is Everything All Right? Interpreting Zero Numerators*, JAMA 249(13):1743–1745, 1983, DOI [10.1001/jama.1983.03330370053031](https://doi.org/10.1001/jama.1983.03330370053031)) — được cite một lần trong Results để diễn giải rule-of-three cho 0/99 checks; claim-fit: supported (bài gốc về zero-numerator upper bound). Bản sửa cũng thêm 1 occurrence thứ hai của `efron1979bootstrap` (đoạn threats-to-validity về episode-resample pooled bootstrap; claim-fit: supported). Tổng hiện tại: 27 entry / 27 khóa dùng / 30 occurrence. Các số 26/28 trong bảng dưới là snapshot trước addendum.

> **Tái xác minh độc lập 2026-07-26 (sau khi thêm `hanley1983zero`):** toàn bộ 27 entry được kiểm tra lại qua nguồn ngoài (Crossref API cho 19 entry có DOI Crossref; ACL Anthology cho Jacovi/Shuster/Artstein; DBLP cho ReAct/AgentBench; IJCAI proceedings cho Guo; NeurIPS proceedings cho Lewis; JMLR cho Pineau; doi.org→nvlpubs cho NIST CSWP 10; arXiv + OpenReview search cho AutoGen COLM 2024; Semantic Scholar cho Hanley). Kết quả: 27/27 tồn tại, metadata khớp. Ghi chú: (a) Crossref tách subtitle "A landscape of research" của Jannach 2023 thành field riêng — title bib gộp là đúng chuẩn; (b) record Crossref của JAMA 1983 chỉ liệt kê tác giả đầu, Semantic Scholar/JAMA xác nhận đồng tác giả Lippman-Hand; (c) DBLP chỉ index bản arXiv của AutoGen ("…Conversation Framework", 10 tác giả) — bib cite đúng bản COLM 2024 ("…Conversations", 14 tác giả, forum BAakY1hNKS).

**Phạm vi:** bản final draft hiện tại của `paper/main.tex`, bibliography hiện
tại của `paper/ref.bib`, và các record chính thức được liên kết bên dưới.

**Nguyên tắc:** số dòng là số dòng vật lý của `main.tex` hiện tại. Metadata và
claim-source fit được kiểm tra độc lập; số `[n]` là thứ tự citation đầu tiên mà
IEEE sẽ dùng, không phải thứ tự entry trong `ref.bib`.

## Kết luận nhanh

| Hạng mục | Kết quả |
|---|---:|
| Số occurrence `\cite{...}` trong `main.tex` | 28 |
| Số citation key duy nhất trong `main.tex` | 26 |
| Số entry trong `ref.bib` | 26 |
| Khóa thiếu / entry không dùng | 0 / 0 |
| Duplicate key / duplicate entry / duplicate DOI | 0 / 0 / 0 |
| Công trình tồn tại qua record chính thức | 26/26 |
| Entry có metadata và tên/note render đúng trong bibliography hiện tại | 26/26 |
| Claim-fit theo 28 occurrence: `supported` / `partial` / `not supported` | 28 / 0 / 0 |
| Claim-fit theo 26 khóa: `supported` / `partial` / `not supported` | 26 / 0 / 0 |

Mốc 26/26 bao gồm cả render đúng của `{Ferrari Dacrema}`, `Yih, Wen-tau`,
`{d'Alché-Buc}` và note `{Survey Track}` trong `main.bbl` hiện tại.

Các câu EAR, Pineau, NIST, Greshake, Artstein và Efron đã được thu hẹp đúng
phạm vi nguồn. Năm chỉnh sửa BibTeX được yêu cầu cũng đã hiện diện. Không còn
lỗi metadata cần sửa; chỉ còn hai discrepancy cần ghi nhớ: DOI IJCAI của Guo
bị collision, và record Microsoft Research của AutoGen khác record accepted
của COLM. Cả hai đều đã được xử lý đúng trong bibliography hiện tại.

## Phương pháp

1. Trích từng `\cite{...}` từ `main.tex`, giữ nguyên thứ tự và số dòng hiện tại.
2. So sánh hai chiều tập khóa citation với 26 khóa đầu entry trong `ref.bib`.
3. Đối chiếu title, authors, venue, year, pages/article number và DOI/URL với
   publisher, proceedings hoặc cơ quan phát hành chính thức.
4. Đọc claim chứa từng citation trong bản thảo mới và chấm riêng từng
   occurrence. Một câu thiết kế của SalePilot được xem là supported khi citation
   chỉ làm căn cứ cho phương pháp hoặc động cơ mà nguồn thực sự bao phủ.
5. Với AutoGen, record **COLM 2024 Accepted Papers** là record venue có thẩm
   quyền; record Microsoft Research được giữ như bằng chứng về discrepancy.

## Inventory mọi occurrence `\cite`

| Occ. | Dòng `main.tex` | Lệnh nguyên văn | Số PDF |
|---:|---:|---|---:|
| 1 | 82 | `\cite{jannach2021survey}` | [1] |
| 2 | 86 | `\cite{christakopoulou2016towards}` | [2] |
| 3 | 86 | `\cite{lei2020ear}` | [3] |
| 4 | 88 | `\cite{huang2025interecagent}` | [4] |
| 5 | 88 | `\cite{nie2024hybrid}` | [5] |
| 6 | 90 | `\cite{jannach2023evaluating}` | [6] |
| 7 | 90 | `\cite{liu2024agentbench}` | [7] |
| 8 | 108 | `\cite{jannach2021survey}` | [1] |
| 9 | 108 | `\cite{zhang2018systemask}` | [8] |
| 10 | 110 | `\cite{lei2020ear}` | [3] |
| 11 | 113 | `\cite{yao2023react}` | [9] |
| 12 | 113 | `\cite{guo2024multiagents}` | [10] |
| 13 | 115 | `\cite{wu2024autogen}` | [11] |
| 14 | 117 | `\cite{lewis2020rag}` | [12] |
| 15 | 117 | `\cite{shuster2021retrieval}` | [13] |
| 16 | 120 | `\cite{zhang2020explainable}` | [14] |
| 17 | 120 | `\cite{jacovi2020faithfulness}` | [15] |
| 18 | 122 | `\cite{herlocker2004evaluating}` | [16] |
| 19 | 122 | `\cite{jarvelin2002cumulated}` | [17] |
| 20 | 124 | `\cite{ferraridacrema2021troubling}` | [18] |
| 21 | 124 | `\cite{hidasi2023widespread}` | [19] |
| 22 | 186 | `\cite{nist2020privacy}` | [20] |
| 23 | 190 | `\cite{greshake2023indirect}` | [21] |
| 24 | 225 | `\cite{beel2016reproducibility}` | [22] |
| 25 | 227 | `\cite{pineau2021reproducibility}` | [23] |
| 26 | 288 | `\cite{artstein2008agreement}` | [24] |
| 27 | 288 | `\cite{efron1979bootstrap}` | [25] |
| 28 | 290 | `\cite{jin2024crsque}` | [26] |

## Audit theo khóa, theo thứ tự citation đầu tiên

| Số PDF / key | Dòng hiện tại | Claim hiện tại | Tồn tại và metadata | Claim-fit | Bằng chứng chính thức |
|---|---:|---|---|---|---|
| [1] `jannach2021survey` | 82, 108 | CRS cho phép elicitation, explanation, feedback; lĩnh vực bao phủ intent, knowledge, interaction và evaluation. | **Có; đúng.** *ACM CSUR* 54(5), Article 105, 36 trang, 2021; authors và DOI khớp. | **`supported`** ở cả hai occurrence. | [ACM DOI](https://doi.org/10.1145/3453154) |
| [2] `christakopoulou2016towards` | 86 | Selective questioning đã được hình thức hóa cho recommendation. | **Có; đúng.** KDD 2016, 815-824; ba authors và DOI khớp. | **`supported`.** Nguồn trực tiếp nghiên cứu chọn câu hỏi để học preference. | [ACM DOI](https://doi.org/10.1145/2939672.2939746) |
| [3] `lei2020ear` | 86, 110 | EAR tách preference estimation, action choice, và reflection sau feedback. | **Có; đúng.** WSDM 2020, 304-312; title, bảy authors và DOI khớp. | **`supported`** ở cả hai occurrence. Bản mới dùng đúng “estimation--action--reflection”. | [ACM DOI](https://doi.org/10.1145/3336191.3371769) |
| [4] `huang2025interecagent` | 88 | Công trình gần đây dùng LLM làm planner trên recommender tools. | **Có; đúng.** *ACM TOIS* 43(4), Article 96, 33 trang, 2025; DOI khớp. | **`supported`.** InteRecAgent dùng LLM làm brain cho planning và tool use. | [ACM DOI](https://doi.org/10.1145/3731446) |
| [5] `nie2024hybrid` | 88 | Hybrid multi-agent design đã được nghiên cứu cho e-commerce consultation. | **Có; đúng.** RecSys 2024, 745-747; 12 authors, title và DOI khớp. | **`supported`.** Claim chỉ nêu existence và domain của hệ thống. | [ACM DOI](https://doi.org/10.1145/3640457.3688061) |
| [6] `jannach2023evaluating` | 90 | CRS evaluation phải phân biệt component quality và user experience. | **Có; đúng sau correction.** Title hiện có subtitle “A Landscape of Research”; *Artificial Intelligence Review* 56(3), 2365-2400, 2023; DOI khớp. | **`supported`.** Abstract nêu trực tiếp component assessment và user perception. | [Springer](https://link.springer.com/article/10.1007/s10462-022-10229-x) |
| [7] `liu2024agentbench` | 90 | Agent benchmarks tạo động cơ cho multi-turn tests trong executable environments. | **Có; đúng.** ICLR 2024; 22 authors; venue không cấp DOI hay page range. | **`supported`.** AgentBench đánh giá agent trong tám interactive environments. | [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/e9df36b21ff4ee211a8b71ee8b7e9f57-Abstract-Conference.html) |
| [8] `zhang2018systemask` | 108 | System Ask--User Respond chủ động elicitate attributes. | **Có; đúng.** CIKM 2018, 177-186; năm authors và DOI khớp. | **`supported`.** Claim bám đúng paradigm được công trình giới thiệu. | [ACM DOI](https://doi.org/10.1145/3269206.3271776) |
| [9] `yao2023react` | 113 | ReAct xen kẽ reasoning với actions và observations. | **Có; đúng sau correction.** ICLR 2023; bảy authors; current BibTeX dùng đúng “Karthik Narasimhan”; không DOI/pages. | **`supported`.** Abstract mô tả reasoning traces và task actions theo cách xen kẽ. | [ICLR](https://iclr.cc/virtual/2023/poster/11003) |
| [10] `guo2024multiagents` | 113 | Multi-agent work được tổ chức theo profiles, communication và skills. | **Có; đúng.** IJCAI-24 Survey Track, 8048-8057; tám authors và title khớp. DOI được bỏ có chủ ý vì collision. | **`supported`.** Abstract nêu đúng ba trục này. | [IJCAI record](https://www.ijcai.org/proceedings/2024/890) · [DOI collision](https://doi.org/10.24963/ijcai.2024/890) |
| [11] `wu2024autogen` | 115 | AutoGen là programmable precedent cho multi-agent conversation. | **Có; đúng theo record accepted của COLM.** Title số nhiều “Multi-Agent Conversations”, 14 authors gồm Jiale Liu, COLM 2024, không page range hay DOI. | **`supported`.** Abstract mô tả framework lập trình ứng dụng bằng nhiều agent hội thoại. | [COLM Accepted Papers](https://colmweb.org/2024/AcceptedPapers.html) · [OpenReview](https://openreview.net/forum?id=BAakY1hNKS) · [Microsoft discrepancy](https://www.microsoft.com/en-us/research/publication/autogen-enabling-next-gen-llm-applications-via-multi-agent-conversation-framework/) |
| [12] `lewis2020rag` | 117 | External stores tạo precedent cho retrieval-augmented generation; SalePilot không chuyển kết quả của phương pháp sang hệ mình. | **Có; đúng.** NeurIPS 2020, volume 33, 9459-9474; 12 authors; không DOI. | **`supported`.** Nguồn kết hợp parametric và non-parametric memory; caveat trong manuscript tránh overclaim. | [NeurIPS](https://proceedings.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html) |
| [13] `shuster2021retrieval` | 117 | Retrieval-in-the-loop là precedent cho conversation; không chuyển kết quả sang SalePilot. | **Có; đúng.** Findings of EMNLP 2021, 3784-3803; năm authors và DOI khớp. | **`supported`.** Nguồn trực tiếp nghiên cứu neural retrieval trong knowledge-grounded dialogue. | [ACL Anthology](https://aclanthology.org/2021.findings-emnlp.320/) |
| [14] `zhang2020explainable` | 120 | Explainable recommendation phục vụ nhiều stakeholder và goal. | **Có; đúng.** *Foundations and Trends in IR* 14(1), 1-101, 2020; authors và DOI khớp. | **`supported`.** Survey phân biệt stakeholder và các mục tiêu explanation. | [Publisher DOI](https://doi.org/10.1561/1500000066) |
| [15] `jacovi2020faithfulness` | 120 | Catalog claim có nguồn không chứng minh text phản ánh causal process của model. | **Có; đúng.** ACL 2020, 4198-4205; authors và DOI khớp. | **`supported`.** Nguồn tách faithfulness khỏi các tiêu chí interpretability khác. | [ACL Anthology](https://aclanthology.org/2020.acl-main.386/) |
| [16] `herlocker2004evaluating` | 122 | Recommendation metrics đo các thuộc tính khác nhau. | **Có; đúng.** *ACM TOIS* 22(1), 5-53, 2004; bốn authors và DOI khớp. | **`supported`.** Nguồn phân tích nhiều mục tiêu và lớp metric khác nhau. | [ACM DOI](https://doi.org/10.1145/963770.963772) |
| [17] `jarvelin2002cumulated` | 122 | nDCG kết hợp graded relevance với rank discount. | **Có; đúng.** *ACM TOIS* 20(4), 422-446, 2002; authors và DOI khớp. | **`supported`.** Đây là định nghĩa trực tiếp của discounted cumulative gain chuẩn hóa. | [ACM DOI](https://doi.org/10.1145/582415.582418) |
| [18] `ferraridacrema2021troubling` | 124 | Baseline đơn giản có thể phơi bày progress claim yếu. | **Có; đúng.** *ACM TOIS* 39(2), Article 20, 49 trang, 2021; DOI khớp. | **`supported`.** Nguồn cho thấy nhiều neural method không vượt baseline đơn giản khi so sánh nhất quán. | [ACM DOI](https://doi.org/10.1145/3434185) |
| [19] `hidasi2023widespread` | 124 | Offline recommender protocols có thể có methodological flaws. | **Có; đúng.** RecSys 2023, 848-855; hai authors và DOI khớp. | **`supported`.** Claim thận trọng và đúng trực tiếp với nội dung công trình. | [ACM DOI](https://doi.org/10.1145/3604915.3608839) |
| [20] `nist2020privacy` | 186 | Chính sách release cấm raw trajectories và contact details, phản ánh data-minimization goals. | **Có; đúng sau correction.** Corporate author NIST, `NIST CSWP 10`, January 2020, DOI canonical `.10`. | **`supported`.** Citation hỗ trợ mục tiêu minimization/risk management; câu không claim anonymity hay compliance. | [NIST CSRC](https://csrc.nist.gov/pubs/cswp/10/nist-privacy-framework-version-10/final) · [canonical DOI](https://doi.org/10.6028/NIST.CSWP.10) |
| [21] `greshake2023indirect` | 190 | Indirect prompt injection tạo động cơ cho server-side boundaries mạnh hơn; controls hiện tại không được gọi là secure jail hay SSRF-resistant. | **Có; đúng.** AISec 2023, 79-90; sáu authors và DOI khớp. | **`supported`.** Nguồn chứng minh attack class; manuscript chỉ dùng làm motivation và nêu rõ giới hạn controls. | [ACM DOI](https://doi.org/10.1145/3605764.3623985) |
| [22] `beel2016reproducibility` | 225 | Frozen inputs và explicit configurations xử lý các vấn đề reproducibility đã được ghi nhận. | **Có; đúng.** *User Modeling and User-Adapted Interaction* 26(1), 69-101, 2016; DOI khớp. | **`supported`.** Nguồn nêu tác động của dataset, scenario và configuration tới reproducibility. | [Springer](https://link.springer.com/article/10.1007/s11257-016-9174-x) |
| [23] `pineau2021reproducibility` | 227 | Artifact practice phản chiếu các phần của NeurIPS program: code submission và checklists. | **Có; đúng.** *JMLR* 22(164), 1-20, 2021; tám authors; không DOI. | **`supported`.** Bản mới gọi đúng hai component mà source liệt kê, không gán bảo đảm rộng hơn. | [JMLR](https://www.jmlr.org/papers/v22/20-303.html) |
| [24] `artstein2008agreement` | 288 | Agreement coefficient sẽ được chọn theo label scale và assumptions. | **Có; đúng.** *Computational Linguistics* 34(4), 555-596, 2008; authors và DOI khớp. | **`supported`.** Sample target và số annotator đã được tách sang dòng 286; citation chỉ hỗ trợ nguyên tắc chọn coefficient. | [ACL Anthology](https://aclanthology.org/J08-4004/) |
| [25] `efron1979bootstrap` | 288 | Uncertainty analysis sẽ resample whole conversations và nêu rõ bootstrap interval. | **Có; đúng.** *Annals of Statistics* 7(1), 1-26, 1979; author và DOI khớp. | **`supported`.** Efron hỗ trợ bootstrap; unit resampling và interval là lựa chọn protocol được manuscript tự khai báo, không quy cho nguồn. | [Project Euclid](https://projecteuclid.org/journals/annals-of-statistics/volume-7/issue-1/Bootstrap-Methods-Another-Look-at-the-Jackknife/10.1214/aos/1176344552.full) |
| [26] `jin2024crsque` | 290 | User-facing constructs sẽ được khai báo từ CRS-Que trước khi thu thập. | **Có; đúng.** *ACM TORS* 2(1), Article 2, 34 trang, 2024; authors và DOI khớp. | **`supported`.** CRS-Que cung cấp và validate các construct đánh giá user-centric. | [ACM DOI](https://doi.org/10.1145/3631534) |

## Đối chiếu khóa, duplicate và malformed

- `keys(main.tex) - keys(ref.bib) = ∅`: không có citation key thiếu.
- `keys(ref.bib) - keys(main.tex) = ∅`: không có entry không được dùng.
- Hai khóa được cite hai lần là `jannach2021survey` và `lei2020ear`; đây là
  occurrence lặp hợp lệ, không phải duplicate entry.
- Không có duplicate citation key, duplicate bibliographic work, duplicate DOI
  string hoặc entry malformed.
- Dạng page `105:1--105:36`, `20:1--20:49`, `96:1--96:33` và `2:1--2:34`
  đi cùng `articleno`; chúng biểu diễn article number và page count, không phải
  metadata error. AutoGen không có `pages`, đúng với record COLM hiện tại.

## Trạng thái các correction đã áp dụng

| Key / claim | Trạng thái hiện tại |
|---|---|
| `jannach2023evaluating` | Subtitle `A Landscape of Research` đã có; metadata đúng. |
| `yao2023react` | Author đã chuẩn hóa thành `Karthik Narasimhan`; metadata đúng. |
| `guo2024multiagents` | DOI collision đã bị bỏ; official IJCAI URL được giữ. |
| `wu2024autogen` | Title accepted số nhiều, 14 authors gồm Jiale Liu, và không còn unofficial pages. |
| `nist2020privacy` | Corporate author, `NIST CSWP 10`, DOI `.10` và URL canonical đã có. |
| `ferraridacrema2021troubling` | Compound surname được nhập là `{Ferrari Dacrema}` và render thành `M. {Ferrari Dacrema}` tại `main.bbl:184`. |
| `lewis2020rag` | Hyphenated first name được nhập là `Yih, Wen-tau` và render đúng thành `W.-t. Yih` tại `main.bbl:129`. |
| `pineau2021reproducibility` | Compound surname được nhập là `{d'Alch{\'e}-Buc}, Florence` và được giữ nguyên tại `main.bbl:230`. |
| `guo2024multiagents` note | Capitalization được bảo vệ bằng `{{Survey Track}}`; `main.bbl:113` giữ `{Survey Track}`. |
| EAR tại dòng 86 và 110 | Đã dùng đúng estimation--action--reflection; cả hai occurrence supported. |
| Pineau tại dòng 227 | Chỉ nêu code submission và checklist như các component của program; supported. |
| Privacy tại dòng 186 | Chỉ viện dẫn data-minimization goals; không claim anonymity/compliance; supported. |
| Security tại dòng 190 | Chỉ dùng indirect injection làm motivation và phủ định secure-jail/SSRF claim; supported. |
| Artstein/Efron tại dòng 286-288 | Project-specific sample design đã tách khỏi citation; hai method claim đều supported. |

## Vấn đề DOI và URL còn cần ghi nhớ

### DOI collision của Guo

Official IJCAI record và BibTeX page in DOI `10.24963/ijcai.2024/890` cho Guo
et al., trang 8048-8057. Tuy nhiên DOI resolver hiện trả record:

> Tian Zhou, Zhaoyang Jia, Dong Yu, and Zhiqi Shen, “DiffECG: Diffusion
> Model-Powered Label-Efficient and Personalized Arrhythmia Diagnosis,”
> 8003-8011.

Vì DOI dẫn tới sai công trình, `ref.bib` **cố ý không có trường `doi`** cho
`guo2024multiagents` và giữ
[`https://www.ijcai.org/proceedings/2024/890`](https://www.ijcai.org/proceedings/2024/890)
làm locator. Không nên khôi phục DOI này hoặc tự đoán DOI khác trước khi registry
được sửa.

### AutoGen: record venue và record Microsoft

[COLM 2024 Accepted Papers](https://colmweb.org/2024/AcceptedPapers.html) liệt kê
title số nhiều **AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent
Conversations** và có Jiale Liu trong 14 authors. Đây là record authoritative
cho accepted paper và khớp `ref.bib` hiện tại.

[Microsoft Research](https://www.microsoft.com/en-us/research/publication/autogen-enabling-next-gen-llm-applications-via-multi-agent-conversation-framework/)
hiện hiển thị title số ít và 13 authors không có Jiale Liu. Đây là discrepancy
first-party đáng lưu ý, không phải lỗi của BibTeX đang dùng record venue.

### Các locator khác

- NIST hiện dùng DOI canonical `10.6028/NIST.CSWP.10`; legacy DOI không còn
  trong bibliography.
- Năm entry không DOI là hợp lý: `lewis2020rag`, `liu2024agentbench`,
  `pineau2021reproducibility`, `wu2024autogen`, và `yao2023react`.
- Mỗi key trong bảng có ít nhất một locator publisher, proceedings, anthology
  hoặc institutional chính thức. Không dùng arXiv DOI hay DOI tự suy diễn.

## Phán quyết

Audit này phản ánh đúng `main.tex` và `ref.bib` hiện tại: **28 occurrence, 26
khóa duy nhất, 26 entry, không missing, không unused và không duplicate**. Cả
26 công trình đều tồn tại và metadata hiện tại phù hợp record chính thức được
chọn. Sau khi wording được thu hẹp, cả **28/28 occurrence đều `supported`**;
không còn occurrence `partial` hoặc `not supported`.

Bibliography không cần correction bổ sung từ audit này. DOI Guo phải tiếp tục
được bỏ cho đến khi collision trong registry được sửa; AutoGen tiếp tục theo
record accepted của COLM thay vì record Microsoft Research khác biệt.
