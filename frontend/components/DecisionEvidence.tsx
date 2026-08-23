"use client";

import type { DecisionContract } from "@/lib/api";
import {
  constraintLabel,
  decisionStatusText,
  decisionTone,
  formatMoney,
  formatValue,
  KEY_LABELS,
  shortHash,
  sourceRow,
  statusLabel,
} from "@/lib/decision";

export function DecisionEvidence({
  decision,
  loading = false,
}: {
  decision: DecisionContract | null;
  loading?: boolean;
}) {
  if (loading) {
    return <div className="empty decision-empty">Đang kiểm tra ràng buộc và nguồn dữ liệu…</div>;
  }

  if (!decision) {
    return (
      <div className="empty decision-empty">
        Sau lượt tư vấn, bảng này sẽ hiện ràng buộc, nguồn SKU và mã kiểm chứng quyết định.
      </div>
    );
  }

  const items = (decision.top3 || []).slice(0, 3);
  const tone = decisionTone(decision);
  const status = decisionStatusText(decision);

  return (
    <div className="decision-evidence">
      <div className={`decision-state ${tone}`}>
        <span className="decision-state-dot" aria-hidden />
        <div>
          <b>{status}</b>
          <span>
            {decision.category_display || decision.category || "Chưa xác định ngành hàng"}
          </span>
        </div>
      </div>

      <div className="decision-meta" aria-label="Metadata quyết định">
        <span className="badge plain">{decision.schema_version || "decision-v1"}</span>
        <span className="badge plain">
          catalog: {decision.source?.catalog_backend || "unknown"}
        </span>
        {decision.source?.catalog_products != null && (
          <span className="badge plain">
            {new Intl.NumberFormat("vi-VN").format(decision.source.catalog_products)} SKU
          </span>
        )}
      </div>

      {decision.need_more && (
        <div className="decision-followup">
          <b>Thông tin còn thiếu</b>
          <div className="constraint-chips">
            {(decision.missing_slots || []).map((slot) => (
              <span key={slot} className="constraint-pill unknown">
                {(slot && KEY_LABELS[slot]) || (typeof slot === "string" ? slot.replaceAll("_", " ") : String(slot))}
              </span>
            ))}
          </div>
          {(decision.ask || []).map((question) => (
            <p key={question}>{question}</p>
          ))}
        </div>
      )}

      {!!items.length && (
        <div className="decision-products">
          {items.map((item, index) => (
            <article className="decision-product" key={`${item.sku || item.name || "item"}-${index}`}>
              <div className="decision-product-head">
                <span className="decision-rank">#{index + 1}</span>
                <div>
                  <h3>{item.name || item.sku || "Sản phẩm"}</h3>
                  <div className="decision-price">{formatMoney(item.price_vnd)}</div>
                </div>
              </div>

              {item.why && <p className="decision-why">{item.why}</p>}

              <div className="constraint-chips">
                {(item?.constraints || []).map((constraint, constraintIndex) => (
                  <span
                    className={`constraint-pill ${constraint.status || "unknown"}`}
                    key={`${constraint.key}-${constraintIndex}`}
                    title={`Kỳ vọng: ${formatValue(constraint.key, constraint.expected)} · Thực tế: ${formatValue(
                      constraint.key,
                      constraint.actual,
                    )}`}
                  >
                    {statusLabel(constraint.status)} · {constraintLabel(constraint)}
                  </span>
                ))}
              </div>

              <div className="decision-provenance">
                <span>SKU {item.sku || "unknown"}</span>
                <span>{sourceRow(item)}</span>
                <span title={item.provenance?.catalog_hash || undefined}>
                  hash {shortHash(item.provenance?.catalog_hash)}
                </span>
              </div>
            </article>
          ))}
        </div>
      )}

      <div className="decision-hashes">
        <div>
          <span>Decision hash</span>
          <code title={decision.decision_hash || undefined}>{shortHash(decision.decision_hash)}</code>
        </div>
        <div>
          <span>Catalog hash</span>
          <code title={decision.source?.catalog_hash || undefined}>
            {shortHash(decision.source?.catalog_hash)}
          </code>
        </div>
      </div>

      {decision.disclaimer && <p className="decision-disclaimer">{decision.disclaimer}</p>}
    </div>
  );
}
