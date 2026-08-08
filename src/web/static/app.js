/**
 * app.js — Material Design 3 Frontend Architecture for Prasad Resumes GraphRAG UI.
 * Discrete Controllers: Navigation, Generator, Chatbot, and PreviewDrawer.
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
        }
    };

    // 1. Navigation Controller (Material Design 3 Segmented Control)
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
                this.navTailorBtn.setAttribute('aria-selected', 'true');
                this.navChatBtn.classList.remove('active');
                this.navChatBtn.setAttribute('aria-selected', 'false');

                this.generatorView.classList.remove('hidden');
                this.chatbotView.classList.add('hidden');
            } else if (tab === 'chat') {
                this.navChatBtn.classList.add('active');
                this.navChatBtn.setAttribute('aria-selected', 'true');
                this.navTailorBtn.classList.remove('active');
                this.navTailorBtn.setAttribute('aria-selected', 'false');

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
        previewDownloadLink: document.getElementById('preview-download-link'),
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
        currentRawText: null,

        init() {
            if (!this.previewSection) return;
            this.closePreviewBtn.addEventListener('click', () => this.close());
            this.togglePdfBtn.addEventListener('click', () => this.switchDrawerMode('pdf'));
            this.toggleEditBtn.addEventListener('click', () => this.switchDrawerMode('edit'));
            this.saveRerenderBtn.addEventListener('click', () => this.handleSaveAndRerender());

            // Global trigger bindings
            window.previewPdf = (pdfUrl, title, txtUrl = '', rawText = '') => this.openPdf(pdfUrl, title, txtUrl, rawText);
            window.editRawContent = (txtUrl, pdfUrl, title, rawText = '') => this.openEdit(txtUrl, pdfUrl, title, rawText);
        },

        openPdf(pdfUrl, title, txtUrl = '', rawText = '') {
            this.currentPdfUrl = pdfUrl;
            this.currentTxtUrl = txtUrl;
            if (rawText) {
                this.currentRawText = rawText;
                this.rawEditTextarea.value = rawText;
            }
            this.previewFilename.textContent = title;
            this.previewOpenLink.href = pdfUrl;
            if (this.previewDownloadLink) this.previewDownloadLink.href = pdfUrl;
            this.pdfIframe.src = pdfUrl;
            this.switchDrawerMode('pdf');
            this.previewSection.classList.remove('hidden');
            this.previewSection.scrollIntoView({ behavior: 'smooth' });
        },

        openEdit(txtUrl, pdfUrl, title, rawText = '') {
            this.currentTxtUrl = txtUrl;
            this.currentPdfUrl = pdfUrl;
            if (rawText) {
                this.currentRawText = rawText;
            }
            this.previewFilename.textContent = title;
            this.previewOpenLink.href = pdfUrl;
            if (this.previewDownloadLink) this.previewDownloadLink.href = pdfUrl;
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
                if (this.currentRawText) {
                    this.rawEditTextarea.value = this.currentRawText;
                } else if (this.currentTxtUrl) {
                    this.fetchRawContent(this.currentTxtUrl);
                }
            }
        },

        async fetchRawContent(txtUrl) {
            try {
                const res = await fetch(txtUrl);
                if (!res.ok) throw new Error('Failed to fetch raw resume content.');
                const text = await res.text();
                this.currentRawText = text;
                this.rawEditTextarea.value = text;
            } catch (err) {
                this.rawEditTextarea.value = `Error loading content: ${err.message}`;
            }
        },

        async handleSaveAndRerender() {
            const newContent = this.rawEditTextarea.value;
            if (!newContent.trim()) return;
            this.setSaveLoading(true);

            try {
                const res = await fetch('/api/render_pdf', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        raw_text: newContent,
                        txt_url: this.currentTxtUrl,
                        company: this.previewFilename.textContent
                    })
                });

                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'Save failed.');

                GeneratorController.showAlert('Resume updated and re-rendered successfully!', 'success');
                this.currentPdfUrl = data.pdf_url;
                this.currentRawText = newContent;
                this.pdfIframe.src = this.currentPdfUrl;
                this.previewOpenLink.href = this.currentPdfUrl;
                if (this.previewDownloadLink) this.previewDownloadLink.href = this.currentPdfUrl;
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
            btnText.textContent = isLoading ? 'Saving & Rendering...' : 'Save & Re-render PDF';
        }
    };

    // 3. Generator Controller (Resume Tailoring Form & Live Char Counter)
    const GeneratorController = {
        resumeForm: document.getElementById('resume-form'),
        companyInput: document.getElementById('company-input'),
        jdInput: document.getElementById('jd-input'),
        jdCharCount: document.getElementById('jd-char-count'),
        generateBtn: document.getElementById('generate-btn'),
        formAlert: document.getElementById('form-alert'),

        init() {
            if (!this.resumeForm) return;
            this.resumeForm.addEventListener('submit', (e) => this.handleSubmit(e));

            // Character counter for Job Description
            if (this.jdInput && this.jdCharCount) {
                this.jdInput.addEventListener('input', () => {
                    const len = this.jdInput.value.length;
                    this.jdCharCount.textContent = `${len.toLocaleString()} / 10,000 chars`;
                });
            }
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
                    PreviewController.openPdf(data.pdf_url, `${company} — Resume PDF`, data.txt_url || '', data.raw_resume || '');
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
            btnText.textContent = isLoading ? 'Tailoring & Generating PDF...' : 'Generate Tailored Resume';
        },

        showAlert(msg, type) { Utils.showAlert(msg, type, this.formAlert); },
        hideAlert() { Utils.hideAlert(this.formAlert); }
    };

    // 4. Chatbot Controller (GraphRAG Q&A, M3 Mode Selector, Copy, Clear Chat)
    const ChatbotController = {
        chatForm: document.getElementById('chat-form'),
        chatInput: document.getElementById('chat-input'),
        chatMessages: document.getElementById('chat-messages'),
        chatSendBtn: document.getElementById('chat-send-btn'),
        clearChatBtn: document.getElementById('clear-chat-btn'),
        modeBtns: document.querySelectorAll('.m3-mode-btn'),
        chips: document.querySelectorAll('.m3-action-chip'),

        currentMode: 'local',

        init() {
            if (!this.chatForm) return;
            this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));

            // Mode Segmented Buttons
            this.modeBtns.forEach(btn => {
                btn.addEventListener('click', () => {
                    this.modeBtns.forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    this.currentMode = btn.dataset.mode || 'local';
                });
            });

            // Action Chip listeners
            this.chips.forEach(chip => {
                chip.addEventListener('click', () => {
                    const question = chip.getAttribute('data-question');
                    if (question) {
                        this.chatInput.value = question;
                        this.sendQuery(question);
                    }
                });
            });

            // Clear Chat listener
            if (this.clearChatBtn) {
                this.clearChatBtn.addEventListener('click', () => this.clearChat());
            }
        },

        handleSubmit(e) {
            e.preventDefault();
            const question = this.chatInput.value.trim();
            if (!question) return;
            this.sendQuery(question);
        },

        async sendQuery(question) {
            const mode = this.currentMode;

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
            if (role === 'assistant') {
                bubbleDiv.innerHTML = Utils.formatMarkdown(text);
                
                // Append Copy to Clipboard Button for Assistant messages
                const copyBtn = document.createElement('button');
                copyBtn.className = 'copy-msg-btn';
                copyBtn.title = 'Copy response to clipboard';
                copyBtn.innerHTML = '<span class="material-symbols-outlined">content_copy</span>';
                copyBtn.addEventListener('click', () => {
                    navigator.clipboard.writeText(text).then(() => {
                        copyBtn.innerHTML = '<span class="material-symbols-outlined" style="color:#6ee7b7">check</span>';
                        setTimeout(() => {
                            copyBtn.innerHTML = '<span class="material-symbols-outlined">content_copy</span>';
                        }, 1500);
                    });
                });
                bubbleDiv.appendChild(copyBtn);
            } else {
                bubbleDiv.textContent = text;
            }

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

        clearChat() {
            this.chatMessages.innerHTML = `
                <div class="message assistant">
                    <div class="message-bubble">
                        <p>👋 Hi! I'm your AI GraphRAG assistant. Ask me anything about Prasad Rane's professional experience, technical skills, or projects, or click one of the suggested questions above!</p>
                    </div>
                </div>
            `;
        },

        setLoading(isLoading) {
            this.chatSendBtn.disabled = isLoading;
            this.chatInput.disabled = isLoading;
            const icon = this.chatSendBtn.querySelector('.material-symbols-outlined');
            if (icon) icon.textContent = isLoading ? 'hourglass_empty' : 'send';
        }
    };

    // Initialize All Controllers
    NavigationController.init();
    PreviewController.init();
    GeneratorController.init();
    ChatbotController.init();
});
