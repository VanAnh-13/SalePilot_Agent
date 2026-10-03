"use client";

import { useEffect, useRef } from "react";
import { ChatEvidence } from "@/components/ChatEvidence";
import { Markdown } from "@/components/Markdown";
import { IconAlert, IconBot, IconSend, IconUser } from "@/components/Icons";
import { CHIPS } from "@/lib/chatConfig";
import { useChatSession } from "@/lib/useChatSession";
import { downloadMarkdown } from "@/lib/markdownExport";

export default function ChatPage() {
  const {
    externalId, input, setInput, msgs, selectedEvidence, setSelectedMsgId,
    loading, error, streamStarted, newSession, send,
  } = useChatSession();
  const logRef = useRef<HTMLDivElement>(null);

  // Keep the conversation scrolled to the latest message.
  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [msgs, loading]);

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

      <ChatEvidence message={selectedEvidence} loading={loading} />
    </main>
  );
}
