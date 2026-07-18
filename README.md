<p align="center">
  <img src="docs/assets/logo.png" alt="StormWorthy logo" width="180">
</p>

# StormWorthy

[![pipeline status](https://gitlab.com/krahul02004/stormworthy/badges/main/pipeline.svg)](https://gitlab.com/krahul02004/stormworthy/-/commits/main)
[![PyPI version](https://img.shields.io/pypi/v/stormworthy)](https://pypi.org/project/stormworthy/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**A perspective-guided, source-grounded research engine with a mandatory claim-level verification gate.**

> ⚠️ Alpha status. API may change before 1.0.

StormWorthy researches a subject through multiple non-overlapping analyst personas (including an
always-on adversarial refuter), grounds every answer in fetched sources, forces every load-bearing
inference into a typed claim, verifies each claim against its cited sources, and assembles a
dossier whose sections carry calibrated confidence, and abstain honestly when the evidence
isn't there.

It is a native re-implementation of the research method behind Stanford's
[STORM](https://arxiv.org/abs/2402.14207) (perspective-guided question asking + grounded
writer↔expert conversations), plus the layer that method lacks: **verification inside the writer,
not after it**.

## Getting started

- **Prerequisites:** Python 3.10 or newer. The engine is standard library only, with zero runtime dependencies.
- **Install:** `pip install stormworthy` (engine plus stubs). See [Install](#install) for the editable-from-clone setup and the optional live LLM extra.
- **Check it works:** run `python -m stormworthy.examples.design_review --demo`. It runs the bundled offline design-review demo (no API key, no network) and prints a per-lens verification table that ends with `evasions caught: 2`. The full walkthrough is in [A worked example: design review](#a-worked-example-design-review).

## Why another research agent?

The open research pipelines I surveyed (Stanford STORM, GPT-Researcher, LangChain deep
research, July 2026) treat "cite as you write" as the guarantee: the generation side never
checks the claims it emits, and verification-side tools (claim benchmarks, citation auditors)
run outside the generator, after the report exists. The best-documented failure mode sits
exactly between them: **individually-true facts woven into an unsupported relationship**: what
the STORM paper itself calls improper inferential linking.

StormWorthy's answer, mechanically:

| Mechanism | What it does |
|---|---|
| **Typed claims** | Every assertion is `fact`, `relational` (X ⟹ Y), or `evaluative`. The gate verifies the FULL proposition (the link, the judgment), never a sub-span. |
| **Structural link rule** | A relational claim with no citation tagged `supports:"link"` is unsupported no matter what any judge says. Inherited antecedent citations don't count. |
| **Anti-evasion guard** | An independent pass re-detects inferences left in prose; a leap that was never surfaced as a claim fails its section. Omission is strictly worse than surfacing. |
| **3-tier gate** | Self-consistency across K independent runs (mandatory) → entailment against the actual fetched source (mandatory) → cross-channel corroboration (optional). Fused multiplicatively. |
| **Adversarial refuter** | A pinned disconfirming persona interrogates every lens. A *supported* refuter claim marks the section contested and hard-floors its confidence (drops it to the fixed 0.1 contested floor), never averaged away. |
| **Honest abstention** | A lens with no supported constructive claim ships as `insufficient_evidence` with confidence `None`: not a generated-anyway section, not a fake 0.0. |
| **Silence ≠ absence** | A source that fails to fetch is recorded as absent evidence: it lowers confidence and can never be fabricated; "we couldn't confirm" never becomes "the source says no". |
| **Deterministic replay** | Claim ids are content hashes (no clock, no RNG); the perspective design is pure. Same inputs, same artifact. |

The engine is ~600 lines of stdlib-only Python: zero dependencies. Everything model- or
domain-shaped is injected through six `typing.Protocol`s, which is how the same engine has already
shipped two very different domains (company research and design briefs).

## Honest validation status

Read this before trusting the output. The gate's *architecture* is tested; its *precision* is not
yet benchmarked:

- **Flag-only is the default and the only supported mode.** `strict_drop` (silently removing
  unsupported claims from the shipped body) is a precision claim that must be **earned** on a
  hand-rated gold set (Wilson lower bound ≥ 0.80 on the predicted-unsupported class). The scoring
  harness is real and runnable today ([`benchmarks/`](benchmarks/), `python benchmarks/score.py`),
  but the bar has **not** been cleared on a real gold set yet, so unsupported claims are retained
  *and flagged*, never silently deleted, and never silently trusted.
- The full pipeline is proven **offline** by deterministic-stub proofs and a fake-client
  live-shape suite (this repo's tests; no network, no spend). **Live** validation so far is
  small-scale smoke runs.
- Claim-level verification is genuinely hard (human experts score ~61% one-shot in recent
  benchmarks). The [`benchmarks/`](benchmarks/) harness scores the real gate against a gold set and
  reports Wilson-bounded precision per class; a headline number will be published once a real
  hand-rated gold set is populated. Until then, treat verdicts as a strong prior, not ground truth.
- Known limitation: with `k_runs ≥ 2`, the default (lexical) recurrence matcher under-recurs on
  live LLMs that reword findings between runs: use `k_runs=1`, lower the `quorum`, or inject a
  semantic recurrence key (`self_consistency(key=...)` is injectable for exactly this).

## Install

From PyPI:

```bash
pip install stormworthy               # engine + stubs, zero runtime deps
pip install "stormworthy[anthropic]"  # + the reference live LLM layer
```

Or editable from a clone:

```bash
pip install -e .[dev]       # + pytest
```

Python ≥ 3.10.

## Quickstart (offline, no API key)

The test suite doubles as the reference wiring; here is a complete run you can paste as-is, using
stub adapters over an in-memory corpus to drive the real engine and gate:

```python
from stormworthy.engine import Angle, Claim, ClaimGate, ResearchRun
from stormworthy.testing import (StubExpert, StubFramework, StubInterrogator,
                                 StubRetrieval, StubSurfacer, StubVerify)

# 1. Your domain = a FrameworkSpec: framework angles + a basic-fact baseline + a refuter.
#    Angles use "Family: detail" anchors; same family merges into one analyst.
framework = StubFramework(
    [Angle(id="a-stack", title="Tech analyst", anchor="Technology: stack",
           question="What does Acme run on?", kind="framework", anchor_keys=("technology",))],
    Angle(id="subject", title="Baseline", anchor="Subject", question="What is Acme?",
          kind="basic_fact", anchor_keys=("subject",)),
    Angle(id="risks", title="Refuter", anchor="Risks", question="What breaks the thesis?",
          kind="refuter", anchor_keys=("risks",)),
)

# 2. Retrieval = search/fetch/trust over your corpus (fetch -> None means ABSENT).
retrieval = StubRetrieval(corpus={"src://about": "Acme sells widgets.",
                                  "src://tech": "Acme runs a queue-based pipeline."})

# 3. Claims cite their sources; the gate needs only a
#    verify(claim_text, url) -> {"verdict": ...} provider to check them.
fact = Claim(kind="fact", text="Acme runs a queue-based pipeline.",
             perspective_id="technology", anchor_keys=("technology",),
             citations=({"claim": "Acme runs a queue-based pipeline.",
                         "url": "src://tech", "supports": "fact"},))
baseline = Claim(kind="fact", text="Acme sells widgets.",
                 perspective_id="subject", anchor_keys=("subject",),
                 citations=({"claim": "Acme sells widgets.",
                             "url": "src://about", "supports": "fact"},))
expert = StubExpert({"technology": ("Acme runs a queue-based pipeline.", [fact]),
                     "subject": ("Acme sells widgets.", [baseline])})
gate = ClaimGate(StubVerify(by_url={"src://tech": "supported", "src://about": "supported"}))

run = ResearchRun(framework, retrieval, StubInterrogator({}), expert, StubSurfacer(),
                  gate, k_runs=1)
dossier = run.research("acme")
for s in dossier.sections:
    print(s.anchor, s.status, s.confidence, "CONTESTED" if s.contested else "")
# prints one line per lens (row order varies between runs):
#   subject filled 1.0
#   technology filled 1.0
```

The refuter found nothing to contest here; see `tests/test_provider.py` for the full end-to-end
scenario (contestation, abstention, the anti-evasion guard), and `src/stormworthy/llm/` for the
live Anthropic-backed roles (bring your own `ANTHROPIC_API_KEY`).

## Writing an adapter

An adapter is six small implementations (two are often reusable as-is from `stormworthy.llm`):

| Protocol | Job | Typical size |
|---|---|---|
| `FrameworkSpec` | your domain's taxonomy → angles, rubrics, basic-fact + refuter floor | ~100 LOC |
| `RetrievalAdapter` | search → fetch → trust over your corpus | ~100 LOC |
| `VerificationGate` | use `ClaimGate` + a `verify` provider | ~0 (shipped) |
| `Interrogator` / `Expert` / `InferenceSurfacer` | use `stormworthy.llm` roles | ~0 (shipped) |

Rules your adapter must keep (they are the quality): the refuter and basic-fact perspectives stay
pinned; an uncited claim never ships; abstains carry no weight downstream (an abstained lens is
missing evidence, not a low-confidence finding); a domain-specific acceptance gate (house style,
register, compliance) stays sovereign over anything this engine emits. Dossier findings are
constraints, not taste: they bound what you may claim, not how you say it.

`None` is load-bearing in three places (each means something different, and none of them means
"error"): `RetrievalAdapter.fetch -> None` means the source is absent (don't fabricate, don't
retry-forever); `Interrogator.ask -> None` means the perspective is saturated (stop the
conversation early, cleanly); `VerificationGate.corroboration -> None` means the optional third
tier is not running (a two-tier gate, the right call when you have no independence model).

## A worked example: design review

A complete second-domain adapter ships in the package,
[`stormworthy.examples.design_review`](src/stormworthy/examples/design_review/): six review
lenses (accessibility, visual brand, information architecture, conversion UX, responsive,
performance) with real rubrics (WCAG 2.2 success criteria, Core Web Vitals thresholds, named
usability heuristics), a corpus-manifest-driven retrieval adapter, and a deterministic offline
demo:

```bash
python -m stormworthy.examples.design_review --demo
```

One run, every gate behavior on a fictional subject. Real output from a run of this demo
(annotations added; row order varies between runs):

```text
lens                         status                    conf  flags
accessibility                filled                    1.00           # cited + entailed -> ships vetted at 1.0
responsive                   filled                    1.00           # WCAG SC 2.5.8 target-size finding, verified
information_architecture     filled                    1.00
subject                      filled                    1.00           # the pinned basic-fact baseline
conversion_ux                filled                    1.00  1 flagged # over-association leap: no supports:"link" cite -> unsupported, retained + flagged
visual_brand                 filled                    0.10  CONTESTED # refuter's SUPPORTED bear-case hard-floors the lens
performance                  insufficient_evidence     None            # its one source doesn't fetch -> abstain, not a guess
evasions caught: 2                                                     # a prose leap never surfaced as a claim, caught per run
```

The uniform 1.00s are a property of the synthetic offline corpus (every stub citation entails
perfectly), not a claim about live accuracy. Each row is a distinct honesty rule firing: a
supported finding ships vetted at 1.0; the refuter's supported bear-case marks a lens contested
at the 0.1 floor (never averaged away); the over-association leap is structurally flagged (and
dropped under `--strict-drop`); an unsurfaced prose leap is caught by the anti-evasion guard;
and the lens whose only source doesn't exist abstains at confidence `None`: silence, not a
fabricated answer.

Honest framing: the rubrics are real, but the sample corpus is illustrative original prose and
the subject is **fictional**: the demo proves the verification mechanism; it is not a
validated design-review product. Copy `framework.py` + `retrieval.py` as the starting point for
your own domain, and point `--live` at your own corpus manifest.

## Use as a Claude Code plugin

The same repo installs as a [Claude Code](https://claude.com/claude-code) plugin: a skill that
wires the pipeline for you and consumes the dossier honestly (supported findings as constraints,
contested sections surfaced, abstains carrying no weight). In Claude Code:

```
/plugin marketplace add https://gitlab.com/krahul02004/stormworthy.git
/plugin install stormworthy@stormworthy
```

Then ask for "a verified research brief on X", or see
[`skills/stormworthy/SKILL.md`](skills/stormworthy/SKILL.md) for what the skill does.

## Attribution

The perspective-guided grounded-conversation method is from **STORM** (Shao et al., NAACL 2024,
[arXiv:2402.14207](https://arxiv.org/abs/2402.14207)) and **Co-STORM**
([arXiv:2408.15232](https://arxiv.org/abs/2408.15232)) by Stanford OVAL. This project is an
independent, from-scratch implementation (it does not use or depend on the `knowledge-storm`
package) and is not affiliated with or endorsed by Stanford. The claim typing, structural link
rule, anti-evasion guard, refuter contestation, abstention semantics, and the in-loop
verification gate are original to this project.

## License

MIT. See [LICENSE](LICENSE).
