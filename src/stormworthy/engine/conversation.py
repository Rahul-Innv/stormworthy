"""
engine/conversation.py — Part 2 core: the perspective-guided, retrieval-grounded conversation loop.

This is STORM's dominant value driver (the ablation-proven part of the method): for each perspective, a multi-turn loop
where a persona ASKS and a grounded EXPERT answers, with each next question conditioned on the prior
answer. The LLM-driven steps (ask / answer) are INJECTED as Protocols so the engine stays portable and
testable — a deterministic stub drives offline proofs; the live LLM impl plugs in for the real run.

silence != absence: retrieval.fetch -> None drops the source (no false evidence); the loop stops early
when the interrogator returns None (saturation), honoring the "most from least" budget.
"""
from __future__ import annotations

from typing import Optional, Protocol

from .contracts import Perspective, RetrievalAdapter, Source, Turn


class Interrogator(Protocol):
    """Persona-conditioned question asker. Returns the next question, or None to stop (saturation)."""
    def ask(self, perspective: Perspective, context: list[Turn]) -> Optional[str]: ...


class Expert(Protocol):
    """Grounded answerer: synthesizes ONLY the trusted sources into an answer + typed, cited Claims."""
    def answer(self, perspective: Perspective, question: str, sources: list[Source]) -> "tuple[str, list]": ...


def run_conversation(perspective: Perspective, retrieval: RetrievalAdapter,
                     interrogator: Interrogator, expert: Expert, *,
                     max_turns: int = 3, k: int = 4, trust_floor: float = 0.0) -> list[Turn]:
    """One perspective's grounded conversation. Pure over its injected collaborators."""
    context: list[Turn] = []
    for _ in range(max_turns):
        question = interrogator.ask(perspective, context)
        if not question:
            break  # saturation -> stop early (budget discipline)
        sources: list[Source] = []
        for ref in retrieval.search(question, k=k, perspective_id=perspective.id):
            src = retrieval.fetch(ref)
            if src is None:
                continue  # absent, not zero
            if retrieval.trust(src) >= trust_floor:
                sources.append(src)
        answer, claims = expert.answer(perspective, question, sources)
        context.append(Turn(question=question, answer=answer,
                            claims=tuple(claims), sources=tuple(sources)))
    return context
