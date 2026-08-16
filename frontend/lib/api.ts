// Same default as the server-side admin proxy (app/api/admin/route.ts):
// set NEXT_PUBLIC_API_URL for deployments; without it both the chat client
// and the admin proxy target the local dev backend.
export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export type TraceStep = {
  agent: string;
  event: string;
  detail?: string;
};

export type DecisionConstraint = {
  key: string;
  hardness?: string;
  missing_policy?: string;
  expected?: unknown;
  actual?: unknown;
  status?: "matched" | "violated" | "unknown" | string;
};

export type DecisionItem = {
  sku?: string | number | null;
  name?: string | null;
  price_vnd?: number | null;
  why?: string | null;
  constraints?: DecisionConstraint[];
  provenance?: {
    source?: string | null;
    source_row?: string | number | null;
    catalog_backend?: string | null;
    catalog_hash?: string | null;
  };
};

export type DecisionContract = {
  schema_version?: string;
  ok?: boolean;
  need_more?: boolean;
  missing_slots?: string[];
  ask?: string[];
  category?: string | null;
  category_display?: string | null;
  top3?: DecisionItem[];
  disclaimer?: string | null;
  decision_hash?: string | null;
  source?: {
    catalog_backend?: string | null;
    catalog_hash?: string | null;
    catalog_products?: number | null;
    label?: string | null;
  };
};

export type ChatDone = {
  reply: string;
  used_agents?: string[];
  used_tools?: string[];
  trace?: TraceStep[];
  needs_human?: boolean;
  lead_id?: number | null;
  conversation_id?: number | null;
  run_id?: string | null;
  memory?: Record<string, unknown> | null;
  memory_summary?: string | null;
  active_skills?: string[];
  decision?: DecisionContract | null;
};

export async function chatOnce(message: string, externalId: string) {
  const res = await fetch(`${API_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      external_id: externalId,
      customer_name: "Khách web",
      channel: "web",
    }),
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as ChatDone;
}

// --- Admin endpoints routed through server-side BFF ---
// ADMIN_API_KEY stays on the server; the browser never sees it.
async function adminFetch<T>(path: string): Promise<T> {
  const res = await fetch(`/api/admin?path=${encodeURIComponent(path)}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as T;
}

export type Lead = {
  id: number;
  name?: string | null;
  phone?: string | null;
  channel?: string | null;
  interest?: string | null;
  budget_vnd?: number | null;
  status?: string | null;
  score?: number | null;
};

export type Conversation = {
  id: number;
  channel: string;
  external_id: string;
  customer_name?: string | null;
  lead_id?: number | null;
  status?: string | null;
  needs_human?: boolean | null;
  summary?: string | null;
};

export type ZaloOutboxItem = {
  id: number;
  user_id: string;
  direction: string;
  content: string;
  status?: string | null;
  created_at?: string | null;
};

export type MemoryProfile = {
  phone?: string | null;
  interests?: string[];
};

export type MemoryItem = {
  id: number;
  channel: string;
  external_id: string;
  profile: MemoryProfile;
  summary?: string | null;
  updated_at?: string | null;
};

export type Job = {
  id: number;
  status?: string | null;
  result?: string | null;
  payload?: string | null;
};

export type AgentRun = {
  run_id: string;
  channel?: string;
  external_id?: string;
  user_text: string;
  reply: string;
  trace?: TraceStep[];
  agents?: string[];
  tools?: string[];
  created_at?: string | null;
};

export async function fetchLeads(): Promise<Lead[]> {
  return adminFetch<Lead[]>("/leads");
}

export async function fetchConversations(): Promise<Conversation[]> {
  return adminFetch<Conversation[]>("/leads/conversations");
}

async function adminPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`/api/admin?path=${encodeURIComponent(path)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()) as T;
}

type ConversationAction = { ok: boolean; conversation_id: number; status: string };

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

export async function fetchZaloOutbox(): Promise<ZaloOutboxItem[]> {
  return adminFetch<ZaloOutboxItem[]>("/outbox/zalo");
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
