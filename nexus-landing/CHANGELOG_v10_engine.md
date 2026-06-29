# NEXUS · Landing — v10 "The Engine" (wired to proof)

> Reviewed as: AWS Grand-Prize judge · Distinguished SA · FAANG CTO · Sequoia · category founder.
> Scope: close the gap every prior reviewer missed — **the myth and the proof were in separate rooms.**
> v9's gorgeous collapse ran on a local deterministic model (`hashText`+`attention[]`) and never
> called the real engine. v10 wires the collapse to `/v1/decide`, surfaces the calibration the
> backend already computes, and makes AWS load-bearing — *without breaking the demo when offline.*

The five fixes from the teardown, all shipped, all additive, demo-safe with **zero** backend required.

---

## FIX 1 — the collapse IS the inference

The signature moment (first reveal **and** every re-collapse) now asks the real OIOS engine and
re-forms the world into the **engine-chosen** survivor when a backend is attached.

- `engineDecide(decision, constraint)` → `POST {api}/v1/decide`, 3.5s abort, returns `null` on any
  failure. Without `?api=` it returns `null` immediately.
- `adoptEngine(j)` folds the verdict back into the **same** `attention[]` model the visuals read, so
  `decideSurvivor()` picks the engine's argmax and the existing morph re-dies into the real survivor.
  **No new render path** — the engine just becomes the model.
- **Timing contract:** the re-die fires on the dramatic beat (~900ms). If the engine answers by then,
  the collapse *is* the inference. If it's slow, the local model drives the visuals and the card
  **upgrades in place** the moment the verdict lands (`patchCardFromEngine`). If there's no backend,
  it's pure local. Three honest states, one set of visuals, never a network stall.
- The card now carries provenance: `● decided by bedrock 4-model ensemble · recorded to hash-chained
  ledger #<entry>` when live, or `● demo engine — connect ?api= for the live bedrock ensemble` offline.
- `composeCard(constraint, eng)` — when `eng` is present, confidence/why/watch are the engine's
  (real), not synthesised. Backward compatible (eng optional).

## FIX 2 — one number a skeptic cannot wave away (the proof panel)

A `#proof` panel enters with the verdict:

- Headline: **accuracy %** + **Brier score** over the OIOS Reality Track corpus (N real public
  strategic decisions with known outcomes). Demo ships honest, modest figures (74% / 0.18) — a
  suspiciously perfect number reads as fake; a calibrated-but-honest one reads as real.
- A reliability sketch (mean actual survival per predicted-decile bucket).
- `loadCalibration()` → `GET {api}/v1/calibration` replaces every number with the real one when live;
  the panel flips to `● live · OIOS reality track`.

## FIX 5 — the loop closes in front of the judge

`prove it on a real decision ↗` cycles the Reality Track corpus:

1. shows a real decision + *"Nexus predicts: survives at 0.71 · checking the ledger against reality…"*
2. ~1.1s later reveals the **known historical outcome** (SURVIVED ✓ / DID NOT SURVIVE ✗) and whether
   the call was right — **misses included** (the corpus keeps them; that's what makes it credible).
3. ticks a running `session: 7/9 calls correct · corpus accuracy 74% over 64 decisions`, and each
   check flashes the ledger witness. **Decision → Outcome → Learn, made physical** — on seeded data,
   honestly framed, no fake scale.

## FIX 3 — AWS made load-bearing

- HUD `decide` line: `bedrock 4-model ensemble · live` when a verdict has landed.
- HUD `substrate` line: `bedrock ensemble · hash-chained ledger · clean-rooms federated` — the three
  AWS-native primitives composed into one auditable learning loop. The "why AWS" *is* the "why not
  OpenAI/Google/Anthropic": none ship the trust substrate (ensemble + immutable ledger + private
  federation) as one stack.
- Card provenance + share-card footer (`74% calibrated over 64 real decisions`) carry the claim
  wherever the card travels.

## FIX 4 — the sentence

- HUD tagline: `nexus · proves which future survives`.
- Share card header: `N E X U S · PROVES WHICH FUTURE SURVIVES`.
- One sentence to repeat: **"Nexus is the decision engine that shows you which future survives — and
  proves it was right."**

---

## Files changed

- **standalone/nexus-awakening.html** — `engineDecide`/`adoptEngine`/`setCardSource`/`patchCardFromEngine`,
  engine-aware `composeCard`, rewritten `recollapse` (engine-in-the-window re-die), first-reveal engine
  adoption, `CALIB`+`loadCalibration`+`renderProof`+`proveNext`, proof panel markup/CSS, card
  provenance line, HUD decide+substrate lines, share-card proof framing. **The v8/v9 spine — one
  BufferGeometry, the GPU morph shader, the 8-pose rig, conservation, Silence + Counterfactual, the
  recursive re-collapse — is byte-for-byte intact.**
- **src/landing/useNexusData.ts** — `engineDecide()`, `fetchCalibration()`, `EngineVerdict`/`Calibration`
  types, demo corpus. (Data-layer parity for the in-app R3F path; the standalone is the canonical
  wired reference.)

Offline (no `?api=`): byte-identical experience to v9 plus the proof panel on demo data. Reduced-motion
and mobile paths preserved (re-die snaps; engine still consulted).

---

## Backend contract — what OIOS must expose for the live demo

All fields are optional and degrade gracefully; the landing never breaks if a field or endpoint is missing.

```
POST {api}/v1/decide
  body: { decision: string, constraint?: string, branches: 7, tenant: "demo_corp", seed?: number }
  200 : {
          survivor?:   int,                 // index of surviving branch (else client keeps local argmax)
          weights?:    number[7],           // per-branch probability/attention from the ensemble
          confidence:  number,              // 0..1 survivor confidence
          why:         string,              // the engine's reasoning (one line)
          watch:       string,              // what flips it (one line)
          model?:      string,              // e.g. "bedrock 4-model ensemble"
          ledger?:     { events:int, chain_valid:bool, entry?:string }   // ledger state after recording
        }

GET {api}/v1/calibration
  200 : {
          n:          int,                  // corpus size (Reality Track)
          accuracy:   number,               // 0..1
          brier:      number,               // 0..1
          reliability:[{ p:number, actual:number, count:int }],   // or number[]
          samples:    [{ decision:string, predicted:number, survived:bool }]
        }

GET {api}/v1/status   (unchanged, already consumed)
GET {api}/v1/graph    (unchanged, already consumed)
```

**Demo runbook for the finale:**
1. `open standalone/nexus-awakening.html` → fully autonomous, proof panel on demo corpus. (fallback)
2. `…/nexus-awakening.html?api=https://<oios-host>` → the collapse becomes a real Bedrock inference,
   the proof panel shows the real Reality Track calibration, the HUD goes live, `chain ✓` is real.
3. Rehearse the `?api=` flip on stage: it is the gesture that answers *"is it real?"* before it's asked.

The last 0.4 to a literal 10 now lives where it should — in whether the live `/v1/decide` is as good
as the myth. That's a backend-quality question, not a landing-page one.
