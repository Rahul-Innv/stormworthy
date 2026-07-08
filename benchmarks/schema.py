"""
benchmarks/schema.py — the gold-set record + loaders, stdlib-only.

A gold record is one claim, its citations, and a human (or oracle) judgment of whether the cited
sources actually support it. Two judge modes read the same record:

  - OracleJudge   — per-citation verdicts come straight from the record's `sources` map. This
                    isolates the GATE POLICY (structural link rule + 3-valued aggregation) from the
                    judge, answering "assuming a perfect per-source judge, how well does the policy
                    classify?". Deterministic, offline, no spend.
  - a live judge  — any `stormworthy.llm` VerifyProvider. Scoring with it measures END-TO-END
                    precision (policy x judge). Same records, harder question.

`gold` is the ground-truth label for the whole claim, in the engine's VERDICTS vocabulary
("supported" | "unsupported" | "unclear"). It is what the gate's prediction is graded against.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from stormworthy.engine.contracts import VERDICTS, Claim


@dataclass(frozen=True)
class GoldRecord:
    id: str
    kind: str                              # fact | relational | evaluative
    text: str
    citations: tuple[dict, ...]            # each: {"url", "supports": fact|antecedent|link, ...}
    sources: dict                          # url -> oracle verdict in VERDICTS (the per-source judge answer)
    gold: str                              # the whole-claim ground-truth label, in VERDICTS
    note: str = ""

    def to_claim(self) -> Claim:
        return Claim(kind=self.kind, text=self.text,
                     citations=tuple(dict(c) for c in self.citations))


def _validate(rec: GoldRecord, line_no: int) -> None:
    if rec.gold not in VERDICTS:
        raise ValueError(f"line {line_no}: gold '{rec.gold}' not in {VERDICTS}")
    for url, v in rec.sources.items():
        if v not in VERDICTS:
            raise ValueError(f"line {line_no}: source verdict '{v}' for {url} not in {VERDICTS}")
    for c in rec.citations:
        if "url" not in c:
            raise ValueError(f"line {line_no}: a citation is missing 'url'")


def load_gold(path: "str | Path") -> "list[GoldRecord]":
    """Load a JSONL gold set. Blank lines and `#`-comment lines are ignored so a set can be
    self-documenting. Every record is validated against the engine's VERDICTS vocabulary."""
    records: "list[GoldRecord]" = []
    for i, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        d = json.loads(line)
        rec = GoldRecord(
            id=d["id"], kind=d["kind"], text=d["text"],
            citations=tuple(d.get("citations", ())), sources=d.get("sources", {}),
            gold=d["gold"], note=d.get("note", ""))
        _validate(rec, i)
        records.append(rec)
    return records


class OracleJudge:
    """A VerifyProvider whose per-source verdicts come from the gold record's `sources` map. An
    unlisted url returns 'unclear' — silence != absence, exactly as a live judge must treat an
    unreadable source."""
    def __init__(self, sources: dict):
        self.sources = sources

    def verify(self, claim_text: str, url: str) -> dict:
        return {"verdict": self.sources.get(url, "unclear"), "note": "oracle"}
