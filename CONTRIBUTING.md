# Contributing to GrampsClean

## Development Setup

### Prerequisites

- GRAMPS 5.x installed
- Python 3.x (bundled with GRAMPS)
- Text editor or IDE (VS Code recommended)

### Local Development

1. Clone or navigate to the plugin directory:
   ```bash
   cd ~/GRAMPS\ plugin/grampsclean
   ```

2. After modifying any `.py` file, sync changes to GRAMPS plugins folder:
   ```bash
   cp -r ./* ~/Library/Application\ Support/gramps/gramps60/plugins/grampsclean/
   ```
   (Adjust path for Linux/Windows as needed)

3. Restart GRAMPS to load changes.

> **Important:** Use `cp` not symlinks — GRAMPS's `os.walk` does not follow symlinks.

### Testing

#### Manual Testing
1. Open GRAMPS with a test database (preferably with known data quality issues)
2. Open **Tools → Utilities → GrampsClean**
3. Test each tab:
   - **Islands** — Verify isolated groups detected correctly
   - **Missing Data** — Verify incomplete records found
   - **Impossibilities** — Verify rule violations flagged (adjust severity to test threshold behavior)
   - **Prefixes** — Test preview and apply workflow

#### UI Testing Checklist
- [ ] Tables sort by all columns
- [ ] Filter textbox works
- [ ] Double-clicking result navigates to person in GRAMPS
- [ ] Export CSV button saves file
- [ ] Preferences dialog opens and saves
- [ ] Scan button shows progress
- [ ] No UI freeze during long scans

## Code Style

- Follow PEP 8 conventions
- Use meaningful variable names (`person`, `family`, `birth_event` not `p`, `f`, `be`)
- Keep functions focused and <50 lines where possible
- Comment non-obvious logic (e.g., why a rule threshold is set)
- Use type hints where helpful (Python 3.6+)

## Adding a New Analysis Tool

1. Create `tab_mytool.py` with class `MyToolTab`:
   ```python
   from .widgets import BaseTab
   
   class MyToolTab(BaseTab):
       def __init__(self, gobj):
           super().__init__(gobj, "My Tool", ["Column 1", "Column 2"])
       
       def run_analysis(self):
           results = []
           # Your analysis logic here
           return results
   ```

2. Import and register in `tool.py`:
   ```python
   from .tab_mytool import MyToolTab
   # In GrampsCleanTool.__init__:
   self.tabs.append(MyToolTab(self.gobj))
   ```

3. Update `README.md` and `ARCHITECTURE.md` with feature description

## Database Access

Use helpers from `db.py`:
```python
from .db import *

# Get a person by handle
person = get_person_from_handle(db, handle)

# Iterate all people
for handle in db.get_person_handles():
    person = db.get_person_from_handle(handle)
```

Avoid direct db queries where possible — use `db.py` utilities for consistency.

## Working with Events

Most GRAMPS objects have event references. Use `db.py` helpers:
```python
from .db import get_event_from_ref

birth_event = get_event_from_ref(db, person.get_birth_ref())
if birth_event:
    date = birth_event.get_date_object()
```

## UI Components

Reuse widgets from `widgets.py`:
- `BaseTab` — Provides table, scan/export buttons, status label
- `SpinBox` — Preference spinner
- `ListView` — Multi-select list

## Performance Tips

- **Batch queries** — Don't call `get_person_from_handle()` in a loop; batch if possible
- **Generator patterns** — Use `yield` for large result sets
- **Threading** — Long scans should use `worker.py` to spawn background thread
- **Memory** — Keep results lean; don't store entire person objects if only one field is needed

## Releasing a New Version

1. Update version in `grampsclean.gpr.py`:
   ```python
   version="X.Y.Z"
   ```

2. Update `CHANGELOG.md` (if present) with release notes

3. Commit version bump:
   ```bash
   git add grampsclean.gpr.py
   git commit -m "version: bump to X.Y.Z"
   ```

4. Create annotated git tag:
   ```bash
   git tag -a vX.Y.Z -m "Release X.Y.Z"
   ```

5. Push with tags:
   ```bash
   git push origin main --tags
   ```

6. Package release:
   ```bash
   bash package.sh
   ```
   This creates `grampsclean-X.Y.Z.zip` for distribution.

## Troubleshooting

**Plugin not visible in GRAMPS after sync:**
- Verify sync command ran without errors
- Check GRAMPS plugins folder exists and has correct permissions
- Restart GRAMPS (not just reload)
- Check GRAMPS logs for import errors

**UI freezes during scan:**
- Add `worker.py` threading to analysis
- Avoid blocking I/O in main thread
- Use `threading.Thread` with callback queue

**Database access errors:**
- Verify GRAMPS db handle is valid (not None)
- Ensure person/family handles exist before querying
- Handle exceptions gracefully; don't crash on bad data

## Questions?

Check:
- `ARCHITECTURE.md` for code structure
- Existing tab implementations for patterns
- GRAMPS plugin dev docs at gramps.readthedocs.io
