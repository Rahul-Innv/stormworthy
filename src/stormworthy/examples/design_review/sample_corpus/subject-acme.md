# Acme Analytics — subject brief

Acme Analytics is a **fictional** B2B web dashboard for mid-market operations teams. Primary
job-to-be-done: check pipeline health at a glance and export a weekly report. Secondary job:
invite a teammate. Intended users are non-technical operations managers on 1366×768 laptops.

## What the current UI contains (observable attributes)

- **Signup flow**: a single form with **nine required fields**; the "Create account" call to
  action sits **below the fold** at the reference 1366×768 viewport.
- **Toolbar**: a row of icon-only buttons, each **20×20 CSS px**, 4 px apart.
- **Body text**: light gray on the white canvas, **measured at 3.8:1** contrast.
- **Type**: a 34 px hero metric; section heads and labels cluster at 18/17/16 px.
- **Accent color**: the brand teal is used as **text on light surfaces** in the nav and footer.
- **Hero chart**: a full-bleed chart is the largest above-the-fold element; its container has
  no reserved dimensions while data loads.
- **States**: loading and error states exist for the chart; the empty (no-data) state is a blank
  panel.
- **Navigation**: seven top-level items; two of them ("Insights" and "Analytics") overlap in
  meaning.

No field performance data (LCP/INP/CLS) has been collected for this fictional product yet.
