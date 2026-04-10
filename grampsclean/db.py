"""GrampsClean — database access layer.

Wraps the GRAMPS DbReadBase with helpers used by all four tool tabs.
No GTK or gramps.gui imports — pure data access only.
"""


class GrampsDb:
    """
    Thin wrapper around the GRAMPS database.

    Provides name formatting, event date extraction, and iteration
    helpers so each tool tab doesn't need to repeat boilerplate.
    """

    def __init__(self, db):
        """
        :param db: GRAMPS DbReadBase instance (from tool.Tool.self.db)
        """
        self.db = db

    # ------------------------------------------------------------------
    # Name helpers
    # ------------------------------------------------------------------

    def format_name(self, person):
        """
        Return a display name string for a person.

        Format: "Surname, Given" — falls back gracefully if either is missing.

        :param person: gramps.gen.lib.Person
        :returns: str
        """
        try:
            name = person.get_primary_name()
            given = (name.get_first_name() or "").strip()
            surname = (name.get_surname() or "").strip()
        except Exception:
            return "[Unknown]"

        if surname and given:
            return f"{surname}, {given}"
        if surname:
            return surname
        if given:
            return given
        return "[Unknown]"

    def get_gramps_id(self, person):
        """
        Return the GRAMPS ID string (e.g. "I0042").

        :param person: gramps.gen.lib.Person
        :returns: str
        """
        return person.get_gramps_id() or ""

    # ------------------------------------------------------------------
    # Event/date helpers
    # ------------------------------------------------------------------

    def get_event_date(self, person, event_type):
        """
        Return the GRAMPS Date object for a person's birth or death event.

        :param person: gramps.gen.lib.Person
        :param event_type: "birth" or "death"
        :returns: gramps.gen.lib.Date or None
        """
        try:
            if event_type == "birth":
                ref = person.get_birth_ref()
            elif event_type == "death":
                ref = person.get_death_ref()
            else:
                return None

            if ref is None:
                return None

            event = self.db.get_event_from_handle(ref.ref)
            if event is None:
                return None

            date = event.get_date_object()
            if date is None or not date.is_regular():
                return None

            return date
        except Exception:
            return None

    def get_year(self, person, event_type):
        """
        Return the year (int) for a birth or death event, or None.

        Convenience wrapper around get_event_date().
        """
        date = self.get_event_date(person, event_type)
        if date is None:
            return None
        year = date.get_year()
        return year if year else None

    # ------------------------------------------------------------------
    # Iteration helpers
    # ------------------------------------------------------------------

    def iter_people(self):
        """Yield every Person in the database."""
        yield from self.db.iter_people()

    def iter_families(self):
        """Yield every Family in the database."""
        yield from self.db.iter_families()

    def get_person_from_handle(self, handle):
        """Return a Person by handle."""
        return self.db.get_person_from_handle(handle)

    def get_family_from_handle(self, handle):
        """Return a Family by handle."""
        return self.db.get_family_from_handle(handle)

    def get_event_from_handle(self, handle):
        """Return an Event by handle."""
        return self.db.get_event_from_handle(handle)

    def count_people(self):
        """Return the total number of people in the database."""
        return self.db.get_number_of_people()
