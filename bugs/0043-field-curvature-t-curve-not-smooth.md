# 0043 — Field Curvature T-curve renders with visible kinks, not a smooth arc

**Status:** Fixed (2026-06-09).
**Component:** Field Curvature analysis plot
(`KrakenOS/UI/services/analysis_plot.py`, `_field_curve_xy`).
**Reported via:** `attachment/field_curvature.png` (KrakenOS — the solid tangential
**T** curve has angular corners near 10.5°, 12°, 13° while the dashed sagittal
**S** curve looks smooth). In the user's words: *"refer
attachment/field_curvature.png, the T-curve not smooth."*

## Diagnosis

The Field Curvature panel draws each series straight from the per-field samples.
`_field_curve_xy` grouped the samples by `|field|` (averaging any ± pair) and the
panel plotted the result **as-is** — by deliberate choice, since an earlier
degree-2 polynomial fit had flattened the genuine edge turnover into a parabola
that overshot the panel and broke the T curve into pieces (see bug 0037
follow-up). So the curve was an honest polyline through the real samples.

The data itself is clean and smooth — dumping the raw tangential focus shows a
monotone rise to ~+0.064 mm at ~9° then a hard bend back to ~−0.094 mm at 14°,
with no per-field jitter. The defect was purely in the **rendering**: the
tangential focus bends sharply in the 11–14° edge region, and at the raw field
spacing (`field_sample_count = max(21, …)` → ~0.7° steps) that fast-curving arc
was drawn as a handful of straight chords. The chords meet at visible corners —
the "not smooth" T curve. The sagittal (S) curve bends gently, so its chords
read as smooth; only the sharply-turning T curve exposed the polyline.

Measured turning angle between consecutive segments (in panel-fraction space, so
mm-vs-deg axis units don't skew it): **32.8°** at the edge turnover for the raw
21-point chord curve — a clearly visible corner.

## Fix

Resample the aggregated samples onto a dense field grid with a **shape-preserving
monotone cubic** (`scipy.interpolate.PchipInterpolator`, scipy is already a core
dependency) before returning them from `_field_curve_xy`:

```python
if avg_fields.size < 3:
    return avg_values, avg_fields
dense_fields = np.linspace(float(avg_fields[0]), float(avg_fields[-1]), 480)
dense_values = PchipInterpolator(avg_fields, avg_values)(dense_fields)
return dense_values, dense_fields
```

PCHIP is the right tool here because it:
- **passes exactly through every real sample**, so the genuine edge turnover is
  preserved, not flattened (the failure mode of the old degree-2 fit); and
- is **shape-preserving / non-overshooting** — it will not introduce the
  ringing a natural cubic spline could add at the sharp inflection.

`field` is the strictly-increasing independent variable (0 → max), and `focus`
folds back as a single-valued function of it, so a 1-D PCHIP of `focus(field)` is
well posed. With 480 points the edge-turnover segment turning angle drops to
**~3.8°** (invisible — the segments are tiny) while still reproducing the full
focus range. Because `_field_curve_xy` is shared, the S and Distortion curves get
the same smooth rendering.

## Tests

`KrakenOS/UI/validate_field_curvature_curve_smoothness.py` (display-free, Agg):
renders the Field Curvature panel on the Double Gauss case-study layout, reads the
*actually drawn* solid T line, and asserts (A) it is densified (≥ 100 points, vs
the ~21 raw samples — proves PCHIP is active); (B) it is smooth — the max segment
turning angle in panel-fraction space is < 12° (the dense curve peaks ~3.8°, the
old chord curve ~33°, so 12° separates with margin on both sides); and (C) the
edge turnover is preserved — the dense value range matches the raw focus range to
within ~±8% (PCHIP neither flattened nor overshot the inflection). SKIPs cleanly
if the analysis is unavailable on a given clone. Folded into the comprehensive
harness as **Phase 49**.

## Verification note

The smoothed plot was rendered headless (`/tmp/fc_smooth.png`) from the Double
Gauss case study and inspected: the solid T curve is a clean arc that still bends
back hard at the edge field (the real turnover), with the angular corners of
`attachment/field_curvature.png` gone; the dashed S curve and the distortion
curve are likewise smooth. Phases 43 and 48 (panel structure and curve physics)
still pass unchanged.
