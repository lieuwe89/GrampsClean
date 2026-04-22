# GrampsClean

Data quality audit toolkit for GRAMPS genealogy databases.

## Overview

GrampsClean provides four integrated tools for auditing and cleaning large kinship databases:

- **Island Detection** — Finds isolated individuals and disconnected groups
- **Missing Data Finder** — Identifies incomplete records (missing dates/places)
- **Impossibilities Checker** — Flags chronological and logical errors (15 validation rules)
- **Name Prefix Corrector** — Bulk-fixes surname prefixes in wrong name fields

## Installation

1. Download `grampsclean-<version>.zip` from the [releases page](https://github.com/lieuwe89/GrampsClean/releases)
2. In GRAMPS, go **Tools → Plugin Manager → Install from file**
3. Select the `.zip` file and restart GRAMPS

## Usage

Open GrampsClean via **Tools → Utilities → GrampsClean**. Use tabs to switch tools, click **Scan** to analyze your database. Click any result to navigate to that person in GRAMPS.

For detailed usage, preferences, and export options, see [the full user guide](#user-guide-and-documentation).

## User Guide and Documentation

- **[Full Plugin Guide](./README-USER.md)** — Installation, usage, preferences, export
- **[Architecture Guide](./ARCHITECTURE.md)** — Code structure, module overview, design decisions
- **[Contributing Guide](./CONTRIBUTING.md)** — Development setup, testing, releasing

## Repository Structure

```
.
├── __init__.py                  # Plugin entry point
├── tool.py                      # Main tool dialog
├── prefs.py                     # Preferences/settings
├── db.py                        # Database utilities
├── graph.py                     # Kinship graph analysis
├── widgets.py                   # Custom UI components
├── worker.py                    # Background processing
├── tab_islands.py               # Island detection
├── tab_missing.py               # Missing data finder
├── tab_impossibilities.py       # Impossibilities checker
├── tab_prefixes.py              # Name prefix corrector
├── grampsclean.gpr.py           # Plugin registration
├── ARCHITECTURE.md              # Technical documentation
├── CONTRIBUTING.md              # Development guide
├── README.md                    # This file
├── README-USER.md               # User guide
├── package.sh                   # Release packaging script
└── .gitignore                   # Git ignore rules
```

## Requirements

- GRAMPS 5.x or later
- Python 3.x (bundled with GRAMPS)

## License

GPL v2 or later (same as GRAMPS).

## Author

Lieuwe Jongsma — lieuwe89@gmail.com
