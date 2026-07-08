"""Locks the benchmark harness: the Wilson math, and the real gate scored end-to-end on the seed.

The seed fixture is engineered so the gate is PERFECT on it (accuracy 1.0) yet still fails to clear
the strict_drop bar (n too small) — the test asserts BOTH, because that honesty property (a tidy
sample must not look validated) is the reason the harness exists.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root -> import `benchmarks`

from benchmarks.metrics import classification_report, wilson_lower_bound
from benchmarks.schema import load_gold
from benchmarks.score import score


def test_wilson_lower_bound_known_values():
    assert wilson_lower_bound(0, 0) == 0.0                 # no evidence -> claim nothing
    assert abs(wilson_lower_bound(18, 18) - 0.8241) < 1e-3  # a perfect-but-small sample that JUST clears 0.80
    assert wilson_lower_bound(45, 50) < 0.80               # 90% raw precision at n=50 still fails the bar
    assert wilson_lower_bound(3, 3) < wilson_lower_bound(18, 18)  # lower bound tightens with n at fixed p


def test_wilson_is_a_lower_bound():
    # the bound is always <= the point estimate, and 0 for the empty case
    for k, n in [(3, 3), (45, 50), (80, 100), (1, 4)]:
        assert 0.0 <= wilson_lower_bound(k, n) <= k / n


def _seed_path():
    return Path(__file__).resolve().parents[1] / "benchmarks" / "gold" / "seed.jsonl"


def test_gate_is_perfect_on_seed_but_does_not_clear_the_bar():
    records = load_gold(_seed_path())
    assert len(records) == 8
    pairs = score(records)
    rep = classification_report(pairs)

    assert rep["_accuracy"] == 1.0                          # gate matches gold on every seed claim
    assert rep["unsupported"].predicted == 3 and rep["unsupported"].correct == 3
    assert rep["supported"].predicted == 4 and rep["supported"].correct == 4
    assert rep["unclear"].predicted == 1 and rep["unclear"].correct == 1

    # ...and yet the sample is far too small to clear strict_drop — the whole point of the Wilson floor
    assert rep["unsupported"].precision == 1.0
    assert rep["unsupported"].precision_lb < 0.80


def test_structural_and_silence_paths_score_as_specified():
    by_id = {r.id: p for r, p in zip(load_gold(_seed_path()), score(load_gold(_seed_path())))}
    assert by_id["conv-leap"][0] == "unsupported"      # over-association leap: judge-independent
    assert by_id["good-inference"][0] == "supported"   # a cited supports:"link" inference passes
    assert by_id["perf-lcp"][0] == "unclear"           # absent source -> silence != absence
    assert by_id["uncited-fact"][0] == "unsupported"   # no citations -> structurally unsupported
