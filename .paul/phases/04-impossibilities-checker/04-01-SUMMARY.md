---
phase: 04-impossibilities-checker
plan: 01
subsystem: detection
tags: [gramps, gtk3, threading, rule-engine, genealogy, impossibilities]

requires:
  - phase: 01-plugin-foundation
    provides: GrampsDb wrapper, ResultList widget, ScanWorker, main-thread snapshot pattern
  - phase: 03-missing-data
    provides: _navigate_person pattern, _on_scan / _check_done / _scan_fn structure

provides:
  - _build_snapshot() — main-thread data collector for persons + families (dates as tuples, event counts, family links)
  - run_rules() — all 15 impossibility rules as pure-Python checks (R01–R15)
  - ImpossibilitiesTab — working scan tab wired into GrampsClean Tab 2
  - DEFAULT_THRESHOLDS dict — configurable limits for age/postdeath rules (hardcoded for now)

affects: [04-02-threshold-config, 04-03-results-ui, 05-name-prefix]

tech-stack:
  added: []
  patterns:
    - two-phase snapshot: persons dict (birth/death/burial as tuples, event counts, life event dates, family links) + families dict (parents, children, marriage/divorce) — all plain Python, no GRAMPS objects
    - rule engine as pure module-level function run_rules(snapshot, thresholds) → list of finding dicts
    - _before(a, b) helper: adaptive precision comparison of (year, month, day) tuples
    - _overlaps(f1, f2): conservative marriage-overlap check — assumes overlap unless divorce provably before next marriage

key-files:
  created: [grampsclean/tab_impossibilities.py]
  modified: [grampsclean/tool.py]

key-decisions:
  - "Snapshot includes burial_date separately from death_date — enables R02 (burial before death) without extra DB call"
  - "life_event_dates list captures all non-birth/death/burial events for R05/R06 — plain (year,month,day) tuples"
  - "_before() uses adaptive precision: year-only when months are 0, year+month when days are 0, full tuple otherwise — conservative, avoids false positives from imprecise genealogical dates"
  - "R08 threshold: child_birth_year > father_death_year + 1 (conservative — avoids flagging year-boundary ambiguity)"
  - "R14 (overlapping marriages): only flags when both families have marriage dates; assumes overlap unless divorce is provably before second marriage"
  - "R15 (circular ancestry): iterative DFS with visited set + depth limit of 50 — safe on genuinely circular data"

patterns-established:
  - "Finding dict shape: {person_handle, family_handle, rule_id, rule_name, severity, detail} — reusable for 04-02/04-03 UI layers"
  - "DEFAULT_THRESHOLDS dict at module level — 04-02 will override by passing custom dict to run_rules()"
  - "Row tuple has person_handle as tag (5th element) — double-click navigates to person even for family-level rules"

duration: ~1 session
started: 2026-04-11T00:00:00Z
completed: 2026-04-11T00:00:00Z
---

# Phase 4 Plan 01: Impossibility Rule Engine Summary

**All 15 impossibility rules implemented as a pure-Python rule engine with main-thread snapshot builder and functional ImpossibilitiesTab wired into GrampsClean Tab 2.**

## Performance

| Metric | Value |
|--------|-------|
| Duration | 1 session |
| Tasks | 3 completed |
| Files modified | 2 (1 created, 1 modified) |
| Verify checks | All passed |

## Acceptance Criteria Results

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Snapshot captures all required data | Pass | Persons: birth/death/burial tuples, event counts, life event dates, family links. Families: parents, children, marriage/divorce dates. All plain Python. |
| AC-2: All 15 rules detect their violations | Pass | R01–R15 implemented. Missing dates produce no finding. Severity assignments correct (Error/Warning). |
| AC-3: ImpossibilitiesTab scans and displays findings | Pass | Tab wired as Tab 2. Scan button → main-thread snapshot → ScanWorker → ResultList. Status bar shows "N issues found (E errors, W warnings)". Double-click navigates. |

## Accomplishments

- `_build_snapshot()` captures all genealogically relevant data in a single main-thread pass: birth/death/burial dates (as precision-aware tuples), event counts (for duplicate detection), all life event dates (for pre-birth/post-death checks), and full family link maps
- `run_rules()` implements all 15 rules in ~160 lines of pure Python — no GRAMPS imports, safe for background thread
- `ImpossibilitiesTab` follows the exact MissingTab/IslandTab pattern: toolbar → ScanWorker → ResultList → status bar → double-click navigation
- Placeholder in `tool.py` replaced with live tab

## Files Created/Modified

| File | Change | Purpose |
|------|--------|---------|
| `grampsclean/tab_impossibilities.py` | Created (583 lines) | Snapshot builder, all 15 rules, ImpossibilitiesTab widget |
| `grampsclean/tool.py` | Modified | Added ImpossibilitiesTab import, wired Tab 2, reduced PLACEHOLDER_TABS to Phase 5 only |

## Decisions Made

| Decision | Rationale | Impact |
|----------|-----------|--------|
| `_before(a, b)` adaptive precision | Genealogical dates often year-only; comparing (1850,0,0) < (1850,3,0) as year-only avoids false positives | All date comparisons consistent across rules |
| R08 threshold `child_year > father_death_year + 1` | Year-level precision can't reliably detect 9-month window at year boundaries; +1 year is conservative | Reduces false positives for fathers dying late in a year |
| Snapshot includes `life_event_dates` list | R05/R06 need all non-birth/death/burial events; collecting on main thread avoids per-event DB calls in worker | Worker has all data needed without any DB access |
| Finding `person_handle` for family-level rules | For R12/R13, uses spouse's handle; for R07–R11, uses child's handle — navigates to the person with the issue | Consistent double-click navigation behavior |

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None.

## Next Phase Readiness

**Ready for Phase 4 Plan 02 (Threshold Configuration UI):**
- `DEFAULT_THRESHOLDS` dict at module level is the single source of truth — 04-02 adds a config UI and passes a user-specified dict to `run_rules()`
- `run_rules(snapshot, thresholds)` signature already accepts any thresholds dict — no changes to rule engine needed for 04-02
- Finding dict shape established — 04-03 can group/filter by `rule_id` or `severity`

**Ready for Phase 4 Plan 03 (Results UI — grouped by rule):**
- `run_rules()` sorts findings by `rule_id` then person name — consistent ordering ready for grouped display
- `severity` field is a plain string ("Error"/"Warning") — easy to filter or color-code in 04-03

**Concerns:**
- R14 (overlapping marriages) and R15 (circular ancestry) are heuristic — may produce false positives on legitimate data (e.g., historical polygamy, remarriage without recorded divorce). 04-02 could add a checkbox to enable/disable individual rules.
- R15 DFS depth limit of 50 is generous but still hard-limits deep trees. Genuine cycles in large databases will be caught; very deep clean trees won't be traversed past 50 levels (benign, just won't flag false positives deeper than 50).

**Blockers:** None

---
*Phase: 04-impossibilities-checker, Plan: 01*
*Completed: 2026-04-11*
