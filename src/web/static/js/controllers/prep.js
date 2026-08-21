/**
 * prep.js — STAR Behavioral & Technical Interview Prep Controller.
 */

import { Logger } from '../core/logger.js';
import { ApiClient } from '../core/api.js';
import { Utils } from '../core/utils.js';

export const InterviewPrepController = {
    form: null,
    jdInput: null,
    container: null,
    btn: null,

    init() {
        this.form = document.getElementById('prep-form');
        this.jdInput = document.getElementById('prep-jd-input');
        this.container = document.getElementById('prep-questions-container');
        this.btn = document.getElementById('generate-prep-btn');

        if (this.form) this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        Logger.info('RESUME', 'InterviewPrepController initialized.');
    },

    async handleSubmit(e) {
        e.preventDefault();
        const jd = this.jdInput ? this.jdInput.value.trim() : '';
        if (this.btn) this.btn.disabled = true;
        if (this.container) this.container.innerHTML = '<p style="color: var(--md-sys-color-primary);">Predicting interview questions & generating STAR talking points...</p>';
        Utils.playTone('pop');

        try {
            const data = await ApiClient.postJson('/api/interview-prep', {
                jd_text: jd || 'Cloud architecture, microservices, and leadership.'
            });

            let html = '';
            (data.questions || []).forEach((q, idx) => {
                const points = (data.talking_points && data.talking_points[q]) || ['Demonstrated production leadership and metrics delivery.'];
                html += `
                    <div class="star-prep-card">
                        <div class="star-question-header">
                            <span>Q${idx + 1}: ${Utils.escapeHtml(q)}</span>
                        </div>
                        <div class="star-grid">
                            <div class="star-box">
                                <div class="star-label s"><span class="material-symbols-outlined" style="font-size: 14px;">place</span> Situation</div>
                                <div>Production modernization & high-scale enterprise workloads.</div>
                            </div>
                            <div class="star-box">
                                <div class="star-label t"><span class="material-symbols-outlined" style="font-size: 14px;">assignment</span> Task</div>
                                <div>Decouple legacy monoliths with zero downtime.</div>
                            </div>
                            <div class="star-box">
                                <div class="star-label a"><span class="material-symbols-outlined" style="font-size: 14px;">play_arrow</span> Action</div>
                                <div>${Utils.escapeHtml(points[0] || 'Engineered automated microservices.')}</div>
                            </div>
                            <div class="star-box">
                                <div class="star-label r"><span class="material-symbols-outlined" style="font-size: 14px;">check_circle</span> Result</div>
                                <div>${Utils.escapeHtml(points[1] || 'Reduced query latency by 70% and lowered infrastructure costs.')}</div>
                            </div>
                        </div>
                    </div>
                `;
            });
            if (this.container) this.container.innerHTML = html;
            Utils.playTone('chime');
        } catch (err) {
            Utils.playTone('error');
            if (this.container) this.container.innerHTML = `<p style="color: var(--md-sys-color-error);">Error: ${err.message}</p>`;
        } finally {
            if (this.btn) this.btn.disabled = false;
        }
    }
};
