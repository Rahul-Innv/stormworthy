"""End-to-end offline proof: the full pipeline over deterministic stubs, zero network/LLM.

Ports the original gate-proof scenarios onto a domain-neutral subject ("Acme"):
  - a supported fact ships in its lens;
  - an over-association leap (relational claim with only antecedent citations) is structurally
    caught — retained + verdict-flagged in flag-only, dropped from the body under strict-drop;
  - a supported refuter claim contests its target lens and hard-floors confidence;
  - a lens whose only source is unfetchable abstains (insufficient_evidence, confidence None);
  - a prose leap the writer never surfaced is flagged by the anti-evasion guard, per run;
  - conversation log and evasions accumulate across all K runs;
  - the surfacer receives each perspective's stance (the refuter's leaps contest, not construct).
"""
import pytest

from stormworthy.engine import Angle, Claim, ClaimGate, ResearchRun
from stormworthy.testing import (
    StubExpert, StubFramework, StubInterrogator, StubRetrieval, StubSurfacer, StubVerify,
)

K_RUNS = 2

FACT_MARKET = Claim(kind="fact", text="Acme competes with three vendors.",
                    perspective_id="market", anchor_keys=("market",),
                    citations=({"claim": "Acme competes with three vendors.",
                                "url": "src://market/report", "supports": "fact"},))
FACT_TECH = Claim(kind="fact", text="Acme runs a queue-based pipeline.",
                  perspective_id="technology", anchor_keys=("technology",),
                  citations=({"claim": "Acme runs a queue-based pipeline.",
                              "url": "src://tech/docs", "supports": "fact"},))
LEAP_TECH = Claim(kind="relational", text="Acme's queue-based pipeline therefore scales better than rivals.",
                  perspective_id="technology", anchor_keys=("technology",), relation="therefore",
                  citations=({"claim": "Acme's queue-based pipeline therefore scales better than rivals.",
                              "url": "src://tech/docs", "supports": "antecedent"},))
FACT_SUBJECT = Claim(kind="fact", text="Acme sells widgets.",
                     perspective_id="subject", anchor_keys=("subject",),
                     citations=({"claim": "Acme sells widgets.",
                                 "url": "src://about", "supports": "fact"},))
FACT_UPTIME = Claim(kind="fact", text="Acme has 99.99% uptime.",
                    perspective_id="reliability", anchor_keys=("reliability",),
                    citations=({"claim": "Acme has 99.99% uptime.",
                                "url": "src://reliability/blog", "supports": "fact"},))
BEAR_PRICING = Claim(kind="fact", text="Acme's pricing page contradicts its rate card.",
                     stance="disconfirming", perspective_id="risks", anchor_keys=("market",),
                     citations=({"claim": "Acme's pricing page contradicts its rate card.",
                                 "url": "src://risk/pricing", "supports": "fact"},))

TECH_BODY = ("Acme runs a queue-based pipeline. It therefore scales better than rivals. "
             "The queue also cuts operating costs.")


def _framework():
    def angle(id, anchor, key, kind="framework", question="q?"):
        return Angle(id=id, title=f"{id} analyst", anchor=anchor, question=question,
                     kind=kind, anchor_keys=(key,))
    return StubFramework(
        [angle("a-competitors", "Market — competitors", "market", question="Who competes with Acme?"),
         angle("a-pricing", "Market — pricing", "market", question="How is Acme priced?"),
         angle("a-stack", "Technology — stack", "technology", question="What does Acme run on?"),
         angle("a-uptime", "Reliability — uptime", "reliability", question="Is Acme reliable?")],
        angle("subject", "Subject", "subject", kind="basic_fact", question="What is Acme?"),
        angle("risks", "Risks", "risks", kind="refuter", question="What breaks the thesis?"),
    )


def _run(strict_drop=False):
    retrieval = StubRetrieval(
        corpus={"src://about": "Acme sells widgets.",
                "src://market/report": "Acme competes with three vendors.",
                "src://tech/docs": "Acme runs a queue-based pipeline.",
                "src://risk/pricing": "The pricing page contradicts the rate card.",
                "src://reliability/blog": None},  # unfetchable -> absent
        refs_by_query={"What is Acme?": ["src://about"],
                       "Who competes with Acme?": ["src://market/report"],
                       "How is Acme priced?": ["src://market/report"],
                       "What does Acme run on?": ["src://tech/docs"],
                       "Is Acme reliable?": ["src://reliability/blog"],
                       "What breaks the thesis?": ["src://risk/pricing"]})
    expert = StubExpert({
        "subject": ("Acme sells widgets.", [FACT_SUBJECT]),
        "market": ("Acme competes with three vendors.", [FACT_MARKET]),
        "technology": (TECH_BODY, [FACT_TECH]),
        "reliability": ("Uptime claims could not be grounded.", [FACT_UPTIME]),
        "risks": ("The pricing page contradicts the rate card.", [BEAR_PRICING]),
    })
    surfacer = StubSurfacer(
        surfaced={"technology": [LEAP_TECH]},
        detections={"technology": [
            "Acme's queue-based pipeline therefore scales better than rivals",
            "the queue also cuts operating costs",  # left in prose, never surfaced -> evasion
        ]})
    gate = ClaimGate(StubVerify(by_url={"src://about": "supported",
                                        "src://market/report": "supported",
                                        "src://tech/docs": "supported",
                                        "src://risk/pricing": "supported"}))
    run = ResearchRun(_framework(), retrieval, StubInterrogator({}), expert, surfacer, gate,
                      k_runs=K_RUNS, max_turns=3, strict_drop=strict_drop)
    return run.research("acme"), surfacer


@pytest.fixture(scope="module")
def dossier_and_surfacer():
    return _run(strict_drop=False)


def _section(dossier, lens):
    return next(s for s in dossier.sections if s.anchor == lens)


def test_supported_fact_ships(dossier_and_surfacer):
    dossier, _ = dossier_and_surfacer
    subject = _section(dossier, "subject")
    assert subject.status == "filled" and subject.vetted and subject.confidence == 1.0


def test_over_association_caught_flag_only_keeps_and_flags(dossier_and_surfacer):
    dossier, _ = dossier_and_surfacer
    tech = _section(dossier, "technology")
    leap = next(c for c in tech.claims if c.kind == "relational")
    assert leap.entailment["verdict"] == "unsupported"   # structural: only antecedent citations
    assert leap.text in tech.body                         # flag-only: retained, not silently dropped
    assert tech.vetted is True                            # 1 of 2 supported = 0.5 >= min_support


def test_strict_drop_removes_the_leap_from_the_body():
    dossier, _ = _run(strict_drop=True)
    tech = _section(dossier, "technology")
    assert "therefore scales better" not in tech.body
    assert "queue-based pipeline" in tech.body            # the supported fact stays


def test_refuter_contests_market_and_floors_confidence(dossier_and_surfacer):
    dossier, _ = dossier_and_surfacer
    market = _section(dossier, "market")
    assert market.contested is True and market.confidence == 0.1


def test_unfetchable_source_lens_abstains(dossier_and_surfacer):
    dossier, _ = dossier_and_surfacer
    reliability = _section(dossier, "reliability")
    assert reliability.status == "insufficient_evidence"
    assert reliability.confidence is None                 # abstain — never 0.0


def test_evasions_accumulate_across_k_runs(dossier_and_surfacer):
    dossier, _ = dossier_and_surfacer
    assert len(dossier.evasions) == K_RUNS                # one unsurfaced leap per run
    assert all(e["perspective"] == "technology" for e in dossier.evasions)


def test_conversation_log_accumulates_across_k_runs(dossier_and_surfacer):
    dossier, _ = dossier_and_surfacer
    # per run: subject 1 + market 2 + technology 1 + reliability 1 + risks 1 = 6 turns
    assert len(dossier.conversation_log) == 6 * K_RUNS


def test_surfacer_received_each_perspectives_stance(dossier_and_surfacer):
    _, surfacer = dossier_and_surfacer
    assert surfacer.stance_seen["risks"] == "disconfirming"
    assert surfacer.stance_seen["technology"] == "constructive"
