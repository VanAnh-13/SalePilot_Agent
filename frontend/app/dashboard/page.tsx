"use client";

import type { ComponentType, SVGProps } from "react";
import { useDashboard } from "@/lib/useDashboard";
import { IconAlert, IconBrain, IconChat, IconClock, IconRefresh, IconUsers } from "@/components/Icons";
import { ConversationsTable } from "@/components/dashboard/ConversationsTable";
import { LeadsTable } from "@/components/dashboard/LeadsTable";
import { statusPillClass } from "@/components/dashboard/shared";

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
  const {
    leads, convs, memory, jobs, run, err, loading, lastUpdated,
    auto, setAuto, busyConv, load, handleConversationAction,
  } = useDashboard();

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
