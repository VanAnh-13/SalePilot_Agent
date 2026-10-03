import {
  ADMIN_PROXY_PATH,
  API_URL,
  CHAT_PATH,
  CHAT_STREAM_PATH,
  OWNER_TOKEN_KEY,
  chatBody,
} from "./constants";
import type {
  AgentRun,
  ChatDone,
  Conversation,
  ConversationAction,
  Job,
  Lead,
  MemoryItem,
  StreamDone,
  StreamEvent,
} from "./types";

export async function chatOnce(message: string, externalId: string) {
  const res = await fetch(`${API_URL}${CHAT_PATH}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(chatBody(message, externalId)),
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as ChatDone;
}

/**
 * Consume the SSE stream, invoking onEvent per parsed event.
 * Throws before the first event when the endpoint is unreachable so the
 * caller can fall back to the batch POST; mid-stream errors are surfaced
 * after whatever events were already delivered.
 */
export async function streamChat(
  message: string,
  externalId: string,
  onEvent: (ev: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<StreamDone> {
  const res = await fetch(`${API_URL}${CHAT_STREAM_PATH}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(chatBody(message, externalId)),
    signal,
  });
  if (!res.ok || !res.body) throw new Error(await res.text().catch(() => res.statusText));

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let done: StreamDone | null = null;
  let streamError = "";

  for (;;) {
    const { value, done: closed } = await reader.read();
    if (closed) break;
    buffer += decoder.decode(value, { stream: true });
    // SSE frames are separated by a blank line.
    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      for (const line of frame.split("\n")) {
        if (!line.startsWith("data: ")) continue;
        let ev: StreamEvent;
        try {
          ev = JSON.parse(line.slice(6)) as StreamEvent;
        } catch {
          continue; // a malformed frame must not kill the whole stream
        }
        if (ev.type === "error") {
          streamError = (ev as { detail?: string }).detail || "unknown stream error";
        }
        if (ev.type === "done") done = ev as StreamDone;
        onEvent(ev);
      }
    }
  }
  if (!done) {
    throw new Error(streamError ? `Stream error: ${streamError}` : "Stream ended without a done event");
  }
  return done;
}

// --- Admin endpoints routed through server-side BFF ---
// ADMIN_API_KEY stays on the server; the browser never sees it. The browser
// authenticates to the BFF with an owner token (X-Owner-Token) checked against
// the server OWNER_TOKEN — without this the proxy would expose all admin data.
function ownerHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  try {
    const token = localStorage.getItem(OWNER_TOKEN_KEY);
    return token ? { "X-Owner-Token": token } : {};
  } catch {
    return {};
  }
}

async function adminFetch<T>(
  path: string,
  options: { method?: "POST"; headers?: Record<string, string>; body?: string } = {},
): Promise<T> {
  const res = await fetch(
    `${ADMIN_PROXY_PATH}?path=${encodeURIComponent(path)}`,
    { ...options, cache: "no-store", headers: { ...options.headers, ...ownerHeaders() } },
  );
  if (res.status === 401) throw new Error("UNAUTHORIZED");
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as T;
}

async function adminPost<T>(path: string, body: unknown): Promise<T> {
  return adminFetch<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function fetchLeads(): Promise<Lead[]> {
  return adminFetch<Lead[]>("/leads");
}

export async function fetchConversations(): Promise<Conversation[]> {
  return adminFetch<Conversation[]>("/leads/conversations");
}

export function takeoverConversation(conv: Conversation): Promise<ConversationAction> {
  return adminPost<ConversationAction>("/leads/conversations/takeover", {
    channel: conv.channel,
    external_id: conv.external_id,
  });
}

export function resolveConversation(conv: Conversation): Promise<ConversationAction> {
  return adminPost<ConversationAction>("/leads/conversations/resolve", {
    channel: conv.channel,
    external_id: conv.external_id,
  });
}

export async function fetchMemory(): Promise<MemoryItem[]> {
  return adminFetch<MemoryItem[]>("/memory");
}

export async function fetchJobs(): Promise<Job[]> {
  return adminFetch<Job[]>("/jobs");
}

export async function fetchLatestRun(): Promise<AgentRun | null> {
  const payload = await adminFetch<{ run: AgentRun | null }>("/runs/latest");
  return payload.run ?? null;
}
