# 0692 — flag_20260902_103541: split-field display truth (circles, axis, cover strips)

## User
"I saved my preference layout, please use this. There is big green circle in A
object plane. There is broken and slanted optical axis shown. The rays at the
sensor, some focus, some defocus, some not reaching the sensor."
Follow-ups (same window): can the arms reach the FULL sensor or just partial —
and "can draw 2 dotted line edge at the Sensor to indicate actual cover area?"

## 1. The big green circle = the Quick-Estimation object-FOV disc
The user's saved layout keeps QE on; its single-axis object FOV circle
(diameter 56.7 = sensor 23.04 / m 0.4066) is the WRONG MODEL for a split-field
scene — each face sees a one-sided BAND through its own arm (0683). FIX: when
`object_fov_bands` are authored the QE overlay stands down entirely (gate at
the top of add_overlays, before even reading QE state).

## 2. The broken circle family at the sensor
`_image_circle_radius` reads `field_metrics_summary()["field_image_radius"]`,
which collapses to Ø0.5 on the seated scene → "Image circle Ø0.5 (short)" +
"Needs Ø32.6" + rings everywhere. For split-field the metric is semantically
wrong (two off-axis strips share the die), so under bands the coverage overlay
suppresses circle-kind line specs and the "Image circle"/"Needs"/"FOV WxH"
labels. The real-sensor square (detector footprint actor) is untouched; a
bare-lens recommended rect still draws.

## 3. Broken/slanted optical axis — two composed defects (bugs/0692_axis_probe.py)
a) PHANTOM BRANCH: the two BS far-half glass rows are free-placed furniture
   (StepOverlayPromotion.center_world) with no walk pose — their anchors sat at
   (0,0,z) on the long-dead UNFOLDED axis and fabricated a +Z branch, dragging
   two vertices mid-air ((0,26.4,-25), (-136.3,0,-25)): the long diagonal across
   the scene + an outgoing leg from empty space. FIX: `_row_is_axis_station`
   excludes free-placed/frozen rows from the branch grouping (frame_seat rows
   STAY — the walk poses them).
b) SKEW SEAT JUNCTION: the +y approach leg rides arm A's field line (z -15.54)
   while the seated lens block rides the shared split-line axis (z -25, 0690).
   The old closest-approach MIDPOINT vertex hovered mid-air (z -20.27) and
   slanted both neighbours. FIX: `_axis_branch_junction_feet` keeps each segment
   ON its own leg line and bridges a >0.5 mm gap with an explicit jog segment
   (`axis:global:reflected:jogN`) — the axis now reads: leg → fold → jog across
   the mirror face onto the lens axis → mirror2 corner (-272.65, 52.8, -25) →
   -y through the sensor.

## 4. Full sensor or partial? MEASURED (bugs/0692_sensor_reach_sweep.py)
±16 mm y-sweep + x extremes through the real chain launch (the additive faceB
source mirrors the same grid — one run measures both arms):
- Arm A: sharp vignette cut below y=-5 (0/361), clean razor spots y -4..+3 →
  sensor z -27.1..-30.2. Above y=+3 the "hits" are wide-z stray-path smears,
  not imaging.
- Arm B: y -4..+3 → z -22.8..-18.2 with ~0.9 mm blur (compromise focus).
- Together ~7.7 mm of the 23.04 mm sensor height; the rest is DARK BY PHYSICS
  (centre-prism split + outer-wedge entry window), not by launch choice. To
  fill a half-sensor one side would need ±28 mm of object field — the prisms
  refuse long before.
- Long axis: object x=-27.5 lands 0.4 mm inside the die edge (width ~fills);
  the +x side lands smeared and slightly off-die (asymmetry — open item).
- "Edge of sensor" launch practice → for split-field the extreme fields are
  the VIGNETTE edges (band edges), which ARE the strip edges on the die.
NOTE: chain rays carry source_id "source:0" (never filter by truthiness — the
first sweep binned 0 of 7943; bugs/0692_sweep_census.py).

## 5. Sensor cover strips (user request)
Each band may author its measured `image_strip` (world center on the sensor
plane, in-plane axis_v, v_lo/v_hi, half_width). The coverage overlay draws the
two dashed edge lines per strip + the band name against the sensor square.
om05a stamped (bugs/0692_stamp_strips.py): A z -30.3..-27.1, B z -22.8..-18.2,
half_width 11.52 about centre (-272.65, -9.9, -25).

## 6. "Some focus, some defocus, some not reaching"
Measured truth, not a defect: arm A focuses at 0.1 µm (0691's refocus put best
focus ON the row); arm B rides the shared sensor at the vendor's compromise
focus (~0.9 mm blur); the "not reaching" rays are the known vignetted stray
light (housing ray-stop via the 0379 machinery remains the queued fix).

## Guards
- NEW `validate_open3d_0692_split_field_sensor_strips` (penta phase 508):
  QE gate order, strip normalizer, circle/label suppression scope, four dashed
  strip edges at the authored offsets, bare-lens rect survives.
- 0672 guard A8b: both om05a bands author the measured strips.
