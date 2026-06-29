# backend/tests/test_incremental_verify.py
"""P2: checkpointed incremental verification — cold starts re-hash only the suffix after
the externally-anchored checkpoint, while still catching post-checkpoint tampering."""
from forward_ledger import Kind, Ledger, MemoryStore, Prediction, TamperError
from forward_ledger.store import FileStore


def _mk(d):
    return Prediction(decision=d, branches=["a", "b"], weights=[0.6, 0.4], survivor=0,
                      confidence=0.6, why="w", watch="t", kind=Kind.FORWARD, oracle_ref="seed:" + d)


def test_checkpoint_roundtrip_and_tail_count():
    s = MemoryStore(); L = Ledger(s)
    for i in range(5):
        L.append(_mk(f"d{i}"), created_at=1.0 + i)
    cp = L.checkpoint()
    assert cp["count"] == 5 and cp["head_hash"] == L.all()[-1].hash
    assert s.load_checkpoint()["merkle_root"] == L.merkle_root()
    assert s.tail()["seq"] == 4 and s.count() == 5


def test_incremental_verify_accepts_valid_chain(tmp_path):
    db = str(tmp_path / "l.jsonl")
    L = Ledger(FileStore(db))
    for i in range(6):
        L.append(_mk(f"d{i}"), created_at=1.0 + i)
    L.checkpoint()                                  # attest [0,6)
    L.append(_mk("d6"), created_at=99.0)            # one more after the checkpoint
    # reload with incremental verification: must pass
    L2 = Ledger(FileStore(db), verify_full=False)
    assert L2.verify() is True and len(L2.all()) == 7


def test_incremental_verify_catches_post_checkpoint_tampering(tmp_path):
    db = str(tmp_path / "l.jsonl")
    s = FileStore(db); L = Ledger(s)
    for i in range(4):
        L.append(_mk(f"d{i}"), created_at=1.0 + i)
    L.checkpoint()
    e = L.append(_mk("after"), created_at=50.0)     # seq 4, after the checkpoint
    # tamper the post-checkpoint entry directly in the store
    rows = s.load()
    rows[4]["prediction"]["decision"] = "edited after sealing"
    # rewrite the file with the tampered row
    import json
    with open(db, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    try:
        Ledger(s, verify_full=False)
        assert False, "tampered post-checkpoint entry went undetected"
    except TamperError:
        pass
