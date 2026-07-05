# Core Web Vitals thresholds

Original summary for this example corpus; the source of truth is Google's web.dev documentation:
https://web.dev/articles/vitals

- **LCP (Largest Contentful Paint)** ≤ **2.5 s** — measured at the 75th percentile of page loads.
- **INP (Interaction to Next Paint)** ≤ **200 ms** at p75.
- **CLS (Cumulative Layout Shift)** ≤ **0.1** at p75.

Design-side implications:

- The LCP element (usually the hero image/chart) should be lightweight, discoverable early, and
  never lazy-loaded.
- **Reserve dimensions** for media, embeds, and late-loading fonts — unreserved containers are
  the classic layout-shift source.
- Perceived speed: skeletons over spinners for content that has a stable shape.

Rule of use: a performance claim needs a **measured number** (lab or field, at p75) or a cited
principle — never an assertion.
