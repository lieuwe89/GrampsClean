# GrampsClean Plugin Repository

GrampsClean is a comprehensive data quality toolkit for GRAMPS genealogy databases. This repository contains the plugin source code, documentation, and release artifacts.

## Overview

GrampsClean provides four integrated tools for auditing and cleaning large kinship databases:

- **Island Detection** — Finds isolated individuals and disconnected groups
- **Missing Data Finder** — Identifies incomplete records (missing dates/places)
- **Impossibilities Checker** — Flags chronological and logical errors (15 validation rules)
- **Name Prefix Corrector** — Bulk-fixes surname prefixes in wrong name fields

## Quick Start

See [grampsclean/README.md](grampsclean/README.md) for installation and usage instructions.

## Documentation

- **[Architecture Guide](grampsclean/ARCHITECTURE.md)** — Code structure, module overview, data flow
- **[Contributing Guide](grampsclean/CONTRIBUTING.md)** — Development workflow, testing, releasing
- **[Plugin README](grampsclean/README.md)** — User guide, features, preferences

## Directory Structure

```
GRAMPS plugin/
├── grampsclean/          # Plugin source code
│   ├── __init__.py       # Plugin entry point
│   ├── tool.py           # Main tool dialog
│   ├── prefs.py          # Preferences/settings
│   ├── db.py             # Database access utilities
│   ├── graph.py          # Kinship graph analysis
│   ├── widgets.py        # Custom UI components
│   ├── worker.py         # Background processing
│   ├── tab_islands.py    # Island detection tool
│   ├── tab_missing.py    # Missing data finder
│   ├── tab_impossibilities.py  # Impossibilities checker
│   ├── tab_prefixes.py   # Name prefix corrector
│   ├── grampsclean.gpr.py # Plugin registration
│   ├── README.md         # User guide
│   ├── ARCHITECTURE.md   # Technical documentation
│   └── CONTRIBUTING.md   # Development guide
├── README.md            # This file
├── package.sh           # Release packaging script
└── .gitignore           # Git ignore rules
```

## License

GPL v2 or later (same as GRAMPS).

## Author

Lieuwe Jongsma — lieuwe89@gmail.com
