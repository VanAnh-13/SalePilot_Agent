"use client";

import { useEffect, useState, type ComponentType, type SVGProps } from "react";
import {
  fetchConversations,
  fetchJobs,
  fetchLatestRun,
  fetchLeads,
  fetchMemory,
  resolveConversation,
  takeoverConversation,
  type AgentRun,
  type Conversation,
  type Job,
  type Lead,
  type MemoryItem,
} from "@/lib/api";
import { IconAlert, IconBrain, IconChat, IconClock, IconRefresh, IconUsers } from "@/components/Icons";
import { ConversationsTable } from "@/components/dashboard/ConversationsTable";
import { LeadsTable } from "@/components/dashboard/LeadsTable";
import { statusPillClass } from "@/components/dashboard/shared";
import { OWNER_TOKEN_KEY } from "@/lib/constants";

// Auto-refresh cadence so a finished consultation shows up without a manual reload.
const AUTO_REFRESH_MS = 7000;
// Characters previewed from an agent run's reply before truncation.
const REPLY_PREVIEW_CAP = 400;

type StatTone = "blue" | "green" | "purple" | "amber";
type Stat = {
  icon: ComponentType<SVGProps<SVGSVGElement>>;
  color: StatTone;
  value: number;
  label: string;
};

export default function DashboardPage() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [convs, setConvs] = useState<Conversation[]>([]);
  const [memory, setMemory] = useState<MemoryItem[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [run, setRun] = useState<AgentRun | null>(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [auto, setAuto] = useState(true);
  const [busyConv, setBusyConv] = useState<number | null>(null);

  async function handleConversationAction(conv: Conversation, action: "takeover" | "resolve") {
    setBusyConv(conv.id);
    try {
      if (action === "takeover") await takeoverConversation(conv);
      else await resolveConversation(conv);
      await load(true);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusyConv(null);
    }
  }

  async function load(silent = false) {
    try {
      setErr("");
      if (!silent) setLoading(true);
      const results = await Promise.allSettled([
        fetchLeads(),
        fetchConversations(),
        fetchMemory(),
        fetchJobs(),
        fetchLatestRun(),
      ]);
      const errors: string[] = [];
      const val = <T,>(r: PromiseSettledResult<T>, fallback: T): T => {
        if (r.status === "fulfilled") return r.value;
        errors.push(r.reason instanceof Error ? r.reason.message : String(r.reason));
        return fallback;
      };
      setLeads(val(results[0], []));
      setConvs(val(results[1], []));
      setMemory(val(results[2], []));
      setJobs(val(results[3], []));
      setRun(val(results[4], null));
      setLastUpdated(new Date());
      if (errors.includes("UNAUTHORIZED")) {
        try {
          localStorage.removeItem(OWNER_TOKEN_KEY);
        } catch {}
        setErr("Owner token không hợp lệ hoặc chưa đặt. Tải lại trang để nhập lại (OWNER_TOKEN).");
      } else if (errors.length) {
        setErr(errors.join(" | "));
      }
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      if (!silent) setLoading(false);
    }
  }

  useEffect(() => {
    (async () => {
      // The admin BFF requires an owner token; prompt for it once if missing.
      try {
        if (typeof window !== "undefined" && !localStorage.getItem(OWNER_TOKEN_KEY)) {
          const token = window.prompt("Nhập owner token để xem dashboard:");
          if (token) localStorage.setItem(OWNER_TOKEN_KEY, token);
        }
      } catch {}
      load();
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-refresh so a finished consultation shows up without a manual reload.
  useEffect(() => {
    if (!auto) return;
    const id = setInterval(() => load(true), AUTO_REFRESH_MS);
    return () => clearInterval(id);
  }, [auto]);

  const stats: Stat[] = [
    { icon: IconUsers, color: "blue", value: leads.length, label: "Leads" },
    { icon: IconChat, color: "green", value: convs.length, label: "Cuộc hội thoại" },
    { icon: IconBrain, color: "purple", value: memory.length, label: "Hồ sơ ghi nhớ" },
    { icon: IconClock, color: "amber", value: jobs.length, label: "Jobs đã lên lịch" },
  ];

  return (
    <main className="stack">
      <div className="dash-head">
        <div>
          <h1>Owner dashboard</h1>
          <p className="muted">Leads · memory · jobs · agent runs</p>
        </div>
        <div className="row" style={{ gap: 12 }}>
          {lastUpdated && (
            <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "var(--muted)" }}>
              {auto && <span className="live" />} Cập nhật {lastUpdated.toLocaleTimeString("vi-VN")}
            </span>
          )}
          <label style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer", fontSize: 13, color: "var(--muted)" }}>
            <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} />
            Tự động
          </label>
          <button className="btn ghost sm" onClick={() => load()} disabled={loading}>
            <IconRefresh width={14} height={14} /> {loading ? "Đang tải…" : "Làm mới"}
          </button>
        </div>
      </div>

      {err && (
        <div className="error-note" style={{ margin: 0 }}>
          <IconAlert width={16} height={16} />
          {err}
        </div>
      )}

      <section className="stat-grid">
        {stats.map((s) => (
          <div key={s.label} className="card stat-card card-hover">
            <div className="top">
              <span className="label">{s.label}</span>
              <span className={`icon-badge sm ${s.color}`} aria-hidden>
                <s.icon width={17} height={17} />
              </span>
            </div>
            <div className="value">{s.value}</div>
          </div>
        ))}
      </section>

      <section className="card">
        <h2 className="card-title">
          <span className="dot" /> Leads ({leads.length})
        </h2>
        <LeadsTable leads={leads} />
      </section>

      <div className="grid2">
        <section className="card">
          <h2 className="card-title">
            <span className="dot" /> Customer memory
          </h2>
          <div className="trace-list" style={{ marginTop: 14 }}>
            {memory.map((m) => (
              <div key={m.id} className="trace-item">
                <div className="meta">
                  {m.channel}:{m.external_id}
                </div>
                <div className="detail">
                  {m.profile?.phone && <div>SĐT: {m.profile.phone}</div>}
                  {m.profile?.interests?.length ? (
                    <div>Quan tâm: {m.profile.interests.join(", ")}</div>
                  ) : null}
                  {!m.profile?.phone && !m.profile?.interests?.length && (
                    <span className="muted">{m.summary || "—"}</span>
                  )}
                </div>
              </div>
            ))}
            {!memory.length && <div className="empty">Chưa có memory.</div>}
          </div>
        </section>

        <section className="card">
          <h2 className="card-title">
            <span className="dot" /> Scheduled jobs
          </h2>
          <div className="trace-list" style={{ marginTop: 14 }}>
            {jobs.map((j) => (
              <div key={j.id} className="trace-item">
                <div className="meta">
                  #{j.id} · <span className={`pill ${statusPillClass(j.status)}`}>{j.status}</span>
                </div>
                <div className="detail">{j.result || j.payload}</div>
              </div>
            ))}
            {!jobs.length && <div className="empty">Chưa có job.</div>}
          </div>
        </section>
      </div>

      <div className="grid2">
        <section className="card">
          <h2 className="card-title">
            <span className="dot" /> Conversations
          </h2>
          <ConversationsTable
            convs={convs}
            onAction={handleConversationAction}
            busyId={busyConv}
          />
        </section>

        <section className="card">
          <h2 className="card-title">
            <span className="dot" /> Latest agent run
          </h2>
          {run ? (
            <div style={{ marginTop: 14, fontSize: 14 }}>
              <div className="meta muted" style={{ marginBottom: 10 }}>
                <code className="md-code">{run.run_id}</code> · agents: {(run.agents || []).join(", ")}
              </div>
              <p style={{ margin: "0 0 8px" }}>
                <strong>User:</strong> {run.user_text}
              </p>
              <p style={{ margin: 0, color: "var(--text-soft)" }}>
                <strong style={{ color: "var(--text)" }}>Reply:</strong> {run.reply?.slice(0, REPLY_PREVIEW_CAP)}
                {(run.reply?.length || 0) > REPLY_PREVIEW_CAP ? "…" : ""}
              </p>
            </div>
          ) : (
            <div className="empty" style={{ marginTop: 14 }}>
              Chưa có run — hãy chat trước.
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
