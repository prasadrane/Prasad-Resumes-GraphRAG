# Resume Viewer Tab Strip Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the congested resume viewer toolbar into a clean, modern GitHub/Docs-style tab strip with left-aligned view tabs (`[ 📄 PDF Preview ]`, `[ 📝 Raw Content ]`) and right-aligned actions (`[ 1 Page | 2 Pages ]`, `[ ⬇ Download PDF ]`, `[ ↗ ]`).

**Architecture:** Refactor the top toolbar in `src/web/static/index.html` to separate the panel header (title and subtitle) from a dedicated `.doc-tab-strip` container. Style `.doc-tab-strip` in `src/web/static/style.css` with responsive flexbox and subtle border separators. Maintain all existing button IDs to preserve existing JavaScript logic and automated test coverage.

**Tech Stack:** HTML5, CSS3, Vanilla JS, Pytest, Python FastAPI/Starlette test client.

## Global Constraints

- Preserve all existing element IDs (`#default-page-1-btn`, `#default-page-2-btn`, `#default-toggle-pdf-btn`, `#default-toggle-edit-btn`, `#default-download-link`, `#default-open-link`).
- Guarantee single-line horizontal alignment on standard desktop widths ($\ge 1024\text{px}$) without awkward 2-row wrapping.
- All unit and integration tests in `tests/` must pass cleanly.

---

### Task 1: Update Test Suite for New Tab Strip Structure

**Files:**
- Modify: `tests/test_sidebar_navigation.py`

**Interfaces:**
- Consumes: `src/web/static/index.html`
- Produces: Test assertions validating the presence of `.doc-tab-strip`, `.doc-tabs-left`, `.doc-actions-right`, and existing control IDs.

- [ ] **Step 1: Write the failing test**

Add `test_doc_tab_strip_structure` to `tests/test_sidebar_navigation.py`:
```python
    def test_doc_tab_strip_structure(self):
        """Verify resume viewer has dedicated doc-tab-strip separating tabs from actions."""
        html_content = (ROOT_DIR / "src" / "web" / "static" / "index.html").read_text(encoding="utf-8")
        self.assertIn('class="doc-tab-strip"', html_content)
        self.assertIn('class="doc-tabs-left"', html_content)
        self.assertIn('class="doc-actions-right"', html_content)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sidebar_navigation.py::TestSidebarNavigation::test_doc_tab_strip_structure -v`  
Expected: FAIL with `AssertionError: 'class="doc-tab-strip"' not found in html_content`.

---

### Task 2: Refactor HTML Structure in Resume Viewer

**Files:**
- Modify: `src/web/static/index.html:115-155`

**Interfaces:**
- Consumes: Spec in `docs/superpowers/specs/2026-08-18-resume-viewer-tab-strip-design.md`
- Produces: Clean `.panel-header` and `.doc-tab-strip` containing `.doc-tabs-left` and `.doc-actions-right`.

- [ ] **Step 1: Refactor HTML in `src/web/static/index.html`**

Update `#default-view`:
```html
                <section class="m3-card default-panel">
                    <div class="panel-header">
                        <h2><span class="material-symbols-outlined header-symbol">badge</span> Master Default Resume</h2>
                        <p>Standard ATS master resume for Prasad Rane. View PDF preview or inspect raw Markdown content below.</p>
                    </div>

                    <!-- Clean Top Tab Strip (GitHub / Docs Style) -->
                    <div class="doc-tab-strip">
                        <div class="doc-tabs-left">
                            <button id="default-toggle-pdf-btn" class="doc-tab-btn active" title="View PDF Preview">
                                <span class="material-symbols-outlined tab-icon">picture_as_pdf</span>
                                <span>PDF Preview</span>
                            </button>
                            <button id="default-toggle-edit-btn" class="doc-tab-btn" title="View Raw Markdown Content">
                                <span class="material-symbols-outlined tab-icon">edit_note</span>
                                <span>Raw Content</span>
                            </button>
                        </div>
                        <div class="doc-actions-right">
                            <!-- 1-Page vs 2-Page Budget Toggle -->
                            <div class="m3-segmented-control page-budget-toggle" title="Select Page Budget">
                                <button id="default-page-1-btn" class="m3-segmented-tab" data-pages="1">
                                    <span class="material-symbols-outlined tab-icon">looks_one</span>
                                    <span>1 Page</span>
                                </button>
                                <button id="default-page-2-btn" class="m3-segmented-tab active" data-pages="2">
                                    <span class="material-symbols-outlined tab-icon">looks_two</span>
                                    <span>2 Pages</span>
                                </button>
                            </div>
                            <a id="default-download-link" href="#" download="Prasad_Rane_Default_Resume.pdf" class="m3-button m3-button-filled btn-sm" title="Download PDF">
                                <span class="material-symbols-outlined btn-icon">download</span>
                                <span>Download PDF</span>
                            </a>
                            <a id="default-open-link" href="#" target="_blank" class="m3-button m3-button-outlined btn-icon-only btn-sm" title="Open in New Tab">
                                <span class="material-symbols-outlined btn-icon">open_in_new</span>
                            </a>
                        </div>
                    </div>
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/test_sidebar_navigation.py::TestSidebarNavigation::test_doc_tab_strip_structure -v`  
Expected: PASS.

---

### Task 3: Add CSS Styling for Tab Strip & Actions

**Files:**
- Modify: `src/web/static/style.css`

**Interfaces:**
- Consumes: `.doc-tab-strip`, `.doc-tabs-left`, `.doc-tab-btn`, `.doc-actions-right`, `.btn-icon-only`
- Produces: Polished glassmorphic/editorial styling with active tab indicators and responsive layout.

- [ ] **Step 1: Implement CSS rules in `src/web/static/style.css`**

Add CSS styles:
```css
/* Document Tab Strip (Clean GitHub/Docs style) */
.doc-tab-strip {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding-bottom: 0.75rem;
    margin-top: 1rem;
    margin-bottom: 1rem;
    gap: 1rem;
    flex-wrap: wrap;
}

.doc-tabs-left {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.doc-tab-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.45rem 0.9rem;
    border-radius: 8px;
    border: 1px solid transparent;
    background: transparent;
    color: var(--m3-sys-color-on-surface-variant);
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s ease;
}

.doc-tab-btn:hover {
    background: rgba(255, 255, 255, 0.04);
    color: var(--m3-sys-color-on-surface);
}

.doc-tab-btn.active {
    background: rgba(168, 199, 250, 0.12);
    color: #a8c7fa;
    border-color: rgba(168, 199, 250, 0.25);
    font-weight: 600;
}

.doc-actions-right {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-wrap: wrap;
}

.btn-icon-only {
    padding: 0.45rem 0.55rem;
    min-width: 36px;
    justify-content: center;
}
```

- [ ] **Step 2: Run all web tests**

Run: `pytest tests/test_sidebar_navigation.py tests/test_web_ui.py -v`  
Expected: All tests PASS.

---

### Task 4: Visual Verification and Commit

**Files:**
- Test: Full Pytest suite
- Verification: Web UI inspection

- [ ] **Step 1: Run full Pytest suite**

Run: `pytest -v`  
Expected: 40/40 tests PASS.

- [ ] **Step 2: Git commit changes**

```bash
git add src/web/static/index.html src/web/static/style.css tests/test_sidebar_navigation.py docs/superpowers/plans/2026-08-18-resume-viewer-tab-strip.md
git commit -m "feat(ui): implement clean top tab strip and right-aligned actions for resume viewer"
```
