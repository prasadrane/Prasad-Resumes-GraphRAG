/**
 * diagnostics.js — Observability & Engine Diagnostics Controller with Live In-Drawer Log Viewer.
 */

import { Logger } from '../core/logger.js';
import { EventBus } from '../core/bus.js';
import { ApiClient } from '../core/api.js';
import { Utils } from '../core/utils.js';

export const DiagnosticsController = {
    openBtn: null,
    closeBtn: null,
    refreshBtn: null,
    drawer: null,

    retrievalP90: null,
    gatewayP90: null,
    renderAvg: null,
    healthVal: null,
    logStreamContainer: null,
    logFilterSelect: null,
    clearLogsBtn: null,

    init() {
        this.openBtn = document.getElementById('open-diag-btn');
        this.closeBtn = document.getElementById('close-diag-btn');
        this.refreshBtn = document.getElementById('refresh-diag-btn');
        this.drawer = document.getElementById('diag-drawer');

        this.retrievalP90 = document.getElementById('diag-retrieval-p90');
        this.gatewayP90 = document.getElementById('diag-gateway-p90');
        this.renderAvg = document.getElementById('diag-render-avg');
        this.healthVal = document.getElementById('diag-health-val');
        this.logStreamContainer = document.getElementById('diag-log-stream');
        this.logFilterSelect = document.getElementById('diag-log-filter');
        this.clearLogsBtn = document.getElementById('diag-clear-logs-btn');

        if (this.openBtn) this.openBtn.addEventListener('click', () => this.open());
        if (this.closeBtn) this.closeBtn.addEventListener('click', () => this.close());
        if (this.refreshBtn) this.refreshBtn.addEventListener('click', () => this.fetchStats());

        if (this.clearLogsBtn) {
            this.clearLogsBtn.addEventListener('click', () => {
                Logger.clear();
                if (this.logStreamContainer) this.logStreamContainer.innerHTML = '';
            });
        }

        if (this.logFilterSelect) {
            this.logFilterSelect.addEventListener('change', () => {
                Logger.setLevel(this.logFilterSelect.value);
                this.renderLogs();
            });
        }

        // Subscribe to live log emissions
        Logger.subscribe((entry) => this.appendLogEntry(entry));

        // Listen for shortcut toggle
        EventBus.on('diag:toggle', () => this.toggle());

        Logger.info('DIAG', 'DiagnosticsController initialized.');
    },

    toggle() {
        if (!this.drawer) return;
        if (this.drawer.classList.contains('open')) {
            this.close();
        } else {
            this.open();
        }
    },

    open() {
        if (this.drawer) this.drawer.classList.add('open');
        Utils.playTone('pop');
        this.fetchStats();
        this.renderLogs();
    },

    close() {
        if (this.drawer) this.drawer.classList.remove('open');
        Utils.playTone('pop');
    },

    renderLogs() {
        if (!this.logStreamContainer) return;
        this.logStreamContainer.innerHTML = '';
        const logs = Logger.getLogs();
        logs.forEach(entry => this.appendLogEntry(entry));
        this.logStreamContainer.scrollTop = this.logStreamContainer.scrollHeight;
    },

    appendLogEntry(entry) {
        if (!this.logStreamContainer) return;
        const line = document.createElement('div');
        line.className = `diag-log-line ${entry.level.toLowerCase()}`;
        line.innerHTML = `
            <span class="diag-time">${entry.timeStr}</span>
            <span class="diag-badge ${entry.subsystem.toLowerCase()}">[${entry.subsystem}]</span>
            <span class="diag-msg">${Utils.escapeHtml(entry.message)}</span>
        `;
        this.logStreamContainer.appendChild(line);
        if (this.logStreamContainer.children.length > 200) {
            this.logStreamContainer.removeChild(this.logStreamContainer.children[0]);
        }
        this.logStreamContainer.scrollTop = this.logStreamContainer.scrollHeight;
    },

    async fetchStats() {
        try {
            const data = await ApiClient.getJson('/api/telemetry-stats');

            if (this.retrievalP90) this.retrievalP90.textContent = `${data.spans.retrieval.p90_ms || 0}ms`;
            if (this.gatewayP90) this.gatewayP90.textContent = `${data.spans.gateway.p90_ms || 0}ms`;
            if (this.renderAvg) this.renderAvg.textContent = `${data.spans.pdf_render.avg_ms || 0}ms`;
            if (this.healthVal) this.healthVal.textContent = data.engine_status || 'Healthy';
        } catch (err) {
            Logger.warn('DIAG', 'Stats fetch failed:', err);
        }
    }
};
