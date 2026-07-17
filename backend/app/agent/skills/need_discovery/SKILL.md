---
name: need_discovery
description: Thu thập nhu cầu tủ lạnh — số người/dung tích, ngân sách, kiểu tủ và kích thước.
agents: [lead, catalog]
---

# Need discovery

Slots bắt buộc trước top 3:
1. household_size hoặc capacity_l
2. budget_vnd (hoặc khách nói linh hoạt → force)
3. Nếu có: preferred_styles, max_width_cm/max_height_cm/max_depth_cm
4. priority: tiet_kiem_dien | gia_re | lay_nuoc_ngoai | tu_dong | dong_mem | bao_quan

Hỏi tối đa 1–2 câu/lượt. Không dump form.
