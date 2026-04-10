# Summary: Plan 02-03 — Results UI with GRAMPS Person Navigation

**Phase:** 02-island-detection
**Plan:** 02-03
**Status:** Complete
**Completed:** 2026-04-10

## What Was Built

| File | Change | Purpose |
|------|--------|---------|
| `grampsclean/widgets.py` | Modified | `ResultList` extended: hidden tag column (N+1th in ListStore), optional `on_activate` callback, `row-activated` signal, auto-padding in `append_row` |
| `grampsclean/tab_islands.py` | Modified | `IslandTab.__init__` takes `uistate`; `_scan_fn` includes person handle as 4th row element; `_navigate_person` switches main GRAMPS window to People view |
| `grampsclean/tool.py` | Modified | Single-line change: passes `self.uistate` to `IslandTab` |

## Acceptance Criteria

| Criterion | Status | Notes |
|-----------|--------|-------|
| AC-1: Row activation triggers GRAMPS navigation | Pass | Double-click navigates main window to person |
| AC-2: ResultList backward compatibility maintained | Pass | Placeholder tabs still call `append_row(N args)` — auto-padded |
| AC-3: Empty-tag rows silently skip navigation | Pass | "No islands found" row yields no handle → no crash, no nav |

## Deviation: Navigation API Required Extra Step

**Plan specified:** `uistate.set_active(handle, 'Person')`

**Actual behavior discovered at checkpoint:** `set_active()` pushes onto the Person navigation history, but only views that are currently active and listening update visually. If the GRAMPS main window is on a non-Person view, the navigation appears to do nothing.

**Fix applied:** After `set_active()`, call `viewmanager.get_category("People")` + `viewmanager.goto_page(cat_num, None)` to switch the main window to the People view first. Wrapped in `try/except` so it degrades gracefully if the view structure changes.

**Impact:** Navigation now works regardless of which GRAMPS view is active. No scope creep — still a single method, same UX.

## Key Pattern for Future Navigation Tabs (Phases 3–5)

```python
def _navigate_person(self, handle):
    if not handle:
        return
    self._uistate.set_active(handle, 'Person')
    try:
        vm = self._uistate.viewmanager
        cat_num = vm.get_category("People")
        if cat_num is not None:
            vm.goto_page(cat_num, None)
    except Exception:
        pass
```

Category names for other object types (if needed in future phases):
- People → `"People"`
- Families → check `viewmanager.views` category names
- Navigate to family/event: use `uistate.set_active(handle, 'Family')` etc.

## Files Modified

- `grampsclean/widgets.py`
- `grampsclean/tab_islands.py`
- `grampsclean/tool.py`

## Phase 2 Complete

All 3 plans shipped:
- **02-01:** Kinship graph builder (union-find, `KinshipGraph`)
- **02-02:** Island scan engine + `IslandTab` UI with ScanWorker
- **02-03:** Row navigation — double-click → GRAMPS People view

**Phase 2 goal achieved:** Users can scan for isolated individuals and small disconnected groups, see results listed by group, and double-click any row to navigate directly to that person in GRAMPS.
