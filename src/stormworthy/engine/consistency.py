"""
engine/consistency.py — the shared self-consistency (recurrence) tier.

A claim earns self-consistency by RECURRING across the K independent runs. This module is the one
reference implementation both adapters previously duplicated, with two lessons folded in at root:

1. The recurrence key is namespaced by STANCE and uses NORMALIZED text (a refuter's same-text
   disconfirming claim must never overwrite the constructive survivor; trivial rewordings still
   recur). `claim_id` is stance-aware too, but keying on normalized text is deliberately looser.

2. Exact/normalized matching UNDER-RECURS on live LLMs: a real expert rewords the same finding
   between runs, so unanimity across K>=2 runs can collapse a report to empty (live-proven).
   Mitigations, in preference order: pass a semantic `key` (embedding/n-gram clustering — injectable
   here precisely for that), lower `quorum` below 1.0 (e.g. 0.5 = majority), or run k=1 (recurrence
   trivially satisfied; the entailment tier still gates every claim).

The function is pure and deterministic given its inputs.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Callable, Hashable

from .contracts import Claim


def norm_text(s: str) -> str:
    """Lowercase, strip non-alphanumerics, collapse whitespace — tolerant of trivial rewordings."""
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in (s or "")).split())


def recurrence_key(c: Claim) -> Hashable:
    """Default recurrence key: (stance, normalized text, sorted citation urls)."""
    urls = tuple(sorted(cc.get("url", "") for cc in (c.citations or ())))
    return (c.stance, norm_text(c.text), urls)


def self_consistency(claims_by_run: "list[list[Claim]]", *,
                     quorum: float = 1.0,
                     key: "Callable[[Claim], Hashable]" = recurrence_key) -> "list[Claim]":
    """Keep claims whose run-presence fraction >= quorum, annotated with that fraction.

    Presence is counted once per run (a claim repeated within one run is one occurrence).
    quorum=1.0 keeps the strict unanimity default; adapters may lower it (see module docstring).
    """
    runs = [r for r in claims_by_run if r is not None]
    n = len(runs) or 1
    seen: "dict[Hashable, int]" = defaultdict(int)
    rep: "dict[Hashable, Claim]" = {}
    for run in runs:
        keys_in_run = set()
        for c in run:
            k = key(c)
            rep.setdefault(k, c)  # first occurrence represents the group (deterministic)
            keys_in_run.add(k)
        for k in keys_in_run:
            seen[k] += 1
    out = []
    for k, count in seen.items():
        frac = count / n
        if frac >= quorum:
            out.append(replace(rep[k], self_consistency=round(frac, 2)))
    return out
