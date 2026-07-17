# Demo — Điện Máy Xanh · SalePilot (tủ lạnh)

## Setup

```bash
cd backend && source .venv/bin/activate
python -m scripts.seed_db && python -m scripts.ingest_kb
uvicorn app.main:app --reload --port 8000
# other terminal
cd frontend && npm run dev
```

## Flow 3 phút

1. **Home** — SalePilot × nhu cầu thật, top 3, không bịa  
2. **Tư vấn** — chip: “Gia đình 4 người, dưới 15 triệu, cần tủ lạnh tiết kiệm điện”
3. Thêm giới hạn “ngang tối đa 70 cm” → top 3 chỉ gồm mẫu vừa chỗ đặt
4. “Bảng có biết tủ còn hàng không?” → trả đúng giới hạn nguồn, không bịa stock
5. “Em để SĐT 0901111222” → CRM lead  
6. **Agent Trace** — lead → catalog/knowledge  
7. **Dashboard** — lead + conversation  

## Pitch

> Không chỉ dump bảng spec — hiểu số người, ngân sách và chỗ đặt; top 3 có trade-off, mọi giá/thông số từ tab Tủ Lạnh category_code 38.
