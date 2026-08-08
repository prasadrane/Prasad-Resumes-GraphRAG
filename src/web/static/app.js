/**
 * app.js — Modular Frontend Architecture for Prasad Resumes GraphRAG UI.
 * Organized into discrete controllers: Navigation, Generator, Chatbot, and PreviewDrawer.
 */

document.addEventListener('DOMContentLoaded', () => {
    // Shared State & Utilities
    const Utils = {
        escapeHtml(str) {
            if (!str) return '';
            return str.replace(/[&<>"']/g, (m) => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            }[m]));
        },
        showAlert(msg, type, alertEl) {
            if (!alertEl) return;
            alertEl.textContent = msg;
            alertEl.className = `alert ${type}`;
        },
        hideAlert(alertEl) {
            if (!alertEl) return;
            alertEl.className = 'alert hidden';
            alertEl.textContent = '';
        }
    };

    // 1. Navigation Controller (Top Tab Switching)
    const NavigationController = {
        navTailorBtn: document.getElementById('nav-tailor-btn'),
        navChatBtn: document.getElementById('nav-chat-btn'),
        generatorView: document.getElementById('generator-view'),
        chatbotView: document.getElementById('chatbot-view'),

        init() {
            if (!this.navTailorBtn || !this.navChatBtn) return;
            this.navTailorBtn.addEventListener('click', () => this.switchTab('tailor'));
            this.navChatBtn.addEventListener('click', () => this.switchTab('chat'));
        },

        switchTab(tab) {
            if (tab === 'tailor') {
                this.navTailorBtn.classList.add('active');
                this.navChatBtn.classList.remove('active');
                this.generatorView.classList.remove('hidden');
                this.chatbotView.classList.add('hidden');
            } else if (tab === 'chat') {
                this.navChatBtn.classList.add('active');
                this.navTailorBtn.classList.remove('active');
                this.chatbotView.classList.remove('hidden');
                this.generatorView.classList.add('hidden');
            }
        }
    };

    // 2. Preview Drawer Controller (PDF & Raw Edit Modes)
    const PreviewController = {
        previewSection: document.getElementById('preview-section'),
        previewFilename: document.getElementById('preview-filename'),
        previewOpenLink: document.getElementById('preview-open-link'),
        pdfIframe: document.getElementById('pdf-iframe'),
        closePreviewBtn: document.getElementById('close-preview-btn'),
        
        togglePdfBtn: document.getElementById('toggle-pdf-btn'),
        toggleEditBtn: document.getElementById('toggle-edit-btn'),
        pdfViewContainer: document.getElementById('pdf-view-container'),
        editViewContainer: document.getElementById('edit-view-container'),
        rawEditTextarea: document.getElementById('raw-edit-textarea'),
        saveRerenderBtn: document.getElementById('save-rerender-btn'),

        currentTxtUrl: null,
        currentPdfUrl: null,

        init() {
            if (!this.previewSection) return;
            this.closePreviewBtn.addEventListener('click', () => this.close());
            this.togglePdfBtn.addEventListener('click', () => this.switchDrawerMode('pdf'));
            this.toggleEditBtn.addEventListener('click', () => this.switchDrawerMode('edit'));
            this.saveRerenderBtn.addEventListener('click', () => this.handleSaveAndRerender());

            // Global trigger bindings
            window.previewPdf = (pdfUrl, title, txtUrl = '') => this.openPdf(pdfUrl, title, txtUrl);
            window.editRawContent = (txtUrl, pdfUrl, title) => this.openEdit(txtUrl, pdfUrl, title);
        },

        openPdf(pdfUrl, title, txtUrl = '') {
            this.currentPdfUrl = pdfUrl;
            this.currentTxtUrl = txtUrl;
            this.previewFilename.textContent = title;
            this.previewOpenLink.href = pdfUrl;
            this.pdfIframe.src = pdfUrl;
            this.switchDrawerMode('pdf');
            this.previewSection.classList.remove('hidden');
            this.previewSection.scrollIntoView({ behavior: 'smooth' });
        },

        openEdit(txtUrl, pdfUrl, title) {
            this.currentTxtUrl = txtUrl;
            this.currentPdfUrl = pdfUrl;
            this.previewFilename.textContent = title;
            this.previewOpenLink.href = pdfUrl;
            this.pdfIframe.src = pdfUrl;
            this.switchDrawerMode('edit');
            this.previewSection.classList.remove('hidden');
            this.previewSection.scrollIntoView({ behavior: 'smooth' });
        },

        close() {
            this.previewSection.classList.add('hidden');
            this.pdfIframe.src = 'about:blank';
        },

        switchDrawerMode(mode) {
            if (mode === 'pdf') {
                this.togglePdfBtn.classList.add('active');
                this.toggleEditBtn.classList.remove('active');
                this.pdfViewContainer.classList.remove('hidden');
                this.editViewContainer.classList.add('hidden');
            } else if (mode === 'edit') {
                this.toggleEditBtn.classList.add('active');
                this.togglePdfBtn.classList.remove('active');
                this.editViewContainer.classList.remove('hidden');
                this.pdfViewContainer.classList.add('hidden');
                if (this.currentTxtUrl) this.fetchRawContent(this.currentTxtUrl);
            }
        },

        async fetchRawContent(txtUrl) {
            try {
                const res = await fetch(txtUrl);
                if (!res.ok) throw new Error('Failed to fetch raw resume content.');
                const text = await res.text();
                this.rawEditTextarea.value = text;
            } catch (err) {
                this.rawEditTextarea.value = `Error loading content: ${err.message}`;
            }
        },

        async handleSaveAndRerender() {
            if (!this.currentTxtUrl) return;
            const newContent = this.rawEditTextarea.value;
            this.setSaveLoading(true);

            try {
                const res = await fetch('/api/save-edit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        txt_url: this.currentTxtUrl,
                        content: newContent
                    })
                });

                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'Save failed.');

                GeneratorController.showAlert('Resume updated and re-rendered successfully!', 'success');
                this.currentPdfUrl = data.pdf_url;
                this.pdfIframe.src = this.currentPdfUrl;
                this.previewOpenLink.href = this.currentPdfUrl;
                this.switchDrawerMode('pdf');
            } catch (err) {
                GeneratorController.showAlert(`Edit Error: ${err.message}`, 'error');
            } finally {
                this.setSaveLoading(false);
            }
        },

        setSaveLoading(isLoading) {
            this.saveRerenderBtn.disabled = isLoading;
            const btnText = this.saveRerenderBtn.querySelector('.btn-text');
            btnText.textContent = isLoading ? '⏳ Saving & Rendering...' : '🔄 Save & Re-render PDF';
        }
    };

    // 3. Generator Controller (Resume Tailoring Form)
    const GeneratorController = {
        resumeForm: document.getElementById('resume-form'),
        companyInput: document.getElementById('company-input'),
        jdInput: document.getElementById('jd-input'),
        generateBtn: document.getElementById('generate-btn'),
        formAlert: document.getElementById('form-alert'),

        init() {
            if (!this.resumeForm) return;
            this.resumeForm.addEventListener('submit', (e) => this.handleSubmit(e));
        },

        async handleSubmit(e) {
            e.preventDefault();
            const company = this.companyInput.value.trim();
            const jdText = this.jdInput.value.trim();

            if (!company) {
                this.showAlert('Please enter a target company name.', 'error');
                return;
            }

            this.setLoading(true);
            this.hideAlert();

            try {
                const res = await fetch('/api/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ company, jd_text: jdText })
                });

                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'Resume generation failed.');

                this.showAlert(`Success! Tailored resume created for ${company}.`, 'success');
                if (data.pdf_url) {
                    PreviewController.openPdf(data.pdf_url, `${company} — Resume PDF`, data.txt_url);
                }
            } catch (err) {
                this.showAlert(err.message, 'error');
            } finally {
                this.setLoading(false);
            }
        },

        setLoading(isLoading) {
            this.generateBtn.disabled = isLoading;
            const btnText = this.generateBtn.querySelector('.btn-text');
            btnText.textContent = isLoading ? '⏳ Tailoring & Generating PDF...' : '✨ Generate Tailored Resume';
        },

        showAlert(msg, type) { Utils.showAlert(msg, type, this.formAlert); },
        hideAlert() { Utils.hideAlert(this.formAlert); }
    };

    // 4. Chatbot Controller (GraphRAG Q&A Interface)
    const ChatbotController = {
        chatForm: document.getElementById('chat-form'),
        chatInput: document.getElementById('chat-input'),
        chatMessages: document.getElementById('chat-messages'),
        chatSendBtn: document.getElementById('chat-send-btn'),
        queryModeSelect: document.getElementById('query-mode-select'),
        chips: document.querySelectorAll('.chip-btn'),

        init() {
            if (!this.chatForm) return;
            this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));

            // Chip click listeners
            this.chips.forEach(chip => {
                chip.addEventListener('click', () => {
                    const question = chip.getAttribute('data-question');
                    if (question) {
                        this.chatInput.value = question;
                        this.sendQuery(question);
                    }
                });
            });
        },

        handleSubmit(e) {
            e.preventDefault();
            const question = this.chatInput.value.trim();
            if (!question) return;
            this.sendQuery(question);
        },

        async sendQuery(question) {
            const mode = this.queryModeSelect ? this.queryModeSelect.value : 'local';

            // Append User Message
            this.appendMessage(question, 'user');
            this.chatInput.value = '';

            // Append Loading Indicator Message
            const loadingMsgId = this.appendLoadingMessage();
            this.setLoading(true);

            try {
                const res = await fetch('/api/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: question, mode })
                });

                const data = await res.json();
                this.removeMessage(loadingMsgId);

                if (!res.ok) throw new Error(data.detail || 'Query execution failed.');

                this.appendMessage(data.response, 'assistant');
            } catch (err) {
                this.removeMessage(loadingMsgId);
                this.appendMessage(`❌ Error: ${err.message}`, 'assistant');
            } finally {
                this.setLoading(false);
            }
        },

        appendMessage(text, role) {
            const msgDiv = document.createElement('div');
            msgDiv.className = `message ${role}`;
            
            const bubbleDiv = document.createElement('div');
            bubbleDiv.className = 'message-bubble';
            bubbleDiv.textContent = text;

            msgDiv.appendChild(bubbleDiv);
            this.chatMessages.appendChild(msgDiv);
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
            return msgDiv;
        },

        appendLoadingMessage() {
            const msgDiv = document.createElement('div');
            msgDiv.className = 'message assistant';
            msgDiv.id = `loading-${Date.now()}`;

            const bubbleDiv = document.createElement('div');
            bubbleDiv.className = 'message-bubble';
            bubbleDiv.textContent = '⏳ Querying GraphRAG knowledge graph...';

            msgDiv.appendChild(bubbleDiv);
            this.chatMessages.appendChild(msgDiv);
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
            return msgDiv.id;
        },

        removeMessage(id) {
            const msg = document.getElementById(id);
            if (msg) msg.remove();
        },

        setLoading(isLoading) {
            this.chatSendBtn.disabled = isLoading;
            this.chatInput.disabled = isLoading;
            const btnText = this.chatSendBtn.querySelector('.btn-text');
            btnText.textContent = isLoading ? '⏳ Thinking...' : 'Send ➔';
        }
    };

    // Initialize All Controllers
    NavigationController.init();
    PreviewController.init();
    GeneratorController.init();
    ChatbotController.init();
});
