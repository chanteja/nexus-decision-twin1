# backend/api/app.py
"""
NEXUS — The Decision Twin API.

The internal /v1/* contract the landing and demo speak, beneath the product-facing
/twin/* surface (see api/twin.py). Both are served; neither breaks the other.

  GET  /v1/status        — telemetry (real; never fabricated)
  GET  /v1/graph         — TYPED reality graph (Questions/Predictions/Outcomes/Authors)
  GET  /v1/movers        — authors who consistently alter reality (graph query)
  POST /v1/decide        — reason + LEARN + SEAL: recalibrates against the resolved
                           curve, blends toward question consensus, then commits.
  POST /v1/commit        — a visitor stakes a prediction onto the public record
  GET  /v1/calibration   — accuracy/Brier from RESOLVED rows only + the fitted
                           reliability curve (the flywheel state)
  GET  /v1/counterfactuals — the scored roads-not-taken corpus (the headline asset)
  GET  /v1/ledger        — the public record (verifiable; carries the Merkle root)
  GET  /v1/verify/{id}   — proof an entry was sealed before it resolved + anchored
  POST /v1/prove         — settle all due entries now, then anchor the new head
  POST /v1/anchor        — publish the Merkle root to an external time authority
  GET  /v1/trust         — the Trust Graph leaderboard
  GET  /v1/markets       — calibration-weighted consensus, canonical-question keyed

Everything degrades gracefully and runs with zero AWS. Set NEXUS_DDB_TABLE
(DynamoDB) and BEDROCK_MODELS to go live; the contract does not change.
"""
from __future__ import annotations

import io
import os
import pathlib
import time
import uuid

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from forward_ledger import (
    CONSENSUS_AUTHOR,
    TRIGGER_ASSUMPTION,
    AnchorLog,
    Kind,
    Ledger,
    Prediction,
    anchor,
    apply_learning,
    arena_oracle,
    assign_graph_id,
    assumptions_corpus,
    build_graph,
    build_store,
    calibration,
    canonical_id,
    consensus_forecast,
    counterfactuals,
    demo_oracle,
    enterprise_scenario,
    first_to_call,
    markets,
    movers,
    propagate,
    reality_score,
    register_tenant,
    reliability_band,
    resolve_due,
    resolve_live,
    seed,
    seed_arena,
    seed_enterprise,
    trust_graph,
)
from forward_ledger import (
    decide as run_ensemble,
)
from forward_ledger.oracles import HttpOracle, SeedOracle, polymarket_resolver
from forward_ledger.store import default_path
from forward_ledger.store import valid_tenant as _valid_tenant

from .auth import Principal, effective_tenant, log_audit, require_auth
from .config import get_settings
from .logging_config import setup_logging

settings = get_settings()
settings.validate_boot()
log = setup_logging()

START = time.time()
DATA = os.environ.get("NEXUS_LEDGER_PATH", default_path("ledger.jsonl"))
DEMO = os.environ.get("NEXUS_DEMO", "1") == "1"
ARENA = os.environ.get("NEXUS_ARENA", "1") == "1"        # seed the Human-vs-AI board
ARENA_HORIZON = float(os.environ.get("NEXUS_ARENA_HORIZON", "6"))
ENTERPRISE = os.environ.get("NEXUS_ENTERPRISE", "1") == "1"   # seed the strategy scenario


DEFAULT_TENANT = settings.default_tenant
_ledgers: dict[str, Ledger] = {}


def get_ledger(tenant: str | None = None) -> Ledger:
    """Return the (tenant-isolated) ledger for a tenant, building it on first use.
    The default tenant is the seeded product/demo surface; other tenants get their
    own isolated store (separate DynamoDB partition, or a separate file locally)."""
    t = tenant or DEFAULT_TENANT
    if not _valid_tenant(t):
        raise HTTPException(400, f"invalid tenant id: {t!r}")
    lg = _ledgers.get(t)
    if lg is None:
        path = DATA if t == DEFAULT_TENANT else None
        lg = Ledger(build_store(tenant=t, path=path))
        register_tenant(lg.store)        # enroll for the autonomous per-tenant loop
        _ledgers[t] = lg
    return lg


def tenant_ledger(principal: Principal = Depends(require_auth)) -> Ledger:
    """Auth + tenant resolution for reads. Authenticates the caller (in production) and
    returns THEIR tenant's ledger — so a read never crosses a tenant boundary and never
    silently serves the default tenant's record. In demo it returns the seeded default."""
    return get_ledger(principal.tenant)


def _build_oracle():
    if DEMO:
        return demo_oracle()
    return HttpOracle({"polymarket:": polymarket_resolver})


ledger = get_ledger()           # the default-tenant ledger: product surface + demo
oracle = _build_oracle()
anchor_log = AnchorLog(os.environ.get("NEXUS_ANCHOR_PATH", DATA + ".anchor"))
if DEMO and not ledger.all():
    seed(ledger, demo=True, demo_horizon_s=float(os.environ.get("NEXUS_DEMO_HORIZON", "8")))
if DEMO and ARENA:
    # The aged Human-vs-AI cohort (the spectacle). seed_arena is idempotent; the
    # oracle is extended with the arena answer key so /v1/prove can settle it.
    seed_arena(ledger, live_horizon_s=ARENA_HORIZON)
    oracle = arena_oracle(oracle if isinstance(oracle, SeedOracle) else None)
if DEMO and ENTERPRISE:
    # The connected enterprise-strategy decision set + the verified Brazil failure
    # that drives the live Decision Graph propagation (the aha). Idempotent.
    seed_enterprise(ledger)

_docs = {} if not settings.is_production else {"docs_url": None, "redoc_url": None, "openapi_url": None}
app = FastAPI(title="NEXUS · The Decision Twin Platform", version="19.0", **_docs)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

# The product surface: the five visible pillars. Everything in /v1/* below is the
# internal implementation those pillars compose. The landing/demo speak /v1/*; the
# product speaks /twin/*. Both are served; neither breaks the other.
import math as _math  # noqa: E402


@app.exception_handler(RequestValidationError)
async def _validation_error_handler(request: Request, exc: RequestValidationError):
    """Return a clean 422 even when the rejected input contained NaN/Inf — FastAPI's
    default error body echoes the input value, and a non-finite float there is not
    JSON-serialisable (would surface as a 500). We sanitise the error context."""
    def _clean(o):
        if isinstance(o, float):
            return o if _math.isfinite(o) else str(o)
        if isinstance(o, dict):
            return {k: _clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [_clean(x) for x in o]
        if isinstance(o, bytes):
            return o.decode("utf-8", "replace")
        # stringify anything else (e.g. exception objects in a validator's ctx) so the
        # 422 body is always JSON-serialisable
        return o if isinstance(o, (str, int, bool, type(None))) else str(o)
    return JSONResponse(status_code=422, content={"detail": _clean(exc.errors())})


from .twin import PILLARS  # noqa: E402
from .twin import router as twin_router  # noqa: E402

app.include_router(twin_router)


@app.middleware("http")
async def _request_context(request: Request, call_next):
    rid = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = rid
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("request_error", extra={"request_id": rid,
                      "method": request.method, "path": request.url.path})
        raise
    response.headers["X-Request-ID"] = rid
    log.info("request", extra={"request_id": rid, "method": request.method,
             "path": request.url.path, "status": response.status_code,
             "dur_ms": round((time.perf_counter() - start) * 1000, 2)})
    return response


_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}


@app.middleware("http")
async def _default_deny(request: Request, call_next):
    """Defense in depth: no mutating request is served without an auth credential when
    auth is enabled — even if a route forgot its dependency. Full key validation still
    happens in require_auth; this only guarantees default-deny at the edge."""
    if request.method in _MUTATING and settings.auth_required:
        has_cred = bool(request.headers.get("x-api-key")) or \
            (request.headers.get("authorization", "").lower().startswith("bearer "))
        if not has_cred:
            return JSONResponse({"detail": "authentication required"}, status_code=401,
                                headers={"WWW-Authenticate": "Bearer"})
    return await call_next(request)


@app.get("/healthz")
def healthz():
    """Liveness + chain-integrity probe (unauthenticated, no secrets). Uses the
    maintained validity flag (verified at load) — O(1), so frequent load-balancer
    probes never re-hash the whole chain."""
    try:
        ok = bool(ledger.is_intact(max_age=0))   # forced live re-verification
    except Exception:
        ok = False
    return {"status": "ok" if ok else "degraded", "chain_valid": ok, "version": app.version}


@app.get("/version")
def version():
    return {"name": "NEXUS Decision Twin", "version": app.version, "env": settings.env}


# ── idempotency (Stripe-grade DX): a retried seal must never double-write ──────
# In-process per-(tenant,key) cache; back with DynamoDB/Redis in a multi-instance
# deployment. Bounded to avoid unbounded growth.
_IDEMPOTENCY: dict[tuple[str, str], dict] = {}


def _idem_get(tenant: str, key: str | None) -> dict | None:
    return _IDEMPOTENCY.get((tenant, key)) if key else None


def _idem_put(tenant: str, key: str | None, resp: dict) -> None:
    if not key:
        return
    if len(_IDEMPOTENCY) > 10000:
        _IDEMPOTENCY.clear()
    _IDEMPOTENCY[(tenant, key)] = resp


# ── schemas ──────────────────────────────────────────────────────────────
class DecideIn(BaseModel):
    decision: str = Field(min_length=1, max_length=settings.max_text)
    constraint: str = Field(default="", max_length=settings.max_text)
    branches: int = Field(default=7, ge=2, le=settings.max_branches)
    tenant: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    seed: int | None = None
    resolves_at: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    oracle_ref: str = Field(default="", max_length=256)
    author: str = Field(default="anon", min_length=1, max_length=128)
    domain: str = Field(default="general", min_length=1, max_length=64)
    assumptions: list[str] = Field(default_factory=list, max_length=settings.max_assumptions)

    @field_validator("assumptions")
    @classmethod
    def _cap_assumptions(cls, v: list[str]) -> list[str]:
        s = get_settings()
        for a in v:
            if len(a) > s.max_text:
                raise ValueError("assumption too long")
        return v


class CommitIn(BaseModel):
    decision: str = Field(min_length=1, max_length=settings.max_text)
    weights: list[float] = Field(min_length=1, max_length=settings.max_branches)
    survivor: int = Field(ge=0, le=settings.max_branches - 1)
    confidence: float = Field(ge=0.0, le=1.0, allow_inf_nan=False)
    why: str = Field(default="", max_length=settings.max_text)
    watch: str = Field(default="", max_length=settings.max_text)
    tenant: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    author: str = Field(default="anon", min_length=1, max_length=128)
    domain: str = Field(default="general", min_length=1, max_length=64)
    resolves_at: float = Field(ge=0, allow_inf_nan=False)
    oracle_ref: str = Field(min_length=1, max_length=256)
    branches: list[str] = Field(default_factory=list, max_length=settings.max_branches)
    assumptions: list[str] = Field(default_factory=list, max_length=settings.max_assumptions)

    @field_validator("weights")
    @classmethod
    def _weights_finite(cls, v: list[float]):
        import math
        if any(not math.isfinite(float(x)) for x in v):
            raise ValueError("weights must be finite (no NaN/Inf)")
        return v

    @field_validator("survivor")
    @classmethod
    def _survivor_in_range(cls, v: int, info):
        w = info.data.get("weights") or []
        if w and v >= len(w):
            raise ValueError("survivor index out of range")
        return v


# ── endpoints ─────────────────────────────────────────────────────────────
@app.get("/v1/status")
def status(lg: Ledger = Depends(tenant_ledger)):
    d = lg.digest()
    return {
        "status": "ready",
        "uptime_s": int(time.time() - START),
        # the product surface: five visible pillars, each hiding its modules.
        "pillars": PILLARS,
        # kept for back-compat with older landing builds; these are internal modules,
        # not product concepts, and are no longer surfaced to users.
        "engines": [m for mods in PILLARS.values() for m in mods],
        "events": d["entries"],
        "chain_valid": d["chain_valid"],
        "merkle_root": d["merkle_root"],
        "source": "live",
    }


@app.get("/v1/graph")
def graph(limit: int = 400, lg: Ledger = Depends(tenant_ledger)):
    limit = min(max(1, limit), 2000)
    # the typed reality graph: Questions, Predictions, Outcomes, Authors and the
    # influence edges between them — not chain order rendered as a line.
    return build_graph(lg, limit=limit)


@app.get("/v1/movers")
def v1_movers(top: int = 10, lg: Ledger = Depends(tenant_ledger)):
    # "which authors consistently alter reality?" — a graph query the line could not answer
    return movers(lg, top=top)


@app.get("/v1/propagate")
def v1_propagate(assumption: str = TRIGGER_ASSUMPTION, evidence: str = "",
                 lg: Ledger = Depends(tenant_ledger)):
    # the living Decision Graph: a falsified assumption re-scores every connected
    # decision and ranks the revisions by business impact. The aha, as raw data.
    return propagate(lg, assumption=assumption, evidence=evidence)


@app.get("/v1/scenario")
def v1_scenario(principal: Principal = Depends(require_auth)):
    return enterprise_scenario()


@app.post("/v1/decide")
def v1_decide(request: Request, body: DecideIn, principal: Principal = Depends(require_auth),
              idempotency_key: str | None = Header(default=None)):
    tenant = effective_tenant(principal, body.tenant)
    cached = _idem_get(tenant, idempotency_key)
    if cached is not None:
        return {**cached, "idempotent_replay": True}
    lg = get_ledger(tenant)
    v = run_ensemble(body.decision, body.constraint, body.branches, body.seed)
    # close the flywheel: recalibrate against the resolved curve (L1) and blend
    # toward the calibration-weighted consensus of peers on this question (L3).
    v = apply_learning(v, lg, body.decision, body.oracle_ref)
    resp = {
        "survivor": v.survivor, "weights": v.weights, "confidence": v.confidence,
        "why": v.why, "watch": v.watch, "model": v.model, "branches": v.branches,
    }
    # the collapse IS the commitment: a resolvable decision is sealed as decided.
    # We seal the INDEPENDENT, recalibrated call (no consensus blending — independence
    # is the asset). If a crowd already exists on this bound question, we ALSO seal the
    # consensus as its OWN forecaster, so the record carries a second scoreboard:
    # crowd vs. this individual, each with its own resolved track record.
    if body.resolves_at and body.oracle_ref:
        pred = Prediction(
            decision=body.decision, branches=v.branches, weights=v.weights, survivor=v.survivor,
            confidence=v.confidence, why=v.why, watch=v.watch, author=body.author, domain=body.domain,
            model=v.model, kind=Kind.FORWARD, resolves_at=body.resolves_at,
            oracle="http" if not DEMO else "seed", oracle_ref=body.oracle_ref,
            assumptions=body.assumptions or [],
            graph_id=assign_graph_id(lg, body.decision, body.assumptions or []),
        )
        e = lg.append(pred)
        d = lg.digest()
        resp["ledger"] = {"events": d["entries"], "chain_valid": d["chain_valid"],
                          "entry": e.id, "merkle_root": d["merkle_root"], "sealed": True}

        cf = consensus_forecast(lg, body.decision, body.oracle_ref)
        if cf and not _consensus_already_sealed(lg, body.decision, body.oracle_ref):
            cw = [round(cf["survival"], 4), round(1 - cf["survival"], 4)]
            cpred = Prediction(
                decision=body.decision, branches=["consensus survives", "consensus fails"],
                weights=cw, survivor=0, confidence=cw[0],
                why="calibration-weighted crowd consensus", watch="competes against each individual",
                author=CONSENSUS_AUTHOR, domain=body.domain, model="nexus-consensus",
                kind=Kind.FORWARD, resolves_at=body.resolves_at,
                oracle="http" if not DEMO else "seed", oracle_ref=body.oracle_ref,
            )
            ce = lg.append(cpred)
            resp["consensus_forecaster"] = {"entry": ce.id, "survival": cf["survival"],
                                            "n_peers": cf["n_peers"], "author": CONSENSUS_AUTHOR}
        log_audit("decide.seal", principal, request, tenant=tenant,
                  entry=resp["ledger"]["entry"], oracle_ref=body.oracle_ref)
        _idem_put(tenant, idempotency_key, resp)
    return resp


def _consensus_already_sealed(lg: Ledger, decision: str, oracle_ref: str) -> bool:
    qid = canonical_id(decision, oracle_ref)
    for e in lg.pending():
        p = e.prediction
        if p.get("author") == CONSENSUS_AUTHOR and \
           canonical_id(p.get("decision", ""), p.get("oracle_ref", "")) == qid:
            return True
    return False


@app.post("/v1/commit")
def v1_commit(request: Request, body: CommitIn, principal: Principal = Depends(require_auth),
              idempotency_key: str | None = Header(default=None)):
    tenant = effective_tenant(principal, body.tenant)
    cached = _idem_get(tenant, idempotency_key)
    if cached is not None:
        return {**cached, "idempotent_replay": True}
    lg = get_ledger(tenant)
    pred = Prediction(
        decision=body.decision, branches=body.branches or [], weights=body.weights,
        survivor=body.survivor, confidence=body.confidence, why=body.why, watch=body.watch,
        author=body.author, domain=body.domain, kind=Kind.FORWARD,
        resolves_at=body.resolves_at, oracle="http" if not DEMO else "seed",
        oracle_ref=body.oracle_ref, assumptions=body.assumptions or [],
        graph_id=assign_graph_id(lg, body.decision, body.assumptions or []),
    )
    e = lg.append(pred)
    d = lg.digest()
    log_audit("commit.seal", principal, request, tenant=tenant, entry=e.id,
              oracle_ref=body.oracle_ref)
    resp = {"entry": e.id, "sealed_at": e.created_at, "merkle_root": d["merkle_root"],
            "chain_valid": d["chain_valid"], "verify": f"/v1/verify/{e.id}"}
    _idem_put(tenant, idempotency_key, resp)
    return resp


@app.get("/v1/calibration")
def v1_calibration(lg: Ledger = Depends(tenant_ledger)):
    return calibration(lg)


@app.get("/v1/ledger")
def v1_ledger(limit: int = 100, lg: Ledger = Depends(tenant_ledger)):
    limit = min(max(1, limit), 1000)
    es = lg.all()[-limit:]
    return {
        "digest": lg.digest(),
        "entries": [{
            "id": e.id, "seq": e.seq, "decision": e.prediction["decision"],
            "kind": e.prediction["kind"], "status": e.status,
            "predicted": e.prediction["weights"][e.prediction["survivor"]]
            if e.prediction.get("weights") else e.prediction.get("confidence"),
            "survived": e.survived, "sealed_at": e.created_at,
            "resolves_at": e.prediction.get("resolves_at"), "resolved_at": e.resolved_at,
            "hash": e.hash, "prev_hash": e.prev_hash, "author": e.prediction.get("author"),
        } for e in es],
    }


@app.get("/v1/verify/{entry_id}")
def v1_verify(entry_id: str, lg: Ledger = Depends(tenant_ledger)):
    e = lg.by_id(entry_id)
    if e is None:
        raise HTTPException(404, "no such entry")
    history = anchor_log.history()
    return {
        "id": e.id,
        "sealed_at": e.created_at,
        "resolved_at": e.resolved_at,
        "sealed_before_outcome": (e.resolved_at is None) or (e.created_at < e.resolved_at),
        "recomputed_hash": e.compute_hash(),
        "stored_hash": e.hash,
        "intact": e.compute_hash() == e.hash,
        "resolution_evidence_hash": e.resolution_evidence_hash,
        "merkle_root": lg.merkle_root(),
        "external_anchors": history[-3:],
        "anchored": bool(history),
        "verify_url": f"/v1/verify/{e.id}",
        "qr": f"/v1/verify/{e.id}/qr",
        "claim": "This prediction's hash is fixed by the chain. Its seal time is "
                 "earlier than its resolution time, and the chain's root is timestamped "
                 "by an external authority — so the seal is checkable without trusting us. "
                 "Edit any sealed entry and every later hash breaks.",
    }


@app.get("/v1/verify/{entry_id}/certificate")
def v1_certificate(entry_id: str, lg: Ledger = Depends(tenant_ledger)):
    """A self-contained, offline-verifiable decision certificate. A third party recomputes
    the leaf hash from `entry`, checks the Merkle `proof` against `merkle_root`, and confirms
    the root was externally anchored before the outcome — WITHOUT trusting NEXUS or calling
    this API again. This is verifiable organisational memory; a model's 'memory' cannot
    produce it. Verify with backend/verify_certificate.py."""
    e = lg.by_id(entry_id)
    if e is None:
        raise HTTPException(404, "no such entry")
    proof = lg.merkle_proof(entry_id)
    return {
        "nexus_certificate": "1.0",
        "entry": e.core(),
        "leaf_hash": e.hash,
        "merkle_proof": proof,
        "merkle_root": proof["merkle_root"] if proof else lg.merkle_root(),
        "external_anchors": anchor_log.history()[-3:],
        "sealed_at": e.created_at,
        "resolved_at": e.resolved_at,
        "sealed_before_outcome": (e.resolved_at is None) or (e.created_at < e.resolved_at),
        "how_to_verify": [
            "1. sha256 of canonical(entry) must equal leaf_hash",
            "2. verify_inclusion(leaf_hash, merkle_proof.path, merkle_root) must be true",
            "3. merkle_root must appear in an external anchor timestamped before resolved_at",
        ],
    }


@app.post("/v1/prove")
def v1_prove(request: Request, principal: Principal = Depends(require_auth)):
    lg = get_ledger(principal.tenant)
    settled = resolve_due(lg, oracle)
    # anchor the new head externally the moment outcomes land, so the freshly
    # resolved record is provable against an authority we do not control.
    anchored = anchor(lg, anchor_log) if settled else None
    log_audit("prove", principal, request, settled=len(settled))
    return {"settled": settled, "calibration": calibration(lg), "anchor": anchored}


@app.get("/v1/counterfactuals")
def v1_counterfactuals(domain: str | None = None, min_regret: float = 0.0, limit: int = 200,
                       lg: Ledger = Depends(tenant_ledger)):
    # the corpus of scored roads-not-taken (weak signal; see /v1/assumptions for causal)
    return counterfactuals(lg, domain=domain, min_regret=min_regret, limit=limit)


@app.get("/v1/assumptions")
def v1_assumptions(domain: str | None = None, limit: int = 100,
                   lg: Ledger = Depends(tenant_ledger)):
    # the Assumption Ledger — beliefs ranked by how often the sealed bets that leaned
    # on them were later falsified by reality. The only honest causal asset.
    return assumptions_corpus(lg, domain=domain, limit=limit)


@app.get("/v1/first_movers")
def v1_first_movers(top: int = 12, lg: Ledger = Depends(tenant_ledger)):
    # who was provably RIGHT FIRST per resolved question — computable only from a
    # seal-time-anchored chain. The reputational fact analysts actually pay for.
    return first_to_call(lg, top=top)


@app.get("/v1/reliability")
def v1_reliability(lg: Ledger = Depends(tenant_ledger)):
    # the recalibration curve WITH its 95% confidence band — a wide band is the honest
    # signal that the bend is not yet earned. Shown on purpose.
    return reliability_band(lg)


@app.post("/v1/anchor")
def v1_anchor(request: Request, principal: Principal = Depends(require_auth)):
    log_audit("anchor", principal, request)
    # publish the current Merkle root to an external time authority (OpenTimestamps;
    # mirrored to S3 Object Lock (WORM) in prod). The credibility keystone.
    return anchor(get_ledger(principal.tenant), anchor_log)


@app.get("/v1/trust")
def v1_trust(lg: Ledger = Depends(tenant_ledger)):
    return trust_graph(lg)


@app.get("/v1/markets")
def v1_markets(lg: Ledger = Depends(tenant_ledger)):
    return markets(lg)


# ── v14 · the Reality Arena (Human vs AI) + phone verification ─────────────
@app.get("/v1/leaderboard")
def v1_leaderboard(lg: Ledger = Depends(tenant_ledger)):
    """The single-number Reality Score board: humans vs AI vs the ensemble, ranked
    by sealed forward calls an external oracle later confirmed. This is the arena."""
    return reality_score(lg)


@app.get("/v1/reality_score")
def v1_reality_score(lg: Ledger = Depends(tenant_ledger)):
    # alias — same payload, clearer name when embedding the one number elsewhere
    return reality_score(lg)


@app.get("/v1/arena")
def v1_arena(lg: Ledger = Depends(tenant_ledger)):
    """Everything the Reality Arena screen needs in one call: the board, the live
    state (how many still pending vs resolved), and the next resolution time so the
    UI can count down to a score moving on stage."""
    board = reality_score(lg)
    pend = [e for e in lg.pending()
            if e.prediction.get("oracle_ref", "").startswith("arena:")]
    res = [e for e in lg.resolved(Kind.FORWARD)
           if e.prediction.get("oracle_ref", "").startswith("arena:")]
    next_at = min((float(e.prediction.get("resolves_at", 0)) for e in pend), default=None)
    return {
        **board,
        "cohort": "demo",
        "arena_pending": len(pend),
        "arena_resolved": len(res),
        "next_resolution_at": next_at,
        "now": time.time(),
        "honesty": ("The arena is a backdated demo cohort — real seal<resolve ordering, "
                    "real chain, but illustrative. The genuinely anchored, verify-on-your-"
                    "phone proof is a seal_live.py entry, not the arena."),
    }


@app.post("/v1/demo/arena")
def v1_demo_arena(request: Request, live_horizon_s: float = ARENA_HORIZON, principal: Principal = Depends(require_auth)):
    if settings.is_production:
        raise HTTPException(404, "not found")
    log_audit("demo.arena", principal, request)
    """(Re)seed the aged Human-vs-AI cohort on demand. Idempotent: if the arena is
    already present it is left untouched. Also (re)extends the oracle answer key."""
    global oracle
    n = seed_arena(ledger, live_horizon_s=live_horizon_s)
    oracle = arena_oracle(oracle if isinstance(oracle, SeedOracle) else None)
    return {"seeded_rows": n, "already_present": n == 0, "arena_horizon_s": live_horizon_s}


def _qr_target(entry_id: str, base: str, allowed: list[str]) -> str:
    """Build the QR deep-link. Anti-phishing: a NEXUS-signed QR may only point at an
    allow-listed origin; an untrusted `base` is dropped to a safe relative link."""
    b = (base or "").rstrip("/")
    if b and b not in {o.rstrip("/") for o in allowed}:
        b = ""
    return f"{b}/verify.html?id={entry_id}&api={b}" if b else f"/verify.html?id={entry_id}"


@app.get("/v1/verify/{entry_id}/qr")
def v1_verify_qr(entry_id: str, base: str = "", lg: Ledger = Depends(tenant_ledger)):
    """An SVG QR code a judge scans to verify a seal on their own phone. Encodes the
    standalone verify page deep-linked to this entry and this API. `base` should be
    the publicly reachable origin of the API (e.g. https://...ngrok.../). Falls back
    to a relative deep-link when omitted."""
    from fastapi.responses import Response
    e = lg.by_id(entry_id)
    if e is None:
        raise HTTPException(404, "no such entry")
    target = _qr_target(entry_id, base, settings.cors_origins)
    try:
        import segno
        buf = io.BytesIO()
        segno.make(target, error="m").save(buf, kind="svg", scale=6, dark="#04050A",
                                            light="#ffffff", border=2)
        return Response(content=buf.getvalue(), media_type="image/svg+xml")
    except Exception as ex:
        # segno absent / failure: hand back the target so the page can render a QR
        # client-side, so phone verification still works.
        raise HTTPException(503, detail={"qr_unavailable": True, "verify_target": target}) from ex


@app.post("/v1/demo/resolve_live")
def v1_demo_resolve_live(request: Request, principal: Principal = Depends(require_auth)):
    """Release the HELD live arena questions — the on-stage 'reality arrives' beat.
    Settles them via the oracle (never self-graded), then anchors the new head."""
    if settings.is_production:
        raise HTTPException(404, "not found")
    log_audit("demo.resolve_live", principal, request)
    settled = resolve_live(ledger, oracle)
    anchored = anchor(ledger, anchor_log) if settled else None
    return {"settled": settled, "leaderboard": reality_score(ledger), "anchor": anchored}


# ── static frontend: serve the standalone landing pages directly at root ──
# Any route not matched by /v1/* or /twin/* falls through to static file serving.
_STANDALONE = pathlib.Path(__file__).resolve().parent.parent.parent / "nexus-landing" / "standalone"
if _STANDALONE.is_dir():
    app.mount("/", StaticFiles(directory=str(_STANDALONE), html=True), name="frontend")

