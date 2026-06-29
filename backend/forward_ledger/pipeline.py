# backend/forward_ledger/pipeline.py
"""
The Decision pipeline, end to end:

  Intent → Knowledge Extraction → Decision Memory → Graph (retrieve/create) →
  Future Explorer → Recommendation → Reality Verification → Learning

Exploration only — it never auto-commits. Sealing (Reality Verification) is a separate,
deliberate step (POST /v1/commit), preserving the human-in-the-loop invariant.
"""
from __future__ import annotations

from .assumptions import assumptions_corpus
from .knowledge import extract_assumptions
from .ledger import Ledger
from .memory import assign_graph_id, find_graph, graph_decisions
from .recommendation import recommend
from .simulation import explore_decision

STAGES = ["intent", "knowledge_extraction", "decision_memory", "graph",
          "future_explorer", "recommendation", "reality_verification", "learning"]


def run_pipeline(ledger: Ledger, decision: str, constraint: str = "",
                 assumptions: list[str] | None = None, n: int = 4000, seed: int = 0) -> dict:
    # 1 · intent
    intent = {"decision": decision, "constraint": constraint}

    # 2 · knowledge extraction
    asms, source = extract_assumptions(decision, assumptions)

    # 3 · decision memory + 4 · graph (retrieve or create)
    gid = assign_graph_id(ledger, decision, asms)
    reused = find_graph(ledger, asms) is not None
    related = [e.prediction.get("decision") for e in graph_decisions(ledger, gid)]

    # 5 · future explorer (learned-probability simulation)
    sim = explore_decision(ledger, decision, asms, n=max(200, min(50000, n)), seed=seed)

    # 6 · recommendation
    rec = recommend(decision, sim, asms)

    # 8 · learning (how the record's experience shapes this decision's beliefs)
    corpus = {r["assumption"]: r for r in assumptions_corpus(ledger)["assumptions"]}
    learning = [{"assumption": a,
                 "falsification_rate": corpus.get(a, {}).get("falsification_rate"),
                 "seen_in_failures": corpus.get(a, {}).get("failed_with")} for a in asms]

    return {
        "pipeline": STAGES,
        "intent": intent,
        "knowledge_extraction": {"assumptions": asms, "source": source},
        "decision_memory": {"graph_id": gid, "reused_existing_graph": reused,
                            "related_decisions": related},
        "future_explorer": sim,
        "recommendation": rec,
        "reality_verification": {
            "status": "not sealed (exploration)",
            "next_step": "POST /v1/commit with resolves_at + oracle_ref to seal this "
                         "decision on the record before its outcome exists",
            "graph_id": gid,
        },
        "learning": learning,
        "honesty": "Exploration only — sealing is a separate, deliberate step.",
    }
