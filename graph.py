"""GrampsClean — kinship graph for island detection.

Builds a connected-components structure from GRAMPS family relationships
using a union-find (disjoint set) algorithm. No third-party dependencies.
"""


class KinshipGraph:
    """
    Represents the kinship network as a union-find structure.

    Each person handle is a node. Family relationships (spouse and
    parent-child) are edges. Connected components are groups of people
    reachable from each other via any family link.

    Usage:
        graph = KinshipGraph(db_wrap)
        graph.build()
        islands = graph.get_islands(max_size=10)
        for component in islands:
            for handle in component:
                person = db_wrap.get_person_from_handle(handle)
                ...
    """

    def __init__(self, db_wrap=None):
        """
        :param db_wrap: GrampsDb instance (optional — not needed if using build_from_raw)
        """
        self.db_wrap = db_wrap
        self._parent = {}   # handle → root handle
        self._rank = {}     # handle → tree rank (for union by rank)
        self._built = False

    @classmethod
    def build_from_raw(cls, person_handles, family_edges):
        """
        Build a graph from pre-fetched plain Python data (no DB access).

        Safe to call from a background thread — all DB reads must have
        been done on the main thread before calling this.

        :param person_handles: iterable of person handle strings
        :param family_edges: iterable of lists of handle strings
                             (each list = one family's members)
        :returns: built KinshipGraph instance
        """
        graph = cls(db_wrap=None)
        for handle in person_handles:
            graph._find(handle)
        for edges in family_edges:
            if len(edges) > 1:
                for h in edges[1:]:
                    graph._union(edges[0], h)
        graph._built = True
        return graph

    # ------------------------------------------------------------------
    # Union-Find internals
    # ------------------------------------------------------------------

    def _find(self, handle):
        """
        Return the root handle for the given handle (path-compressed).
        Registers the handle as an isolated node if not yet seen.
        """
        if handle not in self._parent:
            self._parent[handle] = handle
            self._rank[handle] = 0
            return handle

        # Path compression: point directly to root
        if self._parent[handle] != handle:
            self._parent[handle] = self._find(self._parent[handle])
        return self._parent[handle]

    def _union(self, h1, h2):
        """
        Merge the components containing h1 and h2 (union by rank).
        """
        root1 = self._find(h1)
        root2 = self._find(h2)

        if root1 == root2:
            return  # already in the same component

        # Attach smaller-rank tree under larger-rank root
        if self._rank[root1] < self._rank[root2]:
            self._parent[root1] = root2
        elif self._rank[root1] > self._rank[root2]:
            self._parent[root2] = root1
        else:
            self._parent[root2] = root1
            self._rank[root1] += 1

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    def build(self):
        """
        Populate the graph from the GRAMPS database.

        Registers every person as a node, then unions all people
        who share a family (as spouses or parent-child).
        """
        db = self.db_wrap

        # Register every person as a node (isolated until linked)
        for person in db.iter_people():
            self._find(person.get_handle())

        # Process every family to union connected people
        for family in db.iter_families():
            # Collect all person handles in this family
            handles = []

            father_handle = family.get_father_handle()
            if father_handle:
                handles.append(father_handle)

            mother_handle = family.get_mother_handle()
            if mother_handle:
                handles.append(mother_handle)

            for child_ref in family.get_child_ref_list():
                if child_ref.ref:
                    handles.append(child_ref.ref)

            # Union all members of this family together
            if len(handles) > 1:
                for h in handles[1:]:
                    self._union(handles[0], h)

        self._built = True

    # ------------------------------------------------------------------
    # Component analysis
    # ------------------------------------------------------------------

    def get_components(self):
        """
        Return all connected components as a list of sets of handles.

        Each set contains the handles of one connected group.
        Every person handle appears in exactly one set.

        :returns: list[set[str]]
        """
        if not self._built:
            self.build()

        groups = {}
        for handle in self._parent:
            root = self._find(handle)
            if root not in groups:
                groups[root] = set()
            groups[root].add(handle)

        return list(groups.values())

    def get_islands(self, max_size=10):
        """
        Return components with size <= max_size, sorted smallest first.

        :param max_size: maximum group size to include (default 10)
        :returns: list[set[str]], sorted by len ascending
        """
        components = self.get_components()
        islands = [c for c in components if len(c) <= max_size]
        islands.sort(key=len)
        return islands

    def component_count(self):
        """Return total number of connected components."""
        return len(self.get_components())

    def island_count(self, max_size=10):
        """Return number of isolated/small-group components."""
        return len(self.get_islands(max_size))
