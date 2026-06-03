# 0009 — Persistent thickness overlay skips an imported lens (measures straight through)

**Status:** Fixed. The persistent Open 3D thickness overlay now breaks each
row→row span around any imported optical body that sits between the two
surfaces, drawing a physical edge-gap dimension on each clear side (matching the
live drag readout the user confirmed is correct) instead of one arrow straight
through the lens. The shared dimension line thickness was also bumped, so both
the persistent overlay and the live readout read thicker.
**Component:** Open 3D inspector — persistent thickness overlay
(`Open3DThicknessDimensionService.add_overlays`) and its placement in the scene
refresh (`Open3DSceneRefreshService.refresh_scene`).
**Reported via:** in-app recorder, flag `flag_20260603_133340_743`.

## Symptoms (user's words)

> the thickness overlay skip the lens element and measure the next element while
> the live measurement during dragging is correct, the line thicness of botht
> the live distance and the overlayed distance should increase.

Two requests: (1) the persistent "S0 Thickness = 100 mm" arrow paints straight
across the imported lens to the next analytic surface, skipping the lens body;
the live drag readout ("gap = 44.12 mm", Object→lens-front) is correct and is the
reference behaviour; (2) thicken the line of *both* the live and the persistent
distance.

## State evidence

`flag_20260603_133340_743/state.json` (captured 2026-06-03T13:33:40, recording
active):

* `scene_state.step_actor_bounds["optical"]` z-span = **44.12319 .. 55.70319** —
  the imported optical body lies between Object(z=0) and Image(z=100), with a
  44.12 mm clear gap to the Object (exactly the live readout's "gap = 44.12 mm")
  and ~44.30 mm to the Image.
* `scene_state.thickness_dimension_count = 2` — a *single* dimension (one arrow +
  one framed label) was drawn for the Object→Image row span, i.e. one
  "S0 Thickness = 100 mm" arrow painted across the lens, never split.
* `selected_step_label = "optical"`, `picked_step_label = "optical"` — the lens
  overlay was present and selected.
* `optical_axis_records`: the global guide axis spans z=-65..165.

## Behaviour before

The persistent overlay walked **analytic table rows only**. For each
consecutive pair (S0 Object → S1 Image) it drew one row→row arrow labelled
`S{i} Thickness = {mm}`, with no knowledge of imported STEP bodies. An imported
lens between the two surfaces was therefore invisible to it, and the single
arrow measured Object→Image (100 mm) straight through the lens.

The live drag readout (`Kraken3DInspector._step_overlay_axial_gap` →
`_scene_component_axial_extents`) does *not* have this blind spot: it enumerates
both analytic rows **and** imported `_step_actor_map` overlays, so it correctly
reported the 44.12 mm edge-to-edge gap to the body in front — the behaviour the
user pointed to as correct.

## Root cause

Two compounding causes, both fixed:

1. **Logic gap.** `add_overlays` never consulted the imported overlays, so it
   could only ever draw a row→row arrow — across any lens between the rows.

2. **Refresh ordering.** Once `add_overlays` was taught to split (below), the
   split still did not fire live. In `refresh_scene`, `_step_actor_map` is
   cleared at the top and the imported STEP bodies (the `"optical"` overlay) are
   not re-registered until the STEP overlay loop *late* in the method. The
   thickness-dimension call sat **before** that loop, so it ran against an empty
   `_step_actor_map`, found no body between the surfaces, and fell back to the
   single full-span arrow. (The live readout avoids this because it runs
   on-demand *after* the refresh, when the map is already populated.)

## Fix

* **`KrakenOS/UI/services/open3d_thickness_dimensions.py`** — overlay awareness +
  thicker lines:
  * `add_overlays` now, per row span, projects the two surfaces onto the span
    axis, asks `_overlay_axial_spans_within` for any imported body whose centre
    lies strictly between them, and `split_span_at_overlays` carves the clear
    gaps. Each clear gap is drawn by `_emit_span_dimension` as a physical
    edge-gap dimension (`gap = .. mm`); with no intervening body it stays the
    original single `S{i} Thickness = .. mm` arrow. A split arrow still edits the
    owning row's thickness (drag spans the whole row).
  * Shared thickness knobs `DIMENSION_TUBE_RADIUS_FACTOR` (0.18 → 0.36),
    `DIMENSION_TUBE_RADIUS_FLOOR`, `DIMENSION_LEADER_LINE_WIDTH` (1.4 → 2.2),
    consumed by both the persistent overlay and the live readout.

* **`KrakenOS/UI/services/open3d_scene_refresh.py`** — moved
  `thickness_dimensions = self._add_thickness_dimension_overlays(...)` from before
  the STEP overlay loop to **immediately after** it (after the imported bodies
  register into `_step_actor_map`), so the split has the lens to split around.
  This is the fix that makes the split actually fire on screen.

* **`KrakenOS/UI/open3d_inspector.py`** — the live drag readout
  (`_draw_step_translate_gap_overlay`) leader now uses
  `service.DIMENSION_LEADER_LINE_WIDTH`; its arrow already shares
  `service.arrow_mesh`, so both distances thicken from the same constants.

## Tests

* **`validate_open3d_thickness_overlay_skips_lens`** (display-free, 12 checks) —
  pins the split math without a display: no body → single span; a body between
  → two gaps whose near gap equals the live readout's 44.12319; a body covering
  the span → safe fallback; two bodies → three gaps; `_overlay_axial_spans_within`
  keeps only bodies centred between the surfaces; the thickness constants are
  bumped and the rendered tube is materially thicker than the legacy radius; and
  it source-couples `add_overlays` → `split_span_at_overlays`/`_emit_span_dimension`,
  the persistent leaders and the live readout → `DIMENSION_LEADER_LINE_WIDTH`.

* **`validate_open3d_thickness_overlay_skips_lens_snapshot`** (image-snapshot,
  boots its own Xvfb) — imports the tracked prism between Object(z=0) and
  Image(z=100), centres it on z=50, forces a side view, and isolates the
  dimension *arrow* meshes (hide every prop → blank frame, then show only the
  `vtkActor` arrow shafts; the translucent lens and the framed labels are kept
  out of the diff so neither can pollute it). With the lens present the two gap
  arrows span ~91 screen columns each and **zero** columns cross the lens
  interior; as a sensitivity control, removing the lens collapses the overlay to
  one full-span arrow that crosses the same central band (~40 columns) — proving
  the band detects a crossing and that the fix specifically cleared it. Uses the
  tracked prism fixture, so it always runs; verified by eye (two
  `gap = 37.5 mm` dimensions, no arrow through the lens).

* **Regression / end-to-end** — `Phase 16` in
  `validate_open3d_penta_telescope_comprehensive.py`.
