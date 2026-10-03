import { DecisionEvidence } from "./DecisionEvidence";
import { agentClass, MEMORY_PREVIEW_CAP, type Msg } from "@/lib/chatConfig";

export function ChatEvidence({ message, loading }: { message: Msg | null; loading: boolean }) {
  const trace = message?.meta?.trace ?? [];
  const agents = message?.meta?.used_agents ?? [];
  const memoryHit = message?.meta?.memory_summary ?? "";
  const runId = message?.meta?.run_id ?? "";
  const decision = message?.meta?.decision ?? null;

  return (
    <section className="card trace-panel">
      <h2 className="card-title">
        <span className="dot" /> Bằng chứng quyết định
      </h2>
      <p className="muted panel-intro">
        Ràng buộc, nguồn SKU và hash giúp kiểm tra lại từng đề xuất.
      </p>

      <DecisionEvidence decision={decision} loading={loading} />

      <div className="panel-divider" />

      <h2 className="card-title">
        <span className="dot" /> Agent Trace
      </h2>
      <p className="muted panel-intro">
        Luồng xử lý hỗ trợ debug; không được dùng thay cho bằng chứng quyết định.
      </p>

      {memoryHit && (
        <div className="memory-note" style={{ marginTop: 12 }}>
          <b>Memory</b>
          <div style={{ marginTop: 4 }}>{memoryHit.slice(0, MEMORY_PREVIEW_CAP)}</div>
        </div>
      )}

      <div className="agent-badges">
        {agents.length ? (
          agents.map((a) => (
            <span key={a} className={`badge ${agentClass(a)}`}>
              {a}
            </span>
          ))
        ) : (
          <span className="muted">Chưa có lượt chạy</span>
        )}
      </div>

      {runId && (
        <p className="muted" style={{ marginBottom: 10 }}>
          run: <code className="md-code">{runId}</code>
        </p>
      )}

      <div className="trace-list">
        {trace.length ? (
          trace.map((t, i) => (
            <div key={i} className="trace-item">
              <div className="meta">
                <span className={`badge ${agentClass(t.agent)}`}>{t.agent}</span>
                <span>· {t.event}</span>
              </div>
              <div className="detail">{t.detail || "—"}</div>
            </div>
          ))
        ) : (
          <div className="empty">Trace hiển thị sau mỗi câu trả lời.</div>
        )}
      </div>
    </section>
  );
}
