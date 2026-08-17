# Sidebar Rail Navigation Redesign — Design Spec

**Date:** 2026-08-17  
**Status:** Approved Design  
**Scope:** Full navigation restructure from flat header tabs → sidebar icon rail + elevated visual design

---

## 1. Problem Statement

The current UI uses a flat M3 segmented control with 6 tabs crammed into a single header bar alongside logo, search, status badge, and diagnostics button. This creates several issues:

- **Header overload** — 6 tabs + search + logo + status in one line wraps badly below ~1400px
- **No visual hierarchy** — All 6 features appear equally important when "Tailor" is the primary action
- **No persistent navigation** — Everything is a single scrolling column with `display:none` tab toggling
- **No workflow context** — Users can't see where they are in the resume → tailor → review flow
- **No mobile responsiveness** for navigation at all
- **No spatial transitions** — Simple show/hide, no sense of navigation between views

---

## 2. Design Decisions (Approved)

| Decision | Choice |
|:---|:---|
| **Navigation pattern** | Left sidebar icon rail + content area (VS Code/Notion style) |
| **Sidebar behavior** | Compact icon rail (56px) that expands to ~240px on hover/click |
| **Navigation grouping** | Grouped by workflow stage: BUILD → PREPARE → EXPLORE |
| **Visual direction** | Keep M3 dark slate palette, elevate with glassmorphism, micro-gradients, left accent bar active states |

---

## 3. Navigation Architecture

### Sidebar Rail Groups

```
┌──────────────────────────────┐
│  🔷 Logo Icon                │  ← App brand mark (compact)
│                              │
│  ── BUILD ─────────────────  │  ← Section label (visible on expand)
│  📄 Resume                   │  ← Default/master resume view
│  ✨ Tailor                   │  ← ATS resume generator (primary action)
│  ✉️ Cover Letter             │  ← Cover letter studio
│                              │
│  ── PREPARE ───────────────  │
│  🧠 Interview Prep          │  ← STAR behavioral prep
│  🔗 LinkedIn                │  ← LinkedIn profile optimizer
│                              │
│  ── EXPLORE ───────────────  │
│  💬 Ask Me                   │  ← GraphRAG Q&A chatbot
│                              │
│         (spacer)             │
│                              │
│  📊 Diagnostics              │  ← Engine telemetry drawer
│  ⚙️ Settings                 │  ← Future: theme, preferences
└──────────────────────────────┘
```

### Material Symbols Mapping

| Item | Icon | Material Symbol |
|:---|:---|:---|
| Resume | 📄 | `article` |
| Tailor | ✨ | `auto_awesome` |
| Cover Letter | ✉️ | `mail` |
| Interview Prep | 🧠 | `quiz` |
| LinkedIn | 🔗 | `share` |
| Ask Me | 💬 | `chat` |
| Diagnostics | 📊 | `analytics` |
| Settings | ⚙️ | `settings` |

---

## 4. Sidebar Rail Behavior

### Collapsed State (Default — 56px wide)
- Shows only icons, centered vertically in each row
- Section labels (BUILD, PREPARE, EXPLORE) hidden
- Active item indicated by **left accent bar** (3px, primary blue) + filled icon background
- Hover shows tooltip with label name
- App logo condensed to icon mark only

### Expanded State (On hover/click — 240px wide)
- Icons shift left, labels appear with slide-in animation
- Section group labels appear as uppercase, muted text (0.7rem, `on-surface-variant`)
- Glassmorphism effect: `backdrop-filter: blur(16px)` with semi-transparent background
- Expands over content (overlay), does not push content

### Transitions
- Expand: `width` transition 250ms with `cubic-bezier(0.2, 0, 0, 1)` (M3 emphasized)
- Labels: `opacity` 0→1, `transform` translateX(-8px)→0, delayed 50ms after width starts
- Collapse: reverse, labels fade first (100ms), then width shrinks (200ms)

---

## 5. Header Simplification

### Current Header (Remove)
```
[Logo] [Search] [Tab1][Tab2][Tab3][Tab4][Tab5][Tab6] [Diag][Status]
```

### New Header (Slim)
```
[                Search Bar (centered, max-width 480px)                ] [Status Badge]
```

- Logo moves to sidebar rail top
- All 6 navigation tabs move to sidebar
- Diagnostics button moves to sidebar bottom
- Search bar centered in header, grows on focus
- Status badge remains in header right
- Header height reduces from ~60px to ~48px

---

## 6. Visual Elevation Details

### Sidebar Surface
```css
.sidebar-rail {
    background: rgba(23, 32, 51, 0.85);      /* surface-container-low with alpha */
    backdrop-filter: blur(16px) saturate(1.2);
    border-right: 1px solid var(--md-sys-color-outline-variant);
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.3);
}
```

### Active Nav Item
```css
.nav-item.active {
    background: linear-gradient(135deg, 
        rgba(168, 199, 250, 0.12), 
        rgba(168, 199, 250, 0.04));
    border-left: 3px solid var(--md-sys-color-primary);
    color: var(--md-sys-color-primary);
}
```

### Hover Nav Item
```css
.nav-item:hover {
    background: linear-gradient(135deg,
        rgba(168, 199, 250, 0.08),
        transparent);
}
```

### Cards (Refined)
- Add subtle inner glow on hover: `box-shadow: inset 0 1px 0 rgba(255,255,255,0.04)`
- Micro-lift on hover: `transform: translateY(-1px)`
- Existing elevation tokens preserved

---

## 7. Layout Structure

### Current Layout
```
┌─────────────────────────────────────────┐
│              HEADER (full width)         │
├─────────────────────────────────────────┤
│                                         │
│           CONTENT (single column)       │
│           max-width: 1280px             │
│                                         │
└─────────────────────────────────────────┘
```

### New Layout
```
┌────┬────────────────────────────────────┐
│    │         HEADER (slim, search)      │
│ S  ├────────────────────────────────────┤
│ I  │                                    │
│ D  │       CONTENT (fills remaining)    │
│ E  │       max-width: 1200px            │
│ B  │       padding: 24px               │
│ A  │                                    │
│ R  │                                    │
│    │                                    │
└────┴────────────────────────────────────┘
```

### CSS Grid Structure
```css
.app-container {
    display: grid;
    grid-template-columns: 56px 1fr;  /* rail + content */
    grid-template-rows: 48px 1fr;     /* header + main */
    min-height: 100vh;
    gap: 0;
}

.sidebar-rail {
    grid-row: 1 / -1;       /* spans full height */
    grid-column: 1;
}

.app-header {
    grid-row: 1;
    grid-column: 2;
}

.app-main {
    grid-row: 2;
    grid-column: 2;
    overflow-y: auto;
    padding: 24px;
}
```

---

## 8. Responsive Behavior

### Desktop (≥1024px)
- Full sidebar rail (56px collapsed, 240px on hover)
- Content area fills remaining width

### Tablet (768px–1023px)
- Sidebar rail always collapsed (56px), no hover expand
- Click to expand as overlay with backdrop scrim
- Content area: full width minus 56px

### Mobile (≤767px)
- Sidebar hidden completely
- Bottom navigation bar with 4 primary items (Resume, Tailor, Ask Me, More)
- "More" opens a bottom sheet with remaining items
- Header: logo + hamburger → opens sidebar as full-screen overlay

---

## 9. View Transitions

Replace current `display:none` toggling with animated transitions:

```css
/* Outgoing view */
.tab-view.leaving {
    animation: viewOut 200ms ease-in forwards;
}

/* Incoming view */
.tab-view.entering {
    animation: viewIn 250ms ease-out forwards;
}

@keyframes viewOut {
    to { opacity: 0; transform: translateY(8px); }
}

@keyframes viewIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}
```

---

## 10. Files to Modify

| File | Change Type | Description |
|:---|:---|:---|
| [`index.html`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/web/static/index.html) | **Major restructure** | Replace header nav with sidebar rail HTML, restructure grid layout |
| [`styles.css`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/web/static/styles.css) | **Major restructure** | New sidebar rail styles, glassmorphism, active states, responsive breakpoints, view transitions |
| [`app.js`](file:///C:/Users/mamat/Github/Prasad-Resumes-GraphRAG/src/web/static/app.js) | **Moderate update** | Sidebar expand/collapse logic, view transition animations, mobile bottom nav toggle |

### No Backend Changes Required
All changes are frontend-only. No API routes, Python files, or server logic needs to change.

---

## 11. Mockup Reference

The approved visual direction shows:
- Compact sidebar rail on the left with grouped BUILD / PREPARE / EXPLORE sections
- Active item highlighted with a left blue accent bar
- Settings gear icon pinned to bottom of rail
- Clean header with just the app title and search
- ATS score gauge prominently displayed in the content area
- Dark slate blue palette with elevated glassmorphism surfaces

---

## 12. Success Criteria

1. ✅ Sidebar rail visible on all desktop views, collapsible on tablet/mobile
2. ✅ Navigation grouped into BUILD / PREPARE / EXPLORE with clear section labels
3. ✅ Active state uses left accent bar (not just background fill)
4. ✅ Glassmorphism backdrop-blur on sidebar surface
5. ✅ Smooth expand/collapse transitions (250ms, M3 easing)
6. ✅ View transitions replace `display:none` toggling
7. ✅ Header simplified to search + status only
8. ✅ No regression in existing feature functionality (all 6 views work as before)
9. ✅ Mobile responsive (bottom nav bar at ≤767px)
10. ✅ All existing API integrations preserved (no backend changes)
