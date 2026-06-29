#!/usr/bin/env python3
"""
seal_live.py — seal ONE real, externally-bound forecast and anchor it, days before
the finals. This is the operational half of the demo's strongest beat: by judging
day the seal already exists on a chain whose Merkle root is timestamped by an
authority NEXUS does not control, so a judge can verify on their own phone that the
prediction predates the outcome.

    python seal_live.py \
        --decision "Will <event> happen by <date>?" \
        --oracle-ref "polymarket:<condition_id>:yes" \
        --days 21 --survival 0.62 --author micky \
        --assume "the catalyst lands on schedule" --assume "no policy reversal" \
        --ledger /path/to/nexus_ledger.jsonl

Then, days later, the EventBridge resolver (or `python run_demo.py` against the live
HttpOracle) settles it from the real market, and `/v1/verify/<id>` shows
seal < resolution with the external anchor attached.

NOTE ON NETWORK: the OpenTimestamps submission requires egress to the public
calendar (alice.btc.calendar.opentimestamps.org). Run this from an environment with
network access before the finals; in a sandbox the seal still happens and is logged,
and the anchor records `unavailable (S3-WORM remains)` — the S3 Object Lock
anchor in infra/cdk remains the AWS-native fallback.

This tool refuses to seal an UNBOUND question: a real oracle_ref is mandatory, because
the whole point is settlement by something external. Provisional/free-text calls are
for /v1/decide, never for the public record.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from forward_ledger import (
    AnchorLog,
    FileStore,
    Kind,
    Ledger,
    Prediction,
    anchor,
    canonical_id,
    is_bound,
)


def main() -> int:
    ap = argparse.ArgumentParser(description="Seal one real bound forecast and anchor it.")
    ap.add_argument("--decision", required=True, help="the question, in words")
    ap.add_argument("--oracle-ref", required=True,
                    help="external settleable identity, e.g. polymarket:<cond>:yes / kalshi:<ticker> / fred:<series>:>:<x>")
    ap.add_argument("--days", type=float, default=21.0, help="days until the oracle can settle it")
    ap.add_argument("--survival", type=float, default=0.6, help="your survival probability for the survivor branch, 0..1")
    ap.add_argument("--author", default="house")
    ap.add_argument("--domain", default="general")
    ap.add_argument("--assume", action="append", default=[], help="repeatable: a named assumption the call rests on")
    ap.add_argument("--ledger", default=os.environ.get("NEXUS_LEDGER_PATH", "/tmp/nexus_ledger.jsonl"))
    ap.add_argument("--no-anchor", action="store_true", help="seal only; skip the external anchor step")
    args = ap.parse_args()

    if not is_bound(args.oracle_ref):
        print("refusing to seal: --oracle-ref is empty. The public record takes BOUND questions only.")
        return 2

    p = max(0.0001, min(0.9999, args.survival))
    L = Ledger(FileStore(args.ledger))
    pred = Prediction(
        decision=args.decision,
        branches=[args.decision + " — happens", args.decision + " — does not"],
        weights=[round(p, 4), round(1 - p, 4)],
        survivor=0, confidence=round(p, 4),
        why="sealed live before the outcome exists", watch="settled by the external oracle, not by us",
        author=args.author, domain=args.domain, model="manual-live-seal", kind=Kind.FORWARD,
        resolves_at=time.time() + 86400 * args.days,
        oracle="http", oracle_ref=args.oracle_ref, assumptions=args.assume,
    )
    e = L.append(pred)
    d = L.digest()

    print("\n── SEALED ────────────────────────────────────────────")
    print(f"  entry id     : {e.id}")
    print(f"  canonical q  : {canonical_id(args.decision, args.oracle_ref)}")
    print(f"  entry hash   : {e.hash}")
    print(f"  merkle root  : {d['merkle_root']}")
    print(f"  resolves at  : {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime(pred.resolves_at))}")
    print(f"  chain valid  : {d['chain_valid']}")
    print(f"  assumptions  : {args.assume or '(none)'}")

    if not args.no_anchor:
        a = anchor(L, AnchorLog(args.ledger + ".anchor"))
        ev = a["anchored"]
        print("\n── ANCHORED ──────────────────────────────────────────")
        print(f"  merkle root  : {ev['merkle_root']}")
        print(f"  ots status   : {ev['ots_status']}")
        if ev.get("ots"):
            print(f"  calendar     : {ev['ots'].get('calendar')}")
            print("  → save the returned .ots proof; at the finals a judge verifies it independently.")
        else:
            print("  → no network for OpenTimestamps here; run from a connected env before finals.")
            print("    The S3 Object Lock (WORM) anchor in infra/cdk remains the AWS-native fallback.")

    print(f"\nVerify any time:  GET /v1/verify/{e.id}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
