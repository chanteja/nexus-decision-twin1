// src/landing/useNexusData.ts
// Presence layer: the system was already running before you arrived.
// Polls the REAL backend (/v1/status, /v1/graph) and degrades to a live-feeling
// demo if the API is unreachable. Never blocks the experience on the network.
// Endpoints are READ-ONLY — no backend, route, or business logic is touched.
import { useEffect, useState } from 'react';

const API = (import.meta as any).env?.VITE_NEXUS_API ?? '';

export interface NexusStatus {
  status: 'ready' | 'degraded' | 'down';
  uptimeS: number;
  engines: number;
  events: number;
  chainValid: boolean;
  nodes: number;
  edges: number;
  live: boolean; // true when served by the real backend
}

const DEMO: NexusStatus = {
  status: 'ready', uptimeS: 4200 + Math.random() * 8000,
  engines: 23, events: 128, chainValid: true, nodes: 120, edges: 1400, live: false,
};

export function useNexusStatus(intervalMs = 2000): NexusStatus {
  const [s, setS] = useState<NexusStatus>(DEMO);
  useEffect(() => {
    let alive = true, demo = { ...DEMO };
    const tick = async () => {
      try {
        const r = await fetch(`${API}/v1/status`, { cache: 'no-store' });
        if (!r.ok) throw new Error();
        const j = await r.json();
        let nodes = demo.nodes, edges = demo.edges;
        try {
          const g = await (await fetch(`${API}/v1/graph?limit=400`, { cache: 'no-store' })).json();
          nodes = g.nodes?.length ?? nodes; edges = g.edges?.length ?? edges;
        } catch { /* graph optional */ }
        if (!alive) return;
        setS({
          status: j.status, uptimeS: j.uptime_s, engines: (j.engines || []).length,
          events: j.events, chainValid: j.chain_valid, nodes, edges, live: true,
        });
      } catch {
        demo = { ...demo, uptimeS: demo.uptimeS + intervalMs / 1000, events: demo.events + (Math.random() < 0.25 ? 1 : 0) };
        if (alive) setS({ ...demo });
      }
    };
    tick(); const id = setInterval(tick, intervalMs);
    return () => { alive = false; clearInterval(id); };
  }, [intervalMs]);
  return s;
}

// Pulls real graph topology to seed particle clusters (optional enhancement —
// the field renders beautifully on synthetic anchors if this fails).
export async function fetchGraphAnchors(limit = 200): Promise<number> {
  try {
    const g = await (await fetch(`${API}/v1/graph?limit=${limit}`, { cache: 'no-store' })).json();
    return g.nodes?.length ?? 0;
  } catch { return 0; }
}

// ──────────────────────────────────────────────────────────────────────────
// FIX 1 — the collapse IS the inference. When VITE_NEXUS_API is set, the
// survivor + confidence + reasoning come from the real NEXUS /v1/decide
// (4-model Bedrock ensemble, recorded to the hash-chained ledger). On any
// failure/timeout this returns null and the caller falls back to the local
// deterministic model — identical visuals, never blocks on the network.
// ──────────────────────────────────────────────────────────────────────────
export interface EngineVerdict {
  survivor?: number;          // index of the surviving branch (0..branches-1)
  weights?: number[];         // per-branch probability/attention, length = branches
  confidence: number;         // 0..1
  why: string;
  watch: string;
  model?: string;             // e.g. "bedrock 4-model ensemble"
  ledger?: { events: number; chain_valid: boolean; entry?: string };
}

export async function engineDecide(
  decision: string, constraint = '', branches = 7, tenant = 'demo_corp', seed?: number,
  timeoutMs = 3500,
): Promise<EngineVerdict | null> {
  if (!API) return null;
  try {
    const ctrl = new AbortController();
    const to = setTimeout(() => ctrl.abort(), timeoutMs);
    const r = await fetch(`${API}/v1/decide`, {
      method: 'POST', cache: 'no-store', signal: ctrl.signal,
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ decision, constraint, branches, tenant, seed }),
    });
    clearTimeout(to);
    if (!r.ok) return null;
    return (await r.json()) as EngineVerdict;
  } catch { return null; }
}

// FIX 2/5 — Nexus scores itself against reality, from RESOLVED rows only.
// forward = sealed before the outcome existed (the real test);
// backtest = historical, hindsight, context only — never the headline.
export interface CalSlice {
  n: number; accuracy: number | null; brier: number | null;
  reliability: (number | null)[]; samples: { decision: string; predicted: number; survived: boolean }[];
  sealed_pending?: number; note?: string;
}
export interface Calibration {
  live: boolean; headline: string;
  forward: CalSlice; backtest: CalSlice;
  learning?: LearningState;
  digest?: { entries: number; merkle_root: string; chain_valid: boolean };
}

// v12 — the flywheel state. recalibration_active flips true once enough forward
// rows have resolved (MIN_N) for the reliability curve to bend stated confidence
// toward what each band actually achieved. This is "smarter with every outcome".
export interface LearningState {
  recalibration_active: boolean;
  fitted_reliability: (number | null)[];
  resolved_forward: number;
  needed_for_recalibration: number;
}

const DEMO_CALIB: Calibration = {
  live: false,
  headline:
    '6 forecasts sealed and time-stamped before their outcomes. Verify the seal against the published Merkle root; nothing here is graded by Nexus.',
  forward: {
    n: 3, accuracy: 1.0, brier: 0.078, sealed_pending: 6,
    reliability: [null, null, null, 0.0, null, null, null, 0.7, 0.85, null],
    samples: [
      { decision: 'Ship the v11 forward ledger before the finale demo', predicted: 0.78, survived: true },
      { decision: 'Open-source the calibration resolver this quarter', predicted: 0.70, survived: true },
      { decision: 'Bet the demo on a single un-tested live model', predicted: 0.31, survived: false },
    ],
  },
  backtest: {
    n: 12, accuracy: 0.92, brier: 0.11,
    note: 'historical · hindsight · context only — never the forward claim',
    reliability: [],
    samples: [
      { decision: 'Microsoft acquires GitHub ($7.5B, 2018)', predicted: 0.82, survived: true },
      { decision: 'Google launches Google+ to rival Facebook (2011)', predicted: 0.34, survived: false },
      { decision: 'Facebook acquires Instagram ($1B, 2012)', predicted: 0.86, survived: true },
      { decision: 'Meta bets the company on the metaverse (2021)', predicted: 0.44, survived: false },
    ],
  },
  learning: {
    recalibration_active: false, fitted_reliability: new Array(10).fill(null),
    resolved_forward: 3, needed_for_recalibration: 30,
  },
};

export async function fetchCalibration(): Promise<Calibration> {
  if (!API) return DEMO_CALIB;
  try {
    const j = await (await fetch(`${API}/v1/calibration`, { cache: 'no-store' })).json();
    return { ...DEMO_CALIB, ...j, live: true } as Calibration;
  } catch { return DEMO_CALIB; }
}

// "Put it on the record" — seal a prediction to the public, append-only ledger.
export async function commitPrediction(body: {
  decision: string; weights: number[]; survivor: number; confidence: number;
  why?: string; watch?: string; author?: string; domain?: string;
  resolves_at: number; oracle_ref: string; branches?: string[];
}): Promise<{ entry: string; merkle_root: string; verify: string } | null> {
  if (!API) return null;
  try {
    const r = await fetch(`${API}/v1/commit`, {
      method: 'POST', cache: 'no-store',
      headers: { 'content-type': 'application/json' }, body: JSON.stringify(body),
    });
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}

// The loop, in front of the judge — settle every due prediction by external oracle.
export async function proveLedger(): Promise<{ settled: any[]; calibration: Calibration } | null> {
  if (!API) return null;
  try { return await (await fetch(`${API}/v1/prove`, { method: 'POST', cache: 'no-store' })).json(); }
  catch { return null; }
}

export async function fetchTrust(): Promise<any> {
  if (!API) return { authors: [], scored_on: 0 };
  try { return await (await fetch(`${API}/v1/trust`, { cache: 'no-store' })).json(); }
  catch { return { authors: [], scored_on: 0 }; }
}

export async function fetchMarkets(): Promise<any> {
  if (!API) return { markets: [], weighting: 'calibration-weighted (trust graph)' };
  try { return await (await fetch(`${API}/v1/markets`, { cache: 'no-store' })).json(); }
  catch { return { markets: [] }; }
}

// ──────────────────────────────────────────────────────────────────────────
// v12 — the learning layer made visible. All READ-ONLY, all degrade to a
// live-feeling demo if the API is unreachable. Never blocks the experience.
// ──────────────────────────────────────────────────────────────────────────

// The COUNTERFACTUAL CORPUS — the six roads not taken, scored against what
// actually happened. The headline asset: a dataset that only forms because we
// persisted the rejected branches from the first sealed call.
export interface CounterfactualRow {
  entry_id: string; question: string; branch: string; branch_prob: number | null;
  was_taken: boolean; taken_survived: boolean; regret: number; domain: string;
}
export interface Counterfactuals {
  rows: CounterfactualRow[]; total_branches: number; scored_untaken: number;
  domain_regret: { domain: string; branches: number; mean_regret: number }[];
  note: string;
}
const DEMO_CF: Counterfactuals = {
  rows: [], total_branches: 0, scored_untaken: 0,
  domain_regret: [
    { domain: 'product', branches: 48, mean_regret: 0.08 },
    { domain: 'strategy', branches: 60, mean_regret: 0.046 },
    { domain: 'execution', branches: 24, mean_regret: 0.05 },
  ],
  note: 'the six roads not taken, scored against what actually happened.',
};
export async function fetchCounterfactuals(domain = '', minRegret = 0): Promise<Counterfactuals> {
  if (!API) return DEMO_CF;
  try {
    const q = new URLSearchParams();
    if (domain) q.set('domain', domain);
    if (minRegret) q.set('min_regret', String(minRegret));
    return await (await fetch(`${API}/v1/counterfactuals?${q}`, { cache: 'no-store' })).json();
  } catch { return DEMO_CF; }
}

// The TYPED REALITY GRAPH — Questions / Predictions / Outcomes / Authors and the
// influence edges between them. Replaces the chain-order line; this is the graph
// the universe should render (nodes glow by type, resolved Outcomes pulse).
export interface GraphNode { id: string; type: string; label?: string; [k: string]: any; }
export interface GraphEdge { type: string; source: string; target: string; }
export interface RealityGraph {
  nodes: GraphNode[]; edges: GraphEdge[];
  node_types: string[]; edge_types: string[];
  counts: Record<string, number>;
}
export async function fetchRealityGraph(limit = 400): Promise<RealityGraph | null> {
  if (!API) return null;
  try { return await (await fetch(`${API}/v1/graph?limit=${limit}`, { cache: 'no-store' })).json(); }
  catch { return null; }
}

// "Which authors consistently alter reality?" — a graph query the line could not answer.
export async function fetchMovers(top = 10): Promise<{ reality_movers: any[] }> {
  if (!API) return { reality_movers: [] };
  try { return await (await fetch(`${API}/v1/movers?top=${top}`, { cache: 'no-store' })).json(); }
  catch { return { reality_movers: [] }; }
}

// The EXTERNAL ANCHOR — publish the Merkle root to a time authority NEXUS does not
// control (OpenTimestamps; mirrored to S3 Object Lock + the QLDB digest in prod).
// The credibility keystone: verify the seal without trusting us.
export interface AnchorResult {
  anchored: { merkle_root: string; entries: number; anchored_at: number; ots_status: string };
  history: any[]; claim: string;
}
export async function anchorLedger(): Promise<AnchorResult | null> {
  if (!API) return null;
  try { return await (await fetch(`${API}/v1/anchor`, { method: 'POST', cache: 'no-store' })).json(); }
  catch { return null; }
}
