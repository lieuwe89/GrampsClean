# GrampsClean Architecture

## Overview

GrampsClean is a GRAMPS plugin structured as a tabbed tool dialog. Each tab represents an independent analysis module that queries the GRAMPS database and presents filterable results.

## Module Structure

### Core Entry Points

- **`tool.py`** — Main tool class (`GrampsCleanTool`). Creates the tabbed dialog, manages tab lifecycle, handles UI events (scan, export, preferences).
- **`prefs.py`** — Settings management (`GrampsCleanOptions`). Loads/saves user preferences, provides configuration UI.
- **`grampsclean.gpr.py`** — Plugin registration. Declares plugin metadata, version, GRAMPS compatibility.

### Data Access

- **`db.py`** — Database interface. Wraps GRAMPS db handle, provides utility functions for querying people, families, events, and relationships.

### Analysis Modules (Tabs)

Each tab is a standalone analysis module with a UI class that inherits from a base tab widget.

- **`tab_islands.py`** — Island detection. Finds connected components in the kinship graph using BFS/DFS. Configurable max group size.
- **`tab_missing.py`** — Missing data finder. Scans all people for incomplete birth/death dates/places. Filterable by living/deceased.
- **`tab_impossibilities.py`** — Impossibilities checker. Applies 15 validation rules (age constraints, event ordering, duplicate events, etc.). Severity configurable per rule.
- **`tab_prefixes.py`** — Name prefix corrector. Pattern-matches surname prefixes (van, de, van der, etc.) in primary/given names. Shows preview, applies corrections with full undo.

### Utilities

- **`widgets.py`** — Custom UI components. Reusable widgets (result tables, preference spinners, prefix pattern editors).
- **`worker.py`** — Background processing. Spawns worker threads to prevent UI blocking during long scans.
- **`graph.py`** — Kinship graph analysis. Builds adjacency lists, computes connected components, traverses family relationships.

## Data Flow

1. **User opens GrampsClean** → `tool.py` creates dialog, instantiates all tabs.
2. **User clicks Scan** → Tab's `run_analysis()` method starts a worker thread via `worker.py`.
3. **Worker thread executes analysis**:
   - Queries GRAMPS database via `db.py` utilities
   - Runs analysis logic (graph traversal, pattern matching, rule evaluation)
   - Returns results list
4. **Results displayed in table** → User can filter, sort, double-click to navigate to person in GRAMPS.
5. **User clicks Export** → Results serialized to CSV and saved.
6. **User changes preferences** → Settings persisted via `prefs.py`, tab-specific logic respects thresholds on next scan.

## Graph Analysis (Islands & Impossibilities)

### Connected Components (Islands)

Built in `graph.py`:
- Construct adjacency list from family relationships
- Run BFS from largest connected component to identify smaller isolated groups
- Filter groups by configurable max size threshold

### Kinship Queries (Impossibilities)

Traverse parent/child relationships to:
- Calculate age at event (for validation rules)
- Find all children of a person
- Check event ordering (e.g., birth before death, marriage after adulthood)

## UI Architecture

- **Tab base class** — Provides common table, scan/export buttons, status updates
- **Result table** — Sortable, filterable, rows clickable to GRAMPS navigation
- **Worker thread** — Long-running scans don't block UI; progress via callbacks
- **Preferences dialog** — Modal settings UI, persisted to GRAMPS config

## Key Design Decisions

1. **Worker threads** — Scans can be slow (large databases); worker threads prevent UI freeze. Results queued for main thread.
2. **Severity levels** — Impossibilities checker supports configurable severity (Error/Warning) per rule, allowing selective enforcement.
3. **Preview-before-commit** — Name prefix corrector shows all proposed changes before applying any, with full undo.
4. **CSV export** — Results exportable to spreadsheet for analysis outside GRAMPS.
5. **No schema changes** — All tools read-only (except prefix corrector) and reversible.

## Testing

Run unit tests (if present):
```bash
cd grampsclean
python -m pytest
```

Manual testing:
1. Load sample GRAMPS database with known data quality issues
2. Run each tab's scan, verify results
3. Test filter/sort UI
4. Test CSV export
5. For prefix corrector: apply corrections, undo, verify data integrity

## Performance Considerations

- Large databases (100k+ people) may take 10-30s for full island detection or impossibilities scan
- Name prefix search is O(n) per person
- CSV export writes to disk; no performance bottleneck
- Results held in memory during session; cleared on new scan

## Dependencies

- GRAMPS 5.x (provides db, UI widgets, locale)
- Python 3.x standard library (threading, csv, etc.)
- No external pip packages
