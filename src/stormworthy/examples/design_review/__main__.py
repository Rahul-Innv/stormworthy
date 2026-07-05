"""Run the design-review example.

Offline demo (no network, no keys, no deps):
    python -m stormworthy.examples.design_review --demo [--strict-drop] [-o out.json]

Live run over YOUR corpus manifest (needs `pip install stormworthy[anthropic]` + an API key):
    python -m stormworthy.examples.design_review path/to/manifest.json --live [-o out.json]
"""
from __future__ import annotations

import argparse
import json
import sys


def render(dossier) -> dict:
    """Down-project a Dossier to the shipped JSON shape (same shape as the skill's run template)."""
    return {
        "subject": dossier.entity_id,
        "sections": [{
            "lens": s.anchor, "status": s.status, "headline": s.headline,
            "body": s.body,
            "confidence": s.confidence, "contested": s.contested,
            "contesting_claims": list(s.contesting_claims),
            "claims": [{
                "kind": c.kind, "text": c.text, "stance": c.stance,
                "verdict": (c.entailment or {}).get("verdict"),
                "confidence": c.confidence,
                "citations": [{"url": cc.get("url"), "title": cc.get("title")}
                              for cc in c.citations],
            } for c in s.claims],
        } for s in dossier.sections],
        "evasions": list(dossier.evasions),
    }


def _table(out: dict) -> str:
    rows = [f"{'lens':<28} {'status':<24} {'conf':>5}  flags"]
    for s in out["sections"]:
        conf = "None" if s["confidence"] is None else f"{s['confidence']:.2f}"
        flags = []
        if s["contested"]:
            flags.append("CONTESTED")
        n_flagged = sum(1 for c in s["claims"] if c["verdict"] == "unsupported")
        if n_flagged:
            flags.append(f"{n_flagged} flagged")
        rows.append(f"{s['lens']:<28} {s['status']:<24} {conf:>5}  {', '.join(flags)}")
    rows.append(f"evasions caught: {len(out['evasions'])}")
    return "\n".join(rows)


def _demo(args) -> dict:
    from .demo import build_demo
    run, subject = build_demo(strict_drop=args.strict_drop)
    return render(run.research(subject["name"]))


def _live(args) -> dict:
    # Lazy imports: the anthropic extra is only needed on this path.
    from ...engine import ClaimGate, ResearchRun
    from ...llm import EntailmentJudge, Ledger, LLMExpert, LLMInterrogator, LLMSurfacer, RoleLLM
    from .framework import DesignReviewFramework
    from .retrieval import ManifestRetrieval, _read_file, load_manifest

    subject, docs = load_manifest(args.manifest)
    ledger = Ledger()
    roles = RoleLLM("sonnet", ledger=ledger)
    judge = RoleLLM("opus", ledger=ledger)
    roles.ping()  # fail fast on auth, before any spend
    run = ResearchRun(
        DesignReviewFramework(), ManifestRetrieval(docs),
        LLMInterrogator(roles), LLMExpert(roles, subject), LLMSurfacer(roles),
        ClaimGate(EntailmentJudge(judge, _read_file)),
        k_runs=1,           # k>=2 needs a semantic recurrence key or quorum < 1.0 (see LESSONS)
        max_turns=2, strict_drop=False)
    out = render(run.research(subject["name"]))
    out["ledger"] = ledger.summary()
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="stormworthy.examples.design_review",
                                 description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest", nargs="?", help="corpus manifest JSON (for --live)")
    ap.add_argument("--demo", action="store_true", help="offline demo on the sample corpus")
    ap.add_argument("--strict-drop", action="store_true",
                    help="demo only: drop (instead of flag) unsupported claims — EARN this "
                         "on a gold set before using it on anything real")
    ap.add_argument("--live", action="store_true", help="live LLM run over your manifest")
    ap.add_argument("-o", "--out", help="write the JSON dossier here")
    args = ap.parse_args(argv)

    if args.demo or not args.manifest:
        out = _demo(args)
    elif args.live:
        out = _live(args)
    else:
        ap.error("pass --demo, or a manifest with --live")

    print(_table(out))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)
        print(f"wrote {args.out}")
    if "ledger" in out:
        print(f"cost: ${out['ledger'].get('usd')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
