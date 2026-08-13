"""
resume_structured_parser.py -- Structured resume parser that converts
MASTER_RESUME.txt into a dict matching the ResumeData Pydantic model shape.

Parses markdown-formatted resume sections using regex/pattern matching --
no LLM calls required. Designed for pre-indexing before GraphRAG ingestion.
"""

import re
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_md(text: str) -> str:
    """Remove markdown bold, italic, link, and code syntax."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\[(.+?)\]\([^)]*\)', r'\1', text)
    return text.strip()


# Emoji markers in the resume header
_LOC_EMOJI  = "\U0001F4CD"    # Location pin
_PHONE_EMOJI = "\U0001F4DE"   # Phone
_MAIL_EMOJI = "✉️"             # Envelope (with variation selector)
_CAL_EMOJI  = "\U0001F5D3"    # Spiral calendar (used for job dates)


# ---------------------------------------------------------------------------
# Section helpers
# ---------------------------------------------------------------------------

def _split_by_dividers(text: str) -> List[str]:
    """Split content by ``---`` horizontal-rule dividers. Returns list of
    non-empty section blocks."""
    parts = re.split(r'^---\s*$', text, flags=re.MULTILINE)
    return [p.strip() for p in parts if p.strip()]


def _get_section_block(dividers: List[str], marker_pattern: str):
    """Return the first divider block containing a line that matches
    *marker_pattern* (case-insensitive). Scans ALL lines within each block.
    Returns the full block string, or ``None``.
    """
    pat = re.compile(marker_pattern, re.IGNORECASE)
    for blk in dividers:
        if blk and any(pat.search(ln) for ln in blk.split('\n')):
            return blk
    return None


# ---------------------------------------------------------------------------
# Name / Contact
# ---------------------------------------------------------------------------

def _extract_name(raw: str) -> str:
    """Extract name from H1 heading '# PRASAD RANE — ...'."""
    m = re.search(r'^#\s+(.+?)[—\-]', raw, re.MULTILINE)
    if m:
        return m.group(1).strip()
    m = re.search(r'^\*\*(.+?)\*\*\s*$', raw, re.MULTILINE)
    if m:
        return _strip_md(m.group(1))
    return ''


def _extract_contact(raw: str) -> Dict[str, str]:
    """Extract contact fields from the contact-info line."""
    result = {
        'contact_location': '',
        'contact_phone': '',
        'contact_email': '',
        'contact_linkedin': '',
        'contact_portfolio': '',
    }
    for line in raw.split('\n'):
        s = line.strip()
        if s.startswith('#') or not s or s.startswith('>'):
            continue
        if '@' in s or 'linkedin.com' in s or '513' in s:
            m = re.search(_LOC_EMOJI + r'\s*\*?(.*?)\*?\s*\|', s)
            if m: result['contact_location'] = m.group(1).strip()
            m = re.search(_PHONE_EMOJI + r'\s*(\+?\d[\d\-]+)', s)
            if m: result['contact_phone'] = m.group(1)
            m = re.search(_MAIL_EMOJI + r'\s*(\S+@\S+\.\S+)', s)
            if m: result['contact_email'] = m.group(1)
            m = re.search(r'https?://linkedin\.com/[^\s\)]+', s)
            if m: result['contact_linkedin'] = m.group(0)
            m = re.search(
                r'https?://(?!linkedin)[^\s\)]+\.(app|io|com|dev)[^\s\)]*', s
            )
            if m: result['contact_portfolio'] = m.group(0)
            break
    return result


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def _extract_summary(dividers: List[str]) -> str:
    """Extract canonical + domain-specific summary texts."""
    summaries: List[str] = []

    # Canonical Summary -- single paragraph after heading
    canon = _get_section_block(dividers, r'Canonical\s+Summary')
    if canon:
        for line in canon.split('\n'):
            stripped = line.strip()
            if not stripped:
                continue
            if re.match(r'^#+\s', stripped):       # skip all ## headings
                continue
            cleaned = _strip_md(stripped)
            if cleaned:
                summaries.append(cleaned)
                break

    # Domain-specific variants: ``- **Label**: text``
    domains = _get_section_block(dividers, r'Domain.*Summary|Domain-Specific')
    if domains:
        for b in re.finditer(
            r'^-\s+\*\*([^*]+)\*\*\s*:\s*(.+)$', domains, re.MULTILINE
        ):
            label = b.group(1).strip()
            text = _strip_md(b.group(2).strip())
            summaries.append(f'**{label}**: {text}')

    return '\n\n'.join(summaries).strip() if summaries else ''


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------

def _extract_skills(dividers: List[str]) -> Dict[str, List[str]]:
    """Skills grouped by category: {category: [skill, ...]}."""
    skills: Dict[str, List[str]] = {}
    block = _get_section_block(dividers, r'^##[^#]*[Ss]kills')
    if not block:
        return skills
    for line in block.split('\n'):
        cm = re.match(r'^-\s+\*\*([^*]+)\*\*\s*:\s*(.+)$', line.strip())
        if cm:
            category = cm.group(1).strip()
            items = []
            for part in cm.group(2).split(';'):
                for token in part.split(','):
                    t = token.strip()
                    if t:
                        items.append(t)
            if items:
                skills[category] = items
    return skills


# ---------------------------------------------------------------------------
# Certifications
# ---------------------------------------------------------------------------

def _extract_certifications(dividers: List[str]) -> List[str]:
    """Certification titles (excludes planned/future certs)."""
    certs: List[str] = []
    block = _get_section_block(dividers, r'^##[^#]*[Cc]ertifications')
    if not block:
        return certs
    for bullet in block.split('\n'):
        b = bullet.strip()
        if ('[' in b and '(' in b and ')' in b and '(Planned' not in b):
            tm = re.search(r'\[\*\*(.+?)\*\*\]', b)
            if tm:
                certs.append(_strip_md(tm.group(1)))
    return certs


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------

def _extract_education(dividers: List[str]) -> List[str]:
    """Education entries as list of strings."""
    entries: List[str] = []
    block = _get_section_block(dividers, r'^##[^#]*[Ee]ducation')
    if not block:
        return entries
    for bullet in block.split('\n'):
        b = bullet.strip()
        if b.startswith('- ') and '**' in b:
            entries.append(_strip_md(b[2:].strip()))
    return entries


# ---------------------------------------------------------------------------
# Experience / Jobs
# ---------------------------------------------------------------------------

_COMPANY_RE = re.compile(r'^#{3}\s+\*\*[^*]+\*\*\s*[—\-]')
_SUBSECTION_RE = re.compile(r'^#{4}\s+(.*)$')


def _extract_jobs(dividers: List[str]) -> List[Dict[str, Any]]:
    """Parse experience stories into a flat list of JobEntry-shaped dicts.

    Each subsection (Story N - Title or any level-4 heading under a company
    header) becomes its own dict entry. All entries from the same company
    share inherited title, company, location, and dates fields.
    """
    # Collect all contiguous blocks from the experience section.
    # The experience section may be split across multiple --- divider
    # blocks (one per company). Start at the block containing the
    # "## Exhaustive Experience" heading and continue until we hit a
    # block whose first non-blank line is a different ## heading
    # (e.g. Education, Gap-Framing) or we run out of blocks.
    exp_pat = re.compile(
        r'^##.*[Ee]xhaustive|[Ee]xperience.*[Bb]ullet', re.IGNORECASE
    )
    next_section_pat = re.compile(r'^##[^#]')

    def _first_heading(block: str) -> str:
        for ln in block.split('\n'):
            ls = ln.strip()
            if ls:
                return ls
        return ''

    start_idx: Optional[int] = None
    for idx, blk in enumerate(dividers):
        if blk and any(exp_pat.search(ln) for ln in blk.split('\n')):
            start_idx = idx
            break
    if start_idx is None:
        return []
    # Find end: first block after start whose leading line is a new ## section.
    end_idx = len(dividers)
    for idx in range(start_idx + 1, len(dividers)):
        fh = _first_heading(dividers[idx])
        if fh and next_section_pat.match(fh):
            end_idx = idx
            break
    exp_text = '\n\n'.join(dividers[start_idx:end_idx])
    lines = exp_text.split('\n')

    jobs: List[Dict[str, Any]] = []
    parent: Dict[str, Any] = {}
    bullets: List[str] = []
    heading: Optional[str] = None
    has_parent = False

    def _flush():
        nonlocal bullets, heading
        if bullets:
            entry = {
                'title': parent.get('title', ''),
                'company': parent.get('company', ''),
                'location': parent.get('location', ''),
                'dates': parent.get('dates', ''),
                'heading': heading or '',
                'bullets': list(bullets),
                'bullet_stories': [],
            }
            jobs.append(entry)
        bullets.clear()
        heading = None

    def _parse_company_header(line_text: str):
        hm = re.match(
            r'^#{3}\s+\*\*([^*]+)\*\*\s*[—\-]\s*\*([^*]+)\*?', line_text
        )
        if hm:
            parent['title'] = _strip_md(hm.group(1))
            parent['company'] = _strip_md(hm.group(2))
            parent['location'] = ''
            parent['dates'] = ''
            nonlocal has_parent
            has_parent = True

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if _COMPANY_RE.match(line):
            _flush()
            _parse_company_header(line)
            i += 1
            # Consume location/date info beneath header; skip blanks
            while i < len(lines):
                ll = lines[i].strip()
                if not ll:
                    i += 1
                    continue
                if (ll.startswith('- ') or _COMPANY_RE.match(ll) or
                        _SUBSECTION_RE.match(ll) or
                        (ll.startswith('##') and not ll.startswith('###'))):
                    break
                loc_m = re.search(
                    _LOC_EMOJI + r'\s*\*?(.*?)\*?\s*\|', ll
                )
                date_m = re.search(
                    _CAL_EMOJI + '️?' + r'\s*\*?(.*?)\*?\s*$', ll
                )
                if loc_m:
                    parent['location'] = loc_m.group(1).strip()
                if date_m:
                    parent['dates'] = date_m.group(1).strip()
                i += 1
            continue

        sm = _SUBSECTION_RE.match(line)
        if sm and has_parent:
            _flush()
            heading = _strip_md(sm.group(1).strip()).strip(':-—')
            i += 1
            continue

        if stripped.startswith('- ') and has_parent:
            cleaned = _strip_md(stripped[2:].strip()).strip()
            if cleaned:
                bullets.append(cleaned)
            i += 1
            continue

        i += 1

    _flush()
    return jobs


# ---------------------------------------------------------------------------
# Gap Framing
# ---------------------------------------------------------------------------

def _extract_gap_framing(raw: str) -> str:
    """Optional cheat-sheet table at end of resume."""
    m = re.search(
        r'##[^#]*[Gg]ap[^#]*\n((?:[^\n]*\|[^\n]*\n)+)', raw
    )
    return m.group(1).strip() if m else ''


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_master_resume(raw_text: str) -> Dict[str, Any]:
    """Parse MASTER_RESUME.txt into a ResumeData-matching dictionary.

    Args:
        raw_text: Raw markdown text read from input/MASTER_RESUME.txt.

    Returns:
        Dict mirroring the ResumeData Pydantic model, plus extras
        (*skills* as dict-of-lists, *gap_framing* as plain string).
    """
    dividers = _split_by_dividers(raw_text)

    return {
        'name': _extract_name(raw_text),
        'title': '',
        **_extract_contact(raw_text),
        'summary': _extract_summary(dividers),
        'jobs': _extract_jobs(dividers),
        'skills': _extract_skills(dividers),
        'certifications': _extract_certifications(dividers),
        'education': _extract_education(dividers),
        'gap_framing': _extract_gap_framing(raw_text),
    }
