"""A complete worked adapter: verified design review over a local corpus.

Six analytical lenses with real rubrics (WCAG 2.2 AA, Core Web Vitals, named usability
heuristics), a corpus-manifest-driven retrieval adapter, and a deterministic offline demo that
exercises every gate behavior on a fictional subject. Copy `framework.py` + `retrieval.py` as
the starting point for your own domain adapter.

Try it:  python -m stormworthy.examples.design_review --demo
"""
from .demo import build_demo
from .framework import (
    CWV_RUBRIC,
    HEURISTICS_RUBRIC,
    LENSES,
    WCAG_RUBRIC,
    DesignReviewFramework,
)
from .retrieval import (
    CHANNEL_TRUST,
    PREFERRED_CHANNELS,
    ManifestRetrieval,
    load_manifest,
    sample_manifest_path,
)

__all__ = [
    "CHANNEL_TRUST",
    "CWV_RUBRIC",
    "DesignReviewFramework",
    "HEURISTICS_RUBRIC",
    "LENSES",
    "ManifestRetrieval",
    "PREFERRED_CHANNELS",
    "WCAG_RUBRIC",
    "build_demo",
    "load_manifest",
    "sample_manifest_path",
]
