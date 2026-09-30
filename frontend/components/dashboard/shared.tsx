import type { ReactNode } from "react";
import type { StatusTone } from "@/lib/api";

// Status keywords bucketed by the pill colour they resolve to.
const POSITIVE_STATUS = ["won", "done", "completed", "success", "qualified", "active"];
const PENDING_STATUS = ["pending", "new", "open", "queued", "running"];
const NEGATIVE_STATUS = ["lost", "failed", "error", "escalated"];

export function statusPillClass(status?: string | null): StatusTone {
  const s = (status || "").toLowerCase();
  if (POSITIVE_STATUS.some((k) => s.includes(k))) return "green";
  if (PENDING_STATUS.some((k) => s.includes(k))) return "amber";
  if (NEGATIVE_STATUS.some((k) => s.includes(k))) return "red";
  return "blue";
}

export function EmptyRow({ colSpan, children }: { colSpan: number; children: ReactNode }) {
  return (
    <tr>
      <td colSpan={colSpan}>
        <div className="empty" style={{ border: "none", background: "none" }}>
          {children}
        </div>
      </td>
    </tr>
  );
}
