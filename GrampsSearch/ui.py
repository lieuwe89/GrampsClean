"""Side-by-side approval view, packed into the tool's managed window.

Left pane: local GRAMPS person. Right pane: ranked external candidates
+ detail view. Merge button writes approved fields via GrampsDb.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

from gramps.gen.const import GRAMPS_LOCALE as glocale

_ = glocale.translation.gettext


class SearchBox(Gtk.Box):
    def __init__(self, db, matcher_fn, connectors, person_iter):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.db = db
        self.matcher_fn = matcher_fn
        self.connectors = connectors
        self.person_queue = list(person_iter)
        self.current_local = None
        self.current_person = None
        self.current_candidate = None

        self._build_ui()
        self.next_person()

    # ------------------------------------------------------------------

    def _build_ui(self):
        header = Gtk.Label(xalign=0)
        header.set_markup(f"<b>{_('Review candidates — merge approved fields into GRAMPS.')}</b>")
        header.set_margin_start(8)
        header.set_margin_top(8)
        self.pack_start(header, False, False, 0)

        panes = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, homogeneous=True)
        panes.set_margin_start(8)
        panes.set_margin_end(8)
        self.pack_start(panes, True, True, 0)

        # Left: local person
        self.local_view = Gtk.TextView(editable=False)
        self.local_view.set_wrap_mode(Gtk.WrapMode.WORD)
        panes.pack_start(self._framed(_("Local GRAMPS"), self._scrolled(self.local_view)), True, True, 0)

        # Right: candidate list + detail
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        # score (float), source (str), name (str), birth (str), death (str), obj
        self.candidate_store = Gtk.ListStore(float, str, str, str, str, object)
        tree = Gtk.TreeView(model=self.candidate_store)
        for i, title in enumerate([_("Score"), _("Source"), _("Name"), _("Birth"), _("Death")]):
            tree.append_column(Gtk.TreeViewColumn(title, Gtk.CellRendererText(), text=i))
        tree.get_selection().connect("changed", self._on_candidate_selected)
        right.pack_start(self._scrolled(tree), True, True, 0)

        self.candidate_view = Gtk.TextView(editable=False)
        self.candidate_view.set_wrap_mode(Gtk.WrapMode.WORD)
        right.pack_start(self._scrolled(self.candidate_view), True, True, 0)

        panes.pack_start(self._framed(_("API candidates"), right), True, True, 0)

        # Status bar
        self.status = Gtk.Label(xalign=0)
        self.status.set_margin_start(8)
        self.pack_start(self.status, False, False, 0)

        # Buttons
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        buttons.set_margin_start(8)
        buttons.set_margin_end(8)
        buttons.set_margin_bottom(8)

        skip = Gtk.Button(label=_("Skip person"))
        skip.connect("clicked", lambda *_: self.next_person())
        buttons.pack_start(skip, False, False, 0)

        self.merge_btn = Gtk.Button(label=_("Merge selected"))
        self.merge_btn.connect("clicked", self._on_merge)
        self.merge_btn.set_sensitive(False)
        buttons.pack_end(self.merge_btn, False, False, 0)
        self.pack_start(buttons, False, False, 0)

    def _framed(self, title, child):
        frame = Gtk.Frame(label=title)
        frame.add(child)
        return frame

    def _scrolled(self, child):
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(child)
        return sw

    # ------------------------------------------------------------------

    def next_person(self):
        self.current_candidate = None
        self.merge_btn.set_sensitive(False)
        self.candidate_store.clear()
        self._set_text(self.candidate_view, "")

        if not self.person_queue:
            self._set_text(self.local_view, _("No more people to review."))
            self.status.set_text(_("Done."))
            return

        self.current_person = self.person_queue.pop(0)
        self.current_local = self.db.person_summary(self.current_person)
        self._render_local()
        self._run_search()

    def _render_local(self):
        s = self.current_local
        birth = s.get("birth") or {}
        death = s.get("death") or {}
        lines = [
            f"{s['surname']}, {s['given']}  ({s['gramps_id']})",
            "",
            f"{_('Birth')}: {birth.get('date_text', '—') or '—'}  @ {birth.get('place', '')}",
            f"{_('Death')}: {death.get('date_text', '—') or '—'}  @ {death.get('place', '')}",
        ]
        self._set_text(self.local_view, "\n".join(lines))

    def _run_search(self):
        """Runs connectors synchronously for now. TODO: move to GLib idle thread."""
        self.status.set_text(_("Searching…"))
        all_candidates = []
        for c in self.connectors:
            try:
                all_candidates.extend(
                    c.search(self.current_local["given"], self.current_local["surname"])
                )
            except Exception as e:
                print(f"[GrampsSearch] {c.source_name} failed: {e}")

        ranked = self.matcher_fn(self.current_local, all_candidates)
        for score, cand in ranked:
            self.candidate_store.append([
                round(score.total, 3),
                cand.source,
                f"{cand.given} {cand.surname}".strip(),
                cand.birth_date or "",
                cand.death_date or "",
                cand,
            ])
        self.status.set_text(_("Found %d candidate(s).") % len(ranked))

    def _on_candidate_selected(self, selection):
        model, it = selection.get_selected()
        if not it:
            self.merge_btn.set_sensitive(False)
            return
        cand = model.get_value(it, 5)
        self.current_candidate = cand
        self.merge_btn.set_sensitive(True)
        self._set_text(self.candidate_view, self._fmt_candidate(cand))

    def _fmt_candidate(self, c):
        return (
            f"{c.surname}, {c.given}   [{c.source}]\n\n"
            f"{_('Birth')}: {c.birth_date or '—'}  @ {c.birth_place}\n"
            f"{_('Death')}: {c.death_date or '—'}  @ {c.death_place}\n\n"
            f"{c.detail_url}"
        )

    def _on_merge(self, *_args):
        if not self.current_candidate:
            return
        c = self.current_candidate
        selected = {
            "birth": {"date_text": c.birth_date, "place": c.birth_place}
            if (c.birth_date or c.birth_place) else None,
            "death": {"date_text": c.death_date, "place": c.death_place}
            if (c.death_date or c.death_place) else None,
            "source_url": c.detail_url,
        }
        self.db.merge_fields(
            self.current_person,
            selected,
            source_title=f"GrampsSearch: {c.source}",
        )
        self.status.set_text(_("Merged. Next person…"))
        GLib.idle_add(self.next_person)

    @staticmethod
    def _set_text(view, text):
        view.get_buffer().set_text(text or "")
