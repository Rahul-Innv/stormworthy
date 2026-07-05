"""Deterministic stub implementations of every adapter Protocol — the engine's offline test kit.

These run the ENTIRE pipeline with zero network and zero LLM spend. They exist for three audiences:
the engine's own test suite, adapter authors proving their wiring before paying for a live run, and
CI. Every stub is configurable per-test; none contains domain content.
"""
from .fake_client import FakeClient
from .stubs import (
    StubExpert,
    StubFramework,
    StubInterrogator,
    StubRetrieval,
    StubSurfacer,
    StubVerify,
)

__all__ = [
    "FakeClient",
    "StubExpert",
    "StubFramework",
    "StubInterrogator",
    "StubRetrieval",
    "StubSurfacer",
    "StubVerify",
]
