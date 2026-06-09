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

### Follow-up (2026-06-09): shallower dome + a *ruled* wall (3D slices)

Two outline lines and the white curtains still weren't enough. On a real trace the
user re-flagged it: *"still no edge lines on the vertical walls, and the vertical
white walls is so high. Need 3D slices look."* Two things were wrong against Zemax
(`wavefront_zemax*.png`, where the dome's front face is a dense comb of vertical
ribs and the relief is a low mound):

1. **The relief was too tall** — the OPD weight (`0.45 · z_norm`) made the dome
   nearly as tall as the base plane is wide, so the per-row white curtains became
   tall *bare* vertical walls. Lowered to `0.30 · z_norm` (~⅓ of the footprint
   width) for a shallow Zemax dome with short walls.
2. **The walls had no edge lines** — the white curtains are invisible against the
   white panel, so the front face read as blank. New `_draw_wavefront_front_wall`
   *rules* the visible wall: it takes the surface's **near (lower) silhouette**
   (per screen-x column, the lowest finite surface sample), draws it as the wall's
   top edge, and drops a **comb of vertical ribs** from it to the z=0 base plane
   (`projected_x` has no z term, so each rib is exactly vertical).

The two lone equator side walls from the prior cut are replaced by this comb. Ribs
and silhouette carry the same `gid="wavefront-dome-edge"`. Verified headless on the
synthetic dome and a strong astigmatism+coma saddle (`/tmp/wavefront0036.png`,
`/tmp/wavefront_saddle.png`) and compared side-by-side with
`attachment/wavefront_zemax_optimized.png` (`/tmp/wavefront_compare.png`): a low
dome of hidden-line slices standing on the base plane, the front/side wall ruled
with vertical ribs — the Zemax 3D-slices look, walls no longer tall and bare.

**Broken-line fix.** A first cut of the wall *smoothed* the silhouette (a running
median + 3-tap mean) to tidy a small sawtooth. On a real trace the user flagged a
*"broken line at the wall"*: the smoothed top floated off the actual surface edge,
so it crossed up into the slice bundle in places (a doubled/broken edge) and the
ribs hung from a line the slices didn't touch. Fixed by dropping the smoothing and
anchoring the wall on the **exact** lower envelope, computed from the **drawn rows
only**: each rib top is the lowest *painted* slice point in its column, so the
front edge is one continuous line lying on the surface (it can never cross up into
the bundle — it is the per-column minimum by construction) and every rib meets a
slice that is actually drawn. Re-verified on the dome and saddle: single clean
front edge, ribs connected, no broken/doubled line.

### Follow-up (2026-06-09): the 2D waterfall is now sliced from the real 3D mesh

The broken line *still* recurred on real traces. Root cause: the waterfall was
reconstructed from the **projected masked grid + a binned lower-envelope wall**.
On a strongly-aberrated/saddle wavefront the front edge isn't single-valued in
screen-x, so per-screen-x-bin minima hopped between sparse masked-grid rows → a
gap/stub. Every prior fix patched one shape and the next re-broke it. The user's
call: *"do you want to consider directly slice from the 3D?"* — yes; that is the
root-cause fix.

`_plot_wavefront_function_analysis` now prefers `_draw_wavefront_from_3d_slices`
(falling back to the old grid path only if PyVista/VTK is unavailable):

- **Slices** — `wavefront_3d_view.wavefront_slices` cuts the flat triangulated
  pupil (z=0, OPD scalar) with `slice_along_axis(n=46, axis="y")`. Each horizontal
  slice is a genuine, continuous cross-section of the surface (clean to the true
  rim, no masked-grid stair-step). Drawn back-to-front with the same opaque white
  curtains (hidden-line) + dark lines and base parallelogram.
- **Front silhouette = the lower *envelope* of the slice curves**, not a per-bin
  grid minimum: each slice curve is interpolated onto a common screen-x grid and
  the pointwise minimum is taken. The minimum of continuous functions is
  continuous, so the front edge **cannot break or double** regardless of wavefront
  shape. Ribs drop from the envelope to the z=0 floor of whichever slice owns each
  minimum; left/right rim silhouettes come from the slice endpoints.

A first slice-based attempt took one *frontmost point per x-slice*; that still
jumped where the frontmost point switched from the rim to an interior dip (the
guard caught a 45 % vertical jump on the coma/astigmatism dome). The lower-envelope
construction fixed it. Verified headless on the dome (PV 3.8) and saddle (PV 2.7):
continuous front edge that follows the real surface (it dips where the relief
genuinely dips), ribs clean, no break.

**Common-floor wall.** The user then flagged wall defects: the rib bottoms were
*ragged* (each dropped to its owning slice's z=0 floor, and the lower-envelope's
owning slice jumps even though the envelope value is continuous) and the base
apron showed a *staircase* (per-slice curtains dropped to per-slice floor levels,
revealing the tilted base plane in steps). Fixed by dropping **every curtain and
rib to one common floor** — the base parallelogram's horizontal front edge
(`y=y_lo`). Hidden-line removal is unaffected (nearer slices, painted later, still
occlude farther ones; white-on-white stays invisible, so no "grey block"
recurs). Result: a flat clean base, no ragged rib bottoms, no stepped apron — the
dome stands on the front of the base diamond like Zemax.

**Diamond fit + folded-surface ordering.** The user then flagged (a) the base
diamond's left/right corners spilling past the frame as *clipped blue squares* and
(b) a *white "lens"* on the front face. (a): the affine fit covered only the
surface points, but the base parallelogram is the pupil bounding box — wider than
the dome — so its corners projected outside the plot box. Fixed by folding the
base-corner projections into the fit extent, so the whole diamond lands inside the
frame. (b): the front white lens was a hidden-line **ordering** artifact — slices
were painted back-to-front by raw pupil-y, but on a folded/saddle wavefront a
higher-y slice can dip in *front* of a lower-y one, so its line got white-curtained
away. Fixed by ordering the draw by each slice's **frontmost projected extent**
(min projected_y) instead of pupil-y, so a dipping slice is painted last (on top)
and its line shows. The lens is gone on the saddle (the user's case) and reduces to
the usual y-order on an unfolded dome. A strongly-folded synthetic dome (PV 3.8)
still shows a small front-center zig-zag where the lower envelope switches owners
rapidly — the inherent limit of a 2D painter's waterfall on a folding surface; the
real-3D PyVista view (bug 0044) renders those cases exactly.

### Follow-up (2026-06-09): replaced the whole waterfall+wall with a real MESH

Comparing the 2D to the 3D, the user pinned the remaining oddities precisely: the
*vertical wall lines "don't make sense — I can't visualise them as slices of
anything,"* and there was a residual sawtooth on the front silhouette. Both were
inherent to the stylized wall: the horizontal lines were real cuts, but the wall
(lower envelope + vertical ribs to a floor) was **decoration that doesn't
correspond to any cross-section**, and the lower-envelope line sawtooths where two
slice curves cross. The user chose to **make every line a real slice (a mesh)**.

New `_draw_wavefront_mesh` replaces the entire waterfall/wall path. The structured
pupil grid's **rows (constant-y) and columns (constant-x) are both genuine
wavefront slices**; each grid cell is projected to a quad and the quads are painted
**far→near (painter's algorithm) as opaque white fills with dark edges**, so nearer
cells occlude farther ones (hidden-surface removal) and the visible edges form a
true cross-section mesh — every line a real cut, reading like the 3D surface. Depth
is the orthographic into-screen axis (cross product of the two screen-basis
vectors: `0.12·x − 0.30·y + 0.50·z_norm`), so a high-y cell that dips in front
sorts correctly. The relief sits on a faint base diamond; **there is no stylized
wall, no ribs, no lower-envelope** — so the broken line, the sawtooth, the white
lens and the wall-doesn't-make-sense complaints are all moot (that machinery is
gone). A 2D painter can still mis-occlude a sharply folded saddle; the PyVista 3D
view (bug 0044) stays the exact reference.

This **supersedes** every "wall/ribs/curtain/lower-envelope" follow-up above. The
now-dead `_draw_wavefront_solid_waterfall`, `_draw_wavefront_from_3d_slices`,
`_draw_wavefront_dome_edges`, `_draw_wavefront_front_wall`,
`_wavefront_projected_axes_coordinates`, the `_*_axes_nan_segments` helpers, and
`wavefront_3d_view.wavefront_slices` were removed.

## Tests

`KrakenOS/UI/validate_wavefront_function_solid_waterfall.py` (display-free, Agg;
filename kept so the Phase-42 import is stable) builds a synthetic circular-pupil
wavefront (spherical + coma + astigmatism), draws the panel, and asserts the
**mesh** representation: (A) a `PolyCollection` tagged `gid="wavefront-mesh"` is
drawn with many cells (≥ 100) — a real mesh from both grid directions, not a few
stray polygons; (B) its faces are **opaque white** — hidden-surface removal, not
the see-through wireframe of the original bug; (C) its edges are **dark** — the
visible mesh lines (the real cross-sections); (D) a base-plane diamond patch is
drawn under it. Folded into the comprehensive harness as **Phase 42**.

## Verification note

Rendered headless (`/tmp/wavefront0036.png` dome PV 3.8, `/tmp/wavefront_saddle.png`
PV 2.7) and confirmed on the user's real trace: a real both-direction cross-section
mesh with depth-sorted hidden-surface removal, sitting on a faint base diamond —
reading like the 3D surface, every visible line a genuine cut. The earlier
see-through wireframe, grey block, broken line, sawtooth and "wall doesn't make
sense" are all resolved by the mesh.
