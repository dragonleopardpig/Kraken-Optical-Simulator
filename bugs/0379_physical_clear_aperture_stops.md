# 0379 — User-specified physical clear-aperture (CA) stops from picked edges

**Flags:** 20260721_092541 ("CA of the CO90 output is 51×51.5mm, is this CA detected? If not, we need a
flow that let user to specify all physical CA opening") + 093143 ("Another CA opening dimension:
55×74mm"). User clarifications: **click the CA boundary EDGES and set it as an aperture** (the pick
carries the CA's LOCATION, which a numeric entry would lose); the front window is a closed loop but the
back opening is **3-sided** (no closed loop) — must still be pickable; build the rectangle from the
**3 edges** (2 opposite edges also, less accurately); and the CAs must be **real ray stops**.

**Status:** SHIPPED 2026-07-21. Geometry + ray-stop filter + illumination-trace wiring (phase 319);
the existing face-CA is now a real ray stop; the interactive multi-EDGE pick + persistence + draw
(phase 320). Live in-app eyeball owed (VTK interaction can't run headlessly).

## Why it happened

A decoration STEP overlay (`STEP_OVERLAY_DECORATION_LABELS = led/camera/lens`) is display-only — the
ray trace never uses its geometry, and the illumination emitter is auto-sized to the module's full
axis-aligned bounding box (bugs/0290), not its real CA window. So the CO90's real openings (front
output 51×51.5, back 55×74) are ignored, and the "Set Clear Aperture (pick window FACE)" primitive
cannot capture the 3-sided back opening (no closed face/loop to click).

## The core (shipped)

`services/clear_aperture_stops.py` (pure, display-free):
- `rect_from_edges(edges)` — builds a rectangular CA from one or more picked edge polylines. The plane
  through the edges (least-variance SVD direction) is the CA's **location**; the in-plane bounding box
  of ALL picked points is the opening. A closed loop, **3 edges**, or **2 opposite edges** all yield the
  SAME rectangle (the missing side is the box closing itself). Returns `{center, normal, u_axis, v_axis,
  half_u, half_v}`.
- `ray_passes_apertures(polyline, cas)` / `filter_illumination_records(records, cas)` — a ray is
  vignetted iff its traced path crosses a CA plane OUTSIDE that CA's opening (a ray that never reaches
  the plane is not blocked by it).

Wired into `three_d_scene_tools._coupled_object_illumination_records` via `_apply_clear_aperture_stops`
(reads the `_clear_aperture_rects_by_label` store; **no-op until a CA is specified**, so all existing
scenes are unchanged). Verified: 3-edge / 2-edge / loop pick recover the same rectangle; a stored CA
vignettes illumination rays that miss the opening.

## The interactive pick (shipped)

Right-click a decoration STEP overlay → **"Set Clear Aperture (pick EDGES: loop / 3 sides)…"**. This
arms an edge-collect mode (reuses the single-pick `STEP_CLEAR_APERTURE_PICK` mode via a
`_step_clear_aperture_pick_edges` sub-flag, so cancel / mode badge / empty-space handling all still
apply). Each LEFT click collects the geometry under the cursor — **plain hover gives the whole opening
loop** (front window, one click), **Alt gives the nearest drawn edge** (the 3-sided back, three clicks).
Hover and click both resolve through the SAME `_step_feature_pick_for_display_xy`, so what highlights is
what gets collected (avoids the bugs/0324 two-stream trap). Right-click → **"Finish Clear Aperture Edges
(N)"** builds the rectangle and stores it; a stray empty click keeps the buffer (only Esc/cancel drops
it). The green rectangle is drawn at its plane during refresh (`_add_clear_aperture_edge_rect_actors`,
folded into the recorded-face highlight so both refresh sites draw it). "Forget Clear Aperture Edges"
removes them.

## Not done / deferred

- Size the illumination EMITTER to the limiting CA (replace the bugs/0290 module-bounds auto-seed), and
  apply the filter in the "Illum rays" preview overlay too.
- Wire the measured ~35–40 mm fold CA into the coaxial descriptor to retire the `55·cos45` synthetic.

**Physics note carried forward (bugs/0376 / the coaxial KB):** the 51×51.5 output CA still over-fills
the 39×39 FOV, so specifying it sizes the source correctly but does not by itself make the 2-side fold
dark edges — those need a **downstream** ~35–40 mm fold-axis stop, which this same flow can now express
once picked.

## Files

- `KrakenOS/UI/services/clear_aperture_stops.py` — geometry (`rect_from_edges`) + ray-stop filter.
- `KrakenOS/UI/services/three_d_scene_tools.py` — `_clear_aperture_stop_rects` (unifies face-CA outlines +
  edge rects) + `_apply_clear_aperture_stops` in the object-illumination records; `add_/clear_/
  remove_clear_aperture_edge_rects` store API.
- `KrakenOS/UI/services/layout_settings.py` — `clear_aperture_edge_rects_by_label` snapshot + restore
  (`_portable_clear_aperture_rect`).
- `KrakenOS/UI/open3d_inspector.py` — `start_/finish_step_clear_aperture_edge_pick`,
  `_collect_step_clear_aperture_edge`, `_update_clear_aperture_edge_hover_highlight`,
  `_add_clear_aperture_edge_rect_actors` (+ badge / cancel / hover dispatch).
- `KrakenOS/UI/services/open3d_interaction.py` — edge-collect click routing + buffer-preserving empty click.
- `KrakenOS/UI/services/open3d_face_assignment.py` — the edge-pick menu items on both STEP menus.
- `KrakenOS/UI/validate_open3d_clear_aperture_stops.py` — geometry / face-store / persistence guard (phase 319).
- `KrakenOS/UI/validate_open3d_clear_aperture_edge_pick.py` — interactive state-machine guard (phase 320).
