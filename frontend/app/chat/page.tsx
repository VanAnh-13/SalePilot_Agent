"use client";

import { useEffect, useState } from "react";
import { chatOnce, type TraceStep } from "@/lib/api";

type Msg = { role: "user" | "assistant"; content: string };

const CHIPS = [
  "Gia đình 4 người, dưới 15 triệu, cần tủ lạnh tiết kiệm điện",
  "Nhà 5 người cần tủ Multi Door khoảng 500 lít, ngân sách 25 triệu",
  "Chỗ đặt ngang tối đa 70 cm, nhà 4 người, dưới 15 triệu",
  "Bảng có biết tủ lạnh còn hàng không?",
  "So sánh tủ Side by Side có lấy nước ngoài cho hơn 5 người",
];

function agentClass(name: string) {
  const n = name.toLowerCase();
  if (["lead", "catalog", "knowledge", "crm", "order", "escalation"].includes(n)) return n;
  return "";
}

export default function ChatPage() {
  const [externalId, setExternalId] = useState("");
  const [input, setInput] = useState("");
  const [msgs, setMsgs] = useState<Msg[]>([
    {
      role: "assistant",
      content:
        "Chào bạn! Em là SalePilot — tư vấn tủ lạnh theo nhu cầu thật từ bảng sản phẩm. " +
        "Cho em biết nhà có bao nhiêu người, ngân sách và kích thước chỗ đặt nhé?",
    },
  ]);
  const [trace, setTrace] = useState<TraceStep[]>([]);
  const [agents, setAgents] = useState<string[]>([]);
  const [memoryHit, setMemoryHit] = useState("");
  const [runId, setRunId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setExternalId(`web-${crypto.randomUUID()}`);
  }, []);

  async function send(textIn?: string) {
    const text = (textIn ?? input).trim();
    if (!text || loading || !externalId) return;
    setInput("");
    setError("");
    setMsgs((m) => [...m, { role: "user", content: text }]);
    setLoading(true);
    try {
      const res = await chatOnce(text, externalId);
      setMsgs((m) => [...m, { role: "assistant", content: res.reply }]);
      setTrace(res.trace || []);
      setAgents(res.used_agents || []);
      setMemoryHit(res.memory_summary || "");
      setRunId(res.run_id || "");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      setMsgs((m) => [
        ...m,
        { role: "assistant", content: "Lỗi gọi API. Kiểm tra backend :8000 và CORS." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid2">
      <section className="card">
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
          <strong>Tư vấn tủ lạnh</strong>
          <span className="muted">{externalId || "Đang tạo phiên…"}</span>
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
          {CHIPS.map((c) => (
            <button key={c} type="button" className="btn ghost" style={{ fontSize: 12, padding: "6px 10px" }} onClick={() => send(c)} disabled={loading || !externalId}>
              {c.length > 42 ? c.slice(0, 40) + "…" : c}
            </button>
          ))}
        </div>
        <div className="chat-log">
          {msgs.map((m, i) => (
            <div key={i} className={`bubble ${m.role === "user" ? "user" : "bot"}`}>
              {m.content}
            </div>
          ))}
          {loading && <div className="muted">Agent đang tư vấn…</div>}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            className="input"
            name="message"
            value={input}
            placeholder="Mô tả nhu cầu bằng tiếng Việt…"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
          />
          <button className="btn" onClick={() => send()} disabled={loading || !externalId}>
            Gửi
          </button>
        </div>
        {error && (
          <p className="muted" style={{ color: "var(--danger)", marginTop: 8 }}>
            {error}
          </p>
        )}
      </section>

      <section className="card">
        <strong>Agent Trace</strong>
        <p className="muted">Lead → catalog/knowledge · anti-hallucination via tools</p>
        {memoryHit && (
          <p className="badge" style={{ marginBottom: 8 }}>
            memory: {memoryHit.slice(0, 120)}
          </p>
        )}
        {runId && <p className="muted">run: {runId}</p>}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6, margin: "10px 0" }}>
          {agents.map((a) => (
            <span key={a} className={`badge ${agentClass(a)}`}>
              {a}
            </span>
          ))}
          {!agents.length && <span className="muted">Chưa có lượt chạy</span>}
        </div>
        <div className="trace-list">
          {trace.map((t, i) => (
            <div key={i} className="trace-item">
              <div className="meta">
                <span className={`badge ${agentClass(t.agent)}`}>{t.agent}</span> · {t.event}
              </div>
              <div>{t.detail || "—"}</div>
            </div>
          ))}
          {!trace.length && <div className="muted">Trace hiện sau mỗi câu trả lời.</div>}
        </div>
      </section>
    </main>
  );
}
