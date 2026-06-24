# 0128 — perpendicular thickness labels drift off their arrows when the scene rotates

## Symptom

`flag_20260623_213541_579`:

> "can't those thickness overlay stay strictly perpendicular to the arrow segments?
> They move when I rotate the 3D scene."

The thickness-dimension labels (the boxed "S{n} Thickness = … mm" billboards) read
nicely perpendicular to their arrows at the angle they were first drawn, but as soon
as the user orbits the 3D view they tilt away from perpendicular — the longer the
orbit, the worse the skew.

## Root cause

A label is a `vtkBillboardTextActor3D`; its on-screen tilt is set with
`text_prop.SetOrientation(orientation_deg)`. The angle is computed in
`Open3DThicknessDimensionService._perp_label_orientation(axis, screen_right, screen_up)`,
which projects the **world-space arrow axis** onto the current camera
`(screen_right, screen_up)` basis and rotates the text 90° off that projection — so
the text reads perpendicular to the arrow *as seen on screen*.

The problem: the angle is **baked once at label creation** (`add_label_actor`). When
the camera orbits, the screen basis changes, the screen projection of the same world
axis rotates, and so the perpendicular angle changes too — but the baked
`SetOrientation` value never updated. The label kept its build-time tilt and drifted
off the (now re-projected) arrow.

## Fix

**Remember each label's world arrow axis, and re-derive the angle for the live camera
on every orbit.**

1. `add_label_actor` gains a `perp_axis` argument; when set it records the actor's
   world arrow axis on the inspector via
   `Open3DThicknessDimensionService._register_perp_label_axis(actor, perp_axis)` →
   `inspector._perp_label_axis_map[actor_key] = (x, y, z)` (unit vector). The map is
   cleared with the other thickness maps on every full scene rebuild
   (`open3d_scene_refresh.py`).
2. The three perpendicular call sites forward the axis they already have:
   - the main sequential span loop (`perp_axis=axis`),
   - the promoted-solid own-thickness span (`perp_axis=axis_s`; its hardcoded
     `label_orientation_deg=90.0` is replaced by the same
     `_perp_label_orientation(axis_s, …)` so it too tracks the camera), and
   - the LED→object-edge overlay (`perp_axis=axis_unit`).
3. `Kraken3DInspector._reorient_thickness_labels_for_camera()` re-derives the angle
   for every registered label using the **current** `_camera_screen_world_axes()` and
   re-applies `SetOrientation`. It is cheap (one dot product + a property set per
   label, no geometry rebuild) and returns whether anything changed.
4. It is wired into the existing `_on_camera_interaction` observer (fires on
   `InteractionEvent`/`EndInteractionEvent`), so the labels re-square continuously
   while the user orbits and re-render with the rest of the camera backstop.

## Test

`KrakenOS/UI/validate_open3d_perp_label_camera_track.py::run_checks` — display-free;
binds the real `Kraken3DInspector._reorient_thickness_labels_for_camera` onto a light
fake inspector and reuses the real `_perp_label_orientation`:

- **A** for the user's −YZ view basis, a world-Z arrow's label is re-angled to 90
  (vertical text) and a world-Y arrow's to 0 (horizontal text) — each exactly
  `_perp_label_orientation(axis, right, up)`;
- **B** after the camera orbits 45° in the Y-Z plane, the labels are re-angled again
  and the new angles **differ** from the first basis (they track the camera — the
  bug) while still matching `_perp_label_orientation` for the new basis;
- **C** a label whose actor was cleared on a rebuild is skipped without error, and
  with no camera basis nothing is changed;
- **source contract** — `_on_camera_interaction` calls
  `_reorient_thickness_labels_for_camera`, `add_label_actor` registers the axis via
  `_register_perp_label_axis`, the three call sites forward `perp_axis`, and the
  reorient re-derives via `_perp_label_orientation` (not a baked constant).

Penta **phase 119** runs this guard. Mutation-tested: baking a constant orientation
inside the reorient (the original bug) flips A (Y label wrong), B (both labels stop
tracking the camera), and the reorient source check.

## Note — in-app eyeball owed

Headless llvmpipe can't drive the embedded-VTK render/orbit, so the *visible*
labels staying square through a live mouse orbit is verified in-app. The guard pins
the axis registration, the re-derivation math, and the camera-observer wiring.
