"""ClaimGate: the structural link rule, 3-valued aggregation, optional corroboration."""
from stormworthy.engine import Claim, ClaimGate
from stormworthy.testing import StubVerify


def _fact(url, supports="fact"):
    return Claim(kind="fact", text="Acme uses a queue.",
                 citations=({"claim": "Acme uses a queue.", "url": url, "supports": supports},))


def test_relational_without_link_citation_is_structurally_unsupported():
    """No judge can rescue an uncited inference — the over-association catch."""
    judge = StubVerify(by_url={"u1": "supported"})  # judge WOULD say supported
    gate = ClaimGate(judge)
    claim = Claim(kind="relational", text="queue therefore scales",
                  citations=({"claim": "queue therefore scales", "url": "u1", "supports": "antecedent"},))
    v = gate.entailment(claim)
    assert v["verdict"] == "unsupported"
    assert judge.calls == []  # structural: the judge was never consulted


def test_relational_with_link_citation_reaches_the_judge():
    gate = ClaimGate(StubVerify(by_url={"u1": "supported"}))
    claim = Claim(kind="relational", text="queue therefore scales",
                  citations=({"claim": "queue therefore scales", "url": "u1", "supports": "link"},))
    assert gate.entailment(claim)["verdict"] == "supported"


def test_supported_when_fraction_meets_min_support():
    gate = ClaimGate(StubVerify(by_url={"u1": "supported"}))
    assert gate.entailment(_fact("u1"))["verdict"] == "supported"


def test_short_of_support_but_uncontradicted_is_unclear_not_unsupported():
    """Silence != absence: 'we could not confirm' must never read as 'the source says no'."""
    gate = ClaimGate(StubVerify())  # stub default verdict: unclear
    assert gate.entailment(_fact("unknown://source"))["verdict"] == "unclear"


def test_contradiction_is_unsupported():
    gate = ClaimGate(StubVerify(by_url={"u1": "unsupported"}))
    assert gate.entailment(_fact("u1"))["verdict"] == "unsupported"


def test_no_citations_is_unsupported():
    gate = ClaimGate(StubVerify())
    assert gate.entailment(Claim(kind="fact", text="uncited"))["verdict"] == "unsupported"


def test_corroboration_optional_tier_off_by_default():
    gate = ClaimGate(StubVerify())
    assert gate.corroboration(_fact("u1")) is None


def test_corroboration_two_channels_full():
    gate = ClaimGate(StubVerify(), corroborate=True)
    claim = Claim(kind="fact", text="x", citations=(
        {"claim": "x", "url": "u1", "channel": "web"},
        {"claim": "x", "url": "u2", "channel": "docs"},
    ))
    assert gate.corroboration(claim) == 1.0
