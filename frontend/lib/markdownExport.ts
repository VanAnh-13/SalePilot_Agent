import { GREETING, type Msg } from "./chatConfig";

/**
 * Serialise the conversation (with its per-turn evidence) to Markdown and
 * trigger a browser download. The greeting bubble is deliberately omitted.
 */
export function downloadMarkdown(msgs: Msg[], externalId: string) {
  const lines: string[] = [
    `# Hội thoại SalePilot-R`,
    ``,
    `- Phiên: \`${externalId}\``,
    `- Xuất lúc: ${new Date().toLocaleString("vi-VN")}`,
    ``,
  ];
  for (const m of msgs) {
    if (m.id === GREETING.id) continue;
    lines.push(`## ${m.role === "user" ? "Khách" : "Trợ lý"}`, ``, m.content, ``);
    if (m.meta) {
      if (m.meta.run_id) lines.push(`- run: \`${m.meta.run_id}\``);
      if (m.meta.decision?.decision_hash)
        lines.push(`- decision hash: \`${m.meta.decision.decision_hash}\``);
      for (const item of m.meta.decision?.top3 || []) {
        if (item?.name)
          lines.push(
            `- Đề xuất: ${item.name}${item.price_vnd ? ` — ${Number(item.price_vnd).toLocaleString("vi-VN")}đ` : ""}`,
          );
      }
      if (m.meta.trace?.length) {
        lines.push(`- trace: ${m.meta.trace.map((s) => `${s.agent}/${s.event}`).join(" → ")}`);
      }
      lines.push(``);
    }
  }
  const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `salepilot-${externalId || "hoi-thoai"}.md`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
