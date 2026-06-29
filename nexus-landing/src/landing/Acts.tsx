// src/landing/Acts.tsx
// Environmental storytelling + the v9 "Negotiation" surfaces. The acts narrate the visitor's
// own decision; the reveal reads back ONE true sentence, resolves the survivor into a real
// decision card (the Bridge), then lets the visitor ARGUE with reality: constraint chips and a
// free fork re-weight the same forest and re-collapse it into a (possibly different) survivor
// (recursive agency), the Probability Ledger surfaces the forest as a model, the Lineage rail
// remembers every reality produced, the Sacrifice names what was let go, and the Identity mirror
// reflects how they decide. Nothing here touches the backend; it drives the existing engine.
import { useEffect, useRef, useState } from 'react';
import { usePhase } from './phaseStore';
import { CF_LABELS } from './behavior';

const ACTS = [
  { at: 0.00, eye: 'I · the seed',       line: 'A decision is a seed. Yours is in the ground.' },
  { at: 0.12, eye: 'II · the roots',     line: 'It reaches into everything that bears on this.' },
  { at: 0.30, eye: 'III · emergence',    line: 'From one choice, every version of it diverges.' },
  { at: 0.46, eye: 'IV · the forest',    line: 'Ten thousand ways this could go. One living structure.' },
  { at: 0.62, eye: 'V · intelligence',   line: 'The forest is not alive. It is weighing them.' },
  { at: 0.78, eye: 'VI · selection',     line: 'Most versions of your decision do not survive.' },
  { at: 0.90, eye: 'VII · the survivor', line: 'Reality is the one that does.' },
];

const CHIPS = ['half the runway', 'a year, not a quarter', 'a competitor moves first', "you're wrong about the market"];

export function Acts({ onEnter }: { onEnter?: () => void }) {
  const scroll = usePhase((s) => s.scroll);
  const intro = usePhase((s) => s.intro);
  const seqActive = usePhase((s) => s.seqActive);
  const revealed = usePhase((s) => s.revealed);
  const readback = usePhase((s) => s.readback);
  const card = usePhase((s) => s.card);
  const decision = usePhase((s) => s.decision);
  const seed = usePhase((s) => s.seed);
  const survivor = usePhase((s) => s.survivor);
  const runnerUp = usePhase((s) => s.runnerUp);
  const ledgerRows = usePhase((s) => s.ledgerRows);
  const lineage = usePhase((s) => s.lineage);
  const identity = usePhase((s) => s.identity);
  const sacrifice = usePhase((s) => s.sacrifice);
  const collapseCount = usePhase((s) => s.collapseCount);
  const recollapse = usePhase((s) => s.recollapse);
  const focusBranch = usePhase((s) => s.focusBranch);
  const restore = usePhase((s) => s.restore);
  const set = usePhase((s) => s.set);

  const [act, setAct] = useState(-1);
  const [doorOpen, setDoorOpen] = useState(false);
  const [constraint, setConstraint] = useState('');
  const [ending, setEnding] = useState('');
  const [whisper, setWhisper] = useState('every reality you can live with started as one you killed');
  const prevConf = useRef<number | null>(null);
  const [delta, setDelta] = useState<number | null>(null);

  // act tracking
  let i = -1; const p = intro < 1 ? 0 : Math.min(scroll, 0.9);
  for (let k = 0; k < ACTS.length; k++) if (p >= ACTS[k].at) i = k;
  if (i !== act && !seqActive && !revealed) setAct(i);
  const showCap = act >= 0 && !seqActive && !revealed;

  // confidence delta tick
  useEffect(() => {
    if (!card) return;
    if (prevConf.current != null && Math.abs(card.confidence - prevConf.current) >= 0.005) setDelta(card.confidence - prevConf.current);
    prevConf.current = card.confidence;
  }, [card]);

  // the legendary ending: after they stop forking, their own path reframes everything
  useEffect(() => {
    if (!revealed) return;
    setEnding('');
    const id = setTimeout(() => {
      setEnding(collapseCount > 1 ? `You collapsed ${collapseCount} realities tonight. You kept this one.` : 'One reality survived. You can still argue with it.');
      setWhisper('every reality you can live with started as one you killed');
    }, 7000);
    return () => clearTimeout(id);
  }, [revealed, collapseCount]);

  const enter = () => {
    setDoorOpen(true); onEnter?.();
    try { history.replaceState(null, '', location.pathname + '?d=' + encodeURIComponent(decision || '')); } catch { /* noop */ }
  };
  const fork = (raw: string) => { const v = raw.trim(); if (!v) return; recollapse(v); setConstraint(''); };

  const shareCard = () => {
    const W = 1200, H = 630, cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    const g = cv.getContext('2d'); if (!g) return;
    g.fillStyle = '#04050A'; g.fillRect(0, 0, W, H);
    const grd = g.createRadialGradient(W * 0.32, H * 0.4, 40, W * 0.32, H * 0.4, W * 0.6);
    grd.addColorStop(0, 'rgba(244,199,112,0.10)'); grd.addColorStop(1, 'rgba(4,5,10,0)');
    g.fillStyle = grd; g.fillRect(0, 0, W, H);
    const wrap = (text: string, x: number, y: number, maxW: number, lh: number) => {
      const words = text.split(' '); let line = '', yy = y;
      for (const w of words) { const test = line + w + ' '; if (g.measureText(test).width > maxW && line) { g.fillText(line, x, yy); line = w + ' '; yy += lh; } else line = test; }
      g.fillText(line, x, yy);
    };
    g.textAlign = 'left';
    g.fillStyle = '#566080'; g.font = '600 17px "IBM Plex Mono", monospace'; g.fillText('N E X U S   ·   THE REALITY ENGINE', 64, 78);
    g.fillStyle = '#EEF1F8'; g.font = '300 40px "Fraunces", Georgia, serif'; wrap(card?.decision ?? 'a decision', 64, 140, W - 128, 48);
    g.strokeStyle = 'rgba(28,39,66,.9)'; g.beginPath(); g.moveTo(W / 2, 250); g.lineTo(W / 2, 560); g.stroke();
    g.fillStyle = '#F4C770'; g.font = '600 15px "IBM Plex Mono", monospace'; g.fillText('THE FUTURE YOU KEPT', 64, 290);
    g.fillStyle = '#F4C770'; g.font = '500 52px "IBM Plex Mono", monospace'; g.fillText(card ? card.confidence.toFixed(2) : '—', 64, 360);
    g.fillStyle = '#E8ECF6'; g.font = '300 22px "Fraunces", Georgia, serif'; wrap('because ' + (card?.why ?? ''), 64, 410, W / 2 - 110, 30);
    const cfConf = Math.max(0.34, (card ? card.confidence : 0.7) - 0.12);
    g.fillStyle = '#FF5C7A'; g.font = '600 15px "IBM Plex Mono", monospace'; g.fillText('THE ONE YOU KILLED', W / 2 + 40, 290);
    g.fillStyle = '#FF5C7A'; g.font = '500 52px "IBM Plex Mono", monospace'; g.fillText(cfConf.toFixed(2), W / 2 + 40, 360);
    g.fillStyle = '#C9CFE0'; g.font = '300 22px "Fraunces", Georgia, serif'; wrap(CF_LABELS[runnerUp % CF_LABELS.length] + ' — the road you did not take', W / 2 + 40, 410, W / 2 - 104, 30);
    g.fillStyle = '#46506e'; g.font = '400 15px "IBM Plex Mono", monospace'; g.fillText('reality #' + ((seed % 100000) + '').padStart(5, '0') + '   ·   anyone who asks this gets this exact reality', 64, H - 38);
    const url = location.origin + location.pathname + '?d=' + encodeURIComponent(decision || '');
    cv.toBlob((blob) => {
      if (!blob) return; const file = new File([blob], 'nexus-reality.png', { type: 'image/png' });
      const nav = navigator as any;
      if (nav.canShare && nav.canShare({ files: [file] })) { nav.share({ files: [file], title: 'Nexus — the future that survived', text: 'I asked Nexus ' + (decision ? `"${decision}"` : 'a decision') + '. Ask it yours:', url }).catch(() => {}); return; }
      const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'nexus-reality.png'; a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 4000);
      navigator.clipboard?.writeText(url).catch(() => {});
    }, 'image/png');
  };

  const id5 = (n: number) => ((n % 100000) + '').padStart(5, '0');

  return (
    <>
      {/* the Probability Ledger — the forest is a model, not décor */}
      <div className={`nx-ledger ${ledgerRows.length ? 'show' : ''}`}>
        <div className="lg-eye">possibility space</div>
        {ledgerRows.map((r) => (
          <div key={r.b} className={`lg-row ${r.surv ? 'surv' : ''} ${r.killed ? 'killed' : ''} ${r.dead ? 'dead' : ''}`} onClick={() => focusBranch(r.b)}>
            <span className="dot" /><span className="nm">{r.label}</span>
            <span className="bar"><i style={{ width: Math.max(4, r.pc) + '%' }} /></span><span className="pc">{r.pc}%</span>
          </div>
        ))}
      </div>

      {/* the Lineage rail — the realities you have collapsed (a living system) */}
      <div className={`nx-lineage ${lineage.length ? 'show' : ''}`}>
        <div className="ln-eye">your realities</div>
        {lineage.map((L, k) => (
          <div key={k} className={`ln-dot ${L.killed ? 'killed' : ''}`} title={'reality #' + id5(L.seed)} onClick={() => restore(k)}>
            <span className="tip">#{id5(L.seed)} · {L.label}{L.killed ? ' · let go' : ''}</span>
          </div>
        ))}
      </div>

      <div className={`nx-caption ${showCap ? 'show' : ''}`} aria-hidden>
        <div className="eyebrow">{act >= 0 ? ACTS[act].eye : ''}</div>
        <div className="line">{act >= 0 ? ACTS[act].line : ''}</div>
      </div>

      <div className={`nx-reveal ${revealed ? 'show' : ''}`}>
        <div className="eye">{readback.eye}</div>
        <div className="read">{readback.lines.map((l, k) => <span key={k}>{l}</span>)}</div>
        {card && (
          <div className="nx-card" aria-label="Nexus decision read-out">
            <div className="row"><span className="ck">decision</span><span className="cv gold">{card.decision}</span></div>
            <div className="row"><span className="ck">survives at</span><span className="cv conf">{card.confidence.toFixed(2)}{delta != null && <span className={`delta ${delta < 0 ? 'down' : 'up'}`}>{(delta < 0 ? ' ↓ ' : ' ↑ ') + Math.abs(delta).toFixed(2)}</span>}</span></div>
            <div className="row"><span className="ck">because</span><span className="cv">{card.why}</span></div>
            <div className="row"><span className="ck">watch</span><span className="cv dis">{card.watch}</span></div>
          </div>
        )}
        <div className="sub">{ending || (doorOpen ? 'You are inside Nexus now. Every constraint re-decides reality in place.' : 'This is the future that survives if nothing changes. Something always changes — argue with it.')}</div>
        {sacrifice && <div className={`nx-sacrifice ${/^same survivor/.test(sacrifice) ? 'mute' : ''} show`}>{sacrifice}</div>}

        {/* constraint chips — a re-collapse is always one tap away */}
        <div className="nx-chips">
          {CHIPS.map((c) => <button key={c} className="chip" onClick={() => recollapse(c)}>{c}</button>)}
        </div>

        {identity && <div className="nx-identity show">{identity}</div>}

        {doorOpen && (
          <div className="nx-door show">
            <div className="d-eye">change one thing — watch reality re-decide</div>
            <div className="d-wrap">
              <input className="nx-door-input" autoComplete="off" spellCheck={false} placeholder="add a constraint… e.g. only 8 months of runway"
                value={constraint} onChange={(e) => setConstraint(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') fork(constraint); }} />
              <button className="nx-door-go" onClick={() => fork(constraint)}>re-run</button>
            </div>
          </div>
        )}
        <div className="nx-actions">
          <button className="nx-enter" onClick={enter}>Enter Nexus</button>
          <button className="nx-share" onClick={shareCard}>take your reality card</button>
        </div>
        <div className="whisper">{whisper}</div>
      </div>
    </>
  );
}
