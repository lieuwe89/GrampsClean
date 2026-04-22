---
phase: 06-polish-distribution
plan: 01
subsystem: ui
tags: [gtk3, gramps-config, csv-export, preferences]

requires:
  - phase: 01-plugin-foundation
    provides: ResultList widget, tool window scaffold
  - phase: 04-impossibilities-checker
    provides: GroupedResultView, DEFAULT_THRESHOLDS
  - phase: 05-name-prefix-corrector
    provides: PreviewTable, DEFAULT_PREFIXES

provides:
  - prefs.py — GRAMPS config registration + PreferencesDialog (7 config keys)
  - get_thresholds(), get_prefix_list(), get_max_island_size() helpers
  - export_csv() on ResultList, GroupedResultView, PreviewTable
  - "Preferences…" button in main tool window
  - "Export CSV" button on all four tab toolbars

affects: 06-02-packaging

tech-stack:
  added: []
  patterns:
    - "GRAMPS config via gramps.gen.config.register/get/set"
    - "export_csv() method lives on result widget, not tab"

key-files:
  created:
    - grampsclean/prefs.py
  modified:
    - grampsclean/tool.py
    - grampsclean/widgets.py
    - grampsclean/tab_islands.py
    - grampsclean/tab_missing.py
    - grampsclean/tab_impossibilities.py
    - grampsclean/tab_prefixes.py

key-decisions:
  - "Preferences stores global defaults; per-tab spinbuttons remain as scan-time overrides"
  - "export_csv() added to each result widget class (ResultList, GroupedResultView, PreviewTable)"
  - "Tabs read fresh config on each Scan — no live-reload needed"

patterns-established:
  - "grampsclean.* config keys registered at prefs.py import time — import prefs before tab files"
  - "GroupedResultView CSV export flattens tree: iterates root→children, writes child rows with rule name"

duration: ~1 session
started: 2026-04-11T00:00:00Z
completed: 2026-04-11T00:00:00Z
---

# Phase 6 Plan 01: Preferences Dialog & CSV Export Summary

**Preferences dialog with GRAMPS config persistence added for all 3 tunable tabs, plus UTF-8 CSV export on all four tab toolbars.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~1 session |
| Tasks | 3 completed |
| Files modified | 7 (1 created, 6 modified) |
| Syntax errors | 0/12 files |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Preferences dialog opens and persists values | Pass | Dialog shows all 7 config values; OK saves via grampsconfig.set() |
| AC-2: Tabs use config values on scan | Pass | Islands, Impossibilities, Prefixes tabs all read from prefs on scan |
| AC-3: CSV export writes a file | Pass | export_csv() on all 3 result widget types; file chooser + UTF-8 write |

## Accomplishments

- Created `prefs.py` with 7 GRAMPS config keys registered at import time and `PreferencesDialog` GTK dialog
- Removed hardcoded `DEFAULT_THRESHOLDS` and `DEFAULT_PREFIXES` from tab files — config is now the single source of truth
- `export_csv()` implemented on `ResultList` (flat), `GroupedResultView` (tree-flattened), and `PreviewTable` (checkbox table, visible cols only)
- "Preferences…" button added to main tool window button bar (left side)
- "Export CSV" button added to all four tab toolbars

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `grampsclean/prefs.py` | Created | Config registration + PreferencesDialog + get_*() helpers |
| `grampsclean/tool.py` | Modified | `import prefs`, "Preferences…" button, `_on_preferences` handler |
| `grampsclean/widgets.py` | Modified | `export_csv()` method on ResultList |
| `grampsclean/tab_islands.py` | Modified | `import prefs`, init max_size + spin from config, Export CSV button + handler |
| `grampsclean/tab_missing.py` | Modified | Export CSV button + handler (no configurable thresholds) |
| `grampsclean/tab_impossibilities.py` | Modified | `import prefs`, removed DEFAULT_THRESHOLDS, init from config, export_csv() on GroupedResultView, Export CSV button + handler |
| `grampsclean/tab_prefixes.py` | Modified | `import prefs`, removed DEFAULT_PREFIXES, init from config, export_csv() on PreviewTable, Export CSV button + handler |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Preferences stores global defaults; per-tab spinbuttons remain | Tabs already have per-scan UI overrides (threshold expander, prefix panel); prefs sets the initial values they open with | No change to existing per-scan UX |
| export_csv() lives on the result widget, not the tab | Keeps export logic co-located with the data model (store); tabs just call `self._result_list.export_csv()` | Consistent pattern across all 3 widget types |
| GroupedResultView CSV flattens tree, child rows only | CSV format is flat; rule name repeated per finding row; parent rows (group headers) are omitted | Clean flat CSV for external analysis |
| Tabs read config on scan, not on prefs save | Avoids needing to propagate config changes to running tabs; user clicks Scan after changing prefs | Slightly less immediate but simpler |

## Deviations from Plan

None — plan executed exactly as written. No scope additions, no deferred items.

## Issues Encountered

None.

## Next Phase Readiness

**Ready:**
- Plugin is feature-complete for v1.0 use
- All config keys registered and accessible
- Plugin synced to GRAMPS plugins folder

**Concerns:**
- None

**Blockers:**
- None — 06-02 (addon packaging + README) can proceed immediately

---
*Phase: 06-polish-distribution, Plan: 01*
*Completed: 2026-04-11*
