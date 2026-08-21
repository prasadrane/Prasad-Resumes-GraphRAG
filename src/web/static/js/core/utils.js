/**
 * utils.js — Pure Utilities, DOM Helpers, Markdown Parser, Confetti Burst & Web Audio Synthesizer.
 */

import { Logger } from './logger.js';

let audioCtx = null;
let soundMuted = localStorage.getItem('__dbg_sound_muted__') === 'true';

export const Utils = {
    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/[&<>"']/g, (m) => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        }[m]));
    },

    dataUriToBlobUrl(dataUri) {
        if (!dataUri || typeof dataUri !== 'string' || !dataUri.startsWith('data:application/pdf;base64,')) {
            return dataUri;
        }
        try {
            const base64Data = dataUri.split(',')[1];
            const byteCharacters = atob(base64Data);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: 'application/pdf' });
            return URL.createObjectURL(blob);
        } catch (e) {
            Logger.warn('RESUME', 'Failed to convert data URI to blob URL:', e);
            return dataUri;
        }
    },

    formatMarkdown(text) {
        if (!text) return '';
        if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
            return marked.parse(text);
        }
        let html = this.escapeHtml(text);
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/__(.*?)__/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        html = html.replace(/`(.*?)`/g, '<code>$1</code>');
        const lines = html.split('\n');
        let inList = false;
        let result = '';
        for (let line of lines) {
            const h3Match = line.match(/^###\s+(.*)/);
            const h2Match = line.match(/^##\s+(.*)/);
            const h1Match = line.match(/^#\s+(.*)/);
            const bulletMatch = line.match(/^[\s]*[•\*\-]\s+(.*)/);

            if (bulletMatch) {
                if (!inList) { result += '<ul>'; inList = true; }
                result += `<li>${bulletMatch[1]}</li>`;
            } else {
                if (inList) { result += '</ul>'; inList = false; }
                if (h3Match) {
                    result += `<h3>${h3Match[1]}</h3>`;
                } else if (h2Match) {
                    result += `<h2>${h2Match[1]}</h2>`;
                } else if (h1Match) {
                    result += `<h1>${h1Match[1]}</h1>`;
                } else if (line.trim() === '') {
                    result += '<br>';
                } else {
                    result += `<p>${line}</p>`;
                }
            }
        }
        if (inList) result += '</ul>';
        return result;
    },

    showAlert(msg, type, alertEl) {
        if (!alertEl) return;
        alertEl.textContent = msg;
        alertEl.className = `m3-alert ${type}`;
    },

    hideAlert(alertEl) {
        if (!alertEl) return;
        alertEl.className = 'm3-alert hidden';
        alertEl.textContent = '';
    },

    downloadFile(filename, text) {
        const element = document.createElement('a');
        element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
        element.setAttribute('download', filename);
        element.style.display = 'none';
        document.body.appendChild(element);
        element.click();
        document.body.removeChild(element);
    },

    // ── Web Audio Synthesizer (Zero External Audio Files) ──
    isSoundMuted() {
        return soundMuted;
    },

    toggleSound() {
        soundMuted = !soundMuted;
        localStorage.setItem('__dbg_sound_muted__', soundMuted);
        Logger.info('App', `Audio sound effects: ${soundMuted ? 'MUTED' : 'ACTIVE'}`);
        return soundMuted;
    },

    playTone(type = 'pop') {
        if (soundMuted) return;
        try {
            if (!audioCtx) {
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                if (AudioContext) audioCtx = new AudioContext();
            }
            if (!audioCtx) return;
            if (audioCtx.state === 'suspended') {
                audioCtx.resume();
            }

            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();
            osc.connect(gain);
            gain.connect(audioCtx.destination);

            const now = audioCtx.currentTime;

            if (type === 'pop') {
                // Crisp UI click pop
                osc.type = 'sine';
                osc.frequency.setValueAtTime(520, now);
                osc.frequency.exponentialRampToValueAtTime(880, now + 0.05);
                gain.gain.setValueAtTime(0.12, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.06);
                osc.start(now);
                osc.stop(now + 0.06);
            } else if (type === 'chime') {
                // Pleasant harmonic success chime
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(659.25, now); // E5
                osc.frequency.setValueAtTime(880.00, now + 0.08); // A5
                gain.gain.setValueAtTime(0.15, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
                osc.start(now);
                osc.stop(now + 0.35);
            } else if (type === 'error') {
                // Low thud
                osc.type = 'sawtooth';
                osc.frequency.setValueAtTime(220, now);
                osc.frequency.exponentialRampToValueAtTime(110, now + 0.15);
                gain.gain.setValueAtTime(0.1, now);
                gain.gain.exponentialRampToValueAtTime(0.001, now + 0.16);
                osc.start(now);
                osc.stop(now + 0.16);
            }
        } catch (e) {
            // Non-fatal audio fallback
        }
    },

    // ── Festive Confetti Burst (Canvas Micro-Animation) ──
    triggerConfetti() {
        const canvas = document.createElement('canvas');
        canvas.style.position = 'fixed';
        canvas.style.top = '0';
        canvas.style.left = '0';
        canvas.style.width = '100vw';
        canvas.style.height = '100vh';
        canvas.style.pointerEvents = 'none';
        canvas.style.zIndex = '9999';
        document.body.appendChild(canvas);

        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;

        const colors = ['#a8c7fa', '#38bdf8', '#34d399', '#a78bfa', '#f59e0b', '#ec4899'];
        const particles = Array.from({ length: 70 }, () => ({
            x: canvas.width / 2 + (Math.random() - 0.5) * 200,
            y: canvas.height / 3,
            vx: (Math.random() - 0.5) * 12,
            vy: (Math.random() - 0.8) * 10 - 4,
            size: Math.random() * 8 + 4,
            color: colors[Math.floor(Math.random() * colors.length)],
            rotation: Math.random() * 360,
            vRot: (Math.random() - 0.5) * 10,
            alpha: 1
        }));

        let animationFrame;
        const render = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            let active = false;

            for (const p of particles) {
                p.x += p.vx;
                p.y += p.vy;
                p.vy += 0.35; // Gravity
                p.rotation += p.vRot;
                p.alpha -= 0.012;

                if (p.alpha > 0) {
                    active = true;
                    ctx.save();
                    ctx.translate(p.x, p.y);
                    ctx.rotate((p.rotation * Math.PI) / 180);
                    ctx.globalAlpha = p.alpha;
                    ctx.fillStyle = p.color;
                    ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
                    ctx.restore();
                }
            }

            if (active) {
                animationFrame = requestAnimationFrame(render);
            } else {
                cancelAnimationFrame(animationFrame);
                canvas.remove();
            }
        };
        render();
    }
};
