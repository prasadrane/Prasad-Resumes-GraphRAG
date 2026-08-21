/**
 * cover_letter.js — 1-Page Cover Letter Studio Controller.
 */

import { Logger } from '../core/logger.js';
import { ApiClient } from '../core/api.js';
import { Utils } from '../core/utils.js';

export const CoverLetterController = {
    form: null,
    companyInput: null,
    roleInput: null,
    jdInput: null,
    bodyEl: null,
    copyBtn: null,
    generateBtn: null,

    init() {
        this.form = document.getElementById('cover-letter-form');
        this.companyInput = document.getElementById('cover-company-input');
        this.roleInput = document.getElementById('cover-role-input');
        this.jdInput = document.getElementById('cover-jd-input');
        this.bodyEl = document.getElementById('cover-letter-body');
        this.copyBtn = document.getElementById('copy-cover-btn');
        this.generateBtn = document.getElementById('generate-cover-btn');

        if (this.form) this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        if (this.copyBtn) this.copyBtn.addEventListener('click', () => this.copyToClipboard());

        Logger.info('RESUME', 'CoverLetterController initialized.');
    },

    async handleSubmit(e) {
        e.preventDefault();
        const company = this.companyInput ? this.companyInput.value.trim() : '';
        const role = this.roleInput ? this.roleInput.value.trim() : '';
        const jd = this.jdInput ? this.jdInput.value.trim() : '';

        if (!company) return;
        if (this.generateBtn) this.generateBtn.disabled = true;
        Utils.playTone('pop');

        try {
            const data = await ApiClient.postJson('/api/cover-letter', {
                company,
                role_title: role,
                jd_text: jd
            });
            if (this.bodyEl) this.bodyEl.textContent = data.markdown;
            Utils.playTone('chime');
        } catch (err) {
            Utils.playTone('error');
            if (this.bodyEl) this.bodyEl.textContent = `Error: ${err.message}`;
        } finally {
            if (this.generateBtn) this.generateBtn.disabled = false;
        }
    },

    copyToClipboard() {
        if (!this.bodyEl) return;
        navigator.clipboard.writeText(this.bodyEl.textContent).then(() => {
            Utils.playTone('pop');
            const span = this.copyBtn.querySelector('span:last-child');
            if (span) {
                const orig = span.textContent;
                span.textContent = 'Copied! ✨';
                setTimeout(() => span.textContent = orig, 2000);
            }
        });
    }
};
