# 0036 — Wavefront Function plot is a see-through wireframe, not the Zemax solid surface

**Status:** Fixed (2026-06-08).
**Component:** Wavefront Function analysis plot
(`KrakenOS/UI/services/layout_analysis_display.py`).
**Reported via:** `attachment/wavefront.png` (KrakenOS, see-through wireframe) vs
`attachment/wavefront_zemax.png` and `attachment/wavefront_zemax_optimized.png`
(Zemax, opaque hidden-line surface on a base plane). In the user's words:
*"refer attachment/wavefront.png vs wavefront_zemax.png, can we have the Zemax
look?"*

## Diagnosis

`_plot_wavefront_function_analysis` projected the OPD grid into an oblique
waterfall and then drew it as a stack of translucent polylines:

```python
for row_index in range(0, axis_x.shape[0], row_step):
    self._plot_axes_nan_segments(analysis_ax, axis_x[row_index, :], axis_y[row_index, :],
        color="#111827", linewidth=0.42, alpha=0.96)
```

Every slice was just a line. With nothing drawn *under* each slice, the back of
the surface showed straight through the front — the see-through wireframe in
`wavefront.png`. Zemax instead renders an opaque surface: nearer slices hide the
slices behind them (hidden-line removal), and the whole relief sits on a flat
base-plane parallelogram.

Two things were missing:
1. **Opacity / hidden-line removal.** Each slice needs an opaque fill beneath it
   so it occludes farther slices.
2. **The base plane.** The surface floated around a piston-removed zero instead
   of resting on a visible z=0 floor.

## Fix

Rewrote the projection + drawing into a painter's-algorithm waterfall.

`_wavefront_projected_axes_coordinates` now:
- references the relief to its own minimum (`z_norm -= min`), so the surface
  *rests on* the z=0 base plane instead of straddling it;
- additionally returns the per-point z=0 floor line `base_axis_y`
  (`0.20 * yy` projected — finite everywhere, constant within a waterfall row)
  and the four projected corners of the pupil grid box (`base_corners`).

New `_draw_wavefront_solid_waterfall`:
- draws the base-plane parallelogram first (lowest zorder) as a light apron;
- sorts the rows by floor depth and draws them **back-to-front**, each with an
  opaque white curtain (`fill_between` from the slice down to *its own* floor
  line) plus the dark slice line on top, with monotonically increasing zorder.

Nearer rows, painted last, hide the rows behind them — the opaque hidden-line
surface.

Helper `_fill_axes_nan_segments` mirrors `_plot_axes_nan_segments` but fills
each finite run down to a (scalar or per-sample) bottom, skipping NaN gaps.

## Follow-up: a "huge white block" under the relief

The user reported *"some huge white block under the curves."* The first cut had
each curtain stop at *its own* row's z=0 floor line. When the OPD is tall (the
relief sits well above the floor), those stacked per-row curtains pile up into a
floating white slab with the thin base parallelogram stranded at the very bottom
— the white block.

Fix: every curtain now drops to **one common floor** — the front edge (lowest
point) of the base parallelogram — instead of each row's own floor. The relief
then reads as a single solid body sitting on the parallelogram, and the nearer
(front) rows fully occlude the farther ones. The base parallelogram is still
drawn first underneath, so its apron shows at the sides/front of the footprint.
Verified on a synthetic dome (clean ribbed surface resting on the plane, white
block gone) and confirmed not to regress the harder coma/saddle cases versus the
prior per-row fill (their line scatter is a pre-existing projection limitation,
unchanged by this fill change).

### The "white block" was a white-on-white curtain

The user re-flagged it: the relief still looked like it floated above the base
plane with a big empty block beneath. The curtains *were* filling the gap, but
with **pure white on a white background they were invisible**, so a tall relief
read as disconnected from the plane. The curtain fill is now a subtle visible
shade (`#e4e9f0`) instead of white, so the relief's side faces read as a solid
body resting on the plane (Zemax shows the same subtle shading). Verified on a
dome, a coma+astigmatism wavefront, and a strong astigmatism saddle — all now
render as one solid relief sitting on the base plane with no floating gap.

### Follow-up (2026-06-09): the visible shade became a "huge grey block"

Combining the two earlier fixes (common floor + a *visible* shade) over-corrected.
The front (nearest) row's curtain drops to the common front-edge floor, so on a
tall relief that one curtain is a large flat rectangle — and the visible
`#e4e9f0` shade painted it as a grey slab filling the lower ~60% of the panel
(`attachment/wavefront.png`, 2026-06-09). In the user's words: *"why there is a
huge gray color block? It does not look like the Zemax version."* The Zemax plot
(`wavefront_zemax*.png`) is a **dome of slice lines on white** sitting on the base
parallelogram — no shaded body. Fix: each curtain again fills to **its own row's
z=0 floor** (`base_axis_y[row_index]`, not the common floor) and in **opaque
white** (not the shade). White still occludes the farther slices (hidden-line
removal) but is invisible against the white panel, so only the dark slice lines
read — the Zemax dome — and the base parallelogram apron shows around the
footprint. The earlier per-row white "floating block" did not recur: rendered
headless on the synthetic dome plus a pure-astigmatism saddle and a strong-coma
wavefront (PV ~4–5 waves), all clean with no grey slab and no bleed-through. The
single-common-floor fill is what produced the slab; per-row white does not.

### Follow-up (2026-06-09): the real cause was the projection height, not the fill

The per-row white fill removed the *grey* slab, but the user re-flagged a deeper
problem — the relief still towered up the panel with a large empty gap between
the slices and the floor: *"not color changing from gray to white, white to
gray. Please make it similar to Zemax version, why raise it so high with a block
below the curves?"* The fill colour was never the issue; the **projection
geometry** was. `_wavefront_projected_axes_coordinates` weighted OPD height far
above pupil depth:

```python
projected_x = 1.04 * xx + 0.08 * yy
projected_y = 0.20 * yy + 0.82 * z_norm   # z_norm clipped to ±1.6
```

The OPD term (`0.82 · z_norm`, range up to ~2.6 after the floor shift) dwarfed
the row-depth term (`0.20 · yy`, range ~0.4), so the diamond base plane was a
thin sliver and the relief was projected as a tall tower with the white curtains
filling a big empty wall beneath it. Zemax instead draws a **shallow dome on a
broad base plane**: the footprint depth is comparable to the relief height.

Fix: rebalance the projection so the pupil-depth weight exceeds the OPD-height
weight (and lower the clip so extreme samples don't tower):

```python
z_norm = np.clip(zz / z_scale, -1.2, 1.2)
projected_x = 1.0 * xx + 0.40 * yy   # stronger rightward shear → wider diamond
projected_y = 0.50 * yy + 0.45 * z_norm
```

The matching `base_axis_y` floor line and the four base-parallelogram corners use
the same `0.40`/`0.50` weights so the floor stays consistent with the surface.
The relief now reads as a low mound resting on a wide diamond floor — no empty
block beneath, matching `attachment/wavefront_zemax.png`. Verified headless
(`/tmp/wf_final.png`, `/tmp/wavefront0036.png`) on the synthetic spherical+coma+
astigmatism pupil (PV 3.942): a shallow dome of hidden-line slices on the base
plane, gap gone. Phase 42 still passes (curtains 44, row lines 47, base patch 1).

### Follow-up (2026-06-09): add edge lines so it reads as 3D slices

With the projection lowered, the dome was the right shape but the stacked slices
still floated as **open ribbons** — there was no silhouette bounding the body, so
it didn't read as a solid stack of 3D slices the way Zemax does. In the user's
words: *"shouldn't be the edge should have lines so that the wavefront look like a
3D slices, study the Zemax version again."*

Fix: new `_draw_wavefront_dome_edges`, called at the end of
`_draw_wavefront_solid_waterfall`, draws the dome's bounding edges on top of every
slice/curtain (highest zorder so they're never whited out):

- **Left and right pupil-rim silhouettes.** Each grid row is a horizontal chord
  across the masked pupil disk, so the first/last finite sample of every row is a
  point on the left/right pupil rim. Joining those rim points down the grid traces
  the dome's left and right outline.
- **Two side walls** at the dome's true widest extents (`argmin`/`argmax` of the
  rim x — the pupil *equator*, not the top/bottom poles where the chord collapses
  to the centre and produced stray center lines in a first cut). The projection
  has no z term in x, so dropping a rim point to its z=0 floor (`base_axis_y`) is a
  vertical screen line — the wall — so the relief visibly stands on the base plane.

All four edge lines are tagged `gid="wavefront-dome-edge"` so the guard can count
them distinctly from the slice ribbons. Verified headless (`/tmp/wavefront0036.png`
at the 45-sample synthetic pupil and `/tmp/wavefront0036_dense.png` at 90 samples):
the dome now has a clean bounding silhouette and stands on the base plane, reading
as one 3D body of slices. The bottom-front white-curtain/base-apron boundary stays
slightly stepped (a pre-existing per-row-curtain trait, present with or without the
edges); it shrinks with grid density and is minor at the real sample count.

## Tests

`KrakenOS/UI/validate_wavefront_function_solid_waterfall.py` (display-free, Agg):
builds a synthetic circular-pupil wavefront (spherical + coma + astigmatism) and
asserts the projection returns the surface grid, a finite-everywhere floor line
and a 4-corner base parallelogram; that every surface sample sits at or above its
floor; that drawing produces opaque curtains (fill collections — the old
wireframe had none), the row lines, and the filled base-plane patch; and (edge
follow-up) that the dome's bounding edge lines are drawn — at least the two rim
silhouettes, tagged `gid="wavefront-dome-edge"`, with the tallest sweeping ≥ 40 %
of the dome height so it genuinely bounds the relief rather than a flat stub.
Folded into the comprehensive harness as **Phase 42**.

## Verification note

The fixed plot was rendered headless (`/tmp/wavefront0036.png`) from a synthetic
aberrated pupil and inspected: an opaque dome with hidden-line slices resting on
a light base-plane parallelogram apron — matching the Zemax look rather than the
prior see-through wireframe.
