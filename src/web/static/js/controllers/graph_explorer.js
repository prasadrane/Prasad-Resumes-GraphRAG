/**
 * graph_explorer.js — Knowledge Graph Explorer Controller (v3, Obsidian-style).
 * Fetches Cytoscape-ready JSON from /api/graph/explore and renders the full
 * entity graph as a force-directed constellation.
 *
 * Layout strategy:
 *   - ALL entities are visible from first paint, placed by deterministic
 *     phyllotaxis clusters per community and relaxed with a tiny force pass
 *     (repulsion + edge springs + centroid gravity) for an organic look.
 *   - Communities render as translucent rounded panels (compound parents)
 *     titled with their real GraphRAG report names.
 *   - Click community panel → focus mode: fit-to-cluster + fade the rest.
 *     Click again / background / Reset view → back to overview.
 *   - Click entity → highlight neighborhood, populate details panel.
 *   - Search box / type chips fade non-matches (spatial stability).
 *   - Hover tooltip, zoom/fit controls, first-run hint pill.
 *   - Entity labels appear past a zoom threshold (clean zoomed-out view).
 *   - "Ask Me about this" → seeds chat tab with entity label.
 */

import { Logger } from '../core/logger.js';
import { ApiClient } from '../core/api.js';
import { EventBus } from '../core/bus.js';

export const GraphExplorerController = {
    cy: null,
    cytoscapeLib: null,
    payload: null,

    // Interaction state driving the fade emphasis model
    activeType: 'ALL',
    searchQuery: '',
    focused: null,
    hintDismissed: false,
    layoutDone: false,

    // DOM refs
    canvas: null,
    loadingEl: null,
    errorEl: null,
    freshnessEl: null,
    searchInput: null,
    detailsPanel: null,
    tooltipEl: null,
    hintEl: null,

    init() {
        this.canvas = document.getElementById('graph-canvas');
        this.loadingEl = document.getElementById('graph-loading');
        this.errorEl = document.getElementById('graph-error');
        this.freshnessEl = document.getElementById('graph-freshness');
        this.searchInput = document.getElementById('graph-search');
        this.detailsPanel = document.getElementById('graph-details');
        this.tooltipEl = document.getElementById('graph-tooltip');
        this.hintEl = document.getElementById('graph-hint');

        if (!this.canvas) {
            // Graph tab not present (e.g., some custom builds); skip silently.
            return;
        }

        // Bind toolbar interactions (they're no-ops until payload loads)
        this._bindToolbar();

        // Lazy-load on first tab switch; don't auto-load on init
        EventBus.on('tab:changed', (tab) => {
            if (tab === 'graph') {
                this.load().then(() => {
                    if (this.cy) {
                        this.cy.resize();
                        this.cy.fit(undefined, 40);
                    }
                });
            }
        });

        Logger.info('GRAPH', 'GraphExplorerController initialized.');
    },

    _bindToolbar() {
        // Search
        if (this.searchInput) {
            this.searchInput.addEventListener('input', (e) => this._onSearch(e.target.value));
        }

        // Type filter chips
        const filterChips = document.querySelectorAll('#graph-type-filters .graph-chip');
        filterChips.forEach(chip => {
            chip.addEventListener('click', () => {
                filterChips.forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                this._filterByType(chip.dataset.type);
            });
        });

        // Reset view
        const resetBtn = document.getElementById('graph-collapse-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this._resetView());
        }

        // Details panel close
        const closeBtn = document.getElementById('graph-details-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this._hideDetails();
                this._resetHighlight();
                this._applyState();
            });
        }

        // Ask Me about this
        const askBtn = document.getElementById('graph-details-ask');
        if (askBtn) {
            askBtn.addEventListener('click', () => this._seedChat());
        }

        // Zoom / fit controls
        const zoomIn = document.getElementById('graph-zoom-in');
        const zoomOut = document.getElementById('graph-zoom-out');
        const zoomFit = document.getElementById('graph-zoom-fit');
        if (zoomIn) zoomIn.addEventListener('click', () => this._zoomBy(1.35));
        if (zoomOut) zoomOut.addEventListener('click', () => this._zoomBy(1 / 1.35));
        if (zoomFit) zoomFit.addEventListener('click', () => {
            if (this.cy) this.cy.animate({ fit: { padding: 40 }, duration: 300 });
        });
    },

    _zoomBy(factor) {
        if (!this.cy) return;
        const center = { x: this.cy.width() / 2, y: this.cy.height() / 2 };
        this.cy.animate({
            zoom: { level: this.cy.zoom() * factor, renderedPosition: center },
            duration: 200,
        });
    },

    async load() {
        if (this.payload) {
            if (this.cy) this.cy.resize();
            return;
        }
        this._showLoading();
        try {
            // Use fetch directly so we can inspect status + body on error.
            // ApiClient.getJson swallows the response body when !ok.
            const res = await fetch('/api/graph/explore');
            if (!res.ok) {
                let detail = null;
                try { detail = await res.json(); } catch (_) { /* not JSON */ }
                const err = new Error(`HTTP ${res.status}: ${res.statusText}`);
                err.status = res.status;
                err.detail = detail?.detail ?? detail;
                throw err;
            }
            const data = await res.json();
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

        const status = err?.status;
        const detail = err?.detail;
        const code = typeof detail === 'object' ? detail?.code : null;
        const hint = typeof detail === 'object' ? detail?.hint : null;

        if (status === 503 || code === 'GRAPH_NOT_BUILT') {
            this.errorEl.innerHTML = `
                <span class="material-symbols-outlined" style="font-size:48px;">database_off</span>
                <p><strong>GraphRAG index not built.</strong></p>
                <p style="font-size:0.85rem;">${hint || 'Run <code>graphrag index --root .</code> locally to enable.'}</p>
            `;
        } else if (status === 404) {
            this.errorEl.innerHTML = `
                <span class="material-symbols-outlined" style="font-size:48px;">route</span>
                <p><strong>Endpoint not found.</strong></p>
                <p style="font-size:0.85rem;">The graph API route isn't registered. Try restarting the server.</p>
            `;
        } else {
            const msg = status ? `HTTP ${status}` : 'Network error';
            const detailText = (typeof detail === 'string' ? detail : detail?.message) || err?.message || '';
            this.errorEl.innerHTML = `
                <span class="material-symbols-outlined" style="font-size:48px;">error</span>
                <p><strong>Failed to load graph data.</strong></p>
                <p style="font-size:0.85rem; color: var(--md-sys-color-error);">${msg}${detailText ? ': ' + detailText : ''}</p>
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
                this.cytoscapeLib = cytoscape;
                this._initCytoscape(cytoscape);
            })
            .catch(err => {
                Logger.error('GRAPH', 'Failed to load Cytoscape:', err);
                this._showError({ status: 0, message: 'Cytoscape CDN unreachable' });
            });
    },

    // ── Layout helpers ────────────────────────────────────────────────

    /**
     * Deterministic phyllotaxis (sunflower) slots for communities, ordered
     * largest-first so the biggest community sits at the center. Used as the
     * force-layout seed so every load settles into the same constellation.
     */
    _communitySlots(orderedIds) {
        const GOLDEN_ANGLE = Math.PI * (3 - Math.sqrt(5));
        const scale = 240;
        const slots = {};
        orderedIds.forEach((id, i) => {
            const r = scale * Math.sqrt(i + 0.5);
            const theta = i * GOLDEN_ANGLE;
            slots[id] = { x: r * Math.cos(theta), y: r * Math.sin(theta) };
        });
        return slots;
    },

    /**
     * Position entities in a mini phyllotaxis cluster around their community
     * slot, then relax with a tiny deterministic force pass (intra-cluster
     * repulsion + edge springs + centroid gravity) so connected entities sit
     * together — an organic, Obsidian-like blob without a physics engine.
     */
    _assignPositions(nodes) {
        const childrenByParent = {};
        for (const n of nodes) {
            if (n.data.kind === 'entity' && n.data.parent) {
                (childrenByParent[n.data.parent] ||= []).push(n.data.id);
            }
        }

        const ordered = nodes
            .filter(n => n.data.kind === 'community')
            .sort((a, b) => (childrenByParent[b.data.id]?.length || 0) - (childrenByParent[a.data.id]?.length || 0))
            .map(n => n.data.id);
        const slots = this._communitySlots(ordered);

        const pos = {};
        for (const [pid, childIds] of Object.entries(childrenByParent)) {
            const slot = slots[pid] || { x: 0, y: 0 };
            childIds.forEach((cid, j) => {
                const r = 24 * Math.sqrt(j + 0.5);
                const theta = j * Math.PI * (3 - Math.sqrt(5));
                pos[cid] = {
                    x: slot.x + r * Math.cos(theta),
                    y: slot.y + r * Math.sin(theta),
                };
            });
        }

        // Intra-cluster entity edges act as springs
        const parentOf = {};
        for (const [pid, kids] of Object.entries(childrenByParent)) {
            for (const k of kids) parentOf[k] = pid;
        }
        const springs = this.payload.elements.edges.filter(e =>
            pos[e.data.source] && pos[e.data.target] &&
            parentOf[e.data.source] && parentOf[e.data.source] === parentOf[e.data.target]);

        const ITER = 90, CAP = 6;
        for (let iter = 0; iter < ITER; iter++) {
            const disp = {};
            const add = (id, dx, dy) => {
                (disp[id] ||= { x: 0, y: 0 }).x += dx;
                disp[id].y += dy;
            };
            // Pairwise repulsion within each cluster (short-range)
            for (const kids of Object.values(childrenByParent)) {
                for (let i = 0; i < kids.length; i++) {
                    for (let j = i + 1; j < kids.length; j++) {
                        const a = kids[i], b = kids[j];
                        let dx = pos[a].x - pos[b].x, dy = pos[a].y - pos[b].y;
                        const d2 = dx * dx + dy * dy;
                        if (d2 > 160 * 160) continue;
                        const f = 900 / (d2 || 1);
                        add(a, dx * f, dy * f);
                        add(b, -dx * f, -dy * f);
                    }
                }
            }
            // Springs pull connected entities toward the ideal length
            for (const e of springs) {
                const a = e.data.source, b = e.data.target;
                let dx = pos[a].x - pos[b].x, dy = pos[a].y - pos[b].y;
                const d = Math.sqrt(dx * dx + dy * dy) || 1;
                const f = (d - 60) * 0.02 / d;
                add(a, -dx * f, -dy * f);
                add(b, dx * f, dy * f);
            }
            // Weak gravity toward the cluster slot keeps blobs centered
            for (const [pid, kids] of Object.entries(childrenByParent)) {
                const s = slots[pid] || { x: 0, y: 0 };
                for (const k of kids) {
                    add(k, (s.x - pos[k].x) * 0.05, (s.y - pos[k].y) * 0.05);
                }
            }
            for (const [id, d] of Object.entries(disp)) {
                pos[id].x += Math.max(-CAP, Math.min(CAP, d.x));
                pos[id].y += Math.max(-CAP, Math.min(CAP, d.y));
            }
        }
        return pos;
    },

    _initCytoscape(cytoscape) {
        const cs = getComputedStyle(document.documentElement);
        const primary = cs.getPropertyValue('--md-sys-color-primary').trim() || '#a8c7fa';
        const surface = cs.getPropertyValue('--md-sys-color-surface').trim() || '#0f172a';
        const outline = cs.getPropertyValue('--md-sys-color-outline').trim() || '#475569';
        const onSurface = cs.getPropertyValue('--md-sys-color-on-surface').trim() || '#f8fafc';

        const TYPE_COLORS = {
            PERSON: cs.getPropertyValue('--graph-color-person').trim() || primary,
            ORGANIZATION: cs.getPropertyValue('--graph-color-org').trim() || '#c9a7f5',
            EVENT: cs.getPropertyValue('--graph-color-event').trim() || '#fbbf24',
            GEO: cs.getPropertyValue('--graph-color-geo').trim() || '#4fd1a5',
        };
        this.typeColors = TYPE_COLORS;

        // Decorate entities with type color; communities with child stats
        let nodes = this.payload.elements.nodes.map(n => ({
            ...n,
            data: { ...n.data, colorByType: TYPE_COLORS[n.data.entity_type] || primary },
        }));

        const childCount = {};
        const typeTally = {};
        for (const n of nodes) {
            if (n.data.kind !== 'entity' || !n.data.parent) continue;
            childCount[n.data.parent] = (childCount[n.data.parent] || 0) + 1;
            const tally = (typeTally[n.data.parent] ||= {});
            tally[n.data.entity_type] = (tally[n.data.entity_type] || 0) + 1;
        }
        nodes = nodes.map(n => {
            if (n.data.kind !== 'community') return n;
            const count = childCount[n.data.id] || 0;
            const tally = typeTally[n.data.id] || {};
            const dominant = Object.entries(tally).sort((a, b) => b[1] - a[1])[0]?.[0];
            return {
                ...n,
                data: {
                    ...n.data,
                    child_count: count,
                    colorByDominant: (dominant && TYPE_COLORS[dominant]) || primary,
                },
            };
        });

        // Seed entity cluster positions; compound parents auto-center
        const positions = this._assignPositions(nodes);
        const positionedNodes = nodes.map(n =>
            positions[n.data.id] ? { ...n, position: positions[n.data.id] } : n
        );

        this.cy = cytoscape({
            container: this.canvas,
            elements: { nodes: positionedNodes, edges: this.payload.elements.edges },
            style: [
                // Community cluster panels (compound parents)
                { selector: 'node[kind="community"]', style: {
                    'shape': 'round-rectangle',
                    'background-color': 'data(colorByDominant)',
                    'background-opacity': 0.09,
                    'border-width': 1.5,
                    'border-color': 'data(colorByDominant)',
                    'border-opacity': 0.55,
                    'padding': '16px',
                    'label': 'data(label)',
                    'text-valign': 'top',
                    'text-halign': 'center',
                    'text-margin-y': '-4px',
                    'color': 'data(colorByDominant)',
                    'font-size': '13px',
                    'font-weight': 600,
                    'text-wrap': 'wrap',
                    'text-max-width': '240px',
                    'transition-property': 'background-opacity, border-opacity',
                    'transition-duration': '150ms',
                }},
                { selector: 'node[kind="community"].hovered', style: {
                    'background-opacity': 0.16,
                    'border-opacity': 0.9,
                }},
                // Entities
                { selector: 'node[kind="entity"]', style: {
                    'background-color': 'data(colorByType)',
                    'border-width': 1,
                    'border-color': surface,
                    'label': 'data(label)',
                    'width': 'mapData(degree, 1, 80, 10, 28)',
                    'height': 'mapData(degree, 1, 80, 10, 28)',
                    'font-size': '9px',
                    'color': onSurface,
                    'text-valign': 'bottom',
                    'text-margin-y': 2,
                    'text-wrap': 'ellipsis',
                    'text-max-width': '80px',
                    'text-background-color': surface,
                    'text-background-opacity': 0.6,
                    'text-background-padding': '1px',
                }},
                // Labels collapse to clean dots while zoomed out
                { selector: 'node[kind="entity"].zfar', style: {
                    'label': '',
                }},
                { selector: 'edge', style: {
                    'width': 'mapData(weight, 0, 1, 0.8, 2.2)',
                    'line-color': outline,
                    'target-arrow-shape': 'none',
                    'curve-style': 'bezier',
                    'opacity': 0.35,
                }},
                { selector: '.faded', style: { 'opacity': 0.08 }},
                { selector: '.selected', style: {
                    'border-width': 2.5,
                    'border-color': onSurface,
                }},
            ],
            // Positions are pre-relaxed deterministically (see
            // _assignPositions); preset just adopts them.
            layout: { name: 'preset', fit: false },
            wheelSensitivity: 0.3,
            minZoom: 0.15,
            maxZoom: 4,
        });

        // Preset layout runs synchronously during construction, so reveal +
        // fit right away; the layoutstop fallback covers async edge cases.
        const firstLayoutDone = () => {
            if (this.layoutDone) return;
            this.layoutDone = true;
            if (this.loadingEl) this.loadingEl.classList.add('hidden');
            this.cy.fit(undefined, 40);
            this._updateLabelVis();
            this._showHint();
        };
        firstLayoutDone();
        this.cy.one('layoutstop', firstLayoutDone);

        // ── Focus: click community panel → zoom to cluster, fade rest ──
        this.cy.on('tap', 'node[kind="community"]', (evt) => {
            this._toggleFocus(evt.target);
        });

        // ── Select: click entity → highlight neighborhood ─────────────
        this.cy.on('tap', 'node[kind="entity"]', (evt) => {
            this._selectEntity(evt.target);
        });

        // Click background → clear focus/selection
        this.cy.on('tap', (evt) => {
            if (evt.target === this.cy) {
                this.focused = null;
                this._resetHighlight();
                this._applyState();
                this._hideDetails();
            }
        });

        // ── Tooltip + hover emphasis ──────────────────────────────────
        this.cy.on('mouseover', 'node', (evt) => {
            evt.target.addClass('hovered');
            this._showTooltip(evt.target);
        });
        this.cy.on('mousemove', 'node', (evt) => this._moveTooltip(evt));
        this.cy.on('mouseout', 'node', (evt) => {
            evt.target.removeClass('hovered');
            this._hideTooltip();
        });

        // Any interaction dismisses the hint pill
        this.cy.on('tap drag zoom', () => this._dismissHint());

        // Zoom-dependent entity labels
        this.cy.on('zoom', () => requestAnimationFrame(() => this._updateLabelVis()));

        Logger.info('GRAPH', `Cytoscape rendered: ${positionedNodes.length} nodes, ${this.payload.elements.edges.length} edges (relaxed constellation)`);
    },

    // ── Hint / tooltip / label chrome ─────────────────────────────────

    _updateLabelVis() {
        if (!this.cy) return;
        this.cy.nodes('node[kind="entity"]').toggleClass('zfar', this.cy.zoom() < 0.9);
    },

    _showHint() {
        if (this.hintEl && !this.hintDismissed) this.hintEl.classList.remove('hidden');
    },

    _dismissHint() {
        if (this.hintDismissed) return;
        this.hintDismissed = true;
        if (this.hintEl) this.hintEl.classList.add('hidden');
    },

    _showTooltip(node) {
        if (!this.tooltipEl) return;
        const d = node.data();
        let html;
        if (d.kind === 'community') {
            html = `
                <span class="tt-label">${this._escapeHtml(d.label)}</span>
                <span class="tt-meta">
                    <span class="tt-dot" style="background:${d.colorByDominant}"></span>
                    Community · ${d.child_count} ${d.child_count === 1 ? 'entity' : 'entities'} · click to focus
                </span>`;
        } else {
            const color = d.colorByType || '#888';
            html = `
                <span class="tt-label">${this._escapeHtml(d.label)}</span>
                <span class="tt-meta">
                    <span class="tt-dot" style="background:${color}"></span>
                    ${this._escapeHtml(d.entity_type || 'ENTITY')} · ${d.degree || 0} connections
                </span>`;
        }
        this.tooltipEl.innerHTML = html;
        this.tooltipEl.classList.remove('hidden');
    },

    _moveTooltip(evt) {
        if (!this.tooltipEl) return;
        const rp = evt.renderedPosition;
        const pad = 14;
        const maxX = this.cy.width() - this.tooltipEl.offsetWidth - 8;
        const maxY = this.cy.height() - this.tooltipEl.offsetHeight - 8;
        const x = Math.min(Math.max(rp.x + pad, 8), Math.max(maxX, 8));
        const y = Math.min(Math.max(rp.y + pad, 8), Math.max(maxY, 8));
        this.tooltipEl.style.transform = `translate(${x}px, ${y}px)`;
    },

    _hideTooltip() {
        if (this.tooltipEl) this.tooltipEl.classList.add('hidden');
    },

    _escapeHtml(s) {
        return String(s ?? '').replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
        }[c]));
    },

    // ── Emphasis model (fade-based) ───────────────────────────────────

    /** Recompute faded set from focus + search + type-filter state. */
    _applyState() {
        if (!this.cy) return;
        const cy = this.cy;
        cy.elements().removeClass('faded');

        // Type filter fades non-matching entities (and empty panels)
        if (this.activeType !== 'ALL') {
            cy.nodes('node[kind="entity"]').forEach(n => {
                if (n.data('entity_type') !== this.activeType) n.addClass('faded');
            });
            cy.nodes('node[kind="community"]').forEach(c => {
                if (c.children().filter(k => !k.hasClass('faded')).empty()) c.addClass('faded');
            });
        }

        // Search fades everything outside matches + neighborhood
        const q = this.searchQuery;
        if (q) {
            const matches = cy.nodes('node[kind="entity"]').filter(n =>
                (n.data('label') || '').toLowerCase().includes(q));
            const keep = matches.union(matches.neighborhood());
            cy.elements().forEach(el => {
                if (!keep.contains(el) && !el.same(keep)) el.addClass('faded');
            });
            cy.nodes('node[kind="community"]').forEach(c => {
                if (c.descendants().filter(k => !k.hasClass('faded')).empty()) c.addClass('faded');
            });
        }

        // Focus fades everything outside the focused cluster
        if (this.focused) {
            const inside = this.focused.union(this.focused.descendants());
            cy.elements().forEach(el => {
                if (!inside.contains(el)) el.addClass('faded');
            });
            inside.connectedEdges().forEach(e => {
                if (inside.contains(e.source()) && inside.contains(e.target())) e.removeClass('faded');
            });
        }

        // Edges with a faded endpoint fade too
        cy.edges().forEach(e => {
            if (e.source().hasClass('faded') || e.target().hasClass('faded')) e.addClass('faded');
        });
    },

    _toggleFocus(node) {
        if (this.focused && this.focused.same(node)) {
            this.focused = null;
            this._applyState();
            this.cy.animate({ fit: { padding: 40 }, duration: 450, easing: 'ease-in-out-cubic' });
            return;
        }
        this.focused = node;
        this._applyState();
        const inside = node.union(node.descendants());
        this.cy.animate({
            fit: { eles: inside, padding: 60 },
            duration: 450,
            easing: 'ease-in-out-cubic',
        });
    },

    // ── Selection & details ───────────────────────────────────────────

    _selectEntity(node) {
        const neighborhood = node.closedNeighborhood();
        this.cy.elements().addClass('faded');
        neighborhood.removeClass('faded');
        this.cy.elements('.selected').removeClass('selected');
        node.addClass('selected');
        this._showDetails(node.data());
    },

    _resetHighlight() {
        if (!this.cy) return;
        this.cy.elements().removeClass('faded');
        this.cy.elements('.selected').removeClass('selected');
    },

    _showDetails(data) {
        if (!this.detailsPanel) return;
        this.detailsPanel.classList.remove('hidden');
        document.getElementById('graph-details-title').textContent = data.label || '';
        const typeEl = document.getElementById('graph-details-type');
        typeEl.textContent = data.entity_type || '';
        const color = this.typeColors?.[data.entity_type];
        if (color) {
            typeEl.style.background = `${color}26`;
            typeEl.style.color = color;
        } else {
            typeEl.style.background = '';
            typeEl.style.color = '';
        }
        // Find community label
        const communityNode = this.cy.getElementById(data.parent);
        document.getElementById('graph-details-community').textContent =
            communityNode?.data('label') || '';
        document.getElementById('graph-details-description').textContent =
            data.description || '';
        document.getElementById('graph-details-degree').textContent = data.degree || 0;
        document.getElementById('graph-details-frequency').textContent = data.frequency || 0;
        // Store for Ask Me seeding
        this.detailsPanel.dataset.currentLabel = data.label || '';
    },

    _hideDetails() {
        if (this.detailsPanel) this.detailsPanel.classList.add('hidden');
    },

    // ── Search / filter / reset ───────────────────────────────────────

    _onSearch(query) {
        if (!this.cy) return;
        const q = query.trim().toLowerCase();
        this.searchQuery = q;
        this.focused = null;
        this._resetHighlight();
        this._applyState();
    },

    _filterByType(type) {
        if (!this.cy) return;
        this.activeType = type;
        this.focused = null;
        this._resetHighlight();
        this._applyState();
    },

    _resetView() {
        if (!this.cy) return;
        this.focused = null;
        this.activeType = 'ALL';
        this.searchQuery = '';
        this._resetHighlight();
        this._hideDetails();
        this.cy.animate({ fit: { padding: 40 }, duration: 300 });
        // Reset toolbar state
        if (this.searchInput) this.searchInput.value = '';
        const chips = document.querySelectorAll('#graph-type-filters .graph-chip');
        chips.forEach(c => c.classList.toggle('active', c.dataset.type === 'ALL'));
    },

    _seedChat() {
        const label = this.detailsPanel?.dataset.currentLabel;
        if (!label) return;
        const query = `Tell me about ${label}`;
        // Switch to chat tab
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
};
