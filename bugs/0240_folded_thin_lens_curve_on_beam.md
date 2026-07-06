# 0240 — Imaging-lens surrogate drawn off the folded beam (thin-lens glyph strands at x=0)

## Symptom
flag_20260706_130527_037, on the promoted two-fold AZ85 periscope: after a 55×55 mm FOV
solve-for-thickness the user reported **"the lens surrogate shifted"** — the imaging lens (Blackbox
Group 1 / Group 2, drawn as **Thin Lens** rows 4 and 6) appeared off the ray path while the rest of
the folded arm (datum planes, aperture stop, lens surface mesh, rays) sat correctly on the beam.

## Root cause
In Non-Sequential Preview (`use_folded=False`) every surface curve is built by
`_build_sequential_surface_curves` → `_row_layout_polylines(system, row_index, z_pos)`. That callback
folds a curve onto the promoted-mirror branch by applying the **system world transform**
(`system.Pr3D.TRANS_2A[row_index]`) to the surface's local outline:

- **Standard / Aperture** rows compute `world_pts = (transform @ local).T` and return the **full 3-D
  world** outline (`world_pts[:, :3]`) — so they land folded on the +X arm (e.g. x = 70 / 97.5 / 125).
- The **Thin Lens** branch routes through `thin_lens_glyph_polyline(row, z_pos, transform=…,
  project_fn=_project_xy)`. It *did* apply the same world transform, but then kept only
  `world_z = world[:, 2]` and `world_y = world[:, 1]`, **discarding the folded world X**, and passed
  `(world_z, world_y)` through `project_fn`. `_surface_polyline_world_points` then lifted that 2-column
  result back into 3-D at **x = 0**.

So the glyph inherited the folded Z (207.4) but was stranded on the straight +Z axis (x = 0) while the
lens surface **mesh** — built by a different path — folded onto the beam at x ≈ 87.6 / 107.3. The lens
outline and its solid therefore drew in two different places: the "shifted surrogate."

## Fix
In `thin_lens_glyph_polyline` (`layout_plot_controller.py`), after applying the world transform, return
the **full 3-D world outline** (`world[:, :3]`) when both:

1. a `project_fn` is supplied (the real 3-D display path), and
2. the transform genuinely folds the glyph off the +Z axis: `max |world_x| > _FOLDED_GLYPH_OFF_AXIS_MM`
   (1.0 mm).

This mirrors the Standard-surface curve path exactly, so the drawn lens follows the folded beam. When
the glyph is on-axis (plain sequential layout, `world_x ≈ 0`) it falls through to the byte-identical
2-D projection, and the 2-D layout-controller callers (which pass **no** `project_fn`) are untouched —
both requirements gate the new branch.

This is a **display-follows-physics** fix: the folded world position the transform already computed is
what gets drawn, instead of being projected away and re-seated at x = 0.

## Verification
`KrakenOS/UI/validate_open3d_folded_thin_lens_curve_on_beam.py` (penta **phase 217**):

- **LENS ON BEAM** — on the two-fold after `fov_solve("object","thickness",55,55)` every kind="thin_lens"
  surface curve is off the +Z axis (|x,y| > 5 mm) and coincides (≤ 3 mm) with its own row's folded
  surface mesh (rows 4 → x ≈ 87.6, 6 → x ≈ 107.3).
- **GLYPH 3-D WHEN FOLDED** — `thin_lens_glyph_polyline` with a 90°-fold transform + a `project_fn`
  returns a 3-column outline whose folded X (≈ 92) is preserved.
- **GLYPH 2-D ON-AXIS** — an on-axis transform + `project_fn` keeps the 2-column projection path.
- **STILL IMAGES** — rays still reach the single folded detector.

`validate_layout_plot_controller` still passes (its transform case passes no `project_fn`, so the glyph
shape contract is unchanged). The glyph is a VTK render and can't be pixel-validated headless (llvmpipe
SIGSEGV); this guard checks the bundle geometry the renderer consumes. In-app visual confirm owed
(restart the app onto this build, redo the folded solve, confirm the imaging lens draws on the beam).

## Out of scope (noted)
The promoted RA-mirror `stl_solid` **outline curve** for the *second* mirror (row 8) is still stranded
at x = 0, but the mirror is drawn as a real folded STEP **solid** (body mesh, on-beam) and the user did
not report it. Left for a follow-up if the in-app confirm shows a stray mirror outline.
