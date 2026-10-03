"use client";

import { useEffect, useState } from "react";
import { chatOnce, streamChat } from "./client";
import {
  CHAT_ERROR_MESSAGE, GREETING, LS_ID, LS_MSGS, WEB_ID_PREFIX,
  type Msg, type MsgMeta,
} from "./chatConfig";

function generateId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

export function useChatSession() {
  const [externalId, setExternalId] = useState("");
  const [input, setInput] = useState("");
  const [msgs, setMsgs] = useState<Msg[]>([GREETING]);
  const [selectedMsgId, setSelectedMsgId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [streamStarted, setStreamStarted] = useState(false);

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

  // Evidence follows the SELECTED assistant message (default: latest with
  // evidence) instead of a single overwritten panel — survives refresh.
  const evidenceMsgs = msgs.filter((m) => m.role === "assistant" && m.meta);
  const selectedEvidence =
    evidenceMsgs.find((m) => m.id === selectedMsgId) ??
    evidenceMsgs[evidenceMsgs.length - 1] ??
    null;

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

  return {
    externalId, input, setInput, msgs, selectedEvidence, setSelectedMsgId,
    loading, error, streamStarted, newSession, send,
  };
}
