"""Manifest-driven local-corpus RetrievalAdapter (~100 lines of substance, stdlib-only).

The corpus is a user-supplied JSON manifest — a subject plus a list of docs, each tagged with a
CHANNEL that carries its trustworthiness (a published standard outranks the project's own notes,
which outrank mood-board material). Nothing is hardcoded: point `load_manifest` at your own file.

Semantics the engine relies on (Protocol contract):
  - `search` is deterministic: same query, same ranking (term overlap, then the perspective's
    preferred channels, then trust, then url — no RNG, no clock).
  - `fetch` returning None means ABSENT (file missing/unreadable/empty). The gate treats absence
    as "we could not look", never as "the source says no" (silence != absence). The None is
    cached so one run never re-probes a dead source.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Callable, Optional

from ...engine.contracts import Source, SourceRef

# Trust by channel: how authoritative a doc is, independent of any query.
CHANNEL_TRUST = {
    "standard": 0.98,       # published standards: WCAG, platform HIG, web.dev
    "kb": 0.90,             # your own verified knowledge base
    "design_system": 0.90,  # the project's own tokens / brand guide / component contracts
    "reference": 0.60,      # inspiration and north-star notes — NOT specification
    "web": 0.50,            # unvetted web material
}

# Which channels each perspective hears from first (ties broken toward these).
PREFERRED_CHANNELS = {
    "accessibility": ("standard", "kb"),
    "visual_brand": ("design_system", "reference"),
    "information_architecture": ("kb", "reference"),
    "conversion_ux": ("kb", "reference"),
    "responsive": ("standard", "design_system"),
    "performance": ("standard", "kb"),
    "subject": ("design_system", "kb"),
    "design_risks": ("standard", "kb"),
}


def sample_manifest_path() -> str:
    """Path to the packaged sample corpus manifest (fictional subject, original prose)."""
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "sample_corpus", "manifest.json")


def load_manifest(path: str, *, allowed_channels: "Optional[tuple[str, ...]]" = None):
    """Load and validate a corpus manifest -> (subject, docs).

    Schema: {"subject": {"name": str, "description": str},
             "docs": [{"path"|"url": str, "channel": str, "title": str, "tags": str}, ...]}
    Relative doc paths resolve against the manifest file's own directory. Unknown extra keys are
    tolerated. Violations raise ValueError naming the offending entry — fail fast, not mid-run.
    """
    allowed = tuple(allowed_channels or CHANNEL_TRUST)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    subject = data.get("subject") or {}
    if not subject.get("name"):
        raise ValueError(f"manifest {path!r}: subject.name is required")
    docs = data.get("docs")
    if not isinstance(docs, list) or not docs:
        raise ValueError(f"manifest {path!r}: docs must be a non-empty list")
    base = os.path.dirname(os.path.abspath(path))
    out = []
    for i, d in enumerate(docs):
        loc = d.get("path") or d.get("url")
        if not loc:
            raise ValueError(f"manifest {path!r}: docs[{i}] needs a 'path' or 'url'")
        if d.get("channel") not in allowed:
            raise ValueError(f"manifest {path!r}: docs[{i}] channel {d.get('channel')!r} not in "
                             f"{sorted(allowed)}")
        entry = dict(d)
        if d.get("path") and not os.path.isabs(d["path"]):
            entry["path"] = os.path.normpath(os.path.join(base, d["path"]))
        entry.setdefault("title", os.path.basename(loc))
        entry.setdefault("tags", "")
        out.append(entry)
    return subject, out


def _read_file(url: str) -> Optional[str]:
    try:
        with open(url, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return None
    return text or None  # empty is as useless as missing


_WORDS = re.compile(r"[a-z0-9]+")


class ManifestRetrieval:
    """RetrievalAdapter over a validated manifest doc list."""

    def __init__(self, docs: "list[dict]", *,
                 read: "Optional[Callable[[str], Optional[str]]]" = None,
                 trust_by_channel: "Optional[dict[str, float]]" = None,
                 preferred: "Optional[dict[str, tuple[str, ...]]]" = None,
                 cap: int = 6000):
        self.docs = list(docs)
        self.read = read or _read_file
        self.trust_by_channel = dict(trust_by_channel or CHANNEL_TRUST)
        self.preferred = dict(preferred or PREFERRED_CHANNELS)
        self.cap = cap
        self._cache: "dict[str, Optional[Source]]" = {}

    def _url(self, d: dict) -> str:
        return d.get("path") or d.get("url", "")

    def search(self, query: str, *, k: int, perspective_id: str) -> "list[SourceRef]":
        terms = set(_WORDS.findall(query.lower()))
        prefs = self.preferred.get(perspective_id, ())

        def rank(d):
            hay = " ".join([d.get("title", ""), d.get("tags", ""), d.get("channel", ""),
                            self._url(d)]).lower()
            overlap = len(terms & set(_WORDS.findall(hay)))
            pref = prefs.index(d["channel"]) if d.get("channel") in prefs else len(prefs)
            trust = self.trust_by_channel.get(d.get("channel"), 0.5)
            return (-overlap, pref, -trust, self._url(d))

        return [SourceRef(url=self._url(d), title=d.get("title"), channel=d.get("channel"))
                for d in sorted(self.docs, key=rank)[:k]]

    def fetch(self, ref: SourceRef) -> Optional[Source]:
        if ref.url in self._cache:
            return self._cache[ref.url]  # None is cached too: never re-probe a dead source
        text = self.read(ref.url)
        if text is None:
            src = None  # ABSENT — never fabricate
        else:
            text = text[: self.cap]
            src = Source(url=ref.url, title=ref.title, text=text, channel=ref.channel,
                         trust=self.trust_by_channel.get(ref.channel, 0.5),
                         content_hash=hashlib.sha256(text.encode("utf-8")).hexdigest()[:16])
        self._cache[ref.url] = src
        return src

    def trust(self, src: Source) -> float:
        return self.trust_by_channel.get(src.channel, 0.5)
