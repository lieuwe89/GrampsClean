# GrampsClean

## What This Is

GrampsClean is a GRAMPS genealogy software plugin that helps researchers audit and clean large kinship network databases. It provides a suite of data quality tools: detecting disconnected individuals and isolated groups, surfacing records with missing key dates, flagging genealogical impossibilities (conflicting or implausible dates/relationships), and bulk-correcting surname prefix placement errors. All results are navigable directly to the relevant people in GRAMPS.

## Core Value

Genealogists with large kinship databases can find and fix data quality problems — missing dates, broken connections, logical impossibilities, and naming errors — without manually inspecting every record.

## Current State

| Attribute | Value |
|-----------|-------|
| Type | Application (GRAMPS Plugin) |
| Version | 0.4.0 |
| Status | v1.0 MVP Complete |
| Last Updated | 2026-04-11 |

## Requirements

### Core Features

- **Island Detection** — Find isolated individuals and small disconnected groups (≤10 people) not connected to the main kinship network
- **Missing Data Finder** — Search for people lacking birth dates, death dates, or other key data fields
- **Genealogical Impossibilities Checker** — Flag logical/chronological errors across relationships and events
- **Name Prefix Corrector** — Bulk-detect and fix surname prefixes (van, de, van der, etc.) placed in the wrong field

### Validated (Shipped)

- ✓ Plugin foundation and GRAMPS integration scaffold — Phase 1
- ✓ Island detection engine (scan + group display + person navigation) — Phase 2
- ✓ Missing data finder (configurable fields, living/deceased filter, per-field counts, navigation) — Phase 3
- ✓ Genealogical impossibilities checker (15 rules, configurable thresholds, grouped results with severity colour-coding, navigation) — Phase 4
- ✓ Name prefix corrector (detect → preview with checkboxes → bulk apply via DbTxn with undo) — Phase 5
- ✓ Preferences dialog (default thresholds, max island size, prefix list) + CSV export on all four tabs — Phase 6
- ✓ Plugin packaged as GRAMPS addon zip with README and complete .gpr.py distribution metadata — Phase 6

### Active (In Progress)

*(none — v1.0 MVP complete)*

### Planned (Next)

*(none — all v1.0 phases shipped)*

### Out of Scope

- Syncing with online genealogy services (Ancestry, FamilySearch) — separate integration concern
- Automatic data correction (except name prefix tool) — user always approves changes
- Support for GRAMPS versions below 5.x

## Target Users

**Primary:** Amateur and professional genealogists maintaining large family tree databases in GRAMPS
- Working with databases of hundreds to tens of thousands of individuals
- Dutch/Flemish heritage likely common (given van/de prefix use case), but plugin is language-agnostic
- Comfortable with GRAMPS UI; not necessarily technical
- Goal: get their database to a high state of completeness and consistency

## Context

**Technical Context:**
GRAMPS is an open-source genealogy application written in Python using GTK3. Plugins are Python packages registered via a `.gpr.py` manifest. The plugin API exposes the full database (people, families, events, places) and the GTK UI. GRAMPS plugins can be Gramplets (sidebar/bottombar panels), Tools (menu-triggered dialogs), or Reports.

## Constraints

### Technical Constraints

- Must use Python 3 (GRAMPS 5.x requirement)
- UI must be GTK3 (via GRAMPS plugin API — no web UI)
- Must not modify database without explicit user confirmation
- Must handle large databases (10,000+ individuals) without freezing the UI — use background threads or generators
- NetworkX may be used for graph analysis; must be available or bundled

### Business Constraints

- Personal project — no strict timeline
- Should follow GRAMPS plugin conventions for potential submission to the GRAMPS addon repository

### Compliance Constraints

- No external network calls — all analysis runs locally on the user's database

## Key Decisions

| Decision | Rationale | Date | Status |
|----------|-----------|------|--------|
| Build as GRAMPS Tool plugin (menu-triggered dialog) rather than Gramplet | Provides a full window with tabs for multiple tools; better suited to audit workflows than a sidebar panel | 2026-04-08 | Active |
| Impossibilities checker configurable thresholds | Parent-age limits and post-death birth windows are culturally/historically variable — user should be able to tune them | 2026-04-08 | Active |
| No NetworkX — use stdlib union-find for island detection | NetworkX not reliably available in GRAMPS environment; pure Python union-find is sufficient and zero-dependency | 2026-04-09 | Active |
| SQLite thread restriction: main-thread snapshot pattern | GRAMPS SQLite connections are thread-local — all DB reads happen on the main thread into plain Python dicts before passing to worker | 2026-04-10 | Active — MANDATORY for Phases 3–5 |
| GRAMPS person navigation: set_active() + viewmanager.goto_page("People") | set_active() alone only works if Person view is already active; goto_page switches the main window view first | 2026-04-10 | Active — apply to all future navigation |
| is_deceased = person.get_death_ref() is not None | EventRef presence check avoids extra DB lookup; no probably_alive() needed for living/deceased filter | 2026-04-11 | Active — Phase 3 pattern, reusable |
| Field presence snapshot: bool flags on main thread, not raw objects | Keeps worker data minimal; bool flags safer to pass across thread boundary than GRAMPS objects | 2026-04-11 | Active — MANDATORY for Phases 4–5 |
| DEFAULT_PREFIXES sorted longest-first | Prevents "van" matching before "van der" — would produce wrong prefix strip | 2026-04-11 | Active — must maintain if user edits list |
| DbTxn import: from gramps.gen.db import DbTxn | gramps.db does not exist; all GRAMPS write plugins use gramps.gen.db | 2026-04-11 | Active — apply to all future write operations |
| Plugin sync required after every file edit | GRAMPS loads from ~/Library/Application Support/gramps/gramps60/plugins/ — source edits must be cp -r to that folder | 2026-04-11 | Active — documented in CLAUDE.md |
| README placed inside grampsclean/ | Travels with the plugin in the distribution zip; users see it after unpacking | 2026-04-11 | Distribution |
| package.sh reads version from gpr.py dynamically | Single source of truth for version; re-run script after version bump | 2026-04-11 | Distribution |

## Success Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| All 4 core tools functional | 4/4 | 4/4 | ✓ Complete |
| Handles 10k-person database without UI freeze | <5s per scan | — | Not started |
| Name prefix correction: no accidental data loss | 0 unintended changes | — | Not started |

## Tech Stack / Tools

| Layer | Technology | Notes |
|-------|------------|-------|
| Language | Python 3 | GRAMPS requirement |
| UI Framework | GTK3 (via GRAMPS plugin API) | Must match GRAMPS host app |
| Graph Analysis | stdlib union-find (pure Python) | Island detection — NetworkX not used (unavailable in GRAMPS env) |
| Plugin Type | Tool (menu-triggered dialog) | Full-window tabbed UI |
| Distribution | GRAMPS addon `.zip` | Standard GRAMPS plugin packaging |

## Genealogical Impossibilities — Full Checklist

The checker will flag the following (configurable thresholds where noted):

| Rule | Description |
|------|-------------|
| Death before birth | Person's death date is earlier than their birth date |
| Burial before death | Burial/cremation date precedes death date |
| Birth before parent born | Child's birth predates a parent's birth |
| Child born after father's death | Birth > 9 months after father's death (configurable) |
| Child born after mother's death | Birth after mother's death date |
| Parent too young at birth of child | Mother < 12 yrs, Father < 13 yrs at child's birth (configurable) |
| Parent implausibly old at birth of child | Mother > 60 yrs, Father > 90 yrs at child's birth (configurable) |
| Marriage before birth of spouse | Marriage date precedes one spouse's birth date |
| Marriage after death of spouse | Marriage date follows a spouse's death date |
| Event date before birth | Any life event (marriage, immigration, etc.) predates birth |
| Event date after death | Any life event occurs after the person's death date |
| Duplicate birth events | Person has more than one birth event |
| Duplicate death events | Person has more than one death event |
| Overlapping marriages | A person has two simultaneous active marriages (absent divorce/death) |
| Child listed in own ancestry | Circular reference in family tree |

## Links

| Resource | URL |
|----------|-----|
| Repository | TBD |
| GRAMPS Plugin API Docs | https://www.gramps-project.org/wiki/index.php/Portal:Developers |

---
*PROJECT.md — Updated when requirements or context change*
*Last updated: 2026-04-11 after Phase 6 — v1.0 MVP complete*
