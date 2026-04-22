"""GrampsSearch — main tool class.

Opens a side-by-side search window that fetches candidate matches
from Dutch archive APIs and lets the user merge approved data into
the GRAMPS database.
"""

import os
import sys

# GRAMPS loads tool.py as a top-level module, so add the plugin dir
# to sys.path to allow sibling-module imports.
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gui.plug import tool, MenuToolOptions
from gramps.gui.managedwindow import ManagedWindow

from db import GrampsDb
from matcher import filter_and_rank
from ui import SearchBox
from api import (  # noqa: F401
    OpenArchievenClient,
    AlleGroningersClient,
    GenealogieOnlineClient,
    CachedConnector,
)
import prefs  # registers config keys at import time

_ = glocale.translation.gettext


class GrampsSearchOptions(MenuToolOptions):
    """Stub options class — no configurable options yet."""

    def __init__(self, name, person_id=None, dbstate=None):
        MenuToolOptions.__init__(self, name, person_id, dbstate)

    def add_menu_options(self, menu):
        pass


class GrampsSearchTool(tool.Tool, ManagedWindow):
    def __init__(self, dbstate, user, options_class, name, callback=None):
        uistate = user.uistate
        ManagedWindow.__init__(self, uistate, [], self.__class__)
        tool.Tool.__init__(self, dbstate, options_class, name)

        self.db_wrap = GrampsDb(self.db)
        self.connectors = self._build_connectors()
        self._build_window()
        self.show()

    # ------------------------------------------------------------------

    def _build_connectors(self):
        enabled = prefs.get_enabled_sources()
        raw = []
        if prefs.SOURCE_OPENARCH in enabled:
            raw.append(OpenArchievenClient())
        if prefs.SOURCE_ALLEGRONINGERS in enabled:
            raw.append(AlleGroningersClient())
        if prefs.SOURCE_GENEALOGIEONLINE in enabled:
            raw.append(GenealogieOnlineClient())

        if not prefs.get_cache_enabled():
            return raw
        ttl = prefs.get_cache_ttl_seconds()
        return [CachedConnector(c, ttl_seconds=ttl) for c in raw]

    def _build_window(self):
        window = Gtk.Window()

        people = list(self.db_wrap.iter_people_missing_core_events())

        self.search_box = SearchBox(
            db=self.db_wrap,
            matcher_fn=filter_and_rank,
            connectors=self.connectors,
            person_iter=people,
        )
        window.add(self.search_box)

        self.set_window(window, None, _("GrampsSearch — Find Missing Data"))
        self.setup_configs("interface.grampssearch", 1000, 650)

    def build_menu_names(self, obj):
        return ("GrampsSearch", "GrampsSearch")
