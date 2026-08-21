/**
 * bus.js — Lightweight Typed EventBus for Loose Coupling.
 * Supports cross-module communication, listener cleanup, and developer spy mode.
 */

import { Logger } from './logger.js';

class EventBusService {
    constructor() {
        this.events = new Map();
        this.isSpying = false;
    }

    on(event, handler) {
        if (!this.events.has(event)) {
            this.events.set(event, new Set());
        }
        this.events.get(event).add(handler);
        return () => this.off(event, handler);
    }

    off(event, handler) {
        if (this.events.has(event)) {
            this.events.get(event).delete(handler);
        }
    }

    emit(event, payload = null) {
        if (this.isSpying) {
            Logger.debug('BUS', `📢 Event: '${event}'`, payload);
        }

        if (this.events.has(event)) {
            this.events.get(event).forEach(handler => {
                try {
                    handler(payload);
                } catch (err) {
                    Logger.error('BUS', `Error in handler for '${event}': ${err.message}`, err);
                }
            });
        }
    }

    spy(enable = true) {
        this.isSpying = enable;
        Logger.info('BUS', `EventBus spy mode: ${enable ? 'ENABLED' : 'DISABLED'}`);
    }
}

export const EventBus = new EventBusService();
