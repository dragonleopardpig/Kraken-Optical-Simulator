# 0231 — user-selectable ISO up-axis (feature)

**Status: SHIPPED. The Open 3D "Iso" view's up-axis is now user-selectable via a new "Iso up ▾"
toolbar menu (X / Y / Z). Default Y-up reproduces the historic Iso byte-for-byte. In-app confirm
owed (headless can't drive the VTK view).**

## The request

"the ISO view now defines Y-axis pointing up… I want the user selectable ISO view, meaning user
can define which axis pointing up, etc." Previously `set_camera_preset` hard-coded
`view_up = (0, 1, 0)` for the Iso view (and every cardinal preset).

## What shipped

- **Toolbar**: a new **"Iso up ▾"** menu next to the Iso/cardinal buttons
  (`panels/open3d_top_controls.py`, `build_view_toolbar`) with radiobuttons **Y up (default) /
  Z up / X up**, bound to `inspector.iso_up_axis_var` + `_on_iso_up_axis_changed`. Picking one
  applies the Iso view immediately; the plain "Iso" button also uses the current choice.
- **Pose**: `Kraken3DInspector._iso_camera_offset_and_view_up(up_axis, distance)` (pure,
  unit-testable) — the chosen world axis points UP (`view_up`), its camera offset is
  `+0.55·distance` (above the scene), and the OTHER two axes carry the diagonal horizontal
  spread (`-0.95` and `+0.8`) so all three axes stay visible. `set_camera_preset`'s Iso branch
  reads `self._iso_up_axis` through it.
  - `y` → offset `(-0.95, 0.55, 0.8)·d`, up `(0, 1, 0)` — **identical to the old Iso**.
  - `z` → offset `(-0.95, 0.8, 0.55)·d`, up `(0, 0, 1)`.
  - `x` → offset `(0.55, -0.95, 0.8)·d`, up `(1, 0, 0)`.
- **State**: `iso_up_axis_var` (`StringVar`, default `"y"`) + `_iso_up_axis`; an unknown value
  falls back to `y`. Session-level (not persisted to the layout) — opening the inspector starts
  at Y-up, matching prior behaviour.

The Iso view stays orthographic (the bugs/0048 parallel-projection fit is unchanged), so orbit
never clips regardless of the up-axis.

## Verification

`validate_open3d_iso_up_axis` (display-free, penta phase 204): Y-up reproduces the historic Iso
exactly; each of x/y/z yields a true oblique iso with that axis up, camera above, all three axes
visible; the handler stores + re-applies (unknown → y); the toolbar/preset wiring is present.
`validate_camera_iso_orbit_no_clip` + `validate_open3d_navigation_cube_rotate` still pass;
`validate_open3d_toolbar_layout` has the SAME 4 pre-existing unrelated failures (Ray-count removed
per bugs/0093, side-panels, Import menus) with and without this change — no regression.

## Possible follow-ups (not done)

- Persist the chosen up-axis in the layout SETTINGS so it survives reload.
- Extend the up-axis to the cardinal presets too (they also hard-code `view_up`), if the user
  wants a global "up axis" preference rather than Iso-only.
