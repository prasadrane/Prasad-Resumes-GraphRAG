/**
 * graph_explorer.js — Knowledge Graph Explorer Controller.
 * Fetches Cytoscape-ready JSON from /api/graph/explore and renders
 * an interactive graph of Prasad's career entities & communities.
 *
 * Layout strategy:
 *   - Default view: community meta-nodes (large outlined ellipses)
 *   - Click community → bloom member entities (fade-in + force re-layout)
 *   - Click entity → highlight neighborhood, populate details panel
 *   - Search box → filter by label substring
 *   - Type chips → filter by entity_type (ORG / EVENT / GEO / PERSON)
 *   - Collapse button → return to community meta-view
 *   - "Ask Me about this" → seeds chat tab with entity label
 */

import { Logger } from '../core/logger.js';
import { ApiClient } from '../core/api.js';
import { EventBus } from '../core/bus.js';

export const GraphExplorerController = {
    cy: null,
    cytoscapeLib: null,
    payload: null,

    // DOM refs
    canvas: null,
    loadingEl: null,
    errorEl: null,
    freshnessEl: null,
    searchInput: null,
    detailsPanel: null,

    init() {
        this.canvas = document.getElementById('graph-canvas');
        this.loadingEl = document.getElementById('graph-loading');
        this.errorEl = document.getElementById('graph-error');
        this.freshnessEl = document.getElementById('graph-freshness');
        this.searchInput = document.getElementById('graph-search');
        this.detailsPanel = document.getElementById('graph-details');

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
                        this.cy.fit(undefined, 30);
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

        // Collapse all
        const collapseBtn = document.getElementById('graph-collapse-btn');
        if (collapseBtn) {
            collapseBtn.addEventListener('click', () => this._collapseAll());
        }

        // Details panel close
        const closeBtn = document.getElementById('graph-details-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this._hideDetails();
                this._resetHighlight();
            });
        }

        // Ask Me about this
        const askBtn = document.getElementById('graph-details-ask');
        if (askBtn) {
            askBtn.addEventListener('click', () => this._seedChat());
        }
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
                this.cytoscapeLib = cytoscape;
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

        // Position community meta-nodes at centroid of their member entity positions
        // (entities all have x,y = 0 for now, but this future-proofs for when GraphRAG emits real coords)
        const communityCentroids = this._computeCommunityCentroids(nodes);
        const positionedNodes = nodes.map(n => {
            if (n.data.kind === 'community' && communityCentroids[n.data.id]) {
                return { ...n, position: communityCentroids[n.data.id] };
            }
            if (n.data.kind === 'entity' && (n.data.x || n.data.y)) {
                return { ...n, position: { x: n.data.x, y: n.data.y } };
            }
            return n;
        });

        this.cy = cytoscape({
            container: this.canvas,
            elements: { nodes: positionedNodes, edges: this.payload.elements.edges },
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
                    'font-size': '11px',
                    'font-weight': 'bold',
                    'text-wrap': 'wrap',
                    'text-max-width': '100px',
                    'width': 'mapData(member_count, 1, 100, 50, 140)',
                    'height': 'mapData(member_count, 1, 100, 50, 140)',
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

        // Initial state: hide all entity nodes and edges (they bloom on community click)
        this.cy.elements('node[kind="entity"]').style('display', 'none');
        this.cy.elements('edge').style('display', 'none');

        // ── Bloom: click community → expand children ──────────────────
        this.cy.on('tap', 'node[kind="community"]', (evt) => {
            const node = evt.target;
            const children = node.children();
            if (children.empty()) return;  // no children to bloom
            if (node.hasClass('expanded')) {
                // Collapse
                children.style('display', 'none');
                this.cy.edges().forEach(e => {
                    const srcParent = e.source().parent();
                    const tgtParent = e.target().parent();
                    if (srcParent.same(node) || tgtParent.same(node)) {
                        e.style('display', 'none');
                    }
                });
                node.removeClass('expanded');
            } else {
                // Expand
                children.style('display', 'element');
                node.addClass('expanded');
                // Show edges between visible entities
                this.cy.edges().forEach(e => {
                    if (e.source().style('display') !== 'none' &&
                        e.target().style('display') !== 'none') {
                        e.style('display', 'element');
                    }
                });
                // Re-layout the children around the community centroid
                children.layout({
                    name: 'circle',
                    animate: true,
                    animationDuration: 300,
                    fit: false,
                    boundingBox: {
                        x1: node.position().x - 150,
                        y1: node.position().y - 150,
                        x2: node.position().x + 150,
                        y2: node.position().y + 150,
                    },
                }).run();
            }
        });

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

        Logger.info('GRAPH', `Cytoscape rendered: ${positionedNodes.length} nodes, ${this.payload.elements.edges.length} edges`);
    },

    _computeCommunityCentroids(nodes) {
        const sums = {};
        const counts = {};
        for (const n of nodes) {
            if (n.data.kind === 'entity' && n.data.parent) {
                const pid = n.data.parent;
                if (!sums[pid]) { sums[pid] = { x: 0, y: 0 }; counts[pid] = 0; }
                sums[pid].x += (n.data.x || 0);
                sums[pid].y += (n.data.y || 0);
                counts[pid]++;
            }
        }
        const centroids = {};
        for (const pid of Object.keys(sums)) {
            // If all entities are at (0,0), spread communities in a circle so they're visible
            const avgX = sums[pid].x / counts[pid];
            const avgY = sums[pid].y / counts[pid];
            centroids[pid] = { x: avgX, y: avgY };
        }
        // If all centroids are (0,0), use a force layout to position communities
        const allZero = Object.values(centroids).every(c => c.x === 0 && c.y === 0);
        if (allZero) {
            // Use a deterministic radial layout for communities
            const ids = Object.keys(centroids);
            const radius = Math.max(200, ids.length * 20);
            ids.forEach((id, i) => {
                const angle = (i / ids.length) * 2 * Math.PI;
                centroids[id] = {
                    x: Math.cos(angle) * radius,
                    y: Math.sin(angle) * radius,
                };
            });
        }
        return centroids;
    },

    _selectEntity(node) {
        const neighborhood = node.closedNeighborhood();
        this.cy.elements().addClass('faded');
        neighborhood.removeClass('faded');
        this.cy.elements('.selected').removeClass('selected');
        node.addClass('selected');
        // Ensure edges in neighborhood are visible
        neighborhood.filter('edge').style('display', 'element').removeClass('faded');
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
        this.detailsPanel.dataset.currentLabel = data.label || '';
    },

    _hideDetails() {
        if (this.detailsPanel) this.detailsPanel.classList.add('hidden');
    },

    _onSearch(query) {
        if (!this.cy) return;
        const q = query.trim().toLowerCase();
        if (!q) {
            this._resetHighlight();
            return;
        }
        // Match entities whose label contains the query
        const matches = this.cy.nodes(`node[kind="entity"]`).filter(n =>
            (n.data('label') || '').toLowerCase().includes(q)
        );
        this.cy.elements().addClass('faded');
        matches.removeClass('faded');
        matches.neighborhood().removeClass('faded');
        // Make sure matches are visible (expand their parent communities)
        matches.forEach(n => {
            const parent = n.parent();
            if (parent.length && !parent.hasClass('expanded')) {
                parent.children().style('display', 'element');
                parent.addClass('expanded');
            }
        });
        // Show edges between visible entities
        this.cy.edges().filter(e =>
            e.source().style('display') !== 'none' &&
            e.target().style('display') !== 'none'
        ).style('display', 'element');
    },

    _filterByType(type) {
        if (!this.cy) return;
        const entities = this.cy.nodes('node[kind="entity"]');
        if (type === 'ALL') {
            // Show all entities whose parent community is expanded
            this.cy.nodes('node[kind="community"].expanded')
                .children().style('display', 'element');
            this.cy.edges().filter(e =>
                e.source().style('display') !== 'none' &&
                e.target().style('display') !== 'none'
            ).style('display', 'element');
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

    _collapseAll() {
        if (!this.cy) return;
        this.cy.nodes('node[kind="community"]').removeClass('expanded');
        this.cy.nodes('node[kind="entity"]').style('display', 'none');
        this.cy.edges().style('display', 'none');
        this._resetHighlight();
        this._hideDetails();
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
