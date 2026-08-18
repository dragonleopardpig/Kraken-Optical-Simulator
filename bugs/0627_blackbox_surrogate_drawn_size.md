# 0627 — swapped surrogate drew at 2× its size (the 0624 trace extension leaked to display)

flag_20260818_140218 (build 61916954): *"loaded Apo75, swap lens to pyrite85, lens
surrogate grow big."* Trace healthy (census 279/219/60, zero missed) — display only.

## Root cause

bugs/0624 builds surrogate-block-member surfaces (rows between the Front/Rear vertex
datums, stop excluded) with `surface.Diameter = 2 × spec` so corner pencils REFRACT
instead of bypassing — an intentionally TRACE-only extension ("the display keeps the
row's drawn size"). But that claim was never true in 3D: the display's surface discs
(`system.AAA`) and side bodies (`system.BBB`) are the SAME Kos-built geometry, already
in world coordinates (`_mesh_with_transform` applies no transform). On the Apo75 the
doubled discs hid INSIDE the lens STEP barrel overlay; the swapped-in PYRITE 4.5/85 is
a bare surrogate (datasheet blackbox, no STEP body covering the discs), so the 2×
geometry stood naked — Ø53 discs for Ø26.5 rows.

## Fix

`three_d_scene_tools`:
- `_surrogate_blackbox_member_rows()` — the display-side mirror of the build's
  front/rear-datum scan (stop-like rows excluded).
- `_clip_world_mesh_to_row_radius(mesh, system, index, radius)` — clips the DISPLAY
  copy back to the drawn radius in Kos's own local frame (`TRANS_2A` is local→world;
  its inverse gives exact local x/y for the radial). Fast no-op when the mesh is not
  extended (≤ radius×1.02 — plain scenes untouched, no copy); any failure returns the
  original mesh. The traced geometry is untouched (these are deep copies).
- Both display iterators (`_iter_3d_optical_surface_meshes` analytic fallback,
  `_iter_3d_side_body_meshes` BBB bodies) clip member meshes.

## Verified (diag_0627_swap_surrogate_display_size.py)

Load Apo75 → swap to PYRITE 4.5/85 → live bundle: all 4 member meshes' longest bbox
side = 26.48 = the drawn diameter exactly (pre-fix ~2×); 205 arrivals — the trace is
untouched. Screenshot: bugs/_0627_pyrite_swap_display_size.png.

Guard: phase 471 (`validate_open3d_0627_blackbox_display_size`) — iterator contract,
synthetic doubled-disc clip + identity fast path + None safety, member-scan rule.
