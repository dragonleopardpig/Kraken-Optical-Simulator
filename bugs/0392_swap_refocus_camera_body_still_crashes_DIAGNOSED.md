# 0392 — swap auto-refocus STILL crashes camera into mirror (DIAGNOSED, fix pending)

**Flag:** `flag_20260721_171537_109` — "After swap lens, the camera still crash to the RA
mirror." Build **c13c6bfa** (= 0391, so 0391 IS running). Scene AZ85. **User: fix later.**

## What happened

0391's clamp fired: mirror row 8 gap = **13.48 mm** = exactly `_swap_refocus_min_gap()`
(2 clearance + 11.48 hr25MCX flange). But the camera still overlaps the mirror.

Measured from the flag (`step_actor_bounds` / `promoted_solid_rows`):

| | x-range |
|---|---|
| Camera body | `[200.9, 270.9]` |
| Mirror row 8 | center `206.2`, bounds `[193.7, 218.7]` (±12.5 mm mesh half-extent) |
| **Overlap** | camera front `200.9` is **17.7 mm inside** mirror rear `218.7` → CRASH |

## Root cause — TWO compounding errors in 0391's min-gap

`_swap_refocus_min_gap` returns `clearance + camera_front_to_sensor_mm` = 13.48, but:

1. **Gap reference ≠ mirror rear face.** The clamped gap (`rows[-2].thickness`) is measured
   from the promoted mirror's **center/reference**, but the mirror mesh extends **+12.5 mm**
   from there to its rear face. So the sensor clears the mirror rear by only ~1 mm, not 13.48.
2. **Flange depth ≠ physical body-front depth.** `camera_front_to_sensor_mm` (11.48) is the
   optical **flange/C-mount-to-sensor** datum. The physical camera housing extends ~**18.8 mm**
   ahead of the sensor (camera front 200.9 → sensor ~219.7). I reserved 11.48, ~7 mm short.

## Fix direction (for later)

`_swap_refocus_min_gap` must use REAL mesh geometry, not datums:

```
min_gap (center-to-sensor) =
      mirror_rear_offset_from_gap_reference     # promoted-solid bounds max along the axis (~12.5)
    + clearance                                  # 2 mm air
    + camera_body_front_to_sensor_physical       # camera STEP mesh front->sensor (~18.8, NOT flange 11.48)
```

- **Mirror rear offset:** from the promoted solid's `promotion_bounds_max_world` (or the
  transformed mesh bounds) projected on the fold axis, relative to the gap's reference point.
  Beware the FOLD: measure along the *folded* leg axis, not world x (here the leg happens to be
  ~+x, but derive it — `_optical_axis_fold_world_transform_for_row`).
- **Camera physical front-to-sensor:** from the camera STEP mesh bounds (front face) to the
  sensor plane, not `camera_front_to_sensor_mm`. Candidate helpers already exist:
  `_transformed_imported_camera_step_mesh`, `_camera_step_mount_front_face`
  (layout_polyline_display.py). The sensor plane is the image row world z.
- Expected result on AZ85: min-gap ≈ 12.5 + 2 + 18.8 ≈ **33 mm** (sensor at ~239.5, camera
  front ~220.7, clears mirror rear 218.7 by 2 mm).

## Verify when fixing

Extend `validate_open3d_lens_swap_auto_refocus` and/or add a real-AZ85 geometry check: after
the clamp, the transformed camera STEP mesh bounds must NOT intersect the promoted mirror mesh
bounds (a real bbox non-overlap assertion, the honest test — the mock-standoff test passed yet
the real body still crashed). In-app eyeball on a live swap.

## Files (to touch)

- `KrakenOS/UI/services/layout_table_workbench.py` — `_swap_refocus_min_gap` real geometry.
- `KrakenOS/UI/validate_open3d_lens_swap_auto_refocus.py` — real-mesh non-overlap assertion.
