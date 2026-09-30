# SalePilot Agent — Tổng quan dự án

> Tài liệu này tổng hợp toàn bộ hiểu biết về dự án sau khi đọc source code. Mục tiêu: giúp người mới (hoặc phiên làm việc sau) nắm được kiến trúc, luồng dữ liệu, và cách vận hành mà không phải đọc lại từ đầu.

---

## 1. Dự án là gì?

**SalePilot** là một trợ lý bán hàng / CSKH **đa tác nhân (multi-agent)** cho ngành **điện máy – công nghệ**, xây dựng cho cuộc thi **VAIC 2026** (đề bài của Điện Máy Xanh, track *SME Productivity*).

Bài toán gốc (`requirements.md`): *"AI Product Comparison Advisor Based on Real Customer Needs"* — tư vấn & so sánh sản phẩm **theo nhu cầu thật của khách**, không phải chỉ liệt kê thông số.

Đặc điểm cốt lõi:
- **Tư vấn theo nhu cầu (need discovery):** hỏi ngược để thu thập nhu cầu (số người, diện tích phòng, ngân sách, ưu tiên…) → xếp hạng → **Top 3 + trade-off**.
- **Grounding / chống bịa (anti-hallucination):** mọi con số chỉ đến từ tool/catalog; **không bao giờ khẳng định còn hàng** (nguồn dữ liệu không có cột tồn kho); nói "chưa có dữ liệu" khi thiếu.
- **Đa ngành hàng:** ~8.746 SKU trên 14 ngành (từ `Spec_cate_gia.xlsx`), cộng thêm crawl thực tế từ dienmayxanh.com.
- **Đa kênh:** Web chat + Zalo OA (stub).
- **Tiếng Việt:** hiểu tiếng Việt đời thường (không dấu, viết tắt, tiếng lóng, đơn vị m²/HP/BTU/kg/lít…).

### Ngành hàng
Cấu hình sâu (deep) và generic được khai báo trong `backend/app/catalog/categories.py`. Các ngành có rule sâu gồm (theo `category_id` thật của dienmayxanh):
`dien_thoai` (42) · `laptop` (44) · `tivi` (1942) · `tai_nghe`/loa (13698) · `may_lanh` (2002) · `tu_lanh` (1943, mặc định) · `may_giat` (1944) · `may_hut_bui` (12298).
Các ngành long-tail còn lại được sinh **generic** tự động (`make_generic`) để hệ thống không gãy khi gặp ngành chưa cấu hình sâu.

> ⚠️ **Lưu ý mâu thuẫn tài liệu:** README và một vài docstring nói "MongoDB primary / 14 ngành / mã code 38 cho tủ lạnh". Nhưng **code hiện tại là nguồn chính xác**: `CATALOG_BACKEND=postgres` (mặc định), thứ tự fallback Postgres → MongoDB → snapshot; và tủ lạnh dùng `category_code=1943` trong registry đa ngành mới (mã 38 là của snapshot tủ lạnh cũ `products.json`). Đây là dấu vết của quá trình pivot dữ liệu.

---

## 2. Stack công nghệ

| Lớp | Công nghệ |
|-----|-----------|
| Backend | Python 3.12, **FastAPI** (v0.6.0), **LangGraph + LangChain** (multi-agent), Pydantic-settings |
| LLM | Đa provider: OpenAI (hoặc OpenAI-compatible: Groq/DeepSeek/Together/Ollama/vLLM…) và Anthropic; có **offline fallback** rule-based khi không có API key |
| CSDL quan hệ | **PostgreSQL** (primary: CRM, memory, mirror catalog, KB) — async `asyncpg` + sync `psycopg2` |
| CSDL tài liệu | **MongoDB** (catalog document store, thứ cấp) |
| Vector/RAG | **Chroma** (tùy chọn) + lexical search JSON fallback |
| REST tự sinh | **PostgREST** (read-only trên bảng catalog/KB) |
| Frontend | **Next.js 14** (App Router), React 18, TypeScript — không dùng Tailwind, CSS thủ công |
| Tích hợp ngoài | **MCP server** (stdio, Node.js + `@modelcontextprotocol/sdk`) bắc cầu tới API `/mcp/*` |
| Hạ tầng | Docker Compose (mongo, postgres, postgrest, backend, frontend); deploy cloud (Neon Postgres + MongoDB Atlas) |

---

## 3. Sơ đồ kiến trúc tổng thể

```
                    ┌─────────────┐         ┌──────────────────┐
   Web chat  ──────▶│  Next.js FE │──HTTP──▶│                  │
   (:3000)          └─────────────┘         │   FastAPI (:8000)│
                                            │                  │
   Zalo OA  ──webhook──▶ /webhooks/zalo ───▶│  services.gateway│
                                            │  .ingest_message │
   MCP client ──stdio──▶ Node MCP ──HTTP──▶ │  /mcp/*          │
                                            └────────┬─────────┘
                                                     │ run_agent()
                                                     ▼
                                    ┌────────────────────────────────┐
                                    │  LangGraph multi-agent (Lead)   │
                                    │  ┌──────────────────────────┐   │
                                    │  │ Tier 1: Offline (no key) │   │
                                    │  │ Tier 2: Fast-path (0-1 LLM)│ │
                                    │  │ Tier 3: Full ReAct graph │   │
                                    │  └──────────────────────────┘   │
                                    │  Tools: catalog · knowledge ·    │
                                    │  crm · order · escalation ·      │
                                    │  memory · skills · sandbox · web │
                                    └───────┬───────────────┬─────────┘
                                            │               │
                          ┌─────────────────┘               └──────────────┐
                          ▼                                                 ▼
                 ┌──────────────────┐                            ┌──────────────────┐
                 │ Catalog engine   │                            │ PostgreSQL        │
                 │ (categories.py + │                            │ (CRM, memory,     │
                 │  repository)     │                            │  runs, jobs, KB)  │
                 │  Postgres→Mongo→ │                            └──────────────────┘
                 │  snapshot        │
                 └──────────────────┘
```

**Đường đi quan trọng:** `User → gateway.ingest_message → run_agent → (offline | fast-path | graph) → tools (catalog/knowledge/crm…) → trả lời tiếng Việt + trace + lưu trajectory`.

---

## 4. Backend — cấu trúc thư mục

```
backend/app/
├── main.py            # FastAPI app, lifespan, /health, /
├── config.py          # Settings (pydantic-settings), tất cả env var
├── api/               # HTTP routers
│   ├── chat.py        # /chat, /chat/stream (SSE)
│   ├── leads.py       # /leads, /leads/conversations
│   ├── products.py    # /products, /products/categories
│   ├── mcp.py         # /mcp/* (contract cho MCP server)
│   ├── memory.py      # /memory
│   ├── outbox.py      # /outbox/zalo
│   ├── runs.py        # /runs, /runs/latest (telemetry agent)
│   └── jobs.py        # /jobs, /jobs/tick (scheduler)
├── services/          # nghiệp vụ
│   ├── gateway.py     # ingest_message — cửa ngõ chung web+zalo
│   ├── conversation.py# get_or_create_conversation, append_message, recent_history
│   ├── leads.py       # create_lead_record, upsert_lead_record
│   └── scheduler.py   # follow-up jobs (loop 30s)
├── agent/             # BỘ NÃO multi-agent LangGraph (xem mục 5)
├── catalog/           # engine catalog category-aware (xem mục 6)
│   ├── categories.py  # registry rule từng ngành (declarative)
│   ├── repository.py  # truy cập sản phẩm + fallback Postgres/Mongo/snapshot
│   └── normalize.py   # parser thông số tiếng Việt
├── channels/          # web (base) + zalo (webhook/client/schemas/mapper)
├── models/            # SQLAlchemy 2.0 entities
├── db/                # session.py (async), sync.py (sync)
├── rag/store.py       # FAQ/policy lexical search + Chroma ingest
├── data/              # dữ liệu (xem mục 9)
└── scripts/           # ETL & tiện ích (xem mục 8)
```

### 4.1. Điểm vào & cấu hình
- **`main.py`** — `create_app()` (title "SalePilot" v0.6.0), CORS từ `cors_origin_list`, mount tất cả router. `lifespan`: tạo thư mục data, `init_db()` (tạo bảng), warm catalog cache (`repository.load()` trong thread), khởi động `scheduler_loop`.
  - `GET /` → `{"ping":"pong","ok":true}` (liveness).
  - `GET /health` → metadata: shop, catalog `{source, products, categories}`, `llm_provider`, cờ `features`.
- **`config.py`** — `Settings` cache bằng `@lru_cache`, đọc `.env`. Xem đầy đủ env var ở **mục 10**.

### 4.2. HTTP API (tóm tắt endpoint)

| Method + Path | Chức năng |
|---|---|
| `POST /chat`, `/chat/` | Chat 1 lượt; sinh `external_id` web nếu thiếu; gọi `ingest_message`; trả `reply, used_agents, used_tools, trace, needs_human, run_id, memory, active_skills…` |
| `POST /chat/stream` | Chat SSE (`text/event-stream`), phát event `memory/trace/token/done` qua `run_agent_stream` |
| `GET /leads`, `/leads/conversations` | Danh sách lead / hội thoại gần đây |
| `GET /products`, `/products/categories` | Tìm sản phẩm (validate category) / đếm theo ngành |
| `GET /mcp/products`, `/mcp/products/{sku}` | Contract cho MCP: tìm & chi tiết sản phẩm (phân trang) |
| `POST /mcp/product-comparisons` | So sánh 2–5 SKU |
| `POST /mcp/recommendations` | Top-3 theo nhu cầu (hoặc trả câu hỏi làm rõ) |
| `GET /mcp/knowledge/faq` | Tra FAQ/policy |
| `POST /mcp/leads` (201) | Tạo lead — **cần header `x-salepilot-mcp-token`** (503 nếu chưa bật, 401 nếu sai; so sánh `hmac.compare_digest`) |
| `GET /memory`, `/memory/{channel}/{external_id}` | Hồ sơ khách hàng |
| `GET /outbox/zalo` | Hộp thư gửi Zalo (mock) |
| `GET /runs`, `/runs/latest` | Telemetry mỗi lượt agent (trace/agents/tools) |
| `GET /jobs`, `POST /jobs/tick` | Scheduler jobs / tick thủ công |
| `POST /webhooks/zalo`, `/webhooks/zalo/` | Webhook Zalo OA (verify chữ ký, dedup, escalation) |

### 4.3. Service layer
- **`gateway.ingest_message(channel, external_id, text, customer_name, conversation_id?)`** — cửa ngõ chung: đảm bảo conversation → lưu tin user → lấy history → `run_agent(...)` → lưu tin assistant kèm meta → trả kết quả. Cả web và Zalo đều đi qua đây.
- **`conversation.py`** — quản lý phiên & tin nhắn (`get_or_create_conversation`, `append_message`, `recent_history` giới hạn 12 tin).
- **`leads.py`** — `create_lead_record` (luôn insert), `upsert_lead_record` (idempotent theo `(channel, external_id)`, **không hạ cấp** status đã tiến triển thủ công).
- **`scheduler.py`** — `scheduler_loop` chạy mỗi 30s, xử lý `scheduled_jobs` đến hạn → ghi `outbox_messages` (follow-up) + cập nhật lead. `/jobs/tick` để trigger tay.

### 4.4. Data model (SQLAlchemy `models/entities.py`)
- **Catalog/KB (đọc, expose qua PostgREST):** `categories`, `products` (`CatalogProduct`, PK `sku`, có JSON `norm`/`specs`), `product_specs` (EAV: 1 dòng/spec), `kb_docs`.
- **CRM/runtime:** `leads`, `conversations`, `messages`, `order_drafts`, `outbox_messages`, `processed_events` (idempotency webhook), `customer_memories` (profile_json+summary), `scheduled_jobs`, `agent_runs` (telemetry đầy đủ trace/agents/tools/memory/skills).

### 4.5. DB layer
- **`db/session.py`** (async, asyncpg) — CRM/memory/webhook. Với Postgres cloud (Neon) tự thêm SSL + tắt statement cache (chạy sau PgBouncer). `init_db()` auto-tạo bảng khi khởi động.
- **`db/sync.py`** (sync, psycopg2) — engine đồng bộ cho **catalog ranking** (engine xếp hạng là code đồng bộ) và ETL. → Kiến trúc **2 engine trên cùng 1 Postgres**.

---

## 5. Bộ não multi-agent (`backend/app/agent/`)

Entry point export ở `__init__.py`: **`run_agent`** và **`run_agent_stream`**.

### 5.1. LLM & provider (`llm.py`)
- `_resolve_provider()`: ưu tiên `LLM_PROVIDER`; nếu key trống thì tự dùng key nào có. Hỗ trợ **cả OpenAI-compatible và Anthropic**.
  - Anthropic → `ChatAnthropic`, mặc định `claude-haiku-4-5`.
  - OpenAI/compatible → `ChatOpenAI`; nếu có `OPENAI_BASE_URL` thì tin `MODEL_NAME` verbatim.
- Tham số chung: `temperature=0.3`, `max_tokens=700`, `timeout=30s`, `max_retries=1` (fail nhanh).
- `has_llm_key()` = False → `get_chat_model()` trả **`_FallbackModel`** (canned reply, `bind_tools` là no-op).

### 5.2. LangGraph (`graph.py`, `state.py`)
- **State** `AgentState`: `messages` (reducer `add_messages`), `channel`, `external_id`, `conversation_id`, `lead_id`, `customer_name`, `needs_human`, `active_agents`, `subagent_results`, `trace`, `final_reply`.
- **Graph** = vòng lặp ReAct tối giản, compile 1 lần & cache: node `"lead"` (async) + `"tools"` (`ToolNode(LEAD_TOOLS)`); entry `"lead"`; điều kiện `should_continue` → `"tools"` nếu có `tool_calls`, ngược lại `END`; cạnh `"tools" → "lead"`; `recursion_limit=24`.
- **`lead_node`**: bind `LEAD_TOOLS`, chèn system prompt, chèn **skill bodies đã activate** (`[Active skills]`) và **kết quả sub-agent** (`[Sub-agent results]`), trả response + snapshot trace.
- **"run bag"** (`run_bag.py`): dict **module-global** chia sẻ trace/results/final/skill giữa tool & skill (tránh circular import). ⚠️ Giả định xử lý **tuần tự per-worker** (turn đồng thời trong 1 process sẽ dùng chung bag). `ToolContext` (`tools/runtime.py`) thì dùng `ContextVar` đúng chuẩn.

### 5.3. Ba tầng thực thi trong `run_agent`
1. **Tier 0 — memory prep:** nạp profile + summary, `maybe_extract_from_text` (heuristic cập nhật memory).
2. **Tier 1 — Offline path** (`offline.py`): khi **không có API key** → advisor rule-based đa ngành, mô phỏng đúng hình dạng multi-agent (detect intent/category, tích lũy need, "delegate" song song `do_compare/do_catalog/do_knowledge` bằng `asyncio.gather`, CRM/escalation khi cần), format Top-3/so sánh tiếng Việt. **Đảm bảo chạy được không cần LLM.**
3. **Tier 2 — Fast-path** (`_try_fast_path`): với intent gợi ý sản phẩm rõ ràng → **bỏ qua graph**. Detect category + tích lũy need + budget từ memory; cổng `_looks_like_recommend()` (loại nếu có SĐT/FAQ/escalation/compare keyword); chạy `recommend_top3`; nếu thiếu slot → hỏi lại; nếu OK → tùy chọn **1 lần** LLM `_phrase_recommendation` (chỉ khi `FAST_PATH_PHRASING=true`, timeout 25s, lỗi thì fallback `_format_top3` deterministic); upsert lead "qualified"; trả `fast_path: True`.
4. **Tier 3 — Full graph:** dựng messages (system+memory, replay history), `graph.ainvoke`. Lỗi LLM → degrade thành thông báo tiếng Việt thân thiện (không trả 500 thô). Sau run: gom agents, (tùy chọn) auto-write skill, reload memory, lưu trajectory.

**Return dict** (mọi path): `reply, used_tools, used_agents, trace, subagent_results, needs_human, lead_id, conversation_id, run_id, memory, memory_summary, active_skills, memory_before` (+ `fast_path`).

`run_agent_stream` phát event SSE `memory → trace → token (chunk reply) → done` (không stream token thật từ LLM, mà chunk lại reply đã xong).

### 5.4. Điều phối Lead — delegate / finalize (`lead_tools.py`)
Quyết định thiết kế: **catalog & knowledge được Lead gọi TRỰC TIẾP** (deterministic, hot-path); `delegate` chỉ dành cho specialist hiếm hơn `crm | order | escalation`.

`LEAD_TOOLS`:
- Trực tiếp: `recommend_top3`, `search_products`, `compare_products`, `get_product_detail`, `list_categories`, `search_knowledge`
- Điều phối: `delegate`, `delegate_many` (parse JSON, cap `max_subagents_per_turn=3`, chạy song song), `finalize(reply)`
- Memory: `recall_customer`, `remember_customer`
- Skills: `list_skills_tool`, `activate_skill`
- Sandbox/web: `run_sandbox`, `fetch_page`

### 5.5. Sub-agents (`subagents/base.py`)
Registry `SUBAGENTS` (name → tool được phép):
- **catalog**: list_categories, search_products, get_product_detail, compare_products, recommend_top3
- **knowledge**: search_knowledge
- **crm**: create_lead, update_lead_status, schedule_followup
- **order**: create_order_draft
- **escalation**: escalate_to_human

`run_subagent` = mini ReAct **cap cứng 2 bước** (`MAX_SUBAGENT_STEPS=2`), mỗi sub-agent có prompt riêng, chỉ bind tool được phép, trả `{agent, task, summary, data, tools_used, ok}`.

### 5.6. Danh mục tool đầy đủ
- **Catalog** (`tools/catalog.py`): `list_categories`, `search_products`, `get_product_detail`, `compare_products`, `recommend_top3` (luôn truyền `free_text` để engine bóc slot m²/kg/inch/RAM/lít).
- **Knowledge** (`tools/knowledge.py`): `search_knowledge` → `rag.store.search_faq(k=3)`.
- **CRM** (`tools/crm.py`): `create_lead`, `update_lead_status`, `schedule_followup` (tạo `ScheduledJob` thật), `escalate_to_human`.
- **Order** (`tools/order.py`): `create_order_draft` (validate `[{sku,qty}]`, qty 1–10, SKU phải có giá; không có tồn kho).
- **Memory** (`memory/tools.py`): `recall_customer`, `remember_customer`.
- **Skills** (`skills/tools.py`): `list_skills_tool`, `activate_skill` (progressive load body ≤8000 ký tự).
- **Sandbox** (`sandbox/tools.py`): `run_sandbox`.
- **Web** (`web/tools.py`): `fetch_page`.

### 5.7. Skills subsystem (`skills/`) — progressive disclosure
- **`loader.py`**: `SkillMeta`, parse SKILL.md (frontmatter `name/description/agents` + body). Prompt Lead chỉ thấy **metadata**; body chỉ nạp khi `activate_skill(name)`.
- **`writer.py`**: `maybe_write_skill_from_run` — nếu `AUTO_SKILL_WRITE=true` và ≥2 specialist tham gia → tự viết `auto_<slug>/SKILL.md` (mặc định TẮT).
- **9 skill có sẵn** (`skills/<name>/SKILL.md`):
  1. `advisory_playbook` — logic tư vấn từng ngành (slot chính, câu hỏi ngược, priority→tiêu chí kỹ thuật).
  2. `compare_products` — so sánh 2–5 sản phẩm bằng lợi ích, không phải bảng spec.
  3. `explain_specs_plainly` — dịch thông số sang lợi ích đời thường.
  4. `grounding_guardrail` — chống bịa: số chỉ từ tool, trích SKU, không khẳng định tồn kho.
  5. `handoff` — khi nào/ cách chuyển người thật.
  6. `lead_qualify` — nhận tín hiệu mua, tạo lead không ép SĐT sớm.
  7. `need_discovery` — hỏi ngược thông minh trước khi gợi ý.
  8. `sales_consult` — workflow Top-3 xương sống.
  9. `vietnamese_input` — hiểu tiếng Việt mua sắm thực tế.

### 5.8. Các subsystem phụ trợ
- **Sandbox** (`sandbox/shell.py`): whitelist `{date, pwd, ls, wc, head, cat, echo}`, jail path trong `backend/data`, không shell/network/write, timeout 5s.
- **Web** (`web/fetch.py`): chỉ http/https, **chống SSRF** (chặn localhost/private IP), timeout 12s, cắt body 200KB, strip HTML, trả ≤5000 ký tự.
- **Memory** (`memory/store.py`): SQL-backed theo `(channel, external_id)`, có `need` dict tích lũy đa lượt; `maybe_extract_from_text` bóc SĐT/category/budget an toàn offline.
- **Trajectory** (`trajectory/export.py`): mỗi lượt sinh `run_id` 16-hex, ghi file `data/trajectories/<run_id>.json` + hàng `AgentRun` SQL. (Hiện có ~251 file trajectory.)

---

## 6. Engine catalog category-aware (`backend/app/catalog/`)

### 6.1. `categories.py` — registry rule khai báo
Dataclasses: `Spec` (field chuẩn hóa từ cột gốc, mode num/min/max/int/gb/text/yesno/present/flag), `RangeSpec` (`_min`/`_max`, kind people/area), `Slot` (nhu cầu cần thu thập, kind proximity/max_constraint/min_constraint/range_fit + regex extract + trọng số), `Priority` (keyword ưu tiên → spec), `Tradeoff`, `Category`.
- `normalize_product(cat, product, source)` → tạo document chuẩn (parse giá/rating/sold, áp spec, sinh `name/description/search_text`).
- Lookup `BY_SLUG/BY_CODE/BY_SHEET`; `make_generic` + `_generic_registry` cho long-tail; `get_category(ref)` resolve theo int code hoặc slug.
- **Detect intent:** `detect_category` (alias dài nhất thắng, ưu tiên deep), xử lý phủ định (`detect_negated_categories`, "ko phải tủ lạnh" vs "chưa có tủ lạnh"), `detect_unsupported` (ô tô/xe máy/thực phẩm/du lịch/BĐS → từ chối trung thực).

### 6.2. `catalog_domain.py` — bộ não gợi ý (deterministic)
- `search(...)` — tìm theo category + filter + relevance scoring.
- `compare(skus)` — 2–5 SKU, sinh trade-off theo `cat.tradeoffs`.
- Bóc nhu cầu: `_extract_budget` (parser tiền Việt: "dưới 15tr", "10–12 triệu", "500k"…), `extract_need_from_text`, `merge_needs` (fresh thắng; đổi ngành reset slot nhưng giữ budget), `resolve_followup_answer` (map câu trả lời cụt "50"/"phòng ngủ"/"9" vào slot vừa hỏi).
- `_score` (fit ngân sách + brand + style + slot kind + priority + tie-break rating/độ phổ biến/giảm giá/quà), `_why` (giải thích).
- **`recommend_top3(need)`** — resolve category (không mặc định ngành chưa hỏi), gate slot thiếu (`need_more` + câu hỏi trừ khi `force`), chấm điểm sản phẩm **có giá**, chọn Top-3 **đa dạng brand + khử trùng model** (tránh biến thể màu), kèm `why/match_score/tradeoff` và **disclaimer** (giá/quà tại thời điểm crawl, không có tồn kho realtime).

### 6.3. `repository.py` — truy cập + fallback nhiều tầng
Cache in-memory (`_CACHE`, `_LOCK`). Loader: `_load_from_postgres` → `_load_from_mongo` → `_load_from_snapshot`. `_FALLBACK_ORDER` theo `catalog_backend`:
- `postgres` → (postgres, mongodb, snapshot) — **mặc định**
- `mongodb` → (mongodb, postgres, snapshot)
- `snapshot` → (snapshot,)

`load(force)` dùng kết quả không rỗng đầu tiên. Helper: `by_category`, `get(sku)`, `brands`, `category_counts`, `distinct_categories`, `save_snapshot`.

### 6.4. `normalize.py`
Parser thông số tiếng Việt "dễ tính" (trả None khi fail): `numbers/number/integer/min_number/max_number`, `yes_no`, `price`, `split_features`, `people_range` ("Trên 5 người"→(6,None)), `area_range` (m² cho máy lạnh, bỏ mệnh đề m³).

---

## 7. Kênh (channels) & tích hợp ngoài

### 7.1. Zalo OA (`channels/zalo/`)
- **Mặc định `ZALO_CLIENT=mock`**: `MockZaloOAClient` chỉ ghi `OutboxMessage` (status "sent_mock"), không gọi API thật. `HttpZaloOAClient` là skeleton POST tới `openapi.zalo.me`.
- **`webhook.py`** (`/webhooks/zalo`): verify HMAC-SHA256 (`ZALO_VERIFY_MODE`: off/soft/strict), parse JSON, dedup qua `ProcessedEvent`, xử lý `user_send_text`/`user_send_image`/`follow`; text → log inbound → `ingest_message(channel="zalo")` → nếu `needs_human` thì escalate → gửi reply qua client → ghi `ProcessedEvent`.

### 7.2. MCP server (`mcp/`) — Node.js stdio
Bắc cầu MCP client ↔ FastAPI `/mcp/*` (tập trung vào tủ lạnh `category_code=38` từ snapshot cũ):
```
MCP client --stdio--> Node MCP server --HTTP--> FastAPI /mcp/*
```
- `api-client.ts`: base URL `SALEPILOT_API_BASE_URL` (default `127.0.0.1:8000`); **chặn host non-local** trừ khi `SALEPILOT_ALLOW_REMOTE_API=true`; timeout 10s; validate bằng Zod; write gửi header `x-salepilot-mcp-token`.
- **6 tool** (`tools.ts`): `salepilot_search_products`, `salepilot_get_product`, `salepilot_compare_products`, `salepilot_recommend_products`, `salepilot_search_faq` (read-only), và `salepilot_create_lead` (**write, cần `confirmed:true` + token**).
- Chạy: `cd mcp && npm ci && npm run build && npm run start`; smoke `npm run smoke`.

---

## 8. Scripts ETL & tiện ích (`backend/scripts/`)

Chạy dạng module từ `backend/`: `python -m scripts.<name>`.

| Script | Vai trò | CLI chính |
|---|---|---|
| `import_spec_catalog.py` | Import workbook `Spec_cate_gia.xlsx` (đa ngành) → Mongo `products` + snapshot. Đây là importer tạo catalog 8.746 SKU/14 ngành | `--excel`, `--snapshot-only` |
| `import_products_detail.py` | Import crawl thật dienmayxanh (`products_detail.json`) → Mongo, route theo Category, dedup, prune | `--json`, `--snapshot-only`, `--skip-existing` |
| `import_refrigerators.py` | Import Google Sheet tủ lạnh (code 38) → snapshot `data/products.json` | `--source`, `--output` |
| `import_policies.py` | Ingest policy `.md` → chunk ~750 ký tự → `data/faq.json` + copy vào `data/policies/` | `--src`, `--out` |
| `etl_to_postgres.py` | ETL catalog+KB → PostgreSQL (4 bảng), tạo role PostgREST + grant read-only | `--source {snapshot,mongo}` |
| `ingest_kb.py` | Wrapper `rag.store.ingest_kb()` (nạp KB vào Chroma) | — |
| `seed_db.py` | `init_db()` + warm catalog + seed 2 lead demo | — |
| `simulate_zalo.py` | Giả lập webhook Zalo `user_send_text` | `--text`, `--user-id`, `--url` |
| `verify_mcp.py` | Smoke contract `/mcp/*` bằng ASGITransport in-process | — |

---

## 9. Dữ liệu (`backend/data/`)

- **`faq.json`** (~104 entry): `{id, question, answer, topic, source}`. Topic: dieu_khoan(32), du_lieu_ca_nhan(22), bao_hanh_doi_tra(19), giao_hang_lap_dat(18), noi_quy(6), phuc_vu(4), khui_hop_apple(3).
- **`need_scenarios.json`** (6 kịch bản `sc-01..06`): `{id, user, expect_slots}` — validate bóc nhu cầu.
- **`products.json`** (~1.692 tủ lạnh, snapshot offline từ `import_refrigerators.py`, 45 key/item).
- **`catalog_snapshot.json`** (~45 MB, 8.746 SKU đa ngành) — fallback offline chính.
- **`policies/*.md`** (7 file): chất lượng phục vụ, bảo hành/đổi trả, giao hàng/lắp đặt, khui hộp Apple, xử lý dữ liệu cá nhân, điều khoản sử dụng, nội quy cửa hàng.
- **`chroma/`** (vector store), **`trajectories/`** (~251 file log lượt agent), `salepilot.db` (SQLite cũ, nếu có).
- **`PRODUCT_SOURCE.md`** — nguồn gốc catalog tủ lạnh (workbook, Sheet ID, GID, filter code 38).

### Test (`backend/tests/test_skills_cot.py`)
3 nhóm: (1) SKILL.md well-formed (frontmatter, agents hợp lệ, body ≤6000, delegate chỉ crm/order/escalation, ≥4 ngành); (2) CoT khớp engine (routing category, ask-back máy lạnh nhắc m², out-of-scope xe máy, compare ra trade-off); (3) skill critical tồn tại + không bịa khi ngân sách bất khả thi + disclaimer nhắc "tồn kho" + parse không dấu ("12tr","18m2").

---

## 10. Biến môi trường (`.env.example`)

**LLM:** `LLM_PROVIDER`, `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `ANTHROPIC_API_KEY`, `MODEL_NAME`, `FAST_PATH_PHRASING` (false=Top-3 Markdown tức thì không LLM), `LLM_MAX_TOKENS`, `LLM_TIMEOUT_S`. *Không key → offline advisor.*
**Backend:** `BACKEND_HOST`, `BACKEND_PORT`, `CORS_ORIGINS`, `CHROMA_PATH`.
**PostgreSQL:** `DATABASE_URL` (asyncpg), `POSTGRES_DSN` (psycopg2), `CATALOG_BACKEND` (postgres/mongodb/snapshot), `POSTGRES_USER/PASSWORD/DB`. (Cloud thêm `DATABASE_URL_UNPOOLED` — Neon direct, dùng trong `check_cloud_db.py`.)
**MongoDB:** `MONGODB_URI`, `MONGODB_DB`, `MONGO_ROOT_USER/PASSWORD`, `MONGO_DB`.
**MCP:** `MCP_WRITE_TOKEN` (chỉ cần để tạo lead qua MCP).
**Frontend:** `NEXT_PUBLIC_API_URL`.
**Zalo:** `ZALO_ENABLED`, `ZALO_CLIENT`, `ZALO_OA_ACCESS_TOKEN`, `ZALO_OA_SECRET`, `ZALO_WEBHOOK_SECRET`, `ZALO_VERIFY_MODE`.
**Feature flags:** `MEMORY_ENABLED`, `AUTO_SKILL_WRITE`, `SANDBOX_ENABLED`, `WEB_FETCH_ENABLED`, `SCHEDULER_ENABLED`, `TRAJECTORY_ENABLED`, `MAX_SUBAGENTS_PER_TURN`.

---

## 11. Frontend (`frontend/`) — Next.js 14

- **Stack:** Next.js 14 (App Router), React 18, TS strict, không Tailwind (CSS thủ công `globals.css`), `output: standalone` (Docker), path alias `@/*`.
- **Layout** (`app/layout.tsx`): `lang="vi"`, script no-flash theme (đọc `localStorage['salepilot_theme']`, mặc định dark), `<Nav/>` + footer.
- **Trang:**
  - `/` (`page.tsx`) — landing marketing, 4 card tính năng, giới thiệu agent Lead·Catalog·Knowledge·CRM.
  - `/chat` (`chat/page.tsx`, client) — 2 cột: chat panel (chip gợi ý, phiên lưu `localStorage`, render reply qua `<Markdown/>`) + **Agent Trace panel** (memory summary, badge agent, run_id, các `TraceStep`).
  - `/dashboard` (`dashboard/page.tsx`, client) — auto-refresh 7s, 6 fetch song song (leads/conversations/zalo outbox/memory/jobs/latest run), stat card + bảng lead/memory/jobs/conversations/outbox + latest run.
- **API layer** (`lib/api.ts`): `API_URL = NEXT_PUBLIC_API_URL || "https://optivisionlab.fit-haui.edu.vn"` (fallback prod hardcode). `chatOnce` → `POST /chat`; các GET helper `/leads`, `/leads/conversations`, `/outbox/zalo`, `/memory`, `/jobs`, `/runs/latest`.
- **Components:** `Nav.tsx` (nav sticky + active state), `ThemeToggle.tsx` (dark/light), `Markdown.tsx` (renderer Markdown tự viết, **không `dangerouslySetInnerHTML`** → an toàn output model).
- **Theming:** CSS custom properties, dark mặc định + `:root[data-theme="light"]`, màu riêng cho từng agent (badge trace).

---

## 12. Vận hành

### Quick start (local)
```bash
cp .env.example .env
docker compose up -d mongo postgres          # hoặc dùng cloud qua .env

cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.import_spec_catalog --excel ../Spec_cate_gia.xlsx   # nạp catalog
python -m scripts.seed_db && python -m scripts.ingest_kb
./run.sh                                       # uvicorn :8000 (load ../.env)

# Terminal B
cd frontend && npm install && npm run dev      # :3000
```
Không có DB? Engine tự fallback snapshot → path offline & verify vẫn chạy.

### Docker
```bash
cp .env.example .env
docker compose up --build
```
`docker-compose.yml`: mongo(:27017), postgres(:5433→5432), postgrest(:3001), backend(:8000, `CATALOG_BACKEND=postgres`, trỏ cloud qua `.env`), frontend(:3000).

### Verify / smoke
```bash
./init.sh                # cài + baseline verify
./scripts/verify.sh      # smoke đa tác nhân offline (assert 8746 SKU/14 ngành, offline flow, guardrail, sandbox, memory, MCP…)
python check_cloud_db.py # test kết nối Neon + Atlas
```

### Manual API smoke
```bash
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/chat -H 'Content-Type: application/json' \
  -d '{"message":"Gia đình 4 người cần tủ lạnh dưới 15 triệu, ngang tối đa 70 cm","external_id":"verify","channel":"web"}'
```

---

## 13. Harness kỹ thuật (cho coding-agent)

Repo được thiết kế cho **coding agent chạy dài** theo mô hình 5 subsystem (Instructions · Tools · Environment · State · Feedback). Xem `AGENTS.md`, `docs/HARNESS.md`.

| File | Vai trò |
|------|---------|
| `AGENTS.md` (+ `backend/`, `frontend/`) | Quy tắc vận hành cho coding agent |
| `feature_list.json` | Bộ theo dõi feature (source of truth): 11 feature, 1 active tại 1 thời điểm, cần evidence mới `passing`. Đã passing: agent-001, chat-001, zalo-001, fridge-001, catalog-002, mcp-001. Chưa: dash-001, trace-001, verify-001, deploy-001, vaic-001 |
| `claude-progress.md` | Log phiên + trạng thái verified (bước tiếp theo: `dash-001`) |
| `init.sh` / `scripts/verify.sh` | Cài đặt + kiểm chứng |
| `session-handoff.md` / `clean-state-checklist.md` | Bàn giao & checklist đóng phiên |
| `requirements.md` | Đề bài VAIC gốc |
| `quality-document.md` / `evaluator-rubric.md` | Chấm chất lượng A–D + rubric 6 tiêu chí |
| `skill_install.sh` | Cài 9 external skill (npx skills) |
| `docs/DEMO_SCRIPT.md` / `docs/ZALO_INTEGRATION.md` / `docs/PIVOT_PLAYBOOK.md` | Runbook demo, tích hợp Zalo, playbook pivot ngành |

---

## 14. Nguyên tắc thiết kế chốt lại

1. **Hai tầng tốc độ:** fast-path deterministic (0–1 LLM) cho intent rõ; full ReAct graph cho câu mơ hồ/FAQ/so sánh/escalation.
2. **Grounding kỷ luật:** số chỉ từ catalog tool; **không bao giờ khẳng định tồn kho**; disclaimer + skill `grounding_guardrail`.
3. **Chịu lỗi:** lỗi/timeout LLM → thông báo tiếng Việt thân thiện; fast-path & offline advisor vẫn phục vụ khi không/không được LLM.
4. **Quan sát được:** mỗi lượt có trace (agent/event/detail) + trajectory (file + SQL `agent_runs`) + tool/agent usage.
5. **Mở rộng ngành dễ:** thêm 1 `Category(...)` trong `categories.py` → chạy lại importer; engine/tool/API/offline tự nhận.
6. **Bảo mật:** MCP write cần token + `confirmed`; sandbox whitelist + jail; web fetch chống SSRF; PostgREST chỉ expose read-only catalog/KB (không lộ bảng CRM).

---

## 15. Điểm cần lưu ý / rủi ro đã phát hiện

- **Mâu thuẫn tài liệu Mongo vs Postgres:** README/docstring nói MongoDB primary, nhưng code mặc định `CATALOG_BACKEND=postgres`. Code là chuẩn — cần đồng bộ lại tài liệu.
- **`run_bag` là singleton module-global:** giả định xử lý tuần tự per-worker; các lượt đồng thời trong cùng process dùng chung bag (khác với `ToolContext` đã dùng `ContextVar` đúng).
- **Hai quy ước base URL backend:** frontend dùng `NEXT_PUBLIC_API_URL` (fallback host prod hardcode `optivisionlab.fit-haui.edu.vn`); MCP dùng `127.0.0.1:8000` + họ endpoint `/mcp/*`.
- **`run_agent_stream` không stream token thật** từ LLM — chỉ chunk lại reply đã hoàn tất.
- **Mã ngành tủ lạnh khác nhau giữa hai thế hệ dữ liệu:** snapshot tủ lạnh cũ dùng `category_code=38` (MCP/`products.json`), registry đa ngành mới dùng `1943`.
- Các connector MCP claude.ai (Box/Figma/Microsoft 365/Sanity/Slack/Supabase) đang **chưa xác thực** — không liên quan chạy dự án, chỉ bỏ qua.
