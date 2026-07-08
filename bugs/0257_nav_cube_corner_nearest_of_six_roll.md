# 0257 — Navigation cube: port FreeCAD `getNearestOrientation` (nearest-of-6 corner roll), drop the wide-screen bias

User feedback (2026-07-08, after testing 0256):

* *"clicking the Top Right corner still showing wrong orientation after rotation. I check FreeCAD,
  the cube behaviour is exactly correct. Do you want to view the source code for reference?"*
* (after fetching FreeCAD's `NaviCube.cpp`) *"drop the widescreen."*

This is the **fourth** attempt at the corner-click orientation. The first three (0254 continuous
relative roll, 0255 per-corner 180° flip, 0256 one global 180° flip) all read "wrong orientation"
after the scene was rotated. The user designated **FreeCAD's NaviCube as the exact reference**.

## Root cause — the whole 0254→0256 model was wrong

0254/0255/0256 all decided the corner roll with a **binary flip**: keep the absolute ISO up, or
negate it 180°. A binary flip only ever offers **two** rolls (0° or 180°). But a cube corner viewed
down its diagonal has **six** clean orientations 60° apart (0/60/120/180/240/300). Whenever the view
you rotated to has a *natural nearest* clean roll of 60/120/240/300, **no** binary flip can reach it
— the corner lands visibly rotated by ±60°. That is exactly "still wrong after rotation," and no
amount of tuning the flip criterion (the 0254→0256 progression) can fix a model that can only pick 2
of the 6 answers.

FreeCAD's `NaviCube::getNearestOrientation` (`NaviCube.cpp:954`) instead **preserves the current
roll** and snaps it to the **nearest of six** clean orientations for a corner (nearest of four for a
face/edge). That is the behaviour the user was eyeballing.

## Fix — two parts

### 1. Corner STANDARD pose is the symmetric diagonal (drop the 0252 wide-screen bias)

`nav_cube_orientation.orientation_pose` no longer routes corners through a special ISO branch.
A corner now falls through the **same rule as an edge**:

* `offset = normalize(sign)` — the symmetric `(±1,±1,±1)/√3` diagonal (35.26° elevation), **not**
  the 0252 `(0.95/0.55/0.8)` wide-screen ISO bias (23.9°). This is the user's "drop the widescreen."
* `view_up = _projected_up(offset)` — world **+Y** projected ⊥ the diagonal. This is the **roll-0
  STANDARD** the snap rolls from.

`iso_corner_pose` and its weight constants (`_ISO_UP_WEIGHT`, `_ISO_HORIZONTAL_WEIGHTS`,
`_ISO_UP_AXIS_INDEX`) and the 0256 helper `relative_up_about_sight` + `_UPSIDE_DOWN_EPS` are
**removed**.

Why projected-world-up is a valid roll-0 standard: for a corner, world +Y projects onto the sight
plane **exactly along one of the cube's projected edges** (the +Y edge). The six clean corner rolls
are the three edge-up and three edge-down/face-up orientations, spaced 60° apart — so projected-up is
itself one of the six, and the snapped set is **identical** to FreeCAD's.

### 2. At click, snap the roll to the nearest of six — `nearest_orientation_up`

New pure-math `nav_cube_orientation.nearest_orientation_up(sight_axis, standard_up,
current_sight_axis, current_up, steps=6)` ports `getNearestOrientation`:

1. Minimally rotate the **current** camera so its view axis lands on the corner diagonal
   (`_rotate_between` — a Rodrigues rotation about `current_axis × sight_axis`). This **preserves the
   roll**; apply it to the current up → the intermediate up.
2. Measure the residual roll of the intermediate up from `standard_up` about the sight axis
   (`φ = atan2(dot(a, s×iup), dot(s, iup))`).
3. Round φ to the nearest `2π/steps` (60° for corners) and roll `standard_up` by it.

The inspector (`_apply_navigation_cube_orientation`) now reads **both** `GetViewUp()` and
`GetDirectionOfProjection()` (so `current_sight_axis = -view_direction`) and calls
`nearest_orientation_up` for a corner only; faces/edges keep their absolute view-up.

**Convention note:** FreeCAD is Z-up and measures roll about `standardZ` (out-of-screen); KrakenOS is
Y-up and measures about `+offset` (out-of-screen). Only the **algorithm** ports, not the vectors, and
the snap being a symmetric 6-grid means the sign of the measurement axis cannot change the resulting
up vector (rotating `s` about `−a` by `−θ` ≡ about `+a` by `+θ`).

## Verification (display-free, numeric)

* **Nearest-of-6 snap table**: rolling the standard by k° about the diagonal and clicking snaps to
  the nearest 60° gridpoint (20°→0, 45°→60, 100°→120, …) — within 30° of k, always a 60-multiple.
  Matches FreeCAD's bands except at the exact ±(30+60k)° ties, which are measure-zero and where
  FreeCAD's own hand-written bands are internally inconsistent.
* **Idempotence**: a current view that IS one of the six clean rolls comes back byte-for-byte.
* **Cross-axis** (the real scenario — click a corner from a face/oblique view): returns a clean
  snapped roll, unit and ⊥ the sight line, for all 8 corners.
* **Degenerate** antiparallel current axis / current-up-parallel-to-sight fall back to a finite unit
  perpendicular up.

## Guards

* **Phase 228** (`validate_open3d_nav_cube_corner_iso`) rewritten: pins the **symmetric** corner
  standard pose — unit diagonal along the octant sign, upright projected-up, 35.26° elevation (NOT
  the dropped ISO 23.9°, and no longer the ISO button direction), `iso_corner_pose` gone /
  `nearest_orientation_up` present. Title → "nav cube corners use the symmetric diagonal standard
  (ISO wide-screen dropped)".
* **Phase 230** (`validate_open3d_nav_cube_corner_local_up`) rewritten: pins the **nearest-of-6**
  snap — clean-60-multiple invariant across many views, the snap table, idempotence, cross-axis, the
  degenerate fallbacks, and the inspector/widget wiring (reads GetViewUp + GetDirectionOfProjection,
  corners only). Title → "nav cube corner roll snaps to the nearest of six clean orientations
  (FreeCAD getNearestOrientation)".
* **Phase 147** (`validate_open3d_nav_cube_orientation`) corner branch folded into the edge rule
  (symmetric outward + projected-up); the old "corner == ISO button" assertion removed.
* Baseline titles for 228/230 updated. All standalone guards PASS.

## Notes / tradeoff (intended)

* Corners are **no longer wide-screen-biased** — the user explicitly asked to drop it. The long
  optical axis now frames with the symmetric diagonal fit (same as before 0252).
* Faces still snap to their exact cardinal preset; edges keep their projected-up (both could snap to
  nearest-of-4 like FreeCAD later if wanted — out of scope, not flagged).
* The **live** feel (rotate the scene, click a corner, confirm it lands at the roll closest to how
  you were looking — matching FreeCAD) is still owed an in-app eyeball; headless can't drive the
  embedded-VTK camera. The pure-math + source-contract guards are display-free.
