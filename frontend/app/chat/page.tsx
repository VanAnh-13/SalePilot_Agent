"use client";

import { useEffect, useRef, useState } from "react";
import { DecisionEvidence } from "@/components/DecisionEvidence";
import { Markdown } from "@/components/Markdown";
import { IconAlert, IconBot, IconSend, IconUser } from "@/components/Icons";
import { chatOnce, type DecisionContract, type TraceStep } from "@/lib/api";

type Msg = { id: string; role: "user" | "assistant"; content: string };

const LS_ID = "salepilot_external_id";
const LS_MSGS = "salepilot_msgs";

const GREETING: Msg = {
  id: "greeting",
  role: "assistant",
  content:
    "Chào bạn! Em là **SalePilot-R** — hệ hỗ trợ quyết định điện máy theo nhu cầu thật " +
    "(tủ lạnh, máy lạnh, máy giặt, đồng hồ thông minh, máy tính bảng, PC, màn hình…).\n\n" +
    "Em sẽ kiểm tra ràng buộc và chỉ đề xuất khi có đủ bằng chứng từ catalog. Bạn đang cần sản phẩm gì, ngân sách khoảng bao nhiêu ạ?",
};

const CHIPS = [
  "Gia đình 4 người, dưới 15 triệu, cần tủ lạnh tiết kiệm điện",
  "Cần máy lạnh cho phòng 20m2, tầm 12 triệu, chạy êm",
  "Nhà 5 người cần máy giặt cửa trước 9kg dưới 15 triệu có sấy",
  "Đồng hồ thông minh dưới 3 triệu, nghe gọi, theo dõi sức khỏe",
  "Máy tính bảng dưới 8 triệu, pin trâu, có lắp sim",
];

function agentClass(name: string) {
  const n = name.toLowerCase();
  if (["lead", "catalog", "knowledge", "crm", "order", "escalation"].includes(n)) return n;
  return "plain";
}

export default function ChatPage() {
  const [externalId, setExternalId] = useState("");
  const [input, setInput] = useState("");
  const [msgs, setMsgs] = useState<Msg[]>([GREETING]);
  const [trace, setTrace] = useState<TraceStep[]>([]);
  const [agents, setAgents] = useState<string[]>([]);
  const [memoryHit, setMemoryHit] = useState("");
  const [runId, setRunId] = useState("");
  const [decision, setDecision] = useState<DecisionContract | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  const logRef = useRef<HTMLDivElement>(null);

  // Restore the session + chat history from localStorage so navigating to the
  // dashboard and back (or refreshing) keeps the conversation.
  useEffect(() => {
    let id = "";
    try {
      id = localStorage.getItem(LS_ID) || "";
    } catch {}
    if (!id) {
      id = `web-${crypto.randomUUID()}`;
      try {
        localStorage.setItem(LS_ID, id);
      } catch {}
    }
    setExternalId(id);
    try {
      const raw = localStorage.getItem(LS_MSGS);
      const parsed = raw ? (JSON.parse(raw) as Msg[]) : null;
      // Older saved histories have no id — backfill so list keys stay stable.
      if (Array.isArray(parsed) && parsed.length)
        setMsgs(parsed.map((m, i) => ({ ...m, id: m.id || `restored-${i}` })));
    } catch {}
    setLoaded(true);
  }, []);

  // Persist the chat history whenever it changes (only after the initial load,
  // so we never overwrite saved history with the default greeting).
  useEffect(() => {
    if (!loaded) return;
    try {
      localStorage.setItem(LS_MSGS, JSON.stringify(msgs));
    } catch {}
  }, [msgs, loaded]);

  // Keep the conversation scrolled to the latest message.
  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [msgs, loading]);

  function newSession() {
    const id = `web-${crypto.randomUUID()}`;
    try {
      localStorage.setItem(LS_ID, id);
      localStorage.removeItem(LS_MSGS);
    } catch {}
    setExternalId(id);
    setMsgs([GREETING]);
    setTrace([]);
    setAgents([]);
    setMemoryHit("");
    setRunId("");
    setDecision(null);
    setError("");
  }

  async function send(textIn?: string) {
    const text = (textIn ?? input).trim();
    if (!text || loading || !externalId) return;
    setInput("");
    setError("");
    setDecision(null);
      setMsgs((m) => [...m, { id: crypto.randomUUID(), role: "user", content: text }]);
    setLoading(true);
    try {
      const res = await chatOnce(text, externalId);
      setMsgs((m) => [...m, { id: crypto.randomUUID(), role: "assistant", content: res.reply }]);
      setTrace(res.trace || []);
      setAgents(res.used_agents || []);
      setMemoryHit(res.memory_summary || "");
      setRunId(res.run_id || "");
      setDecision(res.decision || null);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      setMsgs((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "Lỗi gọi API. Kiểm tra kết nối backend và CORS.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="chat-shell">
      <section className="card chat-panel">
        <div className="chat-header">
          <div className="who">
            <span className="assistant-avatar" aria-hidden>
              <IconBot width={21} height={21} />
            </span>
            <div>
              <div className="title">Hỗ trợ quyết định điện máy</div>
              <div className="status">
                <span className="live" /> Trực tuyến · {externalId || "đang tạo phiên…"}
              </div>
            </div>
          </div>
          <button
            type="button"
            className="btn ghost sm"
            onClick={newSession}
            disabled={loading}
            title="Xoá lịch sử và bắt đầu phiên mới"
          >
            Phiên mới
          </button>
        </div>

        <div className="chips">
          {CHIPS.map((c) => (
            <button
              key={c}
              type="button"
              className="chip"
              onClick={() => send(c)}
              disabled={loading || !externalId}
              title={c}
            >
              {c.length > 46 ? c.slice(0, 44) + "…" : c}
            </button>
          ))}
        </div>

        <div className="chat-log" ref={logRef}>
          {msgs.map((m) => (
            <div key={m.id} className={`msg ${m.role === "user" ? "user" : "bot"}`}>
              <span className="msg-avatar" aria-hidden>
                {m.role === "user" ? <IconUser width={16} height={16} /> : <IconBot width={16} height={16} />}
              </span>
              <div className="bubble">
                {m.role === "assistant" ? <Markdown text={m.content} /> : m.content}
              </div>
            </div>
          ))}
          {loading && (
            <div className="msg bot">
              <span className="msg-avatar" aria-hidden>
                <IconBot width={16} height={16} />
              </span>
              <div className="bubble">
                <span className="typing">
                  <span />
                  <span />
                  <span />
                </span>
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="error-note">
            <IconAlert width={16} height={16} />
            {error}
          </div>
        )}

        <div className="composer">
          <input
            className="input"
            name="message"
            value={input}
            placeholder="Mô tả nhu cầu bằng tiếng Việt…"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            disabled={!externalId}
          />
          <button className="btn" onClick={() => send()} disabled={loading || !externalId}>
            Gửi <IconSend width={16} height={16} />
          </button>
        </div>
      </section>

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
            <div style={{ marginTop: 4 }}>{memoryHit.slice(0, 160)}</div>
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
    </main>
  );
}
