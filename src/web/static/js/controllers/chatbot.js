/**
 * chatbot.js — GraphRAG Conversational Q&A Controller with Streaming, Query Modes & Web Speech STT.
 */

import { Logger } from '../core/logger.js';
import { ApiClient } from '../core/api.js';
import { Utils } from '../core/utils.js';

export const ChatbotController = {
    form: null,
    input: null,
    messagesContainer: null,
    clearBtn: null,
    modeBtns: null,
    sampleChips: null,
    voiceBtn: null,
    currentMode: 'local',
    recognition: null,
    isListening: false,

    init() {
        this.form = document.getElementById('chat-form');
        this.input = document.getElementById('chat-input');
        this.messagesContainer = document.getElementById('chat-messages');
        this.clearBtn = document.getElementById('clear-chat-btn');
        this.modeBtns = document.querySelectorAll('.m3-mode-btn');
        this.sampleChips = document.querySelectorAll('.m3-action-chip');
        this.voiceBtn = document.getElementById('voice-input-btn');

        if (this.form) this.form.addEventListener('submit', (e) => this.handleSubmit(e));
        if (this.clearBtn) this.clearBtn.addEventListener('click', () => this.clearChat());

        this.modeBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                this.modeBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.currentMode = btn.getAttribute('data-mode') || 'local';
                Utils.playTone('pop');
                Logger.info('CHATBOT', `Query mode set to: ${this.currentMode.toUpperCase()}`);
            });
        });

        this.sampleChips.forEach(chip => {
            chip.addEventListener('click', () => {
                const q = chip.getAttribute('data-question');
                if (q && this.input) {
                    this.input.value = q;
                    Utils.playTone('pop');
                    this.form.dispatchEvent(new Event('submit', { cancelable: true }));
                }
            });
        });

        this.initVoiceInput();
        Logger.info('CHATBOT', 'ChatbotController initialized.');
    },

    initVoiceInput() {
        if (!this.voiceBtn) return;
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            this.voiceBtn.style.display = 'none';
            return;
        }

        try {
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = false;
            this.recognition.lang = 'en-US';

            this.recognition.onstart = () => {
                this.isListening = true;
                this.voiceBtn.classList.add('listening');
                Utils.playTone('pop');
            };

            this.recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                if (this.input && transcript) {
                    this.input.value = transcript;
                    this.form.dispatchEvent(new Event('submit', { cancelable: true }));
                }
            };

            this.recognition.onerror = () => {
                this.isListening = false;
                this.voiceBtn.classList.remove('listening');
            };

            this.recognition.onend = () => {
                this.isListening = false;
                this.voiceBtn.classList.remove('listening');
            };

            this.voiceBtn.addEventListener('click', () => {
                if (this.isListening) {
                    this.recognition.stop();
                } else {
                    this.recognition.start();
                }
            });
        } catch (e) {
            this.voiceBtn.style.display = 'none';
        }
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
            Utils.playTone('pop');
        }
    },

    async handleSubmit(e) {
        e.preventDefault();
        const q = this.input ? this.input.value.trim() : '';
        if (!q) return;

        this.appendUserMessage(q);
        if (this.input) this.input.value = '';
        Utils.playTone('pop');

        const loadingEl = this.appendLoadingMessage();

        try {
            const data = await ApiClient.postJson('/api/query', {
                query: q,
                mode: this.currentMode
            });

            if (loadingEl) loadingEl.remove();
            this.appendAssistantMessage(data.response || data.answer || 'No response returned.');
            Utils.playTone('chime');
        } catch (err) {
            if (loadingEl) loadingEl.remove();
            this.appendAssistantMessage(`Error retrieving answer: ${err.message}`);
            Utils.playTone('error');
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
        div.innerHTML = `<div class="message-bubble"><p><em>Searching knowledge graph (${this.currentMode})...</em></p></div>`;
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
