from forward_ledger import Kind, Ledger, MemoryStore, Prediction, calibration, trust_graph


def fwd(d, p, author="a", dom="g"):
    return Prediction(decision=d, branches=["s", "x"], weights=[p, 1 - p], survivor=0,
                      confidence=p, why="w", watch="t", author=author, domain=dom,
                      kind=Kind.FORWARD, oracle_ref="seed:" + d)


def test_calibration_uses_only_resolved():
    L = Ledger(MemoryStore())
    e1 = L.append(fwd("a", 0.8), created_at=1.0)
    e2 = L.append(fwd("b", 0.3), created_at=1.0)
    L.append(fwd("c", 0.6), created_at=1.0)  # stays pending
    L.resolve(e1.id, True, "r", at=10.0)
    L.resolve(e2.id, False, "r", at=10.0)
    c = calibration(L)
    assert c["forward"]["n"] == 2
    assert c["forward"]["accuracy"] == 1.0
    assert c["forward"]["sealed_pending"] == 1


def test_fresh_ledger_is_honestly_empty():
    c = calibration(Ledger(MemoryStore()))
    assert c["forward"]["n"] == 0
    assert "begun" in c["headline"] or "sealed" in c["headline"]


def test_trust_graph_quality_weighted():
    L = Ledger(MemoryStore())
    for i in range(4):
        e = L.append(fwd(f"g{i}", 0.85, author="good"), created_at=1.0)
        L.resolve(e.id, True, "r", at=10.0)
    e = L.append(fwd("l0", 0.85, author="lucky"), created_at=1.0)
    L.resolve(e.id, True, "r", at=10.0)
    tg = trust_graph(L)
    ranks = {a["author"]: a["trust"] for a in tg["authors"]}
    assert ranks["good"] > ranks["lucky"]
