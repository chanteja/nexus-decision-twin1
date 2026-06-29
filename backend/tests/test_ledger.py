from forward_ledger import Ledger, MemoryStore, Prediction, TamperError


def mk(d="x", **kw):
    return Prediction(decision=d, branches=["a", "b"], weights=[0.6, 0.4], survivor=0,
                      confidence=0.6, why="w", watch="t", oracle_ref="seed:x", **kw)


def test_chain_links_and_verifies():
    L = Ledger(MemoryStore())
    e1 = L.append(mk("one")); e2 = L.append(mk("two")); e3 = L.append(mk("three"))
    assert e1.prev_hash == "0" * 64
    assert e2.prev_hash == e1.hash and e3.prev_hash == e2.hash
    assert L.verify() is True


def test_tamper_breaks_chain():
    s = MemoryStore(); L = Ledger(s)
    L.append(mk("one")); L.append(mk("two"))
    s._rows[0]["prediction"]["decision"] = "edited after sealing"
    try:
        Ledger(s); assert False, "tamper went undetected"
    except TamperError:
        pass


def test_resolution_cannot_precede_seal():
    L = Ledger(MemoryStore())
    e = L.append(mk("one"), created_at=1000.0)
    try:
        L.resolve(e.id, True, "ref", at=999.0); assert False
    except TamperError:
        pass
    r = L.resolve(e.id, True, "ref", at=1001.0)
    assert r.survived is True and r.resolved_at == 1001.0


def test_merkle_root_changes_on_append():
    L = Ledger(MemoryStore())
    L.append(mk("one")); r1 = L.merkle_root()
    L.append(mk("two")); r2 = L.merkle_root()
    assert r1 != r2 and len(r2) == 64


def test_resolution_does_not_break_seal_hash():
    L = Ledger(MemoryStore())
    e = L.append(mk("one"), created_at=1000.0)
    h = e.hash
    L.resolve(e.id, False, "ref", at=2000.0)
    assert L.verify() is True and L.by_id(e.id).hash == h


def test_flipped_outcome_is_detected_after_settlement():
    """The review gap: outcomes lived outside the hash and could be silently flipped.
    Now a settlement hash binds the outcome to the sealed core; editing it is caught."""
    s = MemoryStore(); L = Ledger(s)
    e = L.append(mk("one"), created_at=1000.0)
    L.resolve(e.id, survived=True, ref="oracle:real", at=2000.0)
    assert L.verify() is True
    # an insider edits the stored outcome (false<-true) without touching the seal core
    for row in s._rows:
        if row["id"] == e.id:
            row["survived"] = False
    try:
        Ledger(s)  # reload re-verifies
        assert False, "flipped outcome went undetected"
    except TamperError:
        pass


def test_settlement_root_changes_when_outcome_settles():
    L = Ledger(MemoryStore())
    e = L.append(mk("one"), created_at=1000.0)
    before = L.digest()["settlement_root"]
    L.resolve(e.id, survived=True, ref="oracle:x", at=2000.0)
    assert L.digest()["settlement_root"] != before


def test_cached_roots_match_fresh_recompute_and_invalidate():
    """The Merkle/settlement caches must equal a from-scratch recompute after every
    mutation — caching for speed must never change the answer."""
    s = MemoryStore(); L = Ledger(s)
    e1 = L.append(mk("one"), created_at=1000.0)
    r1 = L.merkle_root()
    L.append(mk("two"), created_at=1001.0)
    assert L.merkle_root() != r1                      # invalidated on append
    L.resolve(e1.id, survived=True, ref="o", at=2000.0)
    # a freshly loaded ledger (no cache) must agree on both roots
    fresh = Ledger(s)
    assert fresh.merkle_root() == L.merkle_root()
    assert fresh.settlement_root() == L.settlement_root()
    assert L.digest()["chain_valid"] is True
    assert L.digest()["merkle_root"] == L.merkle_root()  # stable across repeated reads


def test_is_intact_is_live_not_a_static_flag():
    """P4: chain_valid must reflect reality, not a constant set at load."""
    L = Ledger(MemoryStore())
    e = L.append(mk("one"), created_at=1000.0)
    L.append(mk("two"), created_at=1001.0)
    assert L.is_intact(max_age=0) is True
    assert L.digest()["chain_valid"] is True
    # corrupt an in-memory sealed hash; a LIVE check must now report degraded
    e.hash = "0" * 64
    assert L.is_intact(max_age=0) is False
    assert L.digest()["chain_valid"] is False
