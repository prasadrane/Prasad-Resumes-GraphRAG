/**
 * search.js — Header Search Bar with SQLite FTS5 Full-Text Search.
 */

import { Logger } from '../core/logger.js';
import { ApiClient } from '../core/api.js';
import { Utils } from '../core/utils.js';

export const FTS5SearchController = {
    input: null,
    dropdown: null,
    debounceTimer: null,

    init() {
        this.input = document.getElementById('global-search-input');
        this.dropdown = document.getElementById('fts-dropdown');

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

        Logger.info('SEARCH', 'FTS5SearchController initialized.');
    },

    async search() {
        const q = this.input.value.trim();
        if (q.length < 2) {
            this.dropdown.classList.add('hidden');
            return;
        }

        try {
            const data = await ApiClient.getJson(`/api/fts-search?q=${encodeURIComponent(q)}&limit=5`);

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
            Logger.warn('SEARCH', 'FTS Search error:', err);
        }
    }
};
