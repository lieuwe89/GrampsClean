"""GrampsClean — reusable GTK widgets (no GRAMPS dependencies)."""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class ResultList(Gtk.Box):
    """
    A reusable scrolled TreeView for displaying scan results.

    Each tool tab instantiates one ResultList with its own column config.
    This widget has zero GRAMPS imports — it is pure GTK.

    Usage:
        columns = [("Name", 0), ("ID", 1), ("Detail", 2)]
        result_list = ResultList(columns)
        result_list.append_row("Jan de Vries", "I0042", "Missing birth date")
        result_list.set_status("3 issues found")

    Navigation:
        Pass on_activate=callback to receive the row tag (e.g. a person handle)
        when a row is double-clicked. Include the tag as the last element of each
        row tuple passed to append_row(); rows without a tag silently skip navigation.
    """

    _STATUS_DEFAULT = "Ready \u2014 click Scan to begin"

    def __init__(self, columns, on_activate=None):
        """
        Build the widget.

        :param columns: list of (column_title, col_index) tuples
        :param on_activate: optional callable(tag: str) invoked on row double-click
        """
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=4)

        self._visible_columns = columns
        self._on_activate = on_activate

        # ListStore — one str column per result column + one hidden tag column
        self.store = Gtk.ListStore(*[str for _ in columns], str)

        # TreeView
        self.tree = Gtk.TreeView(model=self.store)
        self.tree.set_headers_visible(True)
        self.tree.set_enable_search(False)
        self.tree.get_selection().set_mode(Gtk.SelectionMode.SINGLE)

        for col_title, col_index in columns:
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(col_title, renderer)
            column.add_attribute(renderer, "text", col_index)
            column.set_resizable(True)
            column.set_min_width(80)
            self.tree.append_column(column)

        if on_activate:
            self.tree.connect("row-activated", self._row_activated)

        # Scrolled window wrapping the TreeView
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_shadow_type(Gtk.ShadowType.IN)
        sw.add(self.tree)
        self.pack_start(sw, True, True, 0)

        # Status bar
        self.status_label = Gtk.Label(label=self._STATUS_DEFAULT)
        self.status_label.set_halign(Gtk.Align.START)
        self.status_label.set_margin_start(4)
        self.status_label.set_margin_bottom(4)
        self.pack_start(self.status_label, False, False, 0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def clear(self):
        """Remove all rows and reset status label."""
        self.store.clear()
        self.status_label.set_text(self._STATUS_DEFAULT)

    def set_status(self, text):
        """Update the status bar text."""
        self.status_label.set_text(text)

    def append_row(self, *values):
        """
        Append a row.

        Pass N visible-column values, optionally followed by a tag as the
        (N+1)th value. If the tag is omitted, an empty string is used,
        which silently skips navigation on row activation.
        """
        row = list(values)
        n_store_cols = self.store.get_n_columns()
        while len(row) < n_store_cols:
            row.append("")
        self.store.append(row[:n_store_cols])

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _row_activated(self, tree, path, column):
        """Handle row double-click: read tag from hidden column and fire callback."""
        model = tree.get_model()
        it = model.get_iter(path)
        tag = model.get_value(it, len(self._visible_columns))
        if tag and self._on_activate:
            self._on_activate(tag)
