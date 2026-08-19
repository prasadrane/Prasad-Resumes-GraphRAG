/**
 * main.js — Master Bootstrapper for Prasad Resumes GraphRAG Modular UI.
 * Orchestrates module initialization with resilient try/catch error boundaries.
 */

import { Logger } from './core/logger.js';
import { EventBus } from './core/bus.js';
import { ApiClient } from './core/api.js';
import { Utils } from './core/utils.js';
import { DevTools } from './core/devtools.js';

import { NavigationController } from './controllers/navigation.js';
import { DefaultResumeController } from './controllers/default_resume.js';
import { GeneratorController } from './controllers/generator.js';
import { PipelineController } from './controllers/pipeline.js';
import { PreviewDrawerController } from './controllers/preview.js';
import { CoverLetterController } from './controllers/cover_letter.js';
import { InterviewPrepController } from './controllers/prep.js';
import { GraphExplorerController } from './controllers/graph_explorer.js';
import { ChatbotController } from './controllers/chatbot.js';
import { FTS5SearchController } from './controllers/search.js';
import { DiagnosticsController } from './controllers/diagnostics.js';

document.addEventListener('DOMContentLoaded', () => {
    const startTime = performance.now();
    Logger.info('App', '🚀 Bootstrapping Prasad Resumes GraphRAG UI...');

    // Initialize Global DevTools
    DevTools.init();

    // Register controllers in order
    const controllers = [
        ['NavigationController', NavigationController],
        ['DefaultResumeController', DefaultResumeController],
        ['GeneratorController', GeneratorController],
        ['PipelineController', PipelineController],
        ['PreviewDrawerController', PreviewDrawerController],
        ['CoverLetterController', CoverLetterController],
        ['InterviewPrepController', InterviewPrepController],
        ['GraphExplorerController', GraphExplorerController],
        ['FTS5SearchController', FTS5SearchController],
        ['DiagnosticsController', DiagnosticsController],
        ['ChatbotController', ChatbotController],
    ];

    controllers.forEach(([name, ctrl]) => {
        try {
            if (ctrl && typeof ctrl.init === 'function') {
                ctrl.init();
            }
        } catch (err) {
            Logger.error('App', `❌ Failed to initialize ${name}: ${err.message}`, err);
        }
    });

    // Mount global App & dbg namespaces for developer inspection
    window.App = {
        logger: Logger,
        bus: EventBus,
        api: ApiClient,
        utils: Utils,
        devtools: DevTools,
        controllers: {
            navigation: NavigationController,
            defaultResume: DefaultResumeController,
            generator: GeneratorController,
            pipeline: PipelineController,
            preview: PreviewDrawerController,
            coverLetter: CoverLetterController,
            prep: InterviewPrepController,
            graphExplorer: GraphExplorerController,
            chatbot: ChatbotController,
            search: FTS5SearchController,
            diagnostics: DiagnosticsController
        }
    };
    window.dbg = window.dbg || window.App.devtools;

    // Load initial default resume
    try {
        DefaultResumeController.loadDefaultResume();
    } catch (e) {
        Logger.warn('App', 'Could not load initial default resume:', e);
    }

    const elapsed = Math.round(performance.now() - startTime);
    Logger.info('App', `✨ Application initialized in ${elapsed}ms. Ready!`);
});
