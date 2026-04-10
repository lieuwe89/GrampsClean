# Summary: Plan 01-01 — Plugin Manifest + Hello-World Launch

**Phase:** 01-plugin-foundation  
**Plan:** 01-01  
**Status:** Complete  
**Completed:** 2026-04-09

## What Was Built

Three files establishing the GrampsClean plugin skeleton:

| File | Purpose |
|------|---------|
| `grampsclean/__init__.py` | Python package marker |
| `grampsclean/grampsclean.gpr.py` | GRAMPS plugin manifest — registers as TOOL_UTILS, STABLE, GRAMPS 6.0 |
| `grampsclean/tool.py` | `GrampsCleanTool` + `GrampsCleanOptions` — opens an 800×600 placeholder window |

## Acceptance Criteria

- [x] AC-1: Plugin registers in GRAMPS Plugin Manager without error
- [x] AC-2: Clicking Tools → GrampsClean opens a titled window
- [x] AC-3: All three files compile with `python3 -m py_compile`

## Key Decisions & Discoveries

| Item | Detail |
|------|--------|
| Import path | `Tool` must come from `gramps.gui.plug.tool`, not `gramps.gen.plug` |
| Window registration | Must use `self.set_window()` + `self.setup_configs()` — not `self.window = Gtk.Dialog()` directly |
| .gpr.py constants | Must explicitly `from gramps.gen.plug._pluginreg import *` — not injected automatically |
| `tool_modes` required | GRAMPS 6.0 requires `tool_modes=[TOOL_MODE_GUI]` in `.gpr.py` |
| `status=STABLE` required | `UNSTABLE` plugins are filtered out by default (`stable_only=True`) |
| Symlinks don't work | GRAMPS uses `os.walk()` without `followlinks=True` — must use real copy |
| Sync command | `cp -r "grampsclean/"* "~/.../gramps60/plugins/grampsclean/"` after every edit |

## Files Modified

- `grampsclean/__init__.py` (created)
- `grampsclean/grampsclean.gpr.py` (created)
- `grampsclean/tool.py` (created)

## Next Plan

**01-02:** Tabbed main window with result list widget
