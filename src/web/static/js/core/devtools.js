/**
 * devtools.js — Developer CLI Superpowers, Keyboard Shortcuts & Diagnostic Bundle Exporter.
 */

import { Logger, LogLevel } from './logger.js';
import { EventBus } from './bus.js';
import { ApiClient } from './api.js';
import { Utils } from './utils.js';

class DevToolsService {
    constructor() {
        this.state = {
            activeTab: 'default',
            masterResumeLoaded: false,
            tailoredData: null,
            atsBreakdown: null,
            telemetry: null,
            diagnosticsOpen: false
        };
    }

    init() {
        // Expose global debug interface
        window.dbg = {
            state: this.state,
            logger: Logger,
            bus: EventBus,
            network: ApiClient,
            utils: Utils,
            logLevel: (level) => Logger.setLevel(level),
            getRecentLogs: () => Logger.getLogs(),
            clearLogs: () => Logger.clear(),
            exportBundle: () => this.exportBundle(),
            triggerConfetti: () => Utils.triggerConfetti(),
            toggleSound: () => Utils.toggleSound(),
            playTone: (t) => Utils.playTone(t),
            spyBus: (enable = true) => EventBus.spy(enable)
        };

        window.setLogLevel = (lvl) => Logger.setLevel(lvl);

        // Register Global Keyboard Shortcuts
        window.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.shiftKey) {
                const key = e.key.toUpperCase();
                if (key === 'D') {
                    e.preventDefault();
                    EventBus.emit('diag:toggle');
                } else if (key === 'L') {
                    e.preventDefault();
                    this.cycleLogLevel();
                } else if (key === 'E') {
                    e.preventDefault();
                    this.exportBundle();
                } else if (key === 'M') {
                    e.preventDefault();
                    const muted = Utils.toggleSound();
                    EventBus.emit('sound:toggled', muted);
                }
            }
        });

        // Listen for core state events
        EventBus.on('tab:changed', (tab) => { this.state.activeTab = tab; });
        EventBus.on('resume:master_loaded', () => { this.state.masterResumeLoaded = true; });
        EventBus.on('resume:tailored_ready', (data) => { this.state.tailoredData = data; });
        EventBus.on('ats:scored', (breakdown) => { this.state.atsBreakdown = breakdown; });
        EventBus.on('telemetry:update', (telemetry) => { this.state.telemetry = telemetry; });

        Logger.info('App', '🛠️ DevTools initialized. Type `dbg` in console or press `Ctrl+Shift+D` for Diagnostics.');
    }

    cycleLogLevel() {
        const levels = [LogLevel.INFO, LogLevel.DEBUG, LogLevel.WARN, LogLevel.ERROR];
        const current = Logger.currentLevel;
        const nextIdx = (levels.indexOf(current) + 1) % levels.length;
        const nextLevel = levels[nextIdx];
        Logger.setLevel(nextLevel);
    }

    exportBundle() {
        const bundle = {
            exportedAt: new Date().toISOString(),
            userAgent: navigator.userAgent,
            url: window.location.href,
            appState: this.state,
            recentLogs: Logger.getLogs(),
            networkHistory: ApiClient.getHistory(),
            performance: {
                memory: window.performance && window.performance.memory ? {
                    usedJSHeapSize: window.performance.memory.usedJSHeapSize,
                    totalJSHeapSize: window.performance.memory.totalJSHeapSize
                } : null,
                timing: window.performance ? window.performance.timing : null
            }
        };

        const jsonStr = JSON.stringify(bundle, null, 2);
        const filename = `prasad_resumes_debug_${Date.now()}.json`;
        Utils.downloadFile(filename, jsonStr);
        Logger.info('App', `📦 Diagnostic bundle downloaded: ${filename}`);
        Utils.playTone('chime');
        return bundle;
    }
}

export const DevTools = new DevToolsService();
