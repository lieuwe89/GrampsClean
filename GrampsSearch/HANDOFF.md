# GrampsSearch — Handoff

Baseline scaffold of a second GRAMPS plugin sitting alongside
`grampsclean/`. Finds missing genealogical data for a person from
Dutch archive APIs and lets the user approve + merge into the local
database.

## Status

- Scaffold complete, loads in GRAMPS 6.0, window opens (smoke-test passed).
- Live-validated: AlleGroningers + Open Archieven normalizers map
  real responses into the `ExternalPerson` dataclass correctly.
- **Batch scan mode**: opens, auto-scans every person missing birth
  or death (via `GrampsDb.iter_people_missing_core_events`). Threaded
  worker + `GLib.idle_add`; progress bar + Cancel; master TreeStore
  (person = parent, top-5 candidates = children). Merge writes fields
  into the parent's person. Live-tested end-to-end.
- **SSL fix**: GRAMPS's bundled macOS Python ships without trusted CA
  roots → every `urlopen` failed with `CERTIFICATE_VERIFY_FAILED`.
  `api/base.py::_build_ssl_context` now tries `certifi`, then common
  CA bundle paths (`/etc/ssl/cert.pem` works on stock macOS), then
  unverified as last resort. A single `_SSL_CTX` is passed into every
  `urlopen`.
- **Debug log**: `~/Documents/grampssearch-debug.log`. Truncated at
  scan start; per person logs raw API hit counts + first 3 hits +
  top 3 scored (with weight breakdown). Useful when matches are
  missing.
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
├── ui.py                 SearchBox (Gtk.Box) — side-by-side + Merge btn
└── api/
    ├── __init__.py       Re-exports all connectors
    ├── base.py           BaseConnector, ExternalPerson, ConnectorError
    ├── open_archieven.py OpenArchievenClient (public, keyless)
    ├── genealogie_online.py GenealogieOnlineClient (OAuth2, disabled)
    └── alle_groningers.py AlleGroningersClient (Memorix REST)
```

## Key implementation details

- **GRAMPS loader quirk**: `tool.py` adds its own dir to `sys.path`
  because GRAMPS loads `fname` as a top-level module, not as part of
  a package. That's why top-level `from db import ...` works but
  relative imports (`from .db`) would not. Same pattern as
  `grampsclean/tool.py`.
- **`status=STABLE`** — UNSTABLE plugins are hidden in GRAMPS prefs
  by default. This bit us during first sync.
- **Plugin sync**: edits under `GrampsSearch/` must be copied to
  `~/Library/Application Support/gramps/gramps60/plugins/grampssearch/`
  and GRAMPS must be restarted. `__pycache__` should be cleared on
  every sync (stale .pyc files cause stale imports). No symlinks —
  GRAMPS's `os.walk` doesn't follow them.
- **API key (AlleGroningers)**: `6976bb7e-0c61-4f03-bf5b-df645d5fd086`
  — baked into `api/alle_groningers.py`. Public, per obsidian vault
  note `Knowledge/Groninger Archieven API.md`.
- **Open Archieven endpoint**: `https://api.openarch.nl/1.0/records/search.json`.
  Legacy v1 is dead. Each response doc is one person×event; connector
  dispatches `eventtype` (Dutch: `geboorte`/`overlijden` etc.) to
  birth/death fields.
- **Year-narrowed search**: scan worker derives `year_hint` via
  `ui._year_hint(local)` (birth year, else death year, else None)
  and passes it to every connector's `search(given, surname, year=)`.
  Open Archieven forwards it as `eventYear` (exact match).
  AlleGroningers' Memorix backend accepts the arg to keep the
  signature uniform but doesn't use it yet (q-only). Tight exact
  match may hide valid events outside the hint year — switch to a
  `eventYearFrom`/`To` range if recall drops.
- **Matching weights** (`matcher.py`):
  `0.5·name + 0.2·birth_year + 0.2·death_year + 0.1·place`,
  threshold `0.55`. Year proximity: full score within ±3yr, linear
  decay to 0 at ±6yr.
  **Renormalized over present-locally fields** — we filter to people
  *missing* events, so without renormalization their totals always
  capped below threshold. Only fields the local person actually has
  contribute; remaining weights redistribute.
- **Merge** (`db.GrampsDb.merge_fields`): single `DbTxn`; creates
  or updates birth/death events, ensures Place (dedup by name),
  writes a Source + Citation with the candidate detail URL on the
  citation's page field.

## Known issues / limitations

1. **Whole-candidate merge only.** No per-field checkboxes; birth
   and death are both written if the candidate has them. Users
   can't cherry-pick.
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
   OpenArchieven's `eventYear`. If local has a birth year but we're
   also looking for the death record, the death event may fall
   outside that exact year and get filtered server-side. Switch to
   `eventYearFrom`/`eventYearTo` if recall is too low.
5. **AlleGroningers doesn't use year.** Memorix `q`-only for now;
   the `year=` kwarg is accepted but ignored.
6. **Debug log is always on.** Truncates `~/Documents/grampssearch-debug.log`
   at each scan; fine for now, gate behind a flag if noisy later.
7. **Whole-DB scans cost real time.** ~429 people × 2 connectors =
   hundreds of HTTP calls per open. No caching of API responses
   between scans.

## Next steps (pick any)

1. **Per-field merge** — checkboxes per field in the candidate pane.
2. **`prefs.py`** — Gramps config keys for OAuth creds + token,
   modelled on `grampsclean/prefs.py`. Also good home for debug-log
   toggle and source-selection checkboxes.
3. **Widen year window** — swap exact `eventYear` for
   `eventYearFrom=year-10`/`eventYearTo=year+90` in Open Archieven
   to cover a plausible lifespan. Wire year filter into
   AlleGroningers (Memorix supports Solr-style filters via `fq`).
4. **Unit tests for matcher** — stdlib-only, no GRAMPS needed.
5. **Better name splitter** — dedicated parser handling patronymics,
   parens, Dutch `tussenvoegsel` (`van`, `de`, `de la`, `Alberda van`).
6. **Cache API responses** — dedupe across re-scans / across people
   who share a surname.

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
