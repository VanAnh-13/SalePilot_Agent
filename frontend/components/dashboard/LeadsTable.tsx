import type { Lead } from "@/lib/api";
import { EmptyRow, statusPillClass } from "./shared";

export function LeadsTable({ leads }: { leads: Lead[] }) {
  return (
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
                <span className={`pill ${statusPillClass(l.status)}`}>{l.status || "—"}</span>
              </td>
              <td>{l.score ?? "—"}</td>
            </tr>
          ))}
          {!leads.length && <EmptyRow colSpan={8}>Chưa có lead nào.</EmptyRow>}
        </tbody>
      </table>
    </div>
  );
}
