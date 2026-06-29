// src/landing/Question.tsx
// THE QUESTION — the seed is the visitor's own decision. One real input before the
// experience. The string deterministically seeds the whole world (same decision →
// same reality) and is quoted back at the reveal. Skipping is always allowed.
import { useEffect, useRef, useState } from 'react';
import { usePhase } from './phaseStore';
import { cap, seedFromText } from './behavior';

export function Question() {
  const begin = usePhase((s) => s.begin);
  const started = usePhase((s) => s.started);
  const [gone, setGone] = useState(false);
  const [text, setText] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const [shared, setShared] = useState<string | null>(null);

  useEffect(() => {
    const t = setTimeout(() => { try { inputRef.current?.focus({ preventScroll: true }); } catch { inputRef.current?.focus(); } }, 700);
    return () => clearTimeout(t);
  }, []);

  // v9 — a shared reality reproduces exactly: ?d= prefills the decision and self-plants
  useEffect(() => {
    const d = new URLSearchParams(location.search).get('d');
    if (d == null) return;
    const decision = d.slice(0, 120);
    setText(decision); setShared(decision);
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (!reduce) { const id = setTimeout(() => plant(decision), 1700); return () => clearTimeout(id); }
  }, []);  // eslint-disable-line react-hooks/exhaustive-deps

  const plant = (raw: string) => {
    const decision = (raw || '').trim();
    cap.decision = decision;
    const seed = decision ? seedFromText(decision.toLowerCase()) : (Math.random() * 1e9) | 0;
    setGone(true);
    setTimeout(() => begin(decision, seed >>> 0), 80);
  };

  if (started && gone) return null;

  return (
    <div className={`nx-ask ${gone ? 'gone' : ''}`}>
      <div className="q-eye">nexus is listening</div>
      <div className="q">{shared != null ? 'Someone sent you this decision.' : 'What are you trying to decide?'}</div>
      <div className="q-wrap">
        <input
          ref={inputRef} className="nx-ask-input" autoComplete="off" spellCheck={false} maxLength={120}
          placeholder="say it in your own words…" aria-label="The decision you are facing"
          value={text} onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') plant(text); }}
        />
      </div>
      <button className="q-go" onClick={() => plant(text)}>plant it ↵</button>
      <button className="q-skip" onClick={() => plant('')}>or watch without deciding</button>
    </div>
  );
}
