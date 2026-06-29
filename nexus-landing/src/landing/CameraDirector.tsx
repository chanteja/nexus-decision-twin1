// src/landing/CameraDirector.tsx
// The camera is the storyteller. It dollies through the Tree of Futures per phase.
// v7: pose 6 pushes INTO the surviving limb and pose 7 frames the mark + graph
// (a dive, not a pull-out) so the wordmark that composes from the survivor is the
// last thing you see. Parallax quiets through the Silence and reveal.
import * as THREE from 'three';
import { useRef } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import { phaseApi } from './phaseStore';
import { pointer } from './behavior';

const V = (x: number, y: number, z: number) => new THREE.Vector3(x, y, z);
// 8 poses · tree spans y≈-960..1820, canopy mass ≈1050
const RIG: { pos: THREE.Vector3; look: THREE.Vector3 }[] = [
  { pos: V(0, 20, 300),      look: V(0, 10, 0) },     // 0 seed
  { pos: V(0, -220, 620),    look: V(0, -360, 0) },   // 1 roots
  { pos: V(60, 520, 1120),   look: V(0, 560, 0) },    // 2 emergence
  { pos: V(0, 1000, 2150),   look: V(0, 1020, 0) },   // 3 forest
  { pos: V(360, 1200, 1150), look: V(0, 1180, 0) },   // 4 intelligence
  { pos: V(0, 820, 1820),    look: V(0, 880, 0) },    // 5 selection
  { pos: V(0, 1050, 720),    look: V(0, 1050, 0) },   // 6 survivor — push INTO the surviving limb
  { pos: V(0, 1050, 1650),   look: V(0, 1050, 0) },   // 7 reveal — branch resolves to graph, the mark composes
];
const smooth = (t: number) => t * t * (3 - 2 * t);

export function CameraDirector() {
  const { camera } = useThree();
  const m = useRef({ x: 0, y: 0 });

  useFrame((_, dt) => {
    const st = phaseApi.getState();
    const ph = st.phase;
    const i = Math.min(RIG.length - 2, Math.floor(ph)); const t = smooth(ph - i);
    const pos = RIG[i].pos.clone().lerp(RIG[i + 1].pos, t);
    const look = RIG[i].look.clone().lerp(RIG[i + 1].look, t);
    m.current.x += (pointer.tx - m.current.x) * Math.min(1, dt * 3);
    m.current.y += (pointer.ty - m.current.y) * Math.min(1, dt * 3);
    const par = 1 - smooth(Math.min(1, Math.max(0, (ph - 4.6) / 1.6)));   // quiet through silence + reveal
    pos.add(new THREE.Vector3(m.current.x * 90 * par, -m.current.y * 60 * par, 0));
    // v9 — a ledger row can fly the camera to its limb
    if (st.camFocus && performance.now() < st.camFocusUntil) {
      const f = new THREE.Vector3(st.camFocus[0], st.camFocus[1], st.camFocus[2]);
      camera.position.lerp(f.clone().add(new THREE.Vector3(0, 140, 580)), Math.min(1, dt * 2.2));
      camera.lookAt(f); return;
    }
    camera.position.lerp(pos, Math.min(1, dt * 2.2));
    camera.lookAt(look);
  });
  return null;
}
