"use client";

import { useCallback, useEffect, useState } from "react";
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
} from "./api";
import { OWNER_TOKEN_KEY } from "./constants";

const AUTO_REFRESH_MS = 7000;

export function useDashboard() {
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

  const load = useCallback(async (silent = false) => {
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
  }, []);

  useEffect(() => {
    // The admin BFF requires an owner token; prompt for it once if missing.
    try {
      if (typeof window !== "undefined" && !localStorage.getItem(OWNER_TOKEN_KEY)) {
        const token = window.prompt("Nhập owner token để xem dashboard:");
        if (token) localStorage.setItem(OWNER_TOKEN_KEY, token);
      }
    } catch {}
    load();
  }, [load]);

  // Auto-refresh so a finished consultation shows up without a manual reload.
  useEffect(() => {
    if (!auto) return;
    const id = setInterval(() => load(true), AUTO_REFRESH_MS);
    return () => clearInterval(id);
  }, [auto, load]);

  return {
    leads, convs, memory, jobs, run, err, loading, lastUpdated,
    auto, setAuto, busyConv, load, handleConversationAction,
  };
}
