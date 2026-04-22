"""GrampsSearch — Preferences dialog and GRAMPS config registration.

Config keys are registered at module import time. Sibling modules that
need a setting call the `get_*` helpers after importing this module.

Keys cover: cache (enabled + TTL), debug log toggle, per-source
on/off, and GenealogieOnline OAuth2 credentials + persisted token.
"""

import time

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
grampsconfig.register("grampssearch.use_genealogieonline", False)

grampsconfig.register("grampssearch.genealogieonline_client_id",     "")
grampsconfig.register("grampssearch.genealogieonline_client_secret", "")
grampsconfig.register("grampssearch.genealogieonline_redirect_uri",  "")
grampsconfig.register("grampssearch.genealogieonline_token",         "")
grampsconfig.register("grampssearch.genealogieonline_token_expires_at", 0)


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


def get_genealogieonline_creds() -> dict:
    return {
        "client_id":     grampsconfig.get("grampssearch.genealogieonline_client_id")     or "",
        "client_secret": grampsconfig.get("grampssearch.genealogieonline_client_secret") or "",
        "redirect_uri":  grampsconfig.get("grampssearch.genealogieonline_redirect_uri")  or "",
    }


def get_genealogieonline_token():
    """Return (token, expires_at) tuple. Token may be empty string."""
    return (
        grampsconfig.get("grampssearch.genealogieonline_token") or "",
        int(grampsconfig.get("grampssearch.genealogieonline_token_expires_at") or 0),
    )


def set_genealogieonline_token(token: str, expires_at: float):
    grampsconfig.set("grampssearch.genealogieonline_token", token or "")
    grampsconfig.set("grampssearch.genealogieonline_token_expires_at", int(expires_at))


def has_valid_genealogieonline_token() -> bool:
    token, exp = get_genealogieonline_token()
    return bool(token) and time.time() < exp


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
        self._chk_gonline = Gtk.CheckButton(label="GenealogieOnline (OAuth2)")
        self._chk_gonline.set_active(
            bool(grampsconfig.get("grampssearch.use_genealogieonline"))
        )
        src_grid.attach(self._chk_openarch, 0, 0, 2, 1)
        src_grid.attach(self._chk_allegron, 0, 1, 2, 1)
        src_grid.attach(self._chk_gonline,  0, 2, 2, 1)
        main.pack_start(src_grid, False, False, 0)

        main.pack_start(Gtk.Separator(), False, False, 4)

        # --- GenealogieOnline creds ---
        main.pack_start(
            self._section_label("GenealogieOnline OAuth2 credentials"),
            False, False, 0,
        )
        creds_grid = self._make_grid()
        creds = get_genealogieonline_creds()
        self._ent_client_id     = self._entry(creds["client_id"])
        self._ent_client_secret = self._entry(creds["client_secret"], password=True)
        self._ent_redirect_uri  = self._entry(creds["redirect_uri"])
        for row, (label, entry) in enumerate([
            ("Client ID:",     self._ent_client_id),
            ("Client Secret:", self._ent_client_secret),
            ("Redirect URI:",  self._ent_redirect_uri),
        ]):
            lbl = Gtk.Label(label=label)
            lbl.set_halign(Gtk.Align.END)
            creds_grid.attach(lbl,   0, row, 1, 1)
            creds_grid.attach(entry, 1, row, 1, 1)
        main.pack_start(creds_grid, False, False, 0)

        token_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        token_row.set_margin_start(12)
        self._lbl_token_status = Gtk.Label(xalign=0)
        self._refresh_token_status()
        token_row.pack_start(self._lbl_token_status, True, True, 0)
        main.pack_start(token_row, False, False, 0)

        hint = Gtk.Label(xalign=0)
        hint.set_margin_start(12)
        hint.set_markup(
            "<i>Browser-based authorization is not yet wired up — "
            "token must be provisioned manually for now.</i>"
        )
        main.pack_start(hint, False, False, 0)

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

    def _entry(self, value, password=False):
        e = Gtk.Entry()
        e.set_text(value or "")
        e.set_hexpand(True)
        if password:
            e.set_visibility(False)
        return e

    def _refresh_token_status(self):
        token, exp = get_genealogieonline_token()
        if not token:
            txt = "No stored token."
        elif time.time() >= exp:
            txt = "Stored token expired."
        else:
            import datetime as _dt
            when = _dt.datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M")
            txt = f"Token stored, valid until {when}."
        self._lbl_token_status.set_markup(f"<small>{txt}</small>")

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

        grampsconfig.set("grampssearch.genealogieonline_client_id",
                         self._ent_client_id.get_text().strip())
        grampsconfig.set("grampssearch.genealogieonline_client_secret",
                         self._ent_client_secret.get_text().strip())
        grampsconfig.set("grampssearch.genealogieonline_redirect_uri",
                         self._ent_redirect_uri.get_text().strip())
