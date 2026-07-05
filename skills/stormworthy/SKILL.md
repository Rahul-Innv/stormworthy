---
name: stormworthy
description: Runs a claim-verified research pipeline over a subject and consumes the resulting dossier honestly — multiple analyst perspectives plus an adversarial refuter, every claim typed and verified against its cited sources, sections that abstain when evidence is thin. Use when the user wants verified or cited research, a research brief or dossier with confidence levels, competitive or domain analysis they can audit, or asks to "prove the citations" on research findings. Not for casual one-off questions or pure text generation.
---

# StormWorthy — claim-verified research

Read `LESSONS.md` in this directory first if it exists — it holds field lessons that override
anything below.

## What this produces (and what it does not)

A **verified dossier**: per-lens sections of typed, cited claims, each carrying a gate verdict
(`supported` / `unclear` / `unsupported`), section confidence, contestation state, and honest
abstains. It does NOT produce a polished article, a UI, or unsourced opinion. Downstream steps
turn the dossier into deliverables.

## Running the pipeline

The Python package lives at the plugin root (`${CLAUDE_PLUGIN_ROOT}`). One-time setup in the
target environment:

```bash
pip install -e "${CLAUDE_PLUGIN_ROOT}"            # engine + stubs (no runtime deps)
pip install -e "${CLAUDE_PLUGIN_ROOT}[anthropic]" # only for live LLM runs
python -m pytest -q "${CLAUDE_PLUGIN_ROOT}/tests" # offline proofs — run after ANY adapter edit
```

A complete worked adapter ships in the package — `stormworthy.examples.design_review` (six
design-review lenses with real WCAG/CWV/heuristics rubrics + a manifest-driven retrieval
adapter). Prefer copying it over starting from the bare skeleton;
`python -m stormworthy.examples.design_review --demo` is the offline smoke test.

To research a subject, compose a run script (see `references/running.md` for a full template):

1. **FrameworkSpec** — decompose the domain into 4–8 angles with `"Family — detail"` anchors,
   real rubrics (actual thresholds/standards, not vibes), a basic-fact baseline angle, and an
   adversarial refuter angle. The refuter is not optional.
2. **RetrievalAdapter** — a corpus manifest `[{url, channel, title, tags}]` over local files or
   fetchable urls. `fetch -> None` when a source can't be pulled. Never fabricate a source.
3. **Gate** — `ClaimGate(EntailmentJudge(judge_llm, read_source))`. Keep `strict_drop=False`
   (flag-only) unless a hand-rated gold set has EARNED strict-drop (Wilson LB >= 0.80).
4. **Roles** — `LLMInterrogator` / `LLMExpert` / `LLMSurfacer` from `stormworthy.llm`, sharing one
   `Ledger`. Auth = `ANTHROPIC_API_KEY` in the environment; run `RoleLLM.ping()` first (cheap
   4-token auth probe) and report auth failures to the user instead of retrying blindly.
5. `ResearchRun(...).research(subject_id)` → dossier. Default `k_runs=1` (see LESSONS: lexical
   recurrence under-recurs reworded LLM output at k>=2; raise k only with a semantic recurrence
   key or a lowered quorum).

Report the ledger cost to the user after every live run.

## Consuming the dossier (the honesty contract)

| Claim class | Downstream weight |
|---|---|
| `supported` constructive claim | a constraint — build on it |
| supported **refuter** claim (`risks`) | a HARD constraint — address it or escalate |
| retained-but-flagged claim (`unclear`/`unsupported` in flag-only) | advisory only — never present as verified |
| abstained lens (`insufficient_evidence`) | NO weight — say "insufficient evidence", don't fill the gap with generation |
| contested section (confidence floored) | surface the contestation to the user verbatim |

Two rules that override enthusiasm: findings are **constraints, not taste** — they bound the
solution space, they don't pick the design; and any domain-specific acceptance gate the user
already has (house style, register, compliance review) stays **sovereign** — a dossier never
outranks it.

## Capture lessons

When a run teaches something durable (a client quirk, a prompt fix, a recurrence failure), append
it to `LESSONS.md` in this directory with the date and one-line why.
