# 0252 — Navigation cube: a corner click should reproduce the ISO view (for every octant)

User flags (`attachment/recorded_bug_repros/flag_20260708_073846_983/description.txt` +
`flag_20260708_073911_591/description.txt`):

> The ISO button.
>
> Corner at the Nav Cube.

and, in the same turn:

> Can make the Corner clicking the same orientation as the ISO view? (Apply similar
> orientation to all corners.) … the ISO fit to the wide screen better.

The toolbar **ISO** button and clicking a nav-cube **corner** framed the same 3/4 view
differently. The user wants the corner to land on the ISO camera — and wants that ISO-style
framing on **all 8** corners, each from its own octant — because the ISO orientation lays the
long optical axis flatter across the wide screen.

## Root cause

The two paths used different camera recipes for what is visually the same octant:

* **ISO button** (`open3d_inspector._iso_camera_offset_and_view_up`): the chosen world **up**
  axis takes a small `+0.55` elevation weight; the other two axes take the `0.95 / 0.8`
  horizontal spread. Default y-up ⇒ offset `(-0.95, 0.55, 0.8)` normalized, **~23.9°**
  elevation, view-up world **+Y**. Flat and wide — the long axis stretches across the screen.
* **Corner click** (`nav_cube_orientation.orientation_pose`): corners fell through to the
  generic branch — the **symmetric** normalized sign triple `(±1,±1,±1)` (each axis `1/√3`),
  **~35.3°** elevation, with a *projected* up-vector. Steeper and more square-on, so the long
  optical axis ran more diagonally and framed worse on a wide screen.

The flagged corner (TOP+LEFT+FRONT = `(-1,+1,+1)`) is the **same octant** as the default ISO
button, yet the two produced visibly different pictures.

## Fix (`services/nav_cube_orientation.py`, `services/nav_cube_widget.py`, `open3d_inspector.py`)

Route **corners** through the ISO recipe, per octant.

**`nav_cube_orientation.py`** — new `iso_corner_pose(sign, up_axis="y")` mirrors
`_iso_camera_offset_and_view_up`: the world up-axis component gets `_ISO_UP_WEIGHT = 0.55`,
the other two get `_ISO_HORIZONTAL_WEIGHTS = (0.95, 0.8)`, each multiplied by the picked
octant's sign, then normalized; `view_up` is the world up-axis. `orientation_pose` now
dispatches `orientation_kind(sign) == "corner"` to `iso_corner_pose`. **Faces** stay the exact
cardinal presets; **edges** keep the perpendicular projected-up rule — this bug only touched
corners.

The ISO octant `(-1,+1,+1)` therefore yields exactly `(-0.95, 0.55, 0.8)` normalized with
world-+Y up — the corner click and the toolbar button are now the **same camera**. Every other
corner reproduces that framing for its own octant (small elevation on +Y, the 0.95/0.8 spread
on X/Z with the octant's signs).

**Widget forwarding.** So a corner honours the user-selectable ISO up-axis (bugs/0231), the
widget threads it through: `NavigationCube.__init__` takes an optional `iso_up_axis` getter;
`handle_left_press` reads it and calls `orientation_pose(sign, up_axis=…)`. The inspector wires
`iso_up_axis=lambda: getattr(self, "_iso_up_axis", "y")` at construction. Absent the getter it
defaults to `"y"`, so the common case is unchanged.

**Wide-screen fit** comes for free: the existing corner zoom-fit
(`_fit_view_to_scene_for_current_orientation`) projects the scene bounds onto the *new*
orientation. Flattening the corner to the ISO elevation lets that same fit spread the long
optical axis across the wide viewport, exactly as the ISO button already did.

## Guard

`validate_open3d_nav_cube_corner_iso` (display-free, penta **Phase 228**) — pure math + source
contract, no display:

* **A** — all 8 corners equal `iso_corner_pose`: unit offset, world-+Y view-up, sign-consistent
  with the picked octant (`sign(offset) == sign`).
* **B** — the ISO octant `(-1,+1,+1)` equals the ISO button direction `(-0.95,0.55,0.8)`
  normalized — corner and toolbar button are the same camera.
* **C** — every corner sits at the ISO elevation (~23.9°), **not** the old symmetric 35.3°.
* **D** — regression: the 6 faces are still the cardinal presets and the 12 edges still use the
  perpendicular projected-up rule.
* **E** — source contract: `orientation_pose` routes corners to `iso_corner_pose`;
  `handle_left_press` forwards `up_axis`; `NavigationCube.__init__` accepts `iso_up_axis`.
* **F** — up-axis generalization: `iso_corner_pose(up_axis="z")` puts the elevation on +Z with
  view-up +Z.

`validate_open3d_nav_cube_orientation`'s edge/corner check was split so edges keep the
projected-up assertion and corners get the ISO contract.

## Notes

* Verified headless (pure math): ISO octant `(-1,1,1)` → `(-0.6994, 0.4049, 0.589)` up
  `(0,1,0)`, matches the normalized ISO dir; every corner elevation 23.9°; faces/edges
  unchanged. The live camera feel is still owed an in-app eyeball (headless can't drive the
  embedded-VTK corner click / render the framing).
* The earlier reading of this flag as a *zoom* concern (view-change zoom keying off the stray
  optical-axis length) was checked and found already handled — `_visible_actor_bounds` excludes
  the optical-axis actors from the fit. 0252 became the corner-orientation fix instead.
