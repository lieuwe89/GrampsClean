"""GrampsClean — background scan worker.

Runs scan functions in a daemon thread and pushes results to the GTK
main loop via GLib.idle_add, keeping the UI responsive on large databases.

No GRAMPS imports — only threading and GLib.
"""

import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib


class ScanWorker:
    """
    Runs a scan function in a background thread and streams results
    into a ResultList widget via GLib.idle_add.

    Usage:
        def my_scan(db_wrap):
            for person in db_wrap.iter_people():
                name = db_wrap.format_name(person)
                gramps_id = db_wrap.get_gramps_id(person)
                yield (name, gramps_id, "some detail"), f"Found: {name}"
            # Last status_text becomes the completion message

        worker = ScanWorker(result_list, my_scan, db_wrap)
        worker.start()   # call from Scan button handler
        # worker.cancel()  # call from Cancel button handler
    """

    def __init__(self, result_list, scan_fn, db_wrap):
        """
        :param result_list: ResultList widget to populate
        :param scan_fn: callable(db_wrap) → generator of (row_tuple, status_text)
        :param db_wrap: GrampsDb instance
        """
        self.result_list = result_list
        self.scan_fn = scan_fn
        self.db_wrap = db_wrap
        self._thread = None
        self._cancelled = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self):
        """Start the scan in a background thread. Safe to call from GTK handlers."""
        if self._thread is not None and self._thread.is_alive():
            return  # already running

        self._cancelled = False
        self.result_list.clear()
        self.result_list.set_status("Scanning\u2026")

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def cancel(self):
        """Signal the scan to stop. The thread will exit cleanly on next yield."""
        self._cancelled = True

    def is_running(self):
        """Return True if a scan is currently in progress."""
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run(self):
        """Background thread body. Must not touch GTK directly."""
        status_text = "Scan complete"
        try:
            for row_tuple, status_text in self.scan_fn(self.db_wrap):
                if self._cancelled:
                    GLib.idle_add(self.result_list.set_status, "Scan cancelled")
                    return
                GLib.idle_add(self.result_list.append_row, *row_tuple)

            GLib.idle_add(self.result_list.set_status, status_text)

        except Exception as exc:
            GLib.idle_add(
                self.result_list.set_status, f"Error during scan: {exc}"
            )
