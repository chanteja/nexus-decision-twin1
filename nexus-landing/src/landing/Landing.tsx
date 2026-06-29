// src/landing/Landing.tsx
// Composition root for the signature landing experience — the Tree of Futures.
// Mounts ONE persistent Canvas + a tall scroll track.
// v8 "Mirror":
//  • THE QUESTION gates the experience — the seed is the visitor's own decision.
//    RealityAwakening only mounts once a decision is planted (deterministic seed).
//  • scroll carries the visitor only to the brink of selection (phase ≤ 4.7);
//  • behaviour is captured invisibly (behavior.ts);
//  • at the brink the survivor + runner-up are locked from that behaviour (engine.decide),
//    the survivor resolves into a real decision card, and a scripted finale takes over —
//    Silence → counter → Counterfactual → read-back + Bridge (Silence.tsx, Acts.tsx).
//  • an audio bed (audio.ts) carries the Silence. Touches no backend / API / business logic.
import { Canvas } from '@react-three/fiber';
import { EffectComposer, Bloom } from '@react-three/postprocessing';
import { useEffect, useRef } from 'react';
import { RealityAwakening } from './RealityAwakening';
import { CameraDirector } from './CameraDirector';
import { Hud } from './Hud';
import { Acts } from './Acts';
import { Silence } from './Silence';
import { Question } from './Question';
import { usePhase } from './phaseStore';
import { cap, trackPointer, trackScroll, composeReadback } from './behavior';
import { ensureAudio } from './audio';
import './landing.css';

const LOW = typeof window !== 'undefined' &&
  matchMedia('(max-width:760px), (pointer:coarse)').matches;
const REDUCE = typeof window !== 'undefined' &&
  matchMedia('(prefers-reduced-motion: reduce)').matches;

export function Landing({ onEnter }: { onEnter?: () => void }) {
  const set = usePhase((s) => s.set);
  const started = usePhase((s) => s.started);
  const seed = usePhase((s) => s.seed);
  const trackRef = useRef<HTMLDivElement>(null);
  const raf = useRef(0);
  const sequenced = useRef(false);
  const scrollP = useRef(0);

  // invisible capture — cursor + scroll rhythm, never surfaced
  useEffect(() => {
    const onMove = (e: PointerEvent) => trackPointer(e.clientX, e.clientY, usePhase.getState().phase);
    const onScroll = () => { scrollP.current = trackScroll(trackRef.current?.offsetHeight ?? innerHeight); };
    addEventListener('pointermove', onMove, { passive: true });
    addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return () => { removeEventListener('pointermove', onMove); removeEventListener('scroll', onScroll); };
  }, []);

  // the driver: only runs once the visitor has planted a decision (started)
  useEffect(() => {
    if (!started) return;
    ensureAudio();
    let intro = REDUCE ? 1 : 0; let last = performance.now();
    const loop = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000); last = now;
      const s = usePhase.getState();
      if (intro < 1) intro = Math.min(1, intro + dt / 3.0);
      const journey = 1 + scrollP.current * 6;
      let phase: number;
      if (intro < 1) phase = intro;
      else if (s.seqActive) { const sp = s.seqPhase + (s.seqTarget - s.seqPhase) * Math.min(1, dt * 1.7); set({ seqPhase: sp }); phase = sp; }
      else phase = Math.min(4.7, Math.max(1, journey));

      const sm = (s.phase || 0) + (phase - (s.phase || 0)) * Math.min(1, dt * (s.seqActive ? 2.4 : 6));
      set({ intro, scroll: scrollP.current, phase: sm });

      if (intro >= 1 && !s.survivorChosen && sm >= 3.7) s.decide();         // lock survivor + runner-up
      if (intro >= 1 && !sequenced.current && sm >= 4.5) {                  // collapse witnessed → Silence
        sequenced.current = true;
        s.decide();
        set({ readback: composeReadback(), seqActive: true, seqPhase: 5, seqTarget: 5 });
      }
      raf.current = requestAnimationFrame(loop);
    };
    raf.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf.current);
  }, [set, started]);

  const skip = () => {
    if (sequenced.current) return;
    cap.skipped = true; ensureAudio(); scrollP.current = 0.62;
    set({ phase: Math.max(usePhase.getState().phase, 4.0) });
    scrollTo({ top: (trackRef.current?.offsetHeight ?? innerHeight) * 0.62 });
  };

  return (
    <div className="nx-root">
      <div className="nx-stage">
        <Canvas
          dpr={[1, LOW ? 1.5 : 2]} gl={{ antialias: !LOW, powerPreference: 'high-performance' }}
          camera={{ fov: 55, near: 0.1, far: 9000, position: [0, 20, 300] }}
        >
          {started && <RealityAwakening seed={seed} count={LOW ? 3000 : 7200} stars={LOW ? 700 : 1500} />}
          <CameraDirector />
          {!LOW && (
            <EffectComposer>
              <Bloom intensity={0.95} luminanceThreshold={0.2} luminanceSmoothing={0.82} mipmapBlur />
            </EffectComposer>
          )}
        </Canvas>
      </div>
      <Hud />
      <div className="nx-brand">N E X U S</div>
      <Question />
      <Acts onEnter={onEnter} />
      <Silence />
      {started && <button className="nx-skip" onClick={skip} aria-label="Skip to the end of the sequence">skip ↓</button>}
      <div className="nx-track" ref={trackRef} />
    </div>
  );
}
