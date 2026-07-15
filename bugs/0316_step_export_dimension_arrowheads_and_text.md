# 0316 — Exported STEP dimensions are "only lines, no arrow, no text"

## Flag
`attachment/recorded_bug_repros/flag_20260715_125033_313/`:

> *"refer freecad.png, the output of the thickness overlay is only lines, no arrow, no text."*

`attachment/freecad.png` (the exported STEP re-opened in FreeCAD) shows the dimension leaders as
bare tubes — the shaft + two witness lines — with **no arrowheads** at the ends and **no numeric
value** beside them. On screen the same dimension draws cone arrowheads and a `"↔ 32.92 mm"` label,
so the export was dropping two of the three things a dimension *is*.

Not stale: the user had just confirmed *"0314 works, 0313 works, 0312 works"* in-app, so the blue
physical-distance export (0313) and orange Measure-tool export (0315) were both landing lines in the
STEP. This is a genuine scope gap on top of a working export, not a regression — 0313/0315 only ever
emitted the shaft + leaders.

## Root cause — the collectors emit only 3 lines; arrowheads + text were never built
The STEP writer (`_write_step_with_cad_shapes_and_rays`) turns each `dimension_polylines` entry into
solid tubes by walking its **consecutive segments** (`for start, end in zip(pts[:-1], pts[1:])`), so
it can already tube an arbitrary multi-point polyline. But both dimension collectors handed it only:

- `open3d_thickness_dimensions._record_export_dimension` (blue) → `[shaft, leader, leader]`
- `open3d_inspector.collect_measure_export_geometry` (orange) → `[shaft, leader, leader]`

No arrowhead geometry, no text geometry was ever produced — so the STEP faithfully tubed exactly the
three lines it was given. The on-screen cone heads are VTK `vtkConeSource` actors and the value is a
`vtkBillboardTextActor3D`; neither has an export path, and a STEP file cannot carry a billboard label.
`OCC.Core.Font` is **not available** in this pythonocc build (and per the project's tooling rule we add
no external font dependency), so real embedded text was off the table.

## Fix — one shared annotation funnel: barbs + vector-stroke text as ordinary polylines
New `KrakenOS/UI/services/dimension_export_geometry.py`:

- **`dimension_annotation_polylines(base_lo, base_hi, start, end)`** returns, per dimension:
  1. the **STABLE trio** — `shaft (start→end)`, `leader (base_lo→start)`, `leader (base_hi→end)` —
     byte-for-byte the pre-0316 output, so every existing endpoint assertion still holds;
  2. **open-chevron arrowheads** — one 3-point barb polyline per end (`wing → tip → wing`), tips
     exactly on the shaft ends, wings spread in the dimension plane (size `clamp(span*0.06, 2, 12)`,
     matching the on-screen cone head);
  3. the **numeric value text** — `f"{span:.4g} mm"` rendered by an in-process **vector stroke font**
     (seven-segment digits + hand-drawn `. m space - + e`), centered above the shaft, clear of the barbs.

  Everything it returns is a ≥2-point polyline, so it rides the writer's existing segment-by-segment
  tubing with **no writer or plumbing change** — arrowheads and text tube exactly like the shaft.

- Both collectors now funnel their four resolved points through this one helper:
  `_record_export_dimension(base_lo, base_hi, start, end)` and
  `collect_measure_export_geometry` (per segment, `dimension_annotation_polylines(p0, p1, a0, a1)`).
  So the fix lands for **both** the blue physical-distance overlay and the orange Measure tool at once,
  and a future annotation type gets barbs + text for free by calling the same funnel.

Per *"guard the invariant, not the instance"*: the invariant is **every dimension the 3D view shows —
line, arrowhead, and value — must be in the exported STEP.** 0313/0315 satisfied the line; 0316 closes
the arrowhead + value for both overlays through the shared funnel.

## Verified (display-free)
`KrakenOS/UI/validate_open3d_step_export_dimension_annotations.py` — **PASS (21 checks)**:
- **A** the STABLE trio is polylines 0/1/2 with exact endpoints; every entry is a finite Nx3 path.
- **B** two 3-point barb chevrons follow the trio, tips on the shaft ends, wings straddling the line.
- **C** the value text is the numeric span (`"32.92 mm"`), its stroke count equals the font's glyph
  strokes, every glyph resolves, and `dimension_value_text` rounds via `%g` + always carries `mm`.
- **D** the **entire** annotation (trio + barbs + text) is coplanar (max off-plane `0.0`) — a flat
  dimension, never a supernatural scribble in 3-space.
- **E** fed to the real OCC writer, `dimension_count` equals the polyline count and every polyline
  segment becomes a solid tube (35 polylines → 37 solids for the sample).
- **F** both collectors route through `dimension_annotation_polylines`.
- **G** a degenerate (zero-span) dimension keeps the trio and adds nothing.

Non-regression: `validate_open3d_step_export_thickness_dimensions` (0313) now **PASS (27)** and
`validate_open3d_step_export_measure_dimensions` (0315) now **PASS (20)** — their polyline-count
assertions derive from `annotation_polyline_count(...)` while the first-three endpoint asserts are
unchanged. Penta **phase 278** (`phase_278_step_export_dimension_annotations`) delegates to the new
guard; baseline updated (`"278": "pass"`).

## Files
- `KrakenOS/UI/services/dimension_export_geometry.py` — new: vector stroke font, arrowhead barbs, and
  the shared `dimension_annotation_polylines` funnel.
- `KrakenOS/UI/services/open3d_thickness_dimensions.py` — `_record_export_dimension` routes through the
  funnel.
- `KrakenOS/UI/open3d_inspector.py` — `collect_measure_export_geometry` routes through the funnel.
- `KrakenOS/UI/validate_open3d_step_export_dimension_annotations.py` — new display-free guard.
- `KrakenOS/UI/validate_open3d_step_export_thickness_dimensions.py`,
  `KrakenOS/UI/validate_open3d_step_export_measure_dimensions.py` — count assertions track the helper.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_278`.
- `tools/penta_validator_baseline.json` — phase 278 baseline + title.

## Notes / remaining
- Same CAD-path scope as 0313/0315: dimension tubes ride `_write_step_with_cad_shapes_and_rays`, so a
  pure-analytic export (no imported CAD) still carries none. The user's scene has imported camera + lens
  CAD, so the CAD path is taken and the dimensions (now with arrowheads + text) export.
- In-app eyeball owed (needs a GLX display): open a scene with imported CAD, place a Measure-tool
  dimension (and/or turn on the physical-distance overlay), Export 3D Assembly STEP, and confirm the
  exported file shows barbed arrowheads and the stroked value in FreeCAD. The display-free guard proves
  the per-dimension geometry, the coplanar invariant, the font stroke count, and the OCC round-trip.
