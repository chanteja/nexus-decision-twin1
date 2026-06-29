// src/landing/behavior.ts
// The invisible layer. The page never tells the visitor it is watching — it just
// remembers how they moved, and at the end says one true thing anchored to the
// decision they brought. Pure/framework-agnostic so Landing can wire DOM listeners
// and RealityAwakening can read the live cursor without prop-drilling.
//
// v8 "Mirror": the decision is the seed (deterministic). composeReadback quotes the
// visitor's own words; composeCard resolves the survivor into a real decision read-out
// (the Bridge); counterfactualLabel names the self they almost became.
import type { DecisionCard } from './phaseStore';

export const pointer = { tx: 0, ty: 0 };          // live cursor, normalised (-0.5..0.5)

// FNV-1a → unsigned 32-bit. Same decision → same reality (the revisit loop).
export function seedFromText(s: string): number {
  let h = 2166136261 >>> 0;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}

export interface Capture {
  t0: number; firstMove: number; travel: number; lastX: number; lastY: number;
  reversals: number; lastDir: number; maxScroll: number; lastScroll: number;
  collapseTravel: number; skipped: boolean; dwell: number; decision: string;
}
export const cap: Capture = {
  t0: (typeof performance !== 'undefined' ? performance.now() : 0),
  firstMove: -1, travel: 0, lastX: 0.5, lastY: 0.5,
  reversals: 0, lastDir: 0, maxScroll: 0, lastScroll: 0, collapseTravel: 0, skipped: false,
  dwell: 0, decision: '',
};

export function trackPointer(clientX: number, clientY: number, uPhase: number) {
  const nx = clientX / innerWidth, ny = clientY / innerHeight;
  pointer.tx = nx - 0.5; pointer.ty = ny - 0.5;
  if (cap.firstMove < 0) cap.firstMove = performance.now() - cap.t0;
  const d = Math.hypot(nx - cap.lastX, ny - cap.lastY);
  cap.travel += d; cap.lastX = nx; cap.lastY = ny;
  if (uPhase >= 4.0 && uPhase <= 5.0) cap.collapseTravel += d;
}

export function trackScroll(trackPx: number): number {
  const max = trackPx - innerHeight;
  const ns = Math.min(1, Math.max(0, scrollY / Math.max(1, max)));
  const dir = Math.sign(ns - cap.lastScroll);
  if (dir !== 0 && cap.lastDir !== 0 && dir !== cap.lastDir) cap.reversals++;
  if (dir !== 0) cap.lastDir = dir;
  cap.maxScroll = Math.max(cap.maxScroll, Math.abs(ns - cap.lastScroll) * max);
  cap.lastScroll = ns;
  return ns;
}

// one true sentence — anchored to the actual decision (never a horoscope)
export function composeReadback(): { eye: string; lines: string[] } {
  const secs = Math.max(1, Math.round((performance.now() - cap.t0) / 1000));
  const rev = cap.reversals, travel = cap.travel;
  const fast = cap.maxScroll > 120, still = cap.collapseTravel < 0.05, watched = !cap.skipped;
  const D = cap.decision ? `"${cap.decision}"` : 'the decision you brought';
  let eye: string, manner: string;
  if (still && watched)     { eye = 'reality selected · you watched it choose'; manner = 'You held still while the other futures fell.'; }
  else if (rev >= 2)        { eye = 'reality selected · you went back';        manner = `You went back ${rev} times — you weren't sure either.`; }
  else if (fast && secs<45) { eye = 'reality selected · you moved fast';       manner = `You crossed it in ${secs}s. You wanted the answer, not the scenery.`; }
  else if (travel > 9)      { eye = 'reality selected · you reached in';        manner = 'You did not watch the futures — you moved through them.'; }
  else if (secs > 70)       { eye = 'reality selected · you took your time';    manner = `You let it breathe — ${secs} seconds, unhurried.`; }
  else                      { eye = 'reality selected · you moved with intent'; manner = 'Among ten thousand versions, your attention chose one.'; }
  return { eye, lines: [`You asked Nexus ${D}.`, manner, 'One version of that choice survived. This is it.'] };
}

const WHY = [
  'it removes your highest-variance failure path',
  'it preserves optionality the other futures spend',
  'it survives the scenario where you are wrong',
  'it is the only branch that compounds instead of decays',
  'it costs the least when the assumptions break',
  'it keeps you in the game long enough to learn',
  'it is robust to the thing you are not seeing',
];
const WATCH = [
  'the other branch returns if your timeline shortens',
  'reverses if the cost of waiting drops',
  'flips if new information lands in the next 30 days',
  'destabilises if your constraints loosen',
  'the runner-up wins if you can absorb one bad quarter',
  'changes if the people involved change',
  'returns the moment certainty becomes cheap',
];

// the Bridge — deterministic, decision-shaped synthesis. If a live /v1/decide endpoint
// exists, a fetch slots in here with the identical shape; no write, no business logic.
export function composeCard(
  decision: string, seed: number, survivor: number,
  concentration: number, dwell: number, extraConstraint = '',
): DecisionCard {
  const h = seedFromText((decision || '·') + '|' + survivor + '|' + extraConstraint);
  let conf = 0.58 + (h % 34) / 100 + Math.min(0.08, concentration * 0.18) + Math.min(0.04, dwell * 0.01);
  conf = Math.min(0.94, conf);
  if (extraConstraint) conf = Math.max(0.41, conf - 0.06 - (seedFromText(extraConstraint) % 9) / 100);
  const decLabel = decision ? (decision.length > 42 ? decision.slice(0, 40) + '…' : decision) : 'the path you watched survive';
  return { decision: decLabel, confidence: conf, why: WHY[h % WHY.length], watch: WATCH[(h >> 4) % WATCH.length] };
}

export function counterfactualLabel(runnerUp: number): string {
  const labels = ['the bolder one', 'the patient one', 'the safe one', 'the one who waited', 'the one who said no', 'the one who moved first', 'the contrarian'];
  return labels[((runnerUp % labels.length) + labels.length) % labels.length];
}

// ── v9 "The Negotiation" — recursive-agency helpers (pure; no backend) ──
export const BRANCH_LABELS = ['the bold path', 'the patient path', 'the safe path', 'the contrarian path', 'the first-mover path', 'the wait-and-see path', 'the all-in path'];
export const CF_LABELS = ['the bold one', 'the patient one', 'the safe one', 'the contrarian', 'the first mover', 'the one who waited', 'the all-in one'];

// deterministic per-decision naming of the futures (a seeded shuffle of the label pool)
export function makeBranchLabels(seed: number, branches: number): string[] {
  let a = (seed ^ 0x9e3779b9) >>> 0;
  const rng = () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  const pool = BRANCH_LABELS.slice(), out: string[] = [];
  for (let i = 0; i < branches; i++) { const j = (rng() * pool.length) | 0; out.push(pool.splice(j, 1)[0] || BRANCH_LABELS[i % BRANCH_LABELS.length]); }
  return out;
}

// a constraint re-weights the SAME attention model (deterministic), blending prior lean with new pressure
export function biasAttention(att: Float32Array, constraint: string) {
  const b = seedFromText(constraint || '·');
  for (let i = 0; i < att.length; i++) {
    const w = 0.35 + (((b >>> (i * 4)) & 0xf) / 15);
    att[i] = att[i] * 0.4 + w;
  }
}

// classify the survivor's reason — the identity mirror reads which kind of branch the visitor keeps
export function whyCategory(why: string): string {
  if (/optionality/.test(why)) return 'optionality';
  if (/wrong|robust|not seeing/.test(why)) return 'robustness';
  if (/compounds|game long enough/.test(why)) return 'patience';
  return 'cost';
}
