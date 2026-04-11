---
phase: 05-name-prefix-corrector
plan: 01
status: complete
executed: 2026-04-11

requires:
  - phase: 01-plugin-foundation
    provides: ResultList widget, ScanWorker, GrampsDb helpers

provides:
  - PrefixesTab widget (detection only, no apply yet)
  - detect_issues() pure-Python detection engine
  - _build_snapshot() name-field extractor

affects: 05-02 (preview table replaces ResultList), 05-03 (bulk apply)

key-files:
  created: grampsclean/tab_prefixes.py
  modified: grampsclean/tool.py

key-decisions:
  - "DEFAULT_PREFIXES sorted longest-first to prevent 'van' matching before 'van der'"
  - "detect_issues() breaks on first matching prefix per person (one issue per person)"
  - "prefix_field non-empty → skip entirely (correctly placed prefix is never flagged)"

patterns-established:
  - "Name field extraction: name_obj.get_surname_list()[0].get_prefix() for prefix field"
  - "Tab follows identical structure to ImpossibilitiesTab (snapshot + worker + ResultList)"

duration: ~1 session
completed: 2026-04-11
---

# Phase 5 Plan 01: Prefix Detection Engine

**PrefixesTab with configurable prefix dictionary, main-thread snapshot builder, pure-Python detection engine, and ResultList display — replacing the Phase 5 placeholder in tool.py.**

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Prefix detected in given name | Pass | `given_lower.startswith(prefix + " ")` guard |
| AC-2: Prefix detected in surname | Pass | `surname_lower.startswith(prefix + " ")` guard |
| AC-3: Correctly placed prefix not flagged | Pass | `if p["prefix"]: continue` guard |
| AC-4: Configurable prefix list | Pass | Gtk.TextView expander, parsed at scan time |
| AC-5: Navigation on double-click | Pass | `_navigate_person` — same pattern as other tabs |
| AC-6: No-findings graceful | Pass | Empty sentinel yield → "No prefix issues found." |

## Files Created / Modified

| File | Change | Purpose |
|------|--------|---------|
| `grampsclean/tab_prefixes.py` | Created | Full PrefixesTab widget + detection engine |
| `grampsclean/tool.py` | Modified | PLACEHOLDER_TABS removed; PrefixesTab wired as Tab 3 |

## What Was Built

### `grampsclean/tab_prefixes.py`

- **`DEFAULT_PREFIXES`** — 25 Dutch/German/French prefixes, sorted longest-first (ensures "van der" is matched before "van")
- **`_build_snapshot(db_wrap)`** — main-thread function; extracts `given`, `surname`, `prefix` (from `surname_list[0].get_prefix()`), `name`, `gramps_id` per person into plain Python dicts
- **`detect_issues(snapshot, prefixes)`** — pure Python; iterates snapshot, skips persons with non-empty prefix field, checks given name then surname with `startswith(prefix + " ")`, breaks on first match, sorts findings by name
- **`PrefixesTab(Gtk.Box)`** — Scan/Cancel toolbar + "Prefix Settings" Gtk.Expander (editable Gtk.TextView, default text = DEFAULT_PREFIXES joined by newline) + ResultList(Name, ID, Issue) + navigation

### `grampsclean/tool.py`

- Removed `from widgets import ResultList` import (no longer used)
- Removed `PLACEHOLDER_TABS` constant
- Removed placeholder loop in `_build_window`
- Added `from tab_prefixes import PrefixesTab`
- Added `PrefixesTab(self.db_wrap, self.uistate)` as Tab 3

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Break on first matching prefix per person | Avoids duplicate findings for same person; one clear issue per row | Simplest UX; Plan 05-02 preview table remains one-row-per-person |
| Longest-first prefix ordering | Prevents "van" matching "van der Berg" — would miss the full prefix | Must be maintained if user edits the list |
| `prefix_field non-empty → skip` | If GRAMPS already has a prefix field value, the data is correct — no need to flag | Conservative: avoids false positives |

## Deviations

None — plan executed exactly as specified.

## Next Phase Readiness

**Ready for 05-02:**
- `PrefixesTab` exists with `_result_list`, `_snapshot`, `_active_prefixes`, `_scan_fn` all in place
- `detect_issues()` returns finding dicts with `handle`, `name`, `gramps_id`, `issue` — sufficient for preview table
- Plan 05-02 will replace `ResultList` with a two-column before/after preview table with row checkboxes

**Concerns for 05-03:**
- GRAMPS DB write access: `db.commit_person()` requires write-capable DB — need to verify the Tool API exposes a writable db (it should via `tool.Tool.self.db`, but confirm at plan time)
- Undo support: GRAMPS transactions wrap writes in an undoable batch — plan how to use `DbTxn` correctly

**Blockers:** None
