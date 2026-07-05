"""
llm/roles.py — reference LLM implementations of the engine's injected roles.

Drop-in implementations of Interrogator / Expert / InferenceSurfacer (plus the entailment judge the
ClaimGate consumes), each a thin prompt over a RoleLLM. Domain adapters can use these as-is (the
domain lives in the FrameworkSpec's angles/rubrics and the retrieval corpus) or fork the prompts.

Grounding contract (the entailment axis): a claim must be grounded in a cited source, or it does
not ship — silence != absence. Hard rule kept from the field: critique the SUBJECT and its
decisions, never a named individual.
"""
from __future__ import annotations

from ..engine.contracts import Claim

_GROUNDING = ("GROUNDING RULE: every claim must rest on a CITED source from the SOURCES block, or a "
              "directly-observable attribute of the subject stated in the brief. Do not assert a "
              "finding, threshold, or judgment without a cited basis. Critique the SUBJECT and its "
              "decisions, never a named person. If the sources don't support a point, omit it.")

EXPERT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "answer": {"type": "string"},
        "claims": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "kind": {"type": "string", "enum": ["fact", "evaluative"]},
                "text": {"type": "string"},
                "evidence_urls": {"type": "array", "items": {"type": "string"}},
                "anchor_keys": {"type": "array", "items": {"type": "string"}},
                "rubric_anchor": {"type": "string"},
            },
            "required": ["kind", "text", "evidence_urls", "anchor_keys", "rubric_anchor"],
        }},
    },
    "required": ["answer", "claims"],
}

SURFACE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "inferences": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "text": {"type": "string"},
                "relation": {"type": "string"},
                "link_supported": {"type": "boolean"},
                "link_url": {"type": "string"},
            },
            "required": ["text", "relation", "link_supported", "link_url"],
        }},
    },
    "required": ["inferences"],
}

VERDICT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "verdict": {"type": "string", "enum": ["supported", "unsupported", "unclear"]},
        "note": {"type": "string"},
    },
    "required": ["verdict", "note"],
}

_JUDGE_SYSTEM = (
    "You are a neutral evidence checker. Decide whether the SOURCE supports the CLAIM exactly as "
    "stated. Judge the FULL proposition — if the claim asserts a relationship, ranking, threshold, "
    "or judgment ('therefore', 'because', 'fails the standard', 'stronger than'), the source must "
    "support THAT, not merely an underlying fact. Verdicts: 'supported' (the source substantiates "
    "the whole claim), 'unsupported' (it contradicts the claim or does not substantiate the "
    "load-bearing part), 'unclear' (the source is ambiguous or off-topic). Be factual and "
    "unbiased; report a split honestly. Output the verdict and a one-line note.")


class LLMInterrogator:
    """Persona-conditioned asker: seed questions first, then bounded grounded follow-ups; None on
    saturation (the model replies STOP) or when the follow-up budget is spent."""

    def __init__(self, llm, *, max_followups: int = 1):
        self.llm = llm
        self.max_followups = max_followups

    def ask(self, perspective, context):
        i = len(context)
        seeds = perspective.seed_questions or ()
        if i < len(seeds):
            return seeds[i]
        if i - len(seeds) >= self.max_followups:
            return None  # budget: at most `max_followups` LLM follow-ups per perspective
        last = context[-1] if context else None
        if last is None:
            return None
        system = (f"You are a {perspective.persona}. Ask ONE incisive follow-up question the prior "
                  f"answer left open that a retrievable source could answer. If the topic is "
                  f"saturated, reply with exactly STOP. {_GROUNDING}")
        user = f"Prior question: {last.question}\nPrior answer: {last.answer}\n\nYour single follow-up:"
        q = self.llm.text(system, user, max_tokens=120).strip()
        if not q or q.upper().startswith("STOP"):
            return None
        return q


class LLMExpert:
    """Grounded answerer: cites ONLY the trusted sources; emits typed fact/evaluative claims.

    `subject` = what is being researched ({"name", "description"}). `context` = free background
    that informs the answer but is NOT citable. Claims inherit the perspective's stance and are
    constrained to its anchor_keys. No sources -> no claims (silence != absence).
    """

    def __init__(self, llm, subject: dict, *, context: str = ""):
        self.llm = llm
        self.subject = subject or {}
        self.context = context

    def answer(self, perspective, question, sources):
        name = self.subject.get("name") or "the subject"
        allowed = list(perspective.anchor_keys or ())
        chan = {s.url: s.channel for s in sources}
        if not sources:
            return ("", [])  # silence != absence: no trusted source -> no claim
        srcblock = "\n\n".join(
            f"[SOURCE {i+1}] url={s.url} channel={s.channel}\n{s.text[:2500]}"
            for i, s in enumerate(sources))
        desc = self.subject.get("description", "")
        subject_block = f"SUBJECT UNDER RESEARCH: {name}\n{desc}".strip()
        bg = f"\n\nBACKGROUND (context only, NOT citable):\n{self.context}" if self.context else ""
        system = (
            f"You are a {perspective.persona} researching {name}. Answer the question using ONLY "
            f"the SOURCES provided. Produce atomic findings, each cited to the SOURCE url(s) you "
            f"actually used. kind='fact' for a single verifiable attribute or a cited threshold; "
            f"kind='evaluative' for a judgment — an evaluative claim must cite evidence for the "
            f"FULL judgment. Do NOT assert relationships or 'therefore' inferences as claims (a "
            f"separate pass handles those). anchor_keys MUST be chosen from "
            f"{allowed or ['(none)']}. {_GROUNDING}")
        user = (f"{subject_block}\n\nPerspective rubric: {perspective.rubric or '(none)'}\n"
                f"Question: {question}{bg}\n\nSOURCES:\n{srcblock}\n\n"
                f"Return the answer and the typed, cited claims.")
        out = self.llm.structured(system, user, EXPERT_SCHEMA, max_tokens=1600)
        answer = (out.get("answer") or "").strip()
        claims = []
        for rc in out.get("claims") or []:
            kind = rc.get("kind") if rc.get("kind") in ("fact", "evaluative") else "fact"
            text = (rc.get("text") or "").strip()
            urls = [u for u in (rc.get("evidence_urls") or []) if u in chan]
            if not text or not urls:
                continue  # an uncited claim never ships
            keys = tuple(k for k in (rc.get("anchor_keys") or []) if k in allowed) or tuple(allowed)
            cits = tuple({"claim": text, "url": u, "title": chan[u], "kind": kind,
                          "relation": None, "supports": "fact", "channel": chan[u]} for u in urls)
            claims.append(Claim(kind=kind, text=text, citations=cits,
                                perspective_id=perspective.id, anchor_keys=keys,
                                stance=perspective.stance,
                                rubric_anchor=(rc.get("rubric_anchor") or None) if kind == "evaluative" else None))
        return (answer, claims)


class LLMSurfacer:
    """Forces load-bearing leaps out of prose into relational claims (the over-association catch).

    Surfaced claims carry ONLY antecedent citations unless a source DIRECTLY supports the link
    (supports:"link") — so over-association is structurally unsupported by default and the judge is
    a backstop. Claims inherit the `stance` the engine passes (a refuter's causal bear-case leap
    stays disconfirming and contests its lens).
    """

    def __init__(self, llm):
        self.llm = llm

    def surface(self, body, fact_claims, *, perspective_id, stance="constructive"):
        if not body or not fact_claims:
            return []
        ante = tuple({**c, "supports": "antecedent"} for fc in fact_claims for c in fc.citations)
        valid_urls = {c.get("url") for c in ante}
        out = self.llm.structured(
            ("Identify every load-bearing inference in the passage — any place it claims one fact "
             "IMPLIES, ENABLES, or CAUSES another (a 'therefore', 'because', 'so', 'leading to', or "
             "a causal judgment). For each, return the FULL inferred sentence. Set "
             "link_supported=true and link_url to a provided fact-source url ONLY if that source "
             "DIRECTLY supports the inferred relationship (not merely the component facts); "
             "otherwise link_supported=false."),
            f"Passage:\n{body}\n\nFact-source urls available: {sorted(valid_urls)}",
            SURFACE_SCHEMA, max_tokens=700)
        rels = []
        for inf in out.get("inferences") or []:
            text = (inf.get("text") or "").strip()
            if not text:
                continue
            cits = list(ante)
            if inf.get("link_supported") and inf.get("link_url") in valid_urls:
                link_channel = next((c.get("channel") for c in ante if c.get("url") == inf["link_url"]), None)
                cits = cits + [{"claim": text, "url": inf["link_url"], "title": "link",
                                "kind": "relational", "relation": inf.get("relation"),
                                "supports": "link", "channel": link_channel}]
            keys = tuple(dict.fromkeys(k for fc in fact_claims for k in fc.anchor_keys)) or ()
            rels.append(Claim(kind="relational", text=text,
                              relation=inf.get("relation") or "implies",
                              citations=tuple(cits), perspective_id=perspective_id,
                              anchor_keys=keys, stance=stance,
                              antecedent_ids=tuple(fc.id for fc in fact_claims)))
        return rels

    def detect(self, body):
        """Independent re-detection for the anti-evasion guard (engine.writer)."""
        if not body:
            return []
        out = self.llm.structured(
            ("List every sentence in the passage that asserts one fact implies/enables/causes "
             "another (a relationship or causal judgment, not a bare fact)."),
            f"Passage:\n{body}", SURFACE_SCHEMA, max_tokens=500)
        return [(i.get("text") or "").strip() for i in (out.get("inferences") or []) if i.get("text")]


class EntailmentJudge:
    """Fetch-and-judge VerifyProvider for the ClaimGate. `read_source(url) -> str|None` re-reads
    the cited source; `llm` is the judge role. Both injectable for offline proofs. An unreadable
    or missing source is 'unclear' (silence != absence), never 'unsupported'."""

    def __init__(self, llm, read_source):
        self.llm = llm
        self.read = read_source
        self._page: dict = {}

    def _fetch(self, url: str):
        if url in self._page:
            return self._page[url]
        try:
            text = self.read(url)
        except Exception:
            text = None
        self._page[url] = text
        return text

    def verify(self, claim_text: str, url: str) -> dict:
        page = self._fetch(url)
        if not page:
            return {"verdict": "unclear", "note": "source unfetchable or empty (silence != absence)"}
        user = f"CLAIM: {claim_text}\n\nSOURCE ({url}):\n{page[:7000]}\n\nVerdict?"
        out = self.llm.structured(_JUDGE_SYSTEM, user, VERDICT_SCHEMA, max_tokens=300)
        v = out.get("verdict")
        if v not in ("supported", "unsupported", "unclear"):
            return {"verdict": "unclear", "note": "judge returned no parseable verdict"}
        return {"verdict": v, "note": (out.get("note") or "").strip()}
