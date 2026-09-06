# 0722 — om05a: the first RA mirrors must fold exactly 90° (they were 45.29°)

Follow-up to bugs/0721 (flags `135342_027` / `140518_465`: "the green lines are not
centered at the camera sensor"). User: "my understanding is that the ray should bend 90
degree for whatever mirror or BS in this design, so I would say there shouldn't be 45.29
degree."

## Root cause (traced end to end)

After 0721 the two measured sensor strips were mirror images of each other, but about
v = −1.09 mm, not the sensor centre, and a design-axis probe ray (on the lens centreline
from the big prism's +x face) landed 1.09 mm off the sensor centre.

The follower walk (`nonseq_output_ports.optical_solid_output_port_pose_overrides`) poses
every chain row by reflecting its running frame about each solid's Mirror face
(`_reflected_frame_from_interaction_face`). The first reflection is `First RA mirror A`
(row 1, component `attachment/om05a_components/ra_mirror_A_0695v.step`). Its Mirror face
normal was `(0, 0.70351, −0.71069)` = a **45.29°** hypotenuse: `bugs/0695_build_vendor_prisms.py`
read the prism off the vendor section as x 29.1..38.9 × y 20.9..30.8 = **9.8 × 9.9 mm legs**.
A 0.29° face error doubles on reflection to a 0.58° dip (−0.010152 in the leg unit vector)
that every later, exact 45° fold preserves, so the lens block, filter, RA mirror 2 and the
sensor were all posed on a chain tilted 0.58° toward −z: 1.9 mm at the lens, 1.09 mm on the
sensor. `First RA mirror B` carried the mirror-image error. The vendor assembly
(`om05a_26_1_r03_2s_lr_asm.stp`) has square 10.5 × 10.5 first RA mirrors; every fold in
this design is 90°.

(An earlier note attributed the offset to RA mirror 2's −88.84° seat tilt. That probe
compared against a hard-coded sensor centre; the walk moves the sensor with RA2, so
squaring RA2 was neutral. RA2 is left at −90/0 — a harmless clean-up, backup
`om05a_folded_80mm.py.pre-0722.bak`.)

The promoted physics mesh (`Solid_3d_stl`) is saved from the component's STEP mesh, so a
face-record edit alone cannot fix the trace — the component geometry had to change.

## Fix (data + pipeline, `bugs/0722_square_first_ra_mirrors.py`)

* `bugs/0695_build_vendor_prisms.py`: the first RA mirror profile is a right **isosceles**
  triangle, 9.85 × 9.85 about the same centre (34.0, 25.85) — manifest / desp unchanged.
* `--build`: regenerates ONLY `ra_mirror_A/B_0695v.step` (backups `*.pre-0722.bak`).
* `--apply <scene>`: re-promotes rows `First RA mirror A/B` through the editor's own
  STEP → cached mesh → analytic-solid path (`_optical_solid_mesh_path_from_source` +
  `_optical_stl_solid_row`), copying every non-geometric face attribute from the old
  records (matched by normal) so the Mirror flag survives; Mirror normals become exactly
  `(0, ±0.70711, ∓0.70711)`.
* `--seat <scene>`: with the first fold exact, the 0689 seat (one frame-desp on the first
  follower row, `Front Optical Vertex Datum`) is stale — it embedded the dip. Re-derived
  with the same mechanism: `desp += Rᵀ · (world shift onto the fold prism's centre plane)`
  → `(−6.08, 0, −0.3885)` → `(−8.78, 0, −0.3885)`; lens front and sensor now on z −25.000
  (RA mirror 1's centre = the split line), axis exactly +x.

Applied to `attachment/om05a_folded_80mm.py` (backup `.pre-0722b.bak`). The older 50 mm
scene `om05a_folded.py` still references the previous cached meshes and was left as is.

## Verified (headless, real trace)

| | before | after |
|---|---|---|
| walk axis at the lens (row 8) | (0.99995, 0, −0.01015) | (1, 0, 0) |
| design-axis ray on the sensor | +1.09 mm off centre | 0.000 / 0.000 mm |
| strips at 0.37× | A +2.21..+2.82, B −5.03..−4.34 (about −1.05) | A +3.49..+3.68, B −3.67..−3.47; pair midpoint **+0.008 mm** |
| FOV 20 solve (m 1.15, 40.6 mm focus residual) | only face A reaches, off-centre | both faces reach, mirror-symmetric top/bottom (midpoint −0.37 mm on 44/47 rays) |

## Guard

`validate_open3d_0722_first_ra_mirrors_square` = penta phase 521 (display-free; skips
when the Filen-synced scene is absent): A the builder profile has equal legs; B both rows'
Mirror face normal AND the traced mesh hypotenuse are exactly 45°; C the first follower
row's seat was re-derived.

## Follow-ups

* Step 2 (agreed): the optical-axis guide draws BOTH imaging beams at their own offsets,
  parallel to the lens axis, no 0692 jog.
* RA mirror 2's centre sits 1.7 mm off the lens axis in z (its own desp); harmless for the
  fold (its fold plane is x–y), noted only.
