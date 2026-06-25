# 0140 — Switching to a preset YZ/-YZ view leaves thickness labels slanted

## Symptom

`flag_20260625_090727_802`:

> *"Changed from ISO to YZ or -YZ view, the thickness overlay text should changed
> to perpendicular to the arrow segments."*

After clicking a preset-view button (YZ / -YZ) the dimension **arrows** lie flat and
horizontal along Z, but every boxed `S{n} Thickness = … mm` label stays tilted at the
diagonal (~50°) angle it had in the Iso view — slanted across its arrow instead of
square to it. A mouse orbit fixes them; the preset button does not.

## Root cause

bugs/0128 already made the perpendicular thickness labels track the camera: a label's
billboard angle is re-derived from its world arrow axis projected onto the live camera
basis (`Kraken3DInspector._reorient_thickness_labels_for_camera`, using
`_perp_label_orientation`). But that re-derivation was wired into **one** place — the
orbit backstop `_on_camera_interaction`, which fires on a mouse
`InteractionEvent` / `EndInteractionEvent`.

A preset-view button calls `Kraken3DInspector.set_camera_preset(preset)`, which
**jumps** the camera (`SetPosition` / `SetFocalPoint` / `SetViewUp`) and renders —
with no mouse interaction, so `_on_camera_interaction` never fires. The labels kept
the angle baked against the **previous** (Iso) camera basis, which projects to a
diagonal in the new YZ view. So the very gesture that should square the labels (pick a
flat cardinal view) was the one path that didn't re-square them.

## Fix

Re-derive the labels for the just-set basis at the end of `set_camera_preset`
(`open3d_inspector.py`), exactly as an orbit does:

```python
self._reset_camera_clipping_range_for_scene()
# bugs/0140: a preset-view button jumps the camera WITHOUT a mouse
# InteractionEvent, so the orbit backstop never fires ...
try:
    self._reorient_thickness_labels_for_camera()
except Exception:
    pass
self.render()
```

`_reorient_thickness_labels_for_camera` reads the live camera via
`_camera_screen_world_axes` (`camera.GetPosition/GetFocalPoint/GetViewUp`), which
already reflect the values the preset just set — so the labels re-square against the
new YZ/-YZ basis (a horizontal Z arrow → vertical, i.e. 90°, text) before the render.

## Test

- `KrakenOS/UI/validate_open3d_preset_view_squares_labels.py::run_checks` —
  display-free. Binds the REAL `set_camera_preset`,
  `_reorient_thickness_labels_for_camera`, and `_camera_screen_world_axes` onto a
  light fake inspector whose fake camera stores `Set*`/returns `Get*` (so the camera
  the preset sets is the camera the reorient reads back):
  - **A** a fresh registered Z-arrow label has no orientation yet;
  - **B** after `set_camera_preset("-yz")` (and `"+yz"`) the Z label is re-angled to
    exactly `_perp_label_orientation` for the resulting basis — 90° (vertical text),
    square to its horizontal arrow — and the preset rendered;
  - **C** switching `-yz` → `-xz` re-derives against the LIVE camera (not a frozen
    first-preset basis);
  - **D** source contract: `set_camera_preset` calls
    `_reorient_thickness_labels_for_camera`.
  Mutation: removing the reorient call leaves the label orientation unset → B fails;
  the source check (D) fails too.
- Penta **phase 130**.

## Status

Fixed; guard green standalone and in the penta harness (phase 130, display-free).
In-app eyeball owed — headless llvmpipe can't drive the embedded-VTK preset render,
so the user should confirm that clicking the YZ / -YZ preset button now re-squares the
`S{n} Thickness = …` labels perpendicular to their arrows (as a mouse orbit already
did).
