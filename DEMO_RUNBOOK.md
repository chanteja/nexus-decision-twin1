# NEXUS — Demo Runbook

The product in one line: **the decision twin enterprise strategy teams can actually
check.** The demo makes three judges feel it in three minutes: it remembers, it verifies,
and it re-scores the whole strategy the instant an assumption breaks.

---

## The 10-second value proposition
> Ask your strategy a question. Get an answer that **remembers, verifies, and improves.**

## The 30-second pitch
> Enterprise strategy teams make nine-figure bets on assumptions nobody writes down. When
> a bet fails, no one can say which belief broke or what else was standing on it. NEXUS
> builds a **Decision Twin**: it captures every decision and its assumptions, seals each
> one on the record before the outcome exists, and verifies it against reality. When an
> assumption is falsified, the Decision Twin propagates that one fact across the whole
> strategy — dropping confidence, re-ranking what to change, and learning. ChatGPT answers
> and forgets. The Decision Twin remembers, verifies, and compounds.

---

## Setup (once, before you walk on)

```bash
cd backend && pip install -r requirements.txt
python run_demo.py                 # serves :8000, seeds the strategy scenario + arena
# browser:
open "../nexus-landing/standalone/index.html?api=http://localhost:8000"
```

Zero AWS, zero keys. The aha screen (`decision-graph.html`) also runs fully offline on
embedded data, so a hostile venue network can never break the centerpiece.

For the phone-verify beat the judge's phone must reach the API: expose :8000 with a tunnel
(`ngrok http 8000`) and open with `?api=https://<tunnel>`.

**Days before, from a networked machine** — the genuinely anchored seal a judge will check:
```bash
python seal_live.py --decision "Will <real event> happen by <date>?" \
  --oracle-ref "polymarket:<cond>:yes" --days 21 --survival 0.62 --author micky
# save the entry id + the .ots proof — this is the real verify-on-phone artifact.
```

---

## The 3-minute winning demo

**0:00 — The hook.** "Every team here built a twin that answers questions. We built the
one that *remembers, verifies, and changes its mind when reality does* — for enterprise
strategy teams. Let me show you the moment that matters."

**0:20 — The question.** Open `decision-graph.html`. Read the executive's question on
screen: *"Why did we fail in Brazil — and what else is now at risk?"* "Six months ago this
team sealed a Brazil launch on one belief: demand grows over 18% a year. They sealed it on
the record — before they knew the answer."

**0:40 — Reality settles it (the aha).** Hit **▶ Let reality settle it.** The belief
ruptures. Watch the cascade: "Demand came in at six percent. The launch failed — but look
what else was standing on that same belief." Four connected decisions drop their confidence
live, one by one. "Mexico expansion, the São Paulo center, LATAM pricing, the sales org —
all re-scored, in real time, from one verified fact."

**1:20 — What to change.** Point at the right column. "And it doesn't just tell you you're
in trouble — it ranks exactly what to change by business impact, and prices the exposure.
**$40M of committed capital, repriced from one broken belief.** Hold Mexico — $24M — it
inherits the same thesis. Pause the fulfilment capex. Reprice. Freeze the backfill." Each
card reads like an exec memo: action, dollars, why-now, evidence, and the alternative to
take instead. Point at the two untouched cards. "These two don't depend on Brazil demand,
so the twin leaves them alone. That discrimination is the product."

**1:50 — The twin learned.** Point at the learning panel. "This belief's falsification rate
just went up. Every future strategy that leans on it now starts with lower confidence —
automatically. That's organizational memory. ChatGPT would have forgotten this conversation
already."

**2:15 — Don't trust me.** Switch to `verify.html` (or scan the QR with a judge's phone).
"You shouldn't take my word that the Brazil call was made *before* the outcome." Their phone
recomputes the decision's fingerprint on their own device and confirms: sealed before the
outcome ✓, intact ✓, anchored externally ✓. "Your phone just verified a NEXUS decision
without trusting NEXUS."

**2:40 — AWS + the moat.** "Bedrock reasons each decision. EventBridge and Lambda run the
verification loop with no human in it. S3 Object Lock makes every seal write-once. And the
moat isn't any of that — a competitor clones this UI by Thursday. They cannot clone a year
of verified, sealed-before-outcome enterprise decisions. That compounding record is the
business."

**2:58 — Close.** "The decision twin enterprise strategy teams can actually check. It
remembers, it verifies, and it just re-scored an entire strategy in front of you. Thank
you."

---

## The 5-minute technical cut (if asked to go deeper)

Add, after the aha: open `arena.html` and hit **▶ Resolve reality now** to show humans vs
AI scored live on calibration, then **⚡ Release the live question** to watch a 30-day-old
forecast settle on stage. Then walk `ARCHITECTURE.md` Part II: the hash-chained record, the
oracle that settles outcomes (never self-graded), recalibration, and the EventBridge +
Lambda + S3 Object Lock loop. End on the honesty note below.

---

## The honesty beat (say it unprompted — it *is* the product)

"One straight thing: the Brazil scenario and the arena cohort are seeded so you can watch
the mechanism in three minutes. The seals are real — every one was made before its outcome,
on the same chain. The *genuinely* anchored, verify-on-your-phone proof is the `seal_live`
entry from three weeks ago. We keep spectacle and proof separate in the code, not just in
the pitch. That honesty is why an enterprise can trust the number."

---

## One-command dry run
```bash
cd backend && python run_demo.py --check     # prints the seal → settle → propagate flow
```

## If the network is hostile
`decision-graph.html` runs the entire aha offline on embedded data — the centerpiece never
depends on the venue. `arena.html` / `verify.html` need the local API (`?api=http://localhost:8000`).
The external timestamp anchor degrades to `S3-WORM only` offline — say so; it's part of the
honesty.
