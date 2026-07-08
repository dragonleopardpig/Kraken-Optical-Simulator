# 0255 — Navigation cube: corner ISO keeps the wide-screen framing (flip, don't continuously roll)

User flag (2026-07-08, after testing 0254):

> I tested, seems like after rotation, clicking the corner button works but it does not apply the
> previous "wide screen" adjustment.

0254 works (the corner ISO now follows the current view), but the picture is no longer spread
across the wide screen the way 0252's ISO did.

## Root cause

0254's `relative_up_about_sight` projected the **current** camera up onto the new sight plane — a
**continuous** relative roll. But the "wide screen" framing 0252 gives depends on the view-up being
the **absolute** ISO up (world +Y):

`_fit_view_to_scene_for_current_orientation` (`open3d_inspector.py:11191`) sizes the orthographic
zoom with `_parallel_scale_for_orthographic_fit(horizontal_span, vertical_span, aspect)`
(`:10973`), which is

```
horizontal_scale = horizontal_span / (2 * aspect)   # wide screen divides the WIDTH
vertical_scale   = vertical_span   / 2              # ...but not the HEIGHT
parallel_scale   = max(horizontal_scale, vertical_scale, 1) * 1.08
```

The long optical axis only "spreads across the wide screen" when it lands **horizontal** — then its
span goes into `horizontal_span` and is divided down by the aspect. A continuous relative roll (from
orbiting or rolling the scene) rotates the long axis **off horizontal**, so its span lands in
`vertical_span` instead, `parallel_scale` is driven by `vertical_span / 2`, and the view zooms
**out** to cram the axis into the short (vertical) screen dimension. Wide screen lost.

The two wishes fundamentally conflict for an **arbitrary** roll — you cannot keep the axis horizontal
(wide screen) *and* honour a 37°-rolled view. They coincide only for a **180° flip** (or 0°).

## Fix — flip, don't continuously roll

`relative_up_about_sight(offset_unit, current_up, fallback_up)` now returns the **absolute ISO up**
(`fallback_up`, world +Y) projected onto the sight plane, **flipped 180° iff the current view is
upside down** relative to it (`dot(current_up_proj, abs_up_proj) < 0`):

* Upside-down view → `-abs_up_proj`: the visible labels keep their up/down sense (a "RIGHT" you
  rolled upside down stays upside down — the 0254 ask), **and**
* the result is always **collinear** with the absolute ISO up (`|dot| == 1`), so `+abs_up` and
  `-abs_up` give the **same** orthographic fit as 0252's ISO (the framing uses
  `right = cross(view_dir, up)`, which is invariant under `up → -up` up to sign, so the projected
  spans — and the parallel scale — are identical). Wide screen preserved.
* Upright view → `+abs_up_proj`: **byte-identical** to the 0252/0254 upright ISO (no regression).

The sight direction and `iso_corner_pose` / `orientation_pose` are unchanged (the absolute up is the
flip reference), so the 0249/0252/0253 guards stay green. The inspector call site and the corner
gating (`orientation_kind == "corner"`, live `GetViewUp()`) are unchanged — only the helper's math.

**Tradeoff (intended):** an **intermediate** current roll (e.g. 60°) snaps to the nearer of
upright / flipped rather than staying at 60°. That is standard nav-cube "clean ISO" behaviour and is
exactly what keeps the wide screen; the user's asks only ever concerned the up/down (180°) sense.

## Guard

`validate_open3d_nav_cube_corner_local_up` (display-free) **refines penta Phase 230** in place (no
new phase — 0255 changes 0254's exact mechanism, so its guard is updated rather than duplicated):

* **A** — for all 8 octants: the result is unit, ⊥ the sight line, and **collinear with the absolute
  ISO up projected onto the sight plane** (`|dot| == 1` — the wide-screen fit, the crux of 0255); an
  upside-down current up flips it (dot with the ISO up < 0, world-Y stays negative) and differs from
  the absolute up; an upright current up stays upright (dot > 0).
* **E** — **no continuous-roll leak:** an intermediate roll (60° / 120° about the sight line) still
  returns ± the absolute ISO up (collinear), snapping to upright below 90° and flipped above — never
  the intermediate tilt that broke the wide-screen fit.
* **B/C/D** — unchanged: degenerate fallback; inspector reads `GetViewUp()` + gates on
  `orientation_kind == "corner"`; widget forwards the picked `sign`.

Phase 230 title updated to "nav cube corner ISO keeps the current up/down sense and the wide-screen
fit"; baseline title updated to match. All five nav-cube guards (geometry, orientation, corner_iso,
freecad_style, corner_local_up) green.

## Notes

* Pure-math + source-contract guard is display-free. The **live** feel (roll a face upside down,
  click a corner, confirm the labels stay upside down **and** the scene fills the wide screen) is
  still owed an in-app eyeball — headless can't drive the embedded-VTK camera.
* Corners only. Faces still snap to their exact cardinal preset and edges to their projected-up.
