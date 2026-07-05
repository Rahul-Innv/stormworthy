"""Live-shape proof: the REAL LLM roles + client driven through a fake Anthropic client.

No network, no `anthropic` import — proves the live code paths (structured output plumbing, effort
gating, ledger math, claim construction, stance inheritance, judge verdicts) without spend.
"""
from stormworthy.engine import Claim, ClaimGate, Perspective, Source
from stormworthy.llm import (
    EntailmentJudge, Ledger, LLMExpert, LLMInterrogator, LLMSurfacer, RoleLLM,
)
from stormworthy.testing import FakeClient

MODELS = {"cheap": {"id": "model-cheap", "in": 1.0, "out": 5.0, "effort": None},
          "smart": {"id": "model-smart", "in": 5.0, "out": 25.0, "effort": "high"}}

PERSPECTIVE = Perspective(id="market", persona="Market analyst", anchor="Market",
                          kind="framework", seed_questions=("Who competes?",),
                          anchor_keys=("market",), stance="constructive")
REFUTER = Perspective(id="risks", persona="Skeptic", anchor="Risks", kind="refuter",
                      seed_questions=("What breaks it?",), anchor_keys=("market",),
                      stance="disconfirming")
SOURCES = [Source(url="src://report", title="report", text="Acme competes with three vendors.",
                  channel="docs", trust=0.9)]


def _llm(fake, key="cheap", ledger=None):
    return RoleLLM(key, models=MODELS, client=fake, ledger=ledger)


def test_ledger_math_and_effort_gating():
    ledger = Ledger()
    fake = FakeClient()
    _llm(fake, "cheap", ledger).text("s", "u")
    _llm(fake, "smart", ledger).text("s", "u")
    # cheap: (1000*1 + 500*5)/1e6 ; smart: (1000*5 + 500*25)/1e6
    assert round(ledger.usd, 6) == round((3500 + 17500) / 1e6, 6)
    assert ledger.calls == 2
    assert "output_config" not in fake.calls[0]          # effort None -> no config at all
    assert fake.calls[1]["output_config"]["effort"] == "high"


def test_expert_builds_stance_inherited_cited_claims_and_drops_uncited():
    fake = FakeClient(by_schema_prop={"claims": {
        "answer": "Acme competes with three vendors.",
        "claims": [
            {"kind": "fact", "text": "Acme competes with three vendors.",
             "evidence_urls": ["src://report"], "anchor_keys": ["market", "not-allowed"],
             "rubric_anchor": ""},
            {"kind": "fact", "text": "Uncited claim.", "evidence_urls": [],
             "anchor_keys": ["market"], "rubric_anchor": ""},
        ]}})
    expert = LLMExpert(_llm(fake), {"name": "Acme", "description": "widgets"})
    answer, claims = expert.answer(REFUTER, "Who competes?", SOURCES)
    assert answer and len(claims) == 1                    # the uncited claim never ships
    [c] = claims
    assert c.stance == "disconfirming"                    # inherits the perspective's stance
    assert c.anchor_keys == ("market",)                   # filtered to the allowed keys
    assert c.citations[0]["url"] == "src://report"


def test_expert_no_sources_no_claims():
    expert = LLMExpert(_llm(FakeClient()), {"name": "Acme"})
    assert expert.answer(PERSPECTIVE, "q?", []) == ("", [])


def test_surfacer_inherits_stance_and_unlinked_leap_is_structurally_unsupported():
    fact = Claim(kind="fact", text="Acme uses a queue.", perspective_id="risks",
                 anchor_keys=("market",), stance="disconfirming",
                 citations=({"claim": "Acme uses a queue.", "url": "src://report",
                             "supports": "fact", "channel": "docs"},))
    fake = FakeClient(by_schema_prop={"inferences": {
        "inferences": [{"text": "The queue therefore beats rivals.", "relation": "therefore",
                        "link_supported": False, "link_url": ""}]}})
    [leap] = LLMSurfacer(_llm(fake)).surface(
        "body", [fact], perspective_id="risks", stance="disconfirming")
    assert leap.stance == "disconfirming"                 # engine-passed stance, not inferred
    assert all(c["supports"] == "antecedent" for c in leap.citations)
    gate = ClaimGate(verify_provider=None)                # never consulted: structural rule fires
    assert gate.entailment(leap)["verdict"] == "unsupported"


def test_judge_silence_is_unclear_and_verdict_parses():
    fake = FakeClient(by_schema_prop={"verdict": {"verdict": "supported", "note": "backs it"}})
    judge = EntailmentJudge(_llm(fake), read_source=lambda url: None)
    assert judge.verify("claim", "src://x")["verdict"] == "unclear"   # silence != absence
    judge2 = EntailmentJudge(_llm(fake), read_source=lambda url: "source text")
    assert judge2.verify("claim", "src://x")["verdict"] == "supported"


def test_interrogator_seeds_then_stop_then_budget():
    fake = FakeClient(text_reply="STOP")
    asker = LLMInterrogator(_llm(fake), max_followups=1)
    assert asker.ask(PERSPECTIVE, []) == "Who competes?"  # seed first, no LLM call
    from stormworthy.engine import Turn
    turn = Turn(question="Who competes?", answer="Three vendors.", claims=(), sources=())
    assert asker.ask(PERSPECTIVE, [turn]) is None         # model said STOP -> saturation
