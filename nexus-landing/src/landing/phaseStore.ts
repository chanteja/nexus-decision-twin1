// src/landing/phaseStore.ts
// Single source of truth for the cinematic phase. Zustand keeps this outside
// React's render loop so r3f's useFrame can read/write it at 60fps with zero
// re-renders. phase ∈ [0,7]: the Tree of Futures arc —
// seed→roots→emergence→forest→intelligence→selection→silence→survivor→universe.
//
// v8 "Mirror": the seed is the visitor's own decision. The store now also carries
// the decision text, the chosen survivor + the runner-up (the Counterfactual), and
// the resolved decision card (the Bridge) so the DOM overlays stay frame-locked to
// the particles and the camera.
import { create } from 'zustand';

export interface Readback { eye: string; lines: string[]; }
export interface DecisionCard { decision: string; confidence: number; why: string; watch: string; }

// ── v9 "The Negotiation" ──
export interface LedgerRow { b: number; pc: number; label: string; surv: boolean; killed: boolean; dead: boolean; }
export interface LineageEntry { seed: number; dec: string; conf: number; why: string; watch: string; label: string; killed: boolean; killedBranch: number; reverted: boolean; }

export interface PhaseState {
  phase: number;        // smoothed, written every frame
  scroll: number;       // 0..1 raw scroll progress
  intro: number;        // 0..1 cold-open progress
  attack: number;       // adversarial red pulse 0..1
  revealed: boolean;    // final read-back is showing

  // v8 — the decision is the seed
  started: boolean;     // the visitor has planted a decision (or chosen to watch); the world boots
  decision: string;     // the visitor's own words — quoted back, never analysed away
  seed: number;         // derived from the decision (deterministic) or random when watching

  // scripted finale
  seqActive: boolean;   // Silence + reveal has taken over from scroll
  seqPhase: number;     // phase driven by the finale (engine writes this)
  seqTarget: number;    // where the finale is easing toward

  // selection
  survivorChosen: boolean;
  survivor: number;     // branch index 0..BRANCHES-1
  runnerUp: number;     // the future that was one hesitation away (the Counterfactual)
  futures: number;      // derived count shown in the Silence counter
  readback: Readback;   // the one true thing, anchored to this decision
  card: DecisionCard | null; // the Bridge — survivor resolves into a real read-out

  // v9 — recursive agency, the living ledger, the mirror
  collapseCount: number;       // realities collapsed this session
  ledgerRows: LedgerRow[];     // the forest surfaced as a 7-future model
  lineage: LineageEntry[];     // the realities the visitor has produced
  identity: string;            // the decision fingerprint (≥3 collapses)
  sacrifice: string;           // the future just let go of
  reCollapsing: boolean;
  branchLabels: string[];
  camFocus: [number, number, number] | null; // a ledger row can fly the camera to a limb
  camFocusUntil: number;
  recollapse: (constraint: string) => void;   // engine registers this
  focusBranch: (b: number) => void;           // engine registers this
  restore: (i: number) => void;               // restore a prior reality from the lineage

  begin: (decision: string, seed: number) => void; // plant the decision; boots the world
  decide: () => void;   // engine registers this; locks the survivor from behaviour
  set: (p: Partial<PhaseState>) => void;
}

export const usePhase = create<PhaseState>((set) => ({
  phase: 0, scroll: 0, intro: 0, attack: 0, revealed: false,
  started: false, decision: '', seed: 0,
  seqActive: false, seqPhase: 5, seqTarget: 5,
  survivorChosen: false, survivor: 0, runnerUp: 1, futures: 12742,
  readback: { eye: 'reality selected', lines: [] }, card: null,
  collapseCount: 0, ledgerRows: [], lineage: [], identity: '', sacrifice: '',
  reCollapsing: false, branchLabels: [], camFocus: null, camFocusUntil: 0,
  recollapse: () => {}, focusBranch: () => {}, restore: () => {},
  begin: (decision, seed) => set({ started: true, decision, seed }),
  decide: () => {},
  set: (p) => set(p),
}));

// imperative getter for useFrame (avoids subscribing the component)
export const phaseApi = usePhase;
