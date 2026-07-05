# WCAG 2.2 AA quick reference

Original summary for this example corpus; the normative text is the W3C Recommendation:
https://www.w3.org/TR/WCAG22/

- **SC 1.4.3 Contrast (Minimum)**: body text needs a contrast ratio of at least **4.5:1**
  against its background; large text (≥ 24 px, or ≥ 18.66 px bold) needs at least **3:1**.
- **SC 1.4.11 Non-text Contrast**: UI components and graphical objects required for
  understanding — including focus indicators — need at least **3:1**.
- **SC 2.5.8 Target Size (Minimum)**: pointer targets are at least **24×24 CSS px**, or have
  equivalent spacing; 44 px remains the AAA / platform-HIG bar.
- **SC 1.4.10 Reflow**: content reflows at **320 CSS px** width (equivalent to 400% zoom)
  without two-dimensional scrolling.
- **SC 2.4.7 Focus Visible**: keyboard focus is visibly indicated.
- **SC 2.3.1 / 2.2.2**: no more than three flashes per second; moving content longer than five
  seconds can be paused, stopped, or hidden. Provide a reduced-motion variant.
- **Labels/semantics**: form inputs carry programmatic names; icon-only controls need text
  equivalents.

Rule of use: cite the specific success criterion; an untested contrast, label, or target claim
is unsupported.
