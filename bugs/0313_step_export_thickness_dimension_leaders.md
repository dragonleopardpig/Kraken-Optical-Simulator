# 0313 — Export the thickness dimension overlay into the 3D STEP (task #483)

Follow-on to **bugs/0300** ("STEP export faithful to display"), which shipped the export of analytic
surfaces, imported CAD BReps, ray-envelope tubes, and the Object/Image planes but *deferred* the physical-
distance (thickness) dimension overlay with the note: *"can be added as opt-in leader-line geometry (like the
ray cylinders) if the user wants it."* This is that increment.

## What ships
When the **physical-distance overlay is shown** (`show_physical_distances_var`), a 3D STEP export now also
writes every thickness/gap dimension as **solid leader tubes**: per dimension a shaft offset off the optical
axis plus two short leaders back to the two surface reference points — the same shaft + leaders the overlay
draws on screen, minus the text label.

- Gated on the toggle and carried on the **CAD path only** (`_write_step_with_cad_shapes_and_rays`), exactly
  like the ray envelope. A pure-analytic export (no imported CAD) is unchanged.
- The completion status now reports `dimension_leaders=N` alongside `ray_envelopes=N`.

## The one design fork — offset must be deterministic, text can't be baked
The on-screen overlay is **view-dependent**: the side it stands off the axis comes from the live camera
(`_camera_screen_world_axes` / `offset_direction`) so it always reads to the side of the axis in the current
view, and it carries a **billboard text label**. A STEP file has neither a camera nor billboard text. So:

* **Offset is forced view-free.** The export re-runs `offset_direction(segment, view_normal=None)` — the pure
  geometric perpendicular (world −X for a Z-axis span, +X for a folded-arm Y span) — so the exported side is
  the same deterministic world frame every run, not whatever the camera happened to be at export time. The
  *measured span* between the two surface points is identical to the display; only the annotation side is
  fixed.
* **No text.** STEP can't carry a billboard label; the offset leader geometry itself reads as the dimension.

## How it stays faithful — one decision path, a geometry sink (not a re-implementation)
The tempting shape was a second loop that re-derives which dimensions to draw. That would drift from the
overlay the moment either side changed (this export must track cross-arm skips, branch-detector supersede,
promoted-solid spans, fold-detector redirects, overlay carve, re-anchored + LED-edge dims — all the special
cases in `add_overlays`). Per *"guard the invariant, not the instance"*, the export instead **re-runs the
exact same `add_overlays`** with a capture sink:

- `Open3DThicknessDimensionService._dimension_geometry_sink` — when set to a list, `add_overlays` forces the
  view-free offset and every emit **records** its shaft + two leader polylines into the sink instead of
  drawing actors, then returns the same count. `_emit_span_dimension` is the single funnel for the row loop,
  re-anchored, and LED-edge dims; `_branch_distance_overlays` (which draws directly) records too.
- `collect_export_geometry(system, scene_bundle)` sets the sink, calls `add_overlays`, and restores state.
  It preserves the live `_trailing_spacer_gap_offset` (add_overlays rebuilds it) so an export pass never
  disturbs the on-screen edit dialog. It runs on the **main thread at export time**, where the live plotter's
  `_step_actor_map` is present — so the overlay carve around imported bodies matches the display exactly.

Because both the screen overlay and the export are the *same* traversal, the export can never silently drift
from what is shown.

## Data flow
`export_3d_step` (CAD branch) → `_step_export_dimension_polylines(system)` (editor side: toggle gate +
`inspector._open3d_thickness_dimension_service().collect_export_geometry(system, inspector._current_scene_bundle)`)
→ `_start_native_step_export_worker(..., dimension_polylines, ...)` → worker →
`_write_step_with_cad_shapes_and_rays(..., dimension_polylines=...)` tubes each 2-point polyline with the
shared `BRepPrimAPI_MakeCylinder` builder (radius `max(ray_tube_radius·1.4, 0.12)` — a touch fatter than rays
so an annotation reads distinct from the beam beside it). The writer now returns
`(analytic, cad, ray, dimension)`.

## Verified (display-free)
`KrakenOS/UI/validate_open3d_step_export_thickness_dimensions.py` — **PASS (25 checks)**:
- **A** record helper emits shaft + 2 leaders with exact endpoints; no-op when the sink is None.
- **A2** the real funnel `_emit_span_dimension` records the **offset** shaft (`base_lo + side·base_offset`).
- **B** the view-free `offset_direction` is unit-length, perpendicular, and deterministic for Z / folded-Y /
  X axes.
- **C** the OCC writer tubes the polylines: two dimensions (6 leader polylines) → `dimension_count == 6` and
  **+6 solids** in the re-read STEP vs. the no-dimension export; the optics/cad/ray counts are unchanged.
- **D** the editor collector returns `[]` when the toggle is off and when no 3D inspector is open (parity
  with rays exporting only when shown).
- **E** structural wiring: emit short-circuits into the sink, the per-branch overlay records, `add_overlays`
  forces the view-free offset on export, the collector preserves the spacer map and gates on the toggle, and
  `export_3d_step` → worker → writer thread `dimension_polylines` end to end.

Penta **phase 275** (`phase_275_step_export_thickness_dimensions`) delegates to that guard; baseline updated
(`"275": "pass"`). The existing `validate_step_native_export.py` still PASSes with the writer's new 4-tuple
return (its unpack was updated, as was `validate_five_penta_native_step_export.py`).

## Files
- `KrakenOS/UI/services/open3d_thickness_dimensions.py` — `_dimension_geometry_sink`, `collect_export_geometry`,
  `_record_export_dimension`; `add_overlays` forces the view-free offset on export; `_emit_span_dimension` and
  `_branch_distance_overlays` short-circuit into the sink.
- `KrakenOS/UI/services/optical_solid_workflow.py` — `_step_export_dimension_polylines` (toggle + inspector
  gate, deterministic capture).
- `KrakenOS/UI/services/layout_import_export.py` — `export_3d_step` collects + threads `dimension_polylines`;
  `_start_native_step_export_worker` forwards it; completion message reports `dimension_leaders`.
- `KrakenOS/UI/services/cad_step_export.py` — `_write_step_with_cad_shapes_and_rays` takes `dimension_polylines`,
  tubes them, returns `(analytic, cad, ray, dimension)`.
- `KrakenOS/UI/validate_open3d_step_export_thickness_dimensions.py` — new display-free guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_275_step_export_thickness_dimensions`.
- `tools/penta_validator_baseline.json` — phase 275 baseline + title.
- `KrakenOS/UI/validate_step_native_export.py`, `validate_five_penta_native_step_export.py` — 4-tuple unpack.

## Notes / remaining
- In-app eyeball owed (needs a GLX display): open a scene with imported camera/lens CAD, turn on physical
  distances, Export 3D Assembly STEP, and confirm the exported file carries the dimension leader tubes off to
  the side of each element (and none when the toggle is off). The display-free guard proves the record helper,
  the deterministic offset, the OCC tubing, the toggle gate, and the full wiring; the live `add_overlays`
  traversal is the same path the on-screen overlay already exercises.
