"""GrampsClean — Preferences dialog and GRAMPS config registration.

Config keys are registered at module import time so any sibling module
can safely call get_*() helpers after importing this module.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from gramps.gen import config as grampsconfig


# ---------------------------------------------------------------------------
# Config registration — runs at module import time
# ---------------------------------------------------------------------------

_PREFIX_DEFAULT = (
    "van der\nvan den\nvan de\nvan het\nin het\nop de\nin de\naan de\n"
    "von der\nvon den\nde la\nde los\nde las\n"
    "van\nde\nden\nhet\nten\nter\nte\nvon\nzum\nzur\nzu\ndu\ndes\nle\nla\nles"
)

grampsconfig.register("grampsclean.max_island_size",        10)
grampsconfig.register("grampsclean.father_postdeath_years", 1)
grampsconfig.register("grampsclean.mother_min_age",         12)
grampsconfig.register("grampsclean.father_min_age",         13)
grampsconfig.register("grampsclean.mother_max_age",         60)
grampsconfig.register("grampsclean.father_max_age",         90)
grampsconfig.register("grampsclean.prefix_list",            _PREFIX_DEFAULT)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_max_island_size():
    """Return the configured default max island group size (int)."""
    return int(grampsconfig.get("grampsclean.max_island_size"))


def get_thresholds():
    """Return a dict of impossibility thresholds read from config."""
    return {
        "father_postdeath_years": int(grampsconfig.get("grampsclean.father_postdeath_years")),
        "mother_min_age":         int(grampsconfig.get("grampsclean.mother_min_age")),
        "father_min_age":         int(grampsconfig.get("grampsclean.father_min_age")),
        "mother_max_age":         int(grampsconfig.get("grampsclean.mother_max_age")),
        "father_max_age":         int(grampsconfig.get("grampsclean.father_max_age")),
    }


def get_prefix_list():
    """Return the configured prefix list as a list of strings, longest first."""
    raw = grampsconfig.get("grampsclean.prefix_list")
    prefixes = [line.strip() for line in raw.splitlines() if line.strip()]
    prefixes.sort(key=len, reverse=True)
    return prefixes


# ---------------------------------------------------------------------------
# Preferences dialog
# ---------------------------------------------------------------------------

class PreferencesDialog(Gtk.Dialog):
    """Dialog for editing GrampsClean global default preferences."""

    def __init__(self, parent=None):
        Gtk.Dialog.__init__(
            self,
            title="GrampsClean Preferences",
            transient_for=parent,
            modal=True,
            destroy_with_parent=True,
        )
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        ok_btn = self.add_button("OK", Gtk.ResponseType.OK)
        ok_btn.get_style_context().add_class("suggested-action")
        self.set_default_response(Gtk.ResponseType.OK)
        self.set_default_size(440, 500)

        content = self.get_content_area()
        content.set_spacing(0)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_border_width(12)
        content.pack_start(main_box, True, True, 0)

        # --- Island Detection ---
        main_box.pack_start(
            self._section_label("Island Detection"), False, False, 0
        )
        island_grid = self._make_grid()

        lbl = Gtk.Label(label="Max island group size:")
        lbl.set_halign(Gtk.Align.END)
        self._spin_island = Gtk.SpinButton.new_with_range(1, 500, 1)
        self._spin_island.set_value(get_max_island_size())
        island_grid.attach(lbl,               0, 0, 1, 1)
        island_grid.attach(self._spin_island, 1, 0, 1, 1)
        main_box.pack_start(island_grid, False, False, 0)

        main_box.pack_start(Gtk.Separator(), False, False, 4)

        # --- Impossibility Thresholds ---
        main_box.pack_start(
            self._section_label("Impossibility Thresholds"), False, False, 0
        )
        thresh_grid = self._make_grid()

        thresholds = get_thresholds()
        threshold_rows = [
            ("Father post-death birth window (years):", "father_postdeath_years", 0,  10),
            ("Mother minimum age at birth:",             "mother_min_age",         1,  30),
            ("Father minimum age at birth:",             "father_min_age",         1,  30),
            ("Mother maximum age at birth:",             "mother_max_age",        30, 100),
            ("Father maximum age at birth:",             "father_max_age",        30, 150),
        ]

        self._threshold_spins = {}
        for row_idx, (label_text, key, lo, hi) in enumerate(threshold_rows):
            lbl = Gtk.Label(label=label_text)
            lbl.set_halign(Gtk.Align.END)
            spin = Gtk.SpinButton.new_with_range(lo, hi, 1)
            spin.set_value(thresholds[key])
            thresh_grid.attach(lbl,  0, row_idx, 1, 1)
            thresh_grid.attach(spin, 1, row_idx, 1, 1)
            self._threshold_spins[key] = spin

        main_box.pack_start(thresh_grid, False, False, 0)

        main_box.pack_start(Gtk.Separator(), False, False, 4)

        # --- Prefix List ---
        main_box.pack_start(
            self._section_label("Prefix List (one per line, longest first)"),
            False, False, 0,
        )

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_shadow_type(Gtk.ShadowType.IN)
        scroll.set_min_content_height(120)
        scroll.set_vexpand(True)

        self._prefix_view = Gtk.TextView()
        self._prefix_view.set_wrap_mode(Gtk.WrapMode.WORD)
        current_raw = grampsconfig.get("grampsclean.prefix_list")
        self._prefix_view.get_buffer().set_text(current_raw)
        scroll.add(self._prefix_view)
        main_box.pack_start(scroll, True, True, 0)

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
        grid = Gtk.Grid()
        grid.set_column_spacing(12)
        grid.set_row_spacing(4)
        grid.set_margin_start(12)
        return grid

    # ------------------------------------------------------------------
    # Public: override run() to save on OK
    # ------------------------------------------------------------------

    def run(self):
        response = Gtk.Dialog.run(self)
        if response == Gtk.ResponseType.OK:
            self._save()
        return response

    def _save(self):
        """Write all field values to GRAMPS config."""
        grampsconfig.set("grampsclean.max_island_size",
                         int(self._spin_island.get_value()))
        for key, spin in self._threshold_spins.items():
            grampsconfig.set(f"grampsclean.{key}", int(spin.get_value()))
        buf = self._prefix_view.get_buffer()
        text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
        grampsconfig.set("grampsclean.prefix_list", text)
