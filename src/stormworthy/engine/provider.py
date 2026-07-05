"""
engine/provider.py — ResearchRun: the shared Part 1 + Part 2 orchestrator.

Both original adapters carried a near-identical copy of this control flow; it is promoted here so
they converge on one implementation. What stays adapter-side is only the DOWN-PROJECTION of the
Dossier into the domain's shipped artifact (a research fill, a design brief, ...).

Flow: design perspectives once -> K independent runs (each: every perspective's grounded
conversation; surface inferences with the source stance; anti-evasion check) -> 3-tier gate ->
sections -> Dossier. Hardenings carried in from the field:
  - conversation_log and evasions accumulate across ALL K runs (not just the last);
  - the gate's min_support is plumbed into assemble_sections (they were silently unrelated);
  - the surfacer receives the perspective's STANCE, so a refuter's surfaced leap contests its lens.

strict_drop defaults False (flag-only): unsupported claims are retained AND flagged. Dropping them
from the shipped body is a precision claim that must be EARNED on a hand-rated gold set before you
turn it on.
"""
from __future__ import annotations

from .contracts import Dossier, PerspectiveSet
from .conversation import run_conversation
from .gate import assemble_sections, score_claims
from .perspective import design_perspectives
from .writer import assert_no_unsurfaced_inference


class ResearchRun:
    def __init__(self, framework, retrieval, interrogator, expert, surfacer, gate, *,
                 k_runs: int = 2, max_turns: int = 3, k: int = 4, trust_floor: float = 0.0,
                 strict_drop: bool = False, overlap_threshold: float = 0.6):
        self.framework = framework
        self.retrieval = retrieval
        self.interrogator = interrogator
        self.expert = expert
        self.surfacer = surfacer
        self.gate = gate
        self.k_runs = k_runs
        self.max_turns = max_turns
        self.k = k
        self.trust_floor = trust_floor
        self.strict_drop = strict_drop  # False by default: strict-drop is EARNED, never assumed
        self.overlap_threshold = overlap_threshold

    def perspectives(self) -> PerspectiveSet:
        return design_perspectives(self.framework)

    def _run_once(self, perspectives):
        claims, log, evasions = [], [], []
        for p in perspectives:
            turns = run_conversation(p, self.retrieval, self.interrogator, self.expert,
                                     max_turns=self.max_turns, k=self.k,
                                     trust_floor=self.trust_floor)
            log.extend(turns)
            for t in turns:
                claims.extend(t.claims)
                rels = self.surfacer.surface(t.answer, list(t.claims),
                                             perspective_id=p.id, stance=p.stance)
                claims.extend(rels)
                # anti-evasion guard: a leap left in prose but NOT surfaced as a claim is flagged
                missing = assert_no_unsurfaced_inference(t.answer, rels, self.surfacer,
                                                         overlap_threshold=self.overlap_threshold)
                for m in missing:
                    evasions.append({"perspective": p.id, "inference": m})
        return claims, log, evasions

    def research(self, entity_id: str) -> Dossier:
        ps = self.perspectives()
        runs, log, evasions = [], [], []
        for _ in range(self.k_runs):
            run_claims, run_log, run_evasions = self._run_once(ps.perspectives)
            runs.append(run_claims)
            log.extend(run_log)          # accumulate across ALL K runs
            evasions.extend(run_evasions)
        scored = score_claims(runs, self.gate)
        sections = assemble_sections(scored, strict_drop=self.strict_drop,
                                     min_support=getattr(self.gate, "min_support", 0.5))
        return Dossier(entity_id=entity_id, sections=sections,
                       conversation_log=log, unused_sources=[], evasions=evasions)
