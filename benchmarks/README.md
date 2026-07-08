# Gate benchmark

The harness that turns StormWorthy's `strict_drop` mode from a promise into an earned number.

`strict_drop` silently removes claims the gate judges unsupported. The only error that mode can
make that matters is a **false drop** — deleting a claim that was actually true. So the quantity
that gates it is **precision on the predicted-"unsupported" class**: of the claims the gate marks
unsupported, what fraction really are. Because a good-looking precision on a handful of claims is
not trustworthy, the bar is on the Wilson score interval's **lower** bound, not the point estimate:

> **`strict_drop` clears when Wilson-LB(0.95) of precision on the predicted-unsupported class ≥ 0.80.**

Until a gold set clears that bar, flag-only stays the only supported mode — unsupported claims are
retained and flagged, never silently deleted. That is the whole point: the mode is *earned*.

## What it measures — and what it doesn't

The scorer runs the **real** `ClaimGate.entailment` (the structural link rule + 3-valued
aggregation that ships in `src/stormworthy/engine/verify.py`) over each gold claim and compares its
verdict to the human label. Two judge modes answer two different questions from the same gold set:

| Judge | Question it answers | Cost |
|---|---|---|
| **OracleJudge** (default) | *Assuming a perfect per-source judge, how good is the gate POLICY?* Isolates the structural rule + aggregation from LLM judge noise. | offline, deterministic, $0 |
| a live `stormworthy.llm` provider | *End-to-end, how good is policy × judge?* The number you'd actually ship on. | LLM spend |

Report the oracle number to defend the *design*; report the live number to defend the *product*.
Both are honest; they are not interchangeable.

## Run it

```bash
python benchmarks/score.py                    # scores the illustrative seed with the oracle judge
python benchmarks/score.py path/to/gold.jsonl # scores your own hand-rated set
```

Example output on the seed set:

```text
gold set: 8 claims   overall accuracy: 1.00

class          pred  correct  precision  prec-LB  recall
--------------------------------------------------------
supported         4        4       1.00     0.51    1.00
unsupported       3        3       1.00     0.44    1.00
unclear           1        1       1.00     0.21    1.00

strict_drop clearance  (precision-LB[unsupported] >= 0.80):  NOT YET
  precision-LB[unsupported] = 0.438  over n = 3 predicted-unsupported claims
  NOTE: n is tiny — this is a harness smoke run on the illustrative seed, NOT a validation result.
```

Note the harness reports the gate perfect on the seed (accuracy 1.00) yet **does not clear the bar**
— because n = 3 is nowhere near enough for a 0.80 lower bound. That gap is the feature: the Wilson
floor refuses to let a tiny, tidy sample masquerade as validation.

## The gold set

`gold/seed.jsonl` is an **illustrative fixture**, not a validation set — eight hand-labelled claims
that walk every gate path once (supported evaluative, a good `supports:"link"` inference, the
over-association leap, a contradicted fact, an uncited fact, an absent-source abstain). Each line:

```json
{"id": "conv-leap", "kind": "relational",
 "text": "The below-the-fold CTA and the nine required fields therefore suppress conversion.",
 "citations": [{"url": "subject.md", "supports": "antecedent"}, {"url": "subject.md", "supports": "antecedent"}],
 "sources": {"subject.md": "supported"},
 "gold": "unsupported",
 "note": "antecedents cited, the link is not -> structurally unsupported"}
```

- **`sources`** — the oracle per-citation verdict map (`url -> supported|unsupported|unclear`). An
  unlisted url reads as `unclear` (silence ≠ absence). A live judge replaces this map entirely.
- **`gold`** — the whole-claim ground truth the prediction is graded against.

### Building a real gold set

1. Collect ~150–300 claims from live runs across ≥ 2 domains, spanning all three kinds and both
   stances (include refuter claims — contestation is where precision is hardest).
2. Have ≥ 2 independent raters label each claim `supported | unsupported | unclear` against its
   actual cited sources; adjudicate disagreements and record inter-rater agreement.
3. Save as JSONL in this format and run `score.py`. Publish the oracle **and** live numbers, the
   sample size, and the rater agreement — never a bare percentage.
