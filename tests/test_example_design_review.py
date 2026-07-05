"""The worked design-review example: manifest loading, framework invariants, retrieval semantics,
the end-to-end offline demo (every gate behavior on the fictional Acme Analytics subject), and
live-roles compatibility via the fake client. Zero network."""
import json
import os

import pytest

from stormworthy.engine import design_perspectives
from stormworthy.examples.design_review import (
    CHANNEL_TRUST, CWV_RUBRIC, HEURISTICS_RUBRIC, LENSES, WCAG_RUBRIC,
    DesignReviewFramework, ManifestRetrieval, build_demo, load_manifest, sample_manifest_path,
)
from stormworthy.examples.design_review.retrieval import _read_file
from stormworthy.llm import EntailmentJudge, LLMExpert, RoleLLM
from stormworthy.testing import FakeClient

MODELS = {"cheap": {"id": "model-cheap", "in": 1.0, "out": 5.0, "effort": None}}


# --- manifest / corpus -----------------------------------------------------------------------------

def test_sample_manifest_loads():
    subject, docs = load_manifest(sample_manifest_path())
    assert subject["name"] == "Acme Analytics dashboard"
    assert len(docs) == 7
    assert all(d["channel"] in CHANNEL_TRUST for d in docs)
    assert all(os.path.isabs(d["path"]) for d in docs)


def test_manifest_relative_paths_resolve_against_manifest_dir(tmp_path):
    (tmp_path / "doc.md").write_text("content", encoding="utf-8")
    manifest = tmp_path / "m.json"
    manifest.write_text(json.dumps({
        "subject": {"name": "X"},
        "docs": [{"path": "doc.md", "channel": "kb", "title": "d", "tags": ""}]}),
        encoding="utf-8")
    _, docs = load_manifest(str(manifest))
    assert docs[0]["path"] == str(tmp_path / "doc.md")


def test_manifest_validation_errors(tmp_path):
    def write(payload):
        p = tmp_path / "m.json"
        p.write_text(json.dumps(payload), encoding="utf-8")
        return str(p)

    with pytest.raises(ValueError, match="subject.name"):
        load_manifest(write({"docs": [{"path": "a", "channel": "kb"}]}))
    with pytest.raises(ValueError, match="non-empty"):
        load_manifest(write({"subject": {"name": "X"}, "docs": []}))
    with pytest.raises(ValueError, match="docs\\[0\\] needs"):
        load_manifest(write({"subject": {"name": "X"}, "docs": [{"channel": "kb"}]}))
    with pytest.raises(ValueError, match="channel 'nope'"):
        load_manifest(write({"subject": {"name": "X"},
                             "docs": [{"path": "a", "channel": "nope"}]}))


# --- framework invariants ---------------------------------------------------------------------------

def test_framework_shape_6_plus_2():
    ps = design_perspectives(DesignReviewFramework())
    assert len(ps.perspectives) == 8
    assert ps.perspectives[0].kind == "basic_fact" and ps.perspectives[0].id == "subject"
    assert ps.perspectives[-1].kind == "refuter" and ps.perspectives[-1].id == "design_risks"
    assert ps.perspectives[-1].stance == "disconfirming"


def test_refuter_contests_every_lens():
    refuter = design_perspectives(DesignReviewFramework()).perspectives[-1]
    assert set(refuter.anchor_keys) >= set(LENSES) | {"design_risks"}


def test_anchor_families_slug_to_lens_ids():
    # The engine derives perspective ids by slugging the anchor family; the documented lens keys
    # must equal those ids exactly, or role wiring keyed by id silently misses.
    ps = design_perspectives(DesignReviewFramework())
    framework_ids = [p.id for p in ps.perspectives if p.kind == "framework"]
    assert framework_ids == list(LENSES)


def test_rubrics_carry_real_thresholds():
    assert "4.5:1" in WCAG_RUBRIC["contrast"] and "24x24" in WCAG_RUBRIC["targets"]
    assert "2.5" in CWV_RUBRIC["thresholds"] and "200" in CWV_RUBRIC["thresholds"] \
        and "0.1" in CWV_RUBRIC["thresholds"]
    assert "Nielsen" in HEURISTICS_RUBRIC["set"]


# --- retrieval semantics ----------------------------------------------------------------------------

def test_search_deterministic_and_channel_preferred():
    _, docs = load_manifest(sample_manifest_path())
    r = ManifestRetrieval(docs)
    a = r.search("zzz-no-term-overlap", k=3, perspective_id="accessibility")
    b = r.search("zzz-no-term-overlap", k=3, perspective_id="accessibility")
    assert [x.url for x in a] == [x.url for x in b]      # deterministic
    assert a[0].channel == "standard"                     # accessibility prefers standards


def test_fetch_absent_returns_none_and_caches():
    _, docs = load_manifest(sample_manifest_path())
    calls = []

    def read(url):
        calls.append(url)
        return None  # everything absent

    r = ManifestRetrieval(docs, read=read)
    [ref] = r.search("field data measurements", k=1, perspective_id="performance")
    assert r.fetch(ref) is None
    assert r.fetch(ref) is None
    assert len(calls) == 1                                # the None was cached: no re-probe


def test_trust_by_channel_and_cap():
    _, docs = load_manifest(sample_manifest_path())
    r = ManifestRetrieval(docs, cap=10)
    ref = next(x for x in r.search("wcag contrast criterion", k=7,
                                   perspective_id="accessibility")
               if x.url.endswith("wcag-quick-reference.md"))
    src = r.fetch(ref)
    assert len(src.text) <= 10                            # truncated to cap
    assert r.trust(src) == 0.98                           # standard channel
    trend = next(x for x in r.search("trends inspiration mood", k=7,
                                     perspective_id="visual_brand")
                 if x.url.endswith("trend-notes.md"))
    assert r.trust(r.fetch(trend)) == 0.60                # reference channel


# --- the end-to-end offline demo ---------------------------------------------------------------------

@pytest.fixture(scope="module")
def demo_dossier():
    run, subject = build_demo()
    return run.research(subject["name"])


def _section(dossier, lens):
    return next(s for s in dossier.sections if s.anchor == lens)


def test_demo_offline_verdict_mix(demo_dossier):
    d = demo_dossier
    assert {s.anchor for s in d.sections} == set(LENSES) | {"subject"}

    a11y = _section(d, "accessibility")
    assert a11y.vetted and a11y.confidence == 1.0

    brand = _section(d, "visual_brand")
    assert brand.contested and brand.confidence == 0.1    # refuter's supported bear-case floors it

    conv = _section(d, "conversion_ux")
    leap = next(c for c in conv.claims if c.kind == "relational")
    assert leap.entailment["verdict"] == "unsupported"    # structural: antecedent-only citations
    assert leap.text in conv.body                          # flag-only: retained, never silently cut
    assert conv.vetted                                     # 2 of 3 supported >= min_support

    perf = _section(d, "performance")
    assert perf.status == "insufficient_evidence"
    assert perf.confidence is None                         # abstain is None, never 0.0

    assert len(d.evasions) == 2                            # the unsurfaced leap, once per k-run
    assert all(e["perspective"] == "conversion_ux" for e in d.evasions)


def test_demo_strict_drop_removes_flagged_leap():
    run, subject = build_demo(strict_drop=True)
    conv = _section(run.research(subject["name"]), "conversion_ux")
    assert "therefore suppress" not in conv.body           # the leap is dropped from the body
    assert "nine fields" in conv.body                       # the supported facts stay


# --- live-roles compatibility (fake client, zero network) --------------------------------------------

def test_live_roles_over_sample_corpus_with_fake_client():
    subject, docs = load_manifest(sample_manifest_path())
    retrieval = ManifestRetrieval(docs)
    a11y = next(p for p in design_perspectives(DesignReviewFramework()).perspectives
                if p.id == "accessibility")
    refs = retrieval.search(a11y.seed_questions[0], k=3, perspective_id=a11y.id)
    sources = [s for s in (retrieval.fetch(r) for r in refs) if s is not None]
    wcag_url = next(s.url for s in sources if s.url.endswith("wcag-quick-reference.md"))

    fake = FakeClient(by_schema_prop={"claims": {
        "answer": "Body text misses the AA contrast floor.",
        "claims": [{"kind": "evaluative",
                    "text": "Body text contrast fails WCAG 2.2 SC 1.4.3.",
                    "evidence_urls": [wcag_url], "anchor_keys": ["accessibility"],
                    "rubric_anchor": "wcag"}]}})
    expert = LLMExpert(RoleLLM("cheap", models=MODELS, client=fake), subject)
    answer, claims = expert.answer(a11y, a11y.seed_questions[0], sources)
    assert answer and len(claims) == 1
    [claim] = claims
    assert claim.anchor_keys == ("accessibility",)
    assert claim.citations[0]["url"] == wcag_url           # cites the real packaged corpus file

    judge_fake = FakeClient(by_schema_prop={"verdict": {"verdict": "supported", "note": "backs"}})
    judge = EntailmentJudge(RoleLLM("cheap", models=MODELS, client=judge_fake), _read_file)
    assert judge.verify(claim.text, wcag_url)["verdict"] == "supported"
    assert judge.verify(claim.text, wcag_url + ".missing")["verdict"] == "unclear"
