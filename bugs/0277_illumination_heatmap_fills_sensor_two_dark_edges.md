# 0277 — Relative-illumination heatmap: rim gap + "4 dark edges" on the coaxial sensor

## Symptom (flag_20260709_114618_526)

A **direct follow-up** to bugs/0276. On the same MV-150 **coaxial-LED** vendor-STEP scene, after
0276 pinned the heatmap *window* to the vendor sensor override, the quad got larger — but two
defects remained:

> "the black square is larger now but still not fully covered the sensor. There are 4 dark side
> rather than 2."

1. **Rim gap** — the heatmap still stopped short of the orange sensor square, leaving a thin dark
   border on every side.
2. **4 dark edges** — all four edges read dark, instead of the wanted **2 dark (fold / X) + 2
   uniform (perp / Y)** pattern.

## Root cause

Two independent causes, one per symptom:

**1. Bin-centre gap.** The draped quad is a point grid built at bin **centres** (`xc`/`yc` =
`0.5*(edges[:-1]+edges[1:])` in `source_illumination_overlay.build_source_illumination_overlay`). So
the outermost vertex sits **half a bin inside** the window — for a 39 mm sensor at 16 bins that is
±18.28 mm, ~1.22 mm short of the ±19.5 mm rim. The `pv.StructuredGrid` quad therefore ends a bin-half
inside the orange square on all four sides: the "still not fully covered" dark border.

**2. Sparse-scene perp speckle.** The area LED floods far past the sensor, so only ~**800** of the
traced rays land in the 39×39 FOV. The adaptive bin count aims for ~10 hits/bin
(`sqrt(in_extent/10)` → 9 bins), but a **floor of 16** forced 16×16 = 256 bins → ~**3.2 hits/bin** →
30 %+ Poisson counting noise per bin. That noise swamps the gentle ~30 % perp roll-off, so the
**uniform** (over-filled) perp axis randomly speckled **dark** and read as a third and fourth dark
edge. The fold axis has a real ~30 % dip and stayed dark regardless; only the perp axis was
noise-flipped. Confirmed two ways: (a) the perp edge-ratio swung **0.804 / 1.091 / 1.234** across
three ray counts while the fold ratio held ~**0.77** (physics is stable, perp is noise); (b) a
`(bins, sigma)` sweep on one fixed trace pinpointed the 16-bin floor as the culprit — dropping it lets
the honoured ~10-bin grid read the true smooth gradient.

## Fix

**Gap** (`source_illumination_overlay.py`): after computing the bin-centre coordinates, **pin the
outer vertices to the window edges** — `xc[0]=x_edges[0]`, `xc[-1]=x_edges[-1]` (and likewise `yc`).
The edge cell simply holds its outermost bin's value out to the rim. Only the vertex **positions**
move; the density / `relative` grid and the edge ratios are untouched (they read the bins, not the
point coordinates), so the fix is purely geometric coverage.

**Speckle** (`three_d_scene_tools._compute_source_illumination_overlay_spec` + overlay smoothing):
drop the adaptive bin **floor 16 → 10** so the ~10-bin target is honoured (coarser but ~8 hits/bin,
well-populated), and raise the de-speckle Gaussian **σ 1.0 → 1.5 bins** so residual counting noise is
averaged out while the many-bin-wide fold roll-off is left intact. Denser scenes still climb toward
the 48-bin ceiling (more rays → finer), so nothing regresses at high ray counts.

## Verification

New guard `validate_open3d_illumination_heatmap_full_sensor` (phase **244**), display-free (numpy +
one headless coaxial-LED trace, no VTK/Tk), reusing the 0276 override-only fixture:

* **FULL-SENSOR** — the overlay quad half is **19.50 mm**, flush with the 19.50 mm sensor rim (was
  the bin-centre ~18.3 mm), so there is no dark gap to the orange square.
* **2-DARK / 2-UNIFORM** — at 8000 rays (the sparse density that used to speckle): fold(x) = **0.817**
  ≤ 0.85 (dark), perp(y) = **1.078** ≥ 0.85 (uniform), with clear separation. With the old floor/σ the
  perp axis fell below 0.85 at this density — the "4 dark edges" the flag reported.

A rendered proof `bugs/_0277_heatmap_fixed.png` (generator `bugs/render_0277_heatmap.py`) shows the
grayscale `relative` grid flush inside the orange rim, dark left/right (fold) edges, uniform
top/bottom (perp) edges. Sibling phase 243 (the 0276 window-pinning guard) stays green; its INTEGRATION
quad-half now reads 19.5 (its loose bounds still pass). Baseline updated in place (243 pass, 244 new).

## Notes

* **Normal-to-Sensor view (same flag, separate commit).** The flag also asked: *"Every time I have to
  zoom in ISO view in order to see this sensor overlay analysis. Possible to implement Normal view to
  fill the 3D canvas?"* Added `Kraken3DInspector.view_normal_to_sensor` (Overlays ▸ **Normal to
  Sensor**): snaps the camera face-on down the detector normal, orthographic, parallel-scaled to the
  sensor so the orange square + overlay fill the canvas. It resolves the sensor dims through the
  **same** vendor override the heatmap uses (`_camera_detector_active_dims_overrides`) — a headless
  smoke test caught that the target row's `active_width_mm` is 0 in the vendor-glue case, so without
  the override consult the view would have framed a 10 mm fallback instead of the real 39×39.
* **In-app eyeball owed.** The headless fixture reproduces both mechanisms and the guard locks them in,
  but the user's running vendor-STEP scene still owes a visual check that the heatmap now fills the
  orange square with 2-dark / 2-uniform, and that "Normal to Sensor" frames the sensor face-on.
* This closes the "ray density is a separate quality knob" thread left open in the 0276 notes: the
  window is the sensor (0276) **and** the map now reads the smooth fold/perp gradient at sparse density
  (0277).
