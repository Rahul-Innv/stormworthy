# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] — 2026-07-19

### Added

- Added the gate benchmark harness and a visible, reproducible design-review demo transcript.
- Added the public product-family masthead, package badges, install guidance, and a consistent
  getting-started path.

### Fixed

- Preserved honest `insufficient_evidence` abstentions when a requested lens produces no claims,
  including cross-routed empty lenses.
- Derived abstention membership from routing keys so provider output cannot silently omit an empty
  requested lens.
- Made the documented quickstart output match the deterministic packaged demo.

### Changed

- Tightened README wording and punctuation without widening the supported `flag_only` validation
  claim or treating the still-unearned `strict_drop` mode as released behavior.

## [0.1.0] — 2026-07-01

Initial public release.

- **Engine** (`stormworthy.engine`, stdlib-only): perspective designer (basic-fact pinned first,
  adversarial refuter pinned last, family de-dup), grounded conversation loop, typed claims
  (`fact` / `relational` / `evaluative`), the structural `supports:"link"` rule, anti-evasion
  guard, 3-tier verification gate (self-consistency → entailment → optional corroboration),
  honest abstention (`insufficient_evidence`, confidence `None`), contestation hard floor,
  `ResearchRun` orchestrator, deterministic replay.
- **Reference LLM layer** (`stormworthy.llm`, optional `[anthropic]` extra): config-driven model
  registry with cost ledger, interrogator/expert/surfacer roles, entailment judge.
- **Public test kit** (`stormworthy.testing`): deterministic stubs for all six Protocols + a
  fake Anthropic client for zero-spend live-shape proofs.
- **Worked example** (`stormworthy.examples.design_review`): six design-review lenses with real
  WCAG 2.2 / Core Web Vitals / usability-heuristics rubrics, corpus-manifest-driven retrieval,
  and an offline demo exercising every gate behavior on a fictional subject.
- **Claude Code plugin**: `.claude-plugin/` manifest + the `stormworthy` skill.
- 57 offline tests (invariant regressions, end-to-end proofs, live-shape suite); GitLab CI.

Validation status is documented honestly in the README: flag-only is the only supported mode;
`strict_drop` remains unearned; benchmark scores are roadmap.

[Unreleased]: https://gitlab.com/krahul02004/stormworthy/-/compare/v0.1.1...main
[0.1.1]: https://gitlab.com/krahul02004/stormworthy/-/compare/v0.1.0...v0.1.1
[0.1.0]: https://gitlab.com/krahul02004/stormworthy/-/tags/v0.1.0
