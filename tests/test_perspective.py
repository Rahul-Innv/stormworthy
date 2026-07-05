"""Part 1 invariants: pinning, family de-dup, refuter key expansion, determinism."""
from stormworthy.engine import Angle, design_perspectives, family_of
from stormworthy.testing import StubFramework


def _angle(id, anchor, key, kind="framework", question="q?"):
    return Angle(id=id, title=f"{id} title", anchor=anchor, question=question,
                 kind=kind, anchor_keys=(key,))


BASIC = _angle("subject", "Subject", "subject", kind="basic_fact", question="What is it?")
REFUTER = _angle("risks", "Risks", "risks", kind="refuter", question="What breaks it?")


def _spec(framework_angles):
    return StubFramework(framework_angles, BASIC, REFUTER)


def test_basic_fact_first_refuter_last_never_merged():
    ps = design_perspectives(_spec([_angle("a1", "Market — competitors", "market")]))
    kinds = [p.kind for p in ps.perspectives]
    assert kinds[0] == "basic_fact"
    assert kinds[-1] == "refuter"


def test_family_dedup_merges_same_family_angles():
    ps = design_perspectives(_spec([
        _angle("a1", "Market — competitors", "market", question="Who competes?"),
        _angle("a2", "Market — five forces", "market", question="Five forces?"),
        _angle("a3", "Technology — stack", "technology"),
    ]))
    framework = [p for p in ps.perspectives if p.kind == "framework"]
    assert len(framework) == 2  # Market merged, Technology separate
    market = next(p for p in framework if p.anchor == "Market")
    assert market.seed_questions == ("Who competes?", "Five forces?")


def test_refuter_contests_every_framework_lens():
    ps = design_perspectives(_spec([
        _angle("a1", "Market — competitors", "market"),
        _angle("a3", "Technology — stack", "technology"),
    ]))
    refuter = ps.perspectives[-1]
    assert refuter.stance == "disconfirming"
    assert set(refuter.anchor_keys) == {"risks", "market", "technology"}


def test_deterministic():
    spec = _spec([_angle("a1", "Market — competitors", "market")])
    assert design_perspectives(spec) == design_perspectives(spec)


def test_custom_separators():
    assert family_of("Market :: pricing", (" :: ",)) == "Market"
    ps = design_perspectives(
        _spec([_angle("a1", "Market :: competitors", "market"),
               _angle("a2", "Market :: pricing", "market")]),
        separators=(" :: ",))
    framework = [p for p in ps.perspectives if p.kind == "framework"]
    assert len(framework) == 1  # merged under the custom separator convention
