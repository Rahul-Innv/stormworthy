"""Deterministic, configurable stubs for all six adapter Protocols + the VerifyProvider.

Nothing here is random or clocked — the same configuration always produces the same pipeline
output, which is what makes the offline proofs meaningful as regression tests.
"""
from __future__ import annotations

from typing import Optional

from ..engine.contracts import Angle, Claim, Perspective, Source, SourceRef, Turn


class StubFramework:
    """FrameworkSpec built from plain Angle lists."""

    def __init__(self, framework_angles: "list[Angle]", basic_fact: Angle, refuter: Angle,
                 *, fid: str = "stub-framework-v1", rubrics: Optional[dict] = None):
        self._angles = list(framework_angles)
        self._basic = basic_fact
        self._refuter = refuter
        self._fid = fid
        self._rubrics = rubrics or {}

    def framework_id(self) -> str:
        return self._fid

    def angles(self) -> "list[Angle]":
        return list(self._angles)

    def shared_rubrics(self) -> dict:
        return dict(self._rubrics)

    def basic_fact_angle(self) -> Angle:
        return self._basic

    def archetype_floor(self) -> "list[Angle]":
        return [self._basic, self._refuter]


class StubRetrieval:
    """RetrievalAdapter over an in-memory corpus: {url: text}. A url mapped to None (or absent
    from the corpus) is UNFETCHABLE -> fetch returns None (silence != absence)."""

    def __init__(self, corpus: "dict[str, Optional[str]]", *,
                 refs_by_query: "Optional[dict[str, list[str]]]" = None,
                 trust_by_url: "Optional[dict[str, float]]" = None):
        self.corpus = corpus
        self.refs_by_query = refs_by_query
        self.trust_by_url = trust_by_url or {}

    def search(self, query: str, *, k: int, perspective_id: str) -> "list[SourceRef]":
        if self.refs_by_query is not None:
            urls = self.refs_by_query.get(query, [])
        else:
            urls = list(self.corpus.keys())
        return [SourceRef(url=u) for u in urls[:k]]

    def fetch(self, ref: SourceRef) -> Optional[Source]:
        text = self.corpus.get(ref.url)
        if text is None:
            return None  # absent, not zero
        return Source(url=ref.url, title=ref.url, text=text, trust=self.trust_by_url.get(ref.url, 0.9))

    def trust(self, src: Source) -> float:
        return src.trust


class StubInterrogator:
    """Interrogator with a fixed question list per perspective id; returns None when exhausted."""

    def __init__(self, questions: "dict[str, list[str]]"):
        self.questions = questions

    def ask(self, perspective: Perspective, context: "list[Turn]") -> Optional[str]:
        qs = self.questions.get(perspective.id, list(perspective.seed_questions))
        return qs[len(context)] if len(context) < len(qs) else None


class StubExpert:
    """Expert with canned (answer, claims) per perspective id. Claims are emitted as configured —
    including their stance, which for a refuter perspective must be 'disconfirming'."""

    def __init__(self, answers: "dict[str, tuple[str, list[Claim]]]"):
        self.answers = answers

    def answer(self, perspective: Perspective, question: str,
               sources: "list[Source]") -> "tuple[str, list[Claim]]":
        answer, claims = self.answers.get(perspective.id, ("no findings", []))
        return answer, list(claims)


class StubSurfacer:
    """InferenceSurfacer with canned surfaced claims and detections, keyed by perspective id.

    Surfaced claims inherit the `stance` argument (the engine passes the source perspective's
    stance — Protocol contract). Calls are recorded on `.stance_seen` so tests can assert the
    engine passed the right stance.
    """

    def __init__(self, surfaced: "Optional[dict[str, list[Claim]]]" = None,
                 detections: "Optional[dict[str, list[str]]]" = None):
        self.surfaced = surfaced or {}
        self.detections = detections or {}
        self.stance_seen: "dict[str, str]" = {}
        self._bodies_by_perspective: "dict[str, str]" = {}

    def surface(self, body: str, fact_claims: "list[Claim]", *,
                perspective_id: str, stance: str = "constructive") -> "list[Claim]":
        self.stance_seen[perspective_id] = stance
        self._bodies_by_perspective[perspective_id] = body
        out = []
        for c in self.surfaced.get(perspective_id, []):
            out.append(c if c.stance == stance else _restance(c, stance))
        return out

    def detect(self, body: str) -> "list[str]":
        # detections are keyed by the perspective whose body this is (bodies are unique per test)
        for pid, b in self._bodies_by_perspective.items():
            if b == body:
                return list(self.detections.get(pid, []))
        return []


def _restance(c: Claim, stance: str) -> Claim:
    from dataclasses import replace
    return replace(c, stance=stance)  # type: ignore[arg-type]


class StubVerify:
    """VerifyProvider with verdicts keyed by url (fallback: by claim-text substring).
    Unknown urls verdict 'unclear' — the silence != absence default."""

    def __init__(self, by_url: "Optional[dict[str, str]]" = None,
                 by_text: "Optional[dict[str, str]]" = None):
        self.by_url = by_url or {}
        self.by_text = by_text or {}
        self.calls: "list[tuple[str, str]]" = []

    def verify(self, claim_text: str, url: str) -> dict:
        self.calls.append((claim_text, url))
        if url in self.by_url:
            return {"verdict": self.by_url[url], "note": "stub by url"}
        for frag, verdict in self.by_text.items():
            if frag in claim_text:
                return {"verdict": verdict, "note": "stub by text"}
        return {"verdict": "unclear", "note": "stub default (silence != absence)"}
