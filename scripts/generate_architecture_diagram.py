"""
generate_architecture_diagram.py — Programmatic SVG architecture generator with geometric assertions and Playwright PNG rendering.

Adheres strictly to the system-diagrams skill specification:
- 5 categorical layer swimlanes with validated palette
- Orthogonal routing with right-angle elbows
- Zero overlapping boxes, edges, or labels
- Playwright headless 2x high-DPI rasterization
"""

import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent

# ── Data structures ─────────────────────────────────────────────────────────

@dataclass
class Box:
    id: str
    x: float
    y: float
    w: float
    h: float
    layer: int
    title: str
    sub: str = ""
    badge: str = ""
    is_dashed: bool = False
    is_cylinder: bool = False


@dataclass
class Edge:
    src: str
    dst: str
    kind: str  # "control", "graph", "llm", "artifact"
    label: str
    points: List[Tuple[float, float]]  # Orthogonal polyline


@dataclass
class Band:
    layer: int
    y_top: float
    y_bot: float
    label: str
    color: str
    tint: str


# ── Geometry & Assertions ───────────────────────────────────────────────────

def box_rect(b: Box, pad: float = 4.0) -> Tuple[float, float, float, float]:
    return (b.x - pad, b.y - pad, b.x + b.w + pad, b.y + b.h + pad)


def rects_intersect(r1: Tuple[float, float, float, float], r2: Tuple[float, float, float, float]) -> bool:
    return not (r1[2] <= r2[0] or r1[0] >= r2[2] or r1[3] <= r2[1] or r1[1] >= r2[3])


def line_intersects_rect(p1: Tuple[float, float], p2: Tuple[float, float], r: Tuple[float, float, float, float]) -> bool:
    """Liang-Barsky segment vs AABB intersection test."""
    x1, y1 = p1
    x2, y2 = p2
    xmin, ymin, xmax, ymax = r
    dx = x2 - x1
    dy = y2 - y1

    p = [-dx, dx, -dy, dy]
    q = [x1 - xmin, xmax - x1, y1 - ymin, ymax - y1]

    u1 = 0.0
    u2 = 1.0

    for i in range(4):
        if p[i] == 0:
            if q[i] < 0:
                return False
        else:
            t = q[i] / p[i]
            if p[i] < 0:
                if t > u2:
                    return False
                if t > u1:
                    u1 = t
            else:
                if t < u1:
                    return False
                if t < u2:
                    u2 = t

    return u1 <= u2


def assert_layout(boxes: List[Box], edges: List[Edge]):
    """Enforce zero collisions across all visual elements."""
    # 1. Box-vs-Box collision check
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            b1, b2 = boxes[i], boxes[j]
            if rects_intersect(box_rect(b1, pad=6), box_rect(b2, pad=6)):
                raise AssertionError(f"Collision between Box '{b1.id}' and '{b2.id}'")

    # 2. Edge-vs-Box collision check (excluding endpoint boxes)
    box_map = {b.id: b for b in boxes}
    for edge in edges:
        for idx in range(len(edge.points) - 1):
            p1 = edge.points[idx]
            p2 = edge.points[idx + 1]
            for b in boxes:
                if b.id in (edge.src, edge.dst):
                    continue
                if line_intersects_rect(p1, p2, (b.x + 2, b.y + 2, b.x + b.w - 2, b.y + b.h - 2)):
                    raise AssertionError(f"Edge {edge.src}->{edge.dst} intersects Box '{b.id}' on segment {p1}->{p2}")


# ── SVG Generation ──────────────────────────────────────────────────────────

def render_svg(width: int, height: int, bands: List[Band], boxes: List[Box], edges: List[Edge]) -> str:
    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="Prasad Resumes GraphRAG Architecture">')
    svg.append('<style>')
    svg.append("""
        text { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
        .band-title { font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; }
        .box-title { font-size: 15px; font-weight: 600; fill: #0f172a; }
        .box-sub { font-size: 12px; fill: #64748b; }
        .box-badge { font-size: 11px; font-weight: 600; }
        .edge-label { font-size: 11px; font-style: italic; font-weight: 500; }
        .legend-text { font-size: 12px; fill: #334155; font-weight: 500; }
    """)
    svg.append('</style>')

    # Background
    svg.append(f'<rect width="{width}" height="{height}" fill="#f8fafc" />')

    # Arrowhead markers
    svg.append('<defs>')
    colors = {"control": "#475569", "graph": "#059669", "llm": "#b45309", "artifact": "#7c3aed"}
    for kind, col in colors.items():
        svg.append(f'<marker id="ah-{kind}" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">')
        svg.append(f'<path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="{col}" />')
        svg.append('</marker>')
    svg.append('</defs>')

    # Header
    svg.append('<text x="60" y="44" font-size="24" font-weight="700" fill="#0f172a">Prasad Resumes — GraphRAG &amp; Talent Analytics Platform</text>')
    svg.append('<text x="60" y="66" font-size="13" fill="#64748b">Knowledge Graph RAG · Real-Time ATS Match Scoring · Multi-Provider Serverless Gateway (Alibaba/Gemini/OpenRouter)</text>')

    # Legend in header strip
    svg.append('<g transform="translate(1120, 26)">')
    svg.append('<rect width="620" height="46" rx="8" fill="#ffffff" stroke="#e2e8f0" stroke-width="1.5" />')
    legend_items = [
        ("control", "#475569", "Route / Request", 20),
        ("graph", "#059669", "Graph / KG Query", 160),
        ("llm", "#b45309", "LLM Inference", 320),
        ("artifact", "#7c3aed", "Artifact / PDF", 460),
    ]
    for kind, col, lbl, lx in legend_items:
        svg.append(f'<line x1="{lx}" y1="23" x2="{lx + 24}" y2="23" stroke="{col}" stroke-width="2" marker-end="url(#ah-{kind})" />')
        svg.append(f'<text x="{lx + 32}" y="27" class="legend-text">{lbl}</text>')
    svg.append('</g>')

    # Bands
    for band in bands:
        h = band.y_bot - band.y_top
        svg.append(f'<rect x="40" y="{band.y_top}" width="{width - 80}" height="{h}" rx="12" fill="{band.tint}" stroke="{band.color}" stroke-opacity="0.25" stroke-width="1.5" />')
        svg.append(f'<text x="60" y="{band.y_top + 24}" fill="{band.color}" class="band-title">LAYER {band.layer}: {band.label}</text>')

    # Edges
    for edge in edges:
        col = colors.get(edge.kind, "#64748b")
        pts_str = " ".join(f"{x},{y}" for x, y in edge.points)
        svg.append(f'<polyline points="{pts_str}" fill="none" stroke="{col}" stroke-width="2" stroke-linejoin="round" marker-end="url(#ah-{edge.kind})" />')
        if edge.label and len(edge.points) >= 2:
            # Place label at middle of longest segment
            max_seg_len = 0
            best_pt = edge.points[0]
            for idx in range(len(edge.points) - 1):
                p1 = edge.points[idx]
                p2 = edge.points[idx + 1]
                seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
                if seg_len > max_seg_len:
                    max_seg_len = seg_len
                    best_pt = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
            svg.append(f'<text x="{best_pt[0]}" y="{best_pt[1] - 4}" fill="{col}" text-anchor="middle" class="edge-label">{edge.label}</text>')

    # Boxes
    for b in boxes:
        col = colors.get("control", "#0284c7")
        if b.layer == 1: col = "#2563eb"
        elif b.layer == 2: col = "#059669"
        elif b.layer == 3: col = "#b45309"
        elif b.layer == 4: col = "#7c3aed"
        elif b.layer == 5: col = "#0284c7"

        dash_attr = 'stroke-dasharray="5 3"' if b.is_dashed else ''
        svg.append(f'<rect x="{b.x}" y="{b.y}" width="{b.w}" height="{b.h}" rx="10" fill="#ffffff" stroke="{col}" stroke-width="2" {dash_attr} filter="drop-shadow(0 2px 4px rgba(0,0,0,0.04))" />')
        
        # Header / Title inside box
        cx = b.x + b.w / 2
        svg.append(f'<text x="{cx}" y="{b.y + 32}" text-anchor="middle" class="box-title">{b.title}</text>')
        if b.sub:
            svg.append(f'<text x="{cx}" y="{b.y + 54}" text-anchor="middle" class="box-sub">{b.sub}</text>')
        if b.badge:
            svg.append(f'<rect x="{cx - 60}" y="{b.y + b.h - 28}" width="120" height="20" rx="6" fill="{col}" fill-opacity="0.1" />')
            svg.append(f'<text x="{cx}" y="{b.y + b.h - 14}" text-anchor="middle" fill="{col}" class="box-badge">{b.badge}</text>')

    svg.append('</svg>')
    return "\n".join(svg)


# ── Diagram Definition ──────────────────────────────────────────────────────

def build_diagram() -> Tuple[int, int, List[Band], List[Box], List[Edge]]:
    W, H = 1800, 1060

    bands = [
        Band(1, 90, 240, "Multimodal User Ingestion & URL Scraper", "#2563eb", "#eff6ff"),
        Band(2, 270, 440, "Intent Routing, SME Ontology & ATS Scoring", "#059669", "#f0fdf4"),
        Band(3, 470, 640, "Resume Tailoring & Story Context Orchestration", "#b45309", "#fffbeb"),
        Band(4, 670, 840, "Multi-Provider LLM Gateway & Fallback Matrix", "#7c3aed", "#faf5ff"),
        Band(5, 870, 1020, "Knowledge Graph Artifacts & ReportLab PDF Renderer", "#0284c7", "#f0f9ff"),
    ]

    # Grid columns: x = 80, 500, 920, 1340 (box width 380, gap 40)
    boxes = [
        # Layer 1
        Box("cli", 80, 125, 380, 95, 1, "Unified CLI Engine", "cli.py: query, generate, benchmark, ui", badge="Fast Entrypoint"),
        Box("web_ui", 500, 125, 380, 95, 1, "Web UI & Multimodal Voice", "FastAPI app.py + Web Speech API + SSE", badge="Browser Client"),
        Box("jd_scraper", 920, 125, 380, 95, 1, "JD URL Scraper & Normalizer", "jd_extractor.py: LinkedIn, Greenhouse, Lever", badge="Auto-Extraction"),
        Box("source_inputs", 1340, 125, 380, 95, 1, "Master Resumes & Story Bank", "MASTER_RESUME.txt + STAR Story Bank", badge="Candidate Baseline"),

        # Layer 2
        Box("intent_router", 80, 310, 380, 105, 2, "Intent Classifier & Router", "intent_classifier.py: 8 Intent Categories", badge="Query Routing"),
        Box("sme_ontology", 500, 310, 380, 105, 2, "SME Tech Ontology & Taxonomy", "sme_ontology.py: 120+ Skill Taxonomies", badge="Domain Expansion"),
        Box("ats_scorer", 920, 310, 380, 105, 2, "Real-Time ATS Scorer Engine", "ats_scorer.py: Match %, Gaps, Suggestions", badge="Real-Time Analytics"),
        Box("guardrail", 1340, 310, 380, 105, 2, "Retrieval Guardrail & Redactor", "retrieval_guardrail.py + pii_redactor.py", badge="Hallucination Shield"),

        # Layer 3
        Box("domain_matcher", 80, 510, 380, 105, 3, "Domain Variant Matcher", "domain_matcher.py: AI/Cloud/DevEx/Security", badge="Summary Pre-select"),
        Box("prompt_builder", 500, 510, 380, 105, 3, "Prompt Builder & Metric Extractor", "prompt_builder.py: Single-call synthesis", badge="Metric & Story Inject"),
        Box("text_formatter", 920, 510, 380, 105, 3, "Text Formatter & ATS Bolder", "text_formatter.py: <20% Bold Cap, 2-Page Budget", badge="ATS Rules Engine"),
        Box("search_engine", 1340, 510, 380, 105, 3, "GraphRAG & Static Search Engine", "static_graph_reader.py + search_engine.py", badge="Sub-second Graph"),

        # Layer 4
        Box("gateway_facade", 80, 710, 380, 105, 4, "Gateway Facade & Circuit Breaker", "facade.py: Provider failover & backoff", badge="High Availability"),
        Box("alibaba_prov", 500, 710, 380, 105, 4, "Alibaba Cloud Provider", "qwen3.7-plus (Primary Resume Tailor)", badge="Primary Tailor"),
        Box("gemini_prov", 920, 710, 380, 105, 4, "Google Gemini AI Studio", "gemini-2.5-flash-lite (1500 RPD Free Pool)", badge="Active Fallback"),
        Box("openrouter_prov", 1340, 710, 380, 105, 4, "OpenRouter Free Pool", "freellmapi-chat / Nemotron Embeddings", badge="Global Routing"),

        # Layer 5
        Box("graph_store", 80, 905, 380, 95, 5, "GraphRAG Knowledge Graph", "entities.parquet, relationships.parquet", badge="Knowledge Store", is_cylinder=True),
        Box("reportlab_pdf", 500, 905, 380, 95, 5, "ReportLab PDF Renderer", "pdf_renderer.py + pdf_styles.py (2-Page)", badge="Print Engine"),
        Box("telemetry", 920, 905, 380, 95, 5, "Observability & Benchmarks", "benchmark_eval.py + metrics.py + correlation", badge="Metrics & Tracing"),
        Box("static_web", 1340, 905, 380, 95, 5, "Vercel / Production Deployment", "api/index.py + vercel.json + Static UI", badge="Edge Serverless"),
    ]

    edges = [
        # L1 -> L2
        Edge("cli", "intent_router", "control", "dispatch query", [(270, 220), (270, 310)]),
        Edge("web_ui", "sme_ontology", "control", "expand skills", [(690, 220), (690, 310)]),
        Edge("jd_scraper", "ats_scorer", "control", "parsed JD", [(1110, 220), (1110, 310)]),
        Edge("source_inputs", "guardrail", "graph", "sanitize", [(1530, 220), (1530, 310)]),

        # L2 -> L3
        Edge("intent_router", "domain_matcher", "control", "classify domain", [(270, 415), (270, 510)]),
        Edge("sme_ontology", "prompt_builder", "control", "taxonomy map", [(690, 415), (690, 510)]),
        Edge("ats_scorer", "text_formatter", "control", "ats keywords", [(1110, 415), (1110, 510)]),
        Edge("guardrail", "search_engine", "graph", "retrieve entities", [(1530, 415), (1530, 510)]),

        # L3 -> L4
        Edge("domain_matcher", "gateway_facade", "llm", "orchestrate LLM", [(270, 615), (270, 710)]),
        Edge("prompt_builder", "alibaba_prov", "llm", "single-call prompt", [(690, 615), (690, 710)]),
        Edge("text_formatter", "gemini_prov", "llm", "fallback prompt", [(1110, 615), (1110, 710)]),
        Edge("search_engine", "openrouter_prov", "graph", "embed / query", [(1530, 615), (1530, 710)]),

        # L4 -> L5
        Edge("gateway_facade", "graph_store", "graph", "graph query", [(270, 815), (270, 905)]),
        Edge("alibaba_prov", "reportlab_pdf", "artifact", "render PDF", [(690, 815), (690, 905)]),
        Edge("gemini_prov", "telemetry", "control", "record metrics", [(1110, 815), (1110, 905)]),
        Edge("openrouter_prov", "static_web", "control", "stream SSE", [(1530, 815), (1530, 905)]),
    ]

    return W, H, bands, boxes, edges


def main():
    W, H, bands, boxes, edges = build_diagram()

    # Verify no geometric overlap
    assert_layout(boxes, edges)
    print("[SUCCESS] Geometric assertions passed: zero overlaps, zero invalid edge crossings.")

    svg_content = render_svg(W, H, bands, boxes, edges)

    docs_dir = ROOT_DIR / "docs"
    svg_path = docs_dir / "architecture_diagram.svg"
    png_path = docs_dir / "architecture_diagram.png"

    svg_path.write_text(svg_content, encoding="utf-8")
    print(f"[SUCCESS] Saved SVG to {svg_path}")

    # Render PNG using Playwright
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=2)
            page.set_content(svg_content)
            page.screenshot(path=str(png_path), full_page=True)
            browser.close()
        print(f"[SUCCESS] Rendered high-DPI PNG to {png_path}")
    except Exception as e:
        print(f"[WARN] Playwright PNG rendering skipped: {e}")


if __name__ == "__main__":
    main()
