"""Gate orchestration honesty rules: fusion, abstain, contest floor, strict-drop vs flag-only."""
from stormworthy.engine import Claim, ClaimGate, assemble_sections, score_claims
from stormworthy.testing import StubVerify


def _fact(text, url, *, stance="constructive", keys=("lens",)):
    return Claim(kind="fact", text=text, stance=stance, anchor_keys=keys,
                 citations=({"claim": text, "url": url, "supports": "fact"},))


def _score(claims, verdict_by_url, **gate_kw):
    gate = ClaimGate(StubVerify(by_url=verdict_by_url), **gate_kw)
    return score_claims([claims, list(claims)], gate)  # K=2, identical runs


def test_fusion_supported_times_consistency_times_optional_tier():
    scored = _score([_fact("a", "u1")], {"u1": "supported"})
    assert scored[0].confidence == 1.0          # 1.0 (supported) x 1.0 (unanimous) x 1.0 (corr None)
    assert scored[0].self_consistency == 1.0


def test_fusion_unclear_scores_point_four():
    scored = _score([_fact("a", "u-unknown")], {})
    assert scored[0].confidence == 0.4


def test_abstain_is_confidence_none_not_zero():
    scored = _score([_fact("a", "u1")], {"u1": "unsupported"})
    [section] = assemble_sections(scored, strict_drop=False)
    assert section.status == "insufficient_evidence"
    assert section.confidence is None           # abstain, never 0.0
    assert section.vetted is False


def test_supported_refuter_contests_and_hard_floors():
    claims = [_fact("finding", "u1"),
              _fact("bear case", "u2", stance="disconfirming")]
    scored = _score(claims, {"u1": "supported", "u2": "supported"})
    [section] = assemble_sections(scored, strict_drop=False)
    assert section.contested is True
    assert section.confidence == 0.1            # hard floor, never averaged
    assert len(section.contesting_claims) == 1


def test_contested_floor_is_configurable():
    claims = [_fact("finding", "u1"),
              _fact("bear case", "u2", stance="disconfirming")]
    scored = _score(claims, {"u1": "supported", "u2": "supported"})
    [section] = assemble_sections(scored, strict_drop=False, contested_floor=0.25)
    assert section.confidence == 0.25


def test_unsupported_refuter_does_not_contest():
    claims = [_fact("finding", "u1"),
              _fact("weak bear case", "u2", stance="disconfirming")]
    scored = _score(claims, {"u1": "supported", "u2": "unsupported"})
    [section] = assemble_sections(scored, strict_drop=False)
    assert section.contested is False


def test_flag_only_keeps_unsupported_body_strict_drop_removes_it():
    claims = [_fact("good", "u1"), _fact("bad", "u2")]
    scored = _score(claims, {"u1": "supported", "u2": "unsupported"})
    [flag_only] = assemble_sections(scored, strict_drop=False)
    [strict] = assemble_sections(scored, strict_drop=True)
    assert "bad" in flag_only.body and "bad" not in strict.body
    assert "good" in strict.body


def test_min_support_gates_vetted():
    claims = [_fact("good", "u1"), _fact("bad", "u2")]
    scored = _score(claims, {"u1": "supported", "u2": "unsupported"})
    [section] = assemble_sections(scored, strict_drop=False, min_support=0.6)
    assert section.status == "filled" and section.vetted is False   # 1/2 = 0.5 < 0.6
    [ok] = assemble_sections(scored, strict_drop=False, min_support=0.5)
    assert ok.vetted is True
