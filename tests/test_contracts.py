"""Identity + typing invariants on the data model."""
from stormworthy.engine import Claim, claim_id


def test_claim_id_is_deterministic_and_order_insensitive():
    a = claim_id("fact", "Acme uses Postgres.", ["u1", "u2"])
    b = claim_id("fact", "Acme uses Postgres.", ["u2", "u1"])
    assert a == b
    assert len(a) == 16


def test_claim_id_is_stance_aware():
    """A refuter's same-text disconfirming claim must never collide with the constructive one."""
    constructive = Claim(kind="fact", text="Body text fails AA contrast.")
    disconfirming = Claim(kind="fact", text="Body text fails AA contrast.", stance="disconfirming")
    assert constructive.id != disconfirming.id


def test_is_inference_marks_the_over_association_surface():
    assert not Claim(kind="fact", text="x").is_inference
    assert Claim(kind="relational", text="x => y").is_inference
    assert Claim(kind="evaluative", text="x is strong").is_inference
