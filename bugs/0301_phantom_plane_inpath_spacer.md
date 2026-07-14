# 0301 — phantom plane between the RA mirror and the imaging lens in the STEP export

User report (2026-07-14), `attachment/STEP2.png`, same AZ85 folded periscope as bugs/0300: the
exported STEP shows a **phantom plane between the first RA mirror and the imaging lens**. It is not a
physical element and pollutes the production model.

## Root cause

A promoted optical solid (the BK7 RA prism) does not occupy a single prescription row. Its **front**
face carries the body STL (`Solid_3d_stl`, row j=1), and it is followed by an **in-path gap-carrier**
row (j=2). That carrier is the bugs/0079/0093 mechanism: an AIR row that keeps the solid's large clear
aperture (Diameter 25 mm) in the beam path so the sequential trace never clips — it is *bookkeeping*,
not a physical surface. On AZ85 it sits at world `[27.5, 0, 50]`, right after the prism.

`diag_0301_phantom_plane.py` shows it:

```
 j surface  name                  glass  Diam  Draw revol stl?  world           advanced
 1 Standard Promoted OPTICAL STEP  BK7   25.00 True False True  [-0.0,0,50]  Solid_3d_stl=…  <- prism body (STL shell)
 2 Standard Promoted OPTICAL STEP  AIR   25.00 True True  False [27.5,0,50]  InPathTrailingSpacer=True  <- PHANTOM
```

The **3D inspector already skips it** — `_iter_3d_optical_surface_meshes`
(`services/three_d_scene_tools.py`) does `if advanced.get("InPathTrailingSpacer"): continue`
("bugs/0093: … don't draw its big flat clear-aperture disk … 'why is there a big circle?'"). But the
STEP **analytic writers** only gated on `Drawing` / `Diameter>0` / revolution-compatible, so they drew
the carrier as a flat 25 mm disc. Export diverged from the display — the same class as bugs/0300
(**the export must be exactly what the 3D shows**).

The display loop skips a second such row too: `StepAnalyticBodyOmitMesh` — the trailing face of an
analytic-promoted body whose front row owns the body STL (the body mesh already includes that face).

## Fix

One shared predicate, so display and export cannot drift (`services/cad_step_export.py`):

* `_row_is_non_physical_reference(row)` — `True` for a row flagged `InPathTrailingSpacer` or
  `StepAnalyticBodyOmitMesh` (exactly the flags `_iter_3d_optical_surface_meshes` skips on).
* Both analytic writers (`_write_step_with_analytic_surfaces`,
  `_write_step_with_cad_shapes_and_rays`) skip such a row at the top of the surface loop, before the
  Drawing / Diameter guards.

The optical-solid rows themselves (revolution-incompatible, exported as STL shells via bugs/0300) are
unaffected; only the non-physical carrier/omit rows are dropped.

## Result (display-free)

* `diag_step_export_full.py`: writer `analytic_surfaces` **8 → 7** (the carrier disc is gone; Object +
  Image reference planes still counted).
* `diag_step_export_end_to_end.py` read-back: **no body at x≈27.5** between the prism (shells at x≈0)
  and the lens (x≈206); both prisms `[0,0,50]` / `[304.19,0,50]`, Object disc `[0,0,0]` (116 mm) and
  Image disc `[304.19,0,0]` (32.58 mm) unchanged.

## Guard

Facet **D** added to `KrakenOS/UI/validate_open3d_step_export_matches_display.py` (penta **phase
264** — the same "export matches display" invariant as bugs/0300, guarded not re-instanced):

* **D1** — both STEP writers call `_row_is_non_physical_reference` (source).
* **D2** — the predicate's flags equal the display's skip flags (`InPathTrailingSpacer` +
  `StepAnalyticBodyOmitMesh` present in both the predicate and `_iter_3d_optical_surface_meshes`).
* **D3** — on AZ85 the gap-carrier row (which passes Drawing/Diameter/revolution, i.e. *would* draw a
  disc) is excluded by the predicate, while the Object plane is not.
