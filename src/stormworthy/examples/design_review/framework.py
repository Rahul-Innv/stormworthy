"""The design-review FrameworkSpec: six analytical dimensions + the mandatory archetype floor.

This is a complete reference FrameworkSpec (~100 lines of substance). The six dimensions carry
REAL rubrics — WCAG 2.2 success criteria, Core Web Vitals thresholds, named usability heuristics —
because a lens whose rubric is vibes produces claims no gate can check. The panel must cite a
threshold or a named principle, or the claim is unsupported.

Anchor convention gotcha (learned the hard way): the engine derives each framework perspective's
id by slugging the anchor FAMILY (the text before the em-dash). The families below are chosen so
the slug equals the documented lens key exactly — "Conversion UX" slugs to `conversion_ux`. If you
write "Conversion & UX" the id becomes `conversion___ux` and your role wiring silently misses.
A test locks this coupling.
"""
from __future__ import annotations

from ...engine.contracts import Angle

# --- shared rubrics: the thresholds the panel must cite -------------------------------------------

WCAG_RUBRIC = {
    "levels": {"A": "must", "AA": "target (the contract)", "AAA": "aspire"},
    "contrast": "text 4.5:1 / large text 3:1 / UI components + focus indicators 3:1 "
                "(WCAG 2.2 SC 1.4.3, 1.4.11) — computed, no rounding",
    "targets": "pointer targets >= 24x24 CSS px (SC 2.5.8); 44px is the AAA / platform-HIG bar",
    "reflow": "content reflows at 320 CSS px width / 400% zoom without 2-D scrolling (SC 1.4.10)",
    "motion": "provide a reduced-motion variant; <= 3 flashes per second; pause/stop/hide for "
              "anything that moves longer than 5s",
    "rule": "cite the specific success criterion; an untested contrast/label/target claim is "
            "unsupported.",
}

CWV_RUBRIC = {
    "thresholds": "LCP <= 2.5s / INP <= 200ms / CLS <= 0.1, all at p75",
    "rule": "reserve media/font dimensions; a performance claim needs a measured or cited basis, "
            "not a guess.",
}

HEURISTICS_RUBRIC = {
    "set": "Nielsen's 10 usability heuristics + Norman affordance/signifier/feedback + "
           "Hick / Fitts / Miller",
    "rule": "name the heuristic and tie the finding to it; 'looks off' is not a finding.",
}

# --- the six dimensions ----------------------------------------------------------------------------

LENSES = ("accessibility", "visual_brand", "information_architecture",
          "conversion_ux", "responsive", "performance")


def _angle(id, anchor, question, rubric):
    return Angle(id=id, title=f"{anchor.split('—')[0].strip()} analyst", anchor=anchor,
                 question=question, kind="framework", rubric=rubric, anchor_keys=(id,))


_ANGLES = (
    _angle("accessibility",
           "Accessibility — WCAG 2.2 conformance and inclusive interaction",
           "Where does this design meet or fail WCAG 2.2 AA — contrast, keyboard operability, "
           "focus order and visibility, semantics and labels, target size, reduced motion — and "
           "what is the specific success criterion for each finding?",
           "Cite the specific WCAG success criterion and threshold for each finding (see the "
           "wcag shared rubric). Contrast, label, and target claims must reference a computed "
           "value or a cited standard, never a guess."),
    _angle("visual_brand",
           "Visual brand — hierarchy, typography, color, restraint",
           "Does the visual system establish a clear hierarchy and a coherent, on-register brand "
           "voice — typographic scale, color and restraint, spacing rhythm, one signature — and "
           "where does it read generic, cluttered, or off-register?",
           "Ground each judgment in a cited craft principle or the project's own brand/tokens "
           "documentation; prefer positive distinctiveness derived from the brand over a generic "
           "'clean' ideal."),
    _angle("information_architecture",
           "Information architecture — navigation, findability, labeling",
           "Is the content structured so users can find and understand what they need — "
           "navigation model, grouping, labeling, progressive disclosure — and where do labels, "
           "depth, or ordering create confusion?",
           "Tie findings to an IA or labeling principle (Hick's law, recognition over recall, "
           "plain language); cite the reference or the project's own IA documentation."),
    _angle("conversion_ux",
           "Conversion UX — task flow, friction, honest affordances",
           "For the primary job-to-be-done, where is friction, ambiguity, or a dishonest "
           "affordance in the task flow — steps, defaults, states (empty/loading/error), "
           "feedback — and what raises or lowers completion?",
           "Map each finding to a usability heuristic (see the heuristics shared rubric) or a "
           "cited flow principle; affordance-honesty issues (a control that lies about what it "
           "does) are high severity."),
    _angle("responsive",
           "Responsive — breakpoints, reflow, target size",
           "Does the layout hold across breakpoints and inputs — no overflow or overlap, targets "
           ">= 24 CSS px, survives 200% zoom and SC 1.4.10 reflow, longest real copy — and where "
           "does it break on small or large viewports?",
           "Cite the responsive/target/zoom criterion (WCAG 1.4.10 reflow, 2.5.8 target size); a "
           "layout claim must reference the breakpoint and the real content width."),
    _angle("performance",
           "Performance — Core Web Vitals and perceived speed",
           "Where does the design threaten Core Web Vitals or perceived speed — the LCP element, "
           "layout-shift sources, asset and font weight, blocking work, reserved dimensions — "
           "and what is the cited threshold or measured basis?",
           "Cite the CWV threshold (see the cwv shared rubric); a performance claim needs a "
           "measured number or a cited web-performance principle, not an assertion."),
)

# --- the mandatory archetype floor ------------------------------------------------------------------

_BASIC_FACT = Angle(
    id="subject", title="Design-subject desk researcher",
    anchor="Design subject — what this product, page, or flow is",
    question="What is this product, page, or flow, verifiably: its primary job-to-be-done, its "
             "intended users, its brand register, its stated constraints, and what the current UI "
             "actually contains (surfaces, key components, states)?",
    kind="basic_fact", anchor_keys=("subject",),
    rubric="NEUTRAL, VERIFIABLE description grounded in the provided subject brief and design "
           "documentation. No recommendations here — establish the ground truth the other lenses "
           "build on.")

_REFUTER = Angle(
    id="design_risks", title="Adversarial usability critic (bear-case)",
    anchor="Design risk — the strongest evidenced case this design fails its users",
    question="What is the strongest EVIDENCED case that this design fails its users? Sweep the "
             "heuristic set and the accessibility/performance floors for the highest-severity, "
             "load-bearing failures — including any risk both unaddressed and unowned by a "
             "constructive lens.",
    kind="refuter", anchor_keys=("design_risks",),
    rubric="Attack the DESIGN, PATTERNS, and DECISIONS — never a named person. Map each risk to "
           "a cited heuristic or standard (see the shared rubrics); an unfounded 'this is bad' "
           "is not a refutation.")


class DesignReviewFramework:
    """FrameworkSpec for design review: 6 lenses + basic-fact baseline + adversarial refuter."""

    def framework_id(self) -> str:
        return "design-review-example-v1"

    def angles(self) -> "list[Angle]":
        return list(_ANGLES)

    def shared_rubrics(self) -> dict:
        return {"wcag": WCAG_RUBRIC, "cwv": CWV_RUBRIC, "heuristics": HEURISTICS_RUBRIC}

    def basic_fact_angle(self) -> Angle:
        return _BASIC_FACT

    def archetype_floor(self) -> "list[Angle]":
        return [_BASIC_FACT, _REFUTER]
