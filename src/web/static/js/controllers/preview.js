/**
 * preview.js — Tailored Resume Preview Drawer, Human-in-the-Loop Diff Inspector & Export Hub.
 */

import { Logger } from '../core/logger.js';
import { EventBus } from '../core/bus.js';
import { ApiClient } from '../core/api.js';
import { Utils } from '../core/utils.js';

export const PreviewDrawerController = {
    section: null,
    pdfIframe: null,
    rawTextarea: null,
    saveBtn: null,
    closeBtn: null,
    openLink: null,
    applyDiffsBtn: null,

    currentPages: 2,
    page1Btn: null,
    page2Btn: null,

    togglePdfBtn: null,
    toggleEditBtn: null,
    toggleDiffBtn: null,

    pdfContainer: null,
    editContainer: null,
    diffContainer: null,
    diffPanel: null,

    // Export Hub
    exportBtn: null,
    exportMenu: null,

    // Impact Scorer
    impactBar: null,
    impactDesc: null,
    impactBadge: null,

    currentData: null,
    activeDiffs: [],

    init() {
        this.section = document.getElementById('preview-section');
        this.pdfIframe = document.getElementById('pdf-iframe');
        this.rawTextarea = document.getElementById('raw-edit-textarea');
        this.saveBtn = document.getElementById('save-rerender-btn');
        this.closeBtn = document.getElementById('close-preview-btn');
        this.openLink = document.getElementById('preview-open-link');
        this.applyDiffsBtn = document.getElementById('apply-selected-diffs-btn');

        this.page1Btn = document.getElementById('preview-page-1-btn');
        this.page2Btn = document.getElementById('preview-page-2-btn');

        this.togglePdfBtn = document.getElementById('toggle-pdf-btn');
        this.toggleEditBtn = document.getElementById('toggle-edit-btn');
        this.toggleDiffBtn = document.getElementById('toggle-diff-btn');

        this.pdfContainer = document.getElementById('pdf-view-container');
        this.editContainer = document.getElementById('edit-view-container');
        this.diffContainer = document.getElementById('diff-view-container');
        this.diffPanel = document.getElementById('diff-content-panel');

        this.exportBtn = document.getElementById('export-hub-btn');
        this.exportMenu = document.getElementById('export-hub-menu');

        this.impactBar = document.getElementById('bullet-impact-bar');
        this.impactDesc = document.getElementById('impact-score-desc');
        this.impactBadge = document.getElementById('impact-badge');

        if (this.page1Btn) this.page1Btn.addEventListener('click', () => this.switchPages(1));
        if (this.page2Btn) this.page2Btn.addEventListener('click', () => this.switchPages(2));

        if (this.togglePdfBtn) this.togglePdfBtn.addEventListener('click', () => this.switchMode('pdf'));
        if (this.toggleEditBtn) this.toggleEditBtn.addEventListener('click', () => this.switchMode('edit'));
        if (this.toggleDiffBtn) this.toggleDiffBtn.addEventListener('click', () => this.switchMode('diff'));

        if (this.closeBtn) this.closeBtn.addEventListener('click', () => this.close());
        if (this.saveBtn) this.saveBtn.addEventListener('click', () => this.handleSave());
        if (this.applyDiffsBtn) this.applyDiffsBtn.addEventListener('click', () => this.applySelectedDiffs());

        if (this.rawTextarea) {
            this.rawTextarea.addEventListener('input', () => this.analyzeImpact());
        }

        // Export Dropdown Trigger
        if (this.exportBtn && this.exportMenu) {
            this.exportBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.exportMenu.classList.toggle('hidden');
            });
            document.addEventListener('click', () => this.exportMenu.classList.add('hidden'));

            this.exportMenu.querySelectorAll('.export-item').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const fmt = btn.getAttribute('data-format');
                    this.handleExport(fmt);
                    this.exportMenu.classList.add('hidden');
                });
            });
        }

        Logger.info('RESUME', 'PreviewDrawerController initialized.');
    },

    async switchPages(pages) {
        this.currentPages = pages;
        if (this.page1Btn && this.page2Btn) {
            this.page1Btn.classList.toggle('active', pages === 1);
            this.page2Btn.classList.toggle('active', pages === 2);
        }
        Utils.playTone('pop');
        await this.handleSave();
    },

    open(data) {
        this.currentData = data;
        this.activeDiffs = data.diffs || [];
        if (this.section) this.section.classList.remove('hidden');
        const pdfUrl = Utils.dataUriToBlobUrl(data.pdf_data_uri || data.pdf_url);
        if (this.pdfIframe && pdfUrl) this.pdfIframe.src = pdfUrl;
        if (this.rawTextarea && data.raw_resume) {
            this.rawTextarea.value = data.raw_resume;
            this.analyzeImpact();
        }
        if (this.openLink && pdfUrl) this.openLink.href = pdfUrl;

        if (data.pages) {
            this.currentPages = data.pages;
            if (this.page1Btn && this.page2Btn) {
                this.page1Btn.classList.toggle('active', data.pages === 1);
                this.page2Btn.classList.toggle('active', data.pages === 2);
            }
        }

        this.switchMode('pdf');
        if (this.section) this.section.scrollIntoView({ behavior: 'smooth' });
    },

    close() {
        if (this.section) this.section.classList.add('hidden');
        Utils.playTone('pop');
    },

    switchMode(mode) {
        Utils.playTone('pop');
        [this.togglePdfBtn, this.toggleEditBtn, this.toggleDiffBtn].forEach(btn => btn && btn.classList.remove('active'));
        [this.pdfContainer, this.editContainer, this.diffContainer].forEach(c => c && c.classList.add('hidden'));

        if (mode === 'pdf') {
            if (this.togglePdfBtn) this.togglePdfBtn.classList.add('active');
            if (this.pdfContainer) this.pdfContainer.classList.remove('hidden');
        } else if (mode === 'edit') {
            if (this.toggleEditBtn) this.toggleEditBtn.classList.add('active');
            if (this.editContainer) this.editContainer.classList.remove('hidden');
        } else if (mode === 'diff') {
            if (this.toggleDiffBtn) this.toggleDiffBtn.classList.add('active');
            if (this.diffContainer) this.diffContainer.classList.remove('hidden');
            this.renderDiff();
        }
    },

    async renderDiff() {
        if (!this.diffPanel) return;

        // Structured human-in-the-loop diff cards from subagents
        if (this.activeDiffs && this.activeDiffs.length > 0) {
            let html = '<div class="diff-cards-list" style="display: flex; flex-direction: column; gap: 1rem;">';
            this.activeDiffs.forEach((diff, idx) => {
                html += `
                    <div class="diff-card" style="padding: 1rem; border-radius: 8px; background: var(--md-sys-color-surface-container-high); border: 1px solid var(--md-sys-color-outline-variant);">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <span class="chip-kw covered"><strong>${Utils.escapeHtml(diff.role_title || 'Role')}</strong></span>
                            <label style="display: flex; align-items: center; gap: 0.4rem; font-size: 0.85rem; cursor: pointer;">
                                <input type="checkbox" class="diff-accept-checkbox" data-index="${idx}" checked>
                                <span>Accept Change</span>
                            </label>
                        </div>
                        <div style="margin-bottom: 0.5rem; padding: 0.5rem; background: rgba(239, 68, 68, 0.08); border-left: 3px solid #ef4444; border-radius: 4px; font-size: 0.9rem;">
                            <div style="font-size: 0.75rem; color: #ef4444; font-weight: bold; margin-bottom: 2px;">ORIGINAL BULLET:</div>
                            <span style="text-decoration: line-through; color: var(--md-sys-color-on-surface-variant);">${Utils.escapeHtml(diff.original_bullet || diff.original || '')}</span>
                        </div>
                        <div style="padding: 0.5rem; background: rgba(52, 211, 153, 0.08); border-left: 3px solid #34d399; border-radius: 4px; font-size: 0.9rem;">
                            <div style="font-size: 0.75rem; color: #34d399; font-weight: bold; margin-bottom: 2px;">REFINED SURGICAL BULLET:</div>
                            <span style="color: var(--md-sys-color-on-surface); font-weight: 500;">${Utils.escapeHtml(diff.refined_bullet || diff.refined || '')}</span>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            this.diffPanel.innerHTML = html;
            return;
        }

        // Fallback to text diff
        this.diffPanel.innerHTML = '<p style="color: var(--md-sys-color-on-surface-variant);">Computing visual diff against master resume...</p>';
        try {
            const data = await ApiClient.postJson('/api/diff-resume', {
                tailored_text: this.rawTextarea.value
            });

            if (data.diffs && data.diffs.length > 0) {
                this.activeDiffs = data.diffs;
                this.renderDiff();
            } else {
                this.diffPanel.innerHTML = '<p>No differences detected vs master resume.</p>';
            }
        } catch (err) {
            this.diffPanel.innerHTML = `<p style="color: var(--md-sys-color-error);">Failed to load diff: ${err.message}</p>`;
        }
    },

    async applySelectedDiffs() {
        if (!this.applyDiffsBtn || !this.rawTextarea) return;
        const checkboxes = this.diffPanel.querySelectorAll('.diff-accept-checkbox');
        const approved = [];
        checkboxes.forEach(cb => {
            if (cb.checked) {
                const idx = parseInt(cb.getAttribute('data-index'), 10);
                if (!isNaN(idx) && this.activeDiffs[idx]) {
                    approved.push(this.activeDiffs[idx]);
                }
            }
        });

        this.applyDiffsBtn.disabled = true;
        const btnText = this.applyDiffsBtn.querySelector('.btn-text');
        const origText = btnText ? btnText.textContent : 'Apply Selected Diffs';
        if (btnText) btnText.textContent = 'Applying & Re-rendering...';

        try {
            const data = await ApiClient.postJson('/api/apply-diffs', {
                raw_resume: this.rawTextarea.value,
                approved_diffs: approved,
                target_pages: this.currentPages || 2,
                company: this.currentData ? (this.currentData.company || 'Tailored') : 'Tailored',
            });

            this.rawTextarea.value = data.raw_resume;
            const pdfUrl = Utils.dataUriToBlobUrl(data.pdf_url);
            if (this.pdfIframe && pdfUrl) this.pdfIframe.src = pdfUrl;
            if (this.openLink && pdfUrl) this.openLink.href = pdfUrl;
            this.switchMode('pdf');
            Utils.playTone('chime');
            EventBus.emit('diff:applied', data);
        } catch (err) {
            Utils.playTone('error');
            alert(`Error applying diffs: ${err.message}`);
        } finally {
            this.applyDiffsBtn.disabled = false;
            if (btnText) btnText.textContent = origText;
        }
    },

    analyzeImpact() {
        if (!this.rawTextarea || !this.impactDesc || !this.impactBadge) return;
        const text = this.rawTextarea.value;
        const metrics = text.match(/\b\d+[\d,.]*(?:%|\+|K|M|B|x|ms|s|sec)?\b/gi) || [];
        const actionVerbs = text.match(/\b(Architected|Spearheaded|Engineered|Modernized|Optimized|Decoupled|Delivered|Pioneered)\b/gi) || [];

        if (metrics.length >= 5 && actionVerbs.length >= 4) {
            this.impactDesc.textContent = `High Impact (${metrics.length} metrics, ${actionVerbs.length} action verbs detected)`;
            this.impactBadge.className = 'impact-badge high';
            this.impactBadge.innerHTML = '<span class="material-symbols-outlined" style="font-size: 14px;">bolt</span> High Impact (X-Y-Z)';
        } else {
            this.impactDesc.textContent = `Moderate Impact (${metrics.length} metrics, ${actionVerbs.length} verbs)`;
            this.impactBadge.className = 'impact-badge med';
            this.impactBadge.innerHTML = '<span class="material-symbols-outlined" style="font-size: 14px;">insights</span> Moderate Impact';
        }
    },

    async handleExport(format) {
        const raw = this.rawTextarea ? this.rawTextarea.value : '';
        if (format === 'pdf') {
            if (this.currentData) {
                const pdfUrl = Utils.dataUriToBlobUrl(this.currentData.pdf_data_uri || this.currentData.pdf_url);
                if (pdfUrl) {
                    const a = document.createElement('a');
                    a.href = pdfUrl;
                    a.download = 'Prasad_Rane_Resume.pdf';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    Utils.playTone('chime');
                }
            }
            return;
        }

        try {
            const data = await ApiClient.postJson(`/api/export-markup?format=${format}`, {
                raw_text: raw
            });
            Utils.downloadFile(data.filename, data.content);
            Utils.playTone('chime');
            Logger.info('RESUME', `Exported resume as ${format.toUpperCase()}`);
        } catch (err) {
            Logger.warn('RESUME', 'Export failed:', err);
        }
    },

    async handleSave() {
        if (!this.rawTextarea || !this.saveBtn) return;
        const content = this.rawTextarea.value;
        this.saveBtn.disabled = true;

        try {
            const data = await ApiClient.postJson('/api/save-edit', {
                raw_text: content,
                txt_url: this.currentData ? this.currentData.txt_url : null,
                pages: this.currentPages || 2,
            });
            this.currentData = data;
            const pdfUrl = Utils.dataUriToBlobUrl(data.pdf_data_uri || data.pdf_url);
            if (this.pdfIframe && pdfUrl) this.pdfIframe.src = pdfUrl;
            if (this.openLink && pdfUrl) this.openLink.href = pdfUrl;
            this.switchMode('pdf');
            Utils.playTone('chime');
        } catch (err) {
            Utils.playTone('error');
            alert(`Error saving edit: ${err.message}`);
        } finally {
            this.saveBtn.disabled = false;
        }
    }
};
