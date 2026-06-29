// src/landing/Silence.tsx
// P0-3 — the Silence + the count. A true black hold (≈2.5s that feels like 8), then a
// monospace counter DERIVED from this visit that ticks down to "1 survived".
// v8 "Mirror": the count is now framed as simulating the visitor's own decision, an
// audio drone carries the black, and a Counterfactual beat names the self they almost
// became before the black lifts to the reveal. Driven entirely by the phase store.
import { useEffect, useRef, useState } from 'react';
import { usePhase } from './phaseStore';
import { counterfactualLabel } from './behavior';
import { audioSwell, audioTick, audioSurvive, audioGhost } from './audio';

function animateNumber(set: (s: string) => void, from: number, to: number, ms: number, done?: () => void) {
  const t0 = performance.now(); let lastSlot = -1;
  const step = () => {
    const k = Math.min(1, (performance.now() - t0) / ms); const e = 1 - Math.pow(1 - k, 3);
    set(Math.round(from + (to - from) * e).toLocaleString());
    const slot = Math.floor(k * 14); if (slot !== lastSlot) { lastSlot = slot; audioTick(); }
    if (k < 1) requestAnimationFrame(step); else if (done) done();
  };
  step();
}

export function Silence() {
  const seqActive = usePhase((s) => s.seqActive);
  const futures = usePhase((s) => s.futures);
  const decision = usePhase((s) => s.decision);
  const runnerUp = usePhase((s) => s.runnerUp);
  const set = usePhase((s) => s.set);
  const [show, setShow] = useState(false);
  const [label, setLabel] = useState('');
  const [num, setNum] = useState('');
  const [sub, setSub] = useState('');
  const [survived, setSurvived] = useState(false);
  const [dissent, setDissent] = useState(false);
  const ran = useRef(false);

  useEffect(() => {
    if (!seqActive || ran.current) return; ran.current = true;
    const F = futures; const timers: number[] = [];
    setShow(true); audioSwell();                                    // → black, drone rises
    timers.push(window.setTimeout(() => setLabel('simulating every version of your decision'), 1900));
    timers.push(window.setTimeout(() => { setNum('0'); animateNumber(setNum, 0, F, 1200); }, 2350));
    timers.push(window.setTimeout(() => setSub(F.toLocaleString() + ' simulated'), 3700));
    timers.push(window.setTimeout(() => { setSub('eliminating the ones that do not survive'); animateNumber(setNum, F, 1, 1500); }, 4500));
    timers.push(window.setTimeout(() => setSub((F - 1).toLocaleString() + ' eliminated'), 6050));
    timers.push(window.setTimeout(() => { setNum('1'); setSurvived(true); setSub('survived'); audioSurvive(); }, 6650));
    // the Counterfactual — the self you almost became
    timers.push(window.setTimeout(() => { setNum(''); setLabel(''); setSurvived(false); setDissent(true); setSub('one future was a hesitation away'); audioGhost(); }, 7800));
    timers.push(window.setTimeout(() => setSub(decision ? `it was ${counterfactualLabel(runnerUp)} — it needed you to be more certain` : `${counterfactualLabel(runnerUp)} — it needed one more reason`), 9100));
    timers.push(window.setTimeout(() => { setShow(false); setDissent(false); set({ seqTarget: 6.4, revealed: true }); }, 10700));
    return () => { timers.forEach(clearTimeout); };
  }, [seqActive, futures, decision, runnerUp, set]);

  return (
    <div className={`nx-silence ${show ? 'show' : ''}`} aria-hidden>
      <div className="genlabel">{label}</div>
      <div className={`gennum ${survived ? 'survived' : ''}`}>{num}</div>
      <div className={`gensub ${dissent ? 'dis' : ''}`}>{sub}</div>
    </div>
  );
}
