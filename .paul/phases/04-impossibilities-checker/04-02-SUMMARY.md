---
phase: 04-impossibilities-checker
plan: 02
subsystem: ui
tags: [gramps, gtk3, spinbutton, expander, thresholds, configuration]

requires:
  - phase: 04-impossibilities-checker/04-01
    provides: DEFAULT_THRESHOLDS dict, run_rules(snapshot, thresholds) signature, ImpossibilitiesTab widget

provides:
  - _build_config_panel() — collapsed GTK Expander with 5 threshold spinbuttons pre-filled from DEFAULT_THRESHOLDS
  - _active_thresholds — user-configured threshold dict captured on main thread at scan time
  - ImpossibilitiesTab now passes live spinbutton values to run_rules() instead of DEFAULT_THRESHOLDS

affects: [04-03-results-ui]

tech-stack:
  added: []
  patterns:
    - GTK Expander as collapsible config panel — collapsed by default, zero visual weight when not needed
    - Gtk.Adjustment for integer spinbuttons (clean steps, bounded range)
    - Threshold capture on main thread in _on_scan() before worker start — consistent with SQLite threading rule

key-files:
  created: []
  modified: [grampsclean/tab_impossibilities.py]

key-decisions:
  - "Threshold capture in _on_scan() (main thread) not _scan_fn() (worker thread) — preserves threading contract"
  - "_active_thresholds initialised to dict(DEFAULT_THRESHOLDS) in __init__ — safe if somehow called before first scan"
  - "Expander collapsed by default — doesn't intrude on users who want defaults"

patterns-established:
  - "Config panel pattern: Gtk.Expander wrapping Gtk.Grid with label/spinbutton pairs — reusable for Phase 5/6 settings"

duration: ~1 session
started: 2026-04-11T00:00:00Z
completed: 2026-04-11T00:00:00Z
---

# Phase 4 Plan 02: Threshold Configuration UI Summary

**ImpossibilitiesTab gains a collapsed "Threshold Settings" expander with 5 integer spinbuttons; scan now uses live spinbutton values instead of hardcoded DEFAULT_THRESHOLDS.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | 1 session |
| Tasks | 2 completed |
| Files modified | 1 |
| Verify checks | All passed |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Config panel visible and expandable | Pass | Expander collapsed by default between toolbar and results; expands to 5 labeled spinbuttons with DEFAULT_THRESHOLDS values |
| AC-2: Custom thresholds used in scan | Pass | _on_scan captures spinbutton values into _active_thresholds; run_rules() receives them |
| AC-3: Defaults preserved when panel untouched | Pass | _active_thresholds initialised to dict(DEFAULT_THRESHOLDS) — untouched spinbuttons produce identical results to prior behaviour |

## Accomplishments

- `_build_config_panel()` produces a fully self-contained GTK Expander — no state leak, returns widget ready to pack
- Threshold capture correctly placed on the main thread inside `_on_scan()`, consistent with the SQLite threading contract established in 02-02
- `DEFAULT_THRESHOLDS` module-level dict unchanged — still serves as the authoritative source of initial spinbutton values

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `grampsclean/tab_impossibilities.py` | Modified | Added `_build_config_panel()`, `_active_thresholds` init, threshold capture in `_on_scan()`, wired `_scan_fn()` to use live values |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Threshold capture in `_on_scan()` not `_scan_fn()` | `_scan_fn()` runs in worker thread — no GTK widget access allowed there | Threading contract preserved; no risk of race condition |
| Expander collapsed by default | Users scanning with defaults shouldn't see config noise | Clean default UX; power users expand when needed |

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

**Ready for Phase 4 Plan 03 (Results UI — grouped by rule):**
- Finding dict shape (`rule_id`, `severity`, `rule_name`) unchanged — 04-03 can group/filter as planned
- `run_rules()` signature unchanged — 04-03 needs no rule engine modifications
- Threshold config UI is complete and self-contained — 04-03 adds results grouping only

**Concerns:**
- None

**Blockers:** None

---
*Phase: 04-impossibilities-checker, Plan: 02*
*Completed: 2026-04-11*
