# Resume Structured Parser — Completed

## Status: ✅ All bugs fixed, 13/13 tests passing

## Bugs Fixed

### Bug 1: `_parse_company_header` regex mismatch (primary — caused 0 jobs)
- **Root cause**: Regex `r'^#{3}\s+\*\*([^*]+)\*\*[—\-]'` required `**` immediately
  followed by `—`, but actual input has `** — ` (space before em-dash).
- **Fix**: Added `\s*` before `[—\-]`: `r'^#{3}\s+\*\*([^*]+)\*\*\s*[—\-]'`
- **NOTE**: `_COMPANY_RE` already had `\s*` — the two regexes were inconsistent.

### Bug 2: Inner loop consumed `####` subsection headings
- **Root cause**: Break condition `(ll.startswith('#') and not ll.startswith('###'))`
  catches `## ` but NOT `#### Story` (because `####` does start with `###`).
- **Fix**: Added `_SUBSECTION_RE.match(ll)` to break conditions.
- **Also fixed**: Changed `startswith('#')` to `startswith('##')` for clarity.

### Bug 3: Location/date regex captured empty strings
- **Root cause (location)**: `(.*?)` non-greedy with no anchor → captures nothing.
- **Root cause (date)**: Used `_PHONE_EMOJI` (📞) instead of calendar emoji (🗓️ =
  U+1F5D3 + U+FE0F). Also had same empty-capture issue.
- **Fix**: Added `_CAL_EMOJI = "\U0001F5D3"`, anchored location regex with `\s*\|`,
  anchored date regex with `\s*$`.

### Bug 4: `_extract_name` regex matched `### Domain-Specific` as H1
- **Root cause**: `r'#\s+(.+?)[—\-]'` (unanchored) matched the 3rd `#` in
  `### Domain-Specific` + space + `Domain` + `-`.
- **Fix**: Anchored to `r'^#\s+(.+?)[—\-]'` with `re.MULTILINE`.

### Bug 5: Experience section split across `---` dividers
- **Root cause**: `_get_section_block` returned only the first matching block.
  The real resume has `---` between companies, splitting experience into 4 blocks.
- **Fix**: Replaced single-block lookup with contiguous block collection — find
  start block (matching `## Exhaustive Experience`), then consume all blocks
  until hitting a block whose first heading is a new `## ` section.

## Real Resume Output (validated)

| Field              | Value                                              |
|--------------------|----------------------------------------------------|
| name               | PRASAD RANE                                        |
| jobs               | 17 entries (11 Rocket, 3 London, 2 EXFO, 1 Tanish)|
| skills             | 9 categories, 94 total                            |
| certifications     | AWS Certified Cloud Practitioner                   |
| education          | 2 entries                                          |

## Files Modified

- `src/converters/resume_structured_parser.py` — all 5 bug fixes
- `tests/test_resume_structured_parser.py` — NEW, 13 tests (unit + integration)

## Test Results

```
tests/test_resume_structured_parser.py: 13 passed
Full test suite: 273 passed, 15 failed (all pre-existing, unrelated to parser)
```

## Architecture Decisions (unchanged from yesterday)

- Used `---` divider-based section splitting (not regex spanning)
- Experience section spans multiple divider blocks (one per company)
- `bullets` stored as clean strings (markdown stripped), `bullet_stories` always `[]`
- `skills` returned as `dict[str, list[str]]` to preserve category groupings
- No LLM calls, no external dependencies beyond `re` and typing

## Next Steps (optional, not started)

1. Integrate parser into pre-indexing pipeline (currently standalone)
2. Wire parser output into `ResumeData` Pydantic model for end-to-end validation
3. Optionally emit `bullet_stories` from `input/03-Story-Bank.txt` if cross-referencing needed
