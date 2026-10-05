import type { DecisionConstraint, DecisionContract, DecisionItem } from "./types";

// Vietnamese labels for known constraint/need keys; unknown keys fall back to
// the raw key with underscores turned into spaces.
export const KEY_LABELS: Record<string, string> = {
  budget_vnd: "Ngân sách",
  household_size: "Số người dùng",
  area_m2: "Diện tích phòng",
  max_width_cm: "Chiều ngang tối đa",
  max_height_cm: "Chiều cao tối đa",
  max_depth_cm: "Chiều sâu tối đa",
  capacity_l: "Dung tích",
  load_kg: "Khối lượng giặt",
  ram_gb: "RAM",
  storage_gb: "Bộ nhớ",
};

export function shortHash(value?: string | null) {
  if (!value) return "chưa có";
  return value.length > 14 ? `${value.slice(0, 10)}…${value.slice(-4)}` : value;
}

export function formatMoney(value?: number | null) {
  if (value == null) return "Chưa có giá";
  return new Intl.NumberFormat("vi-VN").format(value) + " ₫";
}

export function formatValue(key: string, value: unknown): string {
  if (value == null) return "không có dữ liệu";
  if (key === "budget_vnd" && typeof value === "number") return formatMoney(value);
  if (typeof value === "boolean") return value ? "có" : "không";
  if (typeof value === "object" && !Array.isArray(value)) {
    const range = value as { min?: unknown; max?: unknown };
    if ("min" in range || "max" in range) {
      return `${range.min ?? "?"} – ${range.max ?? "?"}`;
    }
    return JSON.stringify(value);
  }
  return String(value);
}

export function constraintLabel(constraint: DecisionConstraint) {
  return (constraint.key && KEY_LABELS[constraint.key]) || constraint.key?.replaceAll("_", " ") || "Ràng buộc";
}

export function statusLabel(status?: string) {
  if (status === "matched") return "Đạt";
  if (status === "violated") return "Không đạt";
  return "Chưa rõ";
}

export function sourceRow(item: DecisionItem) {
  const row = item.provenance?.source_row;
  return row == null ? "không rõ dòng" : `dòng ${row}`;
}

function hasHardViolation(decision: DecisionContract) {
  return (decision.top3 || []).slice(0, 3).some((item) =>
    (item?.constraints || []).some(
      (constraint) => constraint.hardness === "hard" && constraint.status === "violated",
    ),
  );
}

export function decisionTone(decision: DecisionContract): "success" | "warn" | "danger" {
  if (hasHardViolation(decision)) return "danger";
  return decision.need_more ? "warn" : decision.ok ? "success" : "warn";
}

export function decisionStatusText(decision: DecisionContract): string {
  if (hasHardViolation(decision)) return "Có đề xuất vi phạm ràng buộc cứng";
  if (decision.need_more) return "Cần thêm thông tin";
  if (decision.ok) return "Có đề xuất kèm bằng chứng";
  return "Không đủ bằng chứng để đề xuất";
}
