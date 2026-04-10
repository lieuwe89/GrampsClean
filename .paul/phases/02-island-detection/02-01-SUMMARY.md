# Summary: Plan 02-01 — KinshipGraph (Union-Find)

**Phase:** 02-island-detection
**Plan:** 02-01
**Status:** Complete
**Completed:** 2026-04-09

## What Was Built

| File | Change | Purpose |
|------|--------|---------|
| `grampsclean/graph.py` | Created | `KinshipGraph` — union-find connected-components over GRAMPS family links |

## Acceptance Criteria

- [x] AC-1: Graph builds from database (all people registered, families union-ed)
- [x] AC-2: get_components() returns list of sets covering all handles
- [x] AC-3: get_islands(max_size) filters and sorts small components
- [x] AC-4: No NetworkX dependency — pure stdlib
- [x] AC-5: Compiles with python3 -m py_compile

## Key Decisions

| Item | Detail |
|------|--------|
| Union-find over NetworkX | Resolves the Phase 2 NetworkX blocker entirely — stdlib only, O(α(n)) per operation, no bundling needed |
| Path compression + union by rank | Both optimisations included for near-constant time performance on large databases |
| build() lazy | build() called automatically by get_components() if not yet called — callers don't have to remember to call it |

## Public API for Plan 02-02

- `KinshipGraph(db_wrap)` — instantiate
- `build()` — traverse database (called automatically if skipped)
- `get_components()` → `list[set[str]]` — all connected groups
- `get_islands(max_size=10)` → `list[set[str]]` — small/isolated groups, sorted by size
- `component_count()` → int
- `island_count(max_size=10)` → int

## Files Modified

- `grampsclean/graph.py` (created)

## Next Plan

**02-02:** Connected-components engine with island/small-group filter (scan_fn + ScanWorker wiring)
