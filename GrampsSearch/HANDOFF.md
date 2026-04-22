# GrampsSearch — Handoff

Second GRAMPS plugin sitting alongside `grampsclean/`. Finds missing
genealogical data for a person from Dutch archive APIs and lets the
user approve + merge into the local database.

## Status

- **API response cache (NEW)**: `api/cache.py` ships a `CachedConnector`
  wrapper. `tool._build_connectors` wraps every connector. SQLite file
  at `~/Library/Application Support/gramps/gramps60/grampssearch_cache.db`.
  Key = `source|given_norm|surname_norm|year`. Value = JSON list of
  `ExternalPerson.as_dict()`. TTL = 30 days. One fresh sqlite connection
  per call (scan bottleneck is HTTP). `[cache] HIT`/`MISS` lines land
  in `~/Documents/grampssearch-debug.log`. Offline round-trip smoke
  test passed (1 miss + N hits, normalization + raw-dict preservation).
  Not yet live-tested inside GRAMPS.
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
- **Dutch name parser** (NEW): `names.py` + `tests/test_names.py`
  (28 stdlib unit tests, all green). Connectors normalise candidate
  given/surname via `parse_name`; matcher surname compare strips
  leading tussens on both sides (`van der Berg` ↔ `Berg` → 1.0).
  See Next steps #6 below.
- **Clickable source URL** (NEW): the per-candidate detail grid
  renders `cand.detail_url` as a `Gtk.Label` with `<a href>` markup;
  clicking opens the archive detail page in the default browser via
  Gtk's default `activate-link` handler. Tooltip: "Open in browser".

## Layout

```
GrampsSearch/
├── grampssearch.gpr.py   Plugin registration (status=STABLE)
├── __init__.py           Package docstring
├── tool.py               Tool entry — builds ManagedWindow + SearchBox
├── db.py                 GrampsDb — read helpers + merge_fields() txn writer
├── matcher.py            filter_and_rank() — difflib + year proximity
├── ui.py                 SearchBox (Gtk.Box) — TreeStore + per-field grid + Merge btn
├── prefs.py              GRAMPS config keys + PreferencesDialog
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
- **Year-windowed search**: scan worker derives `(year_from, year_to)`
  via `ui._year_window(local)` — plausible lifespan around the known
  date (birth → [y-10, y+100]; death-only → [y-105, y+10]; neither
  → `(None, None)`). Passes both into every connector's
  `search(given, surname, year_from=, year_to=)`. Open Archieven
  forwards as `eventYearFrom` / `eventYearTo` (range, not exact).
  AlleGroningers accepts but ignores pending Solr `fq` wiring;
  GenealogieOnline maps to `birth_year_from` / `birth_year_to`.
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

1. **Name parsing is rough** on Open Archieven: `personname` has
   alias parens sometimes, `rsplit(" ", 1)` produces artifacts.
   AlleGroningers `voornaam` sometimes contains patronymic. Local
   `Alberda van Bloemersma` → split surname/tussenvoegsel not
   handled; matcher compares as one string.
2. **GenealogieOnline disabled.** OAuth2 flow is coded (authorize
   URL, code exchange, bearer header) but needs `client_id` /
   `client_secret` / `redirect_uri` + token persistence. Needs a
   `prefs.py` config dialog wired into `tool._build_connectors`.
3. **AlleGroningers doesn't use year.** Memorix `q`-only for now;
   the `year_from`/`year_to` kwargs are accepted but ignored. Needs
   a live probe to confirm the Solr `fq=datum:[… TO …]` field name
   + format before wiring.
4. **Debug log is always on.** Truncates `~/Documents/grampssearch-debug.log`
   at each scan; fine for now, gate behind a flag if noisy later.

## Next steps

### 1. Cache API responses — SHIPPED

Implemented in `api/cache.py` exactly to the design below. Live-test
inside GRAMPS still pending (open window twice, confirm `[cache] HIT`
for every person on the second open).

- Key: `source|given_norm|surname_norm|year_from|year_to` (normalize
  names via `.strip().lower()`; year bounds may be empty).
- Value: JSON-encoded list of `ExternalPerson.as_dict()` rows.
  Reconstruct with `ExternalPerson(**d)` on hit.
- Storage: `~/Library/Application Support/gramps/gramps60/grampssearch_cache.db`,
  single `cache(key, source, fetched_at, payload)` table. Users can
  delete the file to reset.
- TTL: 30 days (`DEFAULT_TTL_SECONDS`). Stale rows ignored + overwritten.
- `CachedConnector` exposes the wrapped connector's `source_name` so
  UI introspection (`c.source_name`) keeps working.
- Threading: fresh `sqlite3.connect` per call (5s timeout). Scan
  bottleneck is HTTP; avoids shared-connection locking.
- Logging: `[cache] HIT`/`MISS`/`...` lines written to the same
  `~/Documents/grampssearch-debug.log` that `ui._log` uses.
- `clear_cache()` helper exists (removes the file). Not yet wired to
  a UI button — still a "nice to have".

Remaining follow-ups:
- Live-verified inside GRAMPS (two consecutive window opens — DONE).
- "Clear API cache" button in `ui.SearchBox` button row — DONE
  (wraps `api.cache.clear_cache`, updates status text).
- TTL + cache-enabled toggle exposed via `prefs.py` — DONE
  (see #3 below).

### 2. Widen year window — SHIPPED

- `BaseConnector.search` signature changed to
  `search(given, surname, year_from=None, year_to=None)`.
- `ui._year_window(local)` returns the plausible-lifespan bounds:
  birth known → `[y-10, y+100]`, death-only → `[y-105, y+10]`,
  neither → `(None, None)`.
- OpenArchieven forwards as `eventYearFrom` / `eventYearTo`
  (live-verified against api.openarch.nl — hits stay inside the
  range).
- GenealogieOnline maps to `birth_year_from` / `birth_year_to`
  (still disabled — no OAuth creds).
- AlleGroningers accepts but still ignores. Needs a live probe to
  confirm the Memorix Solr `fq=datum:[…]` field name + type.
- Cache key extended to include both bounds; old single-`year` keys
  would just miss once and repopulate.

### 3. `prefs.py` — SHIPPED

GRAMPS config keys registered on import; `PreferencesDialog` opened
from a new "Settings…" button in `ui.SearchBox`.

Keys (namespace `grampssearch.`):
- `cache_enabled` (bool), `cache_ttl_days` (int, 1-365)
- `debug_log_enabled` (bool)
- `use_openarchieven`, `use_allegroningers`, `use_genealogieonline`
- `genealogieonline_client_id` / `_client_secret` / `_redirect_uri`
- `genealogieonline_token` / `_token_expires_at` (persisted but
  still no in-app OAuth flow — token must be provisioned manually
  or wired up later)

Helpers: `get_cache_enabled`, `get_cache_ttl_seconds`,
`get_debug_log_enabled`, `get_enabled_sources`,
`get_genealogieonline_creds`, `get_genealogieonline_token`,
`set_genealogieonline_token`, `has_valid_genealogieonline_token`.

Wiring:
- `tool._build_connectors` filters by `get_enabled_sources()`, wraps
  with `CachedConnector(ttl_seconds=get_cache_ttl_seconds())` only if
  `get_cache_enabled()`. GenealogieOnline is skipped unless creds
  complete AND a valid token is stored.
- `ui._log` + `_start_scan`'s truncate both gate on
  `get_debug_log_enabled()`.

Changes apply on next scan / next window open. Settings dialog save
does not reload connectors live — user must close + reopen the
window after flipping sources on/off.

Remaining: actual OAuth authorize flow (browser open → paste code
back → token exchange → `set_genealogieonline_token`). Currently
stubbed as a hint in the dialog.

### 4. Wire AlleGroningers year filter

Probe Memorix live: curl with a trial `fq=datum:[1800-01-01 TO 1900-12-31]`
(or numeric `fq=datum:[1800 TO 1900]`) and see which the endpoint
accepts. Then wire year_from/year_to through.

### 5. Unit tests for matcher

Stdlib-only, no GRAMPS needed.

### 6. Better name splitter — SHIPPED

`names.py` adds `parse_name(full) -> NameParts(given, tussenvoegsel,
surname, patronymic)` and `strip_tussenvoegsel(surname)` (leading-
particle split for surname-only strings). Pure stdlib.

Handles:
- Dutch tussenvoegsels (`van`, `de`, `der`, `den`, `ten`, `ter`,
  `'t`, `op`, `in`, `aan`, `bij`, `onder`, `uit`, `la`, `le`, `du`,
  `des`, ...). Compound runs (`van der`, `in 't`) fall out per-token.
- Comma-reordered archive form: `Bloemersma, Jan van` and
  `Alberda van Bloemersma, Jan` (compound surname preserved because
  comma form is authoritative — left side is the surname unit).
- Parenthesised aliases: `Jan (Johannes) de Vries`.
- Trailing patronymics: `Jansz`, `Jansz.`, `Janszoon`, `Jansdr`, `Jansd`.
- Solo `Given Patronymic` (pre-1811): surname="", given=first token,
  patronymic set.

Known limitation: plain (non-comma) input is ambiguous for compound
surnames — `Jan Alberda van Bloemersma` resolves to
given='Jan Alberda', tussen='van', surname='Bloemersma'. Without a
given-name dictionary we can't reliably tell 'Cornelis' (given) from
'Alberda' (surname prefix). Archives that matter (Open Archieven,
AlleGroningers) give us comma form or explicit voornaam/achternaam
fields, so the plain-form case is rare in practice.

Wired into:
- `api/open_archieven.py::_normalize` — replaces the naïve
  `rsplit(" ", 1)` with `parse_name`.
- `api/alle_groningers.py::_normalize` — `strip_tussenvoegsel` on
  `geslachtsnaam` (sometimes comes baked with 'van der'), plus
  `parse_name` on the `person_display_name` fallback.
- `matcher.py::_sim_surname` — new helper, strips leading tussens
  from both sides before comparing, so 'van der Berg' vs 'Berg'
  scores 1.0. `score_candidate` uses it for surname similarity.

Tests: 28 cases in `tests/test_names.py` (stdlib `unittest`, no
GRAMPS). Run from the `GrampsSearch/` dir:

```bash
python3 -m unittest tests.test_names -v
```

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
- **Next session: pick from Next steps #3 OAuth authorize flow,
  #4 AlleGroningers year filter, #5 matcher tests, or #6 name
  splitter.**
