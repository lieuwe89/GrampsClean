"""GrampsSearch — Preferences dialog and GRAMPS config registration.

Config keys are registered at module import time. Sibling modules that
need a setting call the `get_*` helpers after importing this module.

Keys cover: cache (enabled + TTL), debug log toggle, per-source on/off.
GenealogieOnline is a public JSON endpoint — no creds needed.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from gramps.gen import config as grampsconfig


# ---------------------------------------------------------------------------
# Config registration — runs at module import time
# ---------------------------------------------------------------------------

grampsconfig.register("grampssearch.cache_enabled",      True)
grampsconfig.register("grampssearch.cache_ttl_days",     30)
grampsconfig.register("grampssearch.debug_log_enabled",  True)

grampsconfig.register("grampssearch.use_openarchieven",   True)
grampsconfig.register("grampssearch.use_allegroningers",  True)
grampsconfig.register("grampssearch.use_genealogieonline", True)


# Source identifiers used across the codebase (connector.source_name).
SOURCE_OPENARCH      = "openarchieven"
SOURCE_ALLEGRONINGERS = "allegroningers"
SOURCE_GENEALOGIEONLINE = "genealogieonline"


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_cache_enabled() -> bool:
    return bool(grampsconfig.get("grampssearch.cache_enabled"))


def get_cache_ttl_seconds() -> int:
    days = int(grampsconfig.get("grampssearch.cache_ttl_days"))
    return max(1, days) * 24 * 60 * 60


def get_debug_log_enabled() -> bool:
    return bool(grampsconfig.get("grampssearch.debug_log_enabled"))


def get_enabled_sources() -> set:
    out = set()
    if bool(grampsconfig.get("grampssearch.use_openarchieven")):
        out.add(SOURCE_OPENARCH)
    if bool(grampsconfig.get("grampssearch.use_allegroningers")):
        out.add(SOURCE_ALLEGRONINGERS)
    if bool(grampsconfig.get("grampssearch.use_genealogieonline")):
        out.add(SOURCE_GENEALOGIEONLINE)
    return out


# ---------------------------------------------------------------------------
# Preferences dialog
# ---------------------------------------------------------------------------

class PreferencesDialog(Gtk.Dialog):
    """Dialog for editing GrampsSearch preferences."""

    def __init__(self, parent=None):
        Gtk.Dialog.__init__(
            self,
            title="GrampsSearch Preferences",
            transient_for=parent,
            modal=True,
            destroy_with_parent=True,
        )
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        ok_btn = self.add_button("OK", Gtk.ResponseType.OK)
        ok_btn.get_style_context().add_class("suggested-action")
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_default_size(480, 520)

        content = self.get_content_area()
        content.set_spacing(0)

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main.set_border_width(12)
        content.pack_start(main, True, True, 0)

        # --- Cache ---
        main.pack_start(self._section_label("API Cache"), False, False, 0)
        cache_grid = self._make_grid()
        self._chk_cache = Gtk.CheckButton(label="Cache API responses on disk")
        self._chk_cache.set_active(get_cache_enabled())
        cache_grid.attach(self._chk_cache, 0, 0, 2, 1)

        lbl_ttl = Gtk.Label(label="Cache TTL (days):")
        lbl_ttl.set_halign(Gtk.Align.END)
        self._spin_ttl = Gtk.SpinButton.new_with_range(1, 365, 1)
        self._spin_ttl.set_value(int(grampsconfig.get("grampssearch.cache_ttl_days")))
        cache_grid.attach(lbl_ttl,        0, 1, 1, 1)
        cache_grid.attach(self._spin_ttl, 1, 1, 1, 1)
        main.pack_start(cache_grid, False, False, 0)

        main.pack_start(Gtk.Separator(), False, False, 4)

        # --- Logging ---
        main.pack_start(self._section_label("Logging"), False, False, 0)
        log_grid = self._make_grid()
        self._chk_debug = Gtk.CheckButton(
            label="Write ~/Documents/grampssearch-debug.log during scans"
        )
        self._chk_debug.set_active(get_debug_log_enabled())
        log_grid.attach(self._chk_debug, 0, 0, 2, 1)
        main.pack_start(log_grid, False, False, 0)

        main.pack_start(Gtk.Separator(), False, False, 4)

        # --- Sources ---
        main.pack_start(self._section_label("Sources"), False, False, 0)
        src_grid = self._make_grid()
        self._chk_openarch = Gtk.CheckButton(label="Open Archieven (public)")
        self._chk_openarch.set_active(
            bool(grampsconfig.get("grampssearch.use_openarchieven"))
        )
        self._chk_allegron = Gtk.CheckButton(label="AlleGroningers (Memorix)")
        self._chk_allegron.set_active(
            bool(grampsconfig.get("grampssearch.use_allegroningers"))
        )
        self._chk_gonline = Gtk.CheckButton(label="GenealogieOnline (public JSON search)")
        self._chk_gonline.set_active(
            bool(grampsconfig.get("grampssearch.use_genealogieonline"))
        )
        src_grid.attach(self._chk_openarch, 0, 0, 2, 1)
        src_grid.attach(self._chk_allegron, 0, 1, 2, 1)
        src_grid.attach(self._chk_gonline,  0, 2, 2, 1)
        main.pack_start(src_grid, False, False, 0)

        self.show_all()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _section_label(self, text):
        lbl = Gtk.Label()
        lbl.set_markup(f"<b>{text}</b>")
        lbl.set_halign(Gtk.Align.START)
        return lbl

    def _make_grid(self):
        g = Gtk.Grid()
        g.set_column_spacing(12)
        g.set_row_spacing(4)
        g.set_margin_start(12)
        return g

    # ------------------------------------------------------------------

    def run(self):
        response = Gtk.Dialog.run(self)
        if response == Gtk.ResponseType.OK:
            self._save()
        return response

    def _save(self):
        grampsconfig.set("grampssearch.cache_enabled",
                         bool(self._chk_cache.get_active()))
        grampsconfig.set("grampssearch.cache_ttl_days",
                         int(self._spin_ttl.get_value()))
        grampsconfig.set("grampssearch.debug_log_enabled",
                         bool(self._chk_debug.get_active()))

        grampsconfig.set("grampssearch.use_openarchieven",
                         bool(self._chk_openarch.get_active()))
        grampsconfig.set("grampssearch.use_allegroningers",
                         bool(self._chk_allegron.get_active()))
        grampsconfig.set("grampssearch.use_genealogieonline",
                         bool(self._chk_gonline.get_active()))
