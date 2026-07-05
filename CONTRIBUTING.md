# Contributing to StormWorthy

Thanks for your interest! Please read the guardrails below before opening a merge request — they
are the project, not process for its own sake.

## Ground rules (non-negotiable invariants)

- **Honest validation framing.** Flag-only (`strict_drop=False`) is the default and the only
  supported mode. `strict_drop` is a *precision claim* that must be **earned** on a hand-rated
  gold set (Wilson lower bound ≥ 0.80 on the predicted-unsupported class) — no change may enable
  it by default or imply it's safe. Benchmark scores are roadmap, not claims: don't add
  performance numbers to docs that no published run backs.
- **Abstention semantics are load-bearing.** An abstain is confidence `None`, never `0.0`; a
  contested section is hard-floored, never averaged; `fetch -> None` means *absent*, never
  fabricated. Changes that soften any of these will be declined.
- **The engine core stays stdlib-only.** `src/stormworthy/engine/` and `testing/` take **zero
  runtime dependencies**. Model/domain code is injected through the six Protocols; the only
  optional dependency lives behind the `[anthropic]` extra.
- **Tests stay zero-network.** The whole suite must pass with no network and no API key
  (deterministic stubs + the fake client). A test that needs the real API doesn't belong in
  `tests/`.
- **Determinism.** No wall-clock, no RNG in engine paths — claim ids and perspective design must
  replay byte-identically.

## Dev setup

```bash
pip install -e .[dev]
python -m pytest -q          # 57 tests, ~1s, zero network
python -m stormworthy.examples.design_review --demo   # offline end-to-end smoke
```

## Making a change

1. Fork and create a branch (`git checkout -b my-change`).
2. Make a focused change that matches the surrounding style (docstrings explain *why*, not what).
3. **Add or update tests** — especially if you touch gate logic: the invariant regression tests
   in `tests/` encode behaviors that break silently.
4. Open a merge request describing **what** changed and **why**, and name any guardrail it
   touches.

### Commit checklist

- [ ] `python -m pytest -q` passes (zero network).
- [ ] No new runtime dependencies (open an issue first if you think one is warranted).
- [ ] No secrets staged — `git status` shows no `.env` / `*.key` / `*.pem`.
- [ ] Docs still honest: no unearned precision or benchmark claims.

## Reporting bugs & security issues

Open an issue for bugs and ideas. For anything security-sensitive, follow
[SECURITY.md](SECURITY.md) instead of a public issue.
