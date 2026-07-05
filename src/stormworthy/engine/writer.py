"""
engine/writer.py — Part 2: claim routing, inference-surfacing, and the anti-evasion guard.

The over-association defense lives here:
  - the surfacer forces load-bearing "X => Y" leaps OUT of prose into their own typed `relational`
    claims, so the gate can verify the LINK (not just the component facts);
  - assert_no_unsurfaced_inference re-detects relationships in the FINAL body and FAILS the section if a
    leap was left implied in prose but not surfaced as a claim (omission is strictly worse than surfacing);
  - route_claims fans each claim to every lens in its anchor_keys (the many-to-many map).

The detection/surfacing LLM steps are injected (InferenceSurfacer) so the engine stays portable/testable.
Matching in the guard is a lexical HEURISTIC (substring or word-Jaccard), not semantic — it exists to
catch omission, not paraphrase; tune `overlap_threshold` per domain.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Protocol

from .contracts import Claim, Stance


class InferenceSurfacer(Protocol):
    """LLM-driven: turn prose leaps into typed relational/evaluative claims, and (independently) detect them.

    `stance` is the SOURCE perspective's stance — surfaced claims must inherit it, or a refuter's causal
    bear-case leap would be mis-routed as constructive and never contest the lens.
    """
    def surface(self, body: str, fact_claims: list[Claim], *,
                perspective_id: str, stance: Stance = "constructive") -> list[Claim]: ...
    def detect(self, body: str) -> list[str]: ...  # the independent re-detection used by the anti-evasion guard


def route_claims(claims: list[Claim]) -> "dict[str, list[Claim]]":
    """Fan each claim to every lens in its anchor_keys (anchor_keys are pre-constrained to real lens keys)."""
    by_lens: "dict[str, list[Claim]]" = defaultdict(list)
    for c in claims:
        for key in c.anchor_keys:
            by_lens[key].append(c)
    return dict(by_lens)


def _norm(s: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in s).split())


def assert_no_unsurfaced_inference(body: str, relational_claims: list[Claim],
                                   surfacer: InferenceSurfacer, *,
                                   overlap_threshold: float = 0.6) -> list[str]:
    """Return the list of prose inferences NOT matched by a surfaced relational claim (evasion).
    Empty list == the writer surfaced every load-bearing leap (the section may proceed)."""
    surfaced = [_norm(rc.text) for rc in relational_claims]
    missing = []
    for detected in surfacer.detect(body):
        d = _norm(detected)
        # matched if a surfaced claim shares substantial overlap with the detected relationship
        if not any(d in s or s in d or _overlap(d, s) >= overlap_threshold for s in surfaced):
            missing.append(detected)
    return missing


def _overlap(a: str, b: str) -> float:
    wa, wb = set(a.split()), set(b.split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)
