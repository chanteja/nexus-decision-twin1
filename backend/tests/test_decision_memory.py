# backend/tests/test_decision_memory.py
"""P5: related initiatives reuse/extend an existing Decision Graph (shared assumptions)."""
from forward_ledger import (
    Kind,
    Ledger,
    MemoryStore,
    Prediction,
    assign_graph_id,
    find_graph,
    graphs_summary,
)


def _seal(L, d, asm, gid):
    L.append(Prediction(decision=d, branches=["a", "b"], weights=[0.6, 0.4], survivor=0,
                        confidence=0.6, why="w", watch="t", kind=Kind.FORWARD,
                        oracle_ref="seed:" + d, assumptions=asm, graph_id=gid))


def test_related_decision_reuses_existing_graph():
    L = Ledger(MemoryStore())
    _seal(L, "Launch Brazil GTM", ["demand grows >18%", "FX stays stable"], "g:latam")
    # a new initiative leaning on a SHARED belief must extend the same graph
    gid = assign_graph_id(L, "Open Mexico next", ["demand grows >18%"])
    assert gid == "g:latam"


def test_unrelated_decision_starts_a_new_graph():
    L = Ledger(MemoryStore())
    _seal(L, "Launch Brazil GTM", ["demand grows >18%"], "g:latam")
    gid = assign_graph_id(L, "Adopt 4-day work week", ["morale improves retention"])
    assert gid != "g:latam" and gid.startswith("g:")


def test_graphs_summary_groups_by_initiative():
    L = Ledger(MemoryStore())
    _seal(L, "d1", ["a"], "g1"); _seal(L, "d2", ["a", "b"], "g1"); _seal(L, "d3", ["c"], "g2")
    g = graphs_summary(L)
    assert g["count"] == 2
    g1 = next(x for x in g["graphs"] if x["graph_id"] == "g1")
    assert g1["decisions"] == 2 and set(g1["assumptions"]) == {"a", "b"}


def test_find_graph_none_when_no_overlap():
    L = Ledger(MemoryStore())
    _seal(L, "d1", ["a"], "g1")
    assert find_graph(L, ["totally different"]) is None
