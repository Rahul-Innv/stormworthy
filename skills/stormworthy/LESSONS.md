# Field lessons (read before running; append, don't rewrite)

- **2026-07-01 — k_runs>=2 collapses live briefs.** Live LLMs reword findings between runs, so the
  default lexical recurrence key under-recurs and unanimity can empty the whole dossier (observed:
  k=2 → 0 sections where k=1 → 7). Default to `k_runs=1`; raise k only with a semantic recurrence
  key (`self_consistency(key=...)`) or `quorum < 1.0`.
- **2026-07-01 — strict-drop is earned, never assumed.** The judge's precision has not cleared a
  hand-rated gold set (Wilson LB >= 0.80 on predicted-unsupported). Ship flag-only; a flagged
  claim is presented as unverified, not hidden and not trusted.
- **2026-07-01 — the refuter pays rent.** Contested sections with floored confidence are the
  single highest-signal output; never smooth them into an average or drop them from summaries.
- **2026-07-01 — cheap-model overconfidence.** Inter-model agreement is NOT correctness; do not
  use "N models agreed" as a validation claim. Use a stronger model for the judge role than for
  the conversation roles when budget forces a choice.
