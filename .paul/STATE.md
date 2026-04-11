# Project State

## Project Reference

See: .paul/PROJECT.md (updated 2026-04-11)

**Core value:** Genealogists with large kinship databases can find and fix data quality problems — missing dates, broken connections, logical impossibilities, and naming errors — without manually inspecting every record.
**Current focus:** v1.0 MVP — Phase 6: Polish & Distribution

## Current Position

Milestone: v1.0 MVP (v1.0)
Phase: 6 of 6 (Polish & Distribution) — Not started
Plan: Not started
Status: Ready to plan
Last activity: 2026-04-11 — Phase 5 complete, transitioned to Phase 6

Progress:
- Milestone: [█████████████████░░░] 83%
- Phase 6: [░░░░░░░░░░] 0%

## Loop Position

Current loop state:
```
PLAN ──▶ APPLY ──▶ UNIFY
  ○        ○        ○     [Ready to plan Phase 6]
```

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: ~1 session
- Total execution time: —

**By Phase:**

| Phase | Plans | Total Time | Avg/Plan |
|-------|-------|------------|----------|
| 01-Plugin Foundation | 3/3 ✓ | - | - |
| 02-Island Detection | 3/3 ✓ | - | - |
| 03-Missing Data Finder | 2/2 ✓ | - | - |
| 04-Impossibilities Checker | 3/3 ✓ | - | - |
| 05-Name Prefix Corrector | 3/3 ✓ | - | - |
| 06-Polish & Distribution | 0/2 | - | - |

## Accumulated Context

### Decisions

| Decision | Phase | Impact |
|----------|-------|--------|
| Tool plugin (not Gramplet) — tabbed full-window dialog | Init | Affects all UI phases |
| Configurable thresholds for impossibility rules | Init | Phase 4 design |
| Tool imported from gramps.gui.plug.tool (not gen.plug) | 01-01 | All future tool phases |
| Window built via set_window() + setup_configs() | 01-01 | All future window phases |
| Plugin must use status=STABLE (UNSTABLE filtered by default) | 01-01 | Distribution |
| Plugins folder requires real copy, not symlink (os.walk no followlinks) | 01-01 | Dev workflow |
| GRAMPS loads tool.py as top-level module — use sys.path insert + plain import for sibling modules | 01-02 | All future multi-file work |
| ResultList API: append_row(), clear(), set_status() — shared by all 4 tool tabs | 01-02 | Phases 2–5 |
| SQLite thread restriction — all DB reads on main thread, worker gets plain Python snapshot | 02-02 | ALL future tab phases (MANDATORY) |
| Main-thread snapshot pattern: person_handles + person_names + family_edges as dicts before worker.start() | 02-02 | Phases 3–5 |
| GRAMPS navigation: set_active(handle, 'Person') + viewmanager.goto_page(get_category("People"), None) | 02-03 | All future tabs with row navigation |
| DEFAULT_PREFIXES sorted longest-first — prevents partial prefix match | 05-01 | Prefix list maintenance |
| DbTxn import: from gramps.gen.db import DbTxn (NOT gramps.db) | 05-03 | ALL future write operations |
| Plugin sync required after every edit: cp -r grampsclean/* to GRAMPS plugins folder | 05-03 | Dev workflow — documented in CLAUDE.md |

### Deferred Issues

*(none)*

### Blockers/Concerns

| Blocker | Impact | Resolution Path |
|---------|--------|-----------------|
*(none — NetworkX blocker resolved: using stdlib union-find instead)*

## Session Continuity

Last session: 2026-04-11
Stopped at: Phase 5 complete — all 3 plans unified, v0.4.0 tagged and pushed
Next action: /paul:plan — Phase 6 (Polish & Distribution: preferences dialog + CSV export)
Resume file: .paul/ROADMAP.md

---
*STATE.md — Updated after every significant action*
