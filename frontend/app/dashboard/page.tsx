"use client";

import { useEffect, useState } from "react";
import {
  fetchConversations,
  fetchJobs,
  fetchLatestRun,
  fetchLeads,
  fetchMemory,
  fetchZaloOutbox,
} from "@/lib/api";

function statusPill(status?: string) {
  const s = (status || "").toLowerCase();
  if (["won", "done", "completed", "success", "qualified", "active"].some((k) => s.includes(k)))
    return "green";
  if (["pending", "new", "open", "queued", "running"].some((k) => s.includes(k))) return "amber";
  if (["lost", "failed", "error", "escalated"].some((k) => s.includes(k))) return "red";
  return "blue";
}

export default function DashboardPage() {
  const [leads, setLeads] = useState<any[]>([]);
  const [convs, setConvs] = useState<any[]>([]);
  const [zalo, setZalo] = useState<any[]>([]);
  const [memory, setMemory] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [run, setRun] = useState<any>(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [auto, setAuto] = useState(true);

  async function load(silent = false) {
    try {
      setErr("");
      if (!silent) setLoading(true);
      const [l, c, z, m, j, r] = await Promise.all([
        fetchLeads(),
        fetchConversations(),
        fetchZaloOutbox(),
        fetchMemory(),
        fetchJobs(),
        fetchLatestRun(),
      ]);
      setLeads(l);
      setConvs(c);
      setZalo(z);
      setMemory(m);
      setJobs(j);
      setRun(r?.run || null);
      setLastUpdated(new Date());
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      if (!silent) setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  // Auto-refresh so a finished consultation shows up without a manual reload.
  useEffect(() => {
    if (!auto) return;
    const id = setInterval(() => load(true), 7000);
    return () => clearInterval(id);
  }, [auto]);

  const stats = [
    { icon: "🧾", value: leads.length, label: "Leads" },
    { icon: "💬", value: convs.length, label: "Cuộc hội thoại" },
    { icon: "🧠", value: memory.length, label: "Hồ sơ ghi nhớ" },
    { icon: "⏱️", value: jobs.length, label: "Jobs đã lên lịch" },
  ];

  return (
    <main className="stack">
      <div className="dash-head">
        <div>
          <h1>Owner dashboard</h1>
          <p className="muted">Leads · memory · jobs · agent runs · Zalo</p>
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
            {loading ? "Đang tải…" : "↻ Làm mới"}
          </button>
        </div>
      </div>

      {err && <div className="error-note" style={{ margin: 0 }}>⚠️ {err}</div>}

      <section className="stat-grid">
        {stats.map((s) => (
          <div key={s.label} className="card stat-card">
            <div className="top">
              <span className="label">{s.label}</span>
              <span className="icon" aria-hidden>
                {s.icon}
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
        <div className="table-wrap" style={{ marginTop: 14 }}>
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Tên</th>
                <th>SĐT</th>
                <th>Kênh</th>
                <th>Quan tâm</th>
                <th>Ngân sách</th>
                <th>Trạng thái</th>
                <th>Điểm</th>
              </tr>
            </thead>
            <tbody>
              {leads.map((l) => (
                <tr key={l.id}>
                  <td>{l.id}</td>
                  <td>{l.name || "—"}</td>
                  <td>{l.phone || "—"}</td>
                  <td>{l.channel || "—"}</td>
                  <td>{l.interest || "—"}</td>
                  <td>{l.budget_vnd ? `${Number(l.budget_vnd).toLocaleString("vi-VN")}đ` : "—"}</td>
                  <td>
                    <span className={`pill ${statusPill(l.status)}`}>{l.status || "—"}</span>
                  </td>
                  <td>{l.score ?? "—"}</td>
                </tr>
              ))}
              {!leads.length && (
                <tr>
                  <td colSpan={8}>
                    <div className="empty" style={{ border: "none", background: "none" }}>
                      Chưa có lead nào.
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
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
                  {m.profile?.interests?.length > 0 && (
                    <div>Quan tâm: {(m.profile.interests || []).join(", ")}</div>
                  )}
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
                  #{j.id} · <span className={`pill ${statusPill(j.status)}`}>{j.status}</span>
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
          <div className="table-wrap" style={{ marginTop: 14 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Kênh</th>
                  <th>Khách</th>
                  <th>Trạng thái</th>
                  <th>Cần người?</th>
                </tr>
              </thead>
              <tbody>
                {convs.map((c) => (
                  <tr key={c.id}>
                    <td>{c.id}</td>
                    <td>{c.channel}</td>
                    <td>{c.customer_name || "—"}</td>
                    <td>
                      <span className={`pill ${statusPill(c.status)}`}>{c.status || "—"}</span>
                    </td>
                    <td>
                      <span className={`pill ${c.needs_human ? "red" : "green"}`}>
                        {c.needs_human ? "Cần" : "Không"}
                      </span>
                    </td>
                  </tr>
                ))}
                {!convs.length && (
                  <tr>
                    <td colSpan={5}>
                      <div className="empty" style={{ border: "none", background: "none" }}>
                        Chưa có hội thoại.
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="card">
          <h2 className="card-title">
            <span className="dot" /> Zalo outbox (mock)
          </h2>
          <div className="trace-list" style={{ marginTop: 14 }}>
            {zalo.map((z) => (
              <div key={z.id} className="trace-item">
                <div className="meta">
                  {z.direction} · {z.user_id}
                </div>
                <div className="detail">{z.content}</div>
              </div>
            ))}
            {!zalo.length && <div className="empty">Trống.</div>}
          </div>
        </section>
      </div>

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
              <strong style={{ color: "var(--text)" }}>Reply:</strong> {run.reply?.slice(0, 400)}
              {(run.reply?.length || 0) > 400 ? "…" : ""}
            </p>
          </div>
        ) : (
          <div className="empty" style={{ marginTop: 14 }}>
            Chưa có run — hãy chat trước.
          </div>
        )}
      </section>
    </main>
  );
}
