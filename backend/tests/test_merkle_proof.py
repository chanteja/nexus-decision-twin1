# backend/tests/test_merkle_proof.py
"""Merkle inclusion proofs — verifiable WITHOUT trusting NEXUS (the moat primitive)."""
from forward_ledger import Kind, Ledger, MemoryStore, Prediction, verify_inclusion


def _mk(d):
    return Prediction(decision=d, branches=["a", "b"], weights=[0.6, 0.4], survivor=0,
                      confidence=0.6, why="w", watch="t", kind=Kind.FORWARD, oracle_ref="seed:" + d)


def test_every_entry_has_a_valid_inclusion_proof():
    # test odd and even tree sizes (the duplicate-last path must be exercised)
    for size in (1, 2, 3, 5, 8, 9):
        L = Ledger(MemoryStore())
        ids = [L.append(_mk(f"d{i}"), created_at=1.0 + i).id for i in range(size)]
        root = L.merkle_root()
        for eid in ids:
            pr = L.merkle_proof(eid)
            assert pr["merkle_root"] == root
            assert verify_inclusion(pr["leaf"], pr["path"], root) is True


def test_a_forged_leaf_fails_verification():
    L = Ledger(MemoryStore())
    eid = L.append(_mk("real"), created_at=1.0).id
    L.append(_mk("other"), created_at=2.0)
    pr = L.merkle_proof(eid)
    forged = "f" * 64
    assert verify_inclusion(forged, pr["path"], pr["merkle_root"]) is False


def test_proof_breaks_under_wrong_root():
    L = Ledger(MemoryStore())
    eid = L.append(_mk("x"), created_at=1.0).id
    L.append(_mk("y"), created_at=2.0)
    pr = L.merkle_proof(eid)
    assert verify_inclusion(pr["leaf"], pr["path"], "0" * 64) is False


def test_certificate_verifies_offline_and_detects_tampering():
    import importlib.util
    import os
    # load the standalone verifier as a module (it has zero NEXUS imports)
    path = os.path.join(os.path.dirname(__file__), "..", "verify_certificate.py")
    spec = importlib.util.spec_from_file_location("verify_certificate", path)
    vc = importlib.util.module_from_spec(spec); spec.loader.exec_module(vc)

    L = Ledger(MemoryStore())
    eid = L.append(_mk("seal-me"), created_at=1000.0).id
    L.append(_mk("noise"), created_at=1001.0)
    e = L.by_id(eid)
    proof = L.merkle_proof(eid)
    cert = {
        "entry": e.core(), "leaf_hash": e.hash,
        "merkle_proof": proof, "merkle_root": proof["merkle_root"],
        "external_anchors": [{"merkle_root": proof["merkle_root"]}],
        "sealed_before_outcome": True,
    }
    ok, notes = vc.verify(cert)
    assert ok is True, notes
    # tamper the sealed content -> leaf hash no longer matches -> invalid
    cert["entry"]["prediction"]["decision"] = "edited after sealing"
    bad, _ = vc.verify(cert)
    assert bad is False
