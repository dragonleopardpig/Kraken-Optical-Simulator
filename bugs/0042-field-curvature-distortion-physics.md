# 0042 — Field Curvature / Distortion curves were physically wrong

**Status:** Fixed (2026-06-09).
**Component:** Field Curvature / Distortion analysis plot
(`KrakenOS/UI/services/analysis_plot.py`).
**Reported via:** `attachment/distortion.png`. In the user's words: *"refer
attachment/distortion.png, the curve looks wrong. Also compare to the Zemax
version."* (The user clarified `attachment/distortion_zemax.png` — F-THETA.ZMX, a
different lens — is a **reference for the correct shape only**, not the same
plot.)

## Diagnosis

Bug 0037 gave the analysis the right two-panel **layout** (FIELD CURVATURE beside
DISTORTION, field on the vertical axis). But the plotted **curves** were still
wrong in two independent ways:

1. **Distortion did not pass through the origin and grew the wrong way.** The
   "ideal" undistorted image height was a *global least-squares slope* fit
   through the (field, image-height) samples:
   `slope = Σ(f·h) / Σ(f²)`. That line is tilted to minimise the total residual
   across the whole field, so it does **not** coincide with the paraxial
   chief-ray magnification. The percent distortion `(h − slope·f)/(slope·f)` then
   came out non-zero on axis and, on the double-gauss, *largest near the axis and
   shrinking toward the edge* — the opposite of real (pincushion/barrel)
   distortion, which is zero on axis and grows with field.

2. **Tangential (T) and sagittal (S) field curvature were identical, so the
   astigmatism vanished.** The sampler ran **two independent field scans** — one
   along +X, one along +Y — and at each field measured the best-focus shift from
   the *in-plane* ray spread (X-spread for the X scan, Y-spread for the Y scan).
   On a rotationally symmetric lens those two scans are the *same measurement*
   rotated 90° (both are the **tangential** focus), so the "T" and "S" curves
   landed on top of each other and the panel showed no T/S gap at all. Real
   astigmatism is the separation between the tangential focus (in the meridional
   plane) and the sagittal focus (perpendicular to it) measured at the **same**
   field point.

## Fix

Both bugs are in the `field_curvature` sampling logic of
`AnalysisPlotService._plot_analysis`. The sampling was then extracted into
`AnalysisPlotService._sample_field_curvature_distortion` (returns
`(axis_results, field_type, field_limit)`), shared by the two split analysis
modes — see *Follow-up: split into two separate items* below.

1. **One meridional scan, two focus measures — from isolated fans.** The field is
   scanned only along **+Y** (the meridional plane), now **densely and one-sided**
   (`np.linspace(0, field_limit, max(21, …))` instead of 11 bipolar samples), so
   the curve has enough points to show its real shape. At each field the two foci
   come from **separately traced pupil fans**, not from one full 2D bundle:
   - the **tangential** focus from a pupil-Y fan (`pattern="fany"`) and its
     in-plane (Y) convergence, and
   - the **sagittal** focus from a pupil-X fan (`pattern="fanx"`) and its X
     convergence,
   both via the shared `_best_focus(coords, slopes)` helper (longitudinal shift
   that minimises the transverse spread about the centroid, de-meaned as in bug
   0037). They are stored as `axis_results["Y"]` (tangential) and
   `axis_results["X"]` (sagittal), which the plot method maps to T and S.

   This is the **"T still weird"** follow-up fix. The first cut read both spreads
   off a single hexapolar bundle; that made T and S distinct, but off-axis **coma
   and edge vignetting in the meridional plane** leaked into the tangential
   estimate, so the wide-field T curve came out jagged. Tracing the two fans
   independently isolates each focus and the T curve is smooth. (Also,
   `_field_curve_xy` no longer fits a degree-2 parabola through the few distinct
   fields — it now plots a faithful per-|field| aggregation, so a genuine
   inflection like the 28° lens's tangential turnover is preserved instead of
   being smoothed into a parabola.)

2. **Distortion referenced to the paraxial magnification, off the chief ray.** The
   image height for distortion is the **chief-ray** intercept (`pattern="chief"`),
   not the centroid of the full bundle — the centroid carries the coma-induced
   shift, which is *not* distortion and was inflating the curve. The magnification
   `m(f) = h/f` is sampled across the off-axis fields and the **paraxial** value
   `m₀ = m(f → 0)` is recovered as the intercept of a `polyfit(f², m, 1)` (field
   curvature and distortion are even in field, so `f²` is the natural regressor).
   Distortion is then `(h − m₀·f) / (m₀·f) · 100%`, which is identically ~0 on
   axis and grows monotonically toward the edge. Degenerate cases (a single
   distinct field, a non-finite or ~0 intercept) fall back to the min / mean
   magnification.

### Follow-up: split into two separate items

Field curvature and distortion are distinct optical concepts, and bug 0037's
single Zemax-style two-panel cell (FIELD CURVATURE beside DISTORTION, sharing the
field axis) packed both panels into one analysis cell — at the UI's aspect ratio
the left FIELD CURVATURE panel slid **under** the right DISTORTION panel (only
visible in the app, not in a wide headless figure). Rather than re-tune the panel
geometry, the combined cell was **split into two independent analysis modes**:
`field_curvature` (tangential T + sagittal S best focus, mm) and `distortion`
(percent vs field). Each draws a **single full-cell panel** with the field on the
vertical axis (+Y up) and a vertical x=0 reference line. Because each mode now
owns one axis, the panels can no longer overlap. Both modes draw from the one
shared sampler `_sample_field_curvature_distortion`; the drawing split is
`_plot_field_curvature_panel` (T solid + S dashed) and `_plot_distortion_panel`.
The new `distortion` mode is registered alongside `field_curvature` across the UI
(menu button + tooltip, mode-label maps, valid-modes, internal-progress set). This
supersedes the two-panel framing of bug 0037 (Phase 43) and the twin-axis-export
premise of bug 0035 (Phase 41, now exercised through the atmosphere plot's `twinx`
overlay instead).

After the fix, on the *Zemax Double Gauss 28 Degree Field* lens the distortion
runs 0 → +1.13% from axis to edge (smooth pincushion through the origin), the
tangential focus rises to ~+0.064 mm near 9° then turns over smoothly to
−0.094 mm at the 14° edge (the genuine astigmatic turnover, no break), and T/S
separate by ~0.09 mm. (The PSF/MTF case-study layout carries no field setting and
falls back to a small field where the chief-ray distortion is genuinely
sub-0.01%, so it is no longer used as the numeric test vehicle.)

## Tests

`KrakenOS/UI/validate_field_curvature_astigmatism_distortion.py` (display-free,
Agg): renders the field-curvature analysis on the **Zemax Double Gauss 28 Degree
Field** layout (a real 14° half-field, so distortion and astigmatism are both
meaningfully present), captures the sampled `axis_results` (class-level wrapper on
`AnalysisPlotService._sample_field_curvature_distortion`), and asserts
(A) distortion passes through the origin (|dist| on axis ≤ 0.05%), (B) distortion
grows with field (|dist| at the edge ≥ 0.3% and exceeds |dist| near the axis), and
(C) astigmatism is present (max |T − S| ≥ 0.03 mm). Measured: on-axis 0%, edge
1.13%, max|T−S| 0.091 mm over 21 dense fields. SKIPs cleanly if the layout or
analysis is unavailable on a given clone. Folded into the comprehensive harness as
**Phase 48**. The layout guard
(`validate_field_curvature_distortion_panels`, Phase 43) was rewritten for the
split: it now asserts each mode renders exactly one panel (FIELD CURVATURE with
T+S, or DISTORTION) with no sibling, so the two can no longer overlap.

## Verification note

Rendered headless from the *Zemax Double Gauss 28 Degree Field* layout and
inspected: the distortion curve rises smoothly from the origin to +1.13% at the
field edge; the **tangential (solid) curve is now smooth** — it bulges to
~+0.064 mm near 9° and curves back over to −0.094 mm at the 14° edge without the
jagged break the user flagged ("the T still weird") — and the sagittal (dashed)
curve stays distinct from it (the astigmatic split Zemax draws). The earlier
jaggedness came from reading the tangential spread off a full 2D bundle, where
off-axis coma/vignetting corrupted it; the isolated-fan trace fixes it. (Note:
because Python does not hot-reload, a long-running app keeps the old in-memory
code — the app must be **restarted** to pick up this fix; the user's broken-T
re-export was a stale-code artifact.) The garbled distortion-axis tick labels in
the user's original `attachment/distortion.png` come from the high-res
*click-export* path (cramped small plot, bug 0039 territory), not from the base
render, and are not addressed here.
