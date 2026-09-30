import React from "react";

/**
 * Tiny, dependency-free Markdown renderer.
 *
 * The sales agent replies in Markdown (headings, **bold**, bullet / numbered
 * lists, GFM tables, `code`, links, blockquotes). Rendering that as plain text
 * showed raw syntax in the chat bubbles — this turns it into real elements.
 *
 * It builds React nodes directly (no `dangerouslySetInnerHTML`), so nothing the
 * model returns can inject markup.
 */

type Node = React.ReactNode;

/* ----------------------------- inline parsing ----------------------------- */

type InlineRule = {
  re: RegExp;
  render: (m: RegExpMatchArray, key: string) => Node;
};

const INLINE_RULES: InlineRule[] = [
  { re: /^`([^`]+)`/, render: (m, key) => <code key={key} className="md-code">{m[1]}</code> },
  { re: /^\*\*([\s\S]+?)\*\*/, render: (m, key) => <strong key={key}>{inline(m[1], key)}</strong> },
  { re: /^__([^_]+)__/, render: (m, key) => <strong key={key}>{inline(m[1], key)}</strong> },
  { re: /^\*([\s\S]+?)\*/, render: (m, key) => <em key={key}>{inline(m[1], key)}</em> },
  { re: /^_([^_]+)_/, render: (m, key) => <em key={key}>{inline(m[1], key)}</em> },
  { re: /^~~([^~]+)~~/, render: (m, key) => <del key={key}>{inline(m[1], key)}</del> },
  {
    re: /^\[([^\]]+)\]\(([^)\s]+)\)/,
    render: (m, key) => {
      // Allowlist link schemes: http/https/mailto only. React renders other
      // schemes (e.g. javascript:) as live hrefs despite the dev warning, which
      // is a prompt-injection → self-XSS vector into the app origin.
      const href = m[2];
      if (!/^(https?:|mailto:)/i.test(href)) {
        return <span key={key}>{inline(m[1], key)}</span>;
      }
      return (
        <a key={key} href={href} target="_blank" rel="noopener noreferrer" className="md-link">
          {inline(m[1], key)}
        </a>
      );
    },
  },
];

const TRIGGERS = new Set(["`", "*", "_", "~", "["]);

function inline(text: string, keyPrefix: string): Node[] {
  const nodes: Node[] = [];
  let buffer = "";
  let rest = text;
  let k = 0;

  while (rest.length) {
    let matched = false;
    if (TRIGGERS.has(rest[0])) {
      for (const rule of INLINE_RULES) {
        const m = rest.match(rule.re);
        if (m) {
          if (buffer) {
            nodes.push(buffer);
            buffer = "";
          }
          nodes.push(rule.render(m, `${keyPrefix}-${k++}`));
          rest = rest.slice(m[0].length);
          matched = true;
          break;
        }
      }
    }
    if (!matched) {
      buffer += rest[0];
      rest = rest.slice(1);
    }
  }
  if (buffer) nodes.push(buffer);
  return nodes;
}

/* ------------------------------ block parsing ----------------------------- */

function isTableSep(line: string): boolean {
  return /^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$/.test(line) && line.includes("-");
}

function isTable(lines: string[], i: number): boolean {
  return lines[i].includes("|") && i + 1 < lines.length && isTableSep(lines[i + 1]);
}

function splitRow(row: string): string[] {
  let s = row.trim();
  if (s.startsWith("|")) s = s.slice(1);
  if (s.endsWith("|")) s = s.slice(0, -1);
  return s.split("|").map((c) => c.trim());
}

function isBlockStart(line: string, next?: string): boolean {
  const t = line;
  if (/^\s*#{1,6}\s+/.test(t)) return true;
  if (/^\s*```/.test(t)) return true;
  if (/^\s*>\s?/.test(t)) return true;
  if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(t)) return true;
  if (/^\s*[-*•]\s+/.test(t)) return true;
  if (/^\s*\d+[.)]\s+/.test(t)) return true;
  if (t.includes("|") && next !== undefined && isTableSep(next)) return true;
  return false;
}

function parseBlocks(src: string): Node[] {
  const lines = src.replace(/\r\n/g, "\n").split("\n");
  const out: Node[] = [];
  let i = 0;
  let key = 0;
  const nk = () => `b${key++}`;

  while (i < lines.length) {
    const line = lines[i];

    if (!line.trim()) {
      i++;
      continue;
    }

    // fenced code block
    if (/^\s*```/.test(line)) {
      const buf: string[] = [];
      i++;
      while (i < lines.length && !/^\s*```/.test(lines[i])) {
        buf.push(lines[i]);
        i++;
      }
      i++; // consume closing fence
      out.push(
        <pre key={nk()} className="md-pre">
          <code>{buf.join("\n")}</code>
        </pre>,
      );
      continue;
    }

    // heading
    const h = line.match(/^\s*(#{1,6})\s+(.*)$/);
    if (h) {
      const level = Math.min(h[1].length + 1, 6); // shift so `#` renders as h2
      const Tag = `h${level}` as keyof JSX.IntrinsicElements;
      out.push(
        <Tag key={nk()} className={`md-h md-h${h[1].length}`}>
          {inline(h[2], nk())}
        </Tag>,
      );
      i++;
      continue;
    }

    // horizontal rule
    if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
      out.push(<hr key={nk()} className="md-hr" />);
      i++;
      continue;
    }

    // blockquote
    if (/^\s*>\s?/.test(line)) {
      const buf: string[] = [];
      while (i < lines.length && /^\s*>\s?/.test(lines[i])) {
        buf.push(lines[i].replace(/^\s*>\s?/, ""));
        i++;
      }
      out.push(
        <blockquote key={nk()} className="md-quote">
          {parseBlocks(buf.join("\n"))}
        </blockquote>,
      );
      continue;
    }

    // GFM table
    if (isTable(lines, i)) {
      const header = splitRow(lines[i]);
      i += 2; // header + separator
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim() && lines[i].includes("|")) {
        rows.push(splitRow(lines[i]));
        i++;
      }
      out.push(
        <div key={nk()} className="md-table-wrap">
          <table className="md-table">
            <thead>
              <tr>
                {header.map((c) => (
                  <th key={nk()}>{inline(c, nk())}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={nk()}>
                  {header.map((_, ci) => (
                    <td key={nk()}>{inline(r[ci] ?? "", nk())}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }

    // unordered list
    if (/^\s*[-*•]\s+/.test(line)) {
      const items: Node[] = [];
      while (i < lines.length && /^\s*[-*•]\s+/.test(lines[i])) {
        items.push(<li key={nk()}>{inline(lines[i].replace(/^\s*[-*•]\s+/, ""), nk())}</li>);
        i++;
      }
      out.push(
        <ul key={nk()} className="md-ul">
          {items}
        </ul>,
      );
      continue;
    }

    // ordered list
    if (/^\s*\d+[.)]\s+/.test(line)) {
      const items: Node[] = [];
      while (i < lines.length && /^\s*\d+[.)]\s+/.test(lines[i])) {
        items.push(<li key={nk()}>{inline(lines[i].replace(/^\s*\d+[.)]\s+/, ""), nk())}</li>);
        i++;
      }
      out.push(
        <ol key={nk()} className="md-ol">
          {items}
        </ol>,
      );
      continue;
    }

    // paragraph (soft line breaks preserved)
    const para: string[] = [];
    while (i < lines.length && lines[i].trim() && !isBlockStart(lines[i], lines[i + 1])) {
      para.push(lines[i].trim());
      i++;
    }
    out.push(
      <p key={nk()} className="md-p">
        {para.flatMap((pl, idx) =>
          idx === 0 ? inline(pl, nk()) : [<br key={nk()} />, ...inline(pl, nk())],
        )}
      </p>,
    );
  }

  return out;
}

export function Markdown({ text, className }: { text: string; className?: string }) {
  return <div className={className ? `md ${className}` : "md"}>{parseBlocks(text || "")}</div>;
}

export default Markdown;
