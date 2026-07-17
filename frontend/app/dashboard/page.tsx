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

export default function DashboardPage() {
  const [leads, setLeads] = useState<any[]>([]);
  const [convs, setConvs] = useState<any[]>([]);
  const [zalo, setZalo] = useState<any[]>([]);
  const [memory, setMemory] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [run, setRun] = useState<any>(null);
  const [err, setErr] = useState("");

  async function load() {
    try {
      setErr("");
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
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <main style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h2 style={{ margin: 0 }}>Owner dashboard</h2>
          <p className="muted">Leads · memory · jobs · agent runs · Zalo</p>
        </div>
        <button className="btn ghost" onClick={load}>
          Refresh
        </button>
      </div>
      {err && <p style={{ color: "var(--danger)" }}>{err}</p>}

      <section className="card">
        <strong>Leads ({leads.length})</strong>
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Name</th>
              <th>Phone</th>
              <th>Channel</th>
              <th>Interest</th>
              <th>Budget</th>
              <th>Status</th>
              <th>Score</th>
            </tr>
          </thead>
          <tbody>
            {leads.map((l) => (
              <tr key={l.id}>
                <td>{l.id}</td>
                <td>{l.name}</td>
                <td>{l.phone}</td>
                <td>{l.channel}</td>
                <td>{l.interest}</td>
                <td>
                  {l.budget_vnd ? `${Number(l.budget_vnd).toLocaleString("vi-VN")}đ` : "—"}
                </td>
                <td>{l.status}</td>
                <td>{l.score}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <div className="grid2">
        <section className="card">
          <strong>Customer memory</strong>
          <div className="trace-list" style={{ marginTop: 10 }}>
            {memory.map((m) => (
              <div key={m.id} className="trace-item">
                <div className="meta">
                  {m.channel}:{m.external_id}
                </div>
                <div style={{ fontSize: 13 }}>
                  {m.profile?.phone && <div>SĐT: {m.profile.phone}</div>}
                  {m.profile?.interests?.length > 0 && (
                    <div>Interests: {(m.profile.interests || []).join(", ")}</div>
                  )}
                  {!m.profile?.phone && !m.profile?.interests?.length && (
                    <span className="muted">{m.summary || "—"}</span>
                  )}
                </div>
              </div>
            ))}
            {!memory.length && <p className="muted">Chưa có memory.</p>}
          </div>
        </section>

        <section className="card">
          <strong>Scheduled jobs</strong>
          <div className="trace-list" style={{ marginTop: 10 }}>
            {jobs.map((j) => (
              <div key={j.id} className="trace-item">
                <div className="meta">
                  #{j.id} · {j.status}
                </div>
                <div style={{ fontSize: 13 }}>{j.result || j.payload}</div>
              </div>
            ))}
            {!jobs.length && <p className="muted">Chưa có job.</p>}
          </div>
        </section>
      </div>

      <div className="grid2">
        <section className="card">
          <strong>Conversations</strong>
          <table className="table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Channel</th>
                <th>Customer</th>
                <th>Status</th>
                <th>Human?</th>
              </tr>
            </thead>
            <tbody>
              {convs.map((c) => (
                <tr key={c.id}>
                  <td>{c.id}</td>
                  <td>{c.channel}</td>
                  <td>{c.customer_name}</td>
                  <td>{c.status}</td>
                  <td>{c.needs_human ? "yes" : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="card">
          <strong>Zalo outbox (mock)</strong>
          <div className="trace-list" style={{ marginTop: 10 }}>
            {zalo.map((z) => (
              <div key={z.id} className="trace-item">
                <div className="meta">
                  {z.direction} · {z.user_id}
                </div>
                <div>{z.content}</div>
              </div>
            ))}
            {!zalo.length && <p className="muted">Trống.</p>}
          </div>
        </section>
      </div>

      <section className="card">
        <strong>Latest agent run</strong>
        {run ? (
          <div style={{ marginTop: 10, fontSize: 14 }}>
            <div className="meta muted">
              {run.run_id} · agents: {(run.agents || []).join(", ")}
            </div>
            <p>
              <strong>User:</strong> {run.user_text}
            </p>
            <p>
              <strong>Reply:</strong> {run.reply?.slice(0, 400)}
              {(run.reply?.length || 0) > 400 ? "…" : ""}
            </p>
          </div>
        ) : (
          <p className="muted">Chưa có run — chat trước.</p>
        )}
      </section>
    </main>
  );
}
