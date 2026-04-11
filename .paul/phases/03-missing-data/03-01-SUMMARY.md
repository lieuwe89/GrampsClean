---
phase: 03-missing-data
plan: 01
subsystem: ui
tags: [gtk3, gramps, missing-data, scanner, threading]

requires:
  - phase: 01-plugin-foundation
    provides: GrampsDb wrapper, ResultList widget, ScanWorker pattern
  - phase: 02-island-detection
    provides: main-thread snapshot pattern, navigation pattern (for 03-02)

provides:
  - MissingTab widget with 4 field checkboxes and background scan
  - get_event_place_handle() helper in GrampsDb
  - Missing Data tab wired into main GrampsClean notebook

affects: [03-02, 04-impossibilities, 05-name-prefix]

tech-stack:
  added: []
  patterns: [field-presence snapshot — bool flags captured on main thread before worker start]

key-files:
  created: [grampsclean/tab_missing.py]
  modified: [grampsclean/db.py, grampsclean/tool.py]

key-decisions:
  - "Snapshot captures bool flags (missing=True/False) not raw event objects — keeps worker data minimal"
  - "selected dict captured before snapshot so checkbox state at scan-time is preserved"

patterns-established:
  - "Field presence snapshot: capture bool flags on main thread, pass plain dict to worker"
  - "FIELD_LABELS dict maps internal key → display string, shared between snapshot and worker"

duration: ~1 session
started: 2026-04-11T00:00:00Z
completed: 2026-04-11T00:00:00Z
---

# Phase 3 Plan 01: Missing-Field Scanner Summary

**MissingTab widget delivered — scans all persons for missing birth/death dates and places via configurable checkboxes, following the mandatory main-thread snapshot pattern.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | 1 session |
| Tasks | 3 completed |
| Files modified | 3 |
| Verify checks | 7/7 passed |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Field checkboxes control what is scanned | Pass | `selected` dict from checkboxes drives filtering in `_scan_fn` |
| AC-2: Scan finds all people missing at least one selected field | Pass | Worker iterates snapshot, yields rows where any `selected[f] and info[f]` is True |
| AC-3: Main-thread snapshot / background worker pattern respected | Pass | All DB reads in `_on_scan()` on main thread; `_scan_fn` uses only plain Python dicts |
| AC-4: MissingTab replaces placeholder in tool window | Pass | Tab 1 in notebook; "Missing Data" removed from PLACEHOLDER_TABS |

## Accomplishments

- Created `tab_missing.py` (168 lines) with `MissingTab(Gtk.Box)` — full scan lifecycle: toolbar, snapshot, worker, result display
- Extended `db.py` with `get_event_place_handle()` — place presence check used by all future tabs needing place data
- Replaced "Missing Data" placeholder with functional `MissingTab` in `tool.py`; only Impossibilities and Name Prefixes remain as placeholders

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `grampsclean/tab_missing.py` | Created | MissingTab widget — field checkboxes, main-thread snapshot, background scan, result list |
| `grampsclean/db.py` | Modified | Added `get_event_place_handle(person, event_type)` — returns place handle or None |
| `grampsclean/tool.py` | Modified | Import MissingTab, wire as Tab 1, remove Missing Data placeholder |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| Snapshot stores bool flags (missing=True), not event objects | Keeps worker data minimal — no risk of accidentally accessing DB objects in worker | All future tabs should use same bool-flag pattern when the check is simple presence |
| `selected` dict captured at scan-click time, not at worker time | Checkbox state could change mid-scan; capturing upfront prevents race | Consistent with Phase 2 snapshot-before-worker approach |
| `on_activate=None` for ResultList | Navigation is 03-02 scope; wiring it now would be premature | 03-02 will add `_navigate_person` and pass it as `on_activate` |

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

**Ready for 03-02:**
- `MissingTab` class exists and runs; scan produces correct rows including hidden handle as 4th element
- `ResultList` already accepts `on_activate` callback — just needs to be passed in 03-02
- `_navigate_person` pattern is documented in 02-03 SUMMARY for direct reuse

**Concerns:**
- `get_event_date()` returns `None` for events with non-regular dates (uncertain, ranges). This is intentional — uncertain dates count as "missing" for the scanner. Acceptable for MVP; could be made configurable later.

**Blockers:** None

---
*Phase: 03-missing-data, Plan: 01*
*Completed: 2026-04-11*
