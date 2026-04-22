"""Batch search view: scan all filtered people, present master tree.

Scans the supplied person list once on a background thread, polling
all connectors per person and collecting top-N ranked candidates.
Results stream into a TreeStore where each local person is a parent
row and candidates are children. User selects a candidate row and
clicks Merge to write fields into that person.
"""

import os
import threading
from datetime import datetime

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from gramps.gen.const import GRAMPS_LOCALE as glocale

from matcher import score_candidate

_ = glocale.translation.gettext

TOP_N = 5  # candidates kept per person
DEBUG_LOG = os.path.expanduser("~/Documents/grampssearch-debug.log")


def _log(msg):
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%H:%M:%S')} {msg}\n")
    except Exception:
        pass
    print(msg)


def _year_hint(local):
    """Pick a year to narrow the API search.

    Prefer birth year; fall back to death year. `person_summary` stores
    dates as `(year, month, day)` tuples (or None).
    """
    for key in ("birth", "death"):
        ev = local.get(key) or {}
        ymd = ev.get("date")
        if ymd and ymd[0]:
            return int(ymd[0])
    return None


class SearchBox(Gtk.Box):
    def __init__(self, db, matcher_fn, connectors, person_iter):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.db = db
        self.matcher_fn = matcher_fn
        self.connectors = connectors
        self.people = list(person_iter)

        self._cancel = threading.Event()
        self._scan_thread = None
        self._matches_count = 0
        self._people_with_matches = 0
        self._current_candidate = None
        self._current_person = None

        self._build_ui()
        self._start_scan()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        header = Gtk.Label(xalign=0)
        header.set_markup(
            f"<b>{_('Batch search — scanning people missing birth or death data.')}</b>"
        )
        header.set_margin_start(8)
        header.set_margin_top(8)
        self.pack_start(header, False, False, 0)

        # Progress + status row
        prog_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        prog_row.set_margin_start(8)
        prog_row.set_margin_end(8)
        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        prog_row.pack_start(self.progress, True, True, 0)
        self.cancel_btn = Gtk.Button(label=_("Cancel"))
        self.cancel_btn.connect("clicked", self._on_cancel)
        prog_row.pack_end(self.cancel_btn, False, False, 0)
        self.pack_start(prog_row, False, False, 0)

        # Master tree:
        #   cols: score, source, name, birth, death, gramps_id
        #   data: person_obj, candidate_obj
        self.store = Gtk.TreeStore(
            str,     # score (parent: blank, child: rounded)
            str,     # source
            str,     # name
            str,     # birth
            str,     # death
            str,     # gramps_id
            object,  # person_obj   (parent only)
            object,  # candidate_obj (child only)
        )
        tree = Gtk.TreeView(model=self.store)
        tree.set_headers_clickable(True)
        for i, title in enumerate([
            _("Score"), _("Source"), _("Name"), _("Birth"), _("Death"), _("ID"),
        ]):
            col = Gtk.TreeViewColumn(title, Gtk.CellRendererText(), text=i)
            col.set_resizable(True)
            col.set_sort_column_id(i)
            tree.append_column(col)
        tree.get_selection().connect("changed", self._on_row_selected)
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(tree)
        sw.set_margin_start(8)
        sw.set_margin_end(8)
        self.pack_start(sw, True, True, 0)
        self.tree = tree

        # Detail view
        self.detail_view = Gtk.TextView(editable=False)
        self.detail_view.set_wrap_mode(Gtk.WrapMode.WORD)
        det_sw = Gtk.ScrolledWindow()
        det_sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        det_sw.set_min_content_height(120)
        det_sw.add(self.detail_view)
        det_frame = Gtk.Frame(label=_("Selection detail"))
        det_frame.add(det_sw)
        det_frame.set_margin_start(8)
        det_frame.set_margin_end(8)
        self.pack_start(det_frame, False, True, 0)

        # Status + buttons
        self.status = Gtk.Label(xalign=0)
        self.status.set_margin_start(8)
        self.pack_start(self.status, False, False, 0)

        btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btns.set_margin_start(8)
        btns.set_margin_end(8)
        btns.set_margin_bottom(8)
        self.merge_btn = Gtk.Button(label=_("Merge selected candidate"))
        self.merge_btn.connect("clicked", self._on_merge)
        self.merge_btn.set_sensitive(False)
        btns.pack_end(self.merge_btn, False, False, 0)
        self.pack_start(btns, False, False, 0)

    # ------------------------------------------------------------------
    # Scan worker
    # ------------------------------------------------------------------

    def _start_scan(self):
        total = len(self.people)
        if total == 0:
            self.status.set_text(_("No people missing core data."))
            self.progress.set_fraction(1.0)
            self.progress.set_text(_("Done"))
            self.cancel_btn.set_sensitive(False)
            return
        self.status.set_text(_("Starting scan of %d people…") % total)
        try:
            with open(DEBUG_LOG, "w", encoding="utf-8") as f:
                f.write(f"=== GrampsSearch scan start {datetime.now().isoformat()} ===\n")
                f.write(f"connectors: {[c.source_name for c in self.connectors]}\n")
                f.write(f"people queued: {total}\n\n")
        except Exception as e:
            print(f"[GrampsSearch] could not init debug log: {e}")
        _log(f"DEBUG_LOG path: {DEBUG_LOG}")
        self._scan_thread = threading.Thread(
            target=self._scan_worker, args=(total,), daemon=True
        )
        self._scan_thread.start()

    def _scan_worker(self, total):
        for idx, person in enumerate(self.people, 1):
            if self._cancel.is_set():
                GLib.idle_add(self._on_scan_done, idx - 1, total, True)
                return
            try:
                local = self.db.person_summary(person)
            except Exception as e:
                print(f"[GrampsSearch] person_summary failed: {e}")
                GLib.idle_add(self._update_progress, idx, total, None)
                continue

            year_hint = _year_hint(local)
            _log(
                f"--- person {idx}/{total}: '{local.get('given','')}' "
                f"'{local.get('surname','')}' (id={local.get('gramps_id','')}) "
                f"year_hint={year_hint}"
            )
            all_candidates = []
            for c in self.connectors:
                if self._cancel.is_set():
                    break
                try:
                    hits = c.search(local["given"], local["surname"], year=year_hint)
                    _log(f"  {c.source_name}: {len(hits)} hits")
                    for h in hits[:3]:
                        _log(
                            f"    - '{h.given}' '{h.surname}' "
                            f"b={h.birth_date or '-'} d={h.death_date or '-'}"
                        )
                    all_candidates.extend(hits)
                except Exception as e:
                    _log(f"  {c.source_name} FAILED: {e}")
            if self._cancel.is_set():
                GLib.idle_add(self._on_scan_done, idx - 1, total, True)
                return

            scored_all = [(score_candidate(local, c), c) for c in all_candidates]
            scored_all.sort(key=lambda x: x[0].total, reverse=True)
            for s, c in scored_all[:3]:
                _log(
                    f"  scored: total={s.total:.3f} name={s.name:.2f} "
                    f"b={s.birth:.2f} d={s.death:.2f} p={s.place:.2f} "
                    f"-> '{c.given}' '{c.surname}'"
                )

            ranked = self.matcher_fn(local, all_candidates)[:TOP_N]
            _log(f"  kept (>= threshold): {len(ranked)}")
            GLib.idle_add(self._append_results, person, local, ranked, idx, total)

        GLib.idle_add(self._on_scan_done, total, total, False)

    def _append_results(self, person, local, ranked, idx, total):
        if ranked:
            parent_label = f"{local['surname']}, {local['given']}".strip(", ").strip()
            local_birth = (local.get("birth") or {}).get("date_text") or "—"
            local_death = (local.get("death") or {}).get("date_text") or "—"
            parent_iter = self.store.append(None, [
                "", "", parent_label, local_birth, local_death,
                local.get("gramps_id", ""), person, None,
            ])
            for score, cand in ranked:
                self.store.append(parent_iter, [
                    f"{score.total:.3f}",
                    cand.source,
                    f"{cand.given} {cand.surname}".strip(),
                    cand.birth_date or "",
                    cand.death_date or "",
                    "",
                    None,
                    cand,
                ])
            self._matches_count += len(ranked)
            self._people_with_matches += 1
        self._update_progress(idx, total, local)
        return False

    def _update_progress(self, idx, total, local):
        frac = idx / total if total else 1.0
        self.progress.set_fraction(frac)
        name_hint = ""
        if local:
            name_hint = f" — {local.get('surname','')}, {local.get('given','')}".rstrip(", ")
        self.progress.set_text(f"{idx} / {total}{name_hint}")
        self.status.set_text(
            _("Scanned %(i)d / %(n)d. %(m)d candidate(s) across %(p)d person(s).")
            % {"i": idx, "n": total, "m": self._matches_count, "p": self._people_with_matches}
        )
        return False

    def _on_scan_done(self, scanned, total, cancelled):
        self.cancel_btn.set_sensitive(False)
        if cancelled:
            self.cancel_btn.set_label(_("Cancelled"))
            self.status.set_text(
                _("Cancelled at %(i)d / %(n)d. %(m)d candidate(s) across %(p)d person(s).")
                % {"i": scanned, "n": total,
                   "m": self._matches_count, "p": self._people_with_matches}
            )
        else:
            self.cancel_btn.set_label(_("Done"))
            self.progress.set_fraction(1.0)
            self.progress.set_text(_("Done"))
            self.status.set_text(
                _("Scan complete. %(m)d candidate(s) across %(p)d person(s).")
                % {"m": self._matches_count, "p": self._people_with_matches}
            )
        return False

    def _on_cancel(self, *_args):
        self._cancel.set()
        self.cancel_btn.set_sensitive(False)
        self.cancel_btn.set_label(_("Cancelling…"))

    # ------------------------------------------------------------------
    # Selection + merge
    # ------------------------------------------------------------------

    def _on_row_selected(self, selection):
        model, it = selection.get_selected()
        if not it:
            self._current_candidate = None
            self._current_person = None
            self.merge_btn.set_sensitive(False)
            self._set_text(self.detail_view, "")
            return

        cand = model.get_value(it, 7)
        if cand is None:
            # Parent (person) row — no candidate selected
            self._current_candidate = None
            self._current_person = None
            self.merge_btn.set_sensitive(False)
            self._set_text(self.detail_view, _("Select a candidate row to merge."))
            return

        # Walk up to parent for the person object
        parent_it = model.iter_parent(it)
        person = model.get_value(parent_it, 6) if parent_it else None
        if person is None:
            self.merge_btn.set_sensitive(False)
            return

        self._current_candidate = cand
        self._current_person = person
        self.merge_btn.set_sensitive(True)
        self._set_text(self.detail_view, self._fmt_candidate(cand))

    def _fmt_candidate(self, c):
        return (
            f"{c.surname}, {c.given}   [{c.source}]\n\n"
            f"{_('Birth')}: {c.birth_date or '—'}  @ {c.birth_place}\n"
            f"{_('Death')}: {c.death_date or '—'}  @ {c.death_place}\n\n"
            f"{c.detail_url}"
        )

    def _on_merge(self, *_args):
        if not self._current_candidate or not self._current_person:
            return
        c = self._current_candidate
        selected = {
            "birth": {"date_text": c.birth_date, "place": c.birth_place}
            if (c.birth_date or c.birth_place) else None,
            "death": {"date_text": c.death_date, "place": c.death_place}
            if (c.death_date or c.death_place) else None,
            "source_url": c.detail_url,
        }
        try:
            self.db.merge_fields(
                self._current_person,
                selected,
                source_title=f"GrampsSearch: {c.source}",
            )
            self.status.set_text(_("Merged candidate from %s.") % c.source)
        except Exception as e:
            self.status.set_text(_("Merge failed: %s") % e)

    @staticmethod
    def _set_text(view, text):
        view.get_buffer().set_text(text or "")
