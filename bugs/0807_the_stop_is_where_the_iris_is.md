# 0807 -- the stop is where the iris is

flag_20260917_133231 follow-up (SPO TCL4.0X-65DI-5M, object-space telecentric), user: "I think is single
side telecentric, what looks wiered is the rays sudden bend outward." -> "proceed" on pinning the model's
aperture stop to the iris marked on the vendor drawing.

## Measured (before)

bugs/0792's conjugate solve (`solve_conjugate_two_groups`) fixes both ideal groups 5 mm inside the
housing ends and lets the conjugates set their powers. For this lens (4x, WD 65, housing 142.5,
C-mount 17.526, F/12.5 working = object NA 0.16):

* group 1 f +47.113 at 5 mm, group 2 f **-23.883 at 137.5 mm** (5 mm before the shoulder);
* stop at group 1's back focal plane = **52.1 mm** behind the front face -- in FRONT of the iris ring;
* the edge chief ray bends **5.93 deg** at group 2 and reaches the sensor at **7.61 deg** (traced on the
  user's scene: 7.614).

A negative rear group is forced -- no positive pair inside this housing reaches 4x in a 225 mm track
(bugs/0792) -- but its POSITION was the rim rule's, and the rim makes the kink as sharp and as late as
it can be.

## The drawing states the stop

`TCL4.0X-65DI-5M-V2.dwg`, read through libredwg (bugs/0790):

* `DIMENSION_LINEAR` 142.48 (the chain's housing) from sheet x 181.816 to 324.299; the `WD65 ±2`
  dimension shares the 181.816 extension line -> that end is the **front face**, 1 sheet unit = 1 mm;
* dimensioned housing run: 54.9 | **11.6** | 76 (| 4 thread);
* `LEADER` whose landing segment carries the `IRIS` text: arrow tip at sheet x 242.15 = **60.33 mm**,
  inside the 11.6 mm ring (54.9..66.5) -> stop = the ring's middle, **60.70 mm**;
* coaxial diameter dimensions (measured ACROSS the axis) in front of the stop: **Ø31** (15.5 radius).
  The Ø16 illumination port is dimensioned ALONG the axis and is not counted.

The vendor STEP agrees with the picture (no glass in it, only the mechanical bores): front bores r
10.4..12.5 over the first 24 mm, the Ø34 iris ring at 55.1..65.7, a Ø15 rear lens cell from 76.7 to
127.4 mm.

## Fix (general)

* `dwg_spec_import`: one cached `dwgread` payload per drawing; `dwg_iris_stop` (leader label matching
  IRIS / APERTURE STOP / STOP, tip projected onto the housing frame, ring middle when the tip falls in a
  dimensioned housing segment); `dwg_barrel_radius` (largest coaxial Ø in front of it);
  `dwg_telecentric_cardinals` records `stop_from_front_mm`, `stop_ring_mm`, `stop_source`,
  `front_barrel_radius_mm` (new `DatasheetCardinals` fields).
* `solve_conjugate_two_groups` takes separate `front_margin` / `rear_margin` (defaults unchanged).
* `solve_conjugate_two_groups_at_stop`: group 1's back focal plane pinned at the drawn stop leaves a
  one-parameter family. Moving group 2 toward the iris WEAKENS the rear group (less bend, lower sensor
  angle) while group 1 moves back and its beam -- the object-side cone of every field -- grows. The
  member taken is the one whose group 1 is as large as the barrel in front of the stop holds: the
  weakest rear group this housing allows. Group 2 stays behind the iris ring and 5 mm inside the rear.
  `placement` reports which limit applied (`barrel-limited`, `rear-group-at-the-iris`,
  `front-beam-exceeds-barrel`); a stop no two groups can reach raises and the builder keeps the rim
  placement with a note.
* `conjugate_beam_profile`: paraxial beam radius at each group and at each housing end, chief bend at
  group 2, chief angle at the sensor.
* `_core_from_datasheet_cardinals`: uses the pinned solve when the cardinals carry a stop (barrel from
  the drawing, else the STEP barrel); group discs are sized to the beam each group carries (group 1 never
  wider than the barrel, group 2 never narrower than the stop), and the datum discs pass the cone at each
  housing end (the smaller stop had shrunk the field+stop heuristic below the object cone at the front
  face: 22.97 < 23.55). The surrogate note states the placement, the limit, the angles, and that the
  image-side angle is not a vendor figure. Lenses without a drawn stop are untouched.

## Result (the SPO folder)

| | rim (0792) | iris (0807) |
|---|---|---|
| group 1 | f +47.113 at 5.00 mm | f +37.419 at 23.28 mm |
| stop | 52.11 mm, Ø15.076 | **60.70 mm**, Ø11.974 |
| group 2 | f -23.883 at 137.50 mm | f -19.828 at **72.05 mm** |
| chief bend at group 2 | 5.93 deg | **1.20 deg** |
| chief angle at the sensor | 7.61 deg | **3.31 deg** |
| discs (front datum / G1 / G2 / rear datum) | 26.08 / 26.08 / 26.08 / 26.08 | 24.73 / 31.0 / 11.97 / 22.97 |
| delivered m, image gap | -4.000, 17.526 | -4.000, 17.526 |

Replayed on the user's scene (Swap Imaging Lens from Folder, devenv): camera seated on the shoulder,
every field focused on the sensor (spot 0), |m| 4.0012 over the 9-point FOV grid, chief rays parallel at
the object (0.0000 deg), 3.310 deg at the sensor. Rendered side view: the bundles cross at the iris ring
(the inverted image) and glide to the sensor through the rear tube with no kink by the camera.

## Guard

`validate_open3d_0807_the_stop_is_where_the_iris_is` (penta phase 589): A0-A13 closed form + builder
(display-free, offline), B1-B3 the drawing (SKIP without libredwg), C1-C3 the import. Against the old
code it fails (the solve does not exist). Guard 0795 H updated: it pinned the rim stop 15.0761 and an
"18x" f-number misdeclaration; it now checks the declared STOP against the importer's own solve (NA 0.16
through f1) and a >3x misdeclaration (6x at the iris placement).

Unchanged and passing: 0790, 0791, 0792, 0793, 0794, 0796, 0647, 0806 (live swap C1-C5).

## Note for existing scenes

A scene built with the old surrogate keeps its rows until the lens is swapped again (Swap Imaging Lens
from Folder); the saved `MV-CS050-60UM_V5_TCL4.0X-65DI-5M.py` still carries the rim placement.
