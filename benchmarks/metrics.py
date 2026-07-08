"""
benchmarks/metrics.py — the scoring math, stdlib-only (matches the engine's zero-dependency ethos).

The metric that governs `strict_drop`: **precision on the predicted-"unsupported" class**. When the
gate silently removes a claim, the only thing that matters is that it was right to — a false drop
(deleting a true claim) is the unacceptable error. So we measure: of the claims the gate PREDICTS
unsupported, what fraction the gold set confirms are actually unsupported, and we gate on the
Wilson **lower** bound of that fraction (small samples must not be allowed to look better than they
are). The README's `strict_drop` bar is Wilson-LB(0.95) >= 0.80 on this class.
"""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

Z95 = 1.959963984540054  # 95% two-sided normal quantile


def wilson_lower_bound(k: int, n: int, z: float = Z95) -> float:
    """Lower bound of the Wilson score interval for k successes in n trials. Returns 0.0 when n == 0
    (no evidence -> claim nothing). This is deliberately conservative: it is the number you are
    allowed to publish, not the point estimate k/n."""
    if n <= 0:
        return 0.0
    p = k / n
    z2 = z * z
    denom = 1.0 + z2 / n
    centre = p + z2 / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return max(0.0, (centre - margin) / denom)


@dataclass(frozen=True)
class ClassReport:
    label: str
    predicted: int          # how many the gate assigned this label
    correct: int            # of those, how many gold agrees with
    precision: float        # correct / predicted
    precision_lb: float     # Wilson lower bound of precision — the publishable number
    support: int            # how many gold items truly carry this label (for recall context)
    recall: float


def classification_report(pairs: "list[tuple[str, str]]", labels=("supported", "unsupported", "unclear")):
    """pairs = [(predicted, gold), ...] -> {label: ClassReport}. Precision + its Wilson lower bound
    per class, plus recall for context. Overall accuracy is returned under the '_accuracy' key."""
    pred = Counter(p for p, _ in pairs)
    gold = Counter(g for _, g in pairs)
    hit = Counter(p for p, g in pairs if p == g)
    out: "dict[str, ClassReport]" = {}
    for label in labels:
        np_, nc = pred[label], hit[label]
        ng = gold[label]
        out[label] = ClassReport(
            label=label, predicted=np_, correct=nc,
            precision=(nc / np_) if np_ else 0.0,
            precision_lb=wilson_lower_bound(nc, np_),
            support=ng, recall=(nc / ng) if ng else 0.0)
    total = len(pairs)
    out["_accuracy"] = sum(hit.values()) / total if total else 0.0  # type: ignore[assignment]
    return out
