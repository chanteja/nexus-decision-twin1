# NEXUS · Landing — v9 "The Negotiation" (design brief)

> Reviewed as: FAANG CTO · AWS Grand-Prize judge · Active Theory creative director · multi-time founder.
> Scope: landing / interaction / narrative / emotional / perceived-intelligence layers **only**.
> Hard constraint honoured: **zero** backend, API, schema, business-logic, pipeline or geometry-rebuild changes.
> Central leverage: the morph engine is already re-entrant. v8 fires the collapse once and locks it
> (`survivorChosen=true`). v9 unlocks it. That single change converts a *viewer* into an *engine*.

---

## The one-line reframing

v8 says: *"Tell me your decision, I'll show you the future that survives."* (Prediction. One-way. Ends.)
v9 says: *"Bring me your decision. Now argue with reality and watch it rearrange."* (Negotiation. Recursive. Never ends.)

Everything below serves that shift, and every piece reuses code you already shipped.

---

## 1. Top 10 highest-ROI changes (ranked by impact / effort)

| # | Change | Why it moves the score | Reuses | Effort |
|---|--------|------------------------|--------|--------|
| 1 | **Un-lock the collapse → THE RE-COLLAPSE.** After the reveal, a constraint doesn't just repaint the card — it re-runs `decideSurvivor()` and replays the morph 6→4.2→6 into a *possibly different* survivor. The forest you were told was "reality" physically un-dies and re-dies. | This is the holy-shit moment. Viewer→Engine, Spectator→Negotiator, Linear→Recursive, all at once. | `decideSurvivor`, `aSurv`/`aFallen` morph, `uPhase`, `uAttack` | **Low** — remove a guard, route `fork()` through it |
| 2 | **The Probability Ledger.** Surface `attention[]` (already computed) as 7 live labelled rows with %. The decorative forest becomes a readable model: `the bold branch 31% · the patient branch 22% …`. Each row is clickable → camera flies to that limb. | Decorative→Functional. Judges stop asking "do these branches mean anything?" | `attention[]`, `branchAnchors[]`, `camAt()` | Low |
| 3 | **The Sacrifice beat.** When a re-collapse picks a *different* survivor, the old survivor is named and visibly killed: *"you just let go of the future you were about to keep."* | Selection→Consequence. Creates grief = meaning = memory. | runner-up/`chosenSurvivor` swap, `audioGhost` | Low |
| 4 | **The Lineage rail (living system).** Every collapse this session stacks into a left-edge vertical rail of tiny seed-dots: *reality #04412 → #20911 → #71044*. Click any to restore that card. | Session→Living organism. "I am building a decision history," not watching a movie. | in-memory array of `{seed, card}`; optional `localStorage` in your real deploy | Low |
| 5 | **Identity read, by construction (not horoscope).** After ≥3 forks, synthesise from *which survivors they accepted vs killed*: *"across 4 versions you kept the branch that survives being wrong 3 times. You optimise for not-dying, not for winning."* | Simulation→Identity mirror. The system describes **them**, true by construction (same trick that fixed v8's seed). | the lineage array, `WHY[]` tags | Low |
| 6 | **Deep-link reality (`?d=`).** The Reality Card and "Enter Nexus" emit a URL carrying the decision text; opening it reproduces the **exact** tree (seed is `hashText(decision)`). | Viral loop with a payoff: "type my decision and you get *my* reality." Built-in distribution. | `hashText`, existing `?api=` query parsing | Low |
| 7 | **Reality Card → diptych.** The shareable PNG shows two columns: *the future you kept* vs *the one you killed* (survivor + counterfactual), with both confidences and the reality #seed. | Loss-framed cards get screenshotted far more than success cards. | existing `buildShareCard()` canvas | Low |
| 8 | **Constraint chips, not just a text box.** Under the fork input, 4 pre-baked one-tap constraints (`half the runway` · `a year, not a quarter` · `a competitor moves first` · `you're wrong about the market`). Each is a guaranteed re-collapse in one tap — no typing, no empty-field dead end. | Removes the #1 failure mode: a judge stares at a blank box and leaves. Guarantees the recursive moment fires. | `fork()`, `composeCard` | Low |
| 9 | **The HUD becomes a witness.** On each collapse, bump the live `ledger · N decisions recorded` counter and flash `chain ✓` — wire the *page* event into the *already-polling* presence layer so the OS visibly reacts to the visitor. | Connects the poetry to the "operating system" claim without touching the backend. | `paintHud`, demo counters | Low |
| 10 | **Cold-open line swap → worldview, not feature.** Opening/closing copy reframes from "a decision creates futures" to "every choice you make kills the others — Nexus is where you watch which one you can live with." | Product→Mental model. The sentence the judges repeat to each other. | copy only | Trivial |

**Do NOT do:** more particles, more bloom, a tutorial, a second 3D scene, parallax tricks, a loading bar with fake telemetry. All cosmetic. None close a structural gap.

---

## 2. Exact redesigned user journey (0s → final second)

Times are wall-clock from page load; the spine (phases 0–7, 8-pose rig, shaders) is untouched.

- **0.0s — Cold open.** Black. HUD already alive (`uptime 4h 12m…`, `23 engines online`, `ledger 128`). The world was running before you arrived. New eyebrow under the question: *"nexus is listening · 19,442 realities collapsed today"* (in-memory counter, ticks).
- **0.7s — THE QUESTION.** *"What are you trying to decide?"* Input autofocuses. Skip → "watch without deciding." (unchanged, it works.)
- **~2s — boot(decision).** Seed planted. Camera at the seed; particles breathing.
- **2–18s — THE ASCENT (scroll, phases 1→4.5).** Roots → emergence → forest → intelligence. The 7 acts narrate *their* decision. **New:** as phase crosses 2.4, the Probability Ledger fades in top-right — 7 branches, live %, re-sorting as their cursor leans toward limbs. The forest is now legibly a model, not décor.
- **~18s — THE BRINK (phase 4.5).** `decide()` locks survivor + runner-up from attention (or seed if still). Scripted finale takes over.
- **18–20.5s — THE SILENCE.** True black, drone swells. *"simulating every version of your decision."*
- **20.5–25s — THE COUNT.** `0 → 12,742 → 1`. Sub-bass. *"survived."* Three-note resolution.
- **25–27.5s — THE COUNTERFACTUAL.** *"one future was a hesitation away — it was the bolder one."* Descending ghost tone. (v8, kept — strongest beat you have.)
- **27.5–29s — THE BRIDGE.** Black lifts, camera dives into the surviving limb (pose 6), wordmark composes from it, the decision card resolves: `decision / survives at 0.78 / because … / watch …`. Read-back quotes their words.
- **29s — THE INVITATION (new, the pivot).** Sub-line changes from a full stop to a provocation: *"this is the future that survives if nothing changes. something always changes — argue with it."* The 4 constraint chips + fork box are now the visual centre, not a footer afterthought.
- **+T (visitor's choice) — THE RE-COLLAPSE [the holy-shit moment].** They tap `half the runway`. World snaps to ~phase 4.2: the survivor's particles **release**, dead futures lift back out of it, attention re-weights, `decideSurvivor()` re-runs — and a **different** limb ignites and pulls the field into itself. Camera re-dives. Card re-decides in place: confidence drops `0.78 → 0.61`, `because`/`watch` change. If the survivor changed, the **Sacrifice** beat fires: *"you just let go of the patient one."* The reality #seed updates; a dot drops onto the Lineage rail.
- **Loop — RECURSIVE AGENCY.** Each new constraint = a new collapse, a new dot, a shifting confidence, sometimes a death. After 3+, the **Identity read** surfaces. The experience now has no natural end — exactly the property AWS judges score as "startup."
- **Any time — THE DEPARTURE.** "take your reality card" → diptych PNG (kept vs killed) via Web Share, filename carries the seed; or "Enter Nexus" → deep-link `?d=…` to the real product surface. The page leaves with them.
- **Final second:** there is no final second. That is the point. The closing whisper reads *"every reality you can live with started as one you killed."*

---

## 3. The single most powerful reality-distortion moment

**THE RE-COLLAPSE.** One sentence: *the visitor changes one assumption and the universe they were just told was "reality" dissolves and re-forms into a different reality in front of them, and the card in their hands changes under their fingers.*

Why this and nothing else:
- It is the literal felt difference between *"I am watching an animation"* and *"I am operating a reality engine"* — the exact phrase the review says lives at 10/10.
- It is **impossible to fake with a screen recording** — it only happens because *they* moved. That unsettles. Admiration → disbelief.
- It costs almost nothing: the morph already exists, `decideSurvivor` already rewrites the attributes, `uPhase` already drives the shader. You are replaying a transition you already wrote, backwards then forwards, into a new argmax.

Implementation sketch (interaction layer only):
```
function recollapse(constraint){
  // 1. bias the existing attention model from the constraint (no new engine)
  const b = hashText(constraint);
  for(let i=0;i<T.BRANCHES;i++) attention[i] *= (0.6 + ((b>>(i*3))&7)/7);  // re-weight, deterministic
  // 2. un-lock and re-run the collapse you already have
  survivorChosen = false;
  const prevSurvivor = chosenSurvivor;
  decideSurvivor(camera);                 // rewrites aSurv/aFallen + needsUpdate, picks new argmax
  // 3. replay the morph: release → re-die into the new limb
  reCollapsing = true; seqTarget = 4.2;   // frame loop eases uPhase down…
  setTimeout(()=>{ seqTarget = 6.0; }, 900); // …then back into the (possibly new) survivor
  // 4. consequence + card + lineage
  if(chosenSurvivor !== prevSurvivor) fireSacrifice(prevSurvivor);
  CARD = composeCard(constraint); paintCard(CARD);
  pushLineage(SEED ^ b, CARD);
  audioGhost();
}
```
Everything called here already exists. The only genuinely new lines are the attention re-weight and the `seqTarget` down-then-up ease — both in the loop you already run.

---

## 4. The recursive-agency system, using only existing architecture

The forest is a **7-cell weighted model** you already maintain in `attention[]`. Recursion is just: *mutate the weights → re-argmax → replay the morph.* No backend.

- **Input surface:** the existing `fork()` box + 4 constraint chips. Each chip is a fixed string fed to `recollapse()`.
- **Mutation:** deterministic per-branch re-weight from `hashText(constraint)` (above). Same constraint on the same reality always yields the same new reality — preserves the deterministic contract and the deep-link reproducibility.
- **Re-selection:** `decideSurvivor()` verbatim — it already reads `attention`, rewrites `aSurv`/`aFallen`, flags `needsUpdate`.
- **Re-render:** the morph shader already interpolates on `uPhase`; easing it 6→4.2→6 in the frame loop physically re-collapses the field. Zero buffer rewrites beyond the ones `decideSurvivor` already does.
- **Card:** `composeCard(constraint)` already shifts confidence and rotates `WHY`/`WATCH`. Already done — just route it through the re-collapse instead of repainting in isolation.
- **Termination:** none. That's the feature.

This is the whole moat argument: a competitor can copy the tree shader in a weekend. Copying *a deterministic, re-entrant decision model that reorganises a continuous world under live constraints* is copying an operating system for decisions. Same code you have — just stop ending it.

---

## 5. The legendary ending sequence

There is no ending; there is a **last beat that reframes everything**, reachable whenever they choose to leave.

1. They stop forking. After ~6s idle on a resolved card, the Lineage rail animates: every reality-dot they collapsed this session draws a faint thread to the survivor limb — *their* path through possibility, in their own hand.
2. The world pulls back once (pose 7) and the threads converge. Copy: **"you collapsed 5 realities tonight. you kept this one."**
3. Beat. The forest dims to the single surviving limb, which holds the wordmark. The killed survivors flicker once at the edge — present, not gone (conservation).
4. Final line, slow: **"every reality you can live with started as one you killed."** Then the two CTAs and the whisper.

This adds the +0.4 the review attributes to a "you become the centre of the universe" ending — but earns it through *their own* fork history, not a scripted flourish. Emotional residue = the count of futures *they personally* killed.

---

## 6. Strongest identity-reflection mechanism

**The Decision Fingerprint — derived from forks, true by construction.** v8 correctly killed cursor-horoscope. v9's mirror reads only things the visitor literally did: which constraints they tried, and for each, whether they *kept* the new survivor (left the card) or *reverted* (clicked an earlier lineage dot).

After ≥3 collapses, synthesise one sentence from the survivors' `WHY` tags (you already tag each survivor with a `why` like *"survives the scenario where you are wrong"* / *"compounds instead of decays"*):
- mostly robustness `why`s kept → *"you optimise for not-dying, not for winning."*
- mostly optionality `why`s → *"you refuse to close doors — even when closing one is the decision."*
- many reverts → *"you keep returning to the first reality. you already knew. you wanted to be talked out of it."*

This is identity, not a horoscope, because it is computed from choices they can see themselves making. It is the screenshot line.

---

## 7. Strongest consequence / sacrifice mechanism

**Conservation already gives you the visual; v9 gives it the cost.** Today every branch dies but "nothing is lost" — no grief. Fix: a re-collapse that changes the survivor must *take* the one they had.

- The previous survivor's particles, currently bright gold, **desaturate to the dissent red** (`cDis`, already a uniform) for ~700ms as they're released — the audience watches the future they just accepted die.
- Named, specifically: *"you just let go of the patient one — it needed a year you didn't give it."* (reuse `counterfactualLabel`.)
- The Lineage dot for the killed reality renders hollow/crossed. It stays on the rail — you can go back, but going back is now a visible reversal the Fingerprint reads.
- Confidence is the running cost: each constraint that lowers it makes the number bleed downward on screen. Sacrifice becomes quantified, not cosmetic.

Opportunity cost is now felt: *to get the reality that survives the bad quarter, you killed the one that wins the good one.*

---

## 8. Strongest viral / shareable mechanism

Two surfaces, both built from code you have:

1. **The Loss Diptych card.** Rework `buildShareCard()` to two columns — **KEPT** (survivor: decision, conf, why) vs **KILLED** (counterfactual: label, its conf, the road not taken) — over the seed `reality #04412`. Loss-framed > success-framed for sharing; the killed column is the hook ("wait, what was the other one?").
2. **The reproducible reality deep-link.** Because `seed = hashText(decision)`, a URL `…/?d=<decision>` reproduces the *identical* tree and survivor for anyone. The card and CTAs emit it. The loop: someone shares "should I leave my job → reality #71044", a friend opens it and sees *the same collapse*, types their own, shares theirs. Distribution is structural, and the payoff ("how did it land on the same answer for both of us?") is the unsettling hook.

Optional amplifier (still no backend): a `?d=` page can pre-fill the question, so a shared link drops the recipient straight into a seeded boot.

---

## 9. Exact UI / UX modifications

- **Probability Ledger** (new, top-right, monospace): 7 rows `■ the bold branch ····· 31%`, bar-weighted by `attention[]`, re-sorting live, dimming as branches die at phase 4–5; rows clickable → `camAt` fly-to. Reuses HUD type tokens.
- **Constraint chips** (new, under fork box): 4 pill buttons, always one tap from a re-collapse. The free-text box stays for power users but is no longer the only path.
- **Lineage rail** (new, left edge): vertical stack of seed-dots, newest at bottom, killed ones hollow; click restores `{seed, card}`. ~24px wide, unobtrusive until populated.
- **Card** gains a confidence-delta tick (`0.78 ↓ 0.61`) and a state class `.re-decided` (re-uses your existing `.nx-card` fade).
- **Sacrifice flash:** survivor particles → `cDis` for 700ms (uniform-driven, no geometry change) + one-line caption reusing `.gensub.dis`.
- **HUD:** ledger counter increments on each collapse; `chain ✓` flashes. Wire page→`paintHud`.
- **Mobile:** Ledger collapses to a single "× futures" pill; chips wrap to 2×2; Lineage rail hides, lineage lives in the card's back. Re-collapse still fires (tap chips). Honour `prefers-reduced-motion`: skip the morph replay, snap the card + ledger instead.

No new scene, no new geometry, no new shader — only DOM overlays + uniform tweaks + the re-entrant call.

---

## 10. Exact copy replacements

| Location | v8 (now) | v9 (replace with) |
|----------|----------|-------------------|
| Question eyebrow | `nexus is listening` | `nexus is listening · 19,442 realities collapsed today` |
| Silence label | `simulating every version of your decision` | *(keep)* |
| Survivor sub (the pivot) | `The tree was never a tree. It was the one branch that kept all the others.` | `this is the future that survives if nothing changes. something always changes — argue with it.` |
| Fork prompt | `fork it — what changes the answer?` | `change one thing. watch reality re-decide.` |
| Constraint chips | — | `half the runway` · `a year, not a quarter` · `a competitor moves first` · `you're wrong about the market` |
| Sacrifice line (new) | — | `you just let go of {label} — it needed {the thing you didn't give it}.` |
| Identity line (new, ≥3 forks) | — | `across {n} versions you kept the branch that survives being wrong. you optimise for not-dying, not for winning.` |
| Ending headline (new) | — | `you collapsed {n} realities tonight. you kept this one.` |
| Closing whisper | `every reality begins as a decision` | `every reality you can live with started as one you killed.` |
| HUD top line | `nexus · reality-anchored os` | `nexus · the reality engine` |

---

## 11. What AWS Grand-Prize judges think after each major interaction

- **After the Question:** *"It made me commit before it showed me anything. That's a product asking me a question, not a demo playing at me."*
- **After the Ascent + Ledger:** *"Those branches have numbers. This isn't a tree animation — it's a model, and the model is reacting to where I look."*
- **After the Silence + Count:** *"Production-grade theatre. Most finalists can't hold a black screen for three seconds. This one earned it."*
- **After the Bridge card:** *"There's an engine surface here. `survives at 0.78 / because / watch` — that's an API response shape. This could be a real `/v1/decide`."* (It is — and you can flip `?api=` live in front of them.)
- **After THE RE-COLLAPSE [the moment]:** *"Wait — it rebuilt the entire world from one assumption I changed. I'm not watching a future, I'm negotiating with one. I have not seen this before."* ← this is the sentence that gets repeated in the judges' room.
- **After the Sacrifice:** *"It made me feel the cost. I actually didn't want to lose that branch. Nothing else today made me feel anything."*
- **After the Identity read:** *"It described how I decide, not what I decided. That's eerie. That's retention."*
- **After the Diptych + deep-link:** *"I want to send this to someone. And when I do, they get my exact reality. That's a growth loop, not a landing page."*
- **Standing up:** *"That wasn't a hackathon demo. That was a wedge for a decision-intelligence company. What's the moat?"* — and the moat answer is the re-entrant model, which they just operated.

---

## 12. Final score estimate — before vs after

| Axis | v8 (now) | v9 projected | What closed it |
|------|----------|-------------|----------------|
| Innovation | 9.5 | 9.7 | recursion + reproducible realities |
| Technical execution | 9.0 | 9.4 | re-entrant engine shown live, `?api=` flip |
| Storytelling | 9.5 | 9.6 | sacrifice + worldview framing |
| Emotional design | 9.3 | 9.7 | grief, identity mirror, your-own-lineage ending |
| **Real business potential** | **7.5** | **9.0** | viewer→engine, growth loop, "operate the moat" |
| Novelty / "never seen this" | 8.8 | 9.6 | THE RE-COLLAPSE |
| Memorability (3-yr recall) | 8.9 | 9.5 | you-killed-a-future residue |
| **Overall** | **8.9** | **~9.6** | structural, not cosmetic |

The remaining gap to a literal 10 is no longer in the landing page — it's whether the live `/v1/decide` behind `?api=` is as good as the myth. That's a backend question, out of this scope, and it's the *right* place for the last 0.4 to live.

---

## Build order (smallest set that buys the most score)

1. **Un-lock the collapse + route `fork()` through `recollapse()`** (#1, #3, #7-confidence). This alone is the holy-shit moment and lifts business-potential most.
2. **Constraint chips** (#8) — guarantees the moment fires for a non-moving judge.
3. **Probability Ledger** (#2) — turns the forest functional, cheap, high visible polish.
4. **Lineage rail + ending + Identity read** (#4, #5, the §5 ending).
5. **Diptych card + `?d=` deep-link** (#6, #7) — the loop that leaves the room.
6. Copy + HUD wiring (#9, #10) last; trivial, do in one pass.

Steps 1–2 are a few hours and capture most of the delta. Everything is additive; the v8 spine ships untouched.

---

## v9 — SHIPPED (what changed in code)

All additive; the v8 spine (one BufferGeometry, the GPU morph shader strings, the 8-pose rig,
the conservation law, the Silence + Counterfactual, the read-only `/v1/status`+`/v1/graph` presence
layer) is byte-for-byte intact. No backend, route, schema, or business logic touched.

**The core unlock:** selection is now re-entrant. The same routine that locks the first survivor
re-runs under a live constraint — it re-weights the existing `attention[]` model, re-picks argmax,
rewrites only `aSurv`/`aFallen` (the buffers v8 already rewrote once), flags `needsUpdate`, and replays
the morph `6 → 4.2 → 6` through the existing finale channel. The world physically re-collapses into a
(possibly different) survivor. Zero geometry rebuild.

- **standalone/nexus-awakening.html** — `recollapse()`, `biasAttention()`, the Probability Ledger
  (`renderLedger`/`focusBranch`), the Lineage rail (`renderLineage`/`restoreReality`), the Sacrifice
  (`fireSacrifice`), the Identity mirror (`showIdentity`), the diptych Reality Card (kept vs killed)
  + reproducible `?d=` deep-link, constraint chips, HUD witness (`bumpLedgerWitness`), the idle Ending
  (`armEnding`), a decision-shaped `attention` prior, and the camera fly-to. Copy swaps throughout.
- **src/landing/behavior.ts** — `+makeBranchLabels`, `+biasAttention`, `+whyCategory`, `+BRANCH_LABELS`,
  `+CF_LABELS`.
- **src/landing/phaseStore.ts** — `+collapseCount/ledgerRows/lineage/identity/sacrifice/reCollapsing/`
  `branchLabels/camFocus`, and engine handles `+recollapse/focusBranch/restore`.
- **src/landing/RealityAwakening.tsx** — selection factored into a reusable `applySelection`; registers
  `decide` + `recollapse` + `focusBranch` + `restore`; decision-shaped attention prior; live Ledger
  snapshots in `useFrame`; lineage + identity wiring.
- **src/landing/CameraDirector.tsx** — honours `camFocus` (ledger row → fly to limb).
- **src/landing/Acts.tsx** — Ledger, Lineage rail, constraint chips, Sacrifice, Identity, confidence
  delta tick, diptych share + `?d=` link, the Ending. Pivot/whisper copy.
- **src/landing/Question.tsx** — `?d=` prefill + self-plant (a shared reality reproduces exactly).
- **src/landing/landing.css** — `+.nx-ledger`, `.nx-lineage`, `.nx-chips/.chip`, `.nx-sacrifice`,
  `.nx-identity`, confidence-delta.

Reduced-motion: the re-collapse snaps (card + ledger update, no morph replay). Mobile: Ledger becomes a
compact bottom pill row, Lineage rail hides, chips wrap; the re-collapse still fires on tap.
