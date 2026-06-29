#!/usr/bin/env python3
"""
run_demo.py — boot the NEXUS Decision Twin backend locally, zero AWS.

    python run_demo.py            # serve on :8000 (point the landing at ?api=http://localhost:8000)
    python run_demo.py --check    # run the full seal→wait→prove→verify flow and print it, then exit

The --check flow is the on-stage script in miniature: seal a decision, show its
seal predates resolution, fast-forward the demo clock, settle by oracle, watch the
forward accuracy appear from resolved rows only.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def check():
    os.environ.setdefault("NEXUS_DEMO", "1")
    os.environ.setdefault("NEXUS_DEMO_HORIZON", "1")
    os.environ.setdefault("NEXUS_LEDGER_PATH", "/tmp/nexus_demo_check.jsonl")
    if os.path.exists(os.environ["NEXUS_LEDGER_PATH"]):
        os.remove(os.environ["NEXUS_LEDGER_PATH"])
    from forward_ledger import FileStore, Ledger, calibration, demo_oracle, resolve_due, seed
    L = Ledger(FileStore(os.environ["NEXUS_LEDGER_PATH"]))
    seed(L, demo=True, demo_horizon_s=1.0)
    orc = demo_oracle()

    print("\n── SEAL ──────────────────────────────────────────────")
    d = L.digest()
    print(f"  entries sealed : {d['entries']}")
    print(f"  merkle root    : {d['merkle_root'][:24]}…  (publish this to a public anchor)")
    print(f"  chain valid    : {d['chain_valid']}")
    pend = [e for e in L.pending() if e.prediction['kind'] == 'forward']
    print(f"  forward pending: {len(pend)}  (sealed NOW, outcomes do not exist yet)")
    e0 = pend[0]
    print(f"  example sealed : '{e0.prediction['decision']}'  hash {e0.hash[:16]}…")

    print("\n── CALIBRATION (before any resolution) ───────────────")
    c = calibration(L)
    print(f"  forward resolved: {c['forward']['n']}  → {c['headline']}")

    print("\n── WAIT for the demo clock, then PROVE ───────────────")
    time.sleep(1.2)
    settled = resolve_due(L, orc)
    print(f"  oracle settled  : {len(settled)} forward entries")
    for s in settled:
        e = L.by_id(s['id'])
        ok = (e.created_at < e.resolved_at)
        print(f"    • {e.prediction['decision'][:48]:48s} survived={s['survived']}  "
              f"sealed<resolved={ok}  evidence={s['evidence']}")

    print("\n── CALIBRATION (forward, from RESOLVED rows only) ────")
    c = calibration(L)
    f = c['forward']
    print(f"  forward n={f['n']}  accuracy={f['accuracy']}  brier={f['brier']}")
    print(f"  backtest n={c['backtest']['n']}  (hindsight, context only — never the headline)")
    print(f"  chain still valid: {L.verify()}\n")

    print("── v13 · THE COUNTERFACTUAL CORPUS (roads not taken, scored) ──")
    from forward_ledger import (
        AnchorLog,
        anchor,
        assumptions_corpus,
        build_graph,
        counterfactuals,
        first_to_call,
        reliability_band,
    )
    cf = counterfactuals(L)
    print(f"  branch rows scored : {cf['total_branches']}  "
          f"(scored untaken: {cf['scored_untaken']})  [weak signal — see assumptions]")

    print("\n── v13 · THE ASSUMPTION LEDGER (the honest causal asset) ──")
    asm = assumptions_corpus(L)
    print(f"  assumption rows : {asm['total_rows']}  distinct: {asm['distinct']}")
    for a_ in asm["assumptions"][:3]:
        print(f"    • falsified {a_['failed_with']}/{a_['seen']}  "
              f"(rate {a_['falsification_rate']})  \u201c{a_['assumption'][:48]}\u201d")
    print("  \u2192 beliefs sealed before the outcome, ranked by how often reality broke them.")

    print("\n── v13 · FIRST TO BE RIGHT (provable only with seal times) ──")
    fm = first_to_call(L)
    for m in fm["first_movers"][:3]:
        print(f"    • {m['author']:12s} first-right\u00d7{m['first_right']}  lead {round(m['total_lead'],1)}s")

    print("\n── v13 · RECALIBRATION BAND (uncertainty shown on purpose) ──")
    rb = reliability_band(L)
    print(f"  resolved forward {rb['resolved_forward']} / {rb['needed']} needed  "
          f"\u00b7 curve significant: {rb['significant']}")

    print("\n── v13 · THE REALITY GRAPH (typed, not a line) ───────")
    g = build_graph(L)
    print(f"  nodes by type : {g['counts']}")
    print(f"  edge types    : {g['edge_types']}")

    print("\n── v13 · EXTERNAL ANCHOR (verify without trusting us) ─")
    a = anchor(L, AnchorLog(os.environ['NEXUS_LEDGER_PATH'] + '.anchor'))
    ev = a["anchored"]
    print(f"  merkle root anchored : {ev['merkle_root'][:24]}…")
    print(f"  ots status           : {ev['ots_status']}")
    print("  → in prod this root is mirrored to S3 Object Lock (WORM), which NEXUS cannot rewrite.")
    print("\n── v14 · THE REALITY ARENA (humans vs AI, one legible score) ──")
    import time as _t

    from forward_ledger import arena_oracle, reality_score, resolve_live, seed_arena
    seed_arena(L)                                   # aged ~30-day cohort
    orc = arena_oracle(orc)                         # merge the arena answer key
    _now = _t.time()
    resolve_due(L, orc, now=_now)                   # beat 1: the already-due questions
    board = reality_score(L)["leaderboard"]
    print("  beat 1 — board fills (live question still held):")
    for r in [b for b in board if b["scored"]][:5]:
        print(f"    #{r['rank']} {r['forecaster']:13s} {r['kind']:8s} score {r['reality_score']}  acc {r['accuracy']}")
    resolve_live(L, orc, now=_now)                  # beat 2: release the live question
    board = reality_score(L)["leaderboard"]
    print("  beat 2 — reality arrives, scores move:")
    for r in [b for b in board if b["scored"]][:5]:
        print(f"    #{r['rank']} {r['forecaster']:13s} {r['kind']:8s} score {r['reality_score']}  acc {r['accuracy']}  first-right {r['first_right']}")
    print("  \u2192 a judge verifies any one of these seals on their phone: GET /v1/verify/<id>/qr")
    print("  \u2192 the arena is a backdated DEMO cohort (illustrative); the genuinely anchored")
    print("    verify-on-phone proof is a seal_live.py entry. Spectacle vs proof, kept honest.\n")

    print("\n══ THE AHA · the living Decision Graph (one broken assumption) ══")
    from forward_ledger import enterprise_scenario, propagate, seed_enterprise
    seed_enterprise(L)
    sc = enterprise_scenario()
    print(f"  scenario  : {sc['failed_decision']}")
    print(f"  belief    : “{sc['trigger_assumption']}”")
    print(f"  evidence  : {sc['evidence']}")
    prop = propagate(L)
    s_ = prop["summary"]
    print("  cascade   : " + " → ".join(prop["cascade"]))
    print(f"  result    : {s_['already_failed']} failed · {s_['now_at_risk']} now at risk · {s_['unaffected']} untouched")
    print("  what to change (ranked by business impact):")
    for r in prop["recommended_changes"]:
        print(f"    #{r['rank']} [{r['impact_score']:>5}] {r['decision'][:42]:42s} → {r['action'][:46]}…")
    lrn = prop["learning"]
    print(f"  the twin learned: falsification {lrn['falsification_rate_before']} → {lrn['falsification_rate_after']}  ({lrn['decisions_rescored']} decisions re-scored)\n")

    print("\n══ FUTURE EXPLORER · a REAL simulation (learned probabilities) ══")
    from forward_ledger import explore_decision, value_summary
    sim = explore_decision(L, "Open the Mexico expansion next?",
                           ["Brazil consumer demand grows more than 18% YoY",
                            "BRL/USD stays within 10% of plan", "we can hire 40 LATAM roles"],
                           base_survival=0.59, n=8000, seed=7)
    d = sim["distribution"]
    print(f"  expected survival : {sim['expected_survival']}  (stdev {sim['stdev']})")
    print(f"  distribution      : worst {d['p10_worst']} \u00b7 expected {d['p50_expected']} \u00b7 best {d['p90_best']}")
    top = sim["drivers"][0]
    print(f"  pivotal belief    : \u201c{top['assumption'][:44]}\u201d  drives {round(top['variance_share']*100)}% of the variance")
    print("  \u2192 P(holds) is LEARNED from the record; a belief reality keeps breaking lowers every future bet.")

    print("\n══ BUSINESS IMPACT · measured from the record ══")
    val = value_summary(L)
    print("  " + val["headline"])
    if val["capital"]:
        print(f"  capital repriced  : ${val['capital']['capital_repriced_usd']:,} (estimate, model attached)")
    ev = val["estimated_value"]
    print(f"  review labour est : ${ev['labour_value_usd_per_year']:,}/yr  (inputs declared)\n")

    print("Every settled entry was sealed before it resolved. Nothing was graded by NEXUS.")


def serve():
    import uvicorn
    uvicorn.run("api.app:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), reload=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    check() if a.check else serve()
