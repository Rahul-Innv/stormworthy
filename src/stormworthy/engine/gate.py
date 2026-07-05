"""
engine/gate.py — Part 2: the three-tier claim gate orchestration (portable).

Tiers (each via the injected VerificationGate):
  1. self_consistency — keep claims recurring across the K runs (annotated with a fraction).
  2. entailment       — does the cited source support the claim? (relational claims gate on the LINK.)
  3. corroboration    — independent agreeing channels (optional tier; None if no independence model).

Then assemble lens sections with the honesty rules:
  - no surviving SUPPORTED constructive claim -> status `insufficient_evidence`, confidence None (ABSTAIN);
  - a surviving SUPPORTED disconfirming (refuter) claim -> the lens is `contested`, confidence floored
    (a contradiction acts as a hard cap — never averaged into a mushy middle);
  - strict_drop removes unsupported claims from the shipped body; flag-only keeps them (flagged).

Tunables (CONTESTED_FLOOR, the verdict->confidence base map, min_support, headline length) are module
defaults promoted to keyword parameters — override per call, or leave the defaults.
"""
from __future__ import annotations

from dataclasses import replace

from .contracts import Section, VerificationGate
from .writer import route_claims

CONTESTED_FLOOR = 0.1

VERDICT_BASE = {"supported": 1.0, "unclear": 0.4, "unsupported": 0.0}
_BASE = VERDICT_BASE  # backwards-compatible alias


def _verdict(claim) -> str:
    return (claim.entailment or {}).get("verdict", "unsupported")


def score_claims(claims_by_run, gate: VerificationGate, *,
                 verdict_base: "dict[str, float]" = VERDICT_BASE) -> list:
    """Tier 1 (self-consistency) then tiers 2-3 (entailment + corroboration) -> fused confidence per claim."""
    survivors = gate.self_consistency(claims_by_run)
    scored = []
    for c in survivors:
        v = gate.entailment(c)
        corr = gate.corroboration(c)
        sc = c.self_consistency if c.self_consistency is not None else 1.0
        cf = corr if corr is not None else 1.0
        conf = round(verdict_base.get((v or {}).get("verdict"), 0.0) * sc * cf, 2)
        scored.append(replace(c, entailment=v, corroboration=corr, confidence=conf))
    return scored


def assemble_sections(scored_claims, *, strict_drop: bool, min_support: float = 0.5,
                      contested_floor: float = CONTESTED_FLOOR,
                      headline_chars: int = 90) -> list[Section]:
    sections: list[Section] = []
    for lens, claims in route_claims(scored_claims).items():
        constructive = [c for c in claims if c.stance == "constructive"]
        refuting = [c for c in claims if c.stance == "disconfirming"]
        s_plus = [c for c in constructive if _verdict(c) == "supported"]
        r_plus = [c for c in refuting if _verdict(c) == "supported"]

        if not s_plus:  # abstain — silence != absence, lower CONFIDENCE not score
            sections.append(Section(anchor=lens, anchor_keys=(lens,), headline=None, body="",
                                    claims=claims, status="insufficient_evidence",
                                    vetted=False, confidence=None))
            continue

        shipped = s_plus if strict_drop else constructive
        frac = round(len(s_plus) / len(constructive), 2) if constructive else 0.0
        verified = len(s_plus) >= 1 and frac >= min_support
        contested = bool(r_plus)
        conf = contested_floor if contested else round(sum(c.confidence or 0 for c in s_plus) / len(s_plus), 2)
        sections.append(Section(
            anchor=lens, anchor_keys=(lens,),
            headline=(shipped[0].text[:headline_chars] if shipped else None),
            body=" ".join(c.text for c in shipped), claims=claims, status="filled",
            contested=contested, contesting_claims=tuple(c.id for c in r_plus),
            vetted=verified, confidence=conf))
    return sections
