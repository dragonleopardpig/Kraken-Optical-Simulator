# 0669 — The cell lives in the existing 3D canvas

**User (2026-08-31):** "I see you put the 6-sided object in 2D menu and launch a
separate 3D window. Can't we do everything to existing 3D canvas?"

## Shipped

- **Ghost stations in the live canvas.** Right-click the part (or a blow-out axis) →
  *Show the other stations here (ghosts)*: every OTHER enabled station of the cell is
  loaded headlessly, its scene actors are harvested from a throw-away off-screen
  plotter (the 0664 transplant pattern) and re-parented into the LIVE renderer —
  translucent (opacity ≤ 0.35), **non-pickable**, helper axes dropped (the 0663
  extent lesson) — under `T_live⁻¹ @ T_ghost`, the rigid transform carrying its face
  onto the live part. The live chain stays fully editable; picking, gizmos and menus
  never see a ghost.
- **Everything re-seats itself.** The composer runs inside the scene refresh, cached
  per face: a rebuild re-parents cached actors (O(1)); a station whose FILE changed
  rebuilds (mtime); re-targeting the live face (or 0667's Create/Open switch) re-keys
  the set — the face you left ghosts in, the face you opened stops being a ghost.
  Measured: 5 ghost stations compose in ~70 s warm; a face switch costs one station.
- **The part is a 3D gesture too.** The generic optical-axis right-click gains
  *Inspection Part (3D object)…*, so enabling the part never needs the Actions menu.
- Cell discovery: `find_cell_for_layout` scans the `*.cell.json` beside the layout
  and matches by station reference — a plainly-loaded station file finds its cell
  without the editor carrying `inspection_cell_spec`.

The separate Inspection Cell window (0664) still exists for standalone review and
the solve/export chores, but the day-to-day flow is now one window: enable the part
→ ghosts on → right-click an axis → Create/Open station → edit → the ghosts show
the rest of the cell around you.

## Frame invariant (guard A3)

The 0663 cell frames (part-centred) and the 0661 live-world face frames are the SAME
geometry through `T_live⁻¹`: a ghost's object point must land exactly on the
live-world centre of its part face (measured 3.7e-15 mm). Any drift between the two
frame conventions breaks the composition silently — this pins it.

## Verified

Guard `validate_open3d_0669_cell_ghosts_in_canvas` (penta phase 502): frame
consistency (identity / rigidity / face-landing), cell discovery, refresh + menu
wiring, and a REAL live-canvas session on the solved six-station cell — 1005 ghost
actors seated, none pickable, re-key on re-target, clean removal on toggle-off.
Renders eyeballed on the solved cell (ghosts_front / ghosts_top).
