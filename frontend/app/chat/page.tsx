"use client";

import { useEffect, useRef, useState } from "react";
import { DecisionEvidence } from "@/components/DecisionEvidence";
import { Markdown } from "@/components/Markdown";
import { IconAlert, IconBot, IconSend, IconUser } from "@/components/Icons";
import { chatOnce, streamChat } from "@/lib/api";
import {
  agentClass,
  CHAT_ERROR_MESSAGE,
  CHIPS,
  GREETING,
  LS_ID,
  LS_MSGS,
  MEMORY_PREVIEW_CAP,
  WEB_ID_PREFIX,
  type Msg,
  type MsgMeta,
} from "@/lib/chatConfig";
import { downloadMarkdown } from "@/lib/markdownExport";

function generateId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

export default function ChatPage() {
  const [externalId, setExternalId] = useState("");
  const [input, setInput] = useState("");
  const [msgs, setMsgs] = useState<Msg[]>([GREETING]);
  const [selectedMsgId, setSelectedMsgId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [streamStarted, setStreamStarted] = useState(false);

  const logRef = useRef<HTMLDivElement>(null);

  // Restore the session + chat history from localStorage so navigating to the
  // dashboard and back (or refreshing) keeps the conversation.
  useEffect(() => {
    let id = "";
    try {
      id = localStorage.getItem(LS_ID) || "";
    } catch {}
    if (!id) {
      id = WEB_ID_PREFIX + generateId();
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
    const timer = setTimeout(() => {
      try {
        localStorage.setItem(LS_MSGS, JSON.stringify(msgs));
      } catch {}
    }, 500);
    return () => clearTimeout(timer);
  }, [msgs, loaded]);

  // Keep the conversation scrolled to the latest message.
  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [msgs, loading]);

  // Evidence follows the SELECTED assistant message (default: latest with
  // evidence) instead of a single overwritten panel — survives refresh.
  const evidenceMsgs = msgs.filter((m) => m.role === "assistant" && m.meta);
  const selectedEvidence =
    evidenceMsgs.find((m) => m.id === selectedMsgId) ??
    evidenceMsgs[evidenceMsgs.length - 1] ??
    null;
  const trace = selectedEvidence?.meta?.trace ?? [];
  const agents = selectedEvidence?.meta?.used_agents ?? [];
  const memoryHit = selectedEvidence?.meta?.memory_summary ?? "";
  const runId = selectedEvidence?.meta?.run_id ?? "";
  const decision = selectedEvidence?.meta?.decision ?? null;

  function newSession() {
    const id = WEB_ID_PREFIX + generateId();
    try {
      localStorage.setItem(LS_ID, id);
      localStorage.removeItem(LS_MSGS);
    } catch {}
    setExternalId(id);
    setMsgs([GREETING]);
    setSelectedMsgId(null);
    setError("");
  }

  async function send(textIn?: string) {
    const text = (textIn ?? input).trim();
    if (!text || loading || !externalId) return;
    setInput("");
    setError("");
    setSelectedMsgId(null);
    setStreamStarted(false);
    setMsgs((m) => [...m, { id: generateId(), role: "user", content: text }]);
    setLoading(true);

    // Live assistant bubble that grows as tokens stream in.
    const replyId = generateId();
    let received = false;
    let streamed = "";
    let bubbleCreated = false;
    let liveMemory = "";
    const appendAssistant = (content: string, meta?: MsgMeta) =>
      setMsgs((m) => [...m, { id: replyId, role: "assistant", content, meta }]);
    const updateAssistant = (content: string) =>
      setMsgs((m) => m.map((msg) => (msg.id === replyId ? { ...msg, content } : msg)));

    // Evidence attaches to THIS message (not a global panel), so each turn
    // keeps its own trace/decision and refreshes restore it.
    const applyDone = (done: MsgMeta) => {
      const meta: MsgMeta = {
        trace: done.trace || [],
        used_agents: done.used_agents || [],
        memory_summary: done.memory_summary || liveMemory || "",
        run_id: done.run_id || "",
        decision: done.decision || null,
      };
      setMsgs((m) => m.map((msg) => (msg.id === replyId ? { ...msg, meta } : msg)));
    };

    try {
      const done = await streamChat(text, externalId, (ev) => {
        received = true;
        if (ev.type === "token") {
          streamed += ev.content;
          if (bubbleCreated) updateAssistant(streamed);
          else {
            appendAssistant(streamed);
            bubbleCreated = true;
          }
          setStreamStarted(true);
        } else if (ev.type === "memory") {
          liveMemory = ev.summary;
        }
      });
      if (!streamed) appendAssistant(done.reply);
      applyDone(done);
    } catch (e: unknown) {
      // Streaming unavailable before anything arrived → batch POST fallback.
      if (!received) {
        try {
          const res = await chatOnce(text, externalId);
          appendAssistant(res.reply);
          applyDone(res);
          return;
        } catch {
          /* fall through to the error bubble */
        }
      } else if (streamed) {
        updateAssistant(streamed + "\n\n_(Mất kết nối giữa chừng — phản hồi có thể chưa đầy đủ)_");
      }
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      if (!streamed) {
        appendAssistant(CHAT_ERROR_MESSAGE);
      }
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
            onClick={() => downloadMarkdown(msgs, externalId)}
            disabled={loading || msgs.length <= 1}
            title="Tải toàn bộ hội thoại kèm bằng chứng ra file Markdown"
          >
            Xuất hội thoại
          </button>
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
            <div
              key={m.id}
              className={`msg ${m.role === "user" ? "user" : "bot"}${
                m.id === selectedEvidence?.id ? " selected" : ""
              }`}
              onClick={() => m.meta && setSelectedMsgId(m.id)}
              title={m.meta ? "Bấm để xem bằng chứng của lượt này" : undefined}
            >
              <span className="msg-avatar" aria-hidden>
                {m.role === "user" ? <IconUser width={16} height={16} /> : <IconBot width={16} height={16} />}
              </span>
              <div className="bubble">
                {m.role === "assistant" ? <Markdown text={m.content} /> : m.content}
              </div>
            </div>
          ))}
          {loading && !streamStarted && (
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
            onKeyDown={(e) => { if (e.key === "Enter" && !e.nativeEvent.isComposing) send(); }}
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
    </main>
  );
}
