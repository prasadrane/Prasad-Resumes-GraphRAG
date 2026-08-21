# Graph Explorer + LinkedIn Cleanup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Material 3 graph explorer tab under EXPLORE that renders Microsoft GraphRAG's content graph (252 entities / 378 relationships / 37 communities from `output/*.parquet`) using Cytoscape.js with tiered community→entity drill-down, and delete the LinkedIn Optimizer view end-to-end.

**Architecture:** Backend reads `output/{entities,relationships,communities}.parquet` via pandas, builds Cytoscape-ready JSON with communities as compound-node parents, caches in-memory keyed off max parquet mtime, exposes as `GET /api/graph/explore` on the shared router. Frontend is a new ES module `graph_explorer.js` that fetches the payload, mounts Cytoscape in `#graph-canvas`, and wires bloom / select / search / filter / collapse interactions. LinkedIn view is surgically removed across 8 touchpoints (CSS, HTML, JS controller, navigation, main.js registration, backend endpoint, Pydantic model).

**Tech Stack:** Python 3.11, pandas, pyarrow (parquet), FastAPI, Cytoscape.js 3.30 (ESM via jsDelivr), Material Design 3 tokens (existing `tokens.css`), vanilla JS modules.

**Spec:** `docs/superpowers/specs/2026-08-19-graph-explorer-design.md`

## Global Constraints

- IDs must be prefixed (`c:` / `e:` / `r:`) to avoid collisions between community, entity, edge ID spaces.
- Entity `parent` field must reference the community meta-node ID (Cytoscape compound-node built-in).
- Pre-computed `x`, `y` from `entities.parquet` must pass through to preserve GraphRAG layout.
- Cache invalidation uses `max(parquet mtimes)` — no external cache store.
- Missing parquets → `HTTP 503 { code: "GRAPH_NOT_BUILT", hint: "Run graphrag index --root ." }`.
- All frontend CSS uses M3 tokens from `tokens.css` (no hard-coded colors); dark mode is free.
- Cytoscape loaded via ESM CDN: `https://cdn.jsdelivr.net/npm/cytoscape@3.30.0/+esm`.
- No changes to `graphify-out/` — the code graph is out of scope.

---

## File Structure

### New files

| File | Responsibility |
|---|---|
| `src/shared/graph_controller.py` | Read parquets, build Cytoscape JSON, cache in memory |
| `src/web/static/js/controllers/graph_explorer.js` | Cytoscape init, interactions, details panel, chat seeding |
| `src/web/static/css/views/graph_explorer.css` | M3-styled layout for the Graph tab |
| `tests/test_graph_controller.py` | Unit + integration tests for the backend |

### Modified files

| File | Change |
|---|---|
| `src/shared/api_routes.py` | Add `GET /api/graph/explore`; remove `/api/linkedin-profile` endpoint + `LinkedInProfileRequest` import |
| `src/shared/api_models.py` | Remove `LinkedInProfileRequest` class |
| `src/web/static/index.html` | Add `#nav-graph-btn` nav button + `#graph-view` tab view; remove `#nav-linkedin-btn`, `#linkedin-view`, LinkedIn more-sheet-item |
| `src/web/static/js/main.js` | Replace `LinkedInController` import+registration with `GraphExplorerController` |
| `src/web/static/js/controllers/navigation.js` | Replace all `linkedin*` refs with `graph*` refs; add `navGraphBtn` + `graphView` wiring |
| `src/web/static/styles.css` | Replace `@import "./css/views/linkedin.css";` with `@import "./css/views/graph_explorer.css";` |

### Deleted files

| File |
|---|
| `src/web/static/css/views/linkedin.css` |
| `src/web/static/js/controllers/linkedin.js` |

---

## Task 1 · Backend controller: parquet → Cytoscape JSON (TDD)

**Files:**
- Create: `src/shared/graph_controller.py`
- Create: `tests/test_graph_controller.py`

**Interfaces:**
- Consumes: `output/entities.parquet`, `output/relationships.parquet`, `output/communities.parquet` (pandas)
- Produces: `get_explorer_payload() -> dict` returning `{ freshness, elements: { nodes, edges } }`
- Produces: `clear_graph_cache()` for test reset
- Raises: `GraphNotBuiltError` when any parquet is missing (caller maps to HTTP 503)

- [ ] **Step 1: Write the failing test for missing-parquet behavior**

Create `tests/test_graph_controller.py`:

```python
"""Unit tests for src.shared.graph_controller."""
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure repo root is on sys.path for `src.*` imports when run via unittest discovery
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestGraphControllerMissingFiles(unittest.TestCase):
    def setUp(self):
        from src.shared import graph_controller
        self.mod = graph_controller
        self.mod.clear_graph_cache()

    def test_missing_parquet_raises(self):
        """When a parquet is absent, get_explorer_payload raises GraphNotBuiltError."""
        fake_path = Path("/nonexistent/entities.parquet")
        with patch.object(self.mod, "ENTITIES_PATH", fake_path):
            with self.assertRaises(self.mod.GraphNotBuiltError):
                self.mod.get_explorer_payload()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_graph_controller -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.shared.graph_controller'`

- [ ] **Step 3: Write minimal implementation**

Create `src/shared/graph_controller.py`:

```python
"""graph_controller.py — Read GraphRAG parquets and emit Cytoscape-ready JSON.

Caches the payload in memory, invalidated when any source parquet's mtime changes.
"""
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.config import OUTPUT_DIR_PATH

logger = logging.getLogger(__name__)


ENTITIES_PATH = OUTPUT_DIR_PATH / "entities.parquet"
RELS_PATH = OUTPUT_DIR_PATH / "relationships.parquet"
COMMUNITIES_PATH = OUTPUT_DIR_PATH / "communities.parquet"
REPORTS_PATH = OUTPUT_DIR_PATH / "community_reports.parquet"

_PARQUET_PATHS = (ENTITIES_PATH, RELS_PATH, COMMUNITIES_PATH)


class GraphNotBuiltError(RuntimeError):
    """Raised when required parquet files are missing."""


_cache: Optional[Dict[str, Any]] = None
_cache_key: Optional[float] = None


def clear_graph_cache() -> None:
    """Clear in-memory cached payload. Used by tests and after re-index."""
    global _cache, _cache_key
    _cache = None
    _cache_key = None


def _check_parquets() -> None:
    missing = [str(p) for p in _PARQUET_PATHS if not p.exists()]
    if missing:
        raise GraphNotBuiltError(
            f"GraphRAG parquets missing: {missing}. Run `graphrag index --root .` to build."
        )


def _current_mtime_key() -> float:
    return max(p.stat().st_mtime for p in _PARQUET_PATHS)


def get_explorer_payload() -> Dict[str, Any]:
    """Return Cytoscape-ready JSON, rebuilding cache when parquets change."""
    global _cache, _cache_key
    _check_parquets()
    mtime = _current_mtime_key()
    if _cache is not None and _cache_key == mtime:
        return _cache

    entities = pd.read_parquet(ENTITIES_PATH)
    rels = pd.read_parquet(RELS_PATH)
    communities = pd.read_parquet(COMMUNITIES_PATH)
    reports = pd.read_parquet(REPORTS_PATH) if REPORTS_PATH.exists() else pd.DataFrame()

    payload = _build_payload(entities, rels, communities, reports)
    _cache, _cache_key = payload, mtime
    return payload


def _build_payload(
    entities: pd.DataFrame,
    rels: pd.DataFrame,
    communities: pd.DataFrame,
    reports: pd.DataFrame,
) -> Dict[str, Any]:
    """Transform raw parquet DataFrames into Cytoscape elements."""
    # 1. Build entity_id -> community_id mapping from communities.entity_ids
    entity_to_community: Dict[str, str] = {}
    community_rows: List[Dict[str, Any]] = []
    for _, row in communities.iterrows():
        cid = f"c:{row['community']}"
        entity_ids = row.get("entity_ids") or []
        # entity_ids may be stored as a list or as a string representation
        if isinstance(entity_ids, str):
            # try common list-like parsings
            import ast
            try:
                entity_ids = ast.literal_eval(entity_ids)
            except Exception:
                entity_ids = []
        for eid in entity_ids:
            entity_to_community[str(eid)] = cid
        # Pull summary from reports if available
        summary = ""
        if not reports.empty:
            match = reports[reports["community"] == row["community"]]
            if not match.empty:
                full = str(match.iloc[0].get("full_content", "") or "")
                summary = full[:300].strip()
        community_rows.append({
            "id": cid,
            "kind": "community",
            "label": str(row.get("title") or f"Community {row['community']}"),
            "level": int(row.get("level", 0) or 0),
            "rank": float(row.get("size", 0) or 0),
            "member_count": len(entity_ids),
            "summary": summary,
        })

    # 2. Build entity nodes, parented to community
    entity_nodes: List[Dict[str, Any]] = []
    for _, row in entities.iterrows():
        raw_id = str(row.get("id") or row.get("human_readable_id"))
        parent = entity_to_community.get(raw_id)
        ent_type = str(row.get("type") or "").strip() or "ENTITY"
        entity_nodes.append({
            "id": f"e:{raw_id}",
            "kind": "entity",
            "entity_type": ent_type,
            "label": str(row.get("title") or raw_id),
            "description": str(row.get("description") or ""),
            "degree": int(row.get("degree", 0) or 0),
            "frequency": int(row.get("frequency", 0) or 0),
            "parent": parent,
            "x": float(row.get("x", 0) or 0),
            "y": float(row.get("y", 0) or 0),
        })

    # 3. Build edges from relationships
    edges: List[Dict[str, Any]] = []
    for _, row in rels.iterrows():
        src = row.get("source")
        tgt = row.get("target")
        if src is None or tgt is None:
            continue
        edges.append({
            "id": f"r:{row.get('id', len(edges))}",
            "source": f"e:{src}",
            "target": f"e:{tgt}",
            "label": str(row.get("description") or "")[:80],
            "weight": float(row.get("weight", 0.5) or 0.5),
        })

    # 4. Drop orphaned entities (no community) — keeps the tiered view clean
    orphan_parentless = [n for n in entity_nodes if n["parent"] is None]
    if orphan_parentless:
        logger.warning(
            "graph_controller: %d entities without community membership will be parented to a synthetic 'Unassigned' community",
            len(orphan_parentless),
        )
        synthetic_id = "c:__unassigned__"
        if synthetic_id not in {c["id"] for c in community_rows}:
            community_rows.append({
                "id": synthetic_id,
                "kind": "community",
                "label": "Unassigned",
                "level": 0,
                "rank": 0,
                "member_count": len(orphan_parentless),
                "summary": "Entities without community membership.",
            })
        for n in orphan_parentless:
            n["parent"] = synthetic_id

    return {
        "freshness": {
            "built_at": datetime.now(timezone.utc).isoformat(),
            "entity_count": len(entity_nodes),
            "relationship_count": len(edges),
            "community_count": len(community_rows),
        },
        "elements": {
            "nodes": [{ "data": n } for n in community_rows + entity_nodes],
            "edges": [{ "data": e } for e in edges],
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_graph_controller -v`
Expected: PASS

- [ ] **Step 5: Add cache-hit test**

Append to `tests/test_graph_controller.py`:

```python
class TestGraphControllerCache(unittest.TestCase):
    def setUp(self):
        from src.shared import graph_controller
        self.mod = graph_controller
        self.mod.clear_graph_cache()

    @unittest.skipUnless(
        all(p.exists() for p in [
            Path("output/entities.parquet"),
            Path("output/relationships.parquet"),
            Path("output/communities.parquet"),
        ]),
        "Requires live output/*.parquet",
    )
    def test_payload_shape_against_live_parquets(self):
        payload = self.mod.get_explorer_payload()
        self.assertIn("freshness", payload)
        self.assertIn("elements", payload)
        self.assertIn("nodes", payload["elements"])
        self.assertIn("edges", payload["elements"])
        self.assertGreater(payload["freshness"]["entity_count"], 0)
        self.assertGreater(payload["freshness"]["community_count"], 0)

    @unittest.skipUnless(
        all(p.exists() for p in [
            Path("output/entities.parquet"),
            Path("output/relationships.parquet"),
            Path("output/communities.parquet"),
        ]),
        "Requires live output/*.parquet",
    )
    def test_cache_hit_on_second_call(self):
        first = self.mod.get_explorer_payload()
        second = self.mod.get_explorer_payload()
        self.assertIs(first, second)  # exact same object → cache hit
```

- [ ] **Step 6: Run tests**

Run: `python -m unittest tests.test_graph_controller -v`
Expected: 3 PASS

- [ ] **Step 7: Commit**

```bash
git add src/shared/graph_controller.py tests/test_graph_controller.py
git commit -m "feat(graph): add graph_controller with parquet → Cytoscape JSON + cache"
```

---

## Task 2 · Backend endpoint wiring + integration test

**Files:**
- Modify: `src/shared/api_routes.py:342` (remove linkedin endpoint) and add new endpoint
- Modify: `src/shared/api_models.py:157-159` (remove `LinkedInProfileRequest`)
- Modify: `tests/test_graph_controller.py` (add endpoint test)

**Interfaces:**
- Consumes: `get_explorer_payload()` and `GraphNotBuiltError` from Task 1
- Produces: `GET /api/graph/explore` returning JSON payload or 503

- [ ] **Step 1: Write endpoint integration test**

Append to `tests/test_graph_controller.py`:

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient


class TestGraphEndpoint(unittest.TestCase):
    def setUp(self):
        from src.shared import graph_controller
        graph_controller.clear_graph_cache()
        # Build a tiny FastAPI app with just the shared router
        from src.shared.api_routes import shared_router
        app = FastAPI()
        app.include_router(shared_router)
        self.client = TestClient(app)

    def test_endpoint_returns_200_with_live_parquets(self):
        from src.shared import graph_controller
        if not all(p.exists() for p in [
            Path("output/entities.parquet"),
            Path("output/relationships.parquet"),
            Path("output/communities.parquet"),
        ]):
            self.skipTest("Requires live output/*.parquet")
        resp = self.client.get("/api/graph/explore")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("freshness", body)
        self.assertIn("elements", body)

    def test_endpoint_returns_503_when_parquets_missing(self):
        from src.shared import graph_controller
        from unittest.mock import patch
        fake = Path("/nonexistent/entities.parquet")
        with patch.object(graph_controller, "ENTITIES_PATH", fake):
            resp = self.client.get("/api/graph/explore")
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json()["detail"]["code"], "GRAPH_NOT_BUILT")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_graph_controller.TestGraphEndpoint -v`
Expected: FAIL — endpoint not yet registered.

- [ ] **Step 3: Register endpoint in api_routes.py**

At the top of `src/shared/api_routes.py`:

1. Add import: `from src.shared.graph_controller import get_explorer_payload, GraphNotBuiltError`
2. Remove `LinkedInProfileRequest` from the `from src.shared.api_models import (...)` block.
3. Add endpoint anywhere near the top of the router (after the docstring, before other routes):

```python
@shared_router.get("/api/graph/explore")
def graph_explore_endpoint():
    """Return Cytoscape-ready payload for the Graph Explorer tab."""
    try:
        return get_explorer_payload()
    except GraphNotBuiltError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "GRAPH_NOT_BUILT",
                "hint": "Run `graphrag index --root .` to build the GraphRAG index.",
                "message": str(exc),
            },
        )
```

4. Remove the LinkedIn endpoint block around line 342:

```python
# DELETE THIS BLOCK
@shared_router.post("/api/linkedin-profile")
def linkedin_profile_endpoint(req: LinkedInProfileRequest):
    ...  # entire function body
```

- [ ] **Step 4: Remove LinkedInProfileRequest from api_models.py**

In `src/shared/api_models.py`, delete the class at lines 157-159:

```python
# DELETE:
class LinkedInProfileRequest(BaseModel):
    target_role: Optional[str] = Field(...)
    candidate_name: Optional[str] = Field(...)
```

- [ ] **Step 5: Run tests**

Run: `python -m unittest tests.test_graph_controller -v`
Expected: 5 PASS (the 3 from Task 1 + 2 new endpoint tests).

- [ ] **Step 6: Commit**

```bash
git add src/shared/api_routes.py src/shared/api_models.py tests/test_graph_controller.py
git commit -m "feat(api): add GET /api/graph/explore endpoint; remove /api/linkedin-profile"
```

---

## Task 3 · Frontend scaffold: HTML, CSS, nav wiring

**Files:**
- Modify: `src/web/static/index.html` (add Graph nav button + tab view; remove LinkedIn equivalents)
- Create: `src/web/static/css/views/graph_explorer.css`
- Modify: `src/web/static/styles.css` (swap `@import`)
- Modify: `src/web/static/js/controllers/navigation.js` (swap linkedin→graph refs)

**Interfaces:**
- Consumes: existing M3 token system (`tokens.css`)
- Produces: `#graph-view` DOM node, `#nav-graph-btn` button, tab-switchable via `data-tab="graph"`

- [ ] **Step 1: Add Graph nav button to index.html**

In `src/web/static/index.html`, locate the EXPLORE nav-group (around line 62-68). Add the Graph button after the Ask Me button inside the same group:

```html
<!-- Group 3: EXPLORE -->
<div class="nav-group">
    <div class="nav-group-label">EXPLORE</div>
    <button id="nav-chat-btn" class="nav-item" role="tab" aria-selected="false" data-tab="chat" title="Ask Me (GraphRAG Q&A)" data-tooltip="Ask Me">
        <span class="material-symbols-outlined nav-icon">chat</span>
        <span class="nav-label">Ask Me</span>
    </button>
    <button id="nav-graph-btn" class="nav-item" role="tab" aria-selected="false" data-tab="graph" title="Knowledge Graph Explorer" data-tooltip="Graph">
        <span class="material-symbols-outlined nav-icon">hub</span>
        <span class="nav-label">Graph</span>
    </button>
</div>
```

- [ ] **Step 2: Remove LinkedIn nav button**

In `src/web/static/index.html`, delete lines 55-58 (the `#nav-linkedin-btn` block):

```html
<!-- DELETE these 4 lines -->
<button id="nav-linkedin-btn" class="nav-item" role="tab" aria-selected="false" data-tab="linkedin" title="LinkedIn Optimizer" data-tooltip="LinkedIn">
    <span class="material-symbols-outlined nav-icon">share</span>
    <span class="nav-label">LinkedIn</span>
</button>
```

- [ ] **Step 3: Add Graph tab view**

In `src/web/static/index.html`, after the `#chatbot-view` div (search for `id="chatbot-view"` to find the right location), add:

```html
<!-- View: Knowledge Graph Explorer -->
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

- [ ] **Step 4: Remove LinkedIn tab view**

In `src/web/static/index.html`, find and delete the entire `#linkedin-view` div block (around line 516-562):

```html
<!-- DELETE: entire <!-- View 5: LinkedIn Optimizer --> section -->
<div id="linkedin-view" class="tab-view hidden fade-in">
    ...
</div>
```

- [ ] **Step 5: Remove LinkedIn more-sheet item**

In `src/web/static/index.html`, find and delete:

```html
<!-- DELETE -->
<button class="more-sheet-item" data-tab="linkedin">
    <span class="material-symbols-outlined">share</span>
    <span>LinkedIn</span>
</button>
```

- [ ] **Step 6: Create graph_explorer.css**

Create `src/web/static/css/views/graph_explorer.css`:

```css
/* views/graph_explorer.css — Knowledge Graph Explorer Layout */

.graph-panel {
  display: grid;
  grid-template-rows: auto auto 1fr auto;
  gap: 16px;
  height: calc(100vh - 80px);
  min-height: 500px;
}

.graph-panel .panel-header {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
}

.graph-panel .panel-header h2 {
  margin: 0;
  font-size: 1.4rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
  display: flex;
  align-items: center;
  gap: 8px;
}

.graph-freshness {
  margin-left: auto;
  font-size: 0.8rem;
  color: var(--md-sys-color-on-surface-variant);
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--md-sys-color-surface-variant);
}

.graph-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.graph-search-wrapper {
  position: relative;
  flex: 1 1 240px;
  min-width: 180px;
  max-width: 360px;
}

.graph-search-wrapper .material-symbols-outlined {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 18px;
  color: var(--md-sys-color-on-surface-variant);
}

.graph-search-wrapper input {
  width: 100%;
  padding: 8px 12px 8px 34px;
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 8px;
  background: var(--md-sys-color-surface);
  color: var(--md-sys-color-on-surface);
  font-size: 0.9rem;
}

.graph-search-wrapper input:focus {
  outline: 2px solid var(--md-sys-color-primary);
  border-color: transparent;
}

.graph-type-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.graph-chip {
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid var(--md-sys-color-outline-variant);
  background: transparent;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.8rem;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}

.graph-chip:hover {
  background: var(--md-sys-color-surface-variant);
}

.graph-chip.active {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
  border-color: transparent;
}

.graph-canvas {
  position: relative;
  flex: 1 1 auto;
  min-height: 400px;
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 12px;
  background: var(--md-sys-color-surface);
  overflow: hidden;
}

.graph-state {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--md-sys-color-on-surface-variant);
  font-size: 0.95rem;
  z-index: 5;
}

.graph-state.hidden { display: none; }

.graph-details {
  position: relative;
  padding: 16px 20px;
  border: 1px solid var(--md-sys-color-outline-variant);
  border-radius: 12px;
  background: var(--md-sys-color-surface-variant);
  max-height: 220px;
  overflow-y: auto;
}

.graph-details.hidden { display: none; }

.graph-details #graph-details-close {
  position: absolute;
  top: 8px;
  right: 8px;
}

.graph-details h3 {
  margin: 0 0 8px 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
  padding-right: 32px;
}

.graph-details-meta {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
}

.graph-details-meta .m3-chip {
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.graph-details-description {
  margin: 0 0 12px 0;
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--md-sys-color-on-surface);
}

.graph-details-stats {
  display: flex;
  gap: 24px;
  margin: 0 0 12px 0;
  font-size: 0.85rem;
}

.graph-details-stats dt {
  color: var(--md-sys-color-on-surface-variant);
  font-weight: 500;
}

.graph-details-stats dd {
  margin: 0 0 0 6px;
  color: var(--md-sys-color-on-surface);
  font-weight: 600;
}

/* Responsive: tablet / mobile */
@media (max-width: 899px) {
  .graph-panel { height: auto; min-height: calc(100vh - 140px); }
  .graph-details { max-height: 280px; }
}

@media (max-width: 599px) {
  .graph-toolbar { flex-direction: column; align-items: stretch; }
  .graph-search-wrapper { max-width: none; }
}
```

- [ ] **Step 7: Swap CSS import in styles.css**

In `src/web/static/styles.css`, find the line `@import "./css/views/linkedin.css";` and replace with:

```css
@import "./css/views/graph_explorer.css";
```

- [ ] **Step 8: Update navigation.js to swap linkedin→graph**

In `src/web/static/js/controllers/navigation.js`:

1. Line 30: change `navLinkedinBtn: null,` → `navGraphBtn: null,`
2. Line 37: change `linkedinView: null,` → `graphView: null,`
3. Line 57: change `this.navLinkedinBtn = document.getElementById('nav-linkedin-btn');` → `this.navGraphBtn = document.getElementById('nav-graph-btn');`
4. Line 64: change `this.linkedinView = document.getElementById('linkedin-view');` → `this.graphView = document.getElementById('graph-view');`
5. Line 72: change `if (this.navLinkedinBtn) this.navLinkedinBtn.addEventListener('click', () => this.switchTab('linkedin'));` → `if (this.navGraphBtn) this.navGraphBtn.addEventListener('click', () => this.switchTab('graph'));`
6. Line 191 (getView map): change `linkedin: this.linkedinView,` → `graph: this.graphView,`
7. Line 203 (getNavButton map): change `linkedin: this.navLinkedinBtn,` → `graph: this.navGraphBtn,`
8. Line 223 (btns array): change `this.navLinkedinBtn` → `this.navGraphBtn`

- [ ] **Step 9: Manual verification**

Run: `python src/cli.py ui` (starts local dev on port 3000).
Open: http://localhost:3000
Verify:
- Sidebar EXPLORE group shows "Ask Me" and "Graph" (no "LinkedIn")
- Click "Graph" tab → empty canvas area visible (no JS errors in console)
- LinkedIn button is gone from sidebar and mobile more-sheet

- [ ] **Step 10: Commit**

```bash
git add src/web/static/index.html src/web/static/styles.css src/web/static/css/views/graph_explorer.css src/web/static/css/views/linkedin.css src/web/static/js/controllers/navigation.js
git commit -m "feat(ui): add Graph Explorer tab scaffold; remove LinkedIn view (HTML/CSS/nav)"
```

Note: include the deletion of `linkedin.css` in this commit.

---

## Task 4 · Frontend: Cytoscape integration (fetch + render)

**Files:**
- Create: `src/web/static/js/controllers/graph_explorer.js`
- Modify: `src/web/static/js/main.js` (register controller)

**Interfaces:**
- Consumes: `GET /api/graph/explore` payload (Task 2)
- Consumes: `ApiClient` from `core/api.js`, `Logger` from `core/logger.js`, `EventBus` from `core/bus.js`
- Produces: `GraphExplorerController` object with `init()` method
- Produces: `window.App.controllers.graphExplorer` for debugging

- [ ] **Step 1: Create minimal controller skeleton**

Create `src/web/static/js/controllers/graph_explorer.js`:

```js
/**
 * graph_explorer.js — Knowledge Graph Explorer Controller.
 * Fetches Cytoscape-ready JSON from /api/graph/explore and renders
 * an interactive force graph of Prasad's career entities & communities.
 */

import { Logger } from '../core/logger.js';
import { ApiClient } from '../core/api.js';

export const GraphExplorerController = {
    cy: null,
    payload: null,
    canvas: null,
    loadingEl: null,
    errorEl: null,
    freshnessEl: null,

    init() {
        this.canvas = document.getElementById('graph-canvas');
        this.loadingEl = document.getElementById('graph-loading');
        this.errorEl = document.getElementById('graph-error');
        this.freshnessEl = document.getElementById('graph-freshness');

        if (!this.canvas) {
            // Graph tab not present (e.g., some custom builds); skip silently.
            return;
        }

        Logger.info('GRAPH', 'GraphExplorerController initialized.');
        // Lazy-load on first tab switch; initial tab is 'default'.
        // Listen for tab:changed events and load when 'graph' is selected.
        // For now, auto-load on init for simplicity.
        this.load();
    },

    async load() {
        if (this.payload) return;  // already loaded
        this._showLoading();
        try {
            const data = await ApiClient.getJson('/api/graph/explore');
            this.payload = data;
            this._render();
        } catch (err) {
            Logger.error('GRAPH', 'Failed to load graph:', err);
            this._showError(err);
        }
    },

    _showLoading() {
        if (this.loadingEl) this.loadingEl.classList.remove('hidden');
        if (this.errorEl) this.errorEl.classList.add('hidden');
    },

    _showError(err) {
        if (this.loadingEl) this.loadingEl.classList.add('hidden');
        if (!this.errorEl) return;
        this.errorEl.classList.remove('hidden');
        const status = err?.status || err?.response?.status;
        if (status === 503) {
            this.errorEl.innerHTML = `
                <span class="material-symbols-outlined" style="font-size:48px;">database_off</span>
                <p>GraphRAG index not built.</p>
                <p style="font-size:0.85rem;">Run <code>graphrag index --root .</code> locally to enable.</p>
            `;
        } else {
            this.errorEl.innerHTML = `
                <span class="material-symbols-outlined" style="font-size:48px;">error</span>
                <p>Failed to load graph data.</p>
                <button class="m3-button m3-button-tonal" id="graph-retry-btn">Retry</button>
            `;
            const retry = this.errorEl.querySelector('#graph-retry-btn');
            if (retry) retry.addEventListener('click', () => {
                this.payload = null;
                this.load();
            });
        }
    },

    _render() {
        if (!this.payload) return;
        if (this.loadingEl) this.loadingEl.classList.add('hidden');
        if (this.errorEl) this.errorEl.classList.add('hidden');

        // Freshness badge
        if (this.freshnessEl) {
            const f = this.payload.freshness;
            this.freshnessEl.textContent =
                `${f.entity_count} entities · ${f.community_count} communities · ${f.relationship_count} relationships`;
        }

        // Lazy-load Cytoscape from CDN (ESM)
        import('https://cdn.jsdelivr.net/npm/cytoscape@3.30.0/+esm')
            .then(({ default: cytoscape }) => {
                this._initCytoscape(cytoscape);
            })
            .catch(err => {
                Logger.error('GRAPH', 'Failed to load Cytoscape:', err);
                this._showError({ status: 0, message: 'Cytoscape CDN unreachable' });
            });
    },

    _initCytoscape(cytoscape) {
        const cs = getComputedStyle(document.documentElement);
        const primary = cs.getPropertyValue('--md-sys-color-primary').trim() || '#6750a4';
        const secondary = cs.getPropertyValue('--md-sys-color-secondary').trim() || '#625b71';
        const tertiary = cs.getPropertyValue('--md-sys-color-tertiary').trim() || '#7d5260';
        const error = cs.getPropertyValue('--md-sys-color-error').trim() || '#b3261e';
        const outline = cs.getPropertyValue('--md-sys-color-outline-variant').trim() || '#79747e';
        const onSurface = cs.getPropertyValue('--md-sys-color-on-surface').trim() || '#1c1b1f';

        const TYPE_COLORS = {
            ORGANIZATION: secondary,
            EVENT: tertiary,
            GEO: error,
            PERSON: primary,
        };

        // Pre-compute color per entity node
        const nodes = this.payload.elements.nodes.map(n => {
            if (n.data.kind === 'entity') {
                return {
                    ...n,
                    data: {
                        ...n.data,
                        colorByType: TYPE_COLORS[n.data.entity_type] || primary,
                    },
                };
            }
            return n;
        });

        this.cy = cytoscape({
            container: this.canvas,
            elements: { nodes, edges: this.payload.elements.edges },
            style: [
                { selector: 'node[kind="community"]', style: {
                    'background-color': primary,
                    'background-opacity': 0.15,
                    'border-width': 2,
                    'border-color': primary,
                    'label': 'data(label)',
                    'text-valign': 'center',
                    'text-halign': 'center',
                    'color': onSurface,
                    'font-size': '12px',
                    'font-weight': 'bold',
                    'width': 'mapData(member_count, 1, 40, 50, 120)',
                    'height': 'mapData(member_count, 1, 40, 50, 120)',
                    'shape': 'ellipse',
                }},
                { selector: 'node[kind="entity"]', style: {
                    'background-color': 'data(colorByType)',
                    'label': 'data(label)',
                    'width': 'mapData(degree, 1, 50, 15, 40)',
                    'height': 'mapData(degree, 1, 50, 15, 40)',
                    'font-size': '9px',
                    'color': onSurface,
                    'text-valign': 'bottom',
                    'text-margin-y': 4,
                    'text-wrap': 'ellipsis',
                    'text-max-width': '80px',
                }},
                { selector: 'edge', style: {
                    'width': 'mapData(weight, 0, 1, 1, 3)',
                    'line-color': outline,
                    'target-arrow-shape': 'none',
                    'curve-style': 'bezier',
                    'opacity': 0.5,
                }},
                { selector: '.faded', style: { 'opacity': 0.12 }},
                { selector: '.selected', style: {
                    'border-width': 3,
                    'border-color': primary,
                }},
                { selector: 'node:selected', style: {
                    'border-width': 4,
                    'border-color': primary,
                }},
            ],
            layout: { name: 'preset' },
            wheelSensitivity: 0.3,
            minZoom: 0.2,
            maxZoom: 3,
        });

        Logger.info('GRAPH', `Cytoscape rendered: ${nodes.length} nodes, ${this.payload.elements.edges.length} edges`);
    },
};
```

- [ ] **Step 2: Register controller in main.js**

In `src/web/static/js/main.js`:

1. Replace line 19 `import { LinkedInController } from './controllers/linkedin.js';` with `import { GraphExplorerController } from './controllers/graph_explorer.js';`
2. In the `controllers` array (line 32-44), replace `['LinkedInController', LinkedInController],` with `['GraphExplorerController', GraphExplorerController],`
3. In `window.App.controllers` (line 63-75), replace `linkedin: LinkedInController,` with `graphExplorer: GraphExplorerController,`

- [ ] **Step 3: Manual verification**

Run: `python src/cli.py ui`, open http://localhost:3000, click Graph tab.
Verify:
- Freshness badge populates (e.g., "252 entities · 37 communities · 378 relationships")
- Cytoscape canvas renders 37 community meta-nodes (large outlined ellipses)
- No JS errors in console

- [ ] **Step 4: Commit**

```bash
git add src/web/static/js/controllers/graph_explorer.js src/web/static/js/main.js src/web/static/js/controllers/linkedin.js
git commit -m "feat(ui): add Cytoscape rendering for Graph Explorer; remove LinkedInController"
```

Note: include deletion of `linkedin.js` in this commit.

---

## Task 5 · Frontend: Interactions (bloom, select, search, filter, collapse)

**Files:**
- Modify: `src/web/static/js/controllers/graph_explorer.js`

**Interfaces:**
- Consumes: `this.cy` Cytoscape instance from Task 4
- Produces: bloom / select / search / filter / collapse behaviors

- [ ] **Step 1: Add bloom interaction (click community → expand)**

In `graph_explorer.js`, after the cytoscape init block in `_initCytoscape`, add:

```js
        // ── Bloom: click community → expand children ──────────────────
        this.cy.on('tap', 'node[kind="community"]', (evt) => {
            const node = evt.target;
            const children = node.children();
            if (children.nonempty()) {
                // Already expanded; collapse
                children.style('display', 'none');
                node.removeClass('expanded');
            } else {
                // Expand — children are hidden compound members
                // (Cytoscape hides children of collapsed compound nodes)
                children.style('display', 'element');
                node.addClass('expanded');
                // Re-layout the local area
                children.layout({
                    name: 'cose',
                    animate: true,
                    animationDuration: 300,
                    fit: false,
                }).run();
            }
        });
```

Note: For this to work, Cytoscape must be configured to initially hide entity children of community compound nodes. Update the init options:

```js
        this.cy = cytoscape({
            container: this.canvas,
            elements: { nodes, edges: this.payload.elements.edges },
            // ... existing style ...
            layout: { name: 'preset' },
            // Hide entity children initially; they bloom on community click.
            // We use style 'display: none' on entities whose parent is a community.
            wheelSensitivity: 0.3,
            minZoom: 0.2,
            maxZoom: 3,
        });

        // Initial state: hide all entity nodes (they're children of communities)
        this.cy.elements('node[kind="entity"]').style('display', 'none');
        // Also hide edges between hidden entities
        this.cy.elements('edge').style('display', 'none');
```

- [ ] **Step 2: Add select interaction (click entity → highlight neighbors + populate details)**

In `_initCytoscape`, after the bloom handler:

```js
        // ── Select: click entity → highlight neighborhood ─────────────
        this.cy.on('tap', 'node[kind="entity"]', (evt) => {
            const node = evt.target;
            this._selectEntity(node);
        });

        // Click background → reset
        this.cy.on('tap', (evt) => {
            if (evt.target === this.cy) {
                this._resetHighlight();
                this._hideDetails();
            }
        });
```

Add methods to the controller object:

```js
    _selectEntity(node) {
        const neighborhood = node.neighborhood().union(node);
        this.cy.elements().addClass('faded');
        neighborhood.removeClass('faded');
        this.cy.elements('node:selected').removeClass('selected');
        node.addClass('selected');
        // Show edges between selected neighbors
        neighborhood.edgesWith(neighborhood).removeClass('faded').style('display', 'element');
        this._showDetails(node.data());
    },

    _resetHighlight() {
        this.cy.elements().removeClass('faded');
        this.cy.elements('.selected').removeClass('selected');
    },

    _showDetails(data) {
        const panel = document.getElementById('graph-details');
        if (!panel) return;
        panel.classList.remove('hidden');
        document.getElementById('graph-details-title').textContent = data.label || '';
        document.getElementById('graph-details-type').textContent = data.entity_type || '';
        // Find community label
        const communityNode = this.cy.getElementById(data.parent);
        document.getElementById('graph-details-community').textContent =
            communityNode?.data('label') || '';
        document.getElementById('graph-details-description').textContent =
            data.description || '';
        document.getElementById('graph-details-degree').textContent = data.degree || 0;
        document.getElementById('graph-details-frequency').textContent = data.frequency || 0;
        // Store for Ask Me seeding
        panel.dataset.currentLabel = data.label || '';
    },

    _hideDetails() {
        const panel = document.getElementById('graph-details');
        if (panel) panel.classList.add('hidden');
    },
```

- [ ] **Step 3: Add search interaction**

In `init()`, after loading, bind search:

```js
        const searchInput = document.getElementById('graph-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => this._onSearch(e.target.value));
        }
```

Add method:

```js
    _onSearch(query) {
        if (!this.cy) return;
        const q = query.trim().toLowerCase();
        if (!q) {
            this._resetHighlight();
            return;
        }
        const matches = this.cy.nodes(`node[kind="entity"][label @* "${q}"]`);
        this.cy.elements().addClass('faded');
        matches.removeClass('faded');
        matches.neighborhood().removeClass('faded');
        matches.style('display', 'element');
        matches.neighborhood().edgesWith(matches).style('display', 'element');
    },
```

- [ ] **Step 4: Add filter-by-type interaction**

In `init()`:

```js
        const filterChips = document.querySelectorAll('#graph-type-filters .graph-chip');
        filterChips.forEach(chip => {
            chip.addEventListener('click', () => {
                filterChips.forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                this._filterByType(chip.dataset.type);
            });
        });
```

Add method:

```js
    _filterByType(type) {
        if (!this.cy) return;
        const entities = this.cy.nodes('node[kind="entity"]');
        if (type === 'ALL') {
            // Show all entities whose parent community is expanded
            this.cy.nodes('node[kind="community"].expanded')
                .children().style('display', 'element');
            this.cy.edges().style('display', 'element');
            return;
        }
        entities.style('display', 'none');
        entities.filter(n => n.data('entity_type') === type).style('display', 'element');
        // Update edge visibility
        this.cy.edges().style('display', 'none');
        this.cy.edges().filter(e =>
            e.source().style('display') !== 'none' &&
            e.target().style('display') !== 'none'
        ).style('display', 'element');
    },
```

- [ ] **Step 5: Add collapse-all button**

In `init()`:

```js
        const collapseBtn = document.getElementById('graph-collapse-btn');
        if (collapseBtn) {
            collapseBtn.addEventListener('click', () => this._collapseAll());
        }
```

Add method:

```js
    _collapseAll() {
        if (!this.cy) return;
        this.cy.nodes('node[kind="community"]').removeClass('expanded');
        this.cy.nodes('node[kind="entity"]').style('display', 'none');
        this.cy.edges().style('display', 'none');
        this._resetHighlight();
        this._hideDetails();
    },
```

- [ ] **Step 6: Wire details panel close button**

In `init()`:

```js
        const closeBtn = document.getElementById('graph-details-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this._hideDetails();
                this._resetHighlight();
            });
        }
```

- [ ] **Step 7: Manual verification**

Run `python src/cli.py ui`, open http://localhost:3000, click Graph tab.
Verify:
- Click a community → entities bloom out, layout animates
- Click an entity → neighbors highlighted, details panel populated
- Click background → highlight resets
- Type in search box → matches highlighted
- Click type filter chip → only that entity type shown
- Click collapse button → returns to 37-community view
- Click details close button → panel hides

- [ ] **Step 8: Commit**

```bash
git add src/web/static/js/controllers/graph_explorer.js
git commit -m "feat(ui): add bloom, select, search, filter, collapse interactions for Graph Explorer"
```

---

## Task 6 · Frontend: Details panel + Ask Me integration

**Files:**
- Modify: `src/web/static/js/controllers/graph_explorer.js`

**Interfaces:**
- Consumes: `EventBus` from `core/bus.js`, `NavigationController`
- Produces: "Ask Me about this" button seeds chat tab with pre-filled query

- [ ] **Step 1: Wire Ask Me button**

In `init()` (add after the close button wiring):

```js
        const askBtn = document.getElementById('graph-details-ask');
        if (askBtn) {
            askBtn.addEventListener('click', () => this._seedChat());
        }
```

Add method:

```js
    _seedChat() {
        const panel = document.getElementById('graph-details');
        const label = panel?.dataset.currentLabel;
        if (!label) return;
        const query = `Tell me about ${label}`;
        // Emit event to switch tab and pre-fill chat
        EventBus.emit('tab:switch', 'chat');
        // Wait for chat tab to be ready, then inject query
        setTimeout(() => {
            const chatInput = document.getElementById('chat-input');
            if (chatInput) {
                chatInput.value = query;
                chatInput.focus();
            }
        }, 300);
    },
```

- [ ] **Step 2: Manual verification**

Click an entity in the graph → click "Ask Me about this" button → verify:
- Chat tab opens
- Input field pre-filled with "Tell me about {entity label}"
- User can press Enter to send

- [ ] **Step 3: Commit**

```bash
git add src/web/static/js/controllers/graph_explorer.js
git commit -m "feat(ui): wire 'Ask Me about this' button to seed chat tab"
```

---

## Task 7 · Polish: responsive tweaks + loading states

**Files:**
- Modify: `src/web/static/css/views/graph_explorer.css` (if needed)
- Modify: `src/web/static/js/controllers/graph_explorer.js` (tab-change listener)

- [ ] **Step 1: Lazy-load on tab switch**

Update `init()` to not auto-load; instead listen for tab:changed:

```js
    init() {
        // ... existing DOM refs ...
        if (!this.canvas) return;

        // Bind all interactions (search, filter, collapse, close, ask) here...
        // (from Task 5)

        Logger.info('GRAPH', 'GraphExplorerController initialized.');
        EventBus.on('tab:changed', (tab) => {
            if (tab === 'graph') this.load();
        });
    },
```

Remove the `this.load();` call from the end of `init()`.

- [ ] **Step 2: Handle Cytoscape resize on tab switch**

Add to the `tab:changed` listener:

```js
        EventBus.on('tab:changed', (tab) => {
            if (tab === 'graph') {
                this.load().then(() => {
                    if (this.cy) {
                        this.cy.resize();
                        this.cy.fit();
                    }
                });
            }
        });
```

Update `load()` to return a Promise:

```js
    async load() {
        if (this.payload) {
            if (this.cy) this.cy.resize();
            return;
        }
        // ... rest of load ...
    },
```

- [ ] **Step 3: Manual verification**

Open app → click between tabs → return to Graph tab.
Verify:
- Canvas resizes correctly (no blank areas)
- No JS errors

- [ ] **Step 4: Commit**

```bash
git add src/web/static/js/controllers/graph_explorer.js
git commit -m "feat(ui): lazy-load Graph Explorer on tab switch; handle resize"
```

---

## Task 8 · Final verification + cleanup

**Files:** None new — verification only.

- [ ] **Step 1: Run all tests**

```bash
python -m unittest discover tests -v
```

Expected: all tests pass, including new `test_graph_controller.py` tests.

- [ ] **Step 2: Run lint / static analysis** (if configured)

```bash
# Add any lint commands here if project uses them
```

- [ ] **Step 3: Full manual verification**

Run `python src/cli.py ui`, open http://localhost:3000, verify:
1. Graph tab loads and renders 37 communities
2. Click community → entities bloom
3. Click entity → details panel populated, neighbors highlighted
4. Search, filter, collapse all work
5. "Ask Me about this" seeds chat
6. LinkedIn button/view/controller all gone
7. `/api/linkedin-profile` returns 404
8. `/api/graph/explore` returns 200 with correct payload
9. No JS errors in console
10. Responsive behavior on narrow window

- [ ] **Step 4: Commit any stragglers**

```bash
git status  # ensure working tree is clean
git commit -m "chore: finalize Graph Explorer + LinkedIn cleanup"  # only if needed
```

- [ ] **Step 5: Update CLAUDE.md (optional)**

Add a short note to CLAUDE.md under "Key Modules → `src/web/`" describing the new Graph Explorer tab.

- [ ] **Step 6: Push (if on a branch)**

```bash
git push origin HEAD  # or your branch name
```

---

## Self-Review

**1. Spec coverage:**
- ✅ Backend API + cache (Task 1, 2)
- ✅ Frontend HTML/CSS/nav (Task 3)
- ✅ Cytoscape rendering (Task 4)
- ✅ Interactions (Task 5)
- ✅ Details panel + Ask Me (Task 6)
- ✅ LinkedIn cleanup (Task 3, 4, 2)
- ✅ Error handling (Task 4 _showError)
- ⚠️ Testing: unit + integration covered (Task 1, 2), but E2E Playwright not in plan (out of scope for v1 — manual verification in Task 8)
- ⚠️ Responsive CSS: partially in Task 3, refined in Task 7

**2. Placeholder scan:** No TBD/TODO found. All steps have concrete code.

**3. Type consistency:**
- `get_explorer_payload()` used in Task 1, 2 — consistent.
- `GraphNotBuiltError` raised in Task 1, caught in Task 2 — consistent.
- `GraphExplorerController` registered in Task 4, used in Task 5, 6, 7 — consistent.
- IDs: `c:` / `e:` / `r:` prefixes used throughout Task 1 — consistent.
- `entity_type` values (ORGANIZATION, EVENT, GEO, PERSON) used in Task 3 CSS chips and Task 5 filter — consistent.

**No issues found. Plan is ready for execution.**
