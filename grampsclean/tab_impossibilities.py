"""GrampsClean — Impossibilities Checker tab widget.

Threading strategy:
  All GRAMPS DB access happens on the main thread (SQLite restriction).
  _build_snapshot() collects all person/family data into plain Python dicts.
  The worker thread calls run_rules() which is pure Python — no DB access.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from gramps.gen.lib import EventType

from worker import ScanWorker

# Default thresholds — Phase 04-02 adds configuration UI to override these
DEFAULT_THRESHOLDS = {
    "father_postdeath_years": 1,  # flag if child born >1yr after father's death
    "mother_min_age": 12,         # min mother age at child's birth (Warning)
    "father_min_age": 13,         # min father age at child's birth (Warning)
    "mother_max_age": 60,         # max mother age at child's birth (Warning)
    "father_max_age": 90,         # max father age at child's birth (Warning)
}


# ---------------------------------------------------------------------------
# Date helpers (main-thread only)
# ---------------------------------------------------------------------------

def _date_tuple(date_obj):
    """Convert a GRAMPS Date object to (year, month, day) or None.

    Returns None if the date is absent, non-regular, or has no year.
    month and day are 0 when not set (year-only dates).
    Must only be called on the main thread during snapshot building.
    """
    if date_obj is None:
        return None
    try:
        if not date_obj.is_regular():
            return None
        year = date_obj.get_year()
        if not year:
            return None
        month = date_obj.get_month() or 0
        day = date_obj.get_day() or 0
        return (year, month, day)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Snapshot builder (must run on the main thread)
# ---------------------------------------------------------------------------

def _build_snapshot(db_wrap):
    """Build a plain-Python snapshot of all data needed for impossibility checks.

    Must be called on the main thread — accesses GRAMPS SQLite connections.
    Returns a dict with "persons" and "families" sub-dicts containing only
    plain Python types (str, int, tuple, list, bool, None).  No GRAMPS objects
    are stored in the snapshot.
    """
    persons = {}
    for person in db_wrap.iter_people():
        handle = person.get_handle()

        birth_date = None
        death_date = None
        burial_date = None
        birth_count = 0
        death_count = 0
        life_event_dates = []

        for ref in person.get_event_ref_list():
            event = db_wrap.get_event_from_handle(ref.ref)
            if event is None:
                continue
            etype = event.get_type()
            raw_date = event.get_date_object()
            dt = _date_tuple(raw_date)

            if etype == EventType.BIRTH:
                birth_count += 1
                if birth_date is None:
                    birth_date = dt
            elif etype == EventType.DEATH:
                death_count += 1
                if death_date is None:
                    death_date = dt
            elif etype in (EventType.BURIAL, EventType.CREMATION):
                if burial_date is None:
                    burial_date = dt
            else:
                if dt is not None:
                    life_event_dates.append(dt)

        persons[handle] = {
            "name": db_wrap.format_name(person),
            "gramps_id": db_wrap.get_gramps_id(person),
            "birth": birth_date,
            "death": death_date,
            "burial": burial_date,
            "birth_count": birth_count,
            "death_count": death_count,
            "life_event_dates": life_event_dates,
            # families where this person is a parent (spouse)
            "parent_family_handles": list(person.get_family_handle_list()),
            # families where this person is a child
            "child_family_handles": list(person.get_parent_family_handle_list()),
        }

    families = {}
    for family in db_wrap.iter_families():
        handle = family.get_handle()

        marriage_date = None
        divorce_date = None

        for ref in family.get_event_ref_list():
            event = db_wrap.get_event_from_handle(ref.ref)
            if event is None:
                continue
            etype = event.get_type()
            raw_date = event.get_date_object()
            dt = _date_tuple(raw_date)

            if etype == EventType.MARRIAGE and marriage_date is None:
                marriage_date = dt
            elif etype == EventType.DIVORCE and divorce_date is None:
                divorce_date = dt

        families[handle] = {
            "gramps_id": family.get_gramps_id() or "",
            "father_handle": family.get_father_handle(),
            "mother_handle": family.get_mother_handle(),
            "child_handles": [ref.ref for ref in family.get_child_ref_list()],
            "marriage": marriage_date,
            "divorce": divorce_date,
        }

    return {"persons": persons, "families": families}


# ---------------------------------------------------------------------------
# Rule engine helpers (pure Python — safe for background thread)
# ---------------------------------------------------------------------------

def _before(a, b):
    """Return True if date tuple a is definitively before date tuple b.

    Uses the finest precision both dates share:
      both have day → (year, month, day) comparison
      both have month → (year, month) comparison
      otherwise → year-only comparison
    Returns False if either date is None.
    """
    if a is None or b is None:
        return False
    if a[1] and b[1]:
        if a[2] and b[2]:
            return a < b
        return (a[0], a[1]) < (b[0], b[1])
    return a[0] < b[0]


def _overlaps(f1, f2):
    """Return True if two family marriage periods may overlap.

    Two families definitively do NOT overlap only if f1 has a recorded
    divorce before f2's marriage starts (or vice versa).  When in doubt,
    assumes possible overlap (conservative — produces Warning, not Error).
    """
    if not f1["marriage"] or not f2["marriage"]:
        return False  # can't determine overlap without marriage dates

    # Put the earlier marriage first
    if _before(f2["marriage"], f1["marriage"]):
        f1, f2 = f2, f1

    # f1 is earlier. If f1 has a divorce before f2 married, no overlap.
    if f1["divorce"] and _before(f1["divorce"], f2["marriage"]):
        return False

    return True


def _has_cycle(start_handle, persons, families):
    """Return True if start_handle appears in their own ancestry chain.

    Iterative DFS from start_handle upward through the parent chain.
    Visits at most MAX_DEPTH levels to avoid hangs on genuinely circular data.
    """
    MAX_DEPTH = 50
    visited = set()

    p = persons.get(start_handle)
    if p is None:
        return False

    stack = []  # (person_handle, depth)
    for cfh in p["child_family_handles"]:
        fam = families.get(cfh)
        if fam:
            for phd in (fam["father_handle"], fam["mother_handle"]):
                if phd and phd not in visited:
                    stack.append((phd, 1))
                    visited.add(phd)

    while stack:
        current, depth = stack.pop()
        if current == start_handle:
            return True  # found ourselves in our own ancestry
        if depth >= MAX_DEPTH:
            continue
        cp = persons.get(current)
        if cp is None:
            continue
        for cfh in cp["child_family_handles"]:
            fam = families.get(cfh)
            if fam:
                for phd in (fam["father_handle"], fam["mother_handle"]):
                    if phd and phd not in visited:
                        stack.append((phd, depth + 1))
                        visited.add(phd)

    return False


# ---------------------------------------------------------------------------
# Rule engine (pure Python — runs in background thread via ScanWorker)
# ---------------------------------------------------------------------------

def run_rules(snapshot, thresholds):
    """Run all 15 impossibility rules against the snapshot.

    Rules:
      R01 death-before-birth          Error
      R02 burial-before-death         Error
      R03 duplicate-birth             Error
      R04 duplicate-death             Error
      R05 event-before-birth          Warning
      R06 event-after-death           Warning
      R07 child-before-parent-born    Error
      R08 child-after-father-death    Error
      R09 child-after-mother-death    Error
      R10 parent-too-young            Warning
      R11 parent-too-old              Warning
      R12 marriage-before-spouse-born Error
      R13 marriage-after-spouse-death Error
      R14 overlapping-marriages       Warning
      R15 circular-ancestry           Error

    Must not access GRAMPS DB — snapshot only.
    Returns a list of finding dicts sorted by rule_id then person name.
    """
    persons = snapshot["persons"]
    families = snapshot["families"]
    findings = []

    def add(person_handle, family_handle, rule_id, rule_name, severity, detail):
        findings.append({
            "person_handle": person_handle,
            "family_handle": family_handle,
            "rule_id": rule_id,
            "rule_name": rule_name,
            "severity": severity,
            "detail": detail,
        })

    # -------------------------------------------------------------------
    # Person-level rules (R01–R06)
    # -------------------------------------------------------------------
    for handle, p in persons.items():
        birth = p["birth"]
        death = p["death"]
        burial = p["burial"]

        # R01: Death before birth
        if death and birth and _before(death, birth):
            add(handle, None, "R01", "Death before birth", "Error",
                f"Death {death[0]} before birth {birth[0]}")

        # R02: Burial/cremation before death
        if burial and death and _before(burial, death):
            add(handle, None, "R02", "Burial before death", "Error",
                f"Burial {burial[0]} before death {death[0]}")

        # R03: Duplicate birth events
        if p["birth_count"] > 1:
            add(handle, None, "R03", "Duplicate birth events", "Error",
                f"{p['birth_count']} birth events recorded")

        # R04: Duplicate death events
        if p["death_count"] > 1:
            add(handle, None, "R04", "Duplicate death events", "Error",
                f"{p['death_count']} death events recorded")

        # R05: Life event before birth
        if birth:
            early = [d for d in p["life_event_dates"] if _before(d, birth)]
            if early:
                add(handle, None, "R05", "Event date before birth", "Warning",
                    f"{len(early)} event(s) predate birth {birth[0]}")

        # R06: Life event after death
        if death:
            late = [d for d in p["life_event_dates"] if _before(death, d)]
            if late:
                add(handle, None, "R06", "Event date after death", "Warning",
                    f"{len(late)} event(s) postdate death {death[0]}")

    # -------------------------------------------------------------------
    # Family-level rules (R07–R13)
    # -------------------------------------------------------------------
    for fam_handle, fam in families.items():
        father = persons.get(fam["father_handle"]) if fam["father_handle"] else None
        mother = persons.get(fam["mother_handle"]) if fam["mother_handle"] else None
        marriage = fam["marriage"]

        for child_handle in fam["child_handles"]:
            child = persons.get(child_handle)
            if child is None:
                continue
            child_birth = child["birth"]
            child_year = child_birth[0] if child_birth else None

            # R07: Child born before parent born
            for plabel, parent in (("father", father), ("mother", mother)):
                if parent and child_birth and parent["birth"]:
                    if _before(child_birth, parent["birth"]):
                        add(child_handle, fam_handle,
                            "R07", "Child born before parent", "Error",
                            f"Child born {child_birth[0]}, {plabel} born {parent['birth'][0]}")

            # R08: Child born after father's death (>threshold years)
            if father and child_year and father["death"]:
                father_death_year = father["death"][0]
                limit = thresholds.get("father_postdeath_years", 1)
                if child_year > father_death_year + limit:
                    add(child_handle, fam_handle,
                        "R08", "Child born after father's death", "Error",
                        f"Child born {child_year}, father died {father_death_year}")

            # R09: Child born after mother's death
            if mother and child_birth and mother["death"]:
                if _before(mother["death"], child_birth):
                    add(child_handle, fam_handle,
                        "R09", "Child born after mother's death", "Error",
                        f"Child born {child_birth[0]}, mother died {mother['death'][0]}")

            # R10: Parent too young at child's birth
            if child_year:
                for plabel, parent, min_key, default_min in (
                    ("Mother", mother, "mother_min_age", 12),
                    ("Father", father, "father_min_age", 13),
                ):
                    if parent and parent["birth"]:
                        age = child_year - parent["birth"][0]
                        if age < thresholds.get(min_key, default_min):
                            add(child_handle, fam_handle,
                                "R10", "Parent too young at child's birth", "Warning",
                                f"{plabel} ~{age} yrs old at child's birth {child_year}")

            # R11: Parent implausibly old at child's birth
            if child_year:
                for plabel, parent, max_key, default_max in (
                    ("Mother", mother, "mother_max_age", 60),
                    ("Father", father, "father_max_age", 90),
                ):
                    if parent and parent["birth"]:
                        age = child_year - parent["birth"][0]
                        if age > thresholds.get(max_key, default_max):
                            add(child_handle, fam_handle,
                                "R11", "Parent implausibly old at child's birth", "Warning",
                                f"{plabel} ~{age} yrs old at child's birth {child_year}")

        # R12: Marriage before birth of spouse
        if marriage:
            for plabel, parent, phd in (
                ("father", father, fam["father_handle"]),
                ("mother", mother, fam["mother_handle"]),
            ):
                if parent and parent["birth"] and _before(marriage, parent["birth"]):
                    add(phd, fam_handle,
                        "R12", "Marriage before birth of spouse", "Error",
                        f"Marriage {marriage[0]} before {plabel} born {parent['birth'][0]}")

        # R13: Marriage after death of spouse
        if marriage:
            for plabel, parent, phd in (
                ("father", father, fam["father_handle"]),
                ("mother", mother, fam["mother_handle"]),
            ):
                if parent and parent["death"] and _before(parent["death"], marriage):
                    add(phd, fam_handle,
                        "R13", "Marriage after death of spouse", "Error",
                        f"Marriage {marriage[0]} after {plabel} died {parent['death'][0]}")

    # -------------------------------------------------------------------
    # R14: Overlapping marriages
    # -------------------------------------------------------------------
    for handle, p in persons.items():
        fams = [
            families[fh] for fh in p["parent_family_handles"]
            if fh in families and families[fh]["marriage"]
        ]
        if len(fams) < 2:
            continue

        found_overlap = False
        for i in range(len(fams)):
            for j in range(i + 1, len(fams)):
                if _overlaps(fams[i], fams[j]):
                    found_overlap = True
                    break
            if found_overlap:
                break

        if found_overlap:
            fam_ids = ", ".join(f["gramps_id"] for f in fams[:3])
            if len(fams) > 3:
                fam_ids += f", +{len(fams) - 3} more"
            add(handle, None, "R14", "Overlapping marriages", "Warning",
                f"Simultaneous marriages in: {fam_ids}")

    # -------------------------------------------------------------------
    # R15: Circular ancestry
    # -------------------------------------------------------------------
    for handle in persons:
        if _has_cycle(handle, persons, families):
            add(handle, None, "R15", "Circular ancestry", "Error",
                "Person appears in their own ancestry chain")

    # Sort by rule_id, then person name for consistent display
    findings.sort(
        key=lambda f: (f["rule_id"], persons.get(f["person_handle"], {}).get("name", ""))
    )
    return findings


# ---------------------------------------------------------------------------
# Grouped result view
# ---------------------------------------------------------------------------

class GroupedResultView(Gtk.Box):
    """TreeView-based result widget that groups findings under rule-name headers.

    Provides the same public API as ResultList (clear, set_status, append_row)
    so ScanWorker drives it unchanged.
    """

    # TreeStore column indices
    _COL_DISPLAY  = 0   # rule_name for parent; person_name for child
    _COL_ID       = 1   # empty for parent; person GRAMPS ID for child
    _COL_SEVERITY = 2   # empty for parent; "Error"/"Warning" for child
    _COL_DETAIL   = 3   # empty for parent; finding detail string for child
    _COL_HANDLE   = 4   # empty for parent; person_handle for child (hidden)
    _COL_COLOR    = 5   # "" for parent (default); "#cc0000"/"#c07000" for child
    _COL_WEIGHT   = 6   # 700 (bold) for parent; 400 (normal) for child

    _STATUS_DEFAULT = "Ready."

    def __init__(self, on_activate=None):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=4)

        self._on_activate = on_activate
        self._rule_iters = {}   # rule_name -> TreeIter
        self._rule_counts = {}  # rule_name -> int

        # TreeStore: str, str, str, str, str, str, int
        self.store = Gtk.TreeStore(str, str, str, str, str, str, int)

        self.tree = Gtk.TreeView(model=self.store)
        self.tree.set_enable_search(False)
        self.tree.connect("row-activated", self._row_activated)

        # "Rule / Name" column — bold for parent rows, colour for child rows
        renderer_name = Gtk.CellRendererText()
        col0 = Gtk.TreeViewColumn("Rule / Name", renderer_name,
                                  text=self._COL_DISPLAY,
                                  foreground=self._COL_COLOR,
                                  weight=self._COL_WEIGHT)
        col0.set_min_width(200)
        col0.set_resizable(True)
        self.tree.append_column(col0)

        # "ID" column
        renderer_id = Gtk.CellRendererText()
        col1 = Gtk.TreeViewColumn("ID", renderer_id, text=self._COL_ID)
        col1.set_min_width(80)
        col1.set_resizable(True)
        self.tree.append_column(col1)

        # "Severity" column — colour matches child row colour
        renderer_sev = Gtk.CellRendererText()
        col2 = Gtk.TreeViewColumn("Severity", renderer_sev,
                                  text=self._COL_SEVERITY,
                                  foreground=self._COL_COLOR)
        col2.set_min_width(80)
        col2.set_resizable(True)
        self.tree.append_column(col2)

        # "Detail" column
        renderer_detail = Gtk.CellRendererText()
        col3 = Gtk.TreeViewColumn("Detail", renderer_detail, text=self._COL_DETAIL)
        col3.set_min_width(200)
        col3.set_resizable(True)
        self.tree.append_column(col3)

        # Scrolled window containing the tree
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_shadow_type(Gtk.ShadowType.IN)
        scroll.add(self.tree)
        self.pack_start(scroll, True, True, 0)

        # Status label below the tree
        self.status_label = Gtk.Label(label=self._STATUS_DEFAULT)
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_margin_start(4)
        self.status_label.set_margin_bottom(4)
        self.pack_start(self.status_label, False, False, 0)

    # ------------------------------------------------------------------
    # Public API (same surface as ResultList)
    # ------------------------------------------------------------------

    def clear(self):
        self.store.clear()
        self._rule_iters = {}
        self._rule_counts = {}
        self.status_label.set_text(self._STATUS_DEFAULT)

    def set_status(self, text):
        self.status_label.set_text(text)

    def append_row(self, name, gramps_id, rule_name, severity, detail="", handle=""):
        """Add a finding under its rule-name parent group.

        Called via GLib.idle_add from ScanWorker — runs on the GTK main thread.
        Guard on rule_name handles the empty sentinel from the no-findings yield.
        """
        if not rule_name:
            return  # empty sentinel (no-findings yield)

        # Create parent row on first finding for this rule
        if rule_name not in self._rule_iters:
            parent_iter = self.store.append(None, [rule_name, "", "", "", "", "", 700])
            self._rule_iters[rule_name] = parent_iter
            self._rule_counts[rule_name] = 0

        parent_iter = self._rule_iters[rule_name]
        self._rule_counts[rule_name] += 1
        count = self._rule_counts[rule_name]

        # Update parent label with running count
        self.store.set_value(parent_iter, 0, f"{rule_name} ({count})")

        # Colour by severity
        color = "#cc0000" if severity == "Error" else "#c07000"

        # Append child row
        self.store.append(parent_iter, [name, gramps_id, severity, detail, handle, color, 400])

        # Expand parent so child is immediately visible
        self.tree.expand_row(self.store.get_path(parent_iter), False)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _row_activated(self, tree, path, column):
        model = tree.get_model()
        it = model.get_iter(path)
        handle = model.get_value(it, self._COL_HANDLE)
        if handle and self._on_activate:
            self._on_activate(handle)


# ---------------------------------------------------------------------------
# Tab widget
# ---------------------------------------------------------------------------

class ImpossibilitiesTab(Gtk.Box):
    """
    Self-contained tab widget for genealogical impossibilities detection.

    Scans all persons and families for 15 rules covering chronological
    impossibilities and relational inconsistencies.

    Threading strategy:
      _build_snapshot() runs on the main thread — extracts all required
      data into plain Python dicts before the worker starts.
      _scan_fn() runs in the background thread — calls run_rules() against
      the snapshot only, with no GRAMPS DB access.
    """

    def __init__(self, db_wrap, uistate):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.set_border_width(8)

        self.db_wrap = db_wrap
        self._uistate = uistate
        self._snapshot = None
        self._worker = None
        self._active_thresholds = dict(DEFAULT_THRESHOLDS)

        self._build_toolbar()
        self.pack_start(self._build_config_panel(), False, False, 0)
        self._result_list = GroupedResultView(on_activate=self._navigate_person)
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

        self.pack_start(toolbar, False, False, 0)

    def _build_config_panel(self):
        expander = Gtk.Expander(label="Threshold Settings")
        expander.set_expanded(False)

        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(4)
        grid.set_border_width(6)

        rows = [
            ("Father post-death birth window (years):", "father_postdeath_years", 0, 5),
            ("Mother minimum age at birth:",             "mother_min_age",         8, 20),
            ("Father minimum age at birth:",             "father_min_age",         8, 20),
            ("Mother maximum age at birth:",             "mother_max_age",        35, 80),
            ("Father maximum age at birth:",             "father_max_age",        50, 120),
        ]

        self._threshold_spins = {}
        for row_idx, (label_text, key, lo, hi) in enumerate(rows):
            label = Gtk.Label(label=label_text)
            label.set_halign(Gtk.Align.END)

            adj = Gtk.Adjustment(
                value=DEFAULT_THRESHOLDS[key],
                lower=lo, upper=hi,
                step_increment=1, page_increment=5, page_size=0,
            )
            spin = Gtk.SpinButton(adjustment=adj, climb_rate=1, digits=0)
            spin.set_numeric(True)
            spin.set_update_policy(Gtk.SpinButtonUpdatePolicy.IF_VALID)

            grid.attach(label, 0, row_idx, 1, 1)
            grid.attach(spin,  1, row_idx, 1, 1)
            self._threshold_spins[key] = spin

        expander.add(grid)
        return expander

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

        # Capture threshold spinbutton values on the main thread
        self._active_thresholds = {
            key: int(spin.get_value())
            for key, spin in self._threshold_spins.items()
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
            return True  # keep polling
        self._scan_btn.set_sensitive(True)
        self._cancel_btn.set_sensitive(False)
        return False

    def _navigate_person(self, handle):
        """
        Navigate the GRAMPS main window to the given person.

        Follows the same pattern as IslandTab and MissingTab (02-03, 03-02).
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

        Calls run_rules() against self._snapshot (plain Python only).
        Must not access self.db_wrap or any GRAMPS object.
        """
        snap = self._snapshot
        persons = snap["persons"]

        findings = run_rules(snap, self._active_thresholds)

        if not findings:
            yield ("", "", "", ""), "No impossibilities found."
            return

        total = len(findings)
        errors = sum(1 for f in findings if f["severity"] == "Error")
        warnings = total - errors
        status = f"{total} issues found ({errors} errors, {warnings} warnings)"

        for i, f in enumerate(findings):
            p = persons.get(f["person_handle"], {})
            row = (
                p.get("name", "[Unknown]"),
                p.get("gramps_id", ""),
                f["rule_name"],
                f["severity"],
                f.get("detail", ""),
                f["person_handle"],
            )
            s = status if i == len(findings) - 1 else ""
            yield row, s
