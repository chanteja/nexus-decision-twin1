# backend/tests/test_hardening.py
"""SSRF guard on the oracle fetch, and least-privilege local file permissions."""
import os
import stat

from forward_ledger.oracles import polymarket_resolver
from forward_ledger.store import FileStore


def test_oracle_ref_injection_is_rejected_without_network():
    # path-escape / SSRF attempts return None before any HTTP call is made
    for bad in ("polymarket:../../admin:yes",
                "polymarket:abc/def:yes",
                "polymarket:cond:maybe",
                "polymarket:cond",
                "polymarket:a b:yes",
                "polymarket:" + "x" * 200 + ":yes"):
        assert polymarket_resolver(bad) is None


def test_filestore_files_are_owner_only(tmp_path):
    p = tmp_path / "sub" / "ledger.jsonl"
    FileStore(str(p))
    if os.name != "nt":
        for fp in (str(p), str(p) + ".cf", str(p) + ".asm"):
            mode = stat.S_IMODE(os.stat(fp).st_mode)
            assert mode == 0o600, f"{fp} is {oct(mode)}, expected 0600"

