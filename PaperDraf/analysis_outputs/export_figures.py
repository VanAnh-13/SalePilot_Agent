"""Export this manuscript's restricted TikZ flow syntax to editable SVG previews.

The authoritative diagrams remain in main.tex. This exports their node text,
positions and edges without TeX, for visual inspection when TeX is unavailable.
It is not a general TikZ renderer or a substitute for compiling the paper.
Optional PNG rendering uses an existing Node.js + sharp installation.
"""

import argparse
import html
import json
import re
import subprocess
from pathlib import Path

from PIL import ImageFont

PAPER = Path(__file__).resolve().parents[1]
CM = 96 / 2.54
PAD = 5.4
FONT_SIZE = 11
LINE = 14
COLORS = {"bluewash": "#edf4fb", "greenwash": "#ebf5f0", "amberwash": "#fff5e6"}


def plain(text):
    text = text.replace(r"\\", "\n").replace(r"\_", "_")
    text = text.replace(r"\rightarrow", "→").replace(r"\leftrightarrow", "↔")
    text = text.replace(r"\sys", "S (hybrid)").replace(r"\ref{eq:score}", "3")
    text = text.replace("B_0", "B₀").replace("B_1", "B₁")
    text = re.sub(r"\\textbf\{([^{}]*)\}", r"\1", text)
    text = text.replace("$", "").replace("~", " ").replace("{", "").replace("}", "")
    return text


def length(value):
    value = value.strip()
    number = float(re.match(r"[-.\d]+", value)[0])
    if value.endswith("mm"):
        return number * CM / 10
    if value.endswith("pt"):
        return number * 96 / 72
    return number * CM


def anchor(box, side):
    x, y, w, h = (box[k] for k in ("x", "y", "w", "h"))
    return (x + (w / 2 if "east" in side else -w / 2 if "west" in side else 0),
            y + (h / 2 if "south" in side else -h / 2 if "north" in side else 0))


def wrap(text, width, font):
    lines = []
    for part in text.splitlines():
        line = ""
        for word in part.split():
            proposal = (line + " " + word).strip()
            if line and font.getlength(proposal) > width:
                lines.append(line)
                line = word
            else:
                line = proposal
        lines.append(line)
    return lines


def export(name, source, font):
    default_gap = re.search(r"node distance=([.\d]+mm)", source)
    gap = length(default_gap[1]) if default_gap else length("3mm")
    nodes = {}
    for match in re.finditer(r"\\node\[(.*?)\]\s*\(([^)]+)\)\s*(?:at\s*\(([^)]+)\))?\s*\{(.*?)\};", source, re.S):
        opts, identifier, absolute, body = match.groups()
        explicit = re.search(r"text width=([.\d]+cm)", opts)
        content_width = length(explicit[1]) if explicit else length("3.05cm" if "narrow" in opts else "6.6cm")
        lines = wrap(plain(body), content_width, font)
        minimum = re.search(r"minimum height=([.\d]+cm)", opts)
        height = max(len(lines) * LINE + 2 * PAD, length(minimum[1]) if minimum else length(".58cm"))
        width = content_width + 2 * PAD
        fill = next((v for k, v in COLORS.items() if "fill=" + k in opts), COLORS["bluewash"])
        if absolute:
            x, y = (float(v) * CM for v in absolute.split(","))
            y = -y
        else:
            position = re.search(r"below(?: (left|right))?=([^,]+)", opts)
            if not position:
                x, y = 0, 0
            else:
                direction, relative = position.groups()
                distance, parent = relative.rsplit("of ", 1)
                target = nodes[parent.strip()]
                if direction:
                    vertical, horizontal = distance.split(" and ")
                    vertical, horizontal = length(vertical), length(horizontal)
                    x = target["x"] + (-1 if direction == "left" else 1) * (target["w"] / 2 + horizontal + width / 2)
                else:
                    vertical = length(distance) if distance.strip() else gap
                    x = target["x"]
                y = target["y"] + target["h"] / 2 + vertical + height / 2
        nodes[identifier] = dict(x=x, y=y, w=width, h=height, lines=lines, fill=fill)

    def point(token):
        identifier, _, side = token.partition(".")
        return anchor(nodes[identifier], side)

    paths = []
    labels = []
    for expression in re.findall(r"\\draw\[arr\]\s*(.*?);", source):
        label = re.search(r"node\[note(?:,pos=([.\d]+))?\]\{([^}]+)\}", expression)
        expression = re.sub(r"node\[note(?:,pos=[.\d]+)?\]\{[^}]+\}", "", expression)
        start, rest = re.match(r"\(([^)]+)\)(.*)", expression).groups()
        pts = [point(start)]
        relative = re.match(r"--\+\+\(([-.\d]+),([-.\d]+)\)(.*)", rest)
        if relative:
            dx, dy, rest = relative.groups()
            pts.append((pts[-1][0] + float(dx) * CM, pts[-1][1] - float(dy) * CM))
        operator, endpoint = re.fullmatch(r"(--|\|-\|?|-?\|?-\||\|-)\(([^)]+)\)", rest).groups()
        end = point(endpoint)
        if operator == "|-":
            pts.append((pts[-1][0], end[1]))
        elif operator == "-|":
            pts.append((end[0], pts[-1][1]))
        elif operator == "--" and len(pts) == 1 and "." not in start and "." not in endpoint:
            a, b = nodes[start], nodes[endpoint]
            horizontal = abs(a["x"] - b["x"]) > abs(a["y"] - b["y"])
            pts[0] = anchor(a, "east" if horizontal and b["x"] > a["x"] else "west" if horizontal else "south" if b["y"] > a["y"] else "north")
            end = anchor(b, "west" if horizontal and b["x"] > a["x"] else "east" if horizontal else "north" if b["y"] > a["y"] else "south")
        pts.append(end)
        paths.append(pts)
        if label:
            left, right = pts[-2:]
            labels.append(((left[0] + right[0]) / 2, (left[1] + right[1]) / 2 - 4, label[2]))

    all_x = [p[0] for pts in paths for p in pts]
    all_y = [p[1] for pts in paths for p in pts]
    for box in nodes.values():
        all_x.extend([box["x"] - box["w"] / 2, box["x"] + box["w"] / 2])
        all_y.extend([box["y"] - box["h"] / 2, box["y"] + box["h"] / 2])
    x0, y0 = min(all_x) - 12, min(all_y) - 12
    width, height = max(all_x) - x0 + 12, max(all_y) - y0 + 12
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.2f}" height="{height:.2f}" viewBox="{x0:.2f} {y0:.2f} {width:.2f} {height:.2f}">',
             '<title>' + name.replace("_", " ").title() + '</title>',
             '<desc>Preview exported from the corresponding TikZ block in main.tex; positions and text share that source.</desc>',
             f'<rect x="{x0}" y="{y0}" width="{width}" height="{height}" fill="white"/>',
             '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#526477"/></marker></defs>']
    for pts in paths:
        points = " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)
        parts.append(f'<polyline points="{points}" fill="none" stroke="#526477" stroke-width=".9" marker-end="url(#arrow)"/>')
    for box in nodes.values():
        x, y, w, h = (box[k] for k in ("x", "y", "w", "h"))
        parts.append(f'<rect x="{x-w/2:.2f}" y="{y-h/2:.2f}" width="{w:.2f}" height="{h:.2f}" rx="3" fill="{box["fill"]}" stroke="#526477" stroke-width=".7"/>')
        text_y = y - (len(box["lines"]) - 1) * LINE / 2 + 3.5
        for i, line in enumerate(box["lines"]):
            parts.append(f'<text x="{x:.2f}" y="{text_y+i*LINE:.2f}" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="{FONT_SIZE}" fill="#18324d">{html.escape(line)}</text>')
    for x, y, label in labels:
        text_width = font.getlength(label)
        parts.append(f'<rect x="{x-text_width/2-2:.2f}" y="{y-9:.2f}" width="{text_width+4:.2f}" height="12" fill="white"/>')
        parts.append(f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="middle" font-family="Arial,Helvetica,sans-serif" font-size="9" fill="#18324d">{html.escape(label)}</text>')
    parts.append("</svg>")
    out = PAPER / "figures" / (name + ".svg")
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")
    # Report actual rectangle intersections, not harmless line crossings.
    collisions = []
    entries = list(nodes.items())
    for i, (a, first) in enumerate(entries):
        for b, second in entries[i + 1:]:
            if abs(first["x"]-second["x"]) < (first["w"]+second["w"])/2 - .1 and abs(first["y"]-second["y"]) < (first["h"]+second["h"])/2 - .1:
                collisions.append([a, b])
    return out, collisions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", required=True, help="Path to an installed Arial-compatible TTF")
    parser.add_argument("--node", type=Path)
    parser.add_argument("--node-modules", type=Path)
    args = parser.parse_args()
    font = ImageFont.truetype(args.font, FONT_SIZE)
    tex = (PAPER / "main.tex").read_text(encoding="utf-8")
    blocks = re.findall(r"% FIGURE: (\w+)\s*(\\begin\{tikzpicture\}.*?\\end\{tikzpicture\})", tex, re.S)
    assert len(blocks) == 5
    for name, source in blocks:
        out, collisions = export(name, source, font)
        if args.node and args.node_modules:
            subprocess.run([str(args.node), "-e", "const sharp=require(process.argv[1]);sharp(process.argv[2],{density:288}).png().toFile(process.argv[3]);", str(args.node_modules / "sharp"), str(out), str(out.with_suffix(".png"))], check=True)
        print(json.dumps({"figure": name, "overlapping_nodes": collisions}))
        assert not collisions, (name, collisions)


if __name__ == "__main__":
    main()
