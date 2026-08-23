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

// --- Streaming (/chat/stream SSE) ---
export type StreamEvent =
  | { type: "memory"; summary: string }
  | (TraceStep & { type: "trace" })
  | { type: "token"; content: string }
  // Terminal mid-stream failure event from /chat/stream; detail is a safe,
  // user-facing message (root cause stays in server logs).
  | { type: "error"; detail?: string }
  | ({ type: "done" } & ChatDone);

export type StreamDone = Extract<StreamEvent, { type: "done" }>;

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

export type ConversationAction = { ok: boolean; conversation_id: number; status: string };

// Status colour tone for dashboard pills (maps to the .status-pill CSS classes).
export type StatusTone = "green" | "amber" | "red" | "blue";
