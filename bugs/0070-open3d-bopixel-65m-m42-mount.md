# 0070 — Open 3D: use the M42-mount 65 MP Bopixel camera (edge-to-sensor 11.5 mm)

## Request (user's words)

> 1) The Bopixel camera 65MP, can change to M42? The STEP in the Cameras folder.
> I am using M42 version, not F-mount version.
> 2) The distance between the edge to the camera sensor is 11.5mm

The 65 MP Japan Bopixel BC-GM65M12X4 ships in two lens-mount variants. The
database carried the **F-mount** version (F Mount, 92 mm-deep body, the flange
46.5 mm in front of the sensor, the F-mount STEP). The user runs the **M42**
version, whose front edge sits 11.5 mm from the sensor.

## Change

`KrakenOS/UI/camera_database.py` — the F-mount entry was **replaced** (not
duplicated; the user uses the M42, not both) with the M42 variant:

| field | F-mount (was) | M42 (now) |
| --- | --- | --- |
| key / `model` | `…BC-GM65M12X4-F` | `…BC-GM65M12X4-M42` |
| `lens_mount` | `F Mount` | `M42 Mount` |
| `camera_front_to_sensor_mm` | 46.5 | **11.5** |
| `body_dimensions_lwh_mm` | (92.0, 80.0, 80.0) | (66.3, 80.6, 80.0) |
| `step_path` | `BC-GM(C)65M12X4-F.STEP.step` | `BC-GMC65M12X4-M42.STEP` |

The **sensor is unchanged** (29.9 × 22.4 mm, 65 MP, Ø37.36 image circle): only the
lens-mount hardware and the body/flange geometry differ between the two variants.
`camera_front_to_sensor_mm` is the only consumer that matters for placement — it
positions the camera body as `camera_front_z = image_z − front_to_sensor`, so the
M42's shorter 11.5 mm flange seats the body much closer to the sensor than the
F-mount's 46.5 mm did. The M42 body bbox (66.3 × 80.6 × 80.0 mm) was measured from
the vendor STEP.

The layout that mounts this camera, `attachment/machine_vision_120mm_65M.py`
(a gitignored user attachment), points `camera_model` / `camera_step_path` at the
M42 variant.

## Test

`KrakenOS/UI/validate_open3d_bopixel_m42_camera.py` (new, display-free):

* **A** (always runs — the camera database is tracked source) — the DB has the
  M42 entry with `lens_mount == "M42 Mount"`, `camera_front_to_sensor_mm == 11.5`,
  `model == "BC-GM65M12X4-M42"`, the unchanged landscape 29.9 × 22.4 mm sensor,
  the M42 STEP path, and the 66.3 × 80.6 × 80.0 mm body; the old F-mount key is
  gone (replaced) and **no** 65M entry is still the F-mount variant (F Mount or a
  46.5 mm flange). Against the old data every M42-specific assertion fails.
* **B** (skip-if-absent — the layout is a gitignored attachment) — when present,
  `machine_vision_120mm_65M.py` references the M42 `camera_model` + M42 STEP and no
  longer references the F-mount camera/STEP.

## Integrated

Phase 75 of `validate_open3d_penta_telescope_comprehensive.py` (display-free
wrapper over the new guard). Baseline `tools/penta_validator_baseline.json`
updated (`"75": "pass"` + title). The gate now tracks 76 phases (0–75).
