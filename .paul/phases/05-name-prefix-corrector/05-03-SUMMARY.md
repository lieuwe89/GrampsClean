---
phase: 05-name-prefix-corrector
plan: 03
subsystem: ui
tags: [gtk, gramps-db, dbtxn, write, undo, transaction]

requires:
  - phase: 05-02
    provides: PreviewTable with get_selected_findings() API returning checked rows

provides:
  - Apply Selected button wired to _on_apply() handler
  - Single DbTxn wrapping all corrections — one undo entry in GRAMPS history
  - Given name / surname prefix write via Name API (set_first_name / set_surname / set_prefix)

affects: [06-polish-distribution]

tech-stack:
  added: [gramps.gen.db.DbTxn]
  patterns: ["Lazy import not used — module-level import from gramps.gen.db (not gramps.db)"]

key-files:
  created: []
  modified: [grampsclean/tab_prefixes.py]

key-decisions:
  - "One DbTxn for all selected rows — single GRAMPS undo entry"
  - "Apply runs on main GTK thread (button click) — no threading concern, main thread has write access"
  - "No auto-clear after apply — user initiates re-scan deliberately"
  - "Apply button disabled during active scan (re-enabled by _check_done)"

patterns-established:
  - "GRAMPS write pattern: with DbTxn(msg, db) as trans: db.commit_person(person, trans)"
  - "Import path: from gramps.gen.db import DbTxn (NOT gramps.db — that module does not exist)"

duration: ~1 session
started: 2026-04-11T00:00:00Z
completed: 2026-04-11T00:00:00Z
---

# Phase 5 Plan 03: Bulk Apply via DbTxn Summary

**Apply Selected button writes all checked prefix corrections to GRAMPS in a single undoable transaction — completing the detect → preview → apply workflow for Phase 5.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | ~1 session |
| Tasks | 1 auto + 1 human-verify |
| Files modified | 1 |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Apply writes prefix corrections to DB | Pass | Given name / surname stripped; prefix field set; verified in People view |
| AC-2: Single undoable transaction | Pass | One DbTxn wraps all commits; Edit > Undo reverses all in one step |
| AC-3: Status bar reflects outcome | Pass | "N correction(s) applied — use Edit › Undo to reverse" |
| AC-4: Empty selection handled gracefully | Pass | `if not findings: set_status("No rows selected.")` guard |
| AC-5: Apply button disabled during scan | Pass | `_on_scan` disables; `_check_done` re-enables |

## Accomplishments

- `_on_apply()` handler: reads `get_selected_findings()`, opens `DbTxn("Fix name prefixes", db)`, mutates Name/Surname objects in-memory, calls `db.commit_person()` for each — all in one transaction
- Apply Selected button added to PrefixesTab toolbar with scan-state sensitivity management
- Human verification passed: corrections visible in GRAMPS, undo works in one step
- Phase 5 end-to-end workflow complete: Scan → Preview → Select → Apply → Undo

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `grampsclean/tab_prefixes.py` | Modified | DbTxn import, Apply button, _on_apply handler, scan sensitivity |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| One DbTxn for all rows | Simpler undo — one history entry instead of N | User sees "Undo" once to reverse all changes |
| No auto-clear after apply | User may want to inspect what changed; re-scan is deliberate | No state management complexity |
| Main-thread apply | Button click IS main thread; no worker needed for write | Safe SQLite access, simple code |

## Deviations from Plan

### Auto-fixed Issues

**1. Wrong DbTxn import path**
- **Found during:** Task 1 / human-verify (tab went blank in GRAMPS)
- **Issue:** `from gramps.db import DbTxn` — module `gramps.db` does not exist; caused `tab_prefixes.py` to fail at import, leaving the tab completely empty
- **Fix:** Changed to `from gramps.gen.db import DbTxn` (confirmed from GRAMPS plugin source: `importcsv.py`, `todo.py`)
- **Files:** `grampsclean/tab_prefixes.py` line 13
- **Verification:** GRAMPS restarted, tab loaded, scan/apply buttons visible, corrections worked

**Also fixed:** Files were not being synced to the GRAMPS plugins folder (`~/Library/Application Support/gramps/gramps60/plugins/grampsclean/`). Added this to workflow going forward.

## Issues Encountered

| Issue | Resolution |
|-------|------------|
| `from gramps.db import DbTxn` caused silent module crash | Fixed to `from gramps.gen.db import DbTxn` |
| Files not synced to GRAMPS plugins folder after edits | Manual `cp -r` sync run; must be done after every edit |

## Next Phase Readiness

**Ready:**
- Phase 5 fully complete: detect → preview → apply → undo all working
- `tab_prefixes.py` is a complete, stable module
- Plugin v0.4.0 tagged and pushed

**Concerns:**
- Sync step (`cp -r grampsclean/* ...`) is manual — Phase 6 work must remember to sync after every edit
- GRAMPS plugins folder path is documented in `CLAUDE.md` at project root

**Blockers:**
- None

---
*Phase: 05-name-prefix-corrector, Plan: 03*
*Completed: 2026-04-11*
