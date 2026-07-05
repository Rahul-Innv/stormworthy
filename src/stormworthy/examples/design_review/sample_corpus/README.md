# Sample corpus — provenance

- **Acme Analytics is entirely fictional**, invented for this example. Any resemblance to a real
  company or product is coincidental. The demo's findings are about the fictional brief, not
  about anything real.
- All prose here is **original**, written for this repository. Standards documents are
  *summarized and cited* (W3C WCAG 2.2, Google web.dev, Nielsen Norman Group), never copied.
- `perf-field-data.md` is listed in `manifest.json` but **deliberately does not exist**. The
  retrieval adapter's `fetch()` returns `None` for it, and the demo's performance lens abstains
  (`insufficient_evidence`, confidence `None`) instead of fabricating — the engine's
  silence ≠ absence rule, live.
