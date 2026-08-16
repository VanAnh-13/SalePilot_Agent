import Link from "next/link";
import {
  IconHash,
  IconLayers,
  IconScale,
  IconSearchCheck,
  IconShield,
  IconSparkle,
  IconTarget,
} from "@/components/Icons";

const FEATURES = [
  {
    icon: IconTarget,
    color: "blue",
    title: "Ràng buộc trước, xếp hạng sau",
    desc: "Trích xuất ngân sách, kích thước và nhu cầu theo ngành; thiếu dữ liệu quan trọng thì hỏi lại hoặc từ chối đề xuất.",
  },
  {
    icon: IconScale,
    color: "purple",
    title: "Top 3 kèm trade-off",
    desc: "Xếp hạng ứng viên đã qua ràng buộc cứng và nêu rõ đánh đổi để hỗ trợ quyết định, không thay người dùng quyết định.",
  },
  {
    icon: IconSearchCheck,
    color: "green",
    title: "Bằng chứng kiểm tra được",
    desc: "Mỗi đề xuất gắn với SKU, dòng nguồn, trạng thái ràng buộc, catalog hash và decision hash.",
  },
  {
    icon: IconShield,
    color: "amber",
    title: "Fail-closed khi thiếu dữ liệu",
    desc: "Không suy đoán tồn kho và không coi thông số còn thiếu là đã thỏa ràng buộc cứng.",
  },
];

const STATS = [
  { icon: IconShield, color: "amber", v: "Fail-closed", l: "Thông số thiếu không được mặc định là thỏa ràng buộc cứng" },
  { icon: IconLayers, color: "purple", v: "Top 3", l: "Đề xuất kèm trade-off rõ ràng cho mỗi nhu cầu" },
  { icon: IconHash, color: "green", v: "SHA-256", l: "Catalog và quyết định có mã hash để truy vết và tái lập" },
];

export default function HomePage() {
  return (
    <main className="stack">
      <section className="hero">
        <div className="card">
          <span className="hero-eyebrow">
            <IconSparkle width={14} height={14} /> RIVF 2026 Track 2 candidate · AI Applications · Research prototype
          </span>
          <h1 className="hero-title">
            Hỗ trợ quyết định bán lẻ <span className="grad">có bằng chứng</span>
          </h1>
          <p className="hero-lead">
            SalePilot-R là hệ thống constraint-first cho tư vấn điện máy bằng tiếng Việt:
            nhận diện nhu cầu, lọc ràng buộc cứng, đề xuất top 3 và xuất provenance để từng
            quyết định có thể kiểm tra lại.
          </p>
          <div className="cta-row">
            <Link className="btn" href="/chat">
              Bắt đầu tư vấn →
            </Link>
            <Link className="btn ghost" href="/dashboard">
              Xem Dashboard
            </Link>
          </div>
          <div className="hero-try">
            <b>Thử ngay</b>
            “Gia đình 4 người, dưới 15 triệu, cần tủ lạnh inverter, ngang tối đa 70 cm”
          </div>
        </div>

        <div className="hero-panel">
          {FEATURES.map((f) => (
            <div key={f.title} className="feature card-hover">
              <div className={`icon-badge md ${f.color}`} aria-hidden>
                <f.icon />
              </div>
              <div>
                <h3>{f.title}</h3>
                <p>{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="showcase">
        <div>
          <span className="section-eyebrow">
            <IconSearchCheck width={14} height={14} /> Bằng chứng, không phải lời hứa
          </span>
          <h2 className="section-title">Mỗi đề xuất đi kèm bằng chứng có thể kiểm tra lại</h2>
          <p className="section-lead">
            Dưới đây là định dạng thẻ bằng chứng xuất hiện sau mỗi lượt tư vấn trong trang Chat.
          </p>
          <div className="showcase-points">
            <div className="showcase-point">
              <IconShield width={16} height={16} />
              <span>Ràng buộc cứng được kiểm tra theo từng sản phẩm, không suy đoán khi thiếu dữ liệu.</span>
            </div>
            <div className="showcase-point">
              <IconHash width={16} height={16} />
              <span>Catalog hash và decision hash cho phép tái lập và đối chiếu độc lập.</span>
            </div>
            <div className="showcase-point">
              <IconLayers width={16} height={16} />
              <span>Nguồn dữ liệu (dòng SKU) đi kèm để không lấy lời giải thích do mô hình sinh làm bằng chứng.</span>
            </div>
          </div>
        </div>

        <div className="showcase-visual">
          <div className="card showcase-card">
            {/* Illustration label — not real data */}
            <div style={{ fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--muted)", marginBottom: "0.5rem", opacity: 0.7 }}>
              Dạng minh hoạ · Không phải dữ liệu thật
            </div>
            <div className="decision-evidence">
              <div className="decision-state success">
                <span className="decision-state-dot" aria-hidden />
                <div>
                  <b>Có đề xuất kèm bằng chứng</b>
                  <span>Ví dụ: Tủ lạnh</span>
                </div>
              </div>

              <div className="decision-meta">
                <span className="badge plain">decision-v1</span>
                <span className="badge plain">catalog: postgres</span>
                <span className="badge plain">13.716 SKU</span>
              </div>

              <div className="decision-products">
                <article className="decision-product">
                  <div className="decision-product-head">
                    <span className="decision-rank">#1</span>
                    <div>
                      <h3>Tủ lạnh Inverter — tên sản phẩm thực tế</h3>
                      <div className="decision-price">giá thực tế ₫</div>
                    </div>
                  </div>
                  <p className="decision-why">Lý do từ dữ liệu: đạt ngân sách, kích thước khớp, tiết kiệm điện.</p>
                  <div className="constraint-chips">
                    <span className="constraint-pill matched">Đạt · Ngân sách</span>
                    <span className="constraint-pill matched">Đạt · Chiều ngang tối đa</span>
                    <span className="constraint-pill unknown">Chưa rõ · Độ ồn</span>
                  </div>
                  <div className="decision-provenance">
                    <span>SKU ████</span>
                    <span>dòng ████</span>
                    <span>hash ████…████</span>
                  </div>
                </article>
              </div>

              <div className="decision-hashes">
                <div>
                  <span>Decision hash</span>
                  <code>████…████</code>
                </div>
                <div>
                  <span>Catalog hash</span>
                  <code>████…████</code>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>


      <section className="stat-strip">
        {STATS.map((s) => (
          <div key={s.v} className="card card-hover row" style={{ alignItems: "flex-start", gap: 14 }}>
            <div className={`icon-badge sm ${s.color}`} aria-hidden>
              <s.icon width={17} height={17} />
            </div>
            <div>
              <div className="v">
                <span className="grad">{s.v}</span>
              </div>
              <div className="l">{s.l}</div>
            </div>
          </div>
        ))}
      </section>
    </main>
  );
}
