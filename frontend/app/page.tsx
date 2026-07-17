import Link from "next/link";

export default function HomePage() {
  return (
    <main className="hero">
      <div className="card">
        <span className="badge">VAIC 2026 · Năng suất SME · Điện Máy Xanh</span>
        <h1>SalePilot</h1>
        <p>
          Trợ lý AI <strong>so sánh &amp; tư vấn tủ lạnh theo nhu cầu thật</strong> — hiểu số người,
          ngân sách, dung tích, kiểu tủ và kích thước chỗ đặt, hỏi ngược khi thiếu thông tin, đề
          xuất <strong>top 3</strong> kèm trade-off. Multi-agent: Lead · Catalog · Knowledge · CRM.
          Không bịa giá/tồn — mọi số liệu từ Google Sheet category_code 38.
        </p>
        <div className="cta-row">
          <Link className="btn" href="/chat">
            Bắt đầu tư vấn
          </Link>
          <Link className="btn ghost" href="/dashboard">
            Dashboard
          </Link>
        </div>
        <p className="muted" style={{ marginTop: 16 }}>
          Thử: “Gia đình 4 người, dưới 15 triệu, cần tủ lạnh inverter, ngang tối đa 70 cm”
        </p>
      </div>
    </main>
  );
}
