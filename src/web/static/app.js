/**
 * app.js — Material Design 3 Frontend Architecture for Prasad Resumes GraphRAG UI.
 * Discrete Controllers: Navigation, DefaultResume, Generator, Chatbot, and PreviewDrawer.
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
            html = html.replace(/\*(.*?)\*/g, 'em>$1</em>');
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
        navDefaultBtn: document.getElementById('nav-default-btn'),
        navTailorBtn: document.getElementById('nav-tailor-btn'),
        navChatBtn: document.getElementById('nav-chat-btn'),

        defaultView: document.getElementById('default-view'),
        generatorView: document.getElementById('generator-view'),
        chatbotView: document.getElementById('chatbot-view'),

        init() {
            if (this.navDefaultBtn) this.navDefaultBtn.addEventListener('click', () => this.switchTab('default'));
            if (this.navTailorBtn) this.navTailorBtn.addEventListener('click', () => this.switchTab('tailor'));
            if (this.navChatBtn) this.navChatBtn.addEventListener('click', () => this.switchTab('chat'));

            // Load Default Resume on startup as 1st active view
            DefaultResumeController.loadDefaultResume();
        },

        switchTab(tab) {
            // Reset all button active states
            [this.navDefaultBtn, this.navTailorBtn, this.navChatBtn].forEach(btn => {
                if (btn) {
                    btn.classList.remove('active');
                    btn.setAttribute('aria-selected', 'false');
                }
            });

            // Hide all views cleanly (no DOM overlap)
            [this.defaultView, this.generatorView, this.chatbotView].forEach(view => {
                if (view) view.classList.add('hidden');
            });

            if (tab === 'default') {
                if (this.navDefaultBtn) {
                    this.navDefaultBtn.classList.add('active');
                    this.navDefaultBtn.setAttribute('aria-selected', 'true');
                }
                if (this.defaultView) this.defaultView.classList.remove('hidden');
                DefaultResumeController.loadDefaultResume();
            } else if (tab === 'tailor') {
                if (this.navTailorBtn) {
                    this.navTailorBtn.classList.add('active');
                    this.navTailorBtn.setAttribute('aria-selected', 'true');
                }
                if (this.generatorView) this.generatorView.classList.remove('hidden');
            } else if (tab === 'chat') {
                if (this.navChatBtn) {
                    this.navChatBtn.classList.add('active');
                    this.navChatBtn.setAttribute('aria-selected', 'true');
                }
                if (this.chatbotView) this.chatbotView.classList.remove('hidden');
            }
        }
    };

    // 2. Default Resume Controller
    const DefaultResumeController = {
        defaultView: document.getElementById('default-view'),
        defaultPdfIframe: document.getElementById('default-pdf-iframe'),
        defaultRawTextarea: document.getElementById('default-raw-textarea'),
        defaultTogglePdfBtn: document.getElementById('default-toggle-pdf-btn'),
        defaultToggleEditBtn: document.getElementById('default-toggle-edit-btn'),
        defaultPdfContainer: document.getElementById('default-pdf-container'),
        defaultEditContainer: document.getElementById('default-edit-container'),
        defaultDownloadLink: document.getElementById('default-download-link'),
        defaultOpenLink: document.getElementById('default-open-link'),

        isLoaded: false,

        init() {
            if (!this.defaultView) return;
            if (this.defaultTogglePdfBtn) this.defaultTogglePdfBtn.addEventListener('click', () => this.switchMode('pdf'));
            if (this.defaultToggleEditBtn) this.defaultToggleEditBtn.addEventListener('click', () => this.switchMode('edit'));
        },

        async loadDefaultResume() {
            if (this.isLoaded) return;
            try {
                const res = await fetch('/api/default-resume');
                if (!res.ok) throw new Error('Failed to fetch default master resume.');
                const data = await res.json();
                
                if (this.defaultPdfIframe) this.defaultPdfIframe.src = data.pdf_url;
                if (this.defaultRawTextarea) this.defaultRawTextarea.value = data.raw_resume || '';
                if (this.defaultDownloadLink) this.defaultDownloadLink.href = data.pdf_url;
                if (this.defaultOpenLink) this.defaultOpenLink.href = data.pdf_url;
                this.isLoaded = true;
            } catch (err) {
                if (this.defaultRawTextarea) this.defaultRawTextarea.value = `Error loading default resume: ${err.message}`;
            }
        },

        switchMode(mode) {
            if (mode === 'pdf') {
                if (this.defaultTogglePdfBtn) this.defaultTogglePdfBtn.classList.add('active');
                if (this.defaultToggleEditBtn) this.defaultToggleEditBtn.classList.remove('active');
                if (this.defaultPdfContainer) this.defaultPdfContainer.classList.remove('hidden');
                if (this.defaultEditContainer) this.defaultEditContainer.classList.add('hidden');
            } else {
                if (this.defaultToggleEditBtn) this.defaultToggleEditBtn.classList.add('active');
                if (this.defaultTogglePdfBtn) this.defaultTogglePdfBtn.classList.remove('active');
                if (this.defaultEditContainer) this.defaultEditContainer.classList.remove('hidden');
                if (this.defaultPdfContainer) this.defaultPdfContainer.classList.add('hidden');
            }
        }
    };

    // 3. Preview Drawer Controller (PDF & Raw Edit Modes for Tailored Resume)
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
            if (this.closePreviewBtn) this.closePreviewBtn.addEventListener('click', () => this.close());
            if (this.togglePdfBtn) this.togglePdfBtn.addEventListener('click', () => this.switchDrawerMode('pdf'));
            if (this.toggleEditBtn) this.toggleEditBtn.addEventListener('click', () => this.switchDrawerMode('edit'));
            if (this.saveRerenderBtn) this.saveRerenderBtn.addEventListener('click', () => this.handleSaveAndRerender());

            // Global trigger bindings
            window.previewPdf = (pdfUrl, title, txtUrl = '', rawText = '') => this.openPdf(pdfUrl, title, txtUrl, rawText);
            window.editRawContent = (txtUrl, pdfUrl, title, rawText = '') => this.openEdit(txtUrl, pdfUrl, title, rawText);
        },

        openPdf(pdfUrl, title, txtUrl = '', rawText = '') {
            this.currentPdfUrl = pdfUrl;
            this.currentTxtUrl = txtUrl;
            if (rawText) {
                this.currentRawText = rawText;
                if (this.rawEditTextarea) this.rawEditTextarea.value = rawText;
            }
            if (this.previewFilename) this.previewFilename.textContent = title;
            if (this.previewOpenLink) this.previewOpenLink.href = pdfUrl;
            if (this.previewDownloadLink) this.previewDownloadLink.href = pdfUrl;
            if (this.pdfIframe) this.pdfIframe.src = pdfUrl;
            this.switchDrawerMode('pdf');
            if (this.previewSection) {
                this.previewSection.classList.remove('hidden');
                this.previewSection.scrollIntoView({ behavior: 'smooth' });
            }
        },

        openEdit(txtUrl, pdfUrl, title, rawText = '') {
            this.currentTxtUrl = txtUrl;
            this.currentPdfUrl = pdfUrl;
            if (rawText) {
                this.currentRawText = rawText;
            }
            if (this.previewFilename) this.previewFilename.textContent = title;
            if (this.previewOpenLink) this.previewOpenLink.href = pdfUrl;
            if (this.previewDownloadLink) this.previewDownloadLink.href = pdfUrl;
            if (this.pdfIframe) this.pdfIframe.src = pdfUrl;
            this.switchDrawerMode('edit');
            if (this.previewSection) {
                this.previewSection.classList.remove('hidden');
                this.previewSection.scrollIntoView({ behavior: 'smooth' });
            }
        },

        switchDrawerMode(mode) {
            if (mode === 'pdf') {
                if (this.togglePdfBtn) this.togglePdfBtn.classList.add('active');
                if (this.toggleEditBtn) this.toggleEditBtn.classList.remove('active');
                if (this.pdfViewContainer) this.pdfViewContainer.classList.remove('hidden');
                if (this.editViewContainer) this.editViewContainer.classList.add('hidden');
            } else if (mode === 'edit') {
                if (this.toggleEditBtn) this.toggleEditBtn.classList.add('active');
                if (this.togglePdfBtn) this.togglePdfBtn.classList.remove('active');
                if (this.editViewContainer) this.editViewContainer.classList.remove('hidden');
                if (this.pdfViewContainer) this.pdfViewContainer.classList.add('hidden');
                if (this.currentRawText && this.rawEditTextarea) {
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
                if (this.rawEditTextarea) this.rawEditTextarea.value = text;
            } catch (err) {
                if (this.rawEditTextarea) this.rawEditTextarea.value = `Error loading content: ${err.message}`;
            }
        },

        async handleSaveAndRerender() {
            if (!this.rawEditTextarea) return;
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
                        company: this.previewFilename ? this.previewFilename.textContent : 'Tailored'
                    })
                });

                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'Save failed.');

                GeneratorController.showAlert('Resume updated and re-rendered successfully!', 'success');
                this.currentPdfUrl = data.pdf_url;
                this.currentRawText = newContent;
                if (this.pdfIframe) this.pdfIframe.src = this.currentPdfUrl;
                if (this.previewOpenLink) this.previewOpenLink.href = this.currentPdfUrl;
                if (this.previewDownloadLink) this.previewDownloadLink.href = this.currentPdfUrl;
                this.switchDrawerMode('pdf');
            } catch (err) {
                GeneratorController.showAlert(`Edit Error: ${err.message}`, 'error');
            } finally {
                this.setSaveLoading(false);
            }
        },

        setSaveLoading(isLoading) {
            if (!this.saveRerenderBtn) return;
            this.saveRerenderBtn.disabled = isLoading;
            const btnText = this.saveRerenderBtn.querySelector('.btn-text');
            if (btnText) btnText.textContent = isLoading ? 'Saving & Rendering...' : 'Save & Re-render PDF';
        },

        close() {
            if (this.previewSection) {
                this.previewSection.classList.add('hidden');
                if (this.pdfIframe) this.pdfIframe.src = 'about:blank';
            }
        }
    };

    // 4. Generator Form Controller
    const GeneratorController = {
        form: document.getElementById('resume-form'),
        companyInput: document.getElementById('company-input'),
        jdInput: document.getElementById('jd-input'),
        jdCharCount: document.getElementById('jd-char-count'),
        generateBtn: document.getElementById('generate-btn'),
        formAlert: document.getElementById('form-alert'),
        progressContainer: document.getElementById('generation-progress'),
        progressPct: document.getElementById('progress-pct'),
        progressFill: document.getElementById('progress-fill'),
        stepperContainer: document.getElementById('stepper-container'),

        stepsList: [
            { id: 'extracting_keywords', label: 'Extracting ATS keywords' },
            { id: 'loading_master', label: 'Loading master resume' },
            { id: 'selecting_summary', label: 'Selecting best summary variant' },
            { id: 'tailoring_summary', label: 'LLM tailoring summary' },
            { id: 'tailoring_bullets', label: 'LLM tailoring experience bullets' },
            { id: 'formatting', label: 'Formatting & bold marking' },
            { id: 'rendering_pdf', label: 'Rendering PDF' },
            { id: 'complete', label: 'Done' }
        ],
        stepStartTime: {},
        stepTimers: {},

        init() {
            if (!this.form) return;
            this.form.addEventListener('submit', (e) => this.handleSubmit(e));
            this.jdInput.addEventListener('input', () => this.updateCharCount());
        },

        updateCharCount() {
            const count = this.jdInput.value.length;
            this.jdCharCount.textContent = `${count.toLocaleString()} / 10,000 chars`;
        },

        showAlert(msg, type) {
            Utils.showAlert(msg, type, this.formAlert);
        },

        hideAlert() {
            Utils.hideAlert(this.formAlert);
        },

        setLoading(isLoading) {
            this.generateBtn.disabled = isLoading;
            const btnText = this.generateBtn.querySelector('.btn-text');
            const btnIcon = this.generateBtn.querySelector('.btn-icon');
            if (isLoading) {
                btnText.textContent = 'Synthesizing Tailored Resume...';
                btnIcon.textContent = 'hourglass_empty';
            } else {
                btnText.textContent = 'Generate Tailored Resume';
                btnIcon.textContent = 'auto_awesome';
            }
        },

        initializeStepper() {
            this.progressContainer.classList.remove('hidden');
            this.progressPct.textContent = '0%';
            this.progressFill.style.width = '0%';
            this.stepperContainer.innerHTML = '';
            
            this.stepsList.forEach((step, idx) => {
                const item = document.createElement('div');
                item.className = 'step-item pending';
                item.id = `step-${step.id}`;
                
                item.innerHTML = `
                    <div class="step-icon">${idx + 1}</div>
                    <div class="step-content">
                        <div class="step-info">
                            <span class="step-label">${step.label}</span>
                            <span class="step-detail">Pending...</span>
                        </div>
                        <span class="step-elapsed hidden">0.0s</span>
                    </div>
                `;
                this.stepperContainer.appendChild(item);
            });
            this.stepStartTime = {};
            this.stepTimers = {};
        },

        updateStep(stepId, progressPct, detailText) {
            this.progressPct.textContent = `${progressPct}%`;
            this.progressFill.style.width = `${progressPct}%`;
            
            const activeItem = this.stepperContainer.querySelector('.step-item.active');
            if (activeItem) {
                activeItem.classList.remove('active');
                activeItem.classList.add('completed');
                
                const prevId = activeItem.id.replace('step-', '');
                if (this.stepTimers[prevId]) {
                    clearInterval(this.stepTimers[prevId]);
                }
                const elapsedSec = ((Date.now() - this.stepStartTime[prevId]) / 1000).toFixed(1);
                const elapsedBadge = activeItem.querySelector('.step-elapsed');
                elapsedBadge.textContent = `${elapsedSec}s`;
                elapsedBadge.classList.remove('hidden');
                
                activeItem.querySelector('.step-icon').innerHTML = '<span class="material-symbols-outlined" style="font-size: 16px;">check</span>';
            }
            
            const targetItem = document.getElementById(`step-${stepId}`);
            if (targetItem) {
                targetItem.classList.remove('pending');
                targetItem.classList.add('active');
                
                const detailEl = targetItem.querySelector('.step-detail');
                if (detailEl && detailText && typeof detailText === 'string') {
                    detailEl.textContent = detailText;
                }
                
                this.stepStartTime[stepId] = Date.now();
                const elapsedBadge = targetItem.querySelector('.step-elapsed');
                elapsedBadge.classList.remove('hidden');
                elapsedBadge.textContent = '0.0s';
                
                this.stepTimers[stepId] = setInterval(() => {
                    const sec = ((Date.now() - this.stepStartTime[stepId]) / 1000).toFixed(1);
                    elapsedBadge.textContent = `${sec}s`;
                }, 100);
            }
        },

        completeStepper() {
            Object.values(this.stepTimers).forEach(timer => clearInterval(timer));
            
            const items = this.stepperContainer.querySelectorAll('.step-item');
            items.forEach(item => {
                if (!item.classList.contains('completed')) {
                    item.classList.remove('pending', 'active');
                    item.classList.add('completed');
                    item.querySelector('.step-icon').innerHTML = '<span class="material-symbols-outlined" style="font-size: 16px;">check</span>';
                    
                    const stepId = item.id.replace('step-', '');
                    const elapsedBadge = item.querySelector('.step-elapsed');
                    elapsedBadge.classList.remove('hidden');
                    if (this.stepStartTime[stepId]) {
                        const sec = ((Date.now() - this.stepStartTime[stepId]) / 1000).toFixed(1);
                        elapsedBadge.textContent = `${sec}s`;
                    } else {
                        elapsedBadge.textContent = '0.0s';
                    }
                }
            });
            this.progressPct.textContent = '100%';
            this.progressFill.style.width = '100%';
        },

        failStepper(errorMsg) {
            Object.values(this.stepTimers).forEach(timer => clearInterval(timer));
            const activeItem = this.stepperContainer.querySelector('.step-item.active');
            if (activeItem) {
                activeItem.classList.remove('active');
                activeItem.classList.add('pending');
                const detailEl = activeItem.querySelector('.step-detail');
                if (detailEl) detailEl.textContent = `❌ Error: ${errorMsg}`;
            }
        },

        async handleSubmit(e) {
            e.preventDefault();
            this.hideAlert();

            const company = this.companyInput.value.strip ? this.companyInput.value.strip() : this.companyInput.value.trim();
            const jdText = this.jdInput.value.strip ? this.jdInput.value.strip() : this.jdInput.value.trim();

            if (!company) {
                this.showAlert('Please specify target company name.', 'error');
                return;
            }

            this.initializeStepper();
            this.setLoading(true);
            document.getElementById('preview-section').classList.add('hidden');

            try {
                const response = await fetch('/api/generate-stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ company: company, jd_text: jdText })
                });

                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.detail || 'Failed to generate tailored resume.');
                }

                if (!response.body) {
                    throw new Error('ReadableStream not supported by this browser/network.');
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder('utf-8');
                let buffer = '';

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop();

                    for (const line of lines) {
                        const trimmed = line.trim();
                        if (!trimmed) continue;

                        if (trimmed.startsWith('event: error')) {
                            continue;
                        }

                        if (trimmed.startsWith('data: ')) {
                            const rawData = trimmed.slice(6);
                            const payload = JSON.parse(rawData);

                            if (payload.step === 'complete') {
                                this.completeStepper();
                                const detail = payload.detail;
                                this.showAlert(`Success! Tailored resume created for ${company}.`, 'success');
                                if (detail.pdf_url) {
                                    PreviewController.openPdf(detail.pdf_url, `${company} — Resume PDF`, detail.txt_url || '', detail.raw_resume || '');
                                }
                            } else {
                                this.updateStep(payload.step, payload.progress, payload.detail);
                            }
                        }
                    }
                }
            } catch (err) {
                this.failStepper(err.message);
                this.showAlert(err.message, 'error');
            } finally {
                this.setLoading(false);
            }
        }
    };

    // 5. GraphRAG Chatbot Controller
    const ChatbotController = {
        chatForm: document.getElementById('chat-form'),
        chatInput: document.getElementById('chat-input'),
        chatSendBtn: document.getElementById('chat-send-btn'),
        chatMessages: document.getElementById('chat-messages'),
        clearChatBtn: document.getElementById('clear-chat-btn'),
        modeBtns: document.querySelectorAll('.m3-mode-btn'),
        actionChips: document.querySelectorAll('.m3-action-chip'),

        currentMode: 'local',
        sessionId: localStorage.getItem('graphrag_session') || null,

        init() {
            if (!this.chatForm) return;
            this.chatForm.addEventListener('submit', (e) => this.handleSubmit(e));
            this.clearChatBtn.addEventListener('click', () => this.clearChat());

            this.modeBtns.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    this.modeBtns.forEach(b => b.classList.remove('active'));
                    e.currentTarget.classList.add('active');
                    this.currentMode = e.currentTarget.getAttribute('data-mode') || 'local';
                });
            });

            this.actionChips.forEach(chip => {
                chip.addEventListener('click', (e) => {
                    const q = e.currentTarget.getAttribute('data-question');
                    if (q) {
                        this.chatInput.value = q;
                        this.handleSubmit(new Event('submit'));
                    }
                });
            });

            if (!this.sessionId) {
                this.sessionId = crypto.randomUUID();
                localStorage.setItem('graphrag_session', this.sessionId);
            }
        },

        async handleSubmit(e) {
            if (e) e.preventDefault();
            const query = this.chatInput.value.trim();
            if (!query) return;

            this.appendUserMessage(query);
            this.chatInput.value = '';

            const assistantMsgDiv = document.createElement('div');
            assistantMsgDiv.className = 'message assistant';
            const bubbleDiv = document.createElement('div');
            bubbleDiv.className = 'message-bubble';
            bubbleDiv.innerHTML = '<span style="color:#888">⏳ Querying knowledge graph...</span>';

            assistantMsgDiv.appendChild(bubbleDiv);
            this.chatMessages.appendChild(assistantMsgDiv);
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;

            this.setLoading(true);

            try {
                const response = await fetch('/api/chat-stream', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: query,
                        mode: this.currentMode,
                        session_id: this.sessionId
                    })
                });

                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.detail || 'Query execution failed.');
                }

                if (!response.body) {
                    throw new Error('ReadableStream not supported.');
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder('utf-8');
                let buffer = '';
                let fullResponse = '';

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';

                    for (const line of lines) {
                        const trimmed = line.trim();
                        if (!trimmed) continue;

                        if (trimmed.startsWith('data: ')) {
                            const rawData = trimmed.slice(6);
                            try {
                                const payload = JSON.parse(rawData);

                                if (payload.token !== undefined) {
                                    fullResponse += payload.token;
                                    bubbleDiv.innerHTML = Utils.formatMarkdown(fullResponse);
                                    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
                                }

                                if (payload.done) {
                                    const sources = payload.sources || [];
                                    if (sources.length > 0) {
                                        const chipsDiv = document.createElement('div');
                                        chipsDiv.className = 'source-chips';
                                        sources.forEach(src => {
                                            const chip = document.createElement('span');
                                            chip.className = 'source-chip';
                                            const srcLabel = src.name || src.title || 'Source';
                                            chip.innerHTML = `<span class="material-symbols-outlined">description</span> ${srcLabel}`;
                                            chipsDiv.appendChild(chip);
                                        });
                                        assistantMsgDiv.appendChild(chipsDiv);
                                    }
                                    this.addCopyButton(bubbleDiv, fullResponse);
                                }
                            } catch (_) {
                                // Ignore malformed JSON chunks
                            }
                        } else if (trimmed.startsWith('event: error')) {
                            bubbleDiv.innerHTML = `❌ Error: ${JSON.parse(trimmed.slice(12)).detail}`;
                        }
                    }
                }

                this.chatMessages.scrollTop = this.chatMessages.scrollHeight;

            } catch (err) {
                bubbleDiv.innerHTML = `❌ Error: ${err.message}`;
            } finally {
                this.setLoading(false);
            }
        },

        simulateTypewriter(element, text) {
            return new Promise((resolve) => {
                const words = text.split(' ');
                let currentWordIndex = 0;
                let displayedText = '';

                if (words.length <= 1) {
                    element.innerHTML = Utils.formatMarkdown(text);
                    resolve();
                    return;
                }

                const interval = setInterval(() => {
                    if (currentWordIndex >= words.length) {
                        clearInterval(interval);
                        element.innerHTML = Utils.formatMarkdown(text);
                        resolve();
                        return;
                    }

                    displayedText += (currentWordIndex === 0 ? '' : ' ') + words[currentWordIndex];
                    element.innerHTML = Utils.formatMarkdown(displayedText);
                    currentWordIndex++;
                    this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
                }, 20);
            });
        },

        addCopyButton(bubbleDiv, text) {
            // Check if copy button already exists to avoid duplication
            if (bubbleDiv.querySelector('.copy-msg-btn')) return;
            
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
        },

        appendUserMessage(text) {
            const msgDiv = document.createElement('div');
            msgDiv.className = 'message user';
            const bubbleDiv = document.createElement('div');
            bubbleDiv.className = 'message-bubble';
            bubbleDiv.textContent = text;
            msgDiv.appendChild(bubbleDiv);
            this.chatMessages.appendChild(msgDiv);
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        },

        appendAssistantMessage(text) {
            const msgDiv = document.createElement('div');
            msgDiv.className = 'message assistant';
            const bubbleDiv = document.createElement('div');
            bubbleDiv.className = 'message-bubble';

            if (text.includes('#') || text.includes('**') || text.includes('- ') || text.includes('• ')) {
                bubbleDiv.innerHTML = Utils.formatMarkdown(text);
                this.addCopyButton(bubbleDiv, text);
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
    DefaultResumeController.init();
    NavigationController.init();
    PreviewController.init();
    GeneratorController.init();
    ChatbotController.init();
});
