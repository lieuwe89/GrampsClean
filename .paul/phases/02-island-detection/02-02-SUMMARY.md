# Summary: Plan 02-02 — Island Scan + ScanWorker Wiring

**Phase:** 02-island-detection
**Plan:** 02-02
**Status:** Complete
**Completed:** 2026-04-10

## What Was Built

| File | Change | Purpose |
|------|--------|---------|
| `grampsclean/tab_islands.py` | Created | `IslandTab` — toolbar, scan_fn, ScanWorker, live result streaming |
| `grampsclean/tool.py` | Updated | Tab 0 now `IslandTab`; remaining 3 tabs still placeholders |
| `grampsclean/graph.py` | Updated | Added `build_from_raw()` classmethod for thread-safe graph building |

## Acceptance Criteria

- [x] AC-1: Scan button triggers island scan
- [x] AC-2: Results show isolated people and small groups with correct columns
- [x] AC-3: Max group size spinner is configurable
- [x] AC-4: Cancel button stops the scan
- [x] AC-5: Completion status shows summary ("N people in M groups (max size: S)")
- [x] AC-6: Both files compile cleanly

## Critical Discovery: SQLite Thread Restriction

**Problem:** `Error during scan: sqlite objects created in thread can only be used in the same thread`

**Root cause:** GRAMPS uses SQLite under the hood. SQLite connections are thread-local — calling `db.iter_people()` or `db.get_person_from_handle()` from a background thread raises an error.

**Fix applied — main thread snapshot pattern:**
1. On the main thread (in `_on_scan`), read ALL needed data into plain Python dicts:
   - `person_handles` — list of handle strings
   - `person_names` — `{handle: "Surname, Given"}`
   - `family_edges` — list of handle lists (one per family)
2. Pass snapshot to worker — worker receives only plain Python data
3. Worker thread does pure computation only: `KinshipGraph.build_from_raw()` + sorting
4. Added `KinshipGraph.build_from_raw(person_handles, family_edges)` classmethod to graph.py

**This pattern is MANDATORY for all future tab implementations (Phases 3–5).**

## Public Pattern for Phases 3–5

```python
def _on_scan(self, btn):
    # 1. Read all needed data on main thread into plain Python structures
    snapshot = { ... }  # dicts/lists only, no GRAMPS objects
    self._snapshot = snapshot

    # 2. Start worker — scan_fn uses only self._snapshot
    self._worker = ScanWorker(self._result_list, self._scan_fn, None)
    self._worker.start()

def _scan_fn(self, _unused):
    snap = self._snapshot  # plain Python only — no DB calls
    ...
```

## Files Modified

- `grampsclean/tab_islands.py` (created)
- `grampsclean/tool.py` (updated)
- `grampsclean/graph.py` (updated — build_from_raw classmethod)

## Next Plan

**02-03:** Results UI — GRAMPS person navigation from result list rows
