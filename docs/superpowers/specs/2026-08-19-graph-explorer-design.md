# Graph Explorer — Design Spec

**Date:** 2026-08-19
**Status:** Draft
**Owner:** Claude Code (superpowers:brainstorming)

## 1. Goal

Add a fun, interactive graph visualization to the **Explore** sidebar group so users can visually navigate Prasad Rane's career knowledge graph — the Microsoft GraphRAG entities, relationships, and communities extracted from `input/MASTER_RESUME.txt` and `input/03-Story-Bank.txt`.

Concurrently, delete the **LinkedIn Optimizer** view end-to-end (no longer needed).

### Success criteria

- New "Graph" tab under EXPLORE sidebar group
- Renders Microsoft GraphRAG content graph: 252 entities, 378 relationships, 35 communities
- Default view: 35 community meta-nodes; click to bloom member entities
- Click entity → highlight neighborhood + details panel (description, degree, frequency, community)
- Search + entity-type filter
- "Ask Me about this" button seeds the chat tab
- LinkedIn view fully removed (UI, controller, CSS, backend endpoint)
- Works locally; on Vercel shows a friendly disabled state

## 2. Non-Goals

- Visualizing the graphify code graph (`graphify-out/graph.json`) — explicitly out of scope. That graph contains codebase symbols, not resume content.
- Live re-indexing from the UI (re-indexing stays a CLI operation: `graphrag index --root .`)
- Cross-repo / multi-graph comparison

## 3. Decisions Locked (via brainstorming)

| Decision | Choice | Rationale |
|---|---|---|
| Data source | Microsoft GraphRAG content graph (`output/*.parquet`) | Contains resume/skills/stories entities, not codebase symbols |
| Interaction model | Full custom explorer, Material 3 integrated | User-requested "fun and interactive" |
| Layout strategy | Tiered by community (meta-nodes → bloom to entities) | 35 communities is digestible default; entities bloom on demand |
| Renderer | Cytoscape.js | Compound-node native (maps 1:1 to communities→entities); fcose layout; CSS-style selectors integrate with M3 tokens |
| JSON source | Backend API with in-memory cache | Auto-fresh after re-index; ~100ms cold-start cost is negligible for 252 entities |
| Vercel support | Local-only for v1; Vercel tab shows friendly disabled state | `output/` is gitignored; adding serverless support is a follow-up |

## 4. Architecture

```
┌──────────────────────────────────────────────────────────────┐
│ Browser                                                       │
│  EXPLORE sidebar group:                                       │
│    • Ask Me  (existing chatbot)                               │
│    • Graph   (NEW)                                            │
│                                                               │
│  Graph tab UI:                                                │
│    [🔍 search] [All ▾ ORG EVENT GEO PERSON] [Collapse all]   │
│    ┌────────────────────────────────────────────────────┐    │
│    │ Cytoscape.js canvas                                 │    │
│    │   Default: 35 community meta-nodes                  │    │
│    │   Click community → bloom member entities           │    │
│    │   Click entity → highlight neighbors                │    │
│    └────────────────────────────────────────────────────┘    │
│    ┌────────────────────────────────────────────────────┐    │
│    │ Details panel (right / bottom-sheet on mobile)      │    │
│    │   • Title · Type chip · Community                   │    │
│    │   • Description (rich text)                         │    │
│    │   • Stats: degree, frequency                        │    │
│    │   • [Ask Me about this] → seeds chat tab            │    │
│    └────────────────────────────────────────────────────┘    │
│    Freshness: "252 entities · 35 communities · 2026-08-19"    │
│                          │ fetch                              │
└──────────────────────────┼────────────────────────────────────┘
                           │  GET /api/graph/explore
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ FastAPI (src/web/app.py → src/shared/api_routes.py)           │
│   └─ src/shared/graph_controller.py  (NEW)                   │
│        • reads output/{entities,relationships,communities}   │
│        • builds Cytoscape JSON (parents = communities)       │
│        • caches in module-level var keyed off parquet mtime  │
│        • returns { freshness, elements: { nodes, edges } }   │
│                                                              │
│   output/*.parquet  (Microsoft GraphRAG — already exists)    │
└──────────────────────────────────────────────────────────────┘
```

## 5. Backend: `GET /api/graph/explore`

### New file: `src/shared/graph_controller.py`

```python
# Module-level cache (mirrors static_graph_reader.py pattern)
_cache: Optional[dict] = None
_cache_key: Optional[float] = None   # max mtime of the 3 parquets

def get_explorer_payload() -> dict:
    """Read parquets, build Cytoscape JSON, cache until files change."""
    global _cache, _cache_key
    mtime = max(p.stat().st_mtime for p in PARQUET_PATHS)
    if _cache is not None and _cache_key == mtime:
        return _cache
    entities   = pd.read_parquet(ENTITIES_PATH)
    rels       = pd.read_parquet(RELS_PATH)
    comm_units = pd.read_parquet(COMMUNITIES_PATH)   # entity → community mapping
    payload = _build_payload(entities, rels, comm_units)
    _cache, _cache_key = payload, mtime
    return payload
```

### Response shape

```jsonc
{
  "freshness": {
    "built_at": "2026-08-19T14:22:01Z",
    "entity_count": 252,
    "relationship_count": 378,
    "community_count": 35
  },
  "elements": {
    "nodes": [
      // 35 community meta-nodes
      { "data": { "id": "c:42", "kind": "community",
                  "label": "Cloud & AI Architecture",
                  "level": 2, "rank": 87, "member_count": 12,
                  "summary": "Covers AWS ECS Fargate, Bedrock, Kafka governance…" }},
      // 252 entity nodes — parented to their community
      { "data": { "id": "e:Rocket Mortgage", "kind": "entity",
                  "entity_type": "ORGANIZATION",
                  "label": "Rocket Mortgage",
                  "description": "Senior Software Engineer role, Jan 2023 – Jul 2025…",
                  "degree": 23, "frequency": 14,
                  "parent": "c:42", "x": 123.4, "y": 567.8 }}
    ],
    "edges": [
      // 378 relationships — entity-to-entity only;
      // community containment uses the `parent` field (Cytoscape built-in)
      { "data": { "id": "r:0", "source": "e:Rocket Mortgage",
                  "target": "e:AWS ECS Fargate",
                  "label": "utilized", "weight": 0.87 }}
    ]
  }
}
```

### Key decisions

| Concern | Choice | Rationale |
|---|---|---|
| Cache invalidation | `max(parquet mtimes)` | No extra bookkeeping; re-index auto-invalidates |
| IDs | Prefixed `c:` / `e:` / `r:` | Avoid collisions between community / entity / edge ID spaces |
| `parent` field on entities | Cytoscape compound-node built-in | Free tiered rendering — no custom layout code for bloom |
| Pre-computed `x`, `y` | Passed through | Preserves GraphRAG's force-directed layout; skips re-sim |
| Community summary | Truncated `community_reports.full_content` | Powers the meta-node tooltip / details preview |
| Entity → community mapping | Read from whichever parquet carries it (verify at impl time) | GraphRAG schema varies by version; may be in `communities.parquet` or `nodes.parquet` |
| Missing parquets | `HTTP 503` + `{ code: "GRAPH_NOT_BUILT", hint: "Run graphrag index --root ." }` | Matches `static_graph_reader.py` fallback philosophy |

### Endpoint registration

Add `GET /api/graph/explore` to `src/shared/api_routes.py` so it's available in both local FastAPI and the Vercel wrapper.

## 6. Frontend: Graph Explorer Tab

### HTML additions (`src/web/static/index.html`)

**Nav button** (in EXPLORE sidebar group, after "Ask Me"):
```html
<button id="nav-graph-btn" class="nav-item" role="tab" aria-selected="false"
        data-tab="graph" title="Knowledge Graph Explorer" data-tooltip="Graph">
    <span class="material-symbols-outlined nav-icon">hub</span>
    <span class="nav-label">Graph</span>
</button>
```

**Tab view** `#graph-view`:
```html
<div id="graph-view" class="tab-view hidden fade-in">
    <section class="m3-card graph-panel">
        <div class="panel-header">
            <h2><span class="material-symbols-outlined header-symbol">hub</span> Knowledge Graph Explorer</h2>
            <p>Visually navigate Prasad's career — employers, skills, technologies, and the stories that connect them.</p>
            <div class="graph-freshness" id="graph-freshness"></div>
        </div>

        <div class="graph-toolbar">
            <div class="graph-search-wrapper">
                <span class="material-symbols-outlined">search</span>
                <input id="graph-search" type="text" placeholder="Search entities…" autocomplete="off">
            </div>
            <div class="graph-type-filters" id="graph-type-filters">
                <button class="graph-chip active" data-type="ALL">All</button>
                <button class="graph-chip" data-type="ORGANIZATION">Organizations</button>
                <button class="graph-chip" data-type="EVENT">Events</button>
                <button class="graph-chip" data-type="GEO">Locations</button>
                <button class="graph-chip" data-type="PERSON">People</button>
            </div>
            <button id="graph-collapse-btn" class="m3-icon-button" title="Collapse all communities">
                <span class="material-symbols-outlined">compress</span>
            </button>
        </div>

        <div id="graph-canvas" class="graph-canvas">
            <div id="graph-loading" class="graph-state">
                <div class="m3-spinner"></div>
                <p>Loading graph…</p>
            </div>
            <div id="graph-error" class="graph-state hidden"></div>
        </div>

        <aside id="graph-details" class="graph-details hidden">
            <button id="graph-details-close" class="m3-icon-button" aria-label="Close">
                <span class="material-symbols-outlined">close</span>
            </button>
            <h3 id="graph-details-title"></h3>
            <div class="graph-details-meta">
                <span id="graph-details-type" class="m3-chip"></span>
                <span id="graph-details-community" class="m3-chip"></span>
            </div>
            <p id="graph-details-description"></p>
            <dl class="graph-details-stats">
                <dt>Connections</dt><dd id="graph-details-degree"></dd>
                <dt>Mentions</dt><dd id="graph-details-frequency"></dd>
            </dl>
            <button id="graph-details-ask" class="m3-button m3-button-tonal">
                <span class="material-symbols-outlined">chat</span>
                <span>Ask Me about this</span>
            </button>
        </aside>
    </section>
</div>
```

### JS controller: `src/web/static/js/controllers/graph_explorer.js`

Responsibilities:
- `init()` — fetch `/api/graph/explore`, build Cytoscape, bind events
- `buildCytoscape(payload)` — preset layout using pre-computed `x,y`; position community meta-nodes at centroid of their members
- **Events:**
  - `tap` community meta-node → dissolve meta-node, bloom children (Cytoscape compound-node expand with fade + re-layout animation)
  - `tap` entity → highlight node + 1-hop neighbors (fade non-neighbors to opacity 0.15); populate details panel
  - `tap` background → reset highlight, close details
  - `mouseover` → show tooltip with label
- `search(q)` — highlight matches, fade non-matches; empty query resets
- `filterByType(type)` — show/hide entities by `entity_type`; communities always visible
- `collapseAll()` → return to 35-community meta-view
- `seedChat(label)` → switch to chat tab with pre-filled query `"Tell me about {label}"`

### Cytoscape init sketch

```js
import cytoscape from 'https://cdn.jsdelivr.net/npm/cytoscape@3.30.0/+esm';

const cy = cytoscape({
  container: document.getElementById('graph-canvas'),
  elements: payload.elements,
  style: GRAPH_STYLE,      // reads M3 tokens via getComputedStyle
  layout: { name: 'preset' },  // use pre-computed x,y for entities
  wheelSensitivity: 0.3,
});
```

## 7. Material 3 Styling

### Tokens integration

Cytoscape styles read from `tokens.css` at init via `getComputedStyle`. This means dark mode is automatic — when the user toggles theme, the next tab reload picks up new colors. (Live theme-swap without reload is a nice-to-have; not in v1.)

```js
const cs = getComputedStyle(document.documentElement);
const GRAPH_STYLE = [
  { selector: 'node[kind="community"]', style: {
      'background-color': cs.getPropertyValue('--md-sys-color-primary'),
      'background-opacity': 0.15,
      'border-width': 2,
      'border-color': cs.getPropertyValue('--md-sys-color-primary'),
      'label': 'data(label)',
      'text-valign': 'center', 'text-halign': 'center',
      'width': 'mapData(member_count, 1, 30, 40, 100)',
      'height': 'mapData(member_count, 1, 30, 40, 100)',
      'shape': 'ellipse',
  }},
  { selector: 'node[kind="entity"]', style: {
      'background-color': 'data(colorByType)',   // computed from entity_type + tokens
      'label': 'data(label)',
      'width': 'mapData(degree, 1, 50, 15, 45)',
      'height': 'mapData(degree, 1, 50, 15, 45)',
      'font-size': '10px',
      'text-valign': 'bottom', 'text-margin-y': 4,
  }},
  { selector: 'edge', style: {
      'width': 'mapData(weight, 0, 1, 1, 4)',
      'line-color': cs.getPropertyValue('--md-sys-color-outline-variant'),
      'target-arrow-shape': 'none',
      'curve-style': 'bezier',
      'opacity': 0.6,
  }},
  { selector: '.faded', style: { 'opacity': 0.15 }},
  { selector: '.selected', style: {
      'border-width': 3,
      'border-color': cs.getPropertyValue('--md-sys-color-primary'),
  }},
];
```

### Entity-type color mapping

| Type | Token | Rationale |
|---|---|---|
| ORGANIZATION | `--md-sys-color-secondary` | Most common (112 entities); calm mid-tone |
| EVENT | `--md-sys-color-tertiary` | Accents; distinct from ORG |
| GEO | `--md-sys-color-error` (or a custom teal if defined) | Small set; stands out |
| PERSON | `--md-sys-color-primary` | Smallest set; hero color for people |

### Responsive layout

- Desktop (≥900px): details panel on right, 320px wide
- Tablet (600-899px): details panel on right, 280px wide
- Mobile (<600px): details panel becomes bottom-sheet (M3 pattern); canvas full-width
- Type-filter chips wrap on narrow screens

### States

- **Loading**: M3 skeleton pulse over canvas area
- **Empty** (no parquets): illustration + message "GraphRAG index not built. Run `graphrag index --root .` to enable."
- **Error**: toast with retry button

## 8. LinkedIn View Deletion

| File | Action |
|---|---|
| `src/web/static/css/views/linkedin.css` | DELETE |
| `src/web/static/styles.css:14` | Remove `@import "./css/views/linkedin.css";` |
| `src/web/static/index.html:55-58` | Remove nav button `#nav-linkedin-btn` |
| `src/web/static/index.html:~516-562` | Remove `#linkedin-view` div |
| `src/web/static/index.html:672-674` | Remove more-sheet item |
| `src/web/static/js/controllers/linkedin.js` | DELETE |
| `src/web/static/js/main.js:19,40,71` | Remove import, map entry, registration |
| `src/web/static/js/controllers/navigation.js` | Remove `navLinkedinBtn`, `linkedinView`, listener, view map, button map, button array entry |
| Backend `/api/linkedin-profile` | Locate (likely `app.py` or `shared/api_routes.py`) and remove |

## 9. Error Handling

| Scenario | Backend | Frontend |
|---|---|---|
| Parquet files missing | 503 `{ code: "GRAPH_NOT_BUILT", hint }` | Empty state with instructions |
| Parquet parse failure | 500 + log error | Toast "Failed to load graph data" + retry |
| Empty graph | 200 with empty elements | "No entities found" empty state |
| Cytoscape CDN fail | — | Fallback: tabular list view |
| Network error on fetch | — | Retry button |
| Vercel (no parquets) | 503 `GRAPH_NOT_BUILT` | "Available locally. Run `graphrag index` to enable." |

## 10. Testing Strategy

### Unit tests — `tests/test_graph_controller.py`

- Mock parquet reads with tiny fixtures (5 entities, 3 relationships, 1 community)
- Assert payload shape: `freshness`, `elements.nodes`, `elements.edges`
- Assert community meta-node has correct `member_count`
- Assert entity has correct `parent` reference
- Assert cache hit when mtime unchanged, miss when mtime changes
- Assert missing parquet → raises `HTTPException(503)`

### Integration test

- Hit `/api/graph/explore` against real parquets (skip if files missing)
- Assert counts: 252 entities, 378 relationships, 35 communities (with tolerance for drift)

### E2E (Playwright)

- Open Graph tab
- Assert canvas populated (Cytoscape container has child nodes)
- Click first community → assert entities appear
- Click first entity → assert details panel populated
- Search "Rocket" → assert filter narrows to matches
- Click "Ask Me about this" → assert chat tab opens with pre-filled query

### LinkedIn cleanup verification

- Assert nav controller no longer references `linkedin`
- Assert `main.js` no longer imports LinkedInController
- Assert `styles.css` no longer imports linkedin.css
- Assert `/api/linkedin-profile` returns 404 (or doesn't exist)

## 11. File Map (Summary)

### New files

| File | Purpose |
|---|---|
| `src/shared/graph_controller.py` | Parquet reader, Cytoscape JSON builder, cache |
| `src/web/static/js/controllers/graph_explorer.js` | Cytoscape init, interactions, details panel |
| `src/web/static/css/views/graph_explorer.css` | M3-styled layout for Graph tab |
| `tests/test_graph_controller.py` | Unit tests for backend |

### Modified files

| File | Change |
|---|---|
| `src/shared/api_routes.py` | Add `GET /api/graph/explore` |
| `src/web/static/index.html` | Add nav button + graph-view + remove linkedin-view |
| `src/web/static/js/main.js` | Register GraphExplorerController + remove LinkedInController |
| `src/web/static/js/controllers/navigation.js` | Wire new tab + remove linkedin refs |
| `src/web/static/styles.css` | Add import for graph_explorer.css + remove linkedin.css import |

### Deleted files

| File | Purpose |
|---|---|
| `src/web/static/css/views/linkedin.css` | LinkedIn view styles |
| `src/web/static/js/controllers/linkedin.js` | LinkedIn view controller |

## 12. Implementation Order

1. **Backend**: `graph_controller.py` + endpoint + tests
2. **Frontend scaffold**: HTML tab + nav wiring + empty-state handling
3. **Cytoscape integration**: fetch payload, render, preset layout
4. **Interactions**: bloom, select, search, filter, collapse
5. **Details panel**: populate, "Ask Me about this" → chat integration
6. **LinkedIn cleanup**: delete files, remove refs, verify backend endpoint gone
7. **Polish**: responsive layout, dark mode verification, loading/error states
8. **E2E tests**: Playwright scenarios

## 13. Out of Scope (Follow-ups)

- Vercel deployment support (requires committing `static/data/graph_explore.json` snapshot)
- Live theme-swap without reload (requires Cytoscape style reapply on theme toggle)
- Force-directed re-layout on bloom (v1 uses preset layout; bloom is just un-hiding children)
- Path-finding between two entities (A* on Cytoscape)
- Node grouping beyond community (e.g. by entity_type clusters)
- Export to PNG / shareable URL

## 14. Addendum — Constellation Redesign (2026-08-19)

Playwright review of the shipped v1 found the default view rendered as a **blank
canvas**: Cytoscape compound parents derive their position from children, so the
radial positions assigned to community meta-nodes were silently ignored (all
entities sat at 0,0), and the post-init `fit()` raced the async Cytoscape CDN
import. The redesign keeps the bloom interaction model and fixes/polishes:

- **Layout**: entities are positioned in deterministic phyllotaxis clusters per
  community (largest community centered); parents auto-center on children.
  Hardened fit (sync + `layoutstop` + 250ms re-fit).
- **Aggregate edges**: community↔community relationship counts render in the
  meta view; hidden while an endpoint is expanded, a type filter is active, or
  a search query is live (`_refreshAggEdges`).
- **Palette**: new tokens `--graph-color-person/org/event/geo` in
  `tokens.css` (GEO drops the alarm red). Type chips carry matching color dots
  and double as the legend.
- **Chrome**: hover tooltip (`#graph-tooltip`), zoom/fit cluster
  (`#graph-zoom-in/out/fit`), first-run hint pill (`#graph-hint`), dotted
  canvas backdrop, bloom viewport animation, bloom radius scaled to child
  count, zoom-conditional community labels (`.zfar` below zoom 0.55).
- **Sizing/labels** use real child counts (parquet `member_count`
  double-counts entities shared across communities).

Files touched: `graph_explorer.js`, `graph_explorer.css`, `tokens.css`,
`index.html`, `tests/test_web_static_structure.py` (also fixed stale LinkedIn
expectations).

## 15. Addendum — v3 Obsidian-style redesign (2026-08-19)

User feedback on v2: communities showed placeholder numbers, and the meta
view felt too basic. v3 flips the model to a full-graph constellation:

- **Names**: community labels now come from `community_reports.title`
  (fallback: first `# heading` of `full_content`; for the two report-less
  communities, a name derived from their two highest-degree members).
- **All entities visible from first paint**, placed by the phyllotaxis seed
  and relaxed with a tiny deterministic force pass (intra-cluster repulsion +
  edge springs + centroid gravity, 90 iterations) in `_assignPositions`.
  Built-in `cose` was evaluated and rejected (degenerate slabs/lines on this
  compound graph); `cose-bilkent` crashed via CDN ESM.
- **Communities render as translucent rounded panels** (compound parents)
  titled with their real names; click → focus mode (fit + fade rest).
- **Fade-based emphasis** replaces show/hide for search, type filters, and
  focus (`_applyState`); aggregate meta-edges removed (real edges now
  connect clusters). Collapse button repurposed as **Reset view**.
- Cytoscape gotchas learned: `preset` layout runs synchronously in the
  constructor (register `layoutstop` handlers accordingly), and Cytoscape has
  no `:hover` selector or `cursor` style (use mouseover + class).
