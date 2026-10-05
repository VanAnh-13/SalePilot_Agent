import type { DecisionContract, TraceStep } from "./types";

export type MsgMeta = {
  trace?: TraceStep[];
  used_agents?: string[];
  run_id?: string | null;
  decision?: DecisionContract | null;
  memory_summary?: string | null;
};

export type Msg = {
  id: string;
  role: "user" | "assistant";
  content: string;
  meta?: MsgMeta;
};

// localStorage keys used to persist the web session across navigations/refreshes.
export const LS_ID = "salepilot_external_id";
export const LS_MSGS = "salepilot_msgs";

export const WEB_ID_PREFIX = "web-";

export const GREETING: Msg = {
  id: "greeting",
  role: "assistant",
  content:
    "Chào bạn! Em là **SalePilot-R** — hệ hỗ trợ quyết định điện máy theo nhu cầu thật " +
    "(tủ lạnh, máy lạnh, máy giặt, đồng hồ thông minh, máy tính bảng, PC, màn hình…).\n\n" +
    "Em sẽ kiểm tra ràng buộc và chỉ đề xuất khi có đủ bằng chứng từ catalog. Bạn đang cần sản phẩm gì, ngân sách khoảng bao nhiêu ạ?",
};

export const CHIPS = [
  "Gia đình 4 người, dưới 15 triệu, cần tủ lạnh tiết kiệm điện",
  "Cần máy lạnh cho phòng 20m2, tầm 12 triệu, chạy êm",
  "Nhà 5 người cần máy giặt cửa trước 9kg dưới 15 triệu có sấy",
  "Đồng hồ thông minh dưới 3 triệu, nghe gọi, theo dõi sức khỏe",
  "Máy tính bảng dưới 8 triệu, pin trâu, có lắp sim",
];

export const CHAT_ERROR_MESSAGE = "Lỗi gọi API. Kiểm tra kết nối backend và CORS.";

// Maximum characters of the memory summary previewed in the trace panel.
export const MEMORY_PREVIEW_CAP = 160;

// Agent names that map to a dedicated badge colour; anything else renders "plain".
export const AGENT_NAMES = ["lead", "catalog", "knowledge", "crm", "order", "escalation"];

export function agentClass(name: string) {
  const n = name.toLowerCase();
  if (AGENT_NAMES.includes(n)) return n;
  return "plain";
}
