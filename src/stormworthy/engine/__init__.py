"""The portable claim-verified research engine (stdlib-only; everything model- or domain-shaped is injected).

Public API — import from here; submodule paths are implementation detail:

  Part 1 (perspective design):    design_perspectives, family_of, ANCHOR_SEPARATORS
  Part 2 (grounded conversation): run_conversation, Interrogator, Expert
  Writer (claims + anti-evasion): route_claims, assert_no_unsurfaced_inference, InferenceSurfacer
  Gate (3-tier verification):     score_claims, assemble_sections, CONTESTED_FLOOR, VERDICT_BASE
  Reference implementations:      ClaimGate + VerifyProvider (verify), self_consistency +
                                  recurrence_key + norm_text (consistency), ResearchRun (provider)
  Contracts (data model + adapter Protocols): re-exported below.

An adapter implements 6 Protocols: FrameworkSpec, RetrievalAdapter, VerificationGate (contracts) +
Interrogator, Expert (conversation) + InferenceSurfacer (writer). Semantics an adapter must honor:
`fetch -> None` means ABSENT (silence != absence), `ask -> None` means saturation (stop early),
`corroboration -> None` means the optional tier is skipped (two-tier gate).
"""
from .contracts import (
    VERDICTS,
    Angle,
    AngleKind,
    Citation,
    CitationSupports,
    Claim,
    ClaimKind,
    Dossier,
    FrameworkSpec,
    LensStatus,
    Perspective,
    PerspectiveSet,
    RetrievalAdapter,
    Section,
    Source,
    SourceRef,
    Stance,
    Turn,
    Verdict,
    VerificationGate,
    claim_id,
)
from .consistency import norm_text, recurrence_key, self_consistency
from .conversation import Expert, Interrogator, run_conversation
from .gate import CONTESTED_FLOOR, VERDICT_BASE, assemble_sections, score_claims
from .perspective import ANCHOR_SEPARATORS, design_perspectives, family_of
from .provider import ResearchRun
from .verify import ClaimGate, VerifyProvider
from .writer import InferenceSurfacer, assert_no_unsurfaced_inference, route_claims

__all__ = [
    # contracts
    "VERDICTS", "Angle", "AngleKind", "Citation", "CitationSupports", "Claim", "ClaimKind",
    "Dossier", "FrameworkSpec", "LensStatus", "Perspective", "PerspectiveSet", "RetrievalAdapter",
    "Section", "Source", "SourceRef", "Stance", "Turn", "Verdict", "VerificationGate", "claim_id",
    # conversation
    "Expert", "Interrogator", "run_conversation",
    # gate
    "CONTESTED_FLOOR", "VERDICT_BASE", "assemble_sections", "score_claims",
    # perspective
    "ANCHOR_SEPARATORS", "design_perspectives", "family_of",
    # writer
    "InferenceSurfacer", "assert_no_unsurfaced_inference", "route_claims",
    # reference implementations
    "ClaimGate", "VerifyProvider", "ResearchRun",
    "norm_text", "recurrence_key", "self_consistency",
]
