"""GrampsClean — Missing Data Finder tab widget."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from widgets import ResultList
from worker import ScanWorker


COLUMNS = [("Name", 0), ("ID", 1), ("Missing", 2)]

FIELD_LABELS = {
    "birth_date":  "Birth Date",
    "death_date":  "Death Date",
    "birth_place": "Birth Place",
    "death_place": "Death Place",
}


class MissingTab(Gtk.Box):
    """
    Self-contained tab widget for missing data detection.

    Scans all persons for missing birth date, death date, birth place,
    and/or death place — whichever fields the user selects via checkboxes.

    Threading strategy:
      All GRAMPS DB access happens on the main thread (SQLite restriction).
      The snapshot captures per-person field presence as plain Python bools.
      The worker thread performs only pure filtering and row construction —
      no DB object access.
    """

    def __init__(self, db_wrap, uistate):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(8)

        self.db_wrap = db_wrap
        self._uistate = uistate
        self._snapshot = None
        self._worker = None

        self._build_toolbar()
        self._result_list = ResultList(COLUMNS, on_activate=self._navigate_person)
        self.pack_start(self._result_list, True, True, 0)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_toolbar(self):
        toolbar = Gtk.Box(spacing=6)
        toolbar.set_border_width(4)

        self._scan_btn = Gtk.Button(label="Scan")
        self._scan_btn.connect("clicked", self._on_scan)
        toolbar.pack_start(self._scan_btn, False, False, 0)

        self._cancel_btn = Gtk.Button(label="Cancel")
        self._cancel_btn.set_sensitive(False)
        self._cancel_btn.connect("clicked", self._on_cancel)
        toolbar.pack_start(self._cancel_btn, False, False, 0)

        # Field selection checkboxes — all active by default
        self._chk_birth_date  = Gtk.CheckButton(label="Birth Date")
        self._chk_death_date  = Gtk.CheckButton(label="Death Date")
        self._chk_birth_place = Gtk.CheckButton(label="Birth Place")
        self._chk_death_place = Gtk.CheckButton(label="Death Place")

        for chk in (
            self._chk_birth_date,
            self._chk_death_date,
            self._chk_birth_place,
            self._chk_death_place,
        ):
            chk.set_active(True)
            toolbar.pack_start(chk, False, False, 0)

        # Living/deceased filter — packed to the right
        filter_label = Gtk.Label(label="Show:")
        self._filter_combo = Gtk.ComboBoxText()
        self._filter_combo.append("all",      "All people")
        self._filter_combo.append("living",   "Living only")
        self._filter_combo.append("deceased", "Deceased only")
        self._filter_combo.set_active_id("all")

        toolbar.pack_end(self._filter_combo, False, False, 0)
        toolbar.pack_end(filter_label, False, False, 0)

        self.pack_start(toolbar, False, False, 0)

    # ------------------------------------------------------------------
    # Signal handlers (all run on main GTK thread)
    # ------------------------------------------------------------------

    def _on_scan(self, btn):
        if self._worker is not None and self._worker.is_running():
            return

        # Read checkbox state and filter mode before snapshot
        selected = {
            "birth_date":  self._chk_birth_date.get_active(),
            "death_date":  self._chk_death_date.get_active(),
            "birth_place": self._chk_birth_place.get_active(),
            "death_place": self._chk_death_place.get_active(),
        }
        filter_mode = self._filter_combo.get_active_id() or "all"

        if not any(selected.values()):
            self._result_list.set_status("Select at least one field.")
            return

        self._result_list.clear()
        self._result_list.set_status("Reading database\u2026")

        # --- Snapshot all DB data on the main thread ---
        # GRAMPS SQLite connections cannot cross thread boundaries.
        # We capture field presence and deceased status as plain Python bools here.
        person_data = {}
        for person in self.db_wrap.iter_people():
            h = person.get_handle()
            person_data[h] = {
                "name":        self.db_wrap.format_name(person),
                "gramps_id":   self.db_wrap.get_gramps_id(person),
                "is_deceased": person.get_death_ref() is not None,
                "birth_date":  self.db_wrap.get_event_date(person, "birth") is None,
                "death_date":  self.db_wrap.get_event_date(person, "death") is None,
                "birth_place": self.db_wrap.get_event_place_handle(person, "birth") is None,
                "death_place": self.db_wrap.get_event_place_handle(person, "death") is None,
            }

        self._snapshot = {
            "person_data": person_data,
            "selected": selected,
            "filter_mode": filter_mode,
        }

        self._scan_btn.set_sensitive(False)
        self._cancel_btn.set_sensitive(True)
        self._result_list.set_status("Scanning\u2026")

        self._worker = ScanWorker(self._result_list, self._scan_fn, None)
        self._worker.start()
        GLib.timeout_add(200, self._check_done)

    def _on_cancel(self, btn):
        if self._worker:
            self._worker.cancel()
        self._cancel_btn.set_sensitive(False)

    def _check_done(self):
        if self._worker is not None and self._worker.is_running():
            return True
        self._scan_btn.set_sensitive(True)
        self._cancel_btn.set_sensitive(False)
        return False

    def _navigate_person(self, handle):
        """
        Navigate the GRAMPS main window to the given person.

        Follows the same pattern as IslandTab._navigate_person (02-03).
        """
        if not handle:
            return
        self._uistate.set_active(handle, 'Person')
        try:
            vm = self._uistate.viewmanager
            cat_num = vm.get_category("People")
            if cat_num is not None:
                vm.goto_page(cat_num, None)
        except Exception:
            pass  # navigation still works if People view is already active

    # ------------------------------------------------------------------
    # Scan logic (runs in background thread — NO DB calls allowed here)
    # ------------------------------------------------------------------

    def _scan_fn(self, _db_wrap_unused):
        """
        Generator yielding (row_tuple, status_text) pairs.

        Uses only self._snapshot (plain Python dicts/bools).
        Must not access self.db_wrap or any GRAMPS DB object.
        """
        snap = self._snapshot
        person_data = snap["person_data"]
        selected = snap["selected"]
        filter_mode = snap["filter_mode"]

        rows = []
        for handle, info in person_data.items():
            if filter_mode == "living" and info["is_deceased"]:
                continue
            if filter_mode == "deceased" and not info["is_deceased"]:
                continue
            missing = [
                FIELD_LABELS[f]
                for f in ("birth_date", "death_date", "birth_place", "death_place")
                if selected.get(f) and info[f]  # field selected AND missing
            ]
            if missing:
                rows.append((
                    info["name"],
                    info["gramps_id"],
                    ", ".join(missing),
                    handle,          # hidden tag for navigation (wired in 03-02)
                ))

        if not rows:
            yield ("", "", ""), "No missing data found for selected fields."
            return

        total = len(rows)

        # Compute per-field counts for detailed status bar
        field_counts = {}
        for row in rows:
            for label in row[2].split(", "):
                if label:
                    field_counts[label] = field_counts.get(label, 0) + 1

        FIELD_ORDER = ["Birth Date", "Death Date", "Birth Place", "Death Place"]
        parts = [
            f"{field_counts[f]} missing {f}"
            for f in FIELD_ORDER
            if f in field_counts
        ]
        status = (
            f"{total} people \u2014 " + ", ".join(parts)
            if parts else f"{total} people with missing data"
        )

        for i, row in enumerate(rows):
            s = status if i == len(rows) - 1 else ""
            yield row, s
