"""GrampsSearch — database access layer.

Read helpers for extracting person data to send to APIs, and write
helpers for merging approved external data back into the GRAMPS db.
"""

from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.lib import (
    Event,
    EventRef,
    EventType,
    Date,
    Name,
    Place,
    PlaceName,
    Surname,
    Source,
    Citation,
)
from gramps.gen.db import DbTxn

_ = glocale.translation.gettext


class GrampsDb:
    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_active_person(self, uistate):
        handle = uistate.get_active("Person") if uistate else None
        if not handle:
            return None
        return self.db.get_person_from_handle(handle)

    def iter_people_missing_core_events(self):
        """Yield Person objects lacking a birth OR a death event reference."""
        for handle in self.db.get_person_handles():
            person = self.db.get_person_from_handle(handle)
            if not person:
                continue
            if person.get_birth_ref() is None or person.get_death_ref() is None:
                yield person

    def person_summary(self, person):
        """Return dict of core fields consumed by the matcher/UI."""
        name = person.get_primary_name()
        given = (name.get_first_name() or "").strip()
        surname = (name.get_surname() or "").strip()
        return {
            "gramps_id": person.get_gramps_id() or "",
            "handle": person.handle,
            "given": given,
            "surname": surname,
            "gender": person.get_gender(),
            "birth": self._event_summary(person.get_birth_ref()),
            "death": self._event_summary(person.get_death_ref()),
        }

    def _event_summary(self, ref):
        if ref is None:
            return None
        event = self.db.get_event_from_handle(ref.ref)
        if not event:
            return None
        d = event.get_date_object()
        return {
            "date": d.get_ymd() if d and not d.is_empty() else None,
            "date_text": d.get_text() if d else "",
            "place": self._place_name(event.get_place_handle()),
        }

    def _place_name(self, place_handle):
        if not place_handle:
            return ""
        place = self.db.get_place_from_handle(place_handle)
        if not place:
            return ""
        return place.get_name().get_value() if place.get_name() else ""

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def merge_fields(self, person, selected, source_title="External archive"):
        """Apply approved external fields to `person`.

        `selected` dict with optional keys:
          - birth: {"date_text": str|None, "place": str|None}
          - death: {"date_text": str|None, "place": str|None}
          - names: [{"given": str, "surname": str}]
          - source_url: str
        """
        with DbTxn(_("GrampsSearch merge"), self.db) as trans:
            citation_handle = self._ensure_citation(
                trans, source_title, selected.get("source_url", "")
            )

            if selected.get("birth"):
                self._set_event(trans, person, EventType.BIRTH, selected["birth"], citation_handle)
            if selected.get("death"):
                self._set_event(trans, person, EventType.DEATH, selected["death"], citation_handle)

            for alt in selected.get("names", []) or []:
                self._add_alternate_name(person, alt)

            self.db.commit_person(person, trans)

    def _set_event(self, trans, person, etype, data, citation_handle):
        if etype == EventType.BIRTH:
            ref = person.get_birth_ref()
            set_ref = person.set_birth_ref
        else:
            ref = person.get_death_ref()
            set_ref = person.set_death_ref

        if ref is None:
            event = Event()
            event.set_type(EventType(etype))
            self._apply_event_data(trans, event, data, citation_handle)
            self.db.add_event(event, trans)
            new_ref = EventRef()
            new_ref.ref = event.handle
            set_ref(new_ref)
        else:
            event = self.db.get_event_from_handle(ref.ref)
            self._apply_event_data(trans, event, data, citation_handle)
            self.db.commit_event(event, trans)

    def _apply_event_data(self, trans, event, data, citation_handle):
        if data.get("date_text"):
            d = Date()
            d.set_as_text(data["date_text"])
            event.set_date_object(d)
        if data.get("place"):
            place_handle = self._ensure_place(trans, data["place"])
            event.set_place_handle(place_handle)
        if citation_handle:
            event.add_citation(citation_handle)

    def _ensure_place(self, trans, name):
        for handle in self.db.get_place_handles():
            p = self.db.get_place_from_handle(handle)
            if p and p.get_name() and p.get_name().get_value() == name:
                return handle
        place = Place()
        pname = PlaceName()
        pname.set_value(name)
        place.set_name(pname)
        self.db.add_place(place, trans)
        return place.handle

    def _ensure_citation(self, trans, source_title, source_url):
        source = None
        for handle in self.db.get_source_handles():
            s = self.db.get_source_from_handle(handle)
            if s and s.get_title() == source_title:
                source = s
                break
        if source is None:
            source = Source()
            source.set_title(source_title)
            self.db.add_source(source, trans)

        citation = Citation()
        citation.set_reference_handle(source.handle)
        if source_url:
            citation.set_page(source_url)
        self.db.add_citation(citation, trans)
        return citation.handle

    def _add_alternate_name(self, person, alt):
        n = Name()
        n.set_first_name(alt.get("given", ""))
        surname = Surname()
        surname.set_surname(alt.get("surname", ""))
        n.add_surname(surname)
        person.add_alternate_name(n)
