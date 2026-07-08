"""
benchmarks/score.py — run the REAL gate over a gold set and report per-class precision + Wilson LB.

    python benchmarks/score.py                         # scores benchmarks/gold/seed.jsonl (oracle judge)
    python benchmarks/score.py path/to/gold.jsonl      # scores your own hand-rated set

The scorer builds a `Claim` from each record, wires the engine's real `ClaimGate.entailment`
(structural link rule + 3-valued aggregation — the code that ships), and compares its verdict to
the record's gold label. The headline line is the one that governs `strict_drop`:

    strict_drop clearance: precision-LB(unsupported) >= 0.80  ->  CLEARED / not yet

Judge mode is OracleJudge by default (isolates the policy; deterministic, offline). Point `--live`
at a `stormworthy.llm` VerifyProvider to measure end-to-end precision instead.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # make `benchmarks` importable when run as a script

from benchmarks.metrics import classification_report
from benchmarks.schema import GoldRecord, OracleJudge, load_gold
from stormworthy.engine import ClaimGate

STRICT_DROP_BAR = 0.80


def score(records: "list[GoldRecord]") -> "list[tuple[str, str]]":
    """-> [(predicted_verdict, gold_verdict), ...] over the real gate, one oracle judge per record."""
    pairs = []
    for rec in records:
        gate = ClaimGate(OracleJudge(rec.sources))
        predicted = gate.entailment(rec.to_claim()).get("verdict", "unsupported")
        pairs.append((predicted, rec.gold))
    return pairs


def format_report(records, pairs) -> str:
    rep = classification_report(pairs)
    lines = [
        f"gold set: {len(records)} claims   overall accuracy: {rep['_accuracy']:.2f}",
        "",
        f"{'class':<14}{'pred':>5}{'correct':>9}{'precision':>11}{'prec-LB':>9}{'recall':>8}",
        "-" * 56,
    ]
    for label in ("supported", "unsupported", "unclear"):
        r = rep[label]
        lines.append(f"{label:<14}{r.predicted:>5}{r.correct:>9}{r.precision:>11.2f}"
                     f"{r.precision_lb:>9.2f}{r.recall:>8.2f}")
    lb = rep["unsupported"].precision_lb
    n = rep["unsupported"].predicted
    cleared = "CLEARED" if lb >= STRICT_DROP_BAR else "NOT YET"
    lines += [
        "",
        f"strict_drop clearance  (precision-LB[unsupported] >= {STRICT_DROP_BAR:.2f}):  {cleared}",
        f"  precision-LB[unsupported] = {lb:.3f}  over n = {n} predicted-unsupported claims",
    ]
    if n < 30:
        lines.append("  NOTE: n is tiny - this is a harness smoke run on the illustrative seed, "
                     "NOT a validation result. Populate a real hand-rated gold set to earn a number.")
    return "\n".join(lines)


def main(argv: "list[str]") -> int:
    path = argv[0] if argv else str(Path(__file__).resolve().parent / "gold" / "seed.jsonl")
    records = load_gold(path)
    pairs = score(records)
    print(format_report(records, pairs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
