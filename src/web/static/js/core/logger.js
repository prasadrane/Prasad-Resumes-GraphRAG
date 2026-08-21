/**
 * logger.js — High-Contrast, Colorized Debug Logger with Memory Ring Buffer.
 * Provides configurable log levels, Material Design 3 console badges,
 * and live log stream tracking for developers.
 */

export const LogLevel = {
    DEBUG: 0,
    INFO: 1,
    WARN: 2,
    ERROR: 3,
    OFF: 4
};

const LEVEL_NAMES = ['DEBUG', 'INFO', 'WARN', 'ERROR', 'OFF'];

const BADGE_STYLES = {
    APP: 'background: #4f46e5; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-weight: 600;',
    API: 'background: #0284c7; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-weight: 600;',
    'API:REQ': 'background: #0ea5e9; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-weight: 600;',
    'API:RES': 'background: #10b981; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-weight: 600;',
    'API:ERR': 'background: #ef4444; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-weight: 600;',
    SUBAGENT: 'background: #8b5cf6; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-weight: 600;',
    BUS: 'background: #f59e0b; color: #000000; padding: 2px 6px; border-radius: 4px; font-weight: 600;',
    NAV: 'background: #3b82f6; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-weight: 600;',
    RESUME: 'background: #06b6d4; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-weight: 600;',
    GENERATOR: 'background: #ec4899; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-weight: 600;',
    CHATBOT: 'background: #a855f7; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-weight: 600;',
    DIAG: 'background: #64748b; color: #ffffff; padding: 2px 6px; border-radius: 4px; font-weight: 600;',
    DEFAULT: 'background: #334155; color: #f8fafc; padding: 2px 6px; border-radius: 4px; font-weight: 600;'
};

class LoggerService {
    constructor() {
        this.maxBuffer = 250;
        this.buffer = [];
        this.listeners = new Set();

        // Check URL parameter or localStorage for initial log level
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('debug')) {
            this.currentLevel = LogLevel.DEBUG;
        } else {
            const saved = localStorage.getItem('__dbg_log_level__');
            this.currentLevel = saved !== null ? parseInt(saved, 10) : LogLevel.INFO;
        }
    }

    setLevel(level) {
        if (typeof level === 'string') {
            const idx = LEVEL_NAMES.indexOf(level.toUpperCase());
            if (idx !== -1) this.currentLevel = idx;
        } else if (typeof level === 'number' && level >= 0 && level <= 4) {
            this.currentLevel = level;
        }
        localStorage.setItem('__dbg_log_level__', this.currentLevel);
        this.info('App', `Log level set to ${LEVEL_NAMES[this.currentLevel]}`);
    }

    getLevelName() {
        return LEVEL_NAMES[this.currentLevel];
    }

    _formatTime(d = new Date()) {
        return d.toTimeString().split(' ')[0] + '.' + String(d.getMilliseconds()).padStart(3, '0');
    }

    _log(level, subsystem, message, data = null) {
        if (level < this.currentLevel) return;

        const entry = {
            timestamp: new Date().toISOString(),
            timeStr: this._formatTime(),
            level: LEVEL_NAMES[level],
            subsystem: subsystem.toUpperCase(),
            message,
            data
        };

        this.buffer.push(entry);
        if (this.buffer.length > this.maxBuffer) {
            this.buffer.shift();
        }

        // Notify active subscribers (e.g. Diagnostics drawer live stream)
        this.listeners.forEach(cb => {
            try { cb(entry); } catch (e) { /* ignore listener err */ }
        });

        const badgeStyle = BADGE_STYLES[entry.subsystem] || BADGE_STYLES.DEFAULT;
        const timeStyle = 'color: #94a3b8; font-size: 0.85em;';

        const prefix = `%c${entry.timeStr}%c %c[${entry.subsystem}]%c ${message}`;
        const styles = [
            timeStyle,
            '',
            badgeStyle,
            ''
        ];

        if (level === LogLevel.ERROR) {
            if (data !== null) console.error(prefix, ...styles, data);
            else console.error(prefix, ...styles);
        } else if (level === LogLevel.WARN) {
            if (data !== null) console.warn(prefix, ...styles, data);
            else console.warn(prefix, ...styles);
        } else if (level === LogLevel.DEBUG) {
            if (data !== null) console.debug(prefix, ...styles, data);
            else console.debug(prefix, ...styles);
        } else {
            if (data !== null) console.log(prefix, ...styles, data);
            else console.log(prefix, ...styles);
        }
    }

    debug(subsystem, message, data = null) {
        this._log(LogLevel.DEBUG, subsystem, message, data);
    }

    info(subsystem, message, data = null) {
        this._log(LogLevel.INFO, subsystem, message, data);
    }

    warn(subsystem, message, data = null) {
        this._log(LogLevel.WARN, subsystem, message, data);
    }

    error(subsystem, message, data = null) {
        this._log(LogLevel.ERROR, subsystem, message, data);
    }

    getLogs() {
        return [...this.buffer];
    }

    clear() {
        this.buffer = [];
        this.info('App', 'Log buffer cleared.');
    }

    subscribe(listener) {
        this.listeners.add(listener);
        return () => this.listeners.delete(listener);
    }
}

export const Logger = new LoggerService();
