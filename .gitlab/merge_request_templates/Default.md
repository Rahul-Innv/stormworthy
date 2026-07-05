## What & why
<!-- What does this change, and why? Link any issue. -->

## How I tested
- [ ] `python -m pytest -q` passes (zero network)

## Checklist
- [ ] No new runtime dependencies (engine core stays stdlib-only)
- [ ] Honesty invariants intact (flag-only default, abstain = `None`, contestation floor,
      silence ≠ absence, no unearned precision claims in docs)
- [ ] No secrets staged (`git status` shows no `.env` / keys)
- [ ] Tests added/updated for new behavior
