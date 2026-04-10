# Summary: Plan 01-03 — Database Access Layer + Background Worker

**Phase:** 01-plugin-foundation
**Plan:** 01-03
**Status:** Complete
**Completed:** 2026-04-09

## What Was Built

| File | Change | Purpose |
|------|--------|---------|
| `grampsclean/db.py` | Created | `GrampsDb` wrapper — name formatting, event date extraction, person/family iteration |
| `grampsclean/worker.py` | Created | `ScanWorker` — threaded scan with `GLib.idle_add` callbacks, cancel support |
| `grampsclean/tool.py` | Updated | Added `self.db_wrap = GrampsDb(self.db)` + imports for db/worker |

## Acceptance Criteria

- [x] AC-1: GrampsDb.format_name() returns "Surname, Given" with "[Unknown]" fallback
- [x] AC-2: GrampsDb.get_event_date() returns Date object or None safely
- [x] AC-3: ScanWorker runs scan_fn in background thread via GLib.idle_add
- [x] AC-4: ScanWorker updates status on completion/cancellation/error
- [x] AC-5: All three files compile with `python3 -m py_compile`

## Public API for Phases 2–5

**GrampsDb (db.py):**
- `format_name(person)` → "Surname, Given" or "[Unknown]"
- `get_gramps_id(person)` → "I0042"
- `get_event_date(person, "birth"|"death")` → Date or None
- `get_year(person, "birth"|"death")` → int or None
- `iter_people()`, `iter_families()`
- `get_person_from_handle(h)`, `get_family_from_handle(h)`
- `count_people()` → int

**ScanWorker (worker.py):**
- `ScanWorker(result_list, scan_fn, db_wrap)`
- `start()` — clears list, sets "Scanning…", launches thread
- `cancel()` — signals thread to stop cleanly
- `is_running()` → bool
- scan_fn signature: `(db_wrap) → generator of (row_tuple, status_text)`

## Files Modified

- `grampsclean/db.py` (created)
- `grampsclean/worker.py` (created)
- `grampsclean/tool.py` (updated)

## Phase 1 Complete

All three plans delivered:
- 01-01: Plugin registration + skeleton window ✓
- 01-02: Tabbed window + ResultList widget ✓
- 01-03: Database access layer + background worker ✓

**Next phase: Phase 2 — Island Detection**
