# backend/tests/test_sql_store.py
"""Portable SqliteStore satisfies the LedgerStore contract and isolates tenants —
the chain runs off-AWS, stdlib only."""
from forward_ledger import Kind, Ledger, Prediction
from forward_ledger.sql_store import SqliteStore


def _pred(d, asm=None):
    return Prediction(decision=d, branches=["s", "x"], weights=[0.6, 0.4], survivor=0,
                      confidence=0.6, why="w", watch="t", kind=Kind.FORWARD,
                      oracle_ref="seed:" + d, assumptions=asm or [])


def test_roundtrip_durable_and_chain_valid(tmp_path):
    db = str(tmp_path / "l.db")
    L = Ledger(SqliteStore(path=db, tenant="acme"))
    e = L.append(_pred("alpha", asm=["demand holds"]), created_at=1.0)
    L.append(_pred("beta"), created_at=1.0)
    L.resolve(e.id, survived=False, ref="oracle:x", at=9.0)
    # reload from a fresh store instance -> durability + ordering + integrity
    L2 = Ledger(SqliteStore(path=db, tenant="acme"))
    assert [x.prediction["decision"] for x in L2.all()] == ["alpha", "beta"]
    assert L2.verify() is True
    assert L2.by_id(e.id).survived is False
    assert L2.assumption_rows() and L2.counterfactual_rows()


def test_tenant_isolation(tmp_path):
    db = str(tmp_path / "l.db")
    Ledger(SqliteStore(path=db, tenant="acme")).append(_pred("acme-secret"), created_at=1.0)
    Ledger(SqliteStore(path=db, tenant="globex")).append(_pred("globex-secret"), created_at=1.0)
    assert [x.prediction["decision"] for x in Ledger(SqliteStore(path=db, tenant="acme")).all()] == ["acme-secret"]
    assert [x.prediction["decision"] for x in Ledger(SqliteStore(path=db, tenant="globex")).all()] == ["globex-secret"]
