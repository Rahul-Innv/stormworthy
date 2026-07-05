"""
engine/verify.py — ClaimGate: the reference VerificationGate implementation (stdlib-only).

Domain-independent gate logic that previously lived copy-pasted in every adapter. An adapter now
only supplies a `verify_provider` — anything with `verify(claim_text, url) -> {"verdict", "note"}`
(an LLM judge for live runs, a deterministic stub for offline proofs). Everything else is policy
that should behave identically across domains:

  entailment       — structural rule first: a relational claim with no citation tagged
                     supports:"link" is unsupported NO MATTER what any judge says (the
                     over-association catch, judge-independent). Then 3-valued aggregation over the
                     per-citation judge verdicts: enough support -> "supported"; short of threshold
                     but NOTHING contradicts -> "unclear" (scored 0.4), because "we could not
                     confirm" must never read as "the source says no" (silence != absence); an
                     actual contradiction -> "unsupported".
  self_consistency — delegates to engine.consistency (stance-namespaced normalized recurrence,
                     injectable key, quorum knob).
  corroboration    — OPTIONAL tier, off by default (returns None -> two-tier gate). When enabled,
                     >= 2 distinct citation channels count as full corroboration.
"""
from __future__ import annotations

from typing import Callable, Hashable, Optional, Protocol

from .consistency import recurrence_key, self_consistency as _self_consistency
from .contracts import Claim, Verdict


class VerifyProvider(Protocol):
    """Judges one claim against one cited source. Return verdict in VERDICTS; on an unreadable or
    missing source return "unclear" (silence != absence), never "unsupported"."""
    def verify(self, claim_text: str, url: str) -> dict: ...


class ClaimGate:
    def __init__(self, verify_provider: VerifyProvider, *,
                 min_support: float = 0.5,
                 corroborate: bool = False,
                 quorum: float = 1.0,
                 key: "Callable[[Claim], Hashable]" = recurrence_key):
        self.vp = verify_provider
        self.min_support = min_support
        self.corroborate = corroborate
        self.quorum = quorum
        self.key = key

    def entailment(self, claim: Claim) -> Verdict:
        cits = list(claim.citations or ())
        if claim.kind == "relational":
            # only a citation tagged supports:"link" backs the inference itself (structural rule)
            cits = [c for c in cits if c.get("supports") == "link"]
            if not cits:
                return {"verdict": "unsupported", "note": "no citation supports the inferred link",
                        "fraction": 0.0}
        if not cits:
            return {"verdict": "unsupported", "note": "no citations", "fraction": 0.0}
        verdicts = [self.vp.verify(claim.text, c.get("url", "")) for c in cits]
        supported = sum(1 for v in verdicts if v.get("verdict") == "supported")
        contradicted = sum(1 for v in verdicts if v.get("verdict") == "unsupported")
        frac = round(supported / len(verdicts), 2)
        if supported >= 1 and frac >= self.min_support:
            return {"verdict": "supported",
                    "note": f"{supported}/{len(verdicts)} citations support", "fraction": frac}
        if contradicted == 0:
            # short of support, but NO source contradicts -> absent/ambiguous evidence, not a "no"
            return {"verdict": "unclear",
                    "note": f"{supported}/{len(verdicts)} support, none contradict", "fraction": frac}
        return {"verdict": "unsupported",
                "note": f"{supported}/{len(verdicts)} support, {contradicted} contradict",
                "fraction": frac}

    def self_consistency(self, claims_by_run: "list[list[Claim]]") -> "list[Claim]":
        return _self_consistency(claims_by_run, quorum=self.quorum, key=self.key)

    def corroboration(self, claim: Claim) -> Optional[float]:
        if not self.corroborate:
            return None  # optional tier skipped -> two-tier gate
        channels = {c.get("channel") for c in (claim.citations or ()) if c.get("channel")}
        if not channels:
            return None
        return round(min(1.0, len(channels) / 2.0), 2)  # >= 2 independent channels -> full
