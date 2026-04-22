"""GrampsClean — Name Prefix Corrector tab widget.

Threading strategy:
  All GRAMPS DB access happens on the main thread (SQLite restriction).
  _build_snapshot() collects all person name data into plain Python dicts.
  The worker thread calls detect_issues() which is pure Python — no DB access.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from gramps.gen.db import DbTxn
import prefs
from worker import ScanWorker


# ---------------------------------------------------------------------------
# Snapshot builder (must run on the main thread)
# ---------------------------------------------------------------------------

def _build_snapshot(db_wrap):
    """Build a plain-Python snapshot of name data for all persons.

    Must be called on the main thread — accesses GRAMPS SQLite connections.
    Returns a dict keyed by person handle; values contain only plain Python
    types (str).  No GRAMPS objects are stored in the snapshot.
    """
    persons = {}
    for person in db_wrap.iter_people():
        handle = person.get_handle()
        name_obj = person.get_primary_name()

        given = (name_obj.get_first_name() or "").strip()

        surname_list = name_obj.get_surname_list()
        if surname_list:
            sn_obj = surname_list[0]
            surname = (sn_obj.get_surname() or "").strip()
            prefix_field = (sn_obj.get_prefix() or "").strip()
        else:
            surname = ""
            prefix_field = ""

        persons[handle] = {
            "name": db_wrap.format_name(person),
            "gramps_id": db_wrap.get_gramps_id(person),
            "given": given,
            "surname": surname,
            "prefix": prefix_field,
        }

    return persons


# ---------------------------------------------------------------------------
# Detection engine (pure Python — safe for background thread)
# ---------------------------------------------------------------------------

def detect_issues(snapshot, prefixes):
    """Detect misplaced surname prefixes across all persons in the snapshot.

    Rules:
      - If the surname prefix field is already non-empty, skip the person
        (the prefix is correctly placed).
      - If the given name starts with a known prefix followed by a space,
        flag it as "Prefix '{prefix}' in given name".
      - Else if the surname starts with a known prefix followed by a space,
        flag it as "Prefix '{prefix}' in surname".
      - First matching prefix wins (list is sorted longest-first).

    Must not access the GRAMPS DB — snapshot only.
    Returns a list of finding dicts sorted by person name.
    """
    prefixes_lower = [p.lower() for p in prefixes]
    findings = []

    for handle, p in snapshot.items():
        # Already correctly placed — nothing to flag
        if p["prefix"]:
            continue

        given_lower = p["given"].lower()
        surname_lower = p["surname"].lower()
        issue = None
        field_type = None
        prefix = None

        for prefix in prefixes_lower:
            token = prefix + " "
            if given_lower.startswith(token):
                issue = f"Prefix '{prefix}' in given name"
                field_type = "given"
                break
            elif surname_lower.startswith(token):
                issue = f"Prefix '{prefix}' in surname"
                field_type = "surname"
                break

        if issue:
            if field_type == "given":
                current_value = p["given"]
            else:
                current_value = p["surname"]
            proposed_value = current_value[len(prefix) + 1:]

            findings.append({
                "handle": handle,
                "name": p["name"],
                "gramps_id": p["gramps_id"],
                "issue": issue,
                "prefix_found": prefix,
                "field_type": field_type,
                "current_value": current_value,
                "proposed_value": proposed_value,
            })

    findings.sort(key=lambda f: f["name"])
    return findings


# ---------------------------------------------------------------------------
# Preview table widget
# ---------------------------------------------------------------------------

class PreviewTable(Gtk.Box):
    """Gtk.ListStore-based preview table with checkboxes and current/proposed columns."""

    _COL_CHECKED  = 0
    _COL_NAME     = 1
    _COL_ID       = 2
    _COL_FIELD    = 3
    _COL_CURRENT  = 4
    _COL_PROPOSED = 5
    _COL_HANDLE   = 6
    _COL_PREFIX   = 7
    _COL_FTYPE    = 8

    def __init__(self, on_activate=None):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._on_activate = on_activate

        self.store = Gtk.ListStore(bool, str, str, str, str, str, str, str, str)
        self.tree = Gtk.TreeView(model=self.store)
        self.tree.set_enable_search(False)
        self.tree.connect("row-activated", self._row_activated)

        # Checkbox column
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self._on_toggled)
        col_check = Gtk.TreeViewColumn("\u2611", renderer_toggle, active=self._COL_CHECKED)
        col_check.set_min_width(30)
        col_check.set_resizable(False)
        self.tree.append_column(col_check)

        # Text columns
        for title, col_idx, min_w in [
            ("Name",     self._COL_NAME,     160),
            ("ID",       self._COL_ID,        70),
            ("Field",    self._COL_FIELD,     90),
            ("Current",  self._COL_CURRENT,  140),
            ("Proposed", self._COL_PROPOSED, 200),
        ]:
            renderer = Gtk.CellRendererText()
            col = Gtk.TreeViewColumn(title, renderer, text=col_idx)
            col.set_min_width(min_w)
            col.set_resizable(True)
            self.tree.append_column(col)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_shadow_type(Gtk.ShadowType.IN)
        scroll.add(self.tree)
        self.pack_start(scroll, True, True, 0)

        self.status_label = Gtk.Label(label="Ready.")
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_margin_start(4)
        self.status_label.set_margin_bottom(4)
        self.pack_start(self.status_label, False, False, 0)

    def clear(self):
        self.store.clear()
        self.status_label.set_text("Ready.")

    def set_status(self, text):
        self.status_label.set_text(text)

    def export_csv(self, parent_window=None):
        """Export visible rows (Name, ID, Field, Current, Proposed) to a CSV file."""
        import csv
        dialog = Gtk.FileChooserDialog(
            title="Export CSV",
            parent=parent_window,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Save",   Gtk.ResponseType.OK)
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_current_name("grampsclean_export.csv")
        response = dialog.run()
        path = dialog.get_filename()
        dialog.destroy()
        if response != Gtk.ResponseType.OK or not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Name", "ID", "Field", "Current", "Proposed"])
            for row in self.store:
                writer.writerow([
                    row[self._COL_NAME],
                    row[self._COL_ID],
                    row[self._COL_FIELD],
                    row[self._COL_CURRENT],
                    row[self._COL_PROPOSED],
                ])
        n_rows = len(self.store)
        self.set_status(f"Exported {n_rows} rows to {path}")

    def append_row(self, checked, name, gramps_id, field, current, proposed, handle, prefix, ftype):
        if not name:
            return
        self.store.append([checked, name, gramps_id, field, current, proposed, handle, prefix, ftype])

    def get_selected_findings(self):
        result = []
        for row in self.store:
            if row[self._COL_CHECKED]:
                result.append({
                    "handle":       row[self._COL_HANDLE],
                    "prefix_found": row[self._COL_PREFIX],
                    "field_type":   row[self._COL_FTYPE],
                    "proposed_value": row[self._COL_CURRENT][len(row[self._COL_PREFIX]) + 1:],
                })
        return result

    def select_all(self):
        for row in self.store:
            row[self._COL_CHECKED] = True

    def deselect_all(self):
        for row in self.store:
            row[self._COL_CHECKED] = False

    def _on_toggled(self, renderer, path):
        it = self.store.get_iter(Gtk.TreePath(path))
        self.store[it][self._COL_CHECKED] = not self.store[it][self._COL_CHECKED]

    def _row_activated(self, tree, path, column):
        it = self.store.get_iter(path)
        handle = self.store.get_value(it, self._COL_HANDLE)
        if handle and self._on_activate:
            self._on_activate(handle)


# ---------------------------------------------------------------------------
# Tab widget
# ---------------------------------------------------------------------------

class PrefixesTab(Gtk.Box):
    """
    Self-contained tab widget for surname prefix detection.

    Scans all persons for misplaced surname prefixes (e.g. "van" found in
    the given name or surname field instead of the dedicated prefix field).

    Threading strategy:
      _build_snapshot() runs on the main thread — extracts all required
      name data into plain Python dicts before the worker starts.
      _scan_fn() runs in the background thread — calls detect_issues()
      against the snapshot only, with no GRAMPS DB access.
    """

    def __init__(self, db_wrap, uistate):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(8)

        self.db_wrap = db_wrap
        self._uistate = uistate
        self._snapshot = None
        self._worker = None
        self._active_prefixes = prefs.get_prefix_list()

        self._build_toolbar()
        self.pack_start(self._build_prefix_panel(), False, False, 0)

        self._result_list = PreviewTable(on_activate=self._navigate_person)
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

        self._select_all_btn = Gtk.Button(label="Select All")
        self._select_all_btn.connect("clicked", lambda _: self._result_list.select_all())
        toolbar.pack_start(self._select_all_btn, False, False, 0)

        self._deselect_all_btn = Gtk.Button(label="Deselect All")
        self._deselect_all_btn.connect("clicked", lambda _: self._result_list.deselect_all())
        toolbar.pack_start(self._deselect_all_btn, False, False, 0)

        self._apply_btn = Gtk.Button(label="Apply Selected")
        self._apply_btn.connect("clicked", self._on_apply)
        toolbar.pack_start(self._apply_btn, False, False, 0)

        export_btn = Gtk.Button(label="Export CSV")
        export_btn.connect("clicked", self._on_export_csv)
        toolbar.pack_start(export_btn, False, False, 0)

        self.pack_start(toolbar, False, False, 0)

    def _build_prefix_panel(self):
        expander = Gtk.Expander(label="Prefix Settings")
        expander.set_expanded(False)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        inner.set_border_width(6)

        hint = Gtk.Label(label="Prefixes to detect (one per line, longest first):")
        hint.set_halign(Gtk.Align.START)
        inner.pack_start(hint, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_shadow_type(Gtk.ShadowType.IN)
        scroll.set_min_content_height(80)

        self._prefix_view = Gtk.TextView()
        self._prefix_view.set_wrap_mode(Gtk.WrapMode.WORD)
        self._prefix_view.get_buffer().set_text("\n".join(prefs.get_prefix_list()))
        scroll.add(self._prefix_view)

        inner.pack_start(scroll, True, True, 0)
        expander.add(inner)
        return expander

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_prefixes(self):
        """Read the prefix TextView and return a list of non-empty strings."""
        buf = self._prefix_view.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        return [line.strip() for line in text.splitlines() if line.strip()]

    # ------------------------------------------------------------------
    # Signal handlers (all run on the GTK main thread)
    # ------------------------------------------------------------------

    def _on_scan(self, btn):
        if self._worker is not None and self._worker.is_running():
            return

        self._result_list.clear()
        self._result_list.set_status("Reading database\u2026")

        # Build snapshot on the main thread — GRAMPS SQLite restriction
        self._snapshot = _build_snapshot(self.db_wrap)

        # Capture prefix list on the main thread
        self._active_prefixes = self._get_prefixes()

        self._scan_btn.set_sensitive(False)
        self._cancel_btn.set_sensitive(True)
        self._apply_btn.set_sensitive(False)
        self._result_list.set_status("Scanning\u2026")

        self._worker = ScanWorker(self._result_list, self._scan_fn, None)
        self._worker.start()
        GLib.timeout_add(200, self._check_done)

    def _on_cancel(self, btn):
        if self._worker:
            self._worker.cancel()
        self._cancel_btn.set_sensitive(False)

    def _on_export_csv(self, btn):
        self._result_list.export_csv(parent_window=self.get_toplevel())

    def _on_apply(self, btn):
        """Write checked corrections to the GRAMPS database inside a single DbTxn."""
        findings = self._result_list.get_selected_findings()
        if not findings:
            self._result_list.set_status("No rows selected.")
            return

        db = self.db_wrap.db
        with DbTxn("Fix name prefixes", db) as trans:
            for f in findings:
                person = db.get_person_from_handle(f["handle"])
                if person is None:
                    continue
                name_obj = person.get_primary_name()
                surname_list = name_obj.get_surname_list()
                if not surname_list:
                    continue
                sn_obj = surname_list[0]

                if f["field_type"] == "given":
                    name_obj.set_first_name(f["proposed_value"])
                    sn_obj.set_prefix(f["prefix_found"])
                else:  # "surname"
                    sn_obj.set_surname(f["proposed_value"])
                    sn_obj.set_prefix(f["prefix_found"])

                db.commit_person(person, trans)

        count = len(findings)
        self._result_list.set_status(
            f"{count} correction(s) applied \u2014 use Edit \u203a Undo to reverse"
        )

    def _check_done(self):
        if self._worker is not None and self._worker.is_running():
            return True  # keep polling
        self._scan_btn.set_sensitive(True)
        self._cancel_btn.set_sensitive(False)
        self._apply_btn.set_sensitive(True)
        return False

    def _navigate_person(self, handle):
        """Navigate the GRAMPS main window to the given person."""
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

        Calls detect_issues() against self._snapshot (plain Python only).
        Must not access self.db_wrap or any GRAMPS object.
        """
        findings = detect_issues(self._snapshot, self._active_prefixes)

        if not findings:
            yield (False, "", "", "", "", "", "", "", ""), "No prefix issues found."
            return

        total = len(findings)
        status = f"{total} prefix issue(s) found"

        for i, f in enumerate(findings):
            field_label = "Given name" if f["field_type"] == "given" else "Surname"
            proposed_str = f"'{f['proposed_value']}'  \u2022  prefix: {f['prefix_found']}"
            row = (
                True,
                f["name"],
                f["gramps_id"],
                field_label,
                f["current_value"],
                proposed_str,
                f["handle"],
                f["prefix_found"],
                f["field_type"],
            )
            s = status if i == len(findings) - 1 else ""
            yield row, s
