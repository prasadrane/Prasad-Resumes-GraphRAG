document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const resumeForm = document.getElementById('resume-form');
    const companyInput = document.getElementById('company-input');
    const jdInput = document.getElementById('jd-input');
    const generateBtn = document.getElementById('generate-btn');
    const formAlert = document.getElementById('form-alert');
    const historyList = document.getElementById('history-list');
    const historySearch = document.getElementById('history-search');
    const refreshHistoryBtn = document.getElementById('refresh-history-btn');
    
    // Preview Elements
    const previewSection = document.getElementById('preview-section');
    const previewFilename = document.getElementById('preview-filename');
    const previewOpenLink = document.getElementById('preview-open-link');
    const pdfIframe = document.getElementById('pdf-iframe');
    const closePreviewBtn = document.getElementById('close-preview-btn');

    let allHistory = [];

    // Initialize Page
    if (historyList) loadHistory();

    // Event Listeners
    resumeForm.addEventListener('submit', handleFormSubmit);
    if (refreshHistoryBtn) refreshHistoryBtn.addEventListener('click', loadHistory);
    if (historySearch) historySearch.addEventListener('input', filterHistory);
    closePreviewBtn.addEventListener('click', () => {
        previewSection.classList.add('hidden');
        pdfIframe.src = 'about:blank';
    });

    // Load History Function
    async function loadHistory() {
        historyList.innerHTML = '<div class="loading-placeholder">Loading history...</div>';
        try {
            const res = await fetch('/api/history');
            if (!res.ok) throw new Error('Failed to load history');
            allHistory = await res.json();
            renderHistory(allHistory);
        } catch (err) {
            historyList.innerHTML = `<div class="empty-placeholder">Error loading history: ${err.message}</div>`;
        }
    }

    // Render History Function
    function renderHistory(items) {
        if (!items || items.length === 0) {
            historyList.innerHTML = '<div class="empty-placeholder">No tailored resumes found yet.</div>';
            return;
        }

        historyList.innerHTML = items.map(item => `
            <div class="history-item">
                <div class="history-meta">
                    <span class="history-company">${escapeHtml(item.company)}</span>
                    <span class="history-date">📅 ${escapeHtml(item.date)}</span>
                </div>
                <div class="history-actions">
                    <button class="btn btn-secondary btn-sm" onclick="previewPdf('${escapeHtml(item.pdf_url)}', '${escapeHtml(item.company)} — ${escapeHtml(item.pdf_filename)}')">
                        👁️ View PDF
                    </button>
                    ${item.txt_url ? `
                        <a class="btn btn-secondary btn-sm" href="${escapeHtml(item.txt_url)}" target="_blank" title="View Raw Text">
                            📝 TXT
                        </a>
                    ` : ''}
                </div>
            </div>
        `).join('');
    }

    // Filter History Function
    function filterHistory() {
        const query = historySearch.value.toLowerCase().trim();
        if (!query) {
            renderHistory(allHistory);
            return;
        }
        const filtered = allHistory.filter(item => 
            item.company.toLowerCase().includes(query) ||
            item.date.toLowerCase().includes(query)
        );
        renderHistory(filtered);
    }

    // Handle Generation Form Submit
    async function handleFormSubmit(e) {
        e.preventDefault();
        
        const company = companyInput.value.trim();
        const jdText = jdInput.value.trim();

        if (!company) {
            showAlert('Please enter a target company name.', 'error');
            return;
        }

        // Set Loading State
        setLoading(true);
        hideAlert();

        try {
            const res = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ company: company, jd_text: jdText })
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.detail || 'Resume generation failed.');
            }

            showAlert(`Success! Tailored resume created for ${company}.`, 'success');
            
            // Reload history & open preview
            if (historyList) await loadHistory();
            if (data.pdf_url) {
                previewPdf(data.pdf_url, `${company} — Resume PDF`);
            }
        } catch (err) {
            showAlert(err.message, 'error');
        } finally {
            setLoading(false);
        }
    }

    // Preview PDF
    window.previewPdf = function(pdfUrl, title) {
        previewFilename.textContent = title;
        previewOpenLink.href = pdfUrl;
        pdfIframe.src = pdfUrl;
        previewSection.classList.remove('hidden');
        previewSection.scrollIntoView({ behavior: 'smooth' });
    };

    // Helper functions
    function setLoading(isLoading) {
        generateBtn.disabled = isLoading;
        const btnText = generateBtn.querySelector('.btn-text');
        const spinner = generateBtn.querySelector('.spinner');
        if (isLoading) {
            btnText.textContent = '⏳ Tailoring & Generating PDF...';
        } else {
            btnText.textContent = '✨ Generate Tailored Resume';
        }
    }

    function showAlert(msg, type) {
        formAlert.textContent = msg;
        formAlert.className = `alert ${type}`;
    }

    function hideAlert() {
        formAlert.className = 'alert hidden';
        formAlert.textContent = '';
    }

    function escapeHtml(str) {
        if (!str) return '';
        return str.replace(/[&<>"']/g, function(m) {
            return {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            }[m];
        });
    }
});
