---
name: advisory_playbook
description: Logic tư vấn theo từng ngành — slot chính, câu hỏi ngược, ưu tiên→tiêu chí.
agents: [lead, catalog]
---

# Sổ tay tư vấn theo ngành (CoT chi tiết)

Nguyên tắc chung cho MỌI ngành: (1) hỏi đúng **slot chính** trước, (2) map **ưu tiên của khách → tiêu chí kỹ thuật** giúp engine lọc, (3) khi trình bày thì dịch ngược tiêu chí → **lợi ích thật** (khách không cần hiểu spec). Khi gọi `recommend_top3` luôn kèm `free_text` nguyên văn để engine tự bóc số.

---
## Máy lạnh (may_lanh)
- **Slot chính:** diện tích phòng (m²).
- **Hỏi ngược:** "Phòng bao nhiêu m²? Phòng ngủ hay khách? Có nắng chiếu trực tiếp không? Ưu tiên chạy êm hay làm lạnh nhanh? Có cần 2 chiều (sưởi mùa đông) không?"
- **Ưu tiên → tiêu chí:** tiết kiệm điện→Inverter; phòng ngủ/êm→độ ồn thấp (dB); lạnh nhanh/phòng nắng→BTU cao hơn 1 bậc; sưởi→2 chiều.
- **Quy đổi công suất theo m²:** ~<15m²→1.0 HP (9.000 BTU); 15–20m²→1.5 HP (12.000 BTU); 20–30m²→2.0 HP (18.000 BTU); >30m² hoặc nắng nhiều→2.5 HP+. Phòng nắng/nhiều người → cộng thêm 1 bậc.
- **Trade-off điển hình:** inverter đắt hơn nhưng tiết kiệm điện dài hạn; BTU lớn mát nhanh nhưng tốn điện & giá cao.
- **Cạm bẫy:** đừng chọn công suất thiếu so với phòng (không mát); phòng nắng mà chọn đúng bậc tối thiểu → thiếu.

## Tủ lạnh (tu_lanh)
- **Slot chính:** số người dùng (suy ra dung tích).
- **Hỏi ngược:** "Nhà mình mấy người? Trữ nhiều đồ/nấu ăn thường xuyên không? Có cần ngăn đá lớn, lấy nước ngoài không? Chỗ đặt rộng bao nhiêu?"
- **Ưu tiên → tiêu chí:** tiết kiệm điện→Inverter; nhà đông/trữ nhiều→dung tích lớn + Side by Side/Multi Door; tiện→lấy nước ngoài, làm đá tự động.
- **Quy đổi dung tích theo người:** 1–2 người→~150–200L; 3–4 người→~300–400L; 5+ người→>450L (thường Side by Side/Multi Door).
- **Trade-off:** side-by-side rộng đẹp nhưng tốn điện & chỗ; ngăn đông lớn thì ngăn mát nhỏ lại.

## Máy giặt (may_giat)
- **Slot chính:** khối lượng giặt (kg) — suy từ số người.
- **Hỏi ngược:** "Nhà mấy người? Cần sấy không? Thích cửa trước hay cửa trên? Đặt ở đâu (ban công/nhà tắm)?"
- **Ưu tiên → tiêu chí:** tiết kiệm điện/êm→Inverter + cửa trước; giặt nhiều/chăn màn→kg lớn; gấp→có sấy.
- **Quy đổi kg theo người:** 1–2 người→~7–8kg; 3–5 người→~9–10kg; >5 hoặc hay giặt chăn→>11kg.
- **Trade-off:** cửa trước giặt sạch–êm–tiết kiệm nhưng đắt & giặt lâu hơn; cửa trên rẻ, nhanh, nhưng tốn nước/điện hơn.

## Tivi (tivi)
- **Slot chính:** kích thước (inch) — suy từ khoảng cách xem.
- **Hỏi ngược:** "Ngồi cách tivi khoảng mấy mét / phòng rộng bao nhiêu? Xem phim, thể thao hay chơi game? Cần OLED/QLED không?"
- **Ưu tiên → tiêu chí:** nét→4K/OLED/QLED; game/thể thao→tần số quét cao (120Hz); phòng lớn→inch to.
- **Quy đổi inch theo khoảng cách:** ~2m→43–50"; ~2.5m→55"; ~3m→65"; >3.5m→75"+.
- **Trade-off:** OLED màu đẹp/tương phản cao nhưng đắt; LED rẻ, đủ dùng phòng sáng.

## Điện thoại (dien_thoai)
- **Slot chính:** ngân sách (+ mục đích).
- **Hỏi ngược:** "Ưu tiên chơi game, chụp ảnh, hay pin trâu? Cần bộ nhớ lớn / 5G không?"
- **Ưu tiên → tiêu chí:** game→chip mạnh + RAM cao; pin→mAh lớn + sạc nhanh (W); chụp ảnh→camera tốt; lưu nhiều→bộ nhớ lớn.
- **Trade-off:** chip mạnh & pin lớn thường nặng/đắt; máy rẻ thì pin/chip vừa phải.

## Laptop (laptop)
- **Slot chính:** ngân sách + mục đích dùng.
- **Hỏi ngược:** "Dùng chủ yếu văn phòng–học tập, hay đồ họa/gaming? Có hay mang đi (cần mỏng nhẹ, pin lâu) không?"
- **Ưu tiên → tiêu chí:** game/đồ họa→card rời (RTX/GTX) + RAM ≥16GB + SSD lớn; văn phòng→card tích hợp, giá tốt; di chuyển→mỏng nhẹ + pin (Wh) lớn.
- **Trade-off:** card rời mạnh nhưng nặng, nóng, pin ngắn, đắt; máy văn phòng nhẹ–rẻ nhưng game yếu.

## Loa & tai nghe (tai_nghe)
- **Hỏi ngược:** "Tai nghe nhét tai / chụp tai / loa? Không dây (Bluetooth) không? Cần chống ồn, hay loa công suất lớn để hát/party?"
- **Ưu tiên → tiêu chí:** di động→không dây + pin lâu; hát/party→công suất (W) lớn; yên tĩnh→chống ồn.

## Máy hút bụi / robot (may_hut_bui)
- **Hỏi ngược:** "Robot tự động hay cầm tay? Nhà rộng bao nhiêu m²? Cần lau nhà luôn không?"
- **Ưu tiên → tiêu chí:** lười/nhà rộng→robot lau nhà + diện tích phủ lớn; sạch sâu→lực hút (Pa) cao; linh hoạt→cầm tay không dây.

---
## Ngành ngoài 8 nhóm trên
Chỉ tư vấn khi catalog hiện tại có dữ liệu cho ngành khách hỏi. Hỏi **ngân sách + mục đích**, rồi `recommend_top3` — engine xếp theo giá + đánh giá ★ + lượt bán. Nếu catalog không có ngành đó → nói thật, đừng ép SP sai ngành (xem `grounding_guardrail`).
