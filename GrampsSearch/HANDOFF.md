# GrampsSearch — Handoff

Second GRAMPS plugin sitting alongside `grampsclean/`. Finds missing
genealogical data for a person from Dutch archive APIs and lets the
user approve + merge into the local database.

## Status

- Scaffold complete, loads in GRAMPS 6.0, window opens.
- Live-validated: AlleGroningers + Open Archieven normalizers map
  real responses into the `ExternalPerson` dataclass correctly.
- **Batch scan mode**: opens, auto-scans every person missing birth
  or death (via `GrampsDb.iter_people_missing_core_events`). Threaded
  worker + `GLib.idle_add`; progress bar + Cancel; master TreeStore
  (person = parent, top-5 candidates = children). Live-tested.
- **Per-field merge** (NEW): selecting a candidate row populates a
  detail grid with a checkbox per field (birth date, birth place,
  death date, death place). Defaults: tick when candidate has data
  AND local is empty; user can override. Merge writes only ticked
  fields; "Nothing ticked" status if all off. Source citation still
  written if any field merged. Live-tested.
- **SSL fix**: GRAMPS's bundled macOS Python ships without trusted CA
  roots → every `urlopen` failed with `CERTIFICATE_VERIFY_FAILED`.
  `api/base.py::_build_ssl_context` tries `certifi`, then common
  CA bundle paths (`/etc/ssl/cert.pem` works on stock macOS), then
  unverified as last resort. Single `_SSL_CTX` passed to every
  `urlopen`.
- **Debug log**: `~/Documents/grampssearch-debug.log`. Truncated at
  scan start; per person logs raw API hit counts + first 3 hits +
  top 3 scored (with weight breakdown).
- GenealogieOnline OAuth2 stub exists but is **disabled** (no creds
  wired up). See "Next steps" below.

## Layout

```
GrampsSearch/
├── grampssearch.gpr.py   Plugin registration (status=STABLE)
├── __init__.py           Package docstring
├── tool.py               Tool entry — builds ManagedWindow + SearchBox
├── db.py                 GrampsDb — read helpers + merge_fields() txn writer
├── matcher.py            filter_and_rank() — difflib + year proximity
├── ui.py                 SearchBox (Gtk.Box) — TreeStore + per-field grid + Merge btn
└── api/
    ├── __init__.py       Re-exports all connectors
    ├── base.py           BaseConnector, ExternalPerson, ConnectorError, _SSL_CTX
    ├── open_archieven.py OpenArchievenClient (public, keyless)
    ├── genealogie_online.py GenealogieOnlineClient (OAuth2, disabled)
    └── alle_groningers.py AlleGroningersClient (Memorix REST)
```

## Key implementation details

- **GRAMPS loader quirk**: `tool.py` adds its own dir to `sys.path`
  because GRAMPS loads `fname` as a top-level module, not as part of
  a package. Top-level `from db import ...` works; relative imports
  (`from .db`) would not. Same pattern as `grampsclean/tool.py`.
- **`status=STABLE`** — UNSTABLE plugins are hidden in GRAMPS prefs
  by default.
- **Plugin sync**: edits under `GrampsSearch/` must be copied to
  `~/Library/Application Support/gramps/gramps60/plugins/grampssearch/`
  and GRAMPS must be restarted. Clear `__pycache__` on every sync
  (stale .pyc files cause stale imports). No symlinks — GRAMPS's
  `os.walk` doesn't follow them.
- **API key (AlleGroningers)**: `6976bb7e-0c61-4f03-bf5b-df645d5fd086`
  — baked into `api/alle_groningers.py`. Public per obsidian vault
  note `Knowledge/Groninger Archieven API.md`.
- **Open Archieven endpoint**: `https://api.openarch.nl/1.0/records/search.json`.
  Each response doc is one person×event; connector dispatches
  `eventtype` (Dutch: `geboorte`/`overlijden` etc.) to birth/death
  fields.
- **Year-narrowed search**: scan worker derives `year_hint` via
  `ui._year_hint(local)` (birth year, else death year, else None)
  and passes to every connector's `search(given, surname, year=)`.
  Open Archieven forwards as `eventYear` (exact match).
  AlleGroningers accepts the arg but doesn't use it yet.
- **Matching weights** (`matcher.py`):
  `0.5·name + 0.2·birth_year + 0.2·death_year + 0.1·place`,
  threshold `0.55`. Year proximity: full score within ±3yr, linear
  decay to 0 at ±6yr. Renormalized over present-locally fields so
  people missing events can still cross threshold.
- **Per-field merge** (`ui.SearchBox._rebuild_detail` + `_on_merge`):
  selection callback re-runs `db.person_summary(person)` to get
  fresh local snapshot (cheap, main-thread). Builds a Gtk.Grid:
  `[checkbox] [field name] [local value] [candidate value]`.
  `_on_merge` reads `self._field_checks[key].get_active()` and
  builds the `selected` dict that `db.merge_fields` accepts. The
  existing `_apply_event_data` in `db.py` already handles partial
  data (only sets date if `date_text` is truthy, only sets place
  if `place` is truthy), so per-field works without db.py changes.
- **Merge** (`db.GrampsDb.merge_fields`): single `DbTxn`; creates
  or updates birth/death events, ensures Place (dedup by name),
  writes a Source + Citation with the candidate detail URL on the
  citation's page field.

## Known issues / limitations

1. **No caching of API responses.** ~429 people × 2 connectors
   per scan = hundreds of HTTP calls every time the window opens.
   Re-scans repeat the same surname queries. **Next step #1.**
2. **Name parsing is rough** on Open Archieven: `personname` has
   alias parens sometimes, `rsplit(" ", 1)` produces artifacts.
   AlleGroningers `voornaam` sometimes contains patronymic. Local
   `Alberda van Bloemersma` → split surname/tussenvoegsel not
   handled; matcher compares as one string.
3. **GenealogieOnline disabled.** OAuth2 flow is coded (authorize
   URL, code exchange, bearer header) but needs `client_id` /
   `client_secret` / `redirect_uri` + token persistence. Needs a
   `prefs.py` config dialog wired into `tool._build_connectors`.
4. **Year-hint is exact-match only.** We pass a single year to
   OpenArchieven's `eventYear`. If local has a birth year but
   we're also looking for the death record, the death event may
   fall outside that exact year and get filtered server-side.
   Switch to `eventYearFrom`/`eventYearTo` if recall is too low.
5. **AlleGroningers doesn't use year.** Memorix `q`-only for now;
   the `year=` kwarg is accepted but ignored.
6. **Debug log is always on.** Truncates `~/Documents/grampssearch-debug.log`
   at each scan; fine for now, gate behind a flag if noisy later.

## Next steps

### 1. Cache API responses (CHOSEN — next session)

Goal: cut redundant HTTP across re-scans and across people who
share a surname.

Design notes:
- Cache key: tuple `(source_name, given_normalized, surname_normalized, year_hint)`.
  Normalize via `.strip().lower()`. Year may be `None`.
- Cache value: the raw `list[ExternalPerson]` returned by
  `connector.search(...)` — stored as JSON via `dataclasses.asdict`.
- Storage: SQLite file under
  `~/Library/Application Support/gramps/gramps60/grampssearch_cache.db`
  (path chosen so users can delete it). Single table:
  `cache(key TEXT PRIMARY KEY, source TEXT, fetched_at INTEGER, payload TEXT)`.
- TTL: 30 days default. Configurable later via `prefs.py`.
- Wrap each connector's `search()` in a `CachedConnector` decorator
  in `api/cache.py` so connectors stay pure. `tool._build_connectors`
  wraps each connector after construction.
- Add a "Clear cache" button to the toolbar in `ui.SearchBox`,
  or at minimum log cache hits/misses to debug log.
- Threading: SQLite writes happen on the worker thread inside
  `cached_search()`. Use `sqlite3.connect(..., check_same_thread=False)`
  with a `threading.Lock` per connection, OR open a fresh connection
  per call (simpler, slower).

Files to add/touch:
- `api/cache.py` (NEW): `CachedConnector` wrapper + sqlite open helper.
- `tool.py::_build_connectors`: wrap each connector with `CachedConnector`.
- `ui.py`: add "Clear cache" button (optional first pass — can ship
  without UI control and just delete the file manually).
- `HANDOFF.md`: update once shipped.

Acceptance:
- Open the window twice in a row. Second open's debug log shows
  `CACHE HIT` for every person the first scan covered, and total
  scan time should drop dramatically (no HTTP).
- Inspect SQLite file with `sqlite3` cli: rows for both connectors,
  `fetched_at` epoch, JSON payload parses.

### 2. `prefs.py`

Gramps config keys for OAuth creds + token, modelled on
`grampsclean/prefs.py`. Also good home for cache TTL, debug-log
toggle, and source-selection checkboxes.

### 3. Widen year window

Swap exact `eventYear` for `eventYearFrom=year-10`/`eventYearTo=year+90`
in Open Archieven to cover a plausible lifespan. Wire year filter
into AlleGroningers (Memorix supports Solr-style filters via `fq`).

### 4. Unit tests for matcher

Stdlib-only, no GRAMPS needed.

### 5. Better name splitter

Dedicated parser handling patronymics, parens, Dutch
`tussenvoegsel` (`van`, `de`, `de la`, `Alberda van`).

## Useful commands

Sync plugin (after any edit under `GrampsSearch/`):

```bash
rm -rf "GrampsSearch/__pycache__" "GrampsSearch/api/__pycache__"
mkdir -p "$HOME/Library/Application Support/gramps/gramps60/plugins/grampssearch"
cp -r "GrampsSearch/"* "$HOME/Library/Application Support/gramps/gramps60/plugins/grampssearch/"
```

Syntax check everything:

```bash
python3 -m py_compile GrampsSearch/*.py GrampsSearch/api/*.py
```

Live-probe APIs via `curl` (both local Python 3.13 and GRAMPS's
bundled macOS Python hit `CERTIFICATE_VERIFY_FAILED` without help —
see `_build_ssl_context` in `api/base.py`):

```bash
curl -s "https://webservices.memorix.nl/genealogy/person?apiKey=6976bb7e-0c61-4f03-bf5b-df645d5fd086&q=Janssen&rows=3" | python3 -m json.tool | head -30
curl -s "https://api.openarch.nl/1.0/records/search.json?name=Janssen&number=3&lang=nl" | python3 -m json.tool | head -30
```

## Context for next session

- Project root: `GRAMPS plugin/` (git repo, branch `main`).
- `grampsclean/` is a separate, mature sibling plugin — reference
  for conventions (imports, ManagedWindow, prefs pattern).
- Plugin registration is `grampsclean.gpr.py` / `grampssearch.gpr.py`
  — GRAMPS scans any file matching `*.gpr.py` in plugin dirs.
- After any file edit under `GrampsSearch/`, sync + restart GRAMPS
  to test.
- **Next session task: API response caching.** See "Next steps #1"
  above for design + acceptance criteria.
