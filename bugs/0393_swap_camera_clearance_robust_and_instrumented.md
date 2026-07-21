# 0393 — swap camera-body clearance: record-path fallback + instrumentation

**Flag:** `flag_20260722_074116_245` — "After swap, the camera still crash to RA mirror." Build
0df103bf (= 0392 running). Mirror row 8 thickness is **still 13.48** (the 0391 flange floor),
NOT the 33.28 the 0392 mesh-clearance should have produced — so `_swap_camera_body_clearance_deficit`
returned **0** live, meaning one geometry input came back empty and my `try/except` swallowed it.

## Why 0392 returned 0 (and couldn't be reproduced headlessly)

0392's math is verified correct on the flag's real AABBs (deficit 19.8 → gap 33.28, clears by
2 mm). But live it produced 0. The base-scene scaffold can't reproduce the modified config: its
`rows[-2]` is the lens datum (no promotion metadata), and the camera mesh build throws
`_external_cad_mesh_cache` (a `__new__`-bypasses-`__init__` artifact). So neither the mirror
bounds nor the camera bounds could be exercised headlessly, and the live failure was silent.

Prime suspect: the AZ85 hr25MCX is a **dropdown/vendor** camera. `_transformed_imported_camera_step_mesh`
needs `imported_camera_step_path`, which may be unset at swap time (the layout sets it, but the
swap/flip/solve churn or a dropdown-only camera can leave it empty) → mesh None → deficit 0.

## Fix

1. **Record-path fallback** (`_camera_body_world_bounds`): when the imported overlay mesh yields
   nothing, source the vendor **camera record's `step_path`** (present for dropdown cameras like
   the hr25MCX) through the SAME transform (temporarily set + restore `imported_camera_step_path`),
   so the body is placed identically. Returns `(None, reason)` so the caller can surface why.
2. **Instrumentation** (`_swap_clearance_debug` → recorder `swap_clearance_diagnostics`): the
   swap now records each clearance input (`upstream_name`, `cam_bounds`+`cam_reason`,
   `obstacle_bounds`, `leg`, `deficit`, `floor_mm`, `final_gap_mm`, `result`), captured in the
   flag bundle. The geometry is proven; this pins which live input is empty if it still is.
3. **Visible warning**: when a camera IS glued but the clearance geometry can't be resolved, the
   status line says so ("could NOT verify camera-body clearance …") instead of silently leaving
   the sensor where it may collide.

## Verification

- **Guard** `validate_open3d_lens_swap_auto_refocus` (phase 326): the mesh-clearance test now
  passes `(bounds, reason)`; the debug dict populates (`cam_reason=ok`, `obstacle_bounds`, `leg`,
  `deficit=19.8`, `result=ok`) and the wired swap bumps 13.48 → 33.28. All 0388/0391/0392 cases
  still hold.
- Recorder carries `swap_clearance_diagnostics` (new field, populated from the editor).

## Next (needs one live flag)

If the record-path fallback resolves the camera mesh, the swap now clears the body (gap → ~33).
If it still returns 0, the flag's `swap_clearance_diagnostics.result` + `cam_reason` name the
exact empty input (camera / obstacle / leg) and I finalize from that — no more blind geometry.

## Files

- `KrakenOS/UI/services/layout_table_workbench.py` — record-path fallback + instrumentation +
  visible warning.
- `KrakenOS/UI/services/open3d_event_recorder.py` — `swap_clearance_diagnostics` snapshot field.
- `KrakenOS/UI/validate_open3d_lens_swap_auto_refocus.py` — `(bounds, reason)` test update.
