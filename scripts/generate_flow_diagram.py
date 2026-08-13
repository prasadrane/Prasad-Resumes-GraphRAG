"""
generate_flow_diagram.py — Two-flow architecture diagram from how-it-works.md

Shows Chat Q&A flow (left) and Resume Tailoring flow (right) sharing
common infrastructure (LLM Gateway, GraphRAG Engine, LanceDB).

Run: python scripts/generate_flow_diagram.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SVG_OUT = ROOT / "docs" / "architecture_diagram.svg"
PNG_OUT = ROOT / "docs" / "architecture_diagram.png"

# Wider canvas, tighter vertical fit — no wasted white space
W, H = 1800, 900

# ── Theme tokens (light mode, validated palette) ────────────────────────────
INK = "#0f172a"
MUTED = "#64748b"
SURFACE = "#ffffff"
BAND_BORDER = "#e2e8f0"

LAYER_STYLE = {
    "L1": ("#2563eb", "#eff6ff", "USER INPUT"),
    "L2": ("#059669", "#ecfdf5", "EMBEDDING & RETRIEVAL"),
    "L3": ("#b45309", "#fffbeb", "LLM ROUTING"),
    "L4": ("#7c3aed", "#f5f3ff", "OUTPUT"),
}

EDGE_STYLE = {
    "req":   "#475569",
    "llm":   "#b45309",
    "read":  "#0369a1",
}

FONT = "Segoe UI, system-ui, -apple-system, sans-serif"
# Bigger fonts for readability
FS_TITLE, FS_SUB, FS_EDGE, FS_BAND, FS_LEGEND = 17, 13, 13, 14, 13

# ── Layout: fill the full 900px height ───────────────────────────────────────
# Title: 0-80
# L1: 90-220 (130px)
# L2: 240-400 (160px — extra height for cylinder)
# L3: 420-620 (200px — extra height for gateway + chips)
# L4: 640-800 (160px)
# Bottom padding: 800-900

BOXES = {
    # L1 — User Input (band: 90-225, boxes at 130)
    "chat_q": (95, 130, 340, 90, "L1", "box", "Chat Question", "natural language query"),
    "jd_input": (630, 130, 340, 90, "L1", "box", "Job Description", "ATS keywords"),
    "master": (1180, 130, 340, 90, "L1", "box", "Master Resume", "input/MASTER_RESUME.txt"),
    # L2 — Embedding & Retrieval (band: 240-405, boxes at 280)
    "embed": (95, 280, 340, 110, "L2", "box", "Embedding API", "OpenRouter / Gemini"),
    "lancedb": (470, 270, 340, 120, "L2", "cyl", "LanceDB", "vector store + graph"),
    "graphrag": (845, 280, 340, 110, "L2", "box", "GraphRAG Engine", "local · global · drift"),
    "ats": (1200, 280, 340, 110, "L2", "box", "ATS Matcher", "keyword extraction"),
    # L3 — LLM Routing (band: 420-625, boxes at 460)
    "gateway": (95, 460, 700, 150, "L3", "box", "LLM Gateway · src/gateway", "facade.py · _try_chain failover"),
    "registry": (1180, 475, 340, 110, "L3", "box", "Provider Registry", "src/config/providers.py"),
    # L4 — Output (band: 640-800, boxes at 680)
    "chat_a": (95, 680, 340, 110, "L4", "box", "Chat Answer", "streamed SSE response"),
    "tailored": (470, 680, 340, 110, "L4", "box", "Tailored Resume", "Markdown + PDF"),
}

CHIPS = [
    (115, 555, 210, 45, "Alibaba", "Anthropic protocol"),
    (345, 555, 210, 45, "OpenRouter", "OpenAI protocol"),
    (575, 555, 210, 45, "Gemini", "Google REST"),
]

BANDS = [
    ("L1", 90, 225),
    ("L2", 240, 405),
    ("L3", 420, 625),
    ("L4", 640, 800),
]

EDGES = [
    # Chat Q&A flow (left)
    ("chat_q", "embed", "req", "question", (280, 250), [(265, 220), (265, 280)]),
    ("embed", "lancedb", "read", "embedding", (410, 250), [(435, 335), (470, 335)]),
    ("lancedb", "graphrag", "read", "vector search", (655, 250), [(810, 335), (845, 335)]),
    ("graphrag", "gateway", "llm", "context + query", (1015, 420), [(1015, 390), (1015, 460)]),
    ("gateway", "chat_a", "llm", "stream", (265, 650), [(265, 610), (265, 680)]),
    # Resume Tailoring flow (right)
    ("jd_input", "ats", "req", "JD text", (1000, 250), [(800, 220), (800, 250), (1370, 250), (1370, 280)]),
    ("ats", "graphrag", "req", "keyword query", (1200, 265), [(1200, 335), (1185, 335)]),
    ("master", "ats", "req", "resume data", (1345, 250), [(1350, 220), (1350, 280)]),
    ("ats", "gateway", "llm", "tailor prompt", (1370, 420), [(1370, 390), (1370, 460)]),
    ("gateway", "tailored", "llm", "rewritten content", (640, 650), [(640, 610), (640, 680)]),
    # Shared
    ("registry", "gateway", "req", "provider config", (1015, 530), [(1180, 530), (795, 530)]),
]

LEGEND = [
    ("req", "request / control"),
    ("llm", "LLM call"),
    ("read", "retrieval read"),
]

LABEL_ANCHORS = {
    ("chat_q", "embed"): "start",
    ("jd_input", "ats"): "middle",
    ("master", "ats"): "start",
    ("registry", "gateway"): "end",
    ("embed", "lancedb"): "middle",
    ("lancedb", "graphrag"): "middle",
    ("ats", "graphrag"): "start",
}


# ── Geometry helpers ─────────────────────────────────────────────────────────
def rects_intersect(a, b, gap=0.0):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw + gap <= bx or bx + bw + gap <= ax
                or ay + ah + gap <= by or by + bh + gap <= ay)


def seg_rect_cross(p1, p2, rect, tol=1.0):
    x1, y1 = p1
    x2, y2 = p2
    rx, ry, rw, rh = rect
    rx, ry = rx + tol, ry + tol
    rw, rh = rw - 2 * tol, rh - 2 * tol
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - rx), (dx, rx + rw - x1), (-dy, y1 - ry), (dy, ry + rh - y1)):
        if p == 0:
            if q < 0:
                return False
        else:
            r = q / p
            if p < 0:
                if r > t1:
                    return False
                if r > t0:
                    t0 = r
            else:
                if r < t0:
                    return False
                if r < t1:
                    t1 = r
    return (t1 - t0) > 1e-6


def text_w(s, fs):
    return 0.60 * fs * len(s)


# ── Assertions ──────────────────────────────────────────────────────────────
def check_layout():
    errs = []
    ids = list(BOXES)
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            if rects_intersect(BOXES[a][:4], BOXES[b][:4], gap=10):
                errs.append(f"boxes overlap: {a} / {b}")
    # Band label vs box check — labels must not overlap any box in their band
    for layer, y0, y1 in BANDS:
        label_text = LAYER_STYLE[layer][2]
        label_w = text_w(label_text, FS_BAND)
        label_bb = (48, y0 + 8, label_w + 20, FS_BAND + 8)  # x, y, w, h
        for bid in ids:
            bx, by, bw, bh = BOXES[bid][:4]
            # Check if label is within band's y range AND overlaps box
            if rects_intersect(label_bb, (bx, by, bw, bh), gap=4):
                errs.append(f"band label '{label_text}' overlaps box {bid}")
    for cx, cy, cw, ch, _, _ in CHIPS:
        gx, gy, gw, gh = BOXES["gateway"][:4]
        if not (gx + 10 <= cx and cx + cw <= gx + gw - 10 and gy + 50 <= cy and cy + ch <= gy + gh - 10):
            errs.append(f"chip outside gateway: ({cx},{cy})")
    for edge in EDGES:
        src, dst, kind, label, lxy, pts = edge[:6]
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            for bid in ids:
                if bid in (src, dst):
                    continue
                if seg_rect_cross((x1, y1), (x2, y2), BOXES[bid][:4]):
                    errs.append(f"edge {src}->{dst} crosses box {bid}")
        if label and lxy:
            lx, ly = lxy
            bw = text_w(label, FS_EDGE)
            anchor = LABEL_ANCHORS.get((src, dst), "middle")
            if anchor == "middle":
                bb = (lx - bw / 2, ly - FS_EDGE, bw, FS_EDGE + 8)
            elif anchor == "start":
                bb = (lx, ly - FS_EDGE, bw, FS_EDGE + 8)
            else:
                bb = (lx - bw, ly - FS_EDGE, bw, FS_EDGE + 8)
            for bid in ids:
                if rects_intersect(bb, BOXES[bid][:4]):
                    errs.append(f"edge label '{label}' overlaps box {bid}")
    for bid, (x, y, w, h, layer, kind, title, sub) in BOXES.items():
        for s, fs in ((title, FS_TITLE), (sub, FS_SUB)):
            if text_w(s, fs) > w - 20:
                errs.append(f"text overflows box {bid}: '{s}'")
    gx, gy, gw, _gh, _layer, _kind, gtitle, gsub = BOXES["gateway"]
    for s, fs, base in ((gtitle, FS_TITLE, gy + 45), (gsub, FS_SUB, gy + 75)):
        bb = (gx + gw / 2 - text_w(s, fs) / 2, base - fs, text_w(s, fs), fs + 8)
        for cx, cy, cw, ch, _, _ in CHIPS:
            if rects_intersect(bb, (cx, cy, cw, ch)):
                errs.append(f"gateway text '{s}' overlaps chip")
    return errs


# ── SVG emission ─────────────────────────────────────────────────────────────
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg_arrowhead(cid, color):
    return (f'<marker id="ah-{cid}" viewBox="0 0 10 10" refX="8.5" refY="5" '
            f'markerWidth="8" markerHeight="8" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{color}"/></marker>')


def emit() -> str:
    p = []
    p.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
             f'width="{W}" height="{H}" role="img" '
             f'aria-label="Prasad Resumes: Chat Q&amp;A and Resume Tailoring flows">')
    p.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{SURFACE}"/>')
    p.append("<defs>")
    for cid, col in EDGE_STYLE.items():
        p.append(svg_arrowhead(cid, col))
    p.append("</defs>")

    # Title
    p.append(f'<text x="60" y="42" font-family="{FONT}" font-size="28" font-weight="700" fill="{INK}">'
             f'Prasad Resumes — How It Works</text>')
    p.append(f'<text x="60" y="66" font-family="{FONT}" font-size="14" fill="{MUTED}">'
             f'Chat Q&amp;A flow (left) · Resume Tailoring flow (right) · Shared LLM Gateway + GraphRAG</text>')

    # Legend — bottom-right corner to use the bottom area
    n_rows = (len(LEGEND) + 1) // 2
    legend_h = 24 + n_rows * 30
    p.append(f'<rect x="1400" y="820" width="370" height="{legend_h}" rx="10" fill="{SURFACE}" stroke="{BAND_BORDER}"/>')
    for i, (kind, label) in enumerate(LEGEND):
        lx = 1420 + (i % 2) * 185
        ly = 844 + (i // 2) * 30
        col = EDGE_STYLE[kind]
        p.append(f'<line x1="{lx}" y1="{ly}" x2="{lx + 38}" y2="{ly}" stroke="{col}" '
                 f'stroke-width="2.5" marker-end="url(#ah-{kind})"/>')
        p.append(f'<text x="{lx + 50}" y="{ly + 5}" font-family="{FONT}" font-size="{FS_LEGEND}" fill="{MUTED}">{esc(label)}</text>')

    # Bands
    for layer, y0, y1 in BANDS:
        stroke, tint, label = LAYER_STYLE[layer]
        p.append(f'<rect x="30" y="{y0}" width="{W - 60}" height="{y1 - y0}" rx="14" fill="{tint}"/>')
        # Band label — positioned inside band, well clear of boxes
        p.append(f'<text x="50" y="{y0 + 26}" font-family="{FONT}" font-size="{FS_BAND}" font-weight="700" '
                 f'fill="{stroke}" opacity="0.85">{esc(label)}</text>')

    # Edges
    for edge in EDGES:
        src, dst, kind, label, lxy, pts = edge[:6]
        col = EDGE_STYLE[kind]
        d = " ".join(f"{x},{y}" for x, y in pts)
        p.append(f'<polyline points="{d}" fill="none" stroke="{col}" stroke-width="2.5" '
                 f'marker-end="url(#ah-{kind})"/>')
        if label and lxy:
            anchor = LABEL_ANCHORS.get((src, dst), "middle")
            p.append(f'<text x="{lxy[0]}" y="{lxy[1]}" font-family="{FONT}" font-size="{FS_EDGE}" '
                     f'font-style="italic" fill="{col}" text-anchor="{anchor}" '
                     f'paint-order="stroke" stroke="{SURFACE}" stroke-width="5">{esc(label)}</text>')

    # Boxes
    for bid, (x, y, w, h, layer, kind, title, sub) in BOXES.items():
        stroke = LAYER_STYLE[layer][0]
        if kind == "cyl":
            ry = 16
            p.append(f'<path d="M {x} {y + ry} L {x} {y + h - ry} A {w / 2} {ry} 0 0 0 '
                     f'{x + w} {y + h - ry} L {x + w} {y + ry}" fill="{SURFACE}" stroke="{stroke}" stroke-width="2"/>')
            p.append(f'<ellipse cx="{x + w / 2}" cy="{y + ry}" rx="{w / 2}" ry="{ry}" '
                     f'fill="{SURFACE}" stroke="{stroke}" stroke-width="2"/>')
            ty, sy = y + h / 2 + 6, y + h / 2 + 28
        else:
            p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{SURFACE}" '
                     f'stroke="{stroke}" stroke-width="2"/>')
            if bid == "gateway":
                ty, sy = y + 45, y + 75
            else:
                ty, sy = y + h / 2 - 8, y + h / 2 + 18
        p.append(f'<text x="{x + w / 2}" y="{ty}" font-family="{FONT}" font-size="{FS_TITLE}" '
                 f'font-weight="600" fill="{INK}" text-anchor="middle">{esc(title)}</text>')
        p.append(f'<text x="{x + w / 2}" y="{sy}" font-family="{FONT}" font-size="{FS_SUB}" '
                 f'fill="{MUTED}" text-anchor="middle">{esc(sub)}</text>')

    # Chips
    for cx, cy, cw, ch, title, sub in CHIPS:
        p.append(f'<rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="10" fill="#fffbeb" '
                 f'stroke="#d97706" stroke-width="1.5"/>')
        p.append(f'<text x="{cx + cw / 2}" y="{cy + 22}" font-family="{FONT}" font-size="13" '
                 f'font-weight="600" fill="{INK}" text-anchor="middle">{esc(title)}</text>')
        p.append(f'<text x="{cx + cw / 2}" y="{cy + 40}" font-family="{FONT}" font-size="11.5" '
                 f'fill="{MUTED}" text-anchor="middle">{esc(sub)}</text>')

    p.append("</svg>")
    return "\n".join(p)


def render_png(svg_text: str) -> None:
    from playwright.sync_api import sync_playwright

    html = (f"<!doctype html><html><head><meta charset='utf-8'><style>"
            f"html,body{{margin:0;padding:0;background:{SURFACE};}}</style></head>"
            f"<body>{svg_text}</body></html>")
    tmp = ROOT / "scratch" / "_flow_diagram_render.html"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(html, encoding="utf-8")
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
        page.goto(tmp.as_uri())
        page.locator("svg").screenshot(path=str(PNG_OUT))
        browser.close()
    tmp.unlink(missing_ok=True)


def main() -> int:
    errs = check_layout()
    if errs:
        print("LAYOUT ASSERTIONS FAILED:")
        for e in errs:
            print("  -", e)
        return 1
    svg_text = emit()
    SVG_OUT.write_text(svg_text, encoding="utf-8")
    render_png(svg_text)
    print(f"-> {SVG_OUT.name} + {PNG_OUT.name}  ({PNG_OUT.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
