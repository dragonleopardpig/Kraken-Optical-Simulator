# 0721 — om05a split field: symmetric face bands, sensor strips measured from the trace

Flags `flag_20260906_135342_027` ("the green FOV attaching to the side of the device is not
centered, seems like shifted up"; "unknown 90 degree bending of optical axis at the big
inverted RA mirror"; "A-side is missing") and `flag_20260906_140518_465` ("the green lines
are not centered at the camera sensor"), plus `flag_20260906_135823_991` (the inverted big
RA mirror against the LED plate). Build 811bc1f4, `attachment/om05a_folded_80mm.py`.

## The design (from the user)

The centre prism is ONE piece with a two-sided mirror coating. Beam A and beam B (the two
device faces, each through its own arm: first RA mirror → BS cube → one face of the centre
mirror) bend straight down into the big RA prism, which is **inverted on purpose** so each
beam enters a leg face, reflects internally off the hypotenuse and exits toward the lens.
The two beams reach the big prism **independently and offset from its centre** (±6 mm).
What the sensor shows is one thin dark edge at its centre — the image of the centre
mirror's ridge — with a symmetric rectangular strip either side, the two symmetrical
object-side FOVs.

## What was actually wrong (measured)

* **Scene geometry is right.** Mapping the vendor assembly frame onto the scene (axis
  z 1.5 ↔ −25), the arms are symmetric and match `om05a_26_1_r03_2s_lr_asm.stp` within
  0.3 mm: first RA mirrors ±34.0 (assembly ±34.25), BS cubes ±32.25 (±31.5), the centre
  mirror halves **±6.0 (±6.0)**. Nothing to re-seat.
* **The physics at the big prism is right.** A single chief ray (real `NsTrace`) enters the
  top leg face at y 27.8 with no bend, reflects internally at the hypotenuse (y 52.8) and
  exits the +x face at x 25 — then travels the lens leg **8.2 mm off the prism centre**,
  enters the lens ~6 mm off-axis (by design) and lands 2.6 mm from the sensor centre.
* **The "unknown 90° bend" is the dotted axis GUIDE**, not the optics: bugs/0692 bridges
  non-intersecting legs with a lateral jog (`axis:global:reflected:jog4`, 6 mm) because it
  assumes every leg must meet the lens centreline. In this design the beam is MEANT to stay
  offset and parallel. (Guide fix = step 2, separate.)
* **The bands and strips were authored constants.** `object_fov_bands` in the scene file
  carried v −5.25 … +3.1 on both faces (centre −1.08 mm → the green plane 1.1 mm high on
  the device) and `image_strip` A +0.845…+3.845 / B −6.224…−3.114 — not mirror images
  (B 2.5 mm off), and constants cannot follow magnification: the ±6 mm beam offset at the
  lens maps to ∓6·(1 − v/f) on the sensor = ±2.2 mm at 0.37× but ±6.9 mm at 1.15×. The
  first-order prediction reproduces the authored A strip (+2.2 vs +2.35) and exposes B.
* The big prism's top leg face (y 27.80) is flush with the LED plates' underside (27.87):
  a 0.07 mm seat interference over two 4 mm strips. Mechanical detail; the beams pass
  between the plates. Not changed here.

## Fix (general, display-free core)

`detector_coverage_overlay.py`:
* `symmetrize_face_bands(bands)` — a device-face band's field is centred on its face:
  `v_lo/v_hi = ∓span/2` (span kept — it is the arm's short-axis passband). Applied at load
  (`layout_settings`) and on every FOV solve (`_update_split_field_band_widths`).
* `measure_split_field_image_strips(bands, records, image_surface, image_point,
  image_axis)` — the strips are MEASURED: a ray belongs to the band whose face plane is
  nearest its FIRST hit (each arm starts at its own face); rays reaching the image row are
  projected into the detector's in-plane frame (the overlay's own `_basis(normal)`), and
  the band's `image_strip` becomes their trimmed v-range and u half-width. The centre dark
  edge is the gap between the two measured strips. Bands with < 3 landing rays keep their
  previous strip (authored values survive until the first real trace).

`layout_table_workbench._measure_split_field_image_strips(system, rays, scene_bundle)` reads
the scene bundle's detector target (centre + normal) and the trace records; called after
every real trace from both the 2D refresh (`plot_refresh`) and the 3D rebuild
(`three_d_scene_tools`).

## Guard

`validate_open3d_0721_split_field_strips_measured` = penta phase 520 (display-free): A the
symmetrization, B the measurement on synthetic two-face records (mirror-image strips, the
centre gap, trim, min_rays, the overlay frame), C the wiring pins.

## Follow-ups

* Step 2 — the optical-axis guide: draw BOTH imaging beams at their own offsets, parallel
  to the lens axis, no jog.
* The device band span (8.35 mm) is still the authored passband; deriving it from the arm's
  first RA mirror cross-section would remove the last authored number.
