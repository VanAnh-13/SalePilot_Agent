import type { ReactNode } from "react";

export function statusPillClass(status?: string | null) {
  const s = (status || "").toLowerCase();
  if (["won", "done", "completed", "success", "qualified", "active"].some((k) => s.includes(k)))
    return "green";
  if (["pending", "new", "open", "queued", "running"].some((k) => s.includes(k))) return "amber";
  if (["lost", "failed", "error", "escalated"].some((k) => s.includes(k))) return "red";
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
