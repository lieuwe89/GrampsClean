"""GrampsClean — Island Detection tab widget."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

import prefs
from widgets import ResultList
from worker import ScanWorker
from graph import KinshipGraph


COLUMNS = [("Name", 0), ("Group Size", 1), ("Detail", 2)]


class IslandTab(Gtk.Box):
    """
    Self-contained tab widget for island detection.

    Finds isolated individuals and small disconnected groups in the
    kinship network.

    Threading strategy:
      All GRAMPS DB access happens on the main thread (SQLite restriction).
      The worker thread receives plain Python dicts/lists and does only
      pure computation (union-find, sorting, string formatting).
    """

    def __init__(self, db_wrap, uistate):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(8)

        self.db_wrap = db_wrap
        self._uistate = uistate
        self._max_size = prefs.get_max_island_size()
        self._snapshot = None  # pre-fetched data, set on main thread before scan

        self._build_toolbar()
        self._result_list = ResultList(COLUMNS, on_activate=self._navigate_person)
        self.pack_start(self._result_list, True, True, 0)

        self._worker = None

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

        export_btn = Gtk.Button(label="Export CSV")
        export_btn.connect("clicked", self._on_export_csv)
        toolbar.pack_start(export_btn, False, False, 0)

        spin_label = Gtk.Label(label="Max group size:")
        self._spin = Gtk.SpinButton.new_with_range(1, 500, 1)
        self._spin.set_value(prefs.get_max_island_size())
        self._spin.connect("value-changed", self._on_max_size_changed)

        toolbar.pack_end(self._spin, False, False, 0)
        toolbar.pack_end(spin_label, False, False, 0)

        self.pack_start(toolbar, False, False, 0)

    # ------------------------------------------------------------------
    # Signal handlers (all run on main GTK thread)
    # ------------------------------------------------------------------

    def _on_scan(self, btn):
        if self._worker is not None and self._worker.is_running():
            return

        max_size = self._max_size

        # --- Snapshot all DB data on the main thread ---
        # GRAMPS SQLite connections cannot cross thread boundaries.
        # We read everything we need here, producing plain Python objects.
        self._result_list.set_status("Reading database\u2026")

        person_handles = []
        person_names = {}   # handle → "Surname, Given"
        person_ids = {}     # handle → gramps_id (for future use)

        for person in self.db_wrap.iter_people():
            h = person.get_handle()
            person_handles.append(h)
            person_names[h] = self.db_wrap.format_name(person)
            person_ids[h] = self.db_wrap.get_gramps_id(person)

        family_edges = []
        for family in self.db_wrap.iter_families():
            edges = []
            fh = family.get_father_handle()
            if fh:
                edges.append(fh)
            mh = family.get_mother_handle()
            if mh:
                edges.append(mh)
            for cr in family.get_child_ref_list():
                if cr.ref:
                    edges.append(cr.ref)
            if edges:
                family_edges.append(edges)

        # Package snapshot for the worker thread
        self._snapshot = {
            "person_handles": person_handles,
            "person_names": person_names,
            "family_edges": family_edges,
            "max_size": max_size,
        }

        self._scan_btn.set_sensitive(False)
        self._cancel_btn.set_sensitive(True)
        self._result_list.set_status("Scanning\u2026")

        # Worker receives a dummy db_wrap (snapshot has everything)
        self._worker = ScanWorker(self._result_list, self._scan_fn, None)
        self._worker.start()
        GLib.timeout_add(200, self._check_done)

    def _on_cancel(self, btn):
        if self._worker:
            self._worker.cancel()
        self._cancel_btn.set_sensitive(False)

    def _on_export_csv(self, btn):
        self._result_list.export_csv(parent_window=self.get_toplevel())

    def _on_max_size_changed(self, spin):
        self._max_size = int(spin.get_value())

    def _check_done(self):
        if self._worker is not None and self._worker.is_running():
            return True
        self._scan_btn.set_sensitive(True)
        self._cancel_btn.set_sensitive(False)
        return False

    def _navigate_person(self, handle):
        """
        Navigate the GRAMPS main window to the given person.

        Pushes the handle onto the Person navigation history, then switches
        the main window to the People view so the navigation is visible
        regardless of which view was previously active.
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

        Uses only self._snapshot (plain Python dicts/lists).
        Must not access self.db_wrap or any GRAMPS DB object.
        """
        snap = self._snapshot
        person_handles = snap["person_handles"]
        person_names = snap["person_names"]
        family_edges = snap["family_edges"]
        max_size = snap["max_size"]

        # Pure computation — no DB access
        graph = KinshipGraph.build_from_raw(person_handles, family_edges)
        islands = graph.get_islands(max_size)

        rows = []
        for component in islands:
            group_size = len(component)
            detail = "Isolated" if group_size == 1 else f"Group of {group_size}"
            for handle in sorted(component):
                name = person_names.get(handle, "[Unknown]")
                rows.append((name, str(group_size), detail, handle))

        total_people = len(rows)
        total_groups = len(islands)
        status = (
            f"{total_people} people in {total_groups} groups "
            f"(max size: {max_size})"
        )

        if not rows:
            yield ("", "", ""), f"No islands found (max size: {max_size})"
            return

        for i, row in enumerate(rows):
            s = status if i == len(rows) - 1 else ""
            yield row, s
