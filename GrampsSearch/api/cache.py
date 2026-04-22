"""SQLite-backed cache for connector.search() results.

Cuts redundant HTTP across re-scans and across people sharing a surname.
Wrap any `BaseConnector` with `CachedConnector(inner)` — same `search()`
signature, same return shape (list[ExternalPerson]).

Key: `source|given_norm|surname_norm|year`.
Value: JSON-encoded list of `ExternalPerson.as_dict()` payloads.
TTL: 30 days default. Stale rows are ignored (and rewritten on miss).

Storage: `~/Library/Application Support/gramps/gramps60/grampssearch_cache.db`.
User can delete that file to reset.

Thread safety: one fresh sqlite connection per call. Scan bottleneck is
HTTP, not sqlite open; avoids shared-connection locking.
"""

import json
import os
import sqlite3
import time
from datetime import datetime
from typing import List, Optional

from .base import BaseConnector, ExternalPerson


DEFAULT_DB_PATH = os.path.expanduser(
    "~/Library/Application Support/gramps/gramps60/grampssearch_cache.db"
)
DEFAULT_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days
DEBUG_LOG = os.path.expanduser("~/Documents/grampssearch-debug.log")


def _log(msg: str):
    """Append to the same debug log ui.py writes to."""
    line = f"{datetime.now().strftime('%H:%M:%S')} {msg}"
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line)


def _ensure_schema(conn: sqlite3.Connection):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cache (
            key        TEXT PRIMARY KEY,
            source     TEXT NOT NULL,
            fetched_at INTEGER NOT NULL,
            payload    TEXT NOT NULL
        )
        """
    )
    conn.commit()


def _open(db_path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=5.0)
    _ensure_schema(conn)
    return conn


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _make_key(source: str, given: str, surname: str, year: Optional[int]) -> str:
    return f"{source}|{_norm(given)}|{_norm(surname)}|{year if year is not None else ''}"


class CachedConnector:
    """Decorator that adds persistent caching to any BaseConnector.

    Mirrors `BaseConnector.search(given, surname, year=None)`. Exposes
    `source_name` from the wrapped connector so callers can introspect.
    """

    def __init__(
        self,
        inner: BaseConnector,
        db_path: str = DEFAULT_DB_PATH,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ):
        self._inner = inner
        self._db_path = db_path
        self._ttl = ttl_seconds
        self.source_name = inner.source_name

    # ------------------------------------------------------------------

    def search(self, given: str, surname: str, year: Optional[int] = None) -> List[ExternalPerson]:
        key = _make_key(self.source_name, given, surname, year)
        hit = self._read(key)
        if hit is not None:
            _log(f"[cache] HIT  {key} ({len(hit)} rows)")
            return hit

        _log(f"[cache] MISS {key}")
        results = self._inner.search(given, surname, year=year)
        try:
            self._write(key, results)
        except Exception as e:
            _log(f"[cache] write failed for {key}: {e}")
        return results

    # ------------------------------------------------------------------

    def _read(self, key: str) -> Optional[List[ExternalPerson]]:
        cutoff = int(time.time()) - self._ttl
        try:
            conn = _open(self._db_path)
            try:
                row = conn.execute(
                    "SELECT payload, fetched_at FROM cache WHERE key = ?",
                    (key,),
                ).fetchone()
            finally:
                conn.close()
        except Exception as e:
            _log(f"[cache] read failed for {key}: {e}")
            return None

        if not row:
            return None
        payload, fetched_at = row
        if fetched_at < cutoff:
            return None
        try:
            rows = json.loads(payload)
            return [ExternalPerson(**d) for d in rows]
        except Exception as e:
            _log(f"[cache] decode failed for {key}: {e}")
            return None

    def _write(self, key: str, results: List[ExternalPerson]):
        payload = json.dumps([r.as_dict() for r in results], ensure_ascii=False)
        conn = _open(self._db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO cache (key, source, fetched_at, payload) "
                "VALUES (?, ?, ?, ?)",
                (key, self.source_name, int(time.time()), payload),
            )
            conn.commit()
        finally:
            conn.close()


def clear_cache(db_path: str = DEFAULT_DB_PATH):
    """Delete the cache file (used by a future 'Clear cache' button)."""
    try:
        os.remove(db_path)
        _log(f"[cache] cleared {db_path}")
    except FileNotFoundError:
        pass
    except Exception as e:
        _log(f"[cache] clear failed: {e}")
