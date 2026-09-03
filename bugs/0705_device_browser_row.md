# 0705 — "unable to select the Device on the scene, not in right panel browser"

The inspection part (the DEVICE under test) drew as a translucent box + face
outlines (0661) with a canvas right-click menu — but on the om05a the part
sits INSIDE the vendor prism-assembly meshes, so every canvas pick lands on
the STEP overlay actors first: the 0661 menu could never fire there, and the
part had no browser presence at all.

## Fix

The Device is now a first-class Scene Components browser row (root level,
below Scene Sources), listed whenever the part is enabled:

    Device 50 × 1 × 50 mm (inspect: front)

- **Select** → status hint with the size + inspected face.
- **Right-click** → the Device verb menu (the 0619 rule: verbs live on
  right-click), posted via `_popup_scene_component_menu` (0403 dismiss):
  - Device size / part settings… (the Inspection Part dialog — the 0704
    resize entry point)
  - Inspect <Face> (all six faces, active face starred)
  - Solve FOV to the inspected face
  - Create/Open station for the inspected face…

This is the same verb set as the canvas part menu, reachable regardless of
what covers the part in the 3D view.

## Verification

Live headless on `om05a_folded_80mm.py`: the row lists with the exact text
above; selecting writes the hint. Guard
`validate_open3d_0705_device_browser_row` = penta **phase 514** (A row
insert gated on enabled; B selection hint; C1/C2 menu routing + contents).
