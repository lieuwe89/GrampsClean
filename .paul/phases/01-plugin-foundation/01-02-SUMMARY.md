# Summary: Plan 01-02 — Tabbed Window + ResultList Widget

**Phase:** 01-plugin-foundation
**Plan:** 01-02
**Status:** Complete
**Completed:** 2026-04-09

## What Was Built

| File | Change | Purpose |
|------|--------|---------|
| `grampsclean/widgets.py` | Created | Standalone `ResultList(Gtk.Box)` widget — scrolled TreeView + status bar, zero GRAMPS imports |
| `grampsclean/tool.py` | Updated | Replaced placeholder with `Gtk.Notebook`, 4 tabs each hosting a `ResultList` |

## Acceptance Criteria

- [x] AC-1: Window opens with 4 named tabs (Island Detection, Missing Data, Impossibilities, Name Prefixes)
- [x] AC-2: Each tab shows an empty ResultList with 3 columns + "Ready — click Scan to begin"
- [x] AC-3: ResultList is a standalone widget with no GRAMPS imports
- [x] AC-4: Both files compile with `python3 -m py_compile`

## Key Decisions & Discoveries

| Item | Detail |
|------|--------|
| GRAMPS module loading | Plugin `tool.py` is loaded as a **top-level module** (not inside a package) — GRAMPS adds the plugin's parent dir to `sys.path` and calls `__import__("tool")` |
| Relative imports don't work | `from .widgets import ResultList` fails — no package context at load time |
| `from grampsclean.widgets` doesn't work | The plugins folder itself isn't on `sys.path`, only the parent dir |
| Fix | Add `_here = os.path.dirname(__file__)` to `sys.path` in `tool.py`, then use plain `from widgets import ResultList` |
| ResultList API | `append_row(*values)`, `clear()`, `set_status(text)` — used by all 4 tool phases |

## Files Modified

- `grampsclean/widgets.py` (created)
- `grampsclean/tool.py` (updated — sys.path fix + Notebook with 4 tabs)

## Next Plan

**01-03:** Database access layer and background worker pattern
