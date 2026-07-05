"""
llm/client.py — a model-configurable Anthropic client + token/USD ledger.

One client instance is bound to one model role (interrogator / expert / surfacer / judge are each a
thin prompt over a client), and all roles can share one Ledger. The underlying SDK client is
INJECTABLE, so a deterministic fake drives the offline proofs with zero network — only a live run
imports `anthropic` (install the `stormworthy[anthropic]` extra).

Model ids, pricing, and per-model quirks live in a REGISTRY you can override per call site —
`DEFAULT_MODELS` is a snapshot (verified 2026-07) that will rot; treat it as a default, not truth:
  - structured output: output_config={"format": {"type": "json_schema", "schema": ...}}
  - effort: output_config={"effort": ...} is rejected by some models (effort=None gates it off)
Auth resolves from the environment (ANTHROPIC_API_KEY / ANTHROPIC_AUTH_TOKEN / a logged-in CLI
profile); this module never stores credentials.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

# Default registry: pricing per 1M tokens (input, output); effort=None means the model rejects
# the effort param. Override with your own dict of the same shape.
DEFAULT_MODELS = {
    "haiku":  {"id": "claude-haiku-4-5",  "in": 1.0, "out": 5.0,  "effort": None},
    "sonnet": {"id": "claude-sonnet-4-6", "in": 3.0, "out": 15.0, "effort": "medium"},
    "opus":   {"id": "claude-opus-4-8",   "in": 5.0, "out": 25.0, "effort": "high"},
}


@dataclass
class Ledger:
    """Token + USD accounting across every call (cache reads ~0.1x input price, writes ~1.25x)."""
    calls: int = 0
    in_tok: int = 0
    out_tok: int = 0
    cache_read: int = 0
    cache_write: int = 0
    by_model: dict = field(default_factory=dict)
    usd: float = 0.0

    def add(self, model_key: str, usage, *, in_price: float, out_price: float) -> None:
        it = getattr(usage, "input_tokens", 0) or 0
        ot = getattr(usage, "output_tokens", 0) or 0
        cr = getattr(usage, "cache_read_input_tokens", 0) or 0
        cw = getattr(usage, "cache_creation_input_tokens", 0) or 0
        cost = (it * in_price + ot * out_price + cr * in_price * 0.1 + cw * in_price * 1.25) / 1_000_000
        self.calls += 1
        self.in_tok += it
        self.out_tok += ot
        self.cache_read += cr
        self.cache_write += cw
        self.usd += cost
        b = self.by_model.setdefault(model_key, {"calls": 0, "in": 0, "out": 0, "usd": 0.0})
        b["calls"] += 1
        b["in"] += it
        b["out"] += ot
        b["usd"] += cost

    def summary(self) -> dict:
        return {"calls": self.calls, "in_tok": self.in_tok, "out_tok": self.out_tok,
                "cache_read": self.cache_read, "usd": round(self.usd, 4),
                "by_model": {k: {**v, "usd": round(v["usd"], 4)} for k, v in self.by_model.items()}}


class RoleLLM:
    """A single Anthropic client bound to one model role, sharing a Ledger across roles.

    `text()` returns plain text (e.g. the interrogator's follow-up question). `structured()`
    constrains output to a JSON schema and returns the parsed dict — used for the expert's typed
    claims, the surfacer, and the judge verdict. A refusal returns ""/{} (the caller treats it as
    no output, never as evidence).
    """

    def __init__(self, model_key: str, *, models: "dict | None" = None,
                 ledger: "Ledger | None" = None, client=None, max_tokens: int = 1600):
        registry = models if models is not None else DEFAULT_MODELS
        if model_key not in registry:
            raise ValueError(f"unknown model role {model_key!r}; choose from {list(registry)}")
        spec = registry[model_key]
        self.model_key = model_key
        self.model = spec["id"]
        self.effort = spec.get("effort")
        self.in_price = spec.get("in", 0.0)
        self.out_price = spec.get("out", 0.0)
        self.ledger = ledger if ledger is not None else Ledger()
        self.max_tokens = max_tokens
        self._client = client  # injectable: a deterministic fake for offline proofs

    # -- client / auth ------------------------------------------------------------------------------
    def _c(self):
        if self._client is None:
            import anthropic  # lazy: not needed on the offline stub path
            self._client = anthropic.Anthropic()  # resolves credentials from the environment
        return self._client

    def ping(self) -> str:
        """Cheapest possible auth probe — raises a clear error if credentials aren't resolvable."""
        r = self._c().messages.create(model=self.model, max_tokens=4,
                                      messages=[{"role": "user", "content": "ok"}])
        return getattr(r, "model", self.model)

    def _output_config(self, *, fmt=None) -> "dict | None":
        cfg = {}
        if fmt is not None:
            cfg["format"] = fmt
        if self.effort is not None:
            cfg["effort"] = self.effort  # gated per model (some models reject the param)
        return cfg or None

    def _record(self, r) -> None:
        self.ledger.add(self.model_key, r.usage, in_price=self.in_price, out_price=self.out_price)

    # -- calls --------------------------------------------------------------------------------------
    def text(self, system: str, user: str, *, max_tokens: "int | None" = None) -> str:
        kw = {"model": self.model, "max_tokens": max_tokens or self.max_tokens,
              "system": system, "messages": [{"role": "user", "content": user}]}
        oc = self._output_config()
        if oc:
            kw["output_config"] = oc
        r = self._c().messages.create(**kw)
        self._record(r)
        if getattr(r, "stop_reason", None) == "refusal":
            return ""
        return "".join(b.text for b in r.content if getattr(b, "type", None) == "text").strip()

    def structured(self, system: str, user: str, schema: dict, *,
                   max_tokens: "int | None" = None) -> dict:
        kw = {"model": self.model, "max_tokens": max_tokens or self.max_tokens,
              "system": system, "messages": [{"role": "user", "content": user}],
              "output_config": self._output_config(fmt={"type": "json_schema", "schema": schema})}
        r = self._c().messages.create(**kw)
        self._record(r)
        if getattr(r, "stop_reason", None) == "refusal":
            return {}
        text = next((b.text for b in r.content if getattr(b, "type", None) == "text"), "")
        try:
            return json.loads(text)
        except (ValueError, TypeError):
            return {}
