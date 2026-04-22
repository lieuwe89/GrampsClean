"""Open Archieven (openarch.nl) connector.

Public API, no key. Each doc is one person×event; we dispatch
Dutch `eventtype` values onto birth/death fields. If the event is
neither, we return the record with date/place empty so the matcher
can still score on name.
"""

from typing import List, Optional
from .base import BaseConnector, ExternalPerson

try:
    from names import parse_name  # top-level when GRAMPS loads tool.py
except ImportError:
    from ..names import parse_name  # package-relative when run as a package


BIRTH_EVENTS = ("geboorte", "doop", "birth", "baptism")
DEATH_EVENTS = ("overlijden", "begraven", "death", "burial")


class OpenArchievenClient(BaseConnector):
    source_name = "openarchieven"
    base_url = "https://api.openarch.nl/1.0/records/search.json"

    def search(
        self,
        given: str,
        surname: str,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> List[ExternalPerson]:
        params = {
            "name": f"{given} {surname}".strip(),
            "eventYearFrom": year_from,
            "eventYearTo": year_to,
            "start": 0,
            "number": 20,
            "lang": "nl",
        }
        url = f"{self.base_url}?{self._qs(params)}"
        data = self._get_json(url)
        return [self._normalize(rec) for rec in data.get("response", {}).get("docs", [])]

    def _normalize(self, rec: dict) -> ExternalPerson:
        name = (rec.get("personname") or "").strip()
        parts = parse_name(name)
        given = parts.given
        surname = parts.surname

        date = self._fmt_date(rec.get("eventdate"))
        places = rec.get("eventplace") or []
        place = places[0] if places else ""
        eventtype = (rec.get("eventtype") or "").lower()

        birth_date = date if any(w in eventtype for w in BIRTH_EVENTS) else None
        birth_place = place if birth_date else ""
        death_date = date if any(w in eventtype for w in DEATH_EVENTS) else None
        death_place = place if death_date else ""

        return ExternalPerson(
            source=self.source_name,
            source_id=rec.get("identifier", "") or rec.get("pid", ""),
            given=given,
            surname=surname,
            birth_date=birth_date,
            birth_place=birth_place,
            death_date=death_date,
            death_place=death_place,
            detail_url=rec.get("url", "") or "",
            raw=rec,
        )

    @staticmethod
    def _fmt_date(d):
        if not isinstance(d, dict):
            return None
        y = d.get("year")
        if not y:
            return None
        m = d.get("month") or 0
        day = d.get("day") or 0
        if m and day:
            return f"{y:04d}-{m:02d}-{day:02d}"
        if m:
            return f"{y:04d}-{m:02d}"
        return f"{y:04d}"
