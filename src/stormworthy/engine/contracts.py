"""
engine/contracts.py — the portable data model + the adapter Protocols.

This file is the keystone of the engine/adapter firewall: it depends on the standard library ONLY,
so any project can reuse the engine by implementing the adapter Protocols in its own adapter code.
Three live here (FrameworkSpec, RetrievalAdapter, VerificationGate); three more are defined beside
the code they drive (Interrogator + Expert in conversation.py, InferenceSurfacer in writer.py).

`VERDICTS` is the canonical verdict vocabulary. Downstream adapters that keep their own copy should
assert equality against THIS tuple (the engine is the source of truth).

Claim model: every assertion is typed `fact | relational | evaluative`. The `kind` drives gate
logic — relational/evaluative claims (the over-association risk) are verified for the FULL
proposition (the link / the judgment), never a sub-span. This targets the classic failure of
grounded-generation pipelines: individually-true facts woven into an unsupported relationship.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Literal, Optional, Protocol, TypedDict

# --- vocab -------------------------------------------------------------------------------------------

ClaimKind = Literal["fact", "relational", "evaluative"]
#   fact        — one atomic assertion about a single entity/attribute ("Acme uses Postgres").
#   relational  — a load-bearing "X => Y" inference linking facts ("usage-based pricing => better NRR").
#                 The JUDGE must confirm the LINK, not merely that X and Y are each independently true.
#   evaluative  — a judgment/ranking ("strong technical moat"); needs a rubric anchor + cited basis.

AngleKind = Literal["framework", "archetype", "basic_fact", "refuter"]
#   framework   — derived from a FrameworkSpec dimension (one lens of the domain's taxonomy).
#   archetype   — a curated floor role that always fires regardless of framework coverage.
#   basic_fact  — the mandatory "+1" desk-research baseline (pinned; never merged out).
#   refuter     — the adversarial bear-case (pinned); its claims contest constructive ones.

Stance = Literal["constructive", "disconfirming"]

CitationSupports = Literal["fact", "antecedent", "link"]
#   For a relational claim, only a citation tagged "link" supports the inference itself; "antecedent"
#   citations (inherited from the component facts) do NOT. This makes an uncited inference
#   STRUCTURALLY unsupported — no judge required.

VERDICTS = ("supported", "unsupported", "unclear")  # canonical — adapters assert against this


class Verdict(TypedDict, total=False):
    verdict: str   # one of VERDICTS
    note: str
    fraction: float


# --- evidence ----------------------------------------------------------------------------------------

@dataclass(frozen=True)
class SourceRef:
    """A search hit not yet fetched."""
    url: str
    title: Optional[str] = None
    snippet: Optional[str] = None
    channel: Optional[str] = None  # adapter-defined, e.g. "web" | "docs" | "kb" (feeds independence)


@dataclass(frozen=True)
class Source:
    """A fetched, trust-scored source. `None` from RetrievalAdapter.fetch means ABSENT (silence != absence)."""
    url: str
    title: Optional[str]
    text: str
    as_of: Optional[str] = None        # ISO date the content is current as of (staleness handling)
    channel: Optional[str] = None       # the independence channel (corroboration tier)
    trust: float = 0.0                  # 0..1; a 200 is necessary but not sufficient (identity-verified)
    content_hash: Optional[str] = None  # sha256 of fetched text — for replay-reproducibility


class Citation(TypedDict, total=False):
    """A cited basis for a claim. `claim`+`url` are mandatory; the extra keys
    (kind/relation/supports/as_of) thread typing + provenance through the gate."""
    claim: str
    url: str
    title: Optional[str]
    kind: ClaimKind
    relation: Optional[str]
    supports: CitationSupports
    as_of: Optional[str]


# --- claims ------------------------------------------------------------------------------------------

def claim_id(kind: str, text: str, urls: list[str], stance: str = "constructive") -> str:
    """Deterministic id — stable across runs (no wall-clock, no RNG) so the artifact is replay-stable.

    Identity is SEMANTIC: kind + stance + text + evidence. Stance is part of identity because the
    refuter deliberately restates findings as bear-cases — a constructive claim and a disconfirming
    claim with identical text must NOT collapse to one id (de-dup keyed on id would otherwise let the
    refuter's copy overwrite the constructive survivor, forcing a wrongful abstain). perspective_id
    is deliberately EXCLUDED: the same assertion reached from two perspectives IS the same claim.
    """
    h = hashlib.sha256()
    h.update("|".join([kind, stance, text, *sorted(urls)]).encode("utf-8"))
    return h.hexdigest()[:16]


@dataclass(frozen=True)
class Claim:
    kind: ClaimKind
    text: str                                   # for relational: the FULL "X => Y" sentence
    citations: tuple[Citation, ...] = ()
    # routing:
    perspective_id: str = ""
    anchor_keys: tuple[str, ...] = ()           # subset of FrameworkSpec angle ids / lens keys
    stance: Stance = "constructive"
    # relational-only:
    antecedent_ids: tuple[str, ...] = ()        # ids of the `fact` claims the inference rests on
    relation: Optional[str] = None              # "therefore" | "because" | "enables" | "implies" | ...
    # evaluative-only:
    rubric_anchor: Optional[str] = None
    # gate outcomes (filled by the VerificationGate, never by the writer):
    entailment: Optional[Verdict] = None
    corroboration: Optional[float] = None       # None == optional tier not run / insufficient channels
    self_consistency: Optional[float] = None    # fraction of K runs the claim recurred in
    confidence: Optional[float] = None          # final, after the contestation floor

    @property
    def id(self) -> str:
        return claim_id(self.kind, self.text, [c.get("url", "") for c in self.citations], self.stance)

    @property
    def is_inference(self) -> bool:
        """relational/evaluative claims are the over-association surface — gated on the full proposition."""
        return self.kind in ("relational", "evaluative")


# --- conversation ------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Turn:
    question: str
    answer: str
    claims: tuple[Claim, ...]
    sources: tuple[Source, ...]


# --- perspectives (Part 1 output) --------------------------------------------------------------------

@dataclass(frozen=True)
class Angle:
    """A FrameworkSpec-emitted research angle (the raw input to the Perspective Designer)."""
    id: str
    title: str
    anchor: str                 # "Family — detail" string; the family (before the dash) drives de-dup
    question: str
    kind: AngleKind
    rubric: Optional[str] = None
    anchor_keys: tuple[str, ...] = ()   # which lens key(s) this angle feeds


@dataclass(frozen=True)
class Perspective:
    """A designed, de-duplicated perspective (the Part 1 product; drives one conversation)."""
    id: str
    persona: str
    anchor: str
    kind: AngleKind
    seed_questions: tuple[str, ...] = ()
    rubric: Optional[str] = None
    anchor_keys: tuple[str, ...] = ()
    stance: Stance = "constructive"     # the refuter is "disconfirming"


@dataclass(frozen=True)
class PerspectiveSet:
    framework_id: str
    perspectives: tuple[Perspective, ...]
    shared_rubrics: dict = field(default_factory=dict)


# --- dossier (Part 2 output) -------------------------------------------------------------------------

LensStatus = Literal["filled", "insufficient_evidence", "pending_research"]


@dataclass
class Section:
    anchor: str
    anchor_keys: tuple[str, ...]
    headline: Optional[str]
    body: str
    claims: list[Claim]
    status: LensStatus = "filled"
    contested: bool = False
    contesting_claims: tuple[str, ...] = ()
    vetted: bool = False                 # fail-closed: ships publicly only when the verify pass sets this
    confidence: Optional[float] = None   # None == abstain (insufficient_evidence); floored when contested


@dataclass
class Dossier:
    entity_id: str
    sections: list[Section]
    conversation_log: list[Turn] = field(default_factory=list)
    unused_sources: list[Source] = field(default_factory=list)  # the Co-STORM moderator surface
    evasions: list = field(default_factory=list)  # anti-evasion findings: prose leaps never surfaced as claims


# --- the adapter Protocols (an adapter implements these three + the LLM roles) -------------------------

class FrameworkSpec(Protocol):
    """Part 1 input: the domain's analytical taxonomy, framework-derived."""
    def framework_id(self) -> str: ...
    def angles(self) -> list[Angle]: ...
    def shared_rubrics(self) -> dict: ...
    def basic_fact_angle(self) -> Angle: ...      # the mandatory "+1" desk-research baseline
    def archetype_floor(self) -> list[Angle]: ...  # curated floor (incl. the refuter)


class RetrievalAdapter(Protocol):
    """Part 2 grounding: search -> fetch -> trust, returning uniform Sources."""
    def search(self, query: str, *, k: int, perspective_id: str) -> list[SourceRef]: ...
    def fetch(self, ref: SourceRef) -> Optional[Source]: ...   # None == absent
    def trust(self, src: Source) -> float: ...                  # 0..1


class VerificationGate(Protocol):
    """Claim-level gate — the verification layer classic STORM lacks. All tiers return CALIBRATED
    confidence, never a binary.

    entailment + self_consistency are MANDATORY and portable. corroboration is OPTIONAL: a project
    with no independence model returns None and runs a two-tier gate.
    """
    def entailment(self, claim: Claim) -> Verdict: ...                       # mandatory
    def self_consistency(self, claims_by_run: list[list[Claim]]) -> list[Claim]: ...  # mandatory
    def corroboration(self, claim: Claim) -> Optional[float]: ...            # optional
