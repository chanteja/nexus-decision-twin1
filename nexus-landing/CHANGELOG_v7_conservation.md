# Nexus Landing — v7 "Conservation" patch

Evolves the Tree of Futures from a beautiful passive scrubber into a personalized
reality-selection machine. Four P0 changes, all riding the existing single-buffer
GPU-morph architecture. No backend / API / infra touched.

## P0-1 · Agency — the survivor is the branch you cared about
The survivor is no longer `rng()`. Attention accrues invisibly to the limb nearest
the cursor during the growth/forest phases; at selection the survivor is
`argmax(attention)`. Behave differently, a different branch lives. No game, no buttons.
- standalone: `attention[]`, `decideSurvivor()`
- r3f: `RealityAwakening.tsx` (attention in `useFrame`, `decide()` registered into the store)

## P0-2 · Conservation of Possibility — the killer mechanic
At selection the dead futures don't scatter — they **stream into the survivor**, which
brightens by exactly what they lose. Nothing is destroyed; possibility-mass transfers.
- data: non-survivor `aFallen` retargeted to a point along the surviving limb
- shader: `col += cSurv * vSurv * collapse` (survivor inherits the light of the many)

## P0-3 · The Silence + the count
A true black hold (~2.5s that feels like 8), then a monospace counter **derived from this
visit** (seed + canopy size — never a hard-coded 12,742) that ticks down to `1 survived`.
- standalone: `#silence` overlay + `startSequence()` timeline
- r3f: `Silence.tsx` (driven by the phase store)

## P0-4 · The read-back — proof it watched
The reveal shows ONE true, specific, per-visitor sentence (the witness / the returner /
the explorer …) composed from real measured behaviour — never a generic label, never an
"analyzing…" spinner. Then the neural edges return as the graph ("the tree was never a
tree") and the wordmark composes from the surviving branch.
- standalone: `finalizeReadback()` + `#reveal .read`
- r3f: `behavior.ts → composeReadback()`, surfaced in `Acts.tsx`

## Run it
- **Standalone (no build):** open `standalone/nexus-awakening.html`. Optional live HUD: append `?api=https://your-host`.
- **R3F:** drop `src/landing/*` into the app; render `<Landing onEnter={...} />`. New files: `Silence.tsx`, `behavior.ts`; extended `phaseStore.ts`.

## Files changed
standalone/nexus-awakening.html · src/landing/{RealityAwakening,CameraDirector,Acts,Landing}.tsx ·
src/landing/{phaseStore,index}.ts · src/landing/landing.css
## Files added
src/landing/Silence.tsx · src/landing/behavior.ts · CHANGELOG_v7_conservation.md
