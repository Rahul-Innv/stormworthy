"""A fake Anthropic client for live-shape proofs — real LLM roles, zero network, zero spend.

Drives the REAL `stormworthy.llm` code paths (structured-output plumbing, effort gating, ledger
math, claim construction, stance inheritance, judge verdicts) without importing `anthropic`.
Inject it as `RoleLLM(..., client=FakeClient(...))`.
"""
import json


class _Usage:
    input_tokens = 1000
    output_tokens = 500
    cache_read_input_tokens = 0
    cache_creation_input_tokens = 0


class _Block:
    type = "text"

    def __init__(self, text):
        self.text = text


class _Response:
    stop_reason = "end_turn"
    usage = _Usage()

    def __init__(self, text, model):
        self.content = [_Block(text)]
        self.model = model


class FakeClient:
    """Returns scripted payloads; routes by which JSON schema the call requested.

    `by_schema_prop` maps a property name that appears in the requested output schema to the
    payload to return (JSON-encoded into the response text). Calls without a schema get
    `text_reply`. Every call's kwargs are recorded on `self.calls` for assertions.
    """

    def __init__(self, by_schema_prop=None, text_reply="ok"):
        self.by_schema_prop = by_schema_prop or {}
        self.text_reply = text_reply
        self.calls = []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        fmt = (kw.get("output_config") or {}).get("format")
        if fmt is None:
            return _Response(self.text_reply, kw["model"])
        props = set(fmt["schema"].get("properties", {}))
        for prop, payload in self.by_schema_prop.items():
            if prop in props:
                return _Response(json.dumps(payload), kw["model"])
        return _Response("{}", kw["model"])
