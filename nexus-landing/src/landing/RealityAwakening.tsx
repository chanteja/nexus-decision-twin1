// src/landing/RealityAwakening.tsx
// The persistent world — the Tree of Futures. One BufferGeometry, one GPU morph
// shader carries the whole arc with zero per-frame CPU buffer writes:
//   seed → roots(data) → trunk(emergence) → canopy(the forest) →
//   intelligence(the forest thinks) → selection(most futures die) →
//   survivor + memory(the mark) → universe(the seed was everything).
//
// v8 "Mirror":
//  • the seed is the visitor's own decision (deterministic): same decision, same reality.
//  • P0-1 agency — survivor is argmax(attention); if the cursor never moved, the survivor is
//    chosen deterministically from the decision (never screen-centre random), and we keep the
//    runner-up: the future that was one hesitation away (the Counterfactual).
//  • the Bridge — at selection the survivor resolves into a real decision read-out (composeCard).
//  • conservation — dead futures stream INTO the survivor and it brightens by what they lose.
//  • font-race fix — the wordmark re-samples once document.fonts is ready.
import * as THREE from 'three';
import { useMemo, useRef, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { phaseApi } from './phaseStore';
import { pointer, composeCard, seedFromText, biasAttention, makeBranchLabels, whyCategory, CF_LABELS } from './behavior';

const PAL = {
  data: new THREE.Color('#4DE0E8'), possible: new THREE.Color('#8B6CFF'),
  life: new THREE.Color('#46C98A'), bark: new THREE.Color('#9A6B3F'),
  surv: new THREE.Color('#F4C770'), dis: new THREE.Color('#FF5C7A'), faint: new THREE.Color('#1d2640'),
};

function mulberry32(a: number) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);
function bend(dir: THREE.Vector3, tilt: number, az: number) {
  const d = dir.clone().normalize();
  const t = Math.abs(d.y) < 0.99 ? V(0, 1, 0) : V(1, 0, 0);
  const r = new THREE.Vector3().crossVectors(d, t).normalize();
  const f = new THREE.Vector3().crossVectors(d, r);
  const st = Math.sin(tilt), ct = Math.cos(tilt);
  const off = r.clone().multiplyScalar(Math.cos(az) * st).add(f.multiplyScalar(Math.sin(az) * st));
  return d.multiplyScalar(ct).add(off).normalize();
}
const T = { BRANCHES: 7, TRUNK_H: 300, LIMB_LEN: 470, DECAY: 0.74, MAX_DEPTH: 5, ROOT_H: 230, ROOT_LEN: 360, ROOT_DECAY: 0.72, ROOT_DEPTH: 4, ROOT_FANS: 6 };

type Seg = { a: THREE.Vector3; b: THREE.Vector3; gen: number; future: number; lead: number };
function buildTree(seedNum: number) {
  const rng = mulberry32(seedNum >>> 0);
  const wood: Seg[] = [], roots: Seg[] = [], tips: { p: THREE.Vector3; future: number }[] = [];
  const crown = V(0, T.TRUNK_H, 0); const steps = 4;
  for (let i = 0; i < steps; i++) wood.push({ a: V(0, T.TRUNK_H / steps * i, 0), b: V(0, T.TRUNK_H / steps * (i + 1), 0), gen: 0, future: -1, lead: 0 });
  const growW = (start: THREE.Vector3, dir: THREE.Vector3, len: number, gen: number, future: number) => {
    const end = start.clone().add(dir.clone().multiplyScalar(len)); const lead = gen >= T.MAX_DEPTH ? 1 : 0;
    wood.push({ a: start, b: end, gen, future, lead });
    if (lead) { tips.push({ p: end, future }); return; }
    const kids = gen === 0 ? 1 : (rng() < 0.55 ? 3 : 2);
    for (let k = 0; k < kids; k++) {
      const tilt = (gen === 0 ? 0.32 : 0.42) + rng() * 0.22, az = rng() * Math.PI * 2;
      const nd = bend(dir, tilt, az); nd.y = Math.max(nd.y, gen < 2 ? 0.25 : -0.15); nd.normalize();
      growW(end, nd, len * (T.DECAY + rng() * 0.06), gen + 1, future);
    }
  };
  for (let b = 0; b < T.BRANCHES; b++) { const ang = (b / T.BRANCHES) * Math.PI * 2 + rng() * 0.3, out = 0.62 + rng() * 0.16; growW(crown, V(Math.cos(ang) * out, 0.78, Math.sin(ang) * out).normalize(), T.LIMB_LEN, 0, b); }
  const floor = V(0, -T.ROOT_H, 0); roots.push({ a: V(0, 0, 0), b: floor, gen: 0, future: -1, lead: 0 });
  const growR = (start: THREE.Vector3, dir: THREE.Vector3, len: number, gen: number) => {
    const end = start.clone().add(dir.clone().multiplyScalar(len)); roots.push({ a: start, b: end, gen, future: -1, lead: 0 });
    if (gen >= T.ROOT_DEPTH) return; const kids = rng() < 0.6 ? 3 : 2;
    for (let k = 0; k < kids; k++) { const tilt = 0.55 + rng() * 0.35, az = rng() * Math.PI * 2; const nd = bend(dir, tilt, az); nd.x *= 1.3; nd.z *= 1.3; nd.y = Math.min(nd.y, -0.18); nd.normalize(); growR(end, nd, len * (T.ROOT_DECAY + rng() * 0.05), gen + 1); }
  };
  for (let f = 0; f < T.ROOT_FANS; f++) { const ang = (f / T.ROOT_FANS) * Math.PI * 2 + rng() * 0.4; growR(floor, V(Math.cos(ang) * 0.9, -0.7, Math.sin(ang) * 0.9).normalize(), T.ROOT_LEN, 1); }
  return { wood, roots, tips, crown, survivor: (rng() * T.BRANCHES) | 0, rng };
}

function sampleLogo(n: number, out?: Float32Array): Float32Array {
  const cv = document.createElement('canvas'); const W = 1024, H = 300; cv.width = W; cv.height = H;
  const x = cv.getContext('2d')!; x.fillStyle = '#fff'; x.textAlign = 'center'; x.textBaseline = 'middle';
  x.font = '700 200px "Space Grotesk", system-ui, sans-serif'; x.fillText('NEXUS', W / 2, H / 2 + 6);
  const d = x.getImageData(0, 0, W, H).data; const pts: number[] = [];
  for (let i = 0; i < 2_000_000 && pts.length < n * 3; i++) { const px = (Math.random() * W) | 0, py = (Math.random() * H) | 0; if (d[(py * W + px) * 4 + 3] > 128) pts.push(px, py); }
  const arr = out ?? new Float32Array(n * 3);
  if (pts.length < 2) return arr;
  for (let i = 0; i < n; i++) { const j = (i % (pts.length / 2)) | 0, px = pts[j * 2], py = pts[j * 2 + 1]; arr[i * 3] = ((px - W / 2) / W) * 900; arr[i * 3 + 1] = (-(py - H / 2) / H) * 260 + 1050; arr[i * 3 + 2] = (Math.random() * 16 - 8); }
  return arr;
}

export function RealityAwakening({ seed, count = 7200, stars = 1500 }: { seed: number; count?: number; stars?: number }) {
  const { camera } = useThree();
  const geoRef = useRef<THREE.BufferGeometry>(null);
  const attention = useRef<Float32Array>(new Float32Array(T.BRANCHES));
  const dwell = useRef(0);
  const whyCatRef = useRef<string[]>([]);   // v9 — categories of accepted survivors (the mirror)
  const ledgerThrottle = useRef(0);

  const data = useMemo(() => {
    const SEED = (seed >>> 0) || ((Math.random() * 1e9) | 0);
    const tree = buildTree(SEED); const survivor = tree.survivor; const rng = tree.rng;
    const jit = (s: number) => (rng() * 2 - 1) * s;
    const aSeed3 = new Float32Array(count * 3), aGrow = new Float32Array(count * 3), aTree = new Float32Array(count * 3),
      aFallen = new Float32Array(count * 3), aLogo = sampleLogo(count), aKind = new Float32Array(count),
      aSurv = new Float32Array(count), aFuture = new Float32Array(count), aRand = new Float32Array(count), aBranch = new Float32Array(count);
    const setV = (arr: Float32Array, i: number, x: number, y: number, z: number) => { arr[i * 3] = x; arr[i * 3 + 1] = y; arr[i * 3 + 2] = z; };
    const onSeg = (s: Seg, scale = 1) => { const t = rng(); const r = Math.max(2, (8 - s.gen * 1.2)) * scale; return [s.a.x + (s.b.x - s.a.x) * t + jit(r), s.a.y + (s.b.y - s.a.y) * t + jit(r), s.a.z + (s.b.z - s.a.z) * t + jit(r)] as const; };
    const pickWood = () => { let s: Seg; do { s = tree.wood[(rng() * tree.wood.length) | 0]; } while (rng() > 1 / (1 + s.gen * 0.5)); return s; };
    const nRoot = Math.floor(count * 0.14), nWood = Math.floor(count * 0.18), nLeaf = count - nRoot - nWood;
    let i = 0;
    for (let k = 0; k < nRoot; k++, i++) { setV(aSeed3, i, jit(7), jit(7) + 4, jit(7)); const v = onSeg(tree.roots[(rng() * tree.roots.length) | 0]); setV(aTree, i, v[0], v[1], v[2]); setV(aGrow, i, jit(4), jit(4), jit(4)); setV(aFallen, i, v[0], v[1], v[2]); aKind[i] = 0; aSurv[i] = 1; aFuture[i] = 0; aRand[i] = rng() * 6.283; aBranch[i] = -1; }
    for (let k = 0; k < nWood; k++, i++) { setV(aSeed3, i, jit(7), jit(7) + 4, jit(7)); const s = pickWood(); const v = onSeg(s); setV(aTree, i, v[0], v[1], v[2]); setV(aGrow, i, jit(5), jit(5), jit(5)); setV(aFallen, i, v[0] + jit(120), -T.ROOT_H * 0.15 + jit(20), v[2] + jit(120)); aKind[i] = 1; aSurv[i] = (s.future === survivor || s.future === -1) ? 1 : 0; aFuture[i] = s.future < 0 ? 0.5 : s.future / T.BRANCHES; aRand[i] = rng() * 6.283; aBranch[i] = s.future; }
    for (let k = 0; k < nLeaf; k++, i++) { setV(aSeed3, i, jit(7), jit(7) + 4, jit(7)); const tip = tree.tips[(rng() * tree.tips.length) | 0]; const c = tip.p; const sp = 26 + rng() * 30; const v = [c.x + jit(sp), c.y + jit(sp) * 0.9 + 6, c.z + jit(sp)]; setV(aTree, i, v[0], v[1], v[2]); setV(aGrow, i, c.x + jit(6), c.y + jit(6), c.z + jit(6)); setV(aFallen, i, v[0] + jit(160), -T.ROOT_H * 0.1 + jit(24), v[2] + jit(160)); aKind[i] = 2; aSurv[i] = (tip.future === survivor) ? 1 : 0; aFuture[i] = tip.future / T.BRANCHES; aRand[i] = rng() * 6.283; aBranch[i] = tip.future; }

    const branchAnchors: THREE.Vector3[] = [];
    for (let b = 0; b < T.BRANCHES; b++) { const ts = tree.tips.filter(t => t.future === b); const cc = new THREE.Vector3(); ts.forEach(t => cc.add(t.p)); if (ts.length) cc.multiplyScalar(1 / ts.length); else cc.copy(tree.crown); branchAnchors.push(cc); }
    const crownPt = tree.crown.clone();
    const futures = 9000 + tree.tips.length * 7 + (SEED % 1700);

    const tipPts = tree.tips.map(t => t.p); const epos: number[] = [], eseed: number[] = []; const MAXE = stars < 1000 ? 500 : 900;
    for (let e = 0; e < MAXE && tipPts.length > 2; e++) { const a = tipPts[(rng() * tipPts.length) | 0]; let best: THREE.Vector3 | null = null, bd = 1e9; for (let s = 0; s < 6; s++) { const b = tipPts[(rng() * tipPts.length) | 0]; const dd = a.distanceToSquared(b); if (dd > 1 && dd < bd) { bd = dd; best = b; } } if (best && bd < 260 * 260) { epos.push(a.x, a.y, a.z, best.x, best.y, best.z); const sd = rng() * 6.28; eseed.push(sd, sd); } }

    const spos = new Float32Array(stars * 3), srnd = new Float32Array(stars);
    for (let s = 0; s < stars; s++) { const v = new THREE.Vector3(Math.random() * 2 - 1, Math.random() * 2 - 1, Math.random() * 2 - 1).normalize().multiplyScalar(2600 + Math.random() * 2400); spos[s * 3] = v.x; spos[s * 3 + 1] = v.y + 1050; spos[s * 3 + 2] = v.z; srnd[s] = Math.random() * 6.28; }

    return { SEED, aSeed3, aGrow, aTree, aFallen, aLogo, aKind, aSurv, aFuture, aRand, aBranch, branchAnchors, crownPt, futures, epos: new Float32Array(epos), eseed: new Float32Array(eseed), spos, srnd };
  }, [count, stars, seed]);

  // font-race fix: re-sample the wordmark once the webfont is actually ready
  useEffect(() => {
    let alive = true;
    (document.fonts?.ready ?? Promise.resolve()).then(() => {
      if (!alive) return;
      sampleLogo(count, data.aLogo);
      const g = geoRef.current; if (g && g.attributes.aLogo) (g.attributes.aLogo as THREE.BufferAttribute).needsUpdate = true;
    });
    return () => { alive = false; };
  }, [data, count]);

  // P0-1/P0-2 + v9 — selection is re-entrant: the SAME routine locks the first survivor AND
  // re-decides under a live constraint. No geometry rebuild; we rewrite aSurv/aFallen and replay the morph.
  useEffect(() => {
    // decision-shaped baseline so the forest reads as a populated model from the first frame
    const att = attention.current;
    for (let b = 0; b < T.BRANCHES; b++) att[b] = 0.15 + (((data.SEED >>> (b * 3)) & 7) / 7) * 0.28;
    whyCatRef.current = [];
    phaseApi.setState({ branchLabels: makeBranchLabels(data.SEED, T.BRANCHES), futures: data.futures });

    const { aBranch, aKind, aSurv, aFallen } = data;
    const applySelection = (survivor: number) => {
      const core = data.branchAnchors[survivor], crown = data.crownPt;
      const jit = (m: number) => (Math.random() * 2 - 1) * m;
      for (let k = 0; k < count; k++) {
        const br = aBranch[k], kind = aKind[k];
        const surv = kind === 0 ? 1 : (kind === 1 ? ((br === survivor || br < 0) ? 1 : 0) : (br === survivor ? 1 : 0));
        aSurv[k] = surv;
        if (!surv) { const tt = 0.42 + Math.random() * 0.6; aFallen[k * 3] = crown.x + (core.x - crown.x) * tt + jit(46); aFallen[k * 3 + 1] = crown.y + (core.y - crown.y) * tt + jit(40); aFallen[k * 3 + 2] = crown.z + (core.z - crown.z) * tt + jit(46); }
      }
      const g = geoRef.current; if (g) { (g.attributes.aSurv as THREE.BufferAttribute).needsUpdate = true; (g.attributes.aFallen as THREE.BufferAttribute).needsUpdate = true; }
    };

    const rows = (live: boolean) => {
      const s = phaseApi.getState(); const sum = att.reduce((a, b) => a + b, 0) || 1;
      const order = [...Array(T.BRANCHES).keys()].sort((a, b) => att[b] - att[a]);
      return order.map((b) => {
        const surv = !live && b === s.survivor && s.survivorChosen;
        const killed = !live && s.lineage.some((L) => L.killedBranch === b);
        const dead = !live && !surv && !killed && s.survivorChosen;
        return { b, pc: Math.round(att[b] / sum * 100), label: s.branchLabels[b] || ('future ' + b), surv, killed, dead };
      });
    };
    const pushLineage = (survivor: number, killed: boolean, killedBranch: number) => {
      const s = phaseApi.getState(); const c = s.card!; if (!c) return;
      const entry = { seed: (data.SEED ^ seedFromText(c.decision + s.collapseCount)) >>> 0, dec: c.decision, conf: c.confidence, why: c.why, watch: c.watch, label: s.branchLabels[survivor] || 'a path', killed, killedBranch, reverted: false };
      phaseApi.setState({ lineage: [...s.lineage, entry] });
    };
    const identityLine = () => {
      const s = phaseApi.getState(); if (s.collapseCount < 3) return '';
      const counts: Record<string, number> = {}; whyCatRef.current.forEach((c) => counts[c] = (counts[c] || 0) + 1);
      const reverts = s.lineage.filter((L) => L.reverted).length;
      const dom = Object.keys(counts).sort((a, b) => counts[b] - counts[a])[0];
      if (reverts >= 2) return `Across ${s.collapseCount} versions you keep returning to the reality you started with. You already knew — you wanted to be talked out of it.`;
      if (dom === 'robustness') return `Across ${s.collapseCount} versions you kept the branch that survives being wrong. You optimise for not-dying, not for winning.`;
      if (dom === 'optionality') return `Across ${s.collapseCount} versions you refused to close doors — even when closing one was the decision.`;
      if (dom === 'patience') return `Across ${s.collapseCount} versions you chose the branch that compounds. You are playing a longer game than the question asked.`;
      return `Across ${s.collapseCount} versions you chose the branch that costs least when you're wrong. You price downside before upside.`;
    };

    const decide = () => {
      const s = phaseApi.getState(); if (s.survivorChosen) return;
      const order = [...Array(T.BRANCHES).keys()].sort((a, b) => att[b] - att[a]);
      const survivor = order[0]; let runnerUp = order[1]; if (runnerUp === survivor) runnerUp = (runnerUp + 1) % T.BRANCHES;
      applySelection(survivor);
      const sum = att.reduce((a, b) => a + b, 0); const conc = sum > 0 ? att[survivor] / sum : 0;
      const card = composeCard(s.decision, data.SEED, survivor, conc, dwell.current, '');
      whyCatRef.current = [whyCategory(card.why)];
      phaseApi.setState({ survivorChosen: true, survivor, runnerUp, card, collapseCount: 1 });
      pushLineage(survivor, false, -1);
      phaseApi.setState({ ledgerRows: rows(false) });
    };

    const recollapse = (constraint: string) => {
      const v = (constraint || '').trim(); const s0 = phaseApi.getState();
      if (!v || s0.reCollapsing || !s0.survivorChosen) return;
      const prevSurv = s0.survivor; const prevConf = s0.card ? s0.card.confidence : 0;
      biasAttention(att, v);
      const order = [...Array(T.BRANCHES).keys()].sort((a, b) => att[b] - att[a]);
      const survivor = order[0]; let runnerUp = order[1]; if (runnerUp === survivor) runnerUp = (runnerUp + 1) % T.BRANCHES;
      applySelection(survivor);
      const killed = survivor !== prevSurv;
      const sum = att.reduce((a, b) => a + b, 0); const conc = sum > 0 ? att[survivor] / sum : 0;
      const card = composeCard(s0.decision, data.SEED, survivor, conc, dwell.current, v);
      whyCatRef.current.push(whyCategory(card.why));
      uniforms.uAttack.value = 1.0;
      const sacrifice = killed
        ? `you just let go of ${CF_LABELS[prevSurv % CF_LABELS.length]} — it needed one more reason you didn't give it.`
        : 'same survivor. your decision is robust to that.';
      phaseApi.setState({ survivor, runnerUp, card, sacrifice, collapseCount: s0.collapseCount + 1, reCollapsing: true });
      pushLineage(survivor, killed, killed ? prevSurv : -1);
      phaseApi.setState({ ledgerRows: rows(false), identity: identityLine() });
      void prevConf;
      // replay the morph through the existing finale channel: release → re-die → re-compose
      const reduce = typeof window !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (reduce) { phaseApi.setState({ reCollapsing: false }); return; }
      phaseApi.setState({ seqActive: true, seqTarget: 4.2 });
      setTimeout(() => phaseApi.setState({ seqTarget: 6.4 }), 950);
      setTimeout(() => phaseApi.setState({ reCollapsing: false }), 1850);
    };

    const focusBranch = (b: number) => {
      const a = data.branchAnchors[b]; if (!a) return;
      phaseApi.setState({ camFocus: [a.x, a.y, a.z], camFocusUntil: performance.now() + 2600 });
      uniforms.uAttack.value = Math.max(uniforms.uAttack.value, 0.6);
    };

    const restore = (i: number) => {
      const s = phaseApi.getState(); const L = s.lineage[i]; if (!L) return;
      const lineage = s.lineage.slice(); lineage[i] = { ...L, reverted: true };
      phaseApi.setState({ card: { decision: L.dec, confidence: L.conf, why: L.why, watch: L.watch }, lineage, sacrifice: '' });
    };

    phaseApi.setState({ decide, recollapse, focusBranch, restore });
  }, [data, camera, count, uniforms]);

  const uniforms = useMemo(() => ({
    uPhase: { value: 0 }, uTime: { value: 0 }, uAttack: { value: 0 }, uSize: { value: 2.8 }, uPix: { value: Math.min(typeof devicePixelRatio !== 'undefined' ? devicePixelRatio : 1, 2) },
    cData: { value: PAL.data }, cPoss: { value: PAL.possible }, cLife: { value: PAL.life }, cBark: { value: PAL.bark }, cSurv: { value: PAL.surv }, cDis: { value: PAL.dis }, cFaint: { value: PAL.faint },
  }), []);
  const edgeU = useMemo(() => ({ uPhase: uniforms.uPhase, uTime: uniforms.uTime, cLife: { value: PAL.life }, cPoss: { value: PAL.possible } }), [uniforms]);
  const starU = useMemo(() => ({ uPhase: uniforms.uPhase, uTime: uniforms.uTime, uPix: uniforms.uPix }), [uniforms]);
  const lastAttack = useRef(0);

  useFrame((_, dt) => {
    const st = phaseApi.getState(); uniforms.uTime.value += dt;
    uniforms.uPhase.value += (st.phase - uniforms.uPhase.value) * Math.min(1, dt * 6);
    const ph = uniforms.uPhase.value; const now = performance.now();

    if (st.intro >= 1 && ph >= 1.8 && ph < 3.7) {
      const att = attention.current; const cx = pointer.tx * 2, cy = -pointer.ty * 2;
      for (let b = 0; b < T.BRANCHES; b++) { const n = data.branchAnchors[b].clone().project(camera); const ddx = n.x - cx, ddy = n.y - cy; att[b] += dt / (0.06 + ddx * ddx + ddy * ddy); }
    }
    // v9 — surface the model live: the forest is 7 weighted futures
    if (st.intro >= 1 && !st.survivorChosen && ph >= 2.2 && ph < 4.6) {
      ledgerThrottle.current += dt;
      if (ledgerThrottle.current > 0.14) {
        ledgerThrottle.current = 0;
        const att = attention.current; const sum = att.reduce((a, b) => a + b, 0) || 1;
        const order = [...Array(T.BRANCHES).keys()].sort((a, b) => att[b] - att[a]);
        const labels = st.branchLabels;
        phaseApi.setState({ ledgerRows: order.map((b) => ({ b, pc: Math.round(att[b] / sum * 100), label: labels[b] || ('future ' + b), surv: false, killed: false, dead: false })) });
      }
    }
    if (st.intro >= 1 && ph >= 3.0 && ph < 4.5) dwell.current += dt;   // conviction at the brink (feeds the card)

    if (ph > 3.6 && ph < 4.7 && now > lastAttack.current) { uniforms.uAttack.value = 1; lastAttack.current = now + (260 + Math.random() * 260); }
    uniforms.uAttack.value *= Math.pow(0.001, dt);
  });

  return (
    <group>
      <points>
        <bufferGeometry ref={geoRef}>
          <bufferAttribute attach="attributes-position" args={[data.aSeed3.slice(), 3]} />
          <bufferAttribute attach="attributes-aSeed3" args={[data.aSeed3, 3]} />
          <bufferAttribute attach="attributes-aGrow" args={[data.aGrow, 3]} />
          <bufferAttribute attach="attributes-aTree" args={[data.aTree, 3]} />
          <bufferAttribute attach="attributes-aFallen" args={[data.aFallen, 3]} />
          <bufferAttribute attach="attributes-aLogo" args={[data.aLogo, 3]} />
          <bufferAttribute attach="attributes-aKind" args={[data.aKind, 1]} />
          <bufferAttribute attach="attributes-aSurv" args={[data.aSurv, 1]} />
          <bufferAttribute attach="attributes-aFuture" args={[data.aFuture, 1]} />
          <bufferAttribute attach="attributes-aRand" args={[data.aRand, 1]} />
          <bufferAttribute attach="attributes-aBranch" args={[data.aBranch, 1]} />
        </bufferGeometry>
        <shaderMaterial uniforms={uniforms} transparent depthWrite={false} blending={THREE.AdditiveBlending} vertexShader={POINT_VS} fragmentShader={POINT_FS} />
      </points>
      <lineSegments>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[data.epos, 3]} />
          <bufferAttribute attach="attributes-aSeed" args={[data.eseed, 1]} />
        </bufferGeometry>
        <shaderMaterial uniforms={edgeU} transparent depthWrite={false} blending={THREE.AdditiveBlending} vertexShader={EDGE_VS} fragmentShader={EDGE_FS} />
      </lineSegments>
      <points>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[data.spos, 3]} />
          <bufferAttribute attach="attributes-aRnd" args={[data.srnd, 1]} />
        </bufferGeometry>
        <shaderMaterial uniforms={starU} transparent depthWrite={false} blending={THREE.AdditiveBlending} vertexShader={STAR_VS} fragmentShader={STAR_FS} />
      </points>
    </group>
  );
}

const POINT_VS = /* glsl */`
 uniform float uPhase,uTime,uSize,uPix;
 attribute vec3 aSeed3,aGrow,aTree,aFallen,aLogo; attribute float aKind,aSurv,aFuture,aRand,aBranch;
 varying float vKind,vSurv,vFuture,vSeg,vRand,vAlpha;
 float ss(float a,float b,float x){return smoothstep(a,b,x);}
 void main(){
   float p=uPhase; vec3 pos;
   if(aKind<0.5){ pos=mix(aSeed3,aTree,ss(0.0,1.0,p)); }
   else if(aKind<1.5){ pos=mix(aSeed3,aTree,ss(1.0,2.0,p)); if(aSurv<0.5) pos=mix(pos,aFallen,ss(4.0,5.0,p)); pos=mix(pos,aLogo,ss(5.0,6.0,p)); }
   else { pos=mix(aSeed3,aGrow,ss(1.6,2.0,p)); pos=mix(pos,aTree,ss(2.0,3.0,p));
     if(aSurv<0.5){ float c=ss(4.0,5.0,p); vec3 fall=aFallen+vec3(sin(uTime*1.7+aRand)*16.0*c,sin(uTime*1.3+aRand)*10.0*c,cos(uTime*1.5+aRand)*16.0*c); pos=mix(pos,fall,c); }
     pos=mix(pos,aLogo,ss(5.0,6.0,p)); }
   float br=0.6+0.4*sin(uTime*0.5+aRand);
   float amp=(p<2.0?9.0:4.0)*(1.0-ss(5.0,6.0,p));
   pos+=vec3(sin(uTime*0.3+aRand),cos(uTime*0.27+aRand*1.3),sin(uTime*0.2+aRand*0.7))*amp;
   vKind=aKind; vSurv=aSurv; vFuture=aFuture; vSeg=p; vRand=aRand;
   float fade=1.0;
   if(aSurv<0.5 && aKind>0.5) fade=mix(mix(1.0,0.16,ss(4.0,5.0,p)),0.85,ss(5.0,6.0,p));
   if(aKind<0.5) fade=mix(1.0,0.45,ss(5.0,6.0,p));
   vAlpha=br*fade;
   vec4 mv=modelViewMatrix*vec4(pos,1.0);
   gl_PointSize=uSize*uPix*(360.0/-mv.z)*(0.7+0.6*br);
   gl_Position=projectionMatrix*mv;
 }`;
const POINT_FS = /* glsl */`
 precision mediump float; uniform float uPhase,uTime,uAttack;
 uniform vec3 cData,cPoss,cLife,cBark,cSurv,cDis,cFaint;
 varying float vKind,vSurv,vFuture,vSeg,vRand,vAlpha;
 float ss(float a,float b,float x){return smoothstep(a,b,x);}
 void main(){
   vec2 d=gl_PointCoord-0.5; float r=dot(d,d); if(r>0.25)discard; float core=ss(0.25,0.0,r);
   vec3 col;
   if(vKind<0.5){ col=mix(cFaint,cData,ss(0.0,1.0,vSeg)); col=mix(col,cSurv,ss(5.0,6.0,vSeg)*0.5); }
   else if(vKind<1.5){ col=mix(cFaint,cBark,ss(1.0,2.0,vSeg)); }
   else { vec3 leaf=mix(cLife,cPoss,vFuture*0.5); col=mix(cFaint,leaf,ss(2.0,3.0,vSeg));
     float think=ss(3.0,3.6,vSeg)*(1.0-ss(4.2,4.8,vSeg));
     col+=cPoss*think*(0.35+0.65*pow(0.5+0.5*sin(uTime*2.2+vRand*9.0),3.0)); }
   if(vKind>0.5){ float collapse=ss(4.0,5.0,vSeg); col=mix(col,mix(cDis,cSurv,vSurv),collapse); col+=cDis*uAttack*(1.0-vSurv)*ss(3.6,4.4,vSeg);
     col+=cSurv*vSurv*collapse*1.05; }
   col=mix(col,cSurv,ss(5.0,6.0,vSeg)*0.92); col+=col*core*1.4;
   gl_FragColor=vec4(col,vAlpha*core);
 }`;
const EDGE_VS = /* glsl */`
 uniform float uPhase,uTime; attribute float aSeed; varying float vF; varying float vG;
 void main(){
   float grow=smoothstep(2.4,3.2,uPhase);
   float dim=1.0-smoothstep(4.0,4.8,uPhase)*0.7;
   float graph=smoothstep(5.3,6.3,uPhase); vG=graph;
   float vis=max(grow*dim,graph);
   float signal=0.30+0.70*pow(0.5+0.5*sin(uTime*2.0 - aSeed*3.0),3.0);
   vF=vis*signal; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`;
const EDGE_FS = /* glsl */`
 precision mediump float; uniform float uPhase; uniform vec3 cLife,cPoss; varying float vF; varying float vG;
 void main(){ vec3 c=mix(cLife,cPoss,smoothstep(3.0,3.8,uPhase)); gl_FragColor=vec4(c, vF*0.14 + vF*vG*0.20); }`;
const STAR_VS = /* glsl */`
 uniform float uPhase,uTime,uPix; attribute float aRnd; varying float vA;
 void main(){ vA=smoothstep(5.3,6.4,uPhase)*(0.5+0.5*sin(uTime*0.8+aRnd));
   vec4 mv=modelViewMatrix*vec4(position,1.0); gl_PointSize=1.6*uPix*(360.0/-mv.z); gl_Position=projectionMatrix*mv; }`;
const STAR_FS = /* glsl */`
 precision mediump float; varying float vA;
 void main(){ vec2 d=gl_PointCoord-0.5; if(dot(d,d)>0.25)discard; gl_FragColor=vec4(0.8,0.86,1.0,vA*0.9); }`;
