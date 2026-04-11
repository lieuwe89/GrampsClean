---
phase: 05-name-prefix-corrector
plan: 02
subsystem: ui
tags: [gtk, liststore, treeview, checkbox, preview-table]

requires:
  - phase: 05-01
    provides: PrefixesTab with detect_issues() detection engine and ResultList display

provides:
  - PreviewTable widget (Gtk.ListStore, 9-col, checkbox + current/proposed columns)
  - detect_issues() enriched with prefix_found, field_type, current_value, proposed_value
  - Select All / Deselect All toolbar buttons
  - get_selected_findings() API for Plan 05-03 to consume

affects: [05-03-bulk-apply]

tech-stack:
  added: []
  patterns: [PreviewTable pattern — opt-out checkbox UX (all pre-checked), 9-tuple row protocol via ScanWorker *row_tuple unpack]

key-files:
  created: []
  modified: [grampsclean/tab_prefixes.py]

key-decisions:
  - "PreviewTable uses Gtk.ListStore (flat, not TreeStore) — checkboxes simpler on flat model"
  - "All rows pre-checked (opt-out UX) — most common case is apply all"
  - "No Apply button in this plan — write logic belongs in 05-03 with DbTxn"
  - "proposed_value recomputed in get_selected_findings() from current+prefix — no need to store separately"

patterns-established:
  - "9-tuple row protocol: (bool, name, id, field, current, proposed, handle, prefix, ftype)"
  - "append_row guards on empty name — handles no-findings sentinel yield"

duration: ~1 session
started: 2026-04-11T00:00:00Z
completed: 2026-04-11T00:00:00Z
---

# Phase 5 Plan 02: Preview Table Summary

**PreviewTable widget with checkbox, Current/Proposed columns wired into PrefixesTab — user can review and select prefix corrections before committing.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~1 session |
| Tasks | 2 completed |
| Files modified | 1 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Preview shows current and proposed values | Pass | Field, Current, Proposed columns populated from enriched detect_issues() |
| AC-2: Checkboxes individually toggleable | Pass | `_on_toggled` handler toggles `_COL_CHECKED` per row |
| AC-3: Select All / Deselect All | Pass | Toolbar buttons wired to `select_all()` / `deselect_all()` |
| AC-4: get_selected_findings() returns checked rows only | Pass | Iterates store, filters on `_COL_CHECKED`, returns handle/prefix/ftype/proposed_value |
| AC-5: Double-click navigation | Pass | `_row_activated` → `_on_activate(handle)` → `_navigate_person` |
| AC-6: No-findings case handled | Pass | Yields `(False, "", ...)` sentinel; `append_row` guards on empty name |

## Accomplishments

- `detect_issues()` now returns `prefix_found`, `field_type`, `current_value`, `proposed_value` per finding
- `PreviewTable` class: 9-column ListStore with toggle, select/deselect, row navigation, `get_selected_findings()` API
- `PrefixesTab` toolbar extended with Select All / Deselect All buttons
- `_scan_fn` yields 9-tuples consumed by `ScanWorker` via `*row_tuple` unpack — no worker changes needed
- `ResultList` import removed; `PreviewTable` is the sole result view for this tab

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `grampsclean/tab_prefixes.py` | Modified | detect_issues enrichment, PreviewTable class, PrefixesTab wiring |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| No Apply button | Write logic with DbTxn undo belongs in 05-03 | Clean separation; 05-03 reads `get_selected_findings()` |
| All rows pre-checked | Opt-out UX — most users apply all findings | User deselects exceptions; fewer clicks for common case |
| proposed_value recomputed on read | Avoids storing a derived value in the store | `get_selected_findings()` computes `current[len(prefix)+1:]` at call time |

## Deviations from Plan

None — plan executed exactly as written.

## Next Phase Readiness

**Ready:**
- `get_selected_findings()` returns `[{handle, prefix_found, field_type, proposed_value}]` — exactly what 05-03 needs to write corrections
- `PrefixesTab` has `self._result_list` (PreviewTable) accessible for adding Apply button in 05-03

**Concerns:**
- 05-03 must verify GRAMPS write API: `with DbTxn("Fix prefixes", db) as trans: db.commit_person(person, trans)` — not yet tested
- Name/Surname mutation order (in-memory edit before commit) needs care

**Blockers:**
- None

---
*Phase: 05-name-prefix-corrector, Plan: 02*
*Completed: 2026-04-11*
