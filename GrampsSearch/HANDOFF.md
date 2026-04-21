# GrampsSearch — Handoff

Baseline scaffold of a second GRAMPS plugin sitting alongside
`grampsclean/`. Finds missing genealogical data for a person from
Dutch archive APIs and lets the user approve + merge into the local
database.

## Status

- Scaffold complete, loads in GRAMPS 6.0, window opens (smoke-test passed).
- Live-validated: AlleGroningers + Open Archieven normalizers map
  real responses into the `ExternalPerson` dataclass correctly.
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
- **Matching weights** (`matcher.py`):
  `0.5·name + 0.2·birth_year + 0.2·death_year + 0.1·place`,
  threshold `0.55`. Year proximity: full score within ±3yr, linear
  decay to 0 at ±6yr.
- **Merge** (`db.GrampsDb.merge_fields`): single `DbTxn`; creates
  or updates birth/death events, ensures Place (dedup by name),
  writes a Source + Citation with the candidate detail URL on the
  citation's page field.

## Known issues / limitations

1. **GTK blocks during API search.** Connectors run synchronously in
   the UI thread. Threading + `GLib.idle_add` needed for smooth UX.
2. **Whole-candidate merge only.** No per-field checkboxes; birth
   and death are both written if the candidate has them. Users
   can't cherry-pick.
3. **Name parsing is rough** on Open Archieven: `personname` has
   alias parens sometimes, `rsplit(" ", 1)` produces artifacts.
   AlleGroningers `voornaam` sometimes contains patronymic.
4. **GenealogieOnline disabled.** OAuth2 flow is coded (authorize
   URL, code exchange, bearer header) but needs `client_id` /
   `client_secret` / `redirect_uri` + token persistence. Needs a
   `prefs.py` config dialog wired into `tool._build_connectors`.
5. **No year-narrowing in search.** Local birth/death years could
   be passed as `eventYear` to Open Archieven to shrink hit sets.

## Next steps (pick any)

1. **Thread API calls** — background fetch, dispatch results via
   `GLib.idle_add`. Highest UX win.
2. **Per-field merge** — checkboxes per field in the candidate pane.
3. **`prefs.py`** — Gramps config keys for OAuth creds + token,
   modelled on `grampsclean/prefs.py`.
4. **Narrow searches** — pass local year to `search(given, surname, year)`
   from `ui.SearchBox._run_search`.
5. **Unit tests for matcher** — stdlib-only, no GRAMPS needed.
6. **Better name splitter** — dedicated parser handling patronymics,
   parens, Dutch `tussenvoegsel` (`van`, `de`, etc.).

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

Live-probe APIs via `curl` (local Python 3.13 has SSL cert issues,
but curl works; GRAMPS's bundled Python does not have this issue):

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
