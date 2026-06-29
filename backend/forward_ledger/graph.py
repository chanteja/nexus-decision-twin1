# backend/forward_ledger/graph.py
"""
The Reality Graph — a typed entity/influence graph, not a string of beads.

v11's /v1/graph returned edges = [(entry[i] -> entry[i+1])]: chain order rendered as
a line. There were no entity types and no causal structure, so "which assumptions
keep breaking?" or "which authors consistently alter reality?" could not be asked.

This builds a property graph over the record:

  node types : Question · Prediction · Outcome · Author
  edge types : FORECASTS (Author -> Prediction)
               ON        (Prediction -> Question)
               SETTLED_BY(Question  -> Outcome)
               CONTESTS  (Prediction -> Prediction)  # same question, both pending

Predictions accrete onto canonical Questions (questions.canonical_id), so the graph
is the network's accretion structure made visible. In production this lives in Amazon
Neptune; the in-memory build here keeps it demo-able with zero infra, same contract.
"""
from __future__ import annotations

from collections import defaultdict

from .calibration import _survival_prob
from .ledger import Kind, Ledger
from .questions import canonical_id
from .trust import author_weight

NODE_TYPES = ["Question", "Prediction", "Outcome", "Author"]
EDGE_TYPES = ["FORECASTS", "ON", "SETTLED_BY", "CONTESTS"]


def build_graph(ledger: Ledger, limit: int = 400) -> dict:
    entries = ledger.all()[-limit:]
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    trust_cache: dict[str, float] = {}

    def put(nid: str, ntype: str, **attrs) -> None:
        if nid not in nodes:
            nodes[nid] = {"id": nid, "type": ntype, **attrs}
        else:
            nodes[nid].update(attrs)

    def tw(author: str) -> float:
        if author not in trust_cache:
            trust_cache[author] = round(author_weight(ledger, author), 4)
        return trust_cache[author]

    by_question: dict[str, list[str]] = defaultdict(list)

    for e in entries:
        p = e.prediction
        qid = canonical_id(p.get("decision", ""), p.get("oracle_ref", ""))
        author = p.get("author", "anon")
        pid = "p:" + e.id

        put(qid, "Question", label=p.get("decision", "")[:72],
            domain=p.get("domain", "general"), kind=p.get("kind"))
        put(pid, "Prediction", survivor=p.get("survivor", 0),
            confidence=round(_survival_prob(e), 4), status=e.status,
            sealed_at=e.created_at)
        put("a:" + author, "Author", label=author, trust=tw(author))

        edges.append({"type": "FORECASTS", "source": "a:" + author, "target": pid})
        edges.append({"type": "ON", "source": pid, "target": qid})

        if e.status == "resolved":
            oid = "o:" + qid
            put(oid, "Outcome", survived=bool(e.survived),
                resolved_at=e.resolved_at)
            edges.append({"type": "SETTLED_BY", "source": qid, "target": oid})
        else:
            by_question[qid].append(pid)

    # CONTESTS: pending predictions on the same question are in tension
    for qid, pids in by_question.items():
        for i in range(len(pids) - 1):
            edges.append({"type": "CONTESTS", "source": pids[i], "target": pids[i + 1]})

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "node_types": NODE_TYPES,
        "edge_types": EDGE_TYPES,
        "counts": {t: sum(1 for n in nodes.values() if n["type"] == t) for t in NODE_TYPES},
    }


def movers(ledger: Ledger, top: int = 10) -> dict:
    """Authors who consistently alter reality: highest trust over >=2 resolved calls.
    A graph query the v11 line could never answer."""
    resolved = ledger.resolved(Kind.FORWARD)
    by_author: dict[str, int] = defaultdict(int)
    for e in resolved:
        by_author[e.prediction.get("author", "anon")] += 1
    out = [{"author": a, "resolved": n, "trust": round(author_weight(ledger, a), 4)}
           for a, n in by_author.items() if n >= 2]
    out.sort(key=lambda x: x["trust"], reverse=True)
    return {"reality_movers": out[:top]}
