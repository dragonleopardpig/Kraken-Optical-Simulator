# 0315 — The manual Measure-tool dimensions are missing from the 3D STEP export

## Flag
`attachment/recorded_bug_repros/flag_20260715_113521_943/` (imported camera + lens, two RA-mirror
folds):

> *"exported STEP file (with manual thickness overlay, no saving), refer attachment/freecad.png,
> thickness overlay is not exported."*

`attachment/freecad.png` (the exported STEP re-opened in FreeCAD) shows the camera body, the lens
barrel, and the two fold prisms — but **no dimension leaders at all**.

## Root cause — 0313 exports only the BLUE overlay; the user drew ORANGE Measure dimensions
Two different on-screen annotations look like "thickness dimensions":

1. **The automatic physical-distance overlay** (`show_physical_distances_var`), drawn **blue**
   `(0.05, 0.42, 0.70)`. bugs/0313 (task #483) teaches the STEP export to tube *this* overlay.
2. **The manual Measure tool** (`_measure_segments`), drawn **orange** — dimension line
   `(0.95, 0.55, 0.1)`, witness lines `(0.95, 0.7, 0.4)`. This is what the user means by *"manual
   thickness overlay"*: point-to-point measurements they placed by hand.

The recording proves it was the Measure tool, not the physical-distance overlay:
`state.json` has **`thickness_dimension_count: 0`** (no automatic overlay actors), yet the screenshot
shows **orange** dimension leaders — the Measure tool. bugs/0313 has **no export path for
`_measure_segments`**, so the STEP carried no dimensions and FreeCAD showed none.

(The app was *not* stale — its process started 11:19, after the 0313 commit at 10:49, so it had the
0313 code. This is a genuine scope gap, not a regression: 0313 shipped the automatic overlay and
deferred nothing about the Measure tool because the two were never connected.)

## Fix — export the Measure-tool segments too, reusing the SAME resolver
- **`Kraken3DInspector.collect_measure_export_geometry()`** — for every **visible** measure segment
  (skipping `_hidden_measure_segments`), emit the same three world polylines the on-screen overlay
  draws: the offset dimension shaft `a0→a1` plus the two witness lines `p0→a0` and `p1→a1`, minus the
  billboard label and grab handle. It reuses the exact `_measure_segment_offsets` /
  `_measure_segment_offset_endpoints` the draw loop uses, so the exported tubes can never drift from
  what is shown (same invariant approach 0313 took with `add_overlays`).
- **`_step_export_dimension_polylines`** now folds those polylines into `dimension_polylines`
  **independent of the physical-distance toggle** — a measurement is its own annotation, so it exports
  whenever it is shown, exactly like the orange dimension on screen. The physical-distance path is
  unchanged (still toggle-gated); both feed the one list the shared ray-tube writer already tubes, so
  **no writer change**.

The collector was restructured to check the 3D inspector first, then run the (toggle-gated)
physical-distance path and the (always-on) measure path into a shared absorb helper. When there are no
measure segments and the toggle is on, the returned list is byte-for-byte the old 0313 result.

## Why the shared writer, not a second export
Per *"guard the invariant, not the instance"*: the invariant is **every dimension the 3D view shows
must be in the exported STEP.** 0313 satisfied it for the blue overlay; this closes it for the orange
Measure tool. Both annotations resolve their geometry through their own display resolver and hand
2-point polylines to the same `dimension_polylines` sink, so the export tracks the display for both,
and a future annotation type needs only its own `collect_*` + one `_absorb(...)` line.

## Verified (display-free)
`KrakenOS/UI/validate_open3d_step_export_measure_dimensions.py` — **PASS (18 checks)**:
- **A** geometry: a visible segment → shaft (offset `a0→a1`) + witness `p0→a0` + witness `p1→a1` with
  exact endpoints; two segments → 6 polylines, each a 2×3 world segment, the second shaft distinct.
- **B** hidden segments (`_hidden_measure_segments`) are skipped; no segments → `[]`.
- **C** `_step_export_dimension_polylines` exports the measure dims **even when the physical-distance
  toggle is OFF** (the fix — the pre-fix code early-returned `[]`), combines physical + measure when
  ON, returns `[]` with no 3D inspector, and skips an unresolvable segment without failing.
- **D** the export reuses the exact `_measure_segment_offset_endpoints` / `_measure_segment_offsets`
  the on-screen `_refresh_measure_overlays` draw loop uses, and the measure absorb is not nested under
  the physical-distance toggle branch.

The bugs/0313 guard `validate_open3d_step_export_thickness_dimensions` still **PASS (25 checks)** with
the refactored collector. Penta **phase 277** (`phase_277_step_export_measure_dimensions`) delegates
to the new guard; baseline updated (`"277": "pass"`).

## Files
- `KrakenOS/UI/open3d_inspector.py` — `collect_measure_export_geometry`.
- `KrakenOS/UI/services/optical_solid_workflow.py` — `_step_export_dimension_polylines` folds in the
  measure polylines independent of the physical-distance toggle.
- `KrakenOS/UI/validate_open3d_step_export_measure_dimensions.py` — new display-free guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_277_step_export_measure_dimensions`.
- `tools/penta_validator_baseline.json` — phase 277 baseline + title.

## Notes / remaining
- Same CAD-path scope as bugs/0313: dimension tubes ride `_write_step_with_cad_shapes_and_rays`, so a
  pure-analytic export (no imported CAD) still carries none. The user's scene has imported camera + lens
  CAD, so the CAD path is taken and the measure dims export.
- In-app eyeball owed (needs a GLX display): open a scene with imported CAD, place a few Measure-tool
  dimensions (physical-distance overlay left OFF), Export 3D Assembly STEP, and confirm the exported
  file carries the measurement leader tubes in FreeCAD. The display-free guard proves the per-segment
  geometry, the toggle-independent collection, and that the export reuses the on-screen resolver.
