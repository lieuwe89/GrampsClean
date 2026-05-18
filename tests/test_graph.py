import pytest
from graph import KinshipGraph

def test_empty_graph():
    graph = KinshipGraph.build_from_raw([], [])
    assert graph.get_components() == []
    assert graph.component_count() == 0
    assert graph.island_count() == 0

def test_single_person():
    graph = KinshipGraph.build_from_raw(["p1"], [])
    components = graph.get_components()
    assert len(components) == 1
    assert components[0] == {"p1"}
    assert graph.component_count() == 1
    assert graph.island_count(max_size=1) == 1

def test_isolated_people():
    graph = KinshipGraph.build_from_raw(["p1", "p2", "p3"], [])
    components = graph.get_components()
    assert len(components) == 3
    assert {"p1"} in components
    assert {"p2"} in components
    assert {"p3"} in components
    assert graph.component_count() == 3

def test_simple_family():
    # p1 and p2 in a family
    graph = KinshipGraph.build_from_raw(["p1", "p2"], [["p1", "p2"]])
    components = graph.get_components()
    assert len(components) == 1
    assert components[0] == {"p1", "p2"}
    assert graph.component_count() == 1

def test_connected_families():
    # p1-p2 in Fam1, p2-p3 in Fam2 -> p1, p2, p3 should be in one component
    graph = KinshipGraph.build_from_raw(["p1", "p2", "p3"], [["p1", "p2"], ["p2", "p3"]])
    components = graph.get_components()
    assert len(components) == 1
    assert components[0] == {"p1", "p2", "p3"}

def test_multiple_components():
    # p1-p2, p3-p4, p5 isolated
    person_handles = ["p1", "p2", "p3", "p4", "p5"]
    family_edges = [["p1", "p2"], ["p3", "p4"]]
    graph = KinshipGraph.build_from_raw(person_handles, family_edges)
    components = graph.get_components()
    assert len(components) == 3
    assert {"p1", "p2"} in components
    assert {"p3", "p4"} in components
    assert {"p5"} in components

def test_get_islands():
    # Component sizes: 1, 2, 3, 5
    person_handles = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9", "p10", "p11"]
    family_edges = [
        ["p2", "p3"], # size 2
        ["p4", "p5", "p6"], # size 3
        ["p7", "p8", "p9", "p10", "p11"] # size 5
    ]
    # p1 is isolated (size 1)
    graph = KinshipGraph.build_from_raw(person_handles, family_edges)

    islands_2 = graph.get_islands(max_size=2)
    assert len(islands_2) == 2
    assert {"p1"} in islands_2
    assert {"p2", "p3"} in islands_2

    islands_4 = graph.get_islands(max_size=4)
    assert len(islands_4) == 3
    assert {"p1"} in islands_4
    assert {"p2", "p3"} in islands_4
    assert {"p4", "p5", "p6"} in islands_4

    # Verify sorting (smallest first)
    assert len(islands_4[0]) == 1
    assert len(islands_4[1]) == 2
    assert len(islands_4[2]) == 3

def test_counts():
    person_handles = ["p1", "p2", "p3", "p4", "p5"]
    family_edges = [["p1", "p2"]]
    graph = KinshipGraph.build_from_raw(person_handles, family_edges)

    assert graph.component_count() == 4 # {p1, p2}, {p3}, {p4}, {p5}
    assert graph.island_count(max_size=1) == 3
    assert graph.island_count(max_size=2) == 4

def test_build_from_raw_unseen_people_in_families():
    # If a person is in family_edges but not in person_handles,
    # build_from_raw currently doesn't explicitly handle it but _union calls _find.
    # _find adds it to _parent.
    graph = KinshipGraph.build_from_raw([], [["p1", "p2"]])
    components = graph.get_components()
    assert len(components) == 1
    assert components[0] == {"p1", "p2"}
