# 0379 — User-specified physical clear-aperture (CA) stops from picked edges

**Flags:** 20260721_092541 ("CA of the CO90 output is 51×51.5mm, is this CA detected? If not, we need a
flow that let user to specify all physical CA opening") + 093143 ("Another CA opening dimension:
55×74mm"). User clarifications: **click the CA boundary EDGES and set it as an aperture** (the pick
carries the CA's LOCATION, which a numeric entry would lose); the front window is a closed loop but the
back opening is **3-sided** (no closed loop) — must still be pickable; build the rectangle from the
**3 edges** (2 opposite edges also, less accurately); and the CAs must be **real ray stops**.

**Status:** CORE SHIPPED 2026-07-21 (geometry + ray-stop filter + illumination-trace wiring; guard
`validate_open3d_clear_aperture_stops`, penta phase 319). **Interactive pick UI + persistence + draw =
next increment.**

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

## Next increment (interactive UI)

1. **Pick mode** — "Set Clear Aperture (pick edges)…" on a decoration STEP: click a closed loop, or the
   3 available edges of an open opening; accumulate the picked edge polylines → `rect_from_edges` →
   store under the STEP label.
2. **Persistence** — save/load `_clear_aperture_rects_by_label` with the layout.
3. **Draw** — a highlighted rectangle at the CA's plane so the user sees where it sits.
4. Optionally also size the illumination EMITTER to the limiting CA (replace the bugs/0290
   module-bounds auto-seed), and apply the filter in the "Illum rays" overlay too.

**Physics note carried forward (bugs/0376 / the coaxial KB):** the 51×51.5 output CA still over-fills
the 39×39 FOV, so specifying it sizes the source correctly but does not by itself make the 2-side fold
dark edges — those need a **downstream** ~35–40 mm fold-axis stop, which this same flow can now express
once picked.

## Files

- `KrakenOS/UI/services/clear_aperture_stops.py` — geometry + ray-stop filter.
- `KrakenOS/UI/services/three_d_scene_tools.py` — `_clear_aperture_stop_rects` + `_apply_clear_aperture_stops`
  wired into the object-illumination records.
- `KrakenOS/UI/validate_open3d_clear_aperture_stops.py` — display-free guard (penta phase 319).
