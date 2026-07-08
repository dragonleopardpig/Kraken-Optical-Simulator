# 0254 — Navigation cube: a CORNER click gives a LOCAL ISO (roll relative to the current view)

User flag (2026-07-08, after the 0253 roll-arrow trim landed):

> they look correct now, thanks. I play around with the Cube, I think clicking the Corner should
> behave differently, their tilting is refer to the global instead of local. I think local is more
> meaningful. For example, I click the 'Right' face, then rotate the scene until the 'Right' is
> upside down. Now I am to have an ISO view by clicking the Corner, the existing behaviour is that
> it goes back to the absolute global ISO view. But it is more intuitive to just have an ISO view
> relative to the current one, meaning the 'Right' and all other visible alphabet remain upside
> down, get what I mean?

## Before

bugs/0252 made every corner click snap to the **absolute** ISO the toolbar button uses:
`iso_corner_pose(sign)` returns the picked octant's diagonal sight direction **and** an absolute
world-**+Y** view-up. So no matter how the user had rolled the scene, a corner click reset the roll
to upright — if you had flipped "RIGHT" upside down, the corner ISO flipped it back up.

## Why it felt wrong

A corner is a *re-aim*, not a *reset*. The user's mental model: the corner picks the ISO **sight
direction** (which octant to look down), but the **roll** (which way is up on screen) should stay
where it is — the same up/down sense you are already looking at. Global roll throws that away.

## Fix — only the ROLL becomes relative, for corners only

New pure-math helper `relative_up_about_sight(offset_unit, current_up, fallback_up=None)` in
`services/nav_cube_orientation.py`:

* `look = -offset_unit` is the new sight direction.
* Project the **current** camera up onto the plane ⊥ `look` and normalize:
  `proj = current_up − (current_up·look)·look`. Because
  `proj·current_up = 1 − (current_up·look)² > 0` whenever the up isn't parallel to the sight, the
  result is always on the **same roll side** as the current up — the up/down sense is preserved.
* Degenerate guard: if `current_up` is (near) parallel to `look` the projection collapses, so it
  falls back to `fallback_up` (the absolute pose up) projected, then to the world-projected up.
  Returns a unit `(x, y, z)` ⊥ the sight line.

Wiring:

* `services/nav_cube_widget.py` — `handle_left_press` now forwards the picked `sign` as a **third**
  `apply_orientation(offset_unit, view_up, sign)` argument (callback hint widened to
  `Callable[[tuple, tuple, tuple], None]`), so the host can tell a corner apart.
* `open3d_inspector.py` — `_apply_navigation_cube_orientation(self, offset_unit, view_up, sign=None)`
  reads the **live** camera up (`GetViewUp()`) *before* re-aiming, and for a **corner only**
  (`orientation_kind(sign) == "corner"`) replaces `view_up` with
  `relative_up_about_sight(offset, current_up, fallback_up=view_up)`. Faces/edges keep their
  absolute `view_up`. The reframe (`_fit_view_to_scene_for_current_orientation`) and the interaction
  backstop (`_on_camera_interaction`) both preserve the view-up (they set position/focal/scale, never
  `SetViewUp`), so the relative roll set here survives the snap.

`iso_corner_pose` / `orientation_pose` are **unchanged** — they still return the absolute ISO pose
(sight direction + world-+Y up). That absolute up is now used only as the corner's *fallback*, so the
bugs/0249 / 0252 / 0253 pose guards stay green.

### No regression to the common first click

From an already-**upright** view, projecting world-+Y onto the plane ⊥ the sight line yields exactly
what VTK's orthogonalized world-up would give — so the very common "open scene, click a corner" ISO
is visually identical to before. Only a view the user has actually rolled comes out relative.

## Guards

* `validate_open3d_nav_cube_corner_local_up` (display-free, penta **Phase 230**, new):
  * **A** — for all 8 octants, a "rolled upside down" current up (world −Y) projects to a unit vector
    ⊥ the new sight line, on the **same side** as the current up (dot > 0), that stays upside down
    (world-Y component < 0) and differs from the absolute ISO up; and an **upright** current up
    (world +Y) stays upright (world-Y > 0) — no regression.
  * **B** — degenerate fallback: current up parallel to the sight line falls back to a finite, unit,
    perpendicular up, with `fallback_up` given and with `fallback_up=None`.
  * **C** — inspector source contract: `_apply_navigation_cube_orientation` takes a `sign`, reads
    `GetViewUp()`, calls `relative_up_about_sight`, and gates it on `orientation_kind == "corner"`.
  * **D** — widget source contract: `handle_left_press` forwards the picked `sign` as the 3rd
    `apply_orientation` argument.
* `validate_open3d_nav_cube_orientation` / `_corner_iso` / `_freecad_style` / `_geometry` all
  unchanged and still green (the absolute pose math is untouched).

## Notes

* Pure-math + source-contract guard is display-free; the **live** feel (roll a face upside down, click
  a corner, confirm the labels stay upside down in the Tk-embedded pane) is still owed an in-app
  eyeball — headless can't drive the embedded-VTK camera interaction.
* Corners only. Faces still snap to their exact cardinal preset and edges to their projected-up, both
  absolute, unchanged.
