/**
 * app.js — Material Design 3 Frontend Architecture for Prasad Resumes GraphRAG UI.
 * Discrete Controllers: Navigation, DefaultResume, Generator, PreviewDrawer, DiffInspector,
 * CoverLetterStudio, InterviewPrep, LinkedInOptimizer, FTS5Search, and Diagnostics.
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
                console.error('[Utils] Failed to convert data URI to blob URL:', e);
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
        }
    };

    // 1. Navigation Controller (Sidebar Rail & Mobile Navigation)
    const NavigationController = {
        currentTab: 'default',
        isTransitioning: false,

        sidebarRail: document.getElementById('sidebar-rail'),
        sidebarScrim: document.getElementById('sidebar-scrim'),
        mobileBottomNav: document.getElementById('mobile-bottom-nav'),
        mobileMenuBtn: document.getElementById('mobile-menu-btn'),
        mobileMoreBtn: document.getElementById('mobile-more-btn'),
        mobileMoreSheet: document.getElementById('mobile-more-sheet'),
        closeMoreSheetBtn: document.getElementById('close-more-sheet-btn'),
        mobileDiagBtn: document.getElementById('mobile-diag-btn'),
        navSettingsBtn: document.getElementById('nav-settings-btn'),

        navDefaultBtn: document.getElementById('nav-default-btn'),
        navTailorBtn: document.getElementById('nav-tailor-btn'),
        navCoverBtn: document.getElementById('nav-cover-btn'),
        navPrepBtn: document.getElementById('nav-prep-btn'),
        navLinkedinBtn: document.getElementById('nav-linkedin-btn'),
        navChatBtn: document.getElementById('nav-chat-btn'),

        defaultView: document.getElementById('default-view'),
        generatorView: document.getElementById('generator-view'),
        coverView: document.getElementById('cover-view'),
        prepView: document.getElementById('prep-view'),
        linkedinView: document.getElementById('linkedin-view'),
        chatbotView: document.getElementById('chatbot-view'),

        init() {
            // Sidebar Nav button listeners
            if (this.navDefaultBtn) this.navDefaultBtn.addEventListener('click', () => this.switchTab('default'));
            if (this.navTailorBtn) this.navTailorBtn.addEventListener('click', () => this.switchTab('tailor'));
            if (this.navCoverBtn) this.navCoverBtn.addEventListener('click', () => this.switchTab('cover'));
            if (this.navPrepBtn) this.navPrepBtn.addEventListener('click', () => this.switchTab('prep'));
            if (this.navLinkedinBtn) this.navLinkedinBtn.addEventListener('click', () => this.switchTab('linkedin'));
            if (this.navChatBtn) this.navChatBtn.addEventListener('click', () => this.switchTab('chat'));

            if (this.navSettingsBtn) {
                this.navSettingsBtn.addEventListener('click', () => {
                    alert('Settings & Preferences: Theme is set to Dark Slate (M3). Custom AI provider configurations are managed via serverless gateway.');
                });
            }

            // Mobile Bottom Nav buttons
            const mobileNavBtns = document.querySelectorAll('.mobile-nav-btn[data-tab]');
            mobileNavBtns.forEach(btn => {
                btn.addEventListener('click', () => {
                    const tab = btn.getAttribute('data-tab');
                    if (tab) this.switchTab(tab);
                });
            });

            // Mobile More Sheet buttons
            const moreSheetItems = document.querySelectorAll('.more-sheet-item[data-tab]');
            moreSheetItems.forEach(item => {
                item.addEventListener('click', () => {
                    const tab = item.getAttribute('data-tab');
                    if (tab) {
                        this.closeMobileDrawers();
                        this.switchTab(tab);
                    }
                });
            });

            // Mobile Menu / Drawer controls
            if (this.mobileMenuBtn) {
                this.mobileMenuBtn.addEventListener('click', () => this.openMobileSidebar());
            }

            if (this.sidebarScrim) {
                this.sidebarScrim.addEventListener('click', () => this.closeMobileDrawers());
            }

            if (this.mobileMoreBtn) {
                this.mobileMoreBtn.addEventListener('click', () => this.toggleMobileMoreSheet());
            }

            if (this.closeMoreSheetBtn) {
                this.closeMoreSheetBtn.addEventListener('click', () => this.closeMobileDrawers());
            }

            if (this.mobileDiagBtn) {
                this.mobileDiagBtn.addEventListener('click', () => {
                    this.closeMobileDrawers();
                    DiagnosticsController.open();
                });
            }

            // Load Default Resume on startup
            DefaultResumeController.loadDefaultResume();
        },

        openMobileSidebar() {
            if (this.sidebarRail) this.sidebarRail.classList.add('mobile-open');
            if (this.sidebarScrim) this.sidebarScrim.classList.remove('hidden');
        },

        toggleMobileMoreSheet() {
            if (!this.mobileMoreSheet) return;
            const isHidden = this.mobileMoreSheet.classList.contains('hidden');
            if (isHidden) {
                this.mobileMoreSheet.classList.remove('hidden');
                if (this.sidebarScrim) this.sidebarScrim.classList.remove('hidden');
            } else {
                this.closeMobileDrawers();
            }
        },

        closeMobileDrawers() {
            if (this.sidebarRail) this.sidebarRail.classList.remove('mobile-open');
            if (this.mobileMoreSheet) this.mobileMoreSheet.classList.add('hidden');
            if (this.sidebarScrim) this.sidebarScrim.classList.add('hidden');
        },

        getView(tab) {
            const map = {
                default: this.defaultView,
                tailor: this.generatorView,
                cover: this.coverView,
                prep: this.prepView,
                linkedin: this.linkedinView,
                chat: this.chatbotView
            };
            return map[tab];
        },

        getNavButton(tab) {
            const map = {
                default: this.navDefaultBtn,
                tailor: this.navTailorBtn,
                cover: this.navCoverBtn,
                prep: this.navPrepBtn,
                linkedin: this.navLinkedinBtn,
                chat: this.navChatBtn
            };
            return map[tab];
        },

        switchTab(tab) {
            if (this.currentTab === tab && !this.isTransitioning) {
                this.closeMobileDrawers();
                return;
            }

            const outgoingView = this.getView(this.currentTab);
            const incomingView = this.getView(tab);
            if (!incomingView) return;

            this.closeMobileDrawers();

            // Update Sidebar Rail Button States
            const btns = [this.navDefaultBtn, this.navTailorBtn, this.navCoverBtn, this.navPrepBtn, this.navLinkedinBtn, this.navChatBtn];
            btns.forEach(btn => {
                if (btn) {
                    btn.classList.remove('active');
                    btn.setAttribute('aria-selected', 'false');
                }
            });
            const activeBtn = this.getNavButton(tab);
            if (activeBtn) {
                activeBtn.classList.add('active');
                activeBtn.setAttribute('aria-selected', 'true');
            }

            // Update Mobile Bottom Nav States
            const mobileNavBtns = document.querySelectorAll('.mobile-nav-btn[data-tab]');
            mobileNavBtns.forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-tab') === tab);
            });

            // Perform View Transition
            this.isTransitioning = true;
            if (outgoingView && outgoingView !== incomingView) {
                outgoingView.classList.add('leaving');
                setTimeout(() => {
                    outgoingView.classList.add('hidden');
                    outgoingView.classList.remove('leaving');

                    incomingView.classList.remove('hidden');
                    incomingView.classList.add('entering');
                    setTimeout(() => {
                        incomingView.classList.remove('entering');
                        this.isTransitioning = false;
                    }, 250);
                }, 150);
            } else {
                incomingView.classList.remove('hidden');
                incomingView.classList.add('entering');
                setTimeout(() => {
                    incomingView.classList.remove('entering');
                    this.isTransitioning = false;
                }, 250);
            }

            this.currentTab = tab;

            if (tab === 'default') {
                DefaultResumeController.loadDefaultResume();
            }
        }
    };

    // 2. Default Resume Controller
    const DefaultResumeController = {
        isLoaded: false,
        currentPages: 2,
        page1Btn: document.getElementById('default-page-1-btn'),
        page2Btn: document.getElementById('default-page-2-btn'),
        togglePdfBtn: document.getElementById('default-toggle-pdf-btn'),
        toggleEditBtn: document.getElementById('default-toggle-edit-btn'),
        pdfContainer: document.getElementById('default-pdf-container'),
        editContainer: document.getElementById('default-edit-container'),
        pdfIframe: document.getElementById('default-pdf-iframe'),
        rawTextarea: document.getElementById('default-raw-textarea'),
        downloadLink: document.getElementById('default-download-link'),
        openLink: document.getElementById('default-open-link'),
        saveBtn: document.getElementById('default-save-rerender-btn'),

        init() {
            if (this.page1Btn) this.page1Btn.addEventListener('click', () => this.switchPages(1));
            if (this.page2Btn) this.page2Btn.addEventListener('click', () => this.switchPages(2));
            if (this.togglePdfBtn) this.togglePdfBtn.addEventListener('click', () => this.switchMode('pdf'));
            if (this.toggleEditBtn) this.toggleEditBtn.addEventListener('click', () => this.switchMode('edit'));
            if (this.saveBtn) this.saveBtn.addEventListener('click', () => this.handleSave());
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
                const res = await fetch('/api/save-edit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        raw_text: content,
                        company: 'Default',
                        pages: this.currentPages || 2,
                    }),
                });
                if (!res.ok) throw new Error('Failed to save and re-render default resume');
                const data = await res.json();
                const pdfUrl = Utils.dataUriToBlobUrl(data.pdf_data_uri || data.pdf_url);
                if (this.pdfIframe && pdfUrl) this.pdfIframe.src = pdfUrl;
                if (this.downloadLink && pdfUrl) this.downloadLink.href = pdfUrl;
                if (this.openLink && pdfUrl) this.openLink.href = pdfUrl;
                this.switchMode('pdf');
            } catch (err) {
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
            this.loadDefaultResume(true);
        },

        switchMode(mode) {
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
                const res = await fetch(`/api/default-resume?pages=${this.currentPages}`);
                if (!res.ok) throw new Error('Failed to load default resume');
                const data = await res.json();

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
            } catch (err) {
                console.warn('[DefaultResume] Failed to load default resume:', err);
            }
        }
    };

    // 3. Generator & ATS Match Controller
    const GeneratorController = {
        form: document.getElementById('resume-form'),
        urlInput: document.getElementById('url-input'),
        companyInput: document.getElementById('company-input'),
        jdInput: document.getElementById('jd-input'),
        agenticToggle: document.getElementById('agentic-mode-toggle'),
        jdCharCount: document.getElementById('jd-char-count'),
        generateBtn: document.getElementById('generate-btn'),
        checkAtsBtn: document.getElementById('check-ats-btn'),
        formAlert: document.getElementById('form-alert'),

        // ATS Score Card Elements
        atsContainer: document.getElementById('ats-score-container'),
        atsScoreValue: document.getElementById('ats-score-value'),
        atsGaugeFill: document.getElementById('ats-gauge-fill'),
        atsCoveredChips: document.getElementById('ats-covered-chips'),
        atsMissingChips: document.getElementById('ats-missing-chips'),

        init() {
            if (this.jdInput) {
                this.jdInput.addEventListener('input', () => this.updateCharCount());
            }
            if (this.form) {
                this.form.addEventListener('submit', (e) => this.handleSubmit(e));
            }
            if (this.checkAtsBtn) {
                this.checkAtsBtn.addEventListener('click', () => this.checkATSScore());
            }
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
                return;
            }

            try {
                const res = await fetch('/api/ats-score', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ resume_text: masterResume || jd, jd_text: jd }),
                });
                if (!res.ok) throw new Error('ATS check failed');
                const data = await res.json();
                this.renderATSScore(data.overall_score, data.covered_keywords, data.missing_keywords);
            } catch (err) {
                console.warn('[ATS] Score check failed:', err);
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
        },

        async handleSubmit(e) {
            e.preventDefault();
            const company = this.companyInput ? this.companyInput.value.trim() : '';
            const url = this.urlInput ? this.urlInput.value.trim() : '';
            const jd = this.jdInput ? this.jdInput.value.trim() : '';
            const isAgentic = this.agenticToggle ? this.agenticToggle.checked : true;

            if (!company && !url) {
                Utils.showAlert('Please provide a target company name or job URL.', 'error', this.formAlert);
                return;
            }

            Utils.hideAlert(this.formAlert);
            this.setLoading(true);
            StepperController.start();

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

                        // Support multi-line data payloads in SSE
                        const dataLines = block
                            .split('\n')
                            .filter(l => l.startsWith('data:'))
                            .map(l => l.replace(/^data:\s*/, ''))
                            .join('\n');

                        if (!dataLines) continue;

                        try {
                            const stepData = JSON.parse(dataLines);
                            StepperController.update(stepData);

                            const payload = stepData.payload || stepData.data || stepData.detail;
                            if (stepData.step === 'complete' && payload) {
                                PreviewDrawerController.open(payload);
                                if (payload.final_score && GeneratorController.renderATSScore) {
                                    const breakdown = payload.breakdown || {};
                                    GeneratorController.renderATSScore(
                                        payload.final_score,
                                        breakdown.matched_keywords || [],
                                        breakdown.missing_keywords || []
                                    );
                                } else if (jd) {
                                    this.checkATSScore();
                                }
                            }
                        } catch (parseErr) {
                            console.warn('[Stream] SSE parse error on block:', parseErr, dataLines);
                        }
                    }
                }
            } catch (err) {
                Utils.showAlert(`Generation error: ${err.message}`, 'error', this.formAlert);
                StepperController.fail();
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

    // 4. Stepper Controller
    const StepperController = {
        container: document.getElementById('generation-progress'),
        stepperList: document.getElementById('stepper-container'),
        progressFill: document.getElementById('progress-fill'),
        progressPct: document.getElementById('progress-pct'),

        start() {
            if (this.container) this.container.classList.remove('hidden');
            if (this.stepperList) this.stepperList.innerHTML = '';
            if (this.progressFill) {
                this.progressFill.style.width = '5%';
                this.progressFill.style.backgroundColor = 'var(--md-sys-color-primary)';
            }
            if (this.progressPct) this.progressPct.textContent = '5%';
        },

        update(stepData) {
            let msg = stepData.msg || stepData.label || stepData.status;
            let pct = stepData.pct || stepData.progress;

            if (stepData.agent && stepData.status) {
                msg = `[${stepData.agent}] ${stepData.status}`;
            }

            if (pct === undefined) {
                if (stepData.step === 'ingestion') pct = 15;
                else if (stepData.step === 'ingestion_complete') pct = 25;
                else if (stepData.step === 'critic_eval') pct = 40;
                else if (stepData.step === 'graph_retrieval') pct = 55;
                else if (stepData.step === 'graph_retrieval_complete') pct = 65;
                else if (stepData.step === 'optimization') pct = 75;
                else if (stepData.step === 'fact_guard_audit') pct = 82;
                else if (stepData.step === 'iteration_complete') pct = 88;
                else if (stepData.step === 'converged') pct = 90;
                else if (stepData.step === 'rendering') pct = 95;
                else if (stepData.step === 'complete') pct = 100;
                else pct = 50;
            }

            const pctVal = Math.min(100, Math.round(pct || 0));
            if (this.progressFill) this.progressFill.style.width = `${pctVal}%`;
            if (this.progressPct) this.progressPct.textContent = `${pctVal}%`;

            if (this.stepperList && msg) {
                // Mark previous active items as done
                const prevActive = this.stepperList.querySelectorAll('.stepper-step.active');
                prevActive.forEach(el => {
                    el.classList.remove('active');
                    el.classList.add('done');
                    const icon = el.querySelector('.material-symbols-outlined');
                    if (icon) {
                        icon.textContent = 'check_circle';
                        icon.style.color = '#34d399';
                    }
                });

                let iconName = 'progress_activity';
                let iconColor = 'var(--md-sys-color-primary)';
                if (stepData.step === 'complete') {
                    iconName = 'task_alt';
                    iconColor = '#34d399';
                } else if (stepData.step === 'critic_eval' || stepData.step === 'iteration_complete') {
                    iconName = 'analytics';
                } else if (stepData.step === 'graph_retrieval' || stepData.step === 'graph_retrieval_complete') {
                    iconName = 'hub';
                } else if (stepData.step === 'optimization') {
                    iconName = 'auto_fix_high';
                } else if (stepData.step === 'fact_guard_audit') {
                    iconName = 'verified_user';
                } else if (stepData.step === 'rendering') {
                    iconName = 'picture_as_pdf';
                }

                const item = document.createElement('div');
                item.className = `stepper-step ${stepData.step === 'complete' ? 'done' : 'active'}`;
                item.innerHTML = `<span class="material-symbols-outlined" style="font-size: 16px; color: ${iconColor};">${iconName}</span> <span>${Utils.escapeHtml(msg)}</span>`;
                this.stepperList.appendChild(item);
                item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
            if (stepData.telemetry) {
                const t = stepData.telemetry;
                const zeroEl = document.getElementById('telemetry-zero-cost');
                const tokEl = document.getElementById('telemetry-tokens');
                const costEl = document.getElementById('telemetry-cost');
                const latEl = document.getElementById('telemetry-latency');

                if (zeroEl) zeroEl.textContent = `${t.zero_cost_subagents_run}`;
                if (tokEl) tokEl.textContent = `${t.total_tokens}`;
                if (costEl) costEl.textContent = `$${t.estimated_cost_usd.toFixed(4)}`;
                if (latEl) latEl.textContent = `${Math.round(t.latency_ms)}ms`;
            }
        },

        fail() {
            if (this.progressFill) this.progressFill.style.backgroundColor = 'var(--md-sys-color-error)';
        }
    };

    // 5. Preview Drawer & Diff Inspector Controller
    const PreviewDrawerController = {
        section: document.getElementById('preview-section'),
        pdfIframe: document.getElementById('pdf-iframe'),
        rawTextarea: document.getElementById('raw-edit-textarea'),
        saveBtn: document.getElementById('save-rerender-btn'),
        closeBtn: document.getElementById('close-preview-btn'),
        openLink: document.getElementById('preview-open-link'),
        applyDiffsBtn: document.getElementById('apply-selected-diffs-btn'),

        currentPages: 2,
        page1Btn: document.getElementById('preview-page-1-btn'),
        page2Btn: document.getElementById('preview-page-2-btn'),

        togglePdfBtn: document.getElementById('toggle-pdf-btn'),
        toggleEditBtn: document.getElementById('toggle-edit-btn'),
        toggleDiffBtn: document.getElementById('toggle-diff-btn'),

        pdfContainer: document.getElementById('pdf-view-container'),
        editContainer: document.getElementById('edit-view-container'),
        diffContainer: document.getElementById('diff-view-container'),
        diffPanel: document.getElementById('diff-content-panel'),

        // Export Hub
        exportBtn: document.getElementById('export-hub-btn'),
        exportMenu: document.getElementById('export-hub-menu'),

        // Impact Scorer
        impactBar: document.getElementById('bullet-impact-bar'),
        impactDesc: document.getElementById('impact-score-desc'),
        impactBadge: document.getElementById('impact-badge'),

        currentData: null,
        activeDiffs: [],

        init() {
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
        },

        async switchPages(pages) {
            this.currentPages = pages;
            if (this.page1Btn && this.page2Btn) {
                this.page1Btn.classList.toggle('active', pages === 1);
                this.page2Btn.classList.toggle('active', pages === 2);
            }
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
        },

        switchMode(mode) {
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
            
            // If subagents produced structured diffs, render interactive human-in-the-loop review cards
            if (this.activeDiffs && this.activeDiffs.length > 0) {
                let html = '<div class="diff-cards-list" style="display: flex; flex-direction: column; gap: 1rem;">';
                this.activeDiffs.forEach((diff, idx) => {
                    const diffId = diff.diff_id || `diff-${idx}`;
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
                const res = await fetch('/api/diff-resume', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tailored_text: this.rawTextarea.value }),
                });
                if (!res.ok) throw new Error('Diff calculation failed');
                const data = await res.json();

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
                const res = await fetch('/api/apply-diffs', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        raw_resume: this.rawTextarea.value,
                        approved_diffs: approved,
                        target_pages: this.currentPages || 2,
                        company: this.currentData ? (this.currentData.company || 'Tailored') : 'Tailored',
                    }),
                });
                if (!res.ok) throw new Error('Failed to apply approved diffs');
                const data = await res.json();
                this.rawTextarea.value = data.raw_resume;
                const pdfUrl = Utils.dataUriToBlobUrl(data.pdf_url);
                if (this.pdfIframe && pdfUrl) this.pdfIframe.src = pdfUrl;
                if (this.openLink && pdfUrl) this.openLink.href = pdfUrl;
                this.switchMode('pdf');
            } catch (err) {
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
                    }
                }
                return;
            }

            try {
                const res = await fetch(`/api/export-markup?format=${format}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ raw_text: raw }),
                });
                if (!res.ok) throw new Error('Export failed');
                const data = await res.json();
                Utils.downloadFile(data.filename, data.content);
            } catch (err) {
                console.warn('[Export] Error:', err);
            }
        },

        async handleSave() {
            if (!this.rawTextarea || !this.saveBtn) return;
            const content = this.rawTextarea.value;
            this.saveBtn.disabled = true;

            try {
                const res = await fetch('/api/save-edit', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        raw_text: content,
                        txt_url: this.currentData ? this.currentData.txt_url : null,
                        pages: this.currentPages || 2,
                    }),
                });
                if (!res.ok) throw new Error('Failed to save edit');
                const data = await res.json();
                this.currentData = data;
                const pdfUrl = Utils.dataUriToBlobUrl(data.pdf_data_uri || data.pdf_url);
                if (this.pdfIframe && pdfUrl) this.pdfIframe.src = pdfUrl;
                if (this.openLink && pdfUrl) this.openLink.href = pdfUrl;
                this.switchMode('pdf');
            } catch (err) {
                alert(`Error saving edit: ${err.message}`);
            } finally {
                this.saveBtn.disabled = false;
            }
        }
    };

    // 6. Cover Letter Studio Controller
    const CoverLetterController = {
        form: document.getElementById('cover-letter-form'),
        companyInput: document.getElementById('cover-company-input'),
        roleInput: document.getElementById('cover-role-input'),
        jdInput: document.getElementById('cover-jd-input'),
        bodyEl: document.getElementById('cover-letter-body'),
        copyBtn: document.getElementById('copy-cover-btn'),
        generateBtn: document.getElementById('generate-cover-btn'),

        init() {
            if (this.form) this.form.addEventListener('submit', (e) => this.handleSubmit(e));
            if (this.copyBtn) this.copyBtn.addEventListener('click', () => this.copyToClipboard());
        },

        async handleSubmit(e) {
            e.preventDefault();
            const company = this.companyInput ? this.companyInput.value.trim() : '';
            const role = this.roleInput ? this.roleInput.value.trim() : '';
            const jd = this.jdInput ? this.jdInput.value.trim() : '';

            if (!company) return;
            if (this.generateBtn) this.generateBtn.disabled = true;

            try {
                const res = await fetch('/api/cover-letter', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ company, role_title: role, jd_text: jd }),
                });
                if (!res.ok) throw new Error('Failed to generate cover letter');
                const data = await res.json();
                if (this.bodyEl) this.bodyEl.textContent = data.markdown;
            } catch (err) {
                if (this.bodyEl) this.bodyEl.textContent = `Error: ${err.message}`;
            } finally {
                if (this.generateBtn) this.generateBtn.disabled = false;
            }
        },

        copyToClipboard() {
            if (!this.bodyEl) return;
            navigator.clipboard.writeText(this.bodyEl.textContent).then(() => {
                const span = this.copyBtn.querySelector('span:last-child');
                if (span) {
                    const orig = span.textContent;
                    span.textContent = 'Copied!';
                    setTimeout(() => span.textContent = orig, 2000);
                }
            });
        }
    };

    // 7. Interview Prep & STAR Controller
    const InterviewPrepController = {
        form: document.getElementById('prep-form'),
        jdInput: document.getElementById('prep-jd-input'),
        container: document.getElementById('prep-questions-container'),
        btn: document.getElementById('generate-prep-btn'),

        init() {
            if (this.form) this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        },

        async handleSubmit(e) {
            e.preventDefault();
            const jd = this.jdInput ? this.jdInput.value.trim() : '';
            if (this.btn) this.btn.disabled = true;
            if (this.container) this.container.innerHTML = '<p style="color: var(--md-sys-color-primary);">Predicting interview questions & generating STAR talking points...</p>';

            try {
                const res = await fetch('/api/interview-prep', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ jd_text: jd || 'Cloud architecture, microservices, and leadership.' }),
                });
                if (!res.ok) throw new Error('Interview prep failed');
                const data = await res.json();

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
            } catch (err) {
                if (this.container) this.container.innerHTML = `<p style="color: var(--md-sys-color-error);">Error: ${err.message}</p>`;
            } finally {
                if (this.btn) this.btn.disabled = false;
            }
        }
    };

    // 8. LinkedIn Optimizer Controller
    const LinkedInController = {
        form: document.getElementById('linkedin-form'),
        roleInput: document.getElementById('linkedin-role-input'),
        headlineVal: document.getElementById('linkedin-headline-val'),
        aboutVal: document.getElementById('linkedin-about-val'),
        copyHeadlineBtn: document.getElementById('copy-headline-btn'),
        copyAboutBtn: document.getElementById('copy-about-btn'),
        btn: document.getElementById('generate-linkedin-btn'),

        init() {
            if (this.form) this.form.addEventListener('submit', (e) => this.handleSubmit(e));
            if (this.copyHeadlineBtn) this.copyHeadlineBtn.addEventListener('click', () => {
                navigator.clipboard.writeText(this.headlineVal.textContent.trim());
                this.flashCopied(this.copyHeadlineBtn);
            });
            if (this.copyAboutBtn) this.copyAboutBtn.addEventListener('click', () => {
                navigator.clipboard.writeText(this.aboutVal.textContent.trim());
                this.flashCopied(this.copyAboutBtn);
            });
        },

        flashCopied(btn) {
            const span = btn.querySelector('span:last-child');
            if (span) {
                const orig = span.textContent;
                span.textContent = 'Copied!';
                setTimeout(() => span.textContent = orig, 2000);
            }
        },

        async handleSubmit(e) {
            e.preventDefault();
            const role = this.roleInput ? this.roleInput.value.trim() : '';
            if (this.btn) this.btn.disabled = true;

            try {
                const res = await fetch('/api/linkedin-profile', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ target_role: role }),
                });
                if (!res.ok) throw new Error('LinkedIn generation failed');
                const data = await res.json();
                if (this.headlineVal) this.headlineVal.textContent = data.headline;
                if (this.aboutVal) this.aboutVal.textContent = data.about_section;
            } catch (err) {
                console.warn('[LinkedIn] Error:', err);
            } finally {
                if (this.btn) this.btn.disabled = false;
            }
        }
    };

    // 9. Global FTS5 Search Controller
    const FTS5SearchController = {
        input: document.getElementById('global-search-input'),
        dropdown: document.getElementById('fts-dropdown'),
        debounceTimer: null,

        init() {
            if (!this.input || !this.dropdown) return;

            this.input.addEventListener('input', () => {
                clearTimeout(this.debounceTimer);
                this.debounceTimer = setTimeout(() => this.search(), 250);
            });

            document.addEventListener('click', (e) => {
                if (!this.input.contains(e.target) && !this.dropdown.contains(e.target)) {
                    this.dropdown.classList.add('hidden');
                }
            });
        },

        async search() {
            const q = this.input.value.trim();
            if (q.length < 2) {
                this.dropdown.classList.add('hidden');
                return;
            }

            try {
                const res = await fetch(`/api/fts-search?q=${encodeURIComponent(q)}&limit=5`);
                if (!res.ok) throw new Error('FTS search failed');
                const data = await res.json();

                if (!data.results || data.results.length === 0) {
                    this.dropdown.innerHTML = '<div class="fts-item"><span class="fts-snippet">No matching skills or projects found.</span></div>';
                } else {
                    this.dropdown.innerHTML = data.results.map(r => `
                        <div class="fts-item">
                            <div class="fts-title">${Utils.escapeHtml(r.title)}</div>
                            <div class="fts-snippet">${Utils.escapeHtml(r.content.substring(0, 140))}...</div>
                        </div>
                    `).join('');
                }
                this.dropdown.classList.remove('hidden');
            } catch (err) {
                console.warn('[FTS] Search error:', err);
            }
        }
    };

    // 10. Observability & Diagnostics Controller
    const DiagnosticsController = {
        openBtn: document.getElementById('open-diag-btn'),
        closeBtn: document.getElementById('close-diag-btn'),
        refreshBtn: document.getElementById('refresh-diag-btn'),
        drawer: document.getElementById('diag-drawer'),

        retrievalP90: document.getElementById('diag-retrieval-p90'),
        gatewayP90: document.getElementById('diag-gateway-p90'),
        renderAvg: document.getElementById('diag-render-avg'),
        healthVal: document.getElementById('diag-health-val'),

        init() {
            if (this.openBtn) this.openBtn.addEventListener('click', () => this.open());
            if (this.closeBtn) this.closeBtn.addEventListener('click', () => this.close());
            if (this.refreshBtn) this.refreshBtn.addEventListener('click', () => this.fetchStats());
        },

        open() {
            if (this.drawer) this.drawer.classList.add('open');
            this.fetchStats();
        },

        close() {
            if (this.drawer) this.drawer.classList.remove('open');
        },

        async fetchStats() {
            try {
                const res = await fetch('/api/telemetry-stats');
                if (!res.ok) throw new Error('Stats request failed');
                const data = await res.json();

                if (this.retrievalP90) this.retrievalP90.textContent = `${data.spans.retrieval.p90_ms || 0}ms`;
                if (this.gatewayP90) this.gatewayP90.textContent = `${data.spans.gateway.p90_ms || 0}ms`;
                if (this.renderAvg) this.renderAvg.textContent = `${data.spans.pdf_render.avg_ms || 0}ms`;
                if (this.healthVal) this.healthVal.textContent = data.engine_status || 'Healthy';
            } catch (err) {
                console.warn('[Diagnostics] Stats fetch failed:', err);
            }
        }
    };

    // 11. Chatbot Controller
    const ChatbotController = {
        form: document.getElementById('chat-form'),
        input: document.getElementById('chat-input'),
        messagesContainer: document.getElementById('chat-messages'),
        clearBtn: document.getElementById('clear-chat-btn'),
        modeBtns: document.querySelectorAll('.m3-mode-btn'),
        sampleChips: document.querySelectorAll('.m3-action-chip'),
        voiceBtn: document.getElementById('voice-input-btn'),
        currentMode: 'local',

        init() {
            if (this.form) this.form.addEventListener('submit', (e) => this.handleSubmit(e));
            if (this.clearBtn) this.clearBtn.addEventListener('click', () => this.clearChat());

            this.modeBtns.forEach(btn => {
                btn.addEventListener('click', () => {
                    this.modeBtns.forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    this.currentMode = btn.getAttribute('data-mode') || 'local';
                });
            });

            this.sampleChips.forEach(chip => {
                chip.addEventListener('click', () => {
                    const q = chip.getAttribute('data-question');
                    if (q && this.input) {
                        this.input.value = q;
                        this.form.dispatchEvent(new Event('submit', { cancelable: true }));
                    }
                });
            });
        },

        clearChat() {
            if (this.messagesContainer) {
                this.messagesContainer.innerHTML = `
                    <div class="message assistant">
                        <div class="message-bubble">
                            <p>👋 Chat history cleared. How can I help you explore Prasad Rane's experience?</p>
                        </div>
                    </div>
                `;
            }
        },

        async handleSubmit(e) {
            e.preventDefault();
            const q = this.input ? this.input.value.trim() : '';
            if (!q) return;

            this.appendUserMessage(q);
            if (this.input) this.input.value = '';

            const loadingEl = this.appendLoadingMessage();

            try {
                const res = await fetch('/api/query', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query: q, mode: this.currentMode }),
                });

                if (!res.ok) throw new Error(`Query failed (${res.status})`);
                const data = await res.json();
                if (loadingEl) loadingEl.remove();

                this.appendAssistantMessage(data.response || data.answer || 'No response returned.');
            } catch (err) {
                if (loadingEl) loadingEl.remove();
                this.appendAssistantMessage(`Error retrieving answer: ${err.message}`);
            }
        },

        appendUserMessage(text) {
            const div = document.createElement('div');
            div.className = 'message user';
            div.innerHTML = `<div class="message-bubble"><p>${Utils.escapeHtml(text)}</p></div>`;
            this.messagesContainer.appendChild(div);
            div.scrollIntoView({ behavior: 'smooth' });
        },

        appendLoadingMessage() {
            const div = document.createElement('div');
            div.className = 'message assistant';
            div.innerHTML = `<div class="message-bubble"><p><em>Searching knowledge graph...</em></p></div>`;
            this.messagesContainer.appendChild(div);
            div.scrollIntoView({ behavior: 'smooth' });
            return div;
        },

        appendAssistantMessage(markdown) {
            const div = document.createElement('div');
            div.className = 'message assistant';
            div.innerHTML = `<div class="message-bubble">${Utils.formatMarkdown(markdown)}</div>`;
            this.messagesContainer.appendChild(div);
            div.scrollIntoView({ behavior: 'smooth' });
        }
    };

    // Initialize All Controllers
    NavigationController.init();
    DefaultResumeController.init();
    GeneratorController.init();
    PreviewDrawerController.init();
    CoverLetterController.init();
    InterviewPrepController.init();
    LinkedInController.init();
    FTS5SearchController.init();
    DiagnosticsController.init();
    ChatbotController.init();
});
