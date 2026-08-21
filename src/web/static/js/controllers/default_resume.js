/**
 * default_resume.js — Master Default Resume Controller.
 * Manages PDF preview iframe, raw Markdown editor, 1p/2p budget toggle, and re-rendering.
 */

import { Logger } from '../core/logger.js';
import { EventBus } from '../core/bus.js';
import { ApiClient } from '../core/api.js';
import { Utils } from '../core/utils.js';

export const DefaultResumeController = {
    isLoaded: false,
    currentPages: 2,
    page1Btn: null,
    page2Btn: null,
    togglePdfBtn: null,
    toggleEditBtn: null,
    pdfContainer: null,
    editContainer: null,
    pdfIframe: null,
    rawTextarea: null,
    downloadLink: null,
    openLink: null,
    saveBtn: null,

    init() {
        this.page1Btn = document.getElementById('default-page-1-btn');
        this.page2Btn = document.getElementById('default-page-2-btn');
        this.togglePdfBtn = document.getElementById('default-toggle-pdf-btn');
        this.toggleEditBtn = document.getElementById('default-toggle-edit-btn');
        this.pdfContainer = document.getElementById('default-pdf-container');
        this.editContainer = document.getElementById('default-edit-container');
        this.pdfIframe = document.getElementById('default-pdf-iframe');
        this.rawTextarea = document.getElementById('default-raw-textarea');
        this.downloadLink = document.getElementById('default-download-link');
        this.openLink = document.getElementById('default-open-link');
        this.saveBtn = document.getElementById('default-save-rerender-btn');

        if (this.page1Btn) this.page1Btn.addEventListener('click', () => this.switchPages(1));
        if (this.page2Btn) this.page2Btn.addEventListener('click', () => this.switchPages(2));
        if (this.togglePdfBtn) this.togglePdfBtn.addEventListener('click', () => this.switchMode('pdf'));
        if (this.toggleEditBtn) this.toggleEditBtn.addEventListener('click', () => this.switchMode('edit'));
        if (this.saveBtn) this.saveBtn.addEventListener('click', () => this.handleSave());

        EventBus.on('tab:changed', (tab) => {
            if (tab === 'default' && !this.isLoaded) {
                this.loadDefaultResume();
            }
        });

        Logger.info('RESUME', 'DefaultResumeController initialized.');
    },

    async handleSave() {
        if (!this.rawTextarea || !this.saveBtn) return;
        const content = this.rawTextarea.value.trim();
        if (!content) {
            alert('Resume content cannot be empty.');
            return;
        }
        this.saveBtn.disabled = true;
        const btnText = this.saveBtn.querySelector('.btn-text');
        const origText = btnText ? btnText.textContent : 'Save & Re-render PDF';
        if (btnText) btnText.textContent = 'Rendering...';

        try {
            const data = await ApiClient.postJson('/api/save-edit', {
                raw_text: content,
                company: 'Default',
                pages: this.currentPages || 2,
            });

            const pdfUrl = Utils.dataUriToBlobUrl(data.pdf_data_uri || data.pdf_url);
            if (this.pdfIframe && pdfUrl) this.pdfIframe.src = pdfUrl;
            if (this.downloadLink && pdfUrl) this.downloadLink.href = pdfUrl;
            if (this.openLink && pdfUrl) this.openLink.href = pdfUrl;
            this.switchMode('pdf');
            Utils.playTone('chime');
            Logger.info('RESUME', 'Master resume edited and re-rendered successfully.');
        } catch (err) {
            Utils.playTone('error');
            alert(`Error saving edit: ${err.message}`);
        } finally {
            this.saveBtn.disabled = false;
            if (btnText) btnText.textContent = origText;
        }
    },

    switchPages(pages) {
        this.currentPages = pages;
        if (this.page1Btn && this.page2Btn) {
            this.page1Btn.classList.toggle('active', pages === 1);
            this.page2Btn.classList.toggle('active', pages === 2);
        }
        Utils.playTone('pop');
        this.loadDefaultResume(true);
    },

    switchMode(mode) {
        Utils.playTone('pop');
        if (mode === 'pdf') {
            if (this.togglePdfBtn) this.togglePdfBtn.classList.add('active');
            if (this.toggleEditBtn) this.toggleEditBtn.classList.remove('active');
            if (this.pdfContainer) this.pdfContainer.classList.remove('hidden');
            if (this.editContainer) this.editContainer.classList.add('hidden');
        } else {
            if (this.toggleEditBtn) this.toggleEditBtn.classList.add('active');
            if (this.togglePdfBtn) this.togglePdfBtn.classList.remove('active');
            if (this.editContainer) this.editContainer.classList.remove('hidden');
            if (this.pdfContainer) this.pdfContainer.classList.add('hidden');
        }
    },

    async loadDefaultResume(force = false) {
        if (this.isLoaded && !force) return;
        try {
            const data = await ApiClient.getJson(`/api/default-resume?pages=${this.currentPages}`);
            const pdfUrl = Utils.dataUriToBlobUrl(data.pdf_data_uri || data.pdf_url);
            if (this.pdfIframe && pdfUrl) this.pdfIframe.src = pdfUrl;
            if (this.rawTextarea && data.raw_resume) this.rawTextarea.value = data.raw_resume;
            if (this.downloadLink && pdfUrl) {
                this.downloadLink.href = pdfUrl;
                this.downloadLink.download = 'Prasad_Rane_Resume.pdf';
                this.downloadLink.setAttribute('download', 'Prasad_Rane_Resume.pdf');
            }
            if (this.openLink && pdfUrl) this.openLink.href = pdfUrl;

            this.isLoaded = true;
            EventBus.emit('resume:master_loaded', data);
        } catch (err) {
            Logger.warn('RESUME', 'Failed to load master resume:', err);
        }
    }
};
