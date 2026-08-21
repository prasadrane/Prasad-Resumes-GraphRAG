/**
 * generator.js — ATS Resume Tailoring Generator Controller.
 * Manages Tailor Form, Job URL auto-scraping, ATS match score gauge, and SSE generator stream.
 */

import { Logger } from '../core/logger.js';
import { EventBus } from '../core/bus.js';
import { ApiClient } from '../core/api.js';
import { Utils } from '../core/utils.js';
import { PipelineController } from './pipeline.js';
import { PreviewDrawerController } from './preview.js';
import { DefaultResumeController } from './default_resume.js';

export const GeneratorController = {
    form: null,
    urlInput: null,
    companyInput: null,
    jdInput: null,
    agenticToggle: null,
    jdCharCount: null,
    generateBtn: null,
    checkAtsBtn: null,
    formAlert: null,

    // ATS Score Card Elements
    atsContainer: null,
    atsScoreValue: null,
    atsGaugeFill: null,
    atsCoveredChips: null,
    atsMissingChips: null,

    init() {
        this.form = document.getElementById('resume-form');
        this.urlInput = document.getElementById('url-input');
        this.companyInput = document.getElementById('company-input');
        this.jdInput = document.getElementById('jd-input');
        this.agenticToggle = document.getElementById('agentic-mode-toggle');
        this.jdCharCount = document.getElementById('jd-char-count');
        this.generateBtn = document.getElementById('generate-btn');
        this.checkAtsBtn = document.getElementById('check-ats-btn');
        this.formAlert = document.getElementById('form-alert');

        this.atsContainer = document.getElementById('ats-score-container');
        this.atsScoreValue = document.getElementById('ats-score-value');
        this.atsGaugeFill = document.getElementById('ats-gauge-fill');
        this.atsCoveredChips = document.getElementById('ats-covered-chips');
        this.atsMissingChips = document.getElementById('ats-missing-chips');

        if (this.jdInput) {
            this.jdInput.addEventListener('input', () => this.updateCharCount());
        }
        if (this.form) {
            this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        }
        if (this.checkAtsBtn) {
            this.checkAtsBtn.addEventListener('click', () => this.checkATSScore());
        }

        Logger.info('GENERATOR', 'GeneratorController initialized.');
    },

    updateCharCount() {
        if (!this.jdInput || !this.jdCharCount) return;
        const len = this.jdInput.value.length;
        this.jdCharCount.textContent = `${len.toLocaleString()} / 10,000 chars`;
        this.jdCharCount.style.color = len > 10000 ? 'var(--md-sys-color-error)' : 'var(--md-sys-color-on-surface-variant)';
    },

    async checkATSScore() {
        const jd = this.jdInput ? this.jdInput.value.trim() : '';
        const masterResume = DefaultResumeController.rawTextarea ? DefaultResumeController.rawTextarea.value : '';
        if (!jd) {
            Utils.showAlert('Please paste a Job Description first to check the ATS Match Score.', 'error', this.formAlert);
            Utils.playTone('error');
            return;
        }

        try {
            const data = await ApiClient.postJson('/api/ats-score', {
                resume_text: masterResume || jd,
                jd_text: jd
            });
            this.renderATSScore(data.overall_score, data.covered_keywords, data.missing_keywords);
            EventBus.emit('ats:scored', data);
            Utils.playTone('pop');
        } catch (err) {
            Logger.warn('GENERATOR', 'ATS Score check failed:', err);
        }
    },

    renderATSScore(score, covered, missing) {
        if (!this.atsContainer) return;
        this.atsContainer.classList.remove('hidden');

        const scoreVal = Math.round(score || 0);
        if (this.atsScoreValue) this.atsScoreValue.textContent = `${scoreVal}%`;

        // Circumference for r=40 is ~251.2
        const circumference = 251.2;
        const offset = circumference - (scoreVal / 100) * circumference;
        if (this.atsGaugeFill) {
            this.atsGaugeFill.style.strokeDashoffset = offset;
            this.atsGaugeFill.className = `ats-gauge-progress ${scoreVal >= 75 ? 'high' : scoreVal >= 50 ? 'med' : 'low'}`;
        }

        if (this.atsCoveredChips) {
            this.atsCoveredChips.innerHTML = '<strong>Covered:</strong> ' +
                (covered || []).map(k => `<span class="chip-kw covered">✓ ${Utils.escapeHtml(k)}</span>`).join(' ');
        }

        if (this.atsMissingChips) {
            this.atsMissingChips.innerHTML = '<strong>Missing:</strong> ' +
                (missing || []).map(k => `<span class="chip-kw missing" title="Click to insert into JD">+ ${Utils.escapeHtml(k)}</span>`).join(' ');
        }

        if (scoreVal >= 85) {
            Utils.triggerConfetti();
        }
    },

    async handleSubmit(e) {
        e.preventDefault();
        const company = this.companyInput ? this.companyInput.value.trim() : '';
        const url = this.urlInput ? this.urlInput.value.trim() : '';
        const jd = this.jdInput ? this.jdInput.value.trim() : '';
        const isAgentic = this.agenticToggle ? this.agenticToggle.checked : true;

        if (!company && !url) {
            Utils.showAlert('Please provide a target company name or job URL.', 'error', this.formAlert);
            Utils.playTone('error');
            return;
        }

        Utils.hideAlert(this.formAlert);
        this.setLoading(true);
        PipelineController.start();

        try {
            const endpoint = (isAgentic || url) ? '/api/stream-agent-tailor' : '/api/generate-stream';
            const bodyPayload = (isAgentic || url)
                ? { company, url: url || null, jd_text: jd, max_iterations: 2, min_score: 90.0 }
                : { company, jd_text: jd };

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(bodyPayload),
            });

            if (!response.ok) throw new Error(`Generation failed (${response.status})`);

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });
                const blocks = buffer.split('\n\n');
                buffer = blocks.pop(); // Keep partial trailing chunk

                for (let block of blocks) {
                    block = block.trim();
                    if (!block) continue;

                    const dataLines = block
                        .split('\n')
                        .filter(l => l.startsWith('data:'))
                        .map(l => l.replace(/^data:\s*/, ''))
                        .join('\n');

                    if (!dataLines) continue;

                    try {
                        const stepData = JSON.parse(dataLines);
                        PipelineController.update(stepData);

                        const payload = stepData.payload || stepData.data || stepData.detail;
                        if (stepData.step === 'complete' && payload) {
                            PreviewDrawerController.open(payload);
                            EventBus.emit('resume:tailored_ready', payload);
                            if (payload.final_score && this.renderATSScore) {
                                const breakdown = payload.breakdown || {};
                                this.renderATSScore(
                                    payload.final_score,
                                    breakdown.matched_keywords || [],
                                    breakdown.missing_keywords || []
                                );
                            } else if (jd) {
                                this.checkATSScore();
                            }
                        }
                    } catch (parseErr) {
                        Logger.warn('GENERATOR', 'SSE parse error on block:', parseErr);
                    }
                }
            }
        } catch (err) {
            Utils.showAlert(`Generation error: ${err.message}`, 'error', this.formAlert);
            PipelineController.fail();
        } finally {
            this.setLoading(false);
        }
    },

    setLoading(isLoading) {
        if (!this.generateBtn) return;
        this.generateBtn.disabled = isLoading;
        const textSpan = this.generateBtn.querySelector('.btn-text');
        if (textSpan) textSpan.textContent = isLoading ? 'Synthesizing Resume...' : 'Generate Tailored Resume';
    }
};
