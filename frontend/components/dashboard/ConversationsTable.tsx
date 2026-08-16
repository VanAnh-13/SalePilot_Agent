import type { Conversation } from "@/lib/api";
import { EmptyRow, statusPillClass } from "./shared";

export function ConversationsTable({
  convs,
  onAction,
  busyId,
}: {
  convs: Conversation[];
  onAction?: (conv: Conversation, action: "takeover" | "resolve") => void;
  busyId?: number | null;
}) {
  return (
    <div className="table-wrap" style={{ marginTop: 14 }}>
      <table className="table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Kênh</th>
            <th>Khách</th>
            <th>Trạng thái</th>
            <th>Cần người?</th>
            {onAction && <th />}
          </tr>
        </thead>
        <tbody>
          {convs.map((c) => (
            <tr key={c.id}>
              <td>{c.id}</td>
              <td>{c.channel}</td>
              <td>{c.customer_name || "—"}</td>
              <td>
                <span className={`pill ${statusPillClass(c.status)}`}>{c.status || "—"}</span>
              </td>
              <td>
                <span className={`pill ${c.needs_human ? "red" : "green"}`}>
                  {c.needs_human ? "Cần" : "Không"}
                </span>
              </td>
              {onAction && (
                <td>
                  {c.status === "escalated" ? (
                    <button
                      type="button"
                      className="btn ghost sm"
                      disabled={busyId === c.id}
                      onClick={() => onAction(c, "resolve")}
                      title="Bot tiếp tục tự trả lời khách này"
                    >
                      {busyId === c.id ? "…" : "Giao lại bot"}
                    </button>
                  ) : (
                    <button
                      type="button"
                      className="btn ghost sm"
                      disabled={busyId === c.id}
                      onClick={() => onAction(c, "takeover")}
                      title="Bot ngừng trả lời, người tiếp nhận"
                    >
                      {busyId === c.id ? "…" : "Người tiếp nhận"}
                    </button>
                  )}
                </td>
              )}
            </tr>
          ))}
          {!convs.length && <EmptyRow colSpan={onAction ? 6 : 5}>Chưa có hội thoại.</EmptyRow>}
        </tbody>
      </table>
    </div>
  );
}
