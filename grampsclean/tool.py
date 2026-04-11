"""GrampsClean — main tool class and options stub."""

import os
import sys

# GRAMPS loads tool.py as a top-level module (not inside a package), so we
# add the grampsclean/ directory to sys.path to allow sibling-module imports.
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from gramps.gui.plug import tool, MenuToolOptions
from gramps.gui.managedwindow import ManagedWindow

from widgets import ResultList
from db import GrampsDb
from worker import ScanWorker  # noqa: F401 — imported here for future tab use
from tab_islands import IslandTab
from tab_missing import MissingTab
from tab_impossibilities import ImpossibilitiesTab


# Placeholder tabs for tools not yet implemented (Phase 5)
PLACEHOLDER_TABS = [
    ("Name Prefixes", [("Name", 0), ("ID", 1), ("Suggestion", 2)]),
]


class GrampsCleanOptions(MenuToolOptions):
    """Stub options class — no configurable options at this stage."""

    def __init__(self, name, person_id=None, dbstate=None):
        MenuToolOptions.__init__(self, name, person_id, dbstate)

    def add_menu_options(self, menu):
        pass  # No options yet; populated in later phases


class GrampsCleanTool(tool.Tool, ManagedWindow):
    """
    GrampsClean data quality audit tool.

    Opens a tabbed window hosting four data quality tools:
    Island Detection, Missing Data Finder, Impossibilities Checker,
    and Name Prefix Corrector.
    """

    def __init__(self, dbstate, user, options_class, name, callback=None):
        uistate = user.uistate
        ManagedWindow.__init__(self, uistate, [], self.__class__)
        tool.Tool.__init__(self, dbstate, options_class, name)
        self.db_wrap = GrampsDb(self.db)
        self._build_window()
        self.show()

    # ------------------------------------------------------------------
    # Window construction
    # ------------------------------------------------------------------

    def _build_window(self):
        """Build the tabbed main window."""
        window = Gtk.Window()

        # Root container
        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Notebook with one tab per tool
        self.notebook = Gtk.Notebook()
        self.notebook.set_tab_pos(Gtk.PositionType.TOP)

        # Tab 0: Island Detection (fully implemented)
        island_tab = IslandTab(self.db_wrap, self.uistate)
        self.notebook.append_page(island_tab, Gtk.Label(label="Island Detection"))

        # Tab 1: Missing Data Finder (Phase 3)
        missing_tab = MissingTab(self.db_wrap, self.uistate)
        self.notebook.append_page(missing_tab, Gtk.Label(label="Missing Data"))

        # Tab 2: Impossibilities Checker (Phase 4)
        impossibilities_tab = ImpossibilitiesTab(self.db_wrap, self.uistate)
        self.notebook.append_page(impossibilities_tab, Gtk.Label(label="Impossibilities"))

        # Tab 3: placeholder until Phase 5
        for tab_label, columns in PLACEHOLDER_TABS:
            result_list = ResultList(columns)
            result_list.set_border_width(8)
            self.notebook.append_page(result_list, Gtk.Label(label=tab_label))

        root_box.pack_start(self.notebook, True, True, 0)

        # Button bar
        button_bar = Gtk.Box(spacing=6)
        button_bar.set_border_width(8)

        close_btn = Gtk.Button(label="Close")
        close_btn.connect("clicked", self.close)
        button_bar.pack_end(close_btn, False, False, 0)

        root_box.pack_start(button_bar, False, False, 0)

        window.add(root_box)

        self.set_window(window, None, "GrampsClean \u2014 Data Quality Tools")
        self.setup_configs("interface.grampsclean", 900, 600)

    # ------------------------------------------------------------------
    # ManagedWindow interface
    # ------------------------------------------------------------------

    def build_menu_names(self, obj):
        """Return menu label pair required by ManagedWindow."""
        return ("GrampsClean", "GrampsClean")

    def close(self, *args):
        """Close the window and deregister from ManagedWindow."""
        ManagedWindow.close(self)
