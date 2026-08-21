/**
 * api.js — Unified API Client with Correlation ID Tracking, Network History & Status Hooks.
 */

import { Logger } from './logger.js';
import { EventBus } from './bus.js';

class ApiClientService {
    constructor() {
        this.history = [];
        this.maxHistory = 100;
        this.activeRequests = 0;
    }

    _generateCorrelationId() {
        return 'ui-' + Math.random().toString(36).substring(2, 9) + '-' + Date.now().toString(36);
    }

    _recordHistory(entry) {
        this.history.unshift(entry);
        if (this.history.length > this.maxHistory) {
            this.history.pop();
        }
    }

    async request(url, options = {}) {
        const start = performance.now();
        const cid = options.correlationId || this._generateCorrelationId();
        const method = (options.method || 'GET').toUpperCase();

        const headers = {
            'Content-Type': 'application/json',
            'X-Correlation-ID': cid,
            ...(options.headers || {})
        };

        const config = {
            ...options,
            method,
            headers
        };

        this.activeRequests++;
        EventBus.emit('api:start', { url, method, cid });
        Logger.debug('API:REQ', `${method} ${url} [cid=${cid}]`, options.body ? JSON.parse(options.body) : null);

        try {
            const response = await fetch(url, config);
            const duration = Math.round(performance.now() - start);
            this.activeRequests = Math.max(0, this.activeRequests - 1);

            const serverCid = response.headers.get('X-Correlation-ID') || cid;
            const serverMs = response.headers.get('X-Response-Time-Ms');

            const historyEntry = {
                timestamp: new Date().toISOString(),
                method,
                url,
                status: response.status,
                statusText: response.statusText,
                durationMs: duration,
                serverMs: serverMs ? parseFloat(serverMs) : null,
                correlationId: serverCid,
                ok: response.ok
            };
            this._recordHistory(historyEntry);

            if (!response.ok) {
                Logger.error('API:RES', `❌ ${method} ${url} (${response.status} ${response.statusText}) - ${duration}ms [cid=${serverCid}]`);
                EventBus.emit('api:error', historyEntry);
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            Logger.info('API:RES', `✅ ${method} ${url} (${response.status}) - ${duration}ms [cid=${serverCid}]`);
            EventBus.emit('api:success', historyEntry);
            return response;
        } catch (err) {
            const duration = Math.round(performance.now() - start);
            this.activeRequests = Math.max(0, this.activeRequests - 1);
            Logger.error('API:ERR', `💥 ${method} ${url} failed after ${duration}ms: ${err.message}`);
            EventBus.emit('api:error', { method, url, durationMs: duration, error: err.message, correlationId: cid });
            throw err;
        }
    }

    async getJson(url, options = {}) {
        const res = await this.request(url, { ...options, method: 'GET' });
        return await res.json();
    }

    async postJson(url, body, options = {}) {
        const res = await this.request(url, {
            ...options,
            method: 'POST',
            body: typeof body === 'string' ? body : JSON.stringify(body)
        });
        return await res.json();
    }

    getHistory() {
        return [...this.history];
    }

    clearHistory() {
        this.history = [];
    }
}

export const ApiClient = new ApiClientService();
