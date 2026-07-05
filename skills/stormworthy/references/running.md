# Run template (live)

Before starting from this skeleton: a complete worked adapter ships at
`stormworthy.examples.design_review` — a real FrameworkSpec (six lenses, real WCAG 2.2 /
Core-Web-Vitals / heuristics rubrics) and a manifest-driven `ManifestRetrieval` you can copy or
import directly. `python -m stormworthy.examples.design_review --demo` runs it offline;
`... your-manifest.json --live` runs it against your own corpus.

A complete run script skeleton. Everything domain-specific is marked `# <-- yours`.

```python
"""Run a stormworthy research pass. Usage: python run.py subject.json corpus.json out.json"""
import json, sys

from stormworthy.engine import Angle, ClaimGate, ResearchRun
from stormworthy.llm import EntailmentJudge, Ledger, LLMExpert, LLMInterrogator, LLMSurfacer, RoleLLM
from stormworthy.testing import StubFramework  # fine for production: it's just an Angle container

subject = json.load(open(sys.argv[1]))   # {"name": ..., "description": ...}
corpus = json.load(open(sys.argv[2]))    # [{"url": path-or-url, "channel": ..., "title": ...}]

# --- framework -------------------------------------------------------- <-- yours
def angle(id, anchor, key, kind="framework", question="", rubric=None):
    return Angle(id=id, title=f"{id} analyst", anchor=anchor, question=question,
                 kind=kind, rubric=rubric, anchor_keys=(key,))

framework = StubFramework(
    [
        angle("a-x", "FamilyA — detail", "lens_a", question="...?", rubric="real thresholds here"),
        # 4-8 angles; same Family merges into one analyst
    ],
    angle("subject", "Subject", "subject", kind="basic_fact", question=f"What is {subject['name']}?"),
    angle("risks", "Risks", "risks", kind="refuter", question="What breaks the thesis?"),
    fid="my-domain-v1",
)

# --- retrieval (local-file corpus example) ----------------------------- <-- yours
class Retrieval:
    def __init__(self, items):
        self.items = items
        self.trust_by_channel = {"standard": 0.98, "kb": 0.9, "reference": 0.6, "web": 0.5}
    def search(self, query, *, k, perspective_id):
        from stormworthy.engine import SourceRef
        words = set(query.lower().split())
        ranked = sorted(self.items, key=lambda i: -len(words & set(i["title"].lower().split())))
        return [SourceRef(url=i["url"], title=i["title"], channel=i["channel"]) for i in ranked[:k]]
    def fetch(self, ref):
        from stormworthy.engine import Source
        try:
            text = open(ref.url, encoding="utf-8").read()
        except OSError:
            return None  # ABSENT — never fabricate
        return Source(url=ref.url, title=ref.title, text=text[:6000], channel=ref.channel,
                      trust=self.trust_by_channel.get(ref.channel, 0.5))
    def trust(self, src):
        return src.trust

# --- roles + gate (shared ledger; judge on the strongest model you can afford) ---
ledger = Ledger()
roles_llm = RoleLLM("sonnet", ledger=ledger)
judge_llm = RoleLLM("opus", ledger=ledger)
roles_llm.ping()  # cheap auth probe — fail fast with a clear error

def read_source(url):
    try:
        return open(url, encoding="utf-8").read()
    except OSError:
        return None

retrieval = Retrieval(corpus)
run = ResearchRun(
    framework, retrieval,
    LLMInterrogator(roles_llm),
    LLMExpert(roles_llm, subject),
    LLMSurfacer(roles_llm),
    ClaimGate(EntailmentJudge(judge_llm, read_source)),
    k_runs=1,            # see LESSONS: k>=2 needs a semantic recurrence key or quorum<1.0
    max_turns=2,
    strict_drop=False,   # flag-only until EARNED on a gold set
)
dossier = run.research(subject["name"])

out = {
    "subject": dossier.entity_id,
    "sections": [{
        "lens": s.anchor, "status": s.status, "headline": s.headline,
        "confidence": s.confidence, "contested": s.contested,
        "claims": [{"kind": c.kind, "text": c.text,
                    "verdict": (c.entailment or {}).get("verdict"),
                    "confidence": c.confidence, "stance": c.stance,
                    "citations": [{"url": cc.get("url"), "title": cc.get("title")}
                                  for cc in c.citations]} for c in s.claims],
    } for s in dossier.sections],
    "evasions": dossier.evasions,
    "ledger": ledger.summary(),
}
json.dump(out, open(sys.argv[3], "w"), indent=2)
print(f"wrote {sys.argv[3]} — ${ledger.summary()['usd']}")
```

## Cost levers

`k_runs` (multiplies everything) · `max_turns` per perspective · number of angles · model choice
per role (conversation roles cheap, judge strong) · `max_followups` on the interrogator. A rough
shape: cost ≈ perspectives × k_runs × (turns × 2 role calls) + one judge call per cited claim.

## Auth

`ANTHROPIC_API_KEY` (or `ANTHROPIC_AUTH_TOKEN`) in the environment. `ping()` first. On 401/403,
stop and tell the user — do not loop retries. Never write credentials into run scripts or output
artifacts, and never commit output artifacts containing absolute local paths.
