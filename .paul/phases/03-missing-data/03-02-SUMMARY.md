---
phase: 03-missing-data
plan: 02
subsystem: ui
tags: [gtk3, gramps, missing-data, filter, navigation, threading]

requires:
  - phase: 03-01
    provides: MissingTab base widget, scan engine, snapshot pattern
  - phase: 02-island-detection
    provides: _navigate_person pattern (02-03 SUMMARY)

provides:
  - Living/deceased filter (ComboBoxText) on MissingTab toolbar
  - GRAMPS person navigation on row double-click
  - Per-field status count breakdown in status bar
  - Phase 3 complete: Missing Data Finder fully functional

affects: [04-impossibilities, 05-name-prefix]

tech-stack:
  added: []
  patterns:
    - living/deceased filter via is_deceased snapshot bool (no DB in worker)
    - per-field count aggregation from row[2] split in worker

key-files:
  created: []
  modified: [grampsclean/tab_missing.py]

key-decisions:
  - "is_deceased = person.get_death_ref() is not None — uses EventRef presence, not probably_alive() — avoids DB call in worker"
  - "filter_mode captured at scan-click time (same as selected) — consistent snapshot discipline"
  - "FIELD_ORDER list controls display order of counts regardless of dict iteration order"

patterns-established:
  - "Navigation: exact copy of IslandTab._navigate_person — set_active + goto_page pattern"
  - "Per-field counts: split row[2] on ', ' in worker, aggregate into dict, render via FIELD_ORDER"

duration: ~1 session
started: 2026-04-11T00:00:00Z
completed: 2026-04-11T00:00:00Z
---

# Phase 3 Plan 02: Results UI — Filter, Counts, Navigation Summary

**MissingTab completed: living/deceased filter, per-field status counts, and GRAMPS person navigation all wired into the existing scan widget.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | 1 session |
| Tasks | 2 completed |
| Files modified | 1 |
| Verify checks | 7/7 passed |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Living/deceased filter scopes results | Pass | filter_mode from ComboBoxText → snapshot → _scan_fn skip logic |
| AC-2: Status bar shows per-field breakdown | Pass | field_counts dict + FIELD_ORDER → "42 people — 12 missing Birth Date, …" |
| AC-3: Double-click navigates to person in GRAMPS | Pass | _navigate_person follows IslandTab pattern exactly; on_activate wired |

## Accomplishments

- Living/deceased filter added (ComboBoxText, right-aligned in toolbar): "All people" / "Living only" / "Deceased only"
- `is_deceased` flag captured on main thread via `person.get_death_ref() is not None` — no DB access in worker
- `_navigate_person` added, identical to IslandTab pattern — double-click switches GRAMPS to People view and highlights person
- Status bar now shows total + per-field breakdown: e.g. "42 people — 12 missing Birth Date, 8 missing Death Date, 3 missing Birth Place"

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `grampsclean/tab_missing.py` | Modified | Filter dropdown, is_deceased snapshot, filter skip logic, _navigate_person, on_activate wiring, field_counts status |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| `is_deceased = person.get_death_ref() is not None` | Simple EventRef presence check; no extra DB lookup; consistent with main-thread snapshot discipline | Future tabs can use same pattern |
| filter_mode captured at scan-click time (not at yield time) | Consistent with `selected` discipline — checkbox/filter state frozen at scan start | Prevents race if user changes filter while scan runs |
| FIELD_ORDER constant controls count display order | Dict iteration order not guaranteed across Python versions; explicit order ensures consistent UX | Copy pattern for Phase 4 rule-grouped counts |

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Phase 3 Complete

Both plans shipped:
- **03-01:** MissingTab scan engine — 4 field checkboxes, main-thread snapshot, background worker
- **03-02:** Filter, navigation, and detailed status counts

**Phase 3 goal achieved:** Users can scan for people missing birth/death dates and places, filter by living/deceased status, see a per-field breakdown of results, and double-click any row to navigate directly to that person in GRAMPS.

## Next Phase Readiness

**Ready for Phase 4 (Impossibilities Checker):**
- Main-thread snapshot pattern proven across 2 tabs — ready to scale to date/relationship rule engine
- `_navigate_person` pattern documented and reusable
- `db.py` has `get_event_date()`, `get_event_place_handle()`, `get_year()` — likely sufficient for impossibility rules; `get_event_date()` for full Date object comparisons

**Concerns:**
- Phase 4 rules require comparing dates across persons (parent/child) and families — snapshot will need to include family relationships, not just per-person data. Plan 04-01 should design the snapshot shape carefully.

**Blockers:** None

---
*Phase: 03-missing-data, Plan: 02*
*Completed: 2026-04-11*
