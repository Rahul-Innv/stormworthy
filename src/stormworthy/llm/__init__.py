"""Reference LLM layer: an Anthropic client with cost ledger + the injected roles as thin prompts.

The engine never imports this package — it is one (optional) way to satisfy the engine's injected
Protocols. Requires the `stormworthy[anthropic]` extra for live runs; every class also accepts an
injected fake client so the full live code path is testable offline.
"""
from .client import DEFAULT_MODELS, Ledger, RoleLLM
from .roles import (
    EXPERT_SCHEMA,
    SURFACE_SCHEMA,
    VERDICT_SCHEMA,
    EntailmentJudge,
    LLMExpert,
    LLMInterrogator,
    LLMSurfacer,
)

__all__ = [
    "DEFAULT_MODELS", "Ledger", "RoleLLM",
    "EXPERT_SCHEMA", "SURFACE_SCHEMA", "VERDICT_SCHEMA",
    "EntailmentJudge", "LLMExpert", "LLMInterrogator", "LLMSurfacer",
]
