# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project aims to follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://gitlab.com/krahul02004/StormWorthy/-/compare/v0.1.0...main
[0.1.0]: https://gitlab.com/krahul02004/StormWorthy/-/tags/v0.1.0
