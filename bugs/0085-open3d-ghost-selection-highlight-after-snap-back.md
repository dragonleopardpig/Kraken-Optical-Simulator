# 0085 — Open 3D: snapping a beam-splitter overlay back to axis left a ghost selection highlight at the old location

## Symptom (user)

> [flag_20260617_201859_454] snap to axis, slide out of axis, off the show rays,
> beam splitter snap back to optical axis again, leaving ghost selection
> highlight in old location.

(First reported in flag_20260617_194504_424 — same signature, messier scene.)

The beam-splitter cube is imported as an `optical` STEP overlay. The user snaps a
face to the optical axis, slides the body off-axis (drag to `placement_offset`
y≈31 mm), then toggles **Show Rays**. The body **snaps back on-axis** (rendered
at y=0), but a gold STEP-face **selection highlight is stranded at the dragged-off
location** (y≈31), with the hover label "OPTICAL STEP S001/F004 face" floating in
empty space above the on-axis cube.

State proof (`flag_20260617_201859_454`):
- `step_actor_bounds.optical` = y ∈ [−25, 25]  → body **on-axis**.
- `hover_outline_bounds`       = y ∈ [6.2, 56.2] → ghost **off-axis** (centre y≈31).
- `hover_step_cell_key` = `(None, 'passive', 'S001/F004')` — the leading `None`
  shows it came from the **camera-ray coverage-fallback** pick.

## Root cause

The beam-splitter overlay is a **live-trace** optical element
(`transient_step_overlays: 1` at the Show-Rays toggle). Folding it into the
non-sequential trace places it **on the optical axis** — correct physics — so the
DISPLAYED body snaps to y=0. But the user's manual drag offset
(`optical_step_placement_offset_xyz` y≈31) stays baked into the **face metadata**.

The face hover/pick coverage fallback `_step_feature_pick_any_for_display_xy`
(→ `step_feature_pick_for_display_xy`) is designed to resolve a STEP face from the
camera ray **even when VTK reports no actor under the cursor** (so a translucent
prism's far/internal faces stay selectable). It reads the **pose-baked metadata**,
never the rendered actor. With the display snapped on-axis but the metadata still
off-axis, the two **desync**: a hover over the vacated region resolves a face at
the stale y≈31 pose and `_set_step_hover_outline` paints a gold "ghost" there,
above the body that is actually drawn on-axis.

(`refresh_scene` already nulls the hover outline; the ghost is rebuilt *after* the
refresh by the next passive hover reading the stale metadata — so clearing on
refresh alone never closed it.)

## Fix (this commit)

The fallback hit must land on the **live rendered body**, not on stranded
metadata. `Kraken3DInspector` gains:
- `_live_step_body_world_bounds(label)` — union world bounds of the label's drawn
  step-body actors (`_step_actor_map` → `_actor_by_key` → `GetBounds`).
- `_step_fallback_hit_on_live_body(label, feature_pick, feature)` — the
  fallback's hit point (`through_pick.point_world`, else `surface_center`, else
  the feature centroid) must lie within those bounds plus a small margin
  (`max(2 mm, 5 % of body span)` — tolerates surface-edge hits and the hover
  view-offset nudge).

`_step_feature_pick_any_for_display_xy` skips any candidate that fails this gate.
When the display has snapped on-axis but the metadata is still off-axis, the
y≈31 hit is rejected → no ghost. A genuine hover **over** the body (incl. a
translucent far/internal face) stays inside the bounds and is kept; when no live
body is drawn, or no hit point can be resolved, the pick is kept so the
transparent-back-face coverage fallback is never silently lost.

The snap-back to the optical axis itself is **left intact** — a traced
beam-splitter belongs on the axis (North Star, non-sequential). Only the
stranded highlight is removed.

## Regression gate (display-free)

`validate_open3d_step_fallback_pick_on_live_body.py` (`run_checks()`) drives the
real guard helpers against on-axis vs off-axis body bounds:
- ghost hit (y=31, body on-axis) → **rejected**;
- on-body hit, translucent internal far face, surface-edge hit → **kept**;
- no live body → **kept** (coverage preserved);
- synced off-axis drag (body AND hit at y=31, Show Rays off) → **kept** (only the
  desynced ghost is rejected).

Wired as **penta Phase 79** (`phase_79_step_fallback_pick_on_live_body`); baseline
bumped to 80 phases (hand-curated — the full marathon SIGSEGVs headless on
llvmpipe).

## In-app confirmation

PENDING — the embedded-VTK hover pick cannot be driven headlessly (screen-space
picks return nothing under Xvfb), so the rendered ghost itself can't be
image-snapshotted here. Restart the app and repeat the flow (import cube → snap
face to axis → slide off-axis → toggle Show Rays) to confirm the gold ghost no
longer appears above the on-axis body.

## Status: FIXED (pending in-app confirmation)
