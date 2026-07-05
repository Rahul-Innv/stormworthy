# Security Policy

## Reporting a vulnerability

**Please do not open a public issue for security problems.**

Report privately by opening a **confidential issue** on GitLab: use
[New issue](https://gitlab.com/krahul02004/StormWorthy/-/issues/new) and tick **"This issue is
confidential"** before submitting. Confidential issues are visible only to the reporter and
project members.

Include: what the issue is and where, how to reproduce it, and the potential impact.

This is a solo-maintainer project, so responses are best-effort — but security reports are taken
seriously and prioritized over features.

## Supported versions

Only the current `main` branch is supported.

## Secrets & security posture

- The engine core is stdlib-only and makes **no network calls**. The optional live layer
  (`stormworthy[anthropic]`) calls the Anthropic API with a key you supply via
  `ANTHROPIC_API_KEY` — keys live only in environment variables, **never committed** (`.env`,
  `*.key`, `*.pem` are gitignored) and never written into run scripts or output artifacts.
- If a key is ever exposed, **rotate it immediately** — treat anything that touched a commit,
  log, or transcript as compromised.
- Retrieval adapters read the files *you* list in a corpus manifest; the engine never fetches
  URLs on its own. Treat corpus content as untrusted input when you build on top of it.
