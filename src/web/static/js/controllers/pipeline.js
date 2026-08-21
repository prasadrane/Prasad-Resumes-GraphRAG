/**
 * pipeline.js — Interactive Subagent Pipeline Visualizer, Live Agent Thought Terminal & Telemetry Counters.
 */

import { Logger } from '../core/logger.js';
import { EventBus } from '../core/bus.js';
import { Utils } from '../core/utils.js';

export const PipelineController = {
    container: null,
    flowchart: null,
    stepperList: null,
    progressFill: null,
    progressPct: null,
    thoughtTerminal: null,
    thoughtBody: null,
    terminalToggleBtn: null,

    // Telemetry Elements
    zeroEl: null,
    tokEl: null,
    costEl: null,
    latEl: null,

    activeStep: null,
    startTime: null,

    init() {
        this.container = document.getElementById('generation-progress');
        this.flowchart = document.getElementById('pipeline-flowchart');
        this.stepperList = document.getElementById('stepper-container');
        this.progressFill = document.getElementById('progress-fill');
        this.progressPct = document.getElementById('progress-pct');
        this.thoughtTerminal = document.getElementById('agent-thought-terminal');
        this.thoughtBody = document.getElementById('agent-thought-body');
        this.terminalToggleBtn = document.getElementById('toggle-thought-terminal-btn');

        this.zeroEl = document.getElementById('telemetry-zero-cost');
        this.tokEl = document.getElementById('telemetry-tokens');
        this.costEl = document.getElementById('telemetry-cost');
        this.latEl = document.getElementById('telemetry-latency');

        if (this.terminalToggleBtn && this.thoughtBody) {
            this.terminalToggleBtn.addEventListener('click', () => {
                this.thoughtBody.classList.toggle('hidden');
                const isHidden = this.thoughtBody.classList.contains('hidden');
                const icon = this.terminalToggleBtn.querySelector('.material-symbols-outlined');
                if (icon) icon.textContent = isHidden ? 'expand_more' : 'expand_less';
            });
        }

        Logger.info('SUBAGENT', 'PipelineController initialized.');
    },

    start() {
        this.startTime = performance.now();
        if (this.container) this.container.classList.remove('hidden');
        if (this.stepperList) this.stepperList.innerHTML = '';
        if (this.thoughtBody) this.thoughtBody.innerHTML = '<div class="terminal-line system"><span class="prompt">⚡ [Agent Pipeline Initialized]</span> Ingesting target job description & preparing GraphRAG retrieval...</div>';
        if (this.progressFill) {
            this.progressFill.style.width = '5%';
            this.progressFill.style.backgroundColor = 'var(--md-sys-color-primary)';
        }
        if (this.progressPct) this.progressPct.textContent = '5%';

        this.resetFlowchart();
        this.setFlowchartStage('ingest', 'active');
        EventBus.emit('status:update', { text: 'Subagent Pipeline Ingesting...', state: 'busy' });
        Utils.playTone('pop');
    },

    resetFlowchart() {
        if (!this.flowchart) return;
        const nodes = this.flowchart.querySelectorAll('.flowchart-node');
        nodes.forEach(n => {
            n.className = 'flowchart-node pending';
            const statusIcon = n.querySelector('.node-status-icon');
            if (statusIcon) statusIcon.textContent = 'radio_button_unchecked';
        });
    },

    setFlowchartStage(stageKey, state) {
        if (!this.flowchart) return;
        const node = this.flowchart.querySelector(`[data-stage="${stageKey}"]`);
        if (!node) return;

        node.className = `flowchart-node ${state}`;
        const statusIcon = node.querySelector('.node-status-icon');
        if (statusIcon) {
            if (state === 'active') statusIcon.textContent = 'progress_activity';
            else if (state === 'done') statusIcon.textContent = 'check_circle';
            else if (state === 'error') statusIcon.textContent = 'error';
        }
    },

    update(stepData) {
        let msg = stepData.msg || stepData.label || stepData.status;
        let pct = stepData.pct || stepData.progress;
        const agent = stepData.agent || 'Orchestrator';

        if (stepData.agent && stepData.status) {
            msg = `[${stepData.agent}] ${stepData.status}`;
        }

        // Map step key to stage
        if (pct === undefined) {
            if (stepData.step === 'ingestion' || stepData.step === 'extracting_keywords') {
                pct = 15;
                this.setFlowchartStage('ingest', 'done');
                this.setFlowchartStage('extract', 'active');
            } else if (stepData.step === 'critic_eval' || stepData.step === 'selecting_summary') {
                pct = 35;
                this.setFlowchartStage('extract', 'done');
                this.setFlowchartStage('retrieve', 'active');
            } else if (stepData.step === 'graph_retrieval' || stepData.step === 'tailoring_summary') {
                pct = 55;
                this.setFlowchartStage('retrieve', 'active');
            } else if (stepData.step === 'optimization' || stepData.step === 'tailoring_bullets') {
                pct = 75;
                this.setFlowchartStage('retrieve', 'done');
                this.setFlowchartStage('optimize', 'active');
            } else if (stepData.step === 'fact_guard_audit') {
                pct = 85;
                this.setFlowchartStage('optimize', 'done');
                this.setFlowchartStage('audit', 'active');
            } else if (stepData.step === 'rendering' || stepData.step === 'rendering_pdf') {
                pct = 95;
                this.setFlowchartStage('audit', 'done');
                this.setFlowchartStage('render', 'active');
            } else if (stepData.step === 'complete') {
                pct = 100;
                this.setFlowchartStage('render', 'done');
            } else {
                pct = 50;
            }
        }

        const pctVal = Math.min(100, Math.round(pct || 0));
        if (this.progressFill) this.progressFill.style.width = `${pctVal}%`;
        if (this.progressPct) this.progressPct.textContent = `${pctVal}%`;

        // Update Stepper List
        if (this.stepperList && msg) {
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

        // Append to Agent Thought Terminal
        if (this.thoughtBody && msg) {
            const line = document.createElement('div');
            line.className = `terminal-line ${stepData.step === 'complete' ? 'success' : 'agent'}`;
            const timeTag = new Date().toTimeString().split(' ')[0];
            line.innerHTML = `<span class="timestamp">${timeTag}</span> <span class="badge ${agent.toLowerCase()}">[${agent}]</span> <span class="text">${Utils.escapeHtml(msg)}</span>`;
            this.thoughtBody.appendChild(line);
            this.thoughtBody.scrollTop = this.thoughtBody.scrollHeight;
        }

        // Live Telemetry Updates
        if (stepData.telemetry) {
            const t = stepData.telemetry;
            if (this.zeroEl) this.zeroEl.textContent = `${t.zero_cost_subagents_run}`;
            if (this.tokEl) this.tokEl.textContent = `${t.total_tokens.toLocaleString()}`;
            if (this.costEl) this.costEl.textContent = `$${t.estimated_cost_usd.toFixed(4)}`;
            if (this.latEl) this.latEl.textContent = `${Math.round(t.latency_ms)}ms`;
            EventBus.emit('telemetry:update', t);
        }

        if (stepData.step === 'complete') {
            EventBus.emit('status:update', { text: 'Engine Active', state: 'active' });
            Utils.playTone('chime');
            Utils.triggerConfetti();
        }
    },

    fail() {
        if (this.progressFill) this.progressFill.style.backgroundColor = 'var(--md-sys-color-error)';
        EventBus.emit('status:update', { text: 'Generation Failed', state: 'error' });
        Utils.playTone('error');
        if (this.thoughtBody) {
            const line = document.createElement('div');
            line.className = 'terminal-line error';
            line.innerHTML = '<span class="badge error">[FAILED]</span> <span class="text">Subagent pipeline failed to converge or encountered an exception.</span>';
            this.thoughtBody.appendChild(line);
        }
    }
};
