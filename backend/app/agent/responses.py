"""Vietnamese response formatting shared by the offline and fast routes."""

from typing import Any

from app.agent.intent import format_need_more


def format_recommendation(rec: dict[str, Any]) -> str:
    display = rec.get("category_display") or "sản phẩm"
    if rec.get("need_more"):
        return format_need_more(rec)
    if not rec.get("ok"):
        return (
            str(rec.get("message") or "Không tìm thấy mẫu phù hợp với các giới hạn đã chọn.")
            + " Bạn có muốn tăng ngân sách hoặc nới điều kiện không ạ?"
        )

    lines = [f"Em gợi ý **top 3 {display.lower()}** phù hợp từ dữ liệu catalog:\n"]
    for i, p in enumerate(rec.get("top3") or [], 1):
        promo = f" · 🎁 {p['gift_promotion'][:70]}" if p.get("gift_promotion") else ""
        lines.append(
            f"{i}. **{p['name']}** (`{p['sku']}`) — {p['price_display']}"
            f" · {p.get('why', '')}"
            f"{promo}"
        )
    trade = rec.get("tradeoffs") or []
    if trade:
        lines.append("\n**Trade-off nhanh:**")
        for t in trade:
            lines.append(f"- {t}")
    lines.append("\n" + (rec.get("disclaimer") or ""))
    lines.append("Anh/chị muốn em so sánh kỹ 2 mẫu nào, hoặc để lại SĐT để tư vấn viên gọi lại ạ?")
    return "\n".join(lines)


def format_comparison(cmp: dict[str, Any]) -> str:
    if not cmp.get("ok"):
        return (
            str(cmp.get("error") or "Cần ít nhất 2 sản phẩm hợp lệ để so sánh.")
            + " Anh/chị cho em mã SKU, hoặc để em gợi ý top 3 rồi so sánh giúp mình nhé."
        )
    lines = ["Em so sánh nhanh các sản phẩm anh/chị chọn:\n"]
    for it in cmp.get("items", []):
        extra = []
        if it.get("rating"):
            extra.append(f"{it['rating']}★")
        if it.get("sold"):
            extra.append(f"đã bán {it.get('sold_display') or it['sold']}")
        tail = (" · " + " · ".join(extra)) if extra else ""
        lines.append(f"- **{it['name']}** (`{it['sku']}`) — {it['price_display']}{tail}")
    trade = cmp.get("tradeoffs") or []
    if trade:
        lines.append("\n**Khác biệt chính (trade-off):**")
        for t in trade:
            lines.append(f"- {t}")
    lines.append("\nAnh/chị nghiêng về tiêu chí nào (giá / pin / hiệu năng / thương hiệu) để em chốt giúp ạ?")
    return "\n".join(lines)
