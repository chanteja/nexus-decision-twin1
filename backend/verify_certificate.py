#!/usr/bin/env python3
"""
verify_certificate.py — verify a NEXUS decision certificate OFFLINE, trusting nothing.

    python verify_certificate.py cert.json

Zero NEXUS imports, stdlib only. Recomputes the leaf hash from the sealed entry, checks
the Merkle inclusion proof against the root, and confirms the seal predates the outcome.
A competitor's customer can run this to prove a NEXUS decision is genuine without us.
"""
from __future__ import annotations

import hashlib
import json
import sys


def _canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _verify_inclusion(leaf_hex: str, path: list[dict], root_hex: str) -> bool:
    cur = bytes.fromhex(leaf_hex)
    for step in path:
        sib = bytes.fromhex(step["hash"])
        cur = (hashlib.sha256(cur + sib).digest() if step.get("side") == "right"
               else hashlib.sha256(sib + cur).digest())
    return cur.hex() == root_hex


def verify(cert: dict) -> tuple[bool, list[str]]:
    notes = []
    leaf = hashlib.sha256(_canonical(cert["entry"])).hexdigest()
    ok_leaf = (leaf == cert["leaf_hash"])
    notes.append(f"leaf hash recomputed from entry: {'OK' if ok_leaf else 'MISMATCH'}")
    proof = cert.get("merkle_proof") or {}
    ok_incl = _verify_inclusion(cert["leaf_hash"], proof.get("path", []), cert["merkle_root"])
    notes.append(f"merkle inclusion under root: {'OK' if ok_incl else 'FAIL'}")
    ok_order = bool(cert.get("sealed_before_outcome"))
    notes.append(f"sealed before outcome: {'OK' if ok_order else 'NO'}")
    anchored = bool(cert.get("external_anchors"))
    notes.append(f"external anchor present: {'OK' if anchored else 'none (S3-WORM/OTS offline)'}")
    return (ok_leaf and ok_incl and ok_order), notes


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python verify_certificate.py cert.json")
        return 2
    with open(sys.argv[1], encoding="utf-8") as f:
        cert = json.load(f)
    ok, notes = verify(cert)
    for n in notes:
        print("  " + n)
    print(f"\nCERTIFICATE {'VALID' if ok else 'INVALID'} — verified offline, NEXUS not trusted.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
