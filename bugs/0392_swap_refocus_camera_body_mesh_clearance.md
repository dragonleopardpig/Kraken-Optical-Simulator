# 0392 — swap auto-refocus: clear the camera BODY from the mirror by REAL mesh geometry

**Flag:** `flag_20260721_171537_109` — "After swap lens, the camera still crash to the RA
mirror." Build c13c6bfa (= 0391 running). Scene AZ85.

## Why 0391 still crashed

0391's clamp fired (mirror row 8 gap = 13.48 = `clearance + camera_front_to_sensor_mm`), yet
the camera still overlapped the mirror. Measured from the flag:

| | x-range |
|---|---|
| Camera body | `[200.9, 270.9]` |
| Mirror row 8 | center `206.2`, bounds `[193.7, 218.7]` (±12.5 mm mesh half-extent) |
| **Overlap** | camera front `200.9` is **17.7 mm inside** mirror rear `218.7` |

0391 was datum-based and wrong two ways: (1) it measured the gap from the mirror **center**,
not its mesh rear face (+12.5 mm); (2) `camera_front_to_sensor_mm` (11.48) is the optical
**flange** datum, but the physical camera housing front sticks out ~**18.8 mm** ahead of the
sensor. The mock-standoff guard passed while the real body crashed.

## Fix — measure the actual meshes

The auto-refocus now keeps the camera clear in two layers:

1. **Cheap floor** (`_swap_refocus_min_gap`, 0391): `clearance + flange depth` — a lower bound
   and the no-mesh fallback.
2. **Exact mesh clearance** (`_swap_camera_body_clearance_deficit`, 0392): bump the image gap by
   the real face-to-face overlap so the whole camera **body mesh** clears the upstream
   **promoted-solid mesh** by the clearance, measured along the folded leg axis:
   - Camera body AABB ← `_transformed_imported_camera_step_mesh().bounds`.
   - Mirror AABB ← the promoted row's stored `advanced["StepOverlayPromotion"]`
     `bounds_min/max_world`.
   - Leg axis ← the folded optical-axis transform's downstream +Z
     (`_folded_leg_axis_unit`; +x on AZ85).
   - `deficit = clearance − (|Δcentre| − (cam_half + mirror_half))` projected on the leg
     (`_camera_body_clearance_deficit_pure`, sign/scale-independent).

Increasing the image gap slides the sensor **and the glued camera** downstream by the same
amount along the leg, so the bump clears the body exactly. On the flag geometry: deficit =
218.7 + 2 − 200.9 = **19.8 mm** → gap 13.48 → **33.28 mm**, camera front 200.9 → 220.7, clearing
mirror rear 218.7 by exactly 2 mm.

## Verification

- **Guard** `validate_open3d_lens_swap_auto_refocus` (penta phase 326), the honest real-geometry
  test this time: the pure clearance on the **actual flag AABBs** needs 19.8 mm and the
  **post-bump** camera front clears the mirror rear by exactly the clearance; sign/scale
  invariant; already-clear → 0; and the wired end-to-end refocus bumps the gap 13.48 → 33.28 and
  flags "camera body". (0391's flange-floor + no-op/safe/thin-mirror cases still hold.)
- **Real AZ85 scene:** the helpers derive the folded leg axis (+x) and no-op safely (0.0, no
  crash) when the base scaffold lacks a camera STEP / promoted-solid metadata.

## Files

- `KrakenOS/UI/services/layout_table_workbench.py` — `_camera_body_clearance_deficit_pure`,
  `_aabb_corner_projection_range`, `_promoted_solid_world_bounds`, `_camera_body_world_bounds`,
  `_folded_leg_axis_unit`, `_swap_camera_body_clearance_deficit`; `_swap_auto_refocus_to_best_focus`
  layers the mesh deficit on the floor.
- `KrakenOS/UI/validate_open3d_lens_swap_auto_refocus.py` — real-geometry mesh-clearance test.

## In-app eyeball still owed

Verified against the flag's real AABBs, but the full live path (transformed camera mesh +
promoted-mirror metadata at swap time) runs only in-app. Confirm on a real AZ85 swap that the
camera now pins short of the mirror with a 2 mm gap and fires the "camera body" flag.
