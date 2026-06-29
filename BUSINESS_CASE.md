# Business Case

## The buyer and the pain
The **enterprise strategy office** (Head of Strategy / Corp Dev / office of the COO) owns a
portfolio of nine-figure bets — market entries, build/buy, pricing, org moves — resting on
assumptions nobody writes down. When a bet fails, no one can say which belief broke or what
else depended on it; last year's reasoning left with the analyst who built the deck.

## What NEXUS changes (measured, not asserted)
The value surface (`GET /twin/value`) computes these **directly from the record**:
- **Assumption coverage** — % of sealed decisions carrying named, tracked assumptions.
- **Forecast verification rate** — % of sealed decisions reality has settled.
- **Audit readiness** — % of resolved decisions with hashed external evidence.
- **Capital repriced** — committed capital × the drop in survival probability when a shared
  belief is falsified (model declared, flagged an estimate).

## The value model (declared inputs, no invented precision)
```
review_prep_hours_saved/yr = hours_per_review × reviews_per_year × automation_fraction
labour_value/yr            = hours_saved × analyst_hourly_usd
```
Defaults (tunable per query): 40 h/review · 12 reviews/yr · 0.7 automation · $150/h →
~$50k/yr in review-prep labour per strategy team, **plus** the repriced-capital exposure
the twin surfaces the moment an assumption breaks. Both are flagged estimates with inputs.

## Why it compounds (the moat)
Every verified outcome sharpens the twin: a falsified belief's probability drops in every
future simulation automatically (the learning flywheel, `simulation.explore_decision`). The
switching cost is the **compounding corpus of verified, sealed-before-outcome decisions** —
a record a competitor cannot generate, buy, or backfill.

## Outcomes a strategy office is judged on
| Outcome | Before | With NEXUS |
|---|---|---|
| "Which decisions are at risk *now*?" | unknown until the QBR | answered every morning |
| Assumption coverage | implicit | measured, on the record |
| Decision traceability / audit readiness | reconstructed after the fact | provable, sealed before outcome |
| Forecast verification | unmeasured | continuously scored against reality |
| Knowledge retention | walks out the door | persists and compounds in the twin |
