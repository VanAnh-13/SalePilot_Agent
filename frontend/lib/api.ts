export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "https://optivisionlab.fit-haui.edu.vn";

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
async function adminFetch(path: string) {
  const res = await fetch(`/api/admin?path=${encodeURIComponent(path)}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchLeads() {
  return adminFetch("/leads");
}

export async function fetchConversations() {
  return adminFetch("/leads/conversations");
}

export async function fetchZaloOutbox() {
  return adminFetch("/outbox/zalo");
}

export async function fetchMemory() {
  return adminFetch("/memory");
}

export async function fetchJobs() {
  return adminFetch("/jobs");
}

export async function fetchLatestRun() {
  return adminFetch("/runs/latest");
}
