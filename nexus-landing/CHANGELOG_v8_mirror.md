# NEXUS · Landing — v8 "Mirror"

v7 "Conservation" was beautiful but it measured the *mouse*, not the *person*. The
read-back ("you moved with intent") was computed from cursor noise — a Forer/horoscope
trick that inverts the moment a judge scrolls without moving. And the reveal was a
terminus: a gorgeous wordmark and a CTA, with no bridge from the poetry to the product.

v8 makes the seed the visitor's **own decision**, then proves the metaphor is a real
engine surface. Same world, same shaders, same 8-pose rig, same conservation law — the
spine is untouched. Seven changes, all additive.

## The seven changes

1. **THE QUESTION (the seed is yours).** Before the experience: *"What are you trying to
   decide?"* The text is hashed (FNV-1a) into the world seed — so the same decision always
   grows the same tree and the same survivor. Skipping is allowed ("watch without
   deciding") and falls back to a random seed. Nothing is "analysed"; the words are simply
   quoted back. This kills the horoscope problem at the root: the read-back is now true by
   construction because it is built from what the visitor literally typed.

2. **Decision-steered survivor (every visitor steers, not just cursor-movers).** Attention
   still accrues to the limb nearest the cursor during the forest act. But if the visitor
   never moves — the common judge case — the survivor is chosen **deterministically from
   the decision** (`seed % BRANCHES`), never from screen-centre randomness. A different
   decision is a different reality, for everyone.

3. **THE BRIDGE (the survivor resolves into a real decision card).** The surviving limb
   no longer just spells NEXUS. It resolves into a real Nexus read-out — `decision /
   survives at <confidence> / because <reason> / watch <counterfactual condition>` —
   deterministically synthesised from the decision + seed, and shaped so a live
   `/v1/decide` response could drop into the identical structure with no other change.
   This is the hand-off from myth to product.

4. **THE COUNTERFACTUAL (the self you almost became).** We keep the **runner-up** branch
   (second-highest attention, or a deterministic second pick). In the black after "1
   survived", a beat names it — *"one future was a hesitation away… it was the bolder
   one"* — before the mark composes. The reality-break is no longer the expected twist;
   it is a named, specific road not taken.

5. **AUDIO (the Silence finally lands).** A guarded WebAudio bed: a low drone swells under
   the 2.5s black so it feels like 8; sub-bass under the count; a soft tick per counter
   slot; a three-note major resolution on "survived"; a descending triangle for the
   counterfactual ghost. Created on first gesture (autoplay-safe). Zero assets.

6. **THE REALITY CARD + THE DOORWAY (revisit + word-of-mouth).** "Enter Nexus" opens a
   live **fork**: add a constraint ("only 8 months of runway") and the card re-decides in
   place, confidence shifting — the product grammar continues past the reveal. A second
   affordance renders a shareable **Reality Card** PNG (decision, confidence, reason,
   reality #seed) via the Web Share API with a download fallback. The experience now has a
   loop and a surface that leaves the page.

7. **Bug fixes.** The wordmark now samples only **after `document.fonts.ready`** (the v7
   race that could compose the mark from a fallback face is gone — standalone awaits before
   the first sample; the R3F module re-samples on the `fonts.ready` promise). The capped
   scroll-to-finale hand-off is announced via the scripted phase as before, with the parallax
   quieted through the Silence so the camera no longer yanks.

## What did NOT change (the spine)
- One persistent `BufferGeometry`, one GPU-morph shader, `uPhase ∈ [0,7]`, zero per-frame
  CPU buffer writes. Shaders are byte-for-byte the v7 strings.
- 8-pose `CameraDirector`, the conservation law (`col += cSurv*vSurv*collapse*1.05`, dead
  futures streaming **into** the survivor), the act arc, the live `/v1/status` + `/v1/graph`
  presence layer with demo fallback.
- Demo-mode is still zero-AWS-dependency and read-only. No backend, route, schema, or
  business logic is touched. `?api=` still points the showpiece at a live host.

## Files
- **standalone/nexus-awakening.html** — rewritten around an async `boot(decision)` flow
  (renderer/materials init immediately; geometry + scene assemble after the decision is
  planted). +Question overlay, +Bridge card, +Counterfactual beat, +Doorway fork, +Reality
  Card, +audio bed, +font-race fix.
- **src/landing/Question.tsx** *(new)* — the decision gate.
- **src/landing/audio.ts** *(new)* — the WebAudio bed.
- **src/landing/phaseStore.ts** — +decision, +seed, +started, +survivor, +runnerUp, +card,
  +begin().
- **src/landing/behavior.ts** — +seedFromText, +composeCard (the Bridge), +counterfactualLabel,
  read-back now quotes the decision, +dwell capture.
- **src/landing/RealityAwakening.tsx** — seeded by the decision, runner-up captured,
  card composed at selection, font-race re-sample.
- **src/landing/Silence.tsx** — +audio cues, +Counterfactual beat before the reveal.
- **src/landing/Acts.tsx** — +Bridge card, +Counterfactual sub, +Doorway fork, +Reality Card.
- **src/landing/Landing.tsx** — mounts `<Question/>`; the world boots only once a decision
  is planted; audio armed on begin.
- **src/landing/landing.css** — +`.nx-ask`, `.nx-card`, `.nx-door`, `.nx-actions`, `.nx-share`,
  counterfactual tint.
- **src/landing/index.ts** — exports `Question`.
