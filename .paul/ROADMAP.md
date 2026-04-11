# Roadmap: GrampsClean

## Overview

GrampsClean ships as a single GRAMPS plugin with four integrated data quality tools. v1.0 establishes the plugin foundation and delivers all core tools in a tabbed dialog. Work proceeds from infrastructure → detection algorithms → UI polish → packaging, with each phase building on the last.

## Current Milestone

**v1.0 MVP** (v1.0)
Status: In progress
Phases: 4 of 6 complete

## Phases

| Phase | Name | Plans | Status | Completed |
|-------|------|-------|--------|-----------|
| 1 | Plugin Foundation | 3 | Complete | 2026-04-09 |
| 2 | Island Detection | 3 | Complete | 2026-04-10 |
| 3 | Missing Data Finder | 2 | Complete | 2026-04-11 |
| 4 | Impossibilities Checker | 3 | Complete | 2026-04-11 |
| 5 | Name Prefix Corrector | 3 | Not started | - |
| 6 | Polish & Distribution | 2 | Not started | - |

## Phase Details

### Phase 1: Plugin Foundation

**Goal:** A working GRAMPS plugin skeleton — registered, loadable, and launching a tabbed main window — with a database access layer used by all subsequent phases.
**Depends on:** Nothing (first phase)
**Research:** Likely (GRAMPS plugin API, GTK3 patterns, threading model)
**Research topics:** Plugin registration (.gpr.py), Tool vs Gramplet architecture, accessing DbReadBase, background thread pattern to avoid UI freeze

**Scope:**
- Plugin manifest and registration
- Tabbed GTK dialog (one tab placeholder per tool)
- Database reader abstraction (wraps GRAMPS DbReadBase)
- Background worker pattern (keeps UI responsive during scans)
- Basic result list widget (reused by all tools)

**Plans:**
- [ ] 01-01: Plugin manifest, registration, and hello-world launch
- [ ] 01-02: Tabbed main window with result list widget
- [ ] 01-03: Database access layer and background worker pattern

### Phase 2: Island Detection

**Goal:** Users can scan the database and see a list of isolated individuals and small disconnected clusters (≤10 people), with direct navigation to each person.
**Depends on:** Phase 1 (database layer, result list widget)
**Research:** Likely (graph traversal strategy for GRAMPS family links, NetworkX availability)
**Research topics:** Whether NetworkX is bundled with GRAMPS or must be vendored; connected-components algorithm on family graph

**Scope:**
- Build kinship graph from GRAMPS family/person links
- Connected-components analysis
- Filter: single isolated people + small groups (≤ configurable max, default 10)
- Results listed by group, clickable to navigate to person in GRAMPS

**Plans:**
- [ ] 02-01: Kinship graph builder from GRAMPS database
- [ ] 02-02: Connected-components engine with island/small-group filter
- [ ] 02-03: Results UI with group display and GRAMPS navigation

### Phase 3: Missing Data Finder

**Goal:** Users can search for people missing birth dates, death dates, or other configurable data fields, and see paginated filterable results.
**Depends on:** Phase 1 (database layer, result list widget)
**Research:** Unlikely (straightforward record inspection)

**Scope:**
- Scan all persons for missing: birth date, death date, birth place, death place (configurable which fields to check)
- Filterable results (e.g. show only living vs deceased)
- Summary counts per field type
- Navigate to person from result

**Plans:**
- [ ] 03-01: Missing-field scanner with configurable field selection
- [ ] 03-02: Results UI with filters, counts, and navigation

### Phase 4: Impossibilities Checker

**Goal:** Users can run a full audit of genealogical impossibilities across the database, see flagged records grouped by rule, with configurable thresholds and severity levels.
**Depends on:** Phase 1 (database layer, result list widget)
**Research:** Unlikely (rule logic is deterministic; date parsing uses GRAMPS built-ins)

**Scope:**
- Implement all 15 rules from PROJECT.md impossibilities checklist
- Configurable thresholds (parent age limits, post-death birth window)
- Severity levels: Error (definite impossibility) vs Warning (implausible but possible)
- Results grouped by rule type, navigate to person/family

**Plans:**
- [ ] 04-01: Date/relationship rule engine (all 15 rules)
- [ ] 04-02: Threshold configuration UI and severity classification
- [ ] 04-03: Results UI grouped by rule with severity indicators

### Phase 5: Name Prefix Corrector

**Goal:** Users can detect and bulk-correct surname prefixes (van, de, van der, den, ter, le, etc.) that are positioned in the wrong field, with a preview-before-commit workflow and undo support.
**Depends on:** Phase 1 (database layer)
**Research:** Unlikely (string matching + GRAMPS name field API)

**Scope:**
- Configurable prefix list (Dutch, French, German, etc.)
- Detect: prefix embedded in Given Name field instead of Surname Prefix field
- Detect: prefix in Surname field instead of Surname Prefix field
- Preview table: current → proposed correction
- Bulk apply with GRAMPS transaction (supports undo via GRAMPS history)

**Plans:**
- [ ] 05-01: Prefix detection engine with configurable prefix dictionary
- [ ] 05-02: Preview table UI (current vs proposed, select/deselect rows)
- [ ] 05-03: Bulk apply via GRAMPS database transaction with undo

### Phase 6: Polish & Distribution

**Goal:** Plugin is packaged for distribution, has a preferences dialog, can export results to CSV, and has a README for GRAMPS addon repository submission.
**Depends on:** Phases 2–5 (all tools complete)
**Research:** Unlikely (GRAMPS addon packaging is well-documented)

**Scope:**
- Preferences dialog (default thresholds, prefix list, max island size)
- Export results to CSV for any active tool tab
- Plugin packaged as standard GRAMPS `.zip` addon
- README and GRAMPS addon metadata

**Plans:**
- [ ] 06-01: Preferences dialog and CSV export
- [ ] 06-02: Addon packaging and distribution metadata

---
*Roadmap created: 2026-04-08*
*Last updated: 2026-04-11*
