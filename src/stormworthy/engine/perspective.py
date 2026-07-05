"""
engine/perspective.py — Part 1: the Perspective Designer (portable, stdlib-only).

Turns a FrameworkSpec into a de-duplicated PerspectiveSet:
  - framework angles are grouped by their anchor FAMILY (the text before the first separator),
    so overlapping angles (e.g. competitors + Porter's Five Forces) collapse into ONE coherent
    analyst — the de-dup step classic STORM omits;
  - the archetype floor (the mandatory "+1" basic-fact baseline and the adversarial refuter) is
    PINNED: basic-fact first, refuter last, never merged out;
  - the refuter's anchor_keys are expanded to contest every framework lens.

Anchor convention: angles use "Family — detail" anchors (em-dash, en-dash, or " - " as the
separator — see ANCHOR_SEPARATORS, overridable per call). Angles whose anchors share a family are
merged into one perspective; an anchor with no separator is its own family, so de-dup degrades to
per-angle perspectives if the convention is not used.

Deterministic + pure (sorted/insertion-ordered, no RNG) so the same FrameworkSpec yields the same set.
"""
from __future__ import annotations

from collections import OrderedDict

from .contracts import Angle, FrameworkSpec, Perspective, PerspectiveSet

ANCHOR_SEPARATORS = ("—", "–", " - ")  # em-dash, en-dash, " - "


def family_of(anchor: str, separators: "tuple[str, ...]" = ANCHOR_SEPARATORS) -> str:
    """The anchor family: the text before the first separator (else the whole anchor)."""
    for sep in separators:
        if sep in anchor:
            return anchor.split(sep)[0].strip()
    return anchor.strip()


def _slug(text: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in text).strip("_") or "x"


def design_perspectives(spec: FrameworkSpec, *,
                        separators: "tuple[str, ...]" = ANCHOR_SEPARATORS) -> PerspectiveSet:
    framework_angles = [a for a in spec.angles() if a.kind == "framework"]
    floor = spec.archetype_floor()
    basics = [a for a in floor if a.kind == "basic_fact"]
    refuters = [a for a in floor if a.kind == "refuter"]

    perspectives: list[Perspective] = []

    # 1) pinned "+1" basic-fact baseline (first)
    for a in basics:
        perspectives.append(Perspective(
            id=a.id, persona=a.title, anchor=a.anchor, kind="basic_fact",
            seed_questions=(a.question,), rubric=a.rubric, anchor_keys=a.anchor_keys,
            stance="constructive"))

    # 2) framework personas, grouped by framework-section family (the de-dup step)
    groups: "OrderedDict[str, list[Angle]]" = OrderedDict()
    for a in framework_angles:
        groups.setdefault(family_of(a.anchor, separators), []).append(a)
    for family, angles in groups.items():
        keys = tuple(dict.fromkeys(k for a in angles for k in (a.anchor_keys or (a.id,))))
        rubric = " | ".join(r for r in (a.rubric for a in angles) if r) or None
        perspectives.append(Perspective(
            id=_slug(family), persona=f"{family} analyst", anchor=family, kind="framework",
            seed_questions=tuple(a.question for a in angles), rubric=rubric,
            anchor_keys=keys, stance="constructive"))

    # 3) pinned refuter (last) — owns its anchor_keys AND contests every framework lens
    all_keys = tuple(dict.fromkeys(k for a in framework_angles for k in (a.anchor_keys or (a.id,))))
    for a in refuters:
        perspectives.append(Perspective(
            id=a.id, persona=a.title, anchor=a.anchor, kind="refuter",
            seed_questions=(a.question,), rubric=a.rubric,
            anchor_keys=tuple(dict.fromkeys(a.anchor_keys + all_keys)), stance="disconfirming"))

    return PerspectiveSet(framework_id=spec.framework_id(),
                          perspectives=tuple(perspectives),
                          shared_rubrics=spec.shared_rubrics())
