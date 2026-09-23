# 0857 -- the Qt 3D view was missing every optical element

Flagged by the user after 0856 let the shell start: *"it loaded. However, missing two RA mirrors
from the 3D view."*

## What was wrong

`SceneViewport.show_editor_scene` drew the imported STEP bodies and nothing else -- the camera,
the lens barrel and the om05a stage. Everything the MODEL builds as display geometry was absent:
in `om05a_folded.py` that is 20 mesh records, including all six right-angle fold mirrors (rows 1,
5, 7, 15, 16, 18), both BS cubes and their far halves, the two thin-lens groups, the vertex
datums, the filter, the aperture stop and the two LED panels. The user noticed the two large fold
prisms because they are the visually obvious ones.

Not a rendering fault: the viewport was never asking for that geometry.

## Fix

`SceneViewport._draw_optical_elements(editor)` draws `editor._scene_surface_meshes(system,
bundle, include_reference_surfaces=False)` -- the SAME collector the Tk 3D view draws, over the
system from `_build_preview_system_rays_bundle(sampling_mode="world_envelope")`, which is the
preview path's own build. Nothing is re-derived: each record carries the colour and opacity the
Tk view uses, and the viewport uses those. A display that invented its own geometry would drift
from the physics the moment either side changed.

Details that follow the Tk view rather than the easy path:

- the **aperture stop is drawn as a ring**, through the model's own
  `_legacy_3d_stop_ring_mesh`, not as a filled disc;
- a row may yield **more than one record** (the filter yields a disc and a solid body), so
  records are drawn, and compared, positionally -- never keyed by row;
- if the model cannot build its display geometry the viewport **says so** and still draws the
  STEP bodies, rather than showing a silently empty scene: the window's status line reads
  "3D view: the optical elements could not be built -- ...". On success it reads
  "3D view: 20 optical elements, 3 imported bodies."

`show_editor_scene` now returns `{"elements": [...], "bodies": [...], "error": ...}`; guard 0855's
Q4 follows the new shape.

Rays are still not drawn -- that is the next step, not this fix.

## Guard

`validate_open3d_0857_qt_view_draws_elements.py`, penta phase 636. E1 every record the model's
collector yields is drawn, checked BY ROW so the RA mirror rows are demonstrably among them; E2 a
drawn actor's bounds equal its record's mesh bounds exactly (paired positionally -- a row-keyed
version of this check failed by comparing the filter's disc actor against its solid record, which
is how the two-records-per-row case was found); E3 colour and opacity come from the record; E4 the
stop is the model's ring (192 points), not its disc (129); E5 a build failure leaves the window
up, still draws the bodies, and is reported.
