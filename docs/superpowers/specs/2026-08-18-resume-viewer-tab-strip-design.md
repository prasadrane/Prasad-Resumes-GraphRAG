# Resume Viewer Clean Tab Strip & Toolbar Redesign

**Date:** 2026-08-18  
**Status:** Approved  
**Scope:** Frontend UI Toolbar & Viewer Layout (`src/web/static/index.html`, `src/web/static/style.css`, `src/web/static/app.js`)

---

## 1. Problem Statement

In the web application's **Master Default Resume** view (`#default-view`), the top-right header area contained four distinct button containers (`[ 1 Page | 2 Pages ]`, `[ PDF Preview | Raw Content ]`, `[ Download PDF ]`, and `[ Open in New Tab ]`). Because of container width constraints in `.panel-header.flex-between`, these controls wrapped into two uneven rows of pill buttons directly adjacent to the panel title, causing visual clutter, shape overload, and awkward alignment.

---

## 2. Target Design & Layout

We are implementing **Idea 3: Clean Top Tab Strip (GitHub / Docs Style) with Right-Aligned Actions**.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ 📇 Master Default Resume                                                               │
│ Standard ATS master resume for Prasad Rane. View PDF preview or inspect raw Markdown.  │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [ 📄 PDF Preview ]  [ 📝 Raw Content ]     │      [ 1 Page | 2 Pages ]   [ ⬇ PDF ] [ ↗ ] │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│                                [ PDF / RAW VIEWER ]                                    │
│                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Key Architectural Elements:

1. **Header Component (`.panel-header`)**:
   - Contains only the view title `<h2>` and subtitle `<p>`.
   - Free of all action buttons and view toggles, giving the title breathing room and clean vertical rhythm.

2. **Dedicated Control Strip (`.doc-tab-strip`)**:
   - Placed directly between the panel header and the preview body.
   - Sits on a full-width container with a subtle bottom divider border (`1px solid var(--m3-sys-color-outline-variant)`).
   - **Left Section (`.doc-tabs-left`)**:
     - Modern tab buttons (`[ 📄 PDF Preview ]` and `[ 📝 Raw Content ]`) with an active indicator bottom-line / accent state.
   - **Right Section (`.doc-actions-right`)**:
     - Segmented Page Budget Switch: `[ 1 Page | 2 Pages ]`
     - Primary Action: `[ ⬇ Download PDF ]` (compact filled button)
     - Secondary Quick Action: `[ ↗ ]` (compact icon-only button with tooltip "Open in New Tab")

3. **Shared Architecture for Tailored Resume View**:
   - Apply the same clean tab strip pattern across `#tailor-view` output panel for design consistency throughout the application.

---

## 3. Technical Changes

### HTML (`src/web/static/index.html`)
- Move `.preview-actions` out of `.panel-header` into a new `.doc-tab-strip` container.
- Structure `.doc-tab-strip` with `.doc-tabs-left` and `.doc-actions-right`.

### CSS (`src/web/static/style.css`)
- Style `.doc-tab-strip` with `display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 0.75rem; margin-bottom: 1rem;`.
- Add tab underline indicator styles for active view tabs.
- Ensure responsive breakpoints where `.doc-tab-strip` handles tablet/mobile screen sizes gracefully without overflow.

### JS (`src/web/static/app.js`)
- Maintain existing ID bindings (`#default-page-1-btn`, `#default-page-2-btn`, `#default-toggle-pdf-btn`, `#default-toggle-edit-btn`, `#default-download-link`, `#default-open-link`) so all event listeners and state management function seamlessly.

---

## 4. Verification Plan

1. **Automated Tests**:
   - Run `pytest tests/test_sidebar_navigation.py tests/test_web_ui.py -v` to ensure all UI structure and endpoint tests pass.
2. **Visual Inspection**:
   - Launch local server or inspect rendered layout to verify single-row alignment, tab switching, and responsiveness.
