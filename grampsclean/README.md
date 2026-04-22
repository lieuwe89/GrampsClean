# GrampsClean

Data quality tools for GRAMPS genealogy databases.

GrampsClean is a GRAMPS plugin that helps genealogists audit and clean large
kinship databases. It provides four integrated tools in a single tabbed dialog,
accessible from the Tools menu.

## Features

- **Island Detection** — Finds isolated individuals and small disconnected groups
  (up to a configurable maximum size) not connected to the main kinship network.
- **Missing Data Finder** — Lists people lacking birth dates, death dates, birth
  places, or death places; filterable by living or deceased status.
- **Impossibilities Checker** — Flags chronological and logical errors across
  relationships and events (15 rules), with configurable thresholds and Error/Warning
  severity levels.
- **Name Prefix Corrector** — Detects surname prefixes (van, de, van der, den, ter,
  le, etc.) placed in the wrong name field and applies bulk corrections via a
  preview-before-commit workflow with full undo support.

## Requirements

- GRAMPS 5.x or later
- Python 3 (bundled with GRAMPS)

## Installation

### Manual

1. Download `grampsclean-<version>.zip` from the releases page.
2. Unzip to your GRAMPS plugins folder:
   - Linux / macOS: `~/.gramps/gramps60/plugins/`
   - Windows: `%APPDATA%\gramps\gramps60\plugins\`
3. Restart GRAMPS.

### Addon Manager

1. In GRAMPS, open **Tools → Plugin Manager**.
2. Click **Install from file**.
3. Select the downloaded `.zip` file.
4. Restart GRAMPS when prompted.

## Usage

Open GrampsClean via **Tools → Utilities → GrampsClean**.

Use the tabs along the top to switch between tools. Click **Scan** to analyse
your database. Click any result row to navigate directly to that person (or
family) in GRAMPS.

## Preferences

Click the **Preferences** button at the bottom of the dialog to configure
default settings: maximum island group size, impossibility checker thresholds
(parent age limits, post-death birth window), and the surname prefix list.

## Export

Each tab includes an **Export CSV** button that saves the current results to a
UTF-8 CSV file for further analysis in a spreadsheet application.

## License

GPL v2 or later (same as GRAMPS).
