"""GenealogieOnline.nl connector — public OpenSearch-style JSON endpoint.

Endpoint: https://www.genealogieonline.nl/zoeken/index.php
Params:
    q      — surname (required; single token — space-separated values return 0)
    vn     — given name (optional)
    start  — pagination offset, 15 records per page
    output — "json" returns a JSON array; we always set it

No OAuth, no auth headers. Response is a JSON array of records; empty
array means no results. Content-type is ``text/javascript``, so we
decode by hand rather than going through the base ``_get_json``.

The site accepts a ``pn`` (plaatsnaam) place filter but it returns empty
results for many real matches — we omit it and let the matcher handle
place scoring client-side.

Year filtering: the endpoint has no year parameter. We filter results
client-side against [year_from, year_to] using ``geb_jaar`` / ``ovl_jaar``
when the record exposes them; records without any year pass through
(matcher will score them low if year is known locally).

Record shape (JSON row):
    {
      "id": "595_I000245",
      "achternaam": "Coret",
      "voornaam": "Adriana Maria",
      "geb_jaar": 1913,           # optional
      "ovl_jaar": null,           # optional
      "url": "https://.../I000245.php",
      "publ_titel": "Genealogie Coret",
      "publ_url":   "https://.../genealogie-coret/"
    }
"""

import json
import urllib.error
import urllib.request
from typing import List, Optional

try:
    from names import parse_name
except ImportError:
    from ..names import parse_name

from .base import BaseConnector, ExternalPerson, ConnectorError, _SSL_CTX


PAGE_SIZE = 15
DEFAULT_MAX_PAGES = 3
SEARCH_URL = "https://www.genealogieonline.nl/zoeken/index.php"

# Site returns HTTP 404 for the default Python-urllib UA. A plain
# browser-style UA is accepted.
_USER_AGENT = "GrampsSearch/1.0 (+https://gramps-project.org)"


class GenealogieOnlineClient(BaseConnector):
    source_name = "genealogieonline"

    def __init__(self, max_pages: int = DEFAULT_MAX_PAGES):
        self.max_pages = max(1, max_pages)

    def search(
        self,
        given: str,
        surname: str,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> List[ExternalPerson]:
        surname = (surname or "").strip()
        if not surname:
            return []

        out: List[ExternalPerson] = []
        for page in range(self.max_pages):
            start = page * PAGE_SIZE
            batch = self._fetch_page(given, surname, start)
            if not batch:
                break
            out.extend(batch)
            if len(batch) < PAGE_SIZE:
                break

        if year_from is None and year_to is None:
            return [self._normalize(r) for r in out]

        filtered = [r for r in out if self._year_in_window(r, year_from, year_to)]
        return [self._normalize(r) for r in filtered]

    def _fetch_page(self, given: str, surname: str, start: int) -> List[dict]:
        params = {
            "q": surname,
            "vn": given or None,
            "start": start if start else None,
            "output": "json",
        }
        url = f"{SEARCH_URL}?{self._qs(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout, context=_SSL_CTX) as r:
                body = r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raise ConnectorError(f"{self.source_name} HTTP {e.code}: {e.reason}") from e
        except urllib.error.URLError as e:
            raise ConnectorError(f"{self.source_name} network error: {e.reason}") from e

        try:
            data = json.loads(body)
        except ValueError as e:
            raise ConnectorError(f"{self.source_name} malformed JSON: {e}") from e

        if not isinstance(data, list):
            raise ConnectorError(f"{self.source_name} unexpected payload type")
        return data

    @staticmethod
    def _year_in_window(rec: dict, year_from: Optional[int], year_to: Optional[int]) -> bool:
        years = [y for y in (rec.get("geb_jaar"), rec.get("ovl_jaar")) if isinstance(y, int)]
        if not years:
            return True
        lo = year_from if year_from is not None else min(years)
        hi = year_to if year_to is not None else max(years)
        return any(lo <= y <= hi for y in years)

    def _normalize(self, rec: dict) -> ExternalPerson:
        voornaam = (rec.get("voornaam") or "").strip()
        achternaam = (rec.get("achternaam") or "").strip()

        # voornaam occasionally wraps a placeholder like "(baarkind)" or
        # carries aliases in parens — let parse_name untangle.
        parts = parse_name(f"{voornaam} {achternaam}".strip()) if voornaam and achternaam else None
        given = parts.given if parts else voornaam
        surname = parts.surname or achternaam if parts else achternaam
        tussen = parts.tussenvoegsel if parts else ""
        if tussen:
            surname = f"{tussen} {surname}".strip()

        birth_year = rec.get("geb_jaar")
        death_year = rec.get("ovl_jaar")
        return ExternalPerson(
            source=self.source_name,
            source_id=str(rec.get("id", "")),
            given=given,
            surname=surname,
            birth_date=str(birth_year) if isinstance(birth_year, int) else None,
            birth_place="",
            death_date=str(death_year) if isinstance(death_year, int) else None,
            death_place="",
            detail_url=rec.get("url", "") or "",
            raw=rec,
        )
