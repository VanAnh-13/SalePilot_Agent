export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export type TraceStep = {
  agent: string;
  event: string;
  detail?: string;
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

export async function fetchLeads() {
  const res = await fetch(`${API_URL}/leads`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchConversations() {
  const res = await fetch(`${API_URL}/leads/conversations`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchZaloOutbox() {
  const res = await fetch(`${API_URL}/outbox/zalo`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchMemory() {
  const res = await fetch(`${API_URL}/memory`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchJobs() {
  const res = await fetch(`${API_URL}/jobs`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchLatestRun() {
  const res = await fetch(`${API_URL}/runs/latest`, { cache: "no-store" });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
