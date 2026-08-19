/**
 * navigation.js — Navigation Controller.
 * Manages Sidebar Rail, Mobile Navigation, View Transitions, Sound Toggle & Heartbeat Status.
 */

import { Logger } from '../core/logger.js';
import { EventBus } from '../core/bus.js';
import { Utils } from '../core/utils.js';

export const NavigationController = {
    currentTab: 'default',
    isTransitioning: false,

    sidebarRail: null,
    sidebarScrim: null,
    mobileBottomNav: null,
    mobileMenuBtn: null,
    mobileMoreBtn: null,
    mobileMoreSheet: null,
    closeMoreSheetBtn: null,
    mobileDiagBtn: null,
    navSettingsBtn: null,
    soundToggleBtn: null,
    systemStatus: null,

    navDefaultBtn: null,
    navTailorBtn: null,
    navCoverBtn: null,
    navPrepBtn: null,
    navChatBtn: null,
    navGraphBtn: null,

    defaultView: null,
    generatorView: null,
    coverView: null,
    prepView: null,
    chatbotView: null,
    graphView: null,

    init() {
        this.sidebarRail = document.getElementById('sidebar-rail');
        this.sidebarScrim = document.getElementById('sidebar-scrim');
        this.mobileBottomNav = document.getElementById('mobile-bottom-nav');
        this.mobileMenuBtn = document.getElementById('mobile-menu-btn');
        this.mobileMoreBtn = document.getElementById('mobile-more-btn');
        this.mobileMoreSheet = document.getElementById('mobile-more-sheet');
        this.closeMoreSheetBtn = document.getElementById('close-more-sheet-btn');
        this.mobileDiagBtn = document.getElementById('mobile-diag-btn');
        this.navSettingsBtn = document.getElementById('nav-settings-btn');
        this.soundToggleBtn = document.getElementById('sound-toggle-btn');
        this.systemStatus = document.getElementById('system-status');

        this.navDefaultBtn = document.getElementById('nav-default-btn');
        this.navTailorBtn = document.getElementById('nav-tailor-btn');
        this.navCoverBtn = document.getElementById('nav-cover-btn');
        this.navPrepBtn = document.getElementById('nav-prep-btn');
        this.navChatBtn = document.getElementById('nav-chat-btn');
        this.navGraphBtn = document.getElementById('nav-graph-btn');

        this.defaultView = document.getElementById('default-view');
        this.generatorView = document.getElementById('generator-view');
        this.coverView = document.getElementById('cover-view');
        this.prepView = document.getElementById('prep-view');
        this.chatbotView = document.getElementById('chatbot-view');
        this.graphView = document.getElementById('graph-view');

        // Sidebar Nav button listeners
        if (this.navDefaultBtn) this.navDefaultBtn.addEventListener('click', () => this.switchTab('default'));
        if (this.navTailorBtn) this.navTailorBtn.addEventListener('click', () => this.switchTab('tailor'));
        if (this.navCoverBtn) this.navCoverBtn.addEventListener('click', () => this.switchTab('cover'));
        if (this.navPrepBtn) this.navPrepBtn.addEventListener('click', () => this.switchTab('prep'));
        if (this.navChatBtn) this.navChatBtn.addEventListener('click', () => this.switchTab('chat'));
        if (this.navGraphBtn) this.navGraphBtn.addEventListener('click', () => this.switchTab('graph'));

        if (this.navSettingsBtn) {
            this.navSettingsBtn.addEventListener('click', () => {
                alert('Settings & Preferences: Theme is set to Dark Slate (M3). Custom AI provider configurations are managed via serverless gateway.');
            });
        }

        // Sound Toggle Button in Header
        if (this.soundToggleBtn) {
            this.updateSoundIcon();
            this.soundToggleBtn.addEventListener('click', () => {
                const muted = Utils.toggleSound();
                this.updateSoundIcon();
                if (!muted) Utils.playTone('chime');
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
                EventBus.emit('diag:toggle');
            });
        }

        // Listen for external tab switch events
        EventBus.on('tab:switch', (tab) => this.switchTab(tab));
        EventBus.on('sound:toggled', () => this.updateSoundIcon());
        EventBus.on('status:update', (status) => this.setStatus(status));

        Logger.info('NAV', 'NavigationController initialized.');
    },

    updateSoundIcon() {
        if (!this.soundToggleBtn) return;
        const icon = this.soundToggleBtn.querySelector('.material-symbols-outlined');
        if (icon) {
            icon.textContent = Utils.isSoundMuted() ? 'volume_off' : 'volume_up';
        }
        this.soundToggleBtn.title = Utils.isSoundMuted() ? 'Sound Effects Muted (Click to Unmute)' : 'Sound Effects Active (Click to Mute)';
    },

    setStatus({ text = 'Engine Active', state = 'active' }) {
        if (!this.systemStatus) return;
        const dot = this.systemStatus.querySelector('.status-dot');
        if (dot) {
            dot.className = `status-dot ${state === 'busy' ? 'orange pulse-radar' : state === 'error' ? 'red' : 'green'}`;
        }
        const textNode = this.systemStatus.childNodes[this.systemStatus.childNodes.length - 1];
        if (textNode) textNode.nodeValue = ' ' + text;
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
            chat: this.chatbotView,
            graph: this.graphView
        };
        return map[tab];
    },

    getNavButton(tab) {
        const map = {
            default: this.navDefaultBtn,
            tailor: this.navTailorBtn,
            cover: this.navCoverBtn,
            prep: this.navPrepBtn,
            chat: this.navChatBtn,
            graph: this.navGraphBtn
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

        Utils.playTone('pop');
        this.closeMobileDrawers();

        // Update Sidebar Rail Button States
        const btns = [this.navDefaultBtn, this.navTailorBtn, this.navCoverBtn, this.navPrepBtn, this.navChatBtn, this.navGraphBtn];
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
        Logger.debug('NAV', `Switched tab to: ${tab}`);
        EventBus.emit('tab:changed', tab);
    }
};
