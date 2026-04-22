"""AlleGroningers.nl connector — Memorix Genealogy backend.

API key is public (embedded in site source). Endpoint confirmed
against obsidian note `Groninger Archieven API.md`.
"""

from typing import List, Optional
from .base import BaseConnector, ExternalPerson

try:
    from names import parse_name, strip_tussenvoegsel
except ImportError:
    from ..names import parse_name, strip_tussenvoegsel


BIRTH_DEEDS = ("geboorte", "doop", "birth", "baptism")
DEATH_DEEDS = ("overlijden", "begraven", "death", "burial")


class AlleGroningersClient(BaseConnector):
    source_name = "allegroningers"
    base_url = "https://webservices.memorix.nl/genealogy/person"
    api_key = "6976bb7e-0c61-4f03-bf5b-df645d5fd086"
    detail_url_tmpl = "https://www.allegroningers.nl/zoeken-op-naam/persons/{uuid}"

    def search(
        self,
        given: str,
        surname: str,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
    ) -> List[ExternalPerson]:
        # TODO: wire year bounds into Memorix Solr `fq` filter
        # (e.g. fq=datum:[YYYY-01-01 TO YYYY-12-31]). Skipped until
        # we verify the field name + type against live responses.
        q = f"{given} {surname}".strip()
        params = {
            "apiKey": self.api_key,
            "q": q,
            "rows": 25,
        }
        url = f"{self.base_url}?{self._qs(params)}"
        data = self._get_json(url)
        return [self._normalize(rec) for rec in data.get("person", [])]

    def _normalize(self, rec: dict) -> ExternalPerson:
        meta = rec.get("metadata", {}) or {}

        # Prefer explicit fields when present; fall back to display name.
        given = (meta.get("voornaam") or "").strip()
        surname = (meta.get("geslachtsnaam") or meta.get("achternaam") or "").strip()
        if surname:
            # Memorix sometimes bakes the tussenvoegsel into the surname
            # field ("van der Berg") — normalise to core surname so the
            # matcher scores against an equivalent local surname.
            _, surname = strip_tussenvoegsel(surname)
        if not given and not surname:
            display = (meta.get("person_display_name") or "").strip()
            parts = parse_name(display)
            given = parts.given
            surname = parts.surname

        event_date = meta.get("datum")
        event_place = meta.get("plaats", "") or ""
        deed_type = (meta.get("deed_type_title") or "").lower()

        birth_date = event_date if any(w in deed_type for w in BIRTH_DEEDS) else None
        birth_place = event_place if birth_date else ""
        death_date = event_date if any(w in deed_type for w in DEATH_DEEDS) else None
        death_place = event_place if death_date else ""

        uuid = rec.get("entity_uuid", "")
        return ExternalPerson(
            source=self.source_name,
            source_id=uuid or str(rec.get("id", "")),
            given=given,
            surname=surname,
            birth_date=birth_date,
            birth_place=birth_place,
            death_date=death_date,
            death_place=death_place,
            detail_url=self.detail_url_tmpl.format(uuid=uuid) if uuid else "",
            raw=rec,
        )
