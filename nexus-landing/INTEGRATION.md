# NEXUS · The Tree of Futures — Landing Integration

> **Note (product coherence):** the standalone cinematic prototype pages (`nexus-genesis.html`, `nexus-tree.html`, `nexus-awakening.html`) were retired to keep one coherent product story — the enterprise Decision Twin. The design notes below are kept as historical context for the landing concept; the shipped surfaces are `standalone/index.html`, `decision-graph.html`, `arena.html`, and `verify.html`.

The signature landing sequence. **Nothing here touches the backend, APIs,
database, business logic, routes, or existing platform functionality.** Every
data call is read-only (`GET /v1/status`, `GET /v1/graph`) and degrades to a
live-feeling demo if the API is unreachable.

---

## What this is

A single GPU-morphed world that the viewer scrolls *through*, not past. The same
particle set is choreographed across one continuous arc — no scene swaps, no tab
switches. Phase is one uniform, `uPhase ∈ [0,7]`, scrubbed by scroll.

**v8 "Mirror": the seed is the visitor's own decision.** Before the experience, one
question — *"What are you trying to decide?"* — captures a sentence that is hashed
(FNV-1a) into the world seed. The same decision always grows the same tree and the
same survivor, so a different outcome requires a different decision (the revisit
loop). The surviving branch then resolves into a real Nexus decision read-out (the
Bridge), names the runner-up the visitor almost chose (the Counterfactual), and opens
onto a live fork of their decision (the Doorway). See `CHANGELOG_v8_mirror.md`.

```
SEED          a single uncertain point in the void                       (a forecast begins)
SAMPLING      forecasts stream in from everywhere, tinted by source       (sampling)
ROOT FORMATION roots descend into everything that already happened        (evidence)
GROWTH        one forecast surges up the trunk                            (conviction)
ALTERNATE FUTURES the crown splits into every future it could become      (possibility)
PREDICTION BRANCHES branches split, mutate, compete; the graph fires      (reality graph / intelligence)
FOREST        futures unfurl into a living canopy of predictions          (the forecast forest)
SCALE SHOCK   camera pulls back onto ~21k competing futures, counter live (scale)
UNCERTAINTY   non-survivor branches waver between possible positions       (nothing is real yet)
RESOLUTION    reality arrives; most futures redden and fall to litter      (resolution)
REVERSE COLLAPSE the dead stream inward as the forest implodes            (collapse)
NEXUS REVEAL  the convergence resolves into the wordmark — it was inside  (the future that survived)
```
These beats are scrubbed by scroll and normalised by the engine into its single
`uPhase` uniform (range defined in `phaseStore.ts`), one draw call for
the morph cloud. Every visual maps to a forecasting concept; uncertainty, competing
futures, and resolution are all *shown*, not described.

The emotional takeaway, never stated as a slogan, only *experienced*:
**most futures die; reality is the future that survived.**

---

## Option A — Zero-build immersive experience (flagship, judge-ready)
`standalone/nexus-genesis.html` is the signature landing — a single continuous,
cut-free WebGL world the viewer scrolls *through*. It is fully self-contained
(Three.js + postprocessing via CDN import-map; Fraunces / IBM Plex Mono / Space
Grotesk via Google Fonts). Open it, host it, or drop it at any static path.
`standalone/index.html` redirects to it, so hosting the folder root just works.

Point it at the live backend (optional, read-only):
```
nexus-genesis.html?api=https://your-nexus-host
```
Without `?api` it runs the autonomous demo. 60 FPS target, mobile-tiered particle
budgets, reduced-motion aware, single-draw-call GPU morph.

The prior build `standalone/nexus-awakening.html` is retained as a lighter
fallback; `nexus-genesis.html` supersedes it as the canonical experience.

---

## Option B — In-app R3F module (matches the Nexus stack)
React 18 + React Three Fiber + Three + Zustand. Copy `src/landing/` into the
Nexus frontend `src/`.

**1. Dependencies** (all already in the Nexus stack except postprocessing):
```bash
npm i @react-three/postprocessing
# present already: three @react-three/fiber zustand
```
Fonts load from Google Fonts via `landing.css` `@import` (Fraunces for the act
lines + reveal; IBM Plex Mono for the HUD; Space Grotesk for body). To self-host,
swap the `@import` for local `@font-face` — no other change.

**2. Mount at the index route — the ONLY change to existing files.**
```tsx
import { Landing } from './landing';

// add a route; existing routes/platform untouched
<Route path="/" element={<Landing onEnter={() => navigate('/app')} />} />
```
`onEnter` hands off to your existing platform entry — wire it to whatever route
the "Enter Nexus" CTA should open. If `/` is already taken, mount at `/intro`
and link your current hero's CTA to it.

**3. Live data base URL** (optional): set `VITE_NEXUS_API` in `.env`. Defaults to
same-origin, so behind the existing Vite proxy it just works.

### Files added (all new — no edits to your components)
```
src/landing/
  Landing.tsx           composition root: mounts <Question/> first; the world boots
                        only once a decision is planted; one Canvas + 1080vh scroll track
  Question.tsx          THE QUESTION — the decision gate; hashes the text into the seed
  RealityAwakening.tsx  the tree generator + GPU morph shader (roots/wood/leaves/
                        fallen-litter/memory-mark), neural canopy edges, starfield;
                        seeded by the decision, survivor + runner-up locked from behaviour
  CameraDirector.tsx    8-pose phase-driven camera rig + calmed parallax
  Hud.tsx               instrument overlay (real /v1/status)
  Acts.tsx              7 act captions + read-back + the Bridge card + Counterfactual
                        + the Doorway fork + the Reality Card share
  Silence.tsx           the Silence + count + Counterfactual beat (audio-scored)
  audio.ts              guarded WebAudio bed (drone/sub/tick/survive/ghost) — no assets
  phaseStore.ts         Zustand phase state + decision/seed/survivor/runnerUp/card
  behavior.ts           invisible capture + decision read-back + composeCard (the Bridge)
  useNexusData.ts       /v1/status + /v1/graph poller w/ demo fallback
  landing.css           scoped to .nx-* (cannot collide)
  index.ts              barrel export
```

`<Question/>` renders first and gates everything; `onEnter` still hands off to your
platform entry from the "Enter Nexus" CTA. The CTA also opens the in-place **fork**
(add a constraint → the decision card re-decides) so the product grammar continues
past the reveal.

## How the morph works
The tree is generated once on the CPU (seedable L-system: a 4-step trunk, a crown
that splits into seven future limbs — one of them the survivor — recursive
sub-branching to depth 5, a mirrored root system, leaf clusters at the limb
tips). Each particle carries its **seed**, **grown-tree**, **fallen-litter**, and
**memory-mark** positions as static attributes. The vertex shader blends between
them from the single `uPhase` uniform, so the CPU never rewrites the position
buffer — the entire 7-act journey is one draw call.

## Performance notes
- One draw call for ~7.2k particles (3k on mobile / coarse pointer / ≤4GB) plus a
  1.5k-point starfield (0.7k low-power).
- GPU morph: positions blend in the vertex shader from one uniform `uPhase`; the
  CPU never rewrites the position buffer.
- Neural canopy edges light only during the intelligence act; bloom auto-disabled
  on low-power devices.
- `depthWrite:false` + additive blending = no sort cost.
- Phase lives in Zustand, read in `useFrame` — zero React re-renders per frame.

## Accessibility
- `prefers-reduced-motion`: skips the cold-open, holds a gentle composed tree.
- CTA is a real focusable `<button>` with visible focus ring.
- HUD is `aria-hidden` ambient; the CTA carries the actionable label.

## Guarantee
Both ship paths render the identical sequence (same generator, same shaders, same
8-pose rig, same act copy). The only backend contact is two read-only GETs with a
demo fallback. No write, no mutation, no change to any existing component.
