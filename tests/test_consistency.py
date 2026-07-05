"""Self-consistency tier: stance namespacing, normalization, quorum, injectable key."""
from stormworthy.engine import Claim, norm_text, recurrence_key, self_consistency


def _c(text, stance="constructive", kind="fact"):
    return Claim(kind=kind, text=text, stance=stance)


def test_same_text_constructive_and_refuter_both_survive():
    """The F5 scenario: the refuter restates a finding — both stances must survive unanimity."""
    run = [_c("Body text fails AA."), _c("Body text fails AA.", stance="disconfirming")]
    out = self_consistency([run, list(run)])
    assert len(out) == 2
    assert {c.stance for c in out} == {"constructive", "disconfirming"}


def test_trivial_rewording_still_recurs():
    out = self_consistency([[_c("Body text FAILS  AA!")], [_c("body text fails aa")]])
    assert len(out) == 1
    assert out[0].self_consistency == 1.0


def test_unanimity_drops_a_one_run_claim_and_quorum_keeps_it():
    runs = [[_c("only in run one")], []]
    assert self_consistency(runs) == []                       # quorum 1.0 (unanimity)
    kept = self_consistency(runs, quorum=0.5)                 # majority-of-2
    assert len(kept) == 1 and kept[0].self_consistency == 0.5


def test_run_presence_counted_once_per_run():
    """A claim repeated within one run must not fake recurrence across runs."""
    runs = [[_c("dup"), _c("dup")], []]
    assert self_consistency(runs) == []


def test_injectable_semantic_key():
    """A paraphrase-tolerant key (here: crude first-word bucket) plugs in without engine changes."""
    def first_word_key(c):
        return (c.stance, norm_text(c.text).split()[0])
    runs = [[_c("contrast is too low on body text")], [_c("contrast fails the AA floor")]]
    assert self_consistency(runs) == []                       # default key: no recurrence
    out = self_consistency(runs, key=first_word_key)
    assert len(out) == 1                                       # semantic key: recurs


def test_default_key_includes_citations():
    a = _c("same text")
    assert recurrence_key(a) == ("constructive", "same text", ())
