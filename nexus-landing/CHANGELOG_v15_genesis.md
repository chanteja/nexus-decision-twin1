# v15 "Genesis" — the landing becomes a world

The landing page is no longer a page. It is one continuous, cut-free WebGL
journey the viewer scrolls *through*, where every visual element is a forecasting
concept and the product's mechanics are the visual language.

## New
- `standalone/nexus-genesis.html` — the flagship immersive experience. Self-contained
  (Three.js 0.160 + EffectComposer/UnrealBloom via CDN import-map, Google Fonts).
- `standalone/index.html` — redirects the folder root to the flagship.

## Modified
- `INTEGRATION.md` — Option A now points at `nexus-genesis.html`; experience-flow
  block rewritten to the twelve-beat narrative.

## Retained
- `standalone/nexus-awakening.html` — kept as a lighter fallback; superseded.

## The twelve-beat flow (one `uPhase ∈ [0,11]`, scroll-scrubbed, one morph draw call)
1. SEED — a single uncertain point in the void.
2. SAMPLING — thousands of forecasts stream in from a far shell, tinted by source
   (each colour = a model / human pool), absorbed into the seed.
3. ROOT FORMATION — roots descend into "everything that already happened" (evidence).
4. GROWTH — one forecast surges up the trunk (conviction).
5. ALTERNATE FUTURES — the crown splits into every future it could become (violet).
6. PREDICTION BRANCHES — recursive branching; the reality-graph edges fire.
7. FOREST — futures unfurl into a living canopy of individual predictions.
8. SCALE SHOCK — the camera pulls back onto a ~21,000-node field; a live counter
   ramps so the scale is *felt*, not stated.
9. UNCERTAINTY — non-survivor branches visibly waver between possible positions.
10. RESOLUTION — reality arrives; most futures redden and fall to the litter.
11. REVERSE COLLAPSE — the field implodes inward; the dead stream toward what remains.
12. NEXUS REVEAL — the convergence resolves into the NEXUS wordmark. The mark was
    inside the tree all along; then one true sealed decision read-out + Enter CTA.

## Systems
- **Core morph cloud** (~6k desktop / ~4k mobile): one `BufferGeometry`, per-particle
  `aSeed / aOrigin / aTree / aFall / aLogo` positions + `aGrow / aKind / aSurv / aFuture
  / aSrc / aRand`; the vertex shader blends all twelve beats from one uniform, so the
  CPU never rewrites the position buffer.
- **Forest** (21k / 6k points): the scale-shock field; rises at beat 8, reddens and
  implodes through collapse.
- **Reality-graph edges**: additive `LineSegments` that pulse during the branching /
  intelligence beats and fade through collapse.
- **Starfield**: the seed was one point in a universe.
- **Camera choreography**: 12 eased poses — dive to the seed, fall through the roots,
  rise the trunk, fly the branches, pull back to the impossible forest, settle on the mark.
- **Postprocessing**: UnrealBloom, auto-disabled on low-power devices.

## Forecasting semantics made visible (the three gaps that mattered)
- *Prediction mechanics are the visuals*: seed = a new forecast, roots = evidence,
  branch = a possible future, leaf = an individual prediction, gold = the survivor,
  red fall = a future that died.
- *Uncertainty is shown*: branches waver/mutate before resolution; the forest field
  flickers; nothing is real until reality arrives.
- *A unique signature*: the reverse collapse into the wordmark — the logo is discovered
  inside the structure, not displayed on top of it.

## Guarantee (unchanged)
Backend contact is read-only and optional (`GET /v1/status`, `POST /v1/decide`) with a
full demo fallback. No write, no mutation, no change to any platform component.
