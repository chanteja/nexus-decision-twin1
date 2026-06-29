// src/landing/Hud.tsx
// Instrument overlay — control-room presence. Reads the REAL backend status so
// the page feels like an operating system that was running before you arrived.
import { useNexusStatus } from './useNexusData';

export function Hud() {
  const s = useNexusStatus();
  const up = Math.floor(s.uptimeS);
  const fmt = `${(up / 3600) | 0}h ${((up % 3600) / 60) | 0}m ${up % 60 | 0}s`;
  return (
    <div className="nx-hud" aria-hidden>
      <div><span className="k">nexus</span> · reality-anchored os</div>
      <div><span className="k">status</span> <span className="v" data-ok={s.status === 'ready'}>{s.status}{s.live ? '' : ' · demo'}</span></div>
      <div><span className="k">uptime</span> <span className="v">{fmt}</span></div>
      <div><span className="k">engines</span> <span className="v">{s.engines} online</span></div>
      <div><span className="k">ledger</span> <span className="v">{s.events}</span> futures recorded · chain <span className="ok">{s.chainValid ? '✓ valid' : '…'}</span></div>
      <div><span className="k">graph</span> <span className="v">{s.nodes}</span> nodes · <span className="v">{s.edges}</span> edges</div>
    </div>
  );
}
