"""The deterministic gate-behavior proof on the fictional Acme Analytics subject.

Runs the REAL framework, the REAL manifest retrieval (over the packaged sample corpus, including
its deliberately-absent doc), and the REAL engine gate/orchestrator — only the three LLM roles are
deterministic stubs from `stormworthy.testing`, parameterized with design-domain content. Offline,
zero network, zero spend. What it proves, in one run:

  - a cited, supported accessibility finding ships vetted at 1.0;
  - the refuter's supported bear-case CONTESTS visual_brand and hard-floors its confidence at 0.1;
  - an over-association leap in conversion_ux (relational claim with only antecedent citations)
    is structurally unsupported — retained + flagged in flag-only, dropped under strict_drop;
  - a second prose leap the writer never surfaced is caught by the anti-evasion guard (per run);
  - the performance lens cites the corpus doc that DOESN'T EXIST -> fetch None, judge silent ->
    the lens abstains (insufficient_evidence, confidence None). Silence != absence, live.
"""
from __future__ import annotations

import os

from ...engine import Claim, ClaimGate, ResearchRun
from ...testing import StubExpert, StubInterrogator, StubSurfacer, StubVerify
from .framework import DesignReviewFramework
from .retrieval import ManifestRetrieval, load_manifest, sample_manifest_path


def build_demo(*, strict_drop: bool = False, k_runs: int = 2):
    """Wire the demo -> (ResearchRun, subject). Callers do `run.research(subject["name"])`."""
    subject, docs = load_manifest(sample_manifest_path())
    p = {os.path.basename(d["path"]): d["path"] for d in docs}  # cite RESOLVED paths, never guess

    def cite(text, url, supports="fact", channel="design_system"):
        return {"claim": text, "url": url, "supports": supports, "channel": channel}

    fact_subject = Claim(
        kind="fact", perspective_id="subject", anchor_keys=("subject",),
        text="Acme Analytics is a fictional B2B dashboard whose primary job is checking pipeline "
             "health and exporting a weekly report.",
        citations=(cite("Acme Analytics is a fictional B2B dashboard whose primary job is "
                        "checking pipeline health and exporting a weekly report.",
                        p["subject-acme.md"]),))

    claim_contrast = Claim(
        kind="evaluative", perspective_id="accessibility", anchor_keys=("accessibility",),
        rubric_anchor="wcag",
        text="Body text at 3.8:1 on the white canvas fails WCAG 2.2 AA contrast — SC 1.4.3 "
             "requires 4.5:1.",
        citations=(cite("SC 1.4.3 requires 4.5:1 for body text.",
                        p["wcag-quick-reference.md"], channel="standard"),
                   cite("Body text is measured at 3.8:1 on the white canvas.",
                        p["subject-acme.md"])))

    claim_targets = Claim(
        kind="evaluative", perspective_id="responsive", anchor_keys=("responsive",),
        rubric_anchor="wcag",
        text="The 20x20 CSS px toolbar targets fall below the 24x24 minimum of SC 2.5.8.",
        citations=(cite("SC 2.5.8 requires pointer targets of at least 24x24 CSS px.",
                        p["wcag-quick-reference.md"], channel="standard"),
                   cite("Toolbar buttons are 20x20 CSS px.", p["subject-acme.md"])))

    claim_nav = Claim(
        kind="evaluative", perspective_id="information_architecture",
        anchor_keys=("information_architecture",), rubric_anchor="heuristics",
        text="The overlapping 'Insights' and 'Analytics' nav labels tax findability — Hick's "
             "law, and consistency demands one meaning per label.",
        citations=(cite("Hick's law: decision time grows with the number and complexity of "
                        "choices.", p["heuristics.md"], channel="kb"),
                   cite("Two of seven nav items overlap in meaning.", p["subject-acme.md"])))

    claim_type = Claim(
        kind="evaluative", perspective_id="visual_brand", anchor_keys=("visual_brand",),
        text="The 18/17/16 px cluster of section heads collapses the hierarchy the brand "
             "guide's locked type scale exists to enforce.",
        citations=(cite("The locked type scale is 12/14/16/20/28/34; adjacent sizes read as no "
                        "hierarchy.", p["brand-guide-acme.md"]),
                   cite("Section heads and labels cluster at 18/17/16 px.",
                        p["subject-acme.md"])))

    fact_fields = Claim(
        kind="fact", perspective_id="conversion_ux", anchor_keys=("conversion_ux",),
        text="The signup form requires nine fields.",
        citations=(cite("The signup form has nine required fields.", p["subject-acme.md"]),))
    fact_cta = Claim(
        kind="fact", perspective_id="conversion_ux", anchor_keys=("conversion_ux",),
        text="The 'Create account' call to action sits below the fold at 1366x768.",
        citations=(cite("The call to action sits below the fold at the reference viewport.",
                        p["subject-acme.md"]),))
    # The over-association leap: both citations only back the ANTECEDENT facts — no source
    # supports the inferred link itself, so no supports:"link" citation exists. Structural catch.
    leap_conversion = Claim(
        kind="relational", perspective_id="conversion_ux", anchor_keys=("conversion_ux",),
        relation="therefore",
        text="The below-the-fold call to action and the nine required fields therefore suppress "
             "signup conversion.",
        citations=(cite("The signup form has nine required fields.", p["subject-acme.md"],
                        supports="antecedent"),
                   cite("The call to action sits below the fold.", p["subject-acme.md"],
                        supports="antecedent")))

    bear_accent = Claim(
        kind="fact", perspective_id="design_risks", anchor_keys=("visual_brand",),
        stance="disconfirming",
        text="The accent teal is used as text on light surfaces, contradicting the brand "
             "guide's own contract reserving it for interactive elements on dark surfaces.",
        citations=(cite("Accent teal is reserved for interactive elements on dark surfaces.",
                        p["brand-guide-acme.md"]),
                   cite("The brand teal is used as text on light surfaces in nav and footer.",
                        p["subject-acme.md"])))

    claim_lcp = Claim(
        kind="fact", perspective_id="performance", anchor_keys=("performance",),
        text="Acme's LCP at p75 exceeds the 2.5 s threshold.",
        citations=(cite("Field LCP measurements.", p["perf-field-data.md"], channel="kb"),))

    conversion_body = (
        "The signup form requires nine fields and the call to action sits below the fold. "
        "The below-the-fold call to action and the nine required fields therefore suppress "
        "signup conversion. Fewer fields would therefore lift completion.")

    expert = StubExpert({
        "subject": ("Acme Analytics is a fictional B2B dashboard.", [fact_subject]),
        "accessibility": ("Body text misses the AA contrast floor.", [claim_contrast]),
        "visual_brand": ("The mid-size type cluster flattens hierarchy.", [claim_type]),
        "information_architecture": ("Two nav labels overlap in meaning.", [claim_nav]),
        "conversion_ux": (conversion_body, [fact_fields, fact_cta]),
        "responsive": ("Toolbar targets are under the minimum.", [claim_targets]),
        "performance": ("No grounded performance basis was found.", [claim_lcp]),
        "design_risks": ("The accent usage contradicts the brand contract.", [bear_accent]),
    })
    surfacer = StubSurfacer(
        surfaced={"conversion_ux": [leap_conversion]},
        detections={"conversion_ux": [
            leap_conversion.text,                            # surfaced -> covered
            "Fewer fields would therefore lift completion",  # left in prose -> evasion, per run
        ]})
    # The judge: the sample docs genuinely back the claims above; the ABSENT perf doc is
    # deliberately unlisted -> StubVerify's default "unclear" (silence != absence).
    gate = ClaimGate(StubVerify(by_url={
        p["subject-acme.md"]: "supported",
        p["wcag-quick-reference.md"]: "supported",
        p["brand-guide-acme.md"]: "supported",
        p["heuristics.md"]: "supported",
    }))
    run = ResearchRun(DesignReviewFramework(), ManifestRetrieval(docs), StubInterrogator({}),
                      expert, surfacer, gate, k_runs=k_runs, max_turns=3,
                      strict_drop=strict_drop)
    return run, subject
