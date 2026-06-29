// src/landing/audio.ts
// A tiny, fully-guarded WebAudio bed that carries the Silence (the 2.5s black that
// must feel like 8). Created on first gesture per autoplay policy. No assets, no deps.
let actx: AudioContext | null = null;
let droneGain: GainNode | null = null;
let subGain: GainNode | null = null;

export function ensureAudio() {
  if (actx) return;
  try {
    const Ctx = (window.AudioContext || (window as any).webkitAudioContext);
    actx = new Ctx();
    const o = actx.createOscillator(); droneGain = actx.createGain();
    o.type = 'sine'; o.frequency.value = 57.27; droneGain.gain.value = 0;
    o.connect(droneGain).connect(actx.destination); o.start();
    const s = actx.createOscillator(); subGain = actx.createGain();
    s.type = 'sine'; s.frequency.value = 38; subGain.gain.value = 0;
    s.connect(subGain).connect(actx.destination); s.start();
  } catch { /* audio is optional */ }
}

export function audioSwell() {
  try {
    if (!actx || !droneGain) return; const t = actx.currentTime;
    droneGain.gain.cancelScheduledValues(t); droneGain.gain.setValueAtTime(droneGain.gain.value, t);
    droneGain.gain.linearRampToValueAtTime(0.06, t + 1.6);
    droneGain.gain.linearRampToValueAtTime(0.085, t + 4.2);
    droneGain.gain.linearRampToValueAtTime(0.0, t + 6.6);
    if (subGain) { subGain.gain.setValueAtTime(0, t); subGain.gain.linearRampToValueAtTime(0.05, t + 4.2); subGain.gain.linearRampToValueAtTime(0, t + 6.6); }
  } catch { /* noop */ }
}

export function audioTick() {
  try {
    if (!actx) return; const t = actx.currentTime; const o = actx.createOscillator(), g = actx.createGain();
    o.type = 'square'; o.frequency.value = 2200;
    g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(0.012, t + 0.005); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.05);
    o.connect(g).connect(actx.destination); o.start(); o.stop(t + 0.06);
  } catch { /* noop */ }
}

export function audioSurvive() {
  try {
    if (!actx) return; const t = actx.currentTime;
    [55, 82.4, 110].forEach((f, k) => {
      const o = actx!.createOscillator(), g = actx!.createGain();
      o.type = 'sine'; o.frequency.setValueAtTime(f * 2, t); o.frequency.exponentialRampToValueAtTime(f, t + 1.1);
      g.gain.setValueAtTime(0.0001, t + k * 0.04); g.gain.linearRampToValueAtTime(0.07, t + 0.06 + k * 0.04); g.gain.exponentialRampToValueAtTime(0.0001, t + 1.7);
      o.connect(g).connect(actx!.destination); o.start(); o.stop(t + 1.8);
    });
  } catch { /* noop */ }
}

export function audioGhost() {
  try {
    if (!actx) return; const t = actx.currentTime; const o = actx.createOscillator(), g = actx.createGain();
    o.type = 'triangle'; o.frequency.setValueAtTime(140, t); o.frequency.exponentialRampToValueAtTime(70, t + 0.9);
    g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(0.05, t + 0.05); g.gain.exponentialRampToValueAtTime(0.0001, t + 1.0);
    o.connect(g).connect(actx.destination); o.start(); o.stop(t + 1.1);
  } catch { /* noop */ }
}
