# 0395 — swap camera-clearance: use the mirror's REAL DISPLAYED actor bounds

**Flag:** `flag_20260722_082931_051` — "after lens swap, camera still crash to RA mirror." Build
64df2dcb (= 0394). The 0393 diagnostics show 0394 re-centred on the wrong frame:

```
obstacle_center_source: live_bundle
obstacle_bounds: [459.31, 484.31, -12.5, 12.5, -195.4, -170.4]   ← wrong frame
leg: [0, 0, -1]   deficit: 0.0
```

## Why 0394 was still wrong

0394 re-centred the mirror on the scene-bundle `optical_solid` placement centre. But that
placement is in an **unfolded / system frame** (`[471, 0, -183]`), not the DISPLAYED position.
The mirror's real displayed actor bounds (from `row_actor_bounds[8]`) are **x[223.3, 248.6]
z[40.4, 65.7]** — which DO overlap the camera (`z[40.4, 51.0]`), the crash the user sees. The
camera bounds were displayed-frame correct all along; only the mirror was in the wrong frame.

There is no cheap *editor-side* source for a promoted solid's DISPLAYED (folded) bounds — the
promotion metadata is stale-on-move, the bundle placement is unfolded, and rebuilding the fold
transform means a full 3D system build.

## Fix

The inspector HAS the mirror's displayed bounds (its rendered actor), and the mirror does not
move during a lens swap. So the inspector captures the upstream element's real displayed AABB
from the live scene **before** the swap and injects it:

- `Kraken3DInspector._row_display_world_bounds(row_index)` — combined world AABB of the DISPLAYED
  actors for a row (`_actor_row_map` → `_actor_by_key[key].GetBounds()`).
- `swap_imaging_lens_from_folder` stashes `editor._swap_upstream_display_bounds` for
  `rows[-2]` before `editor.swap(...)`, clears it in `finally`.
- `_swap_camera_body_clearance_deficit` prefers the injected displayed AABB
  (`obstacle_center_source = inspector_actor`), falling back to the live-bundle / stale
  promotion centre only when it is absent (headless / no inspector).

The camera's displayed bounds already come from `_transformed_imported_camera_step_mesh` (which
reflects the just-solved gap), so the deficit now compares two displayed-frame AABBs.

On the flag geometry: obstacle = the real x[223.3,248.6] z[40.4,65.7], deficit **12.6 mm** (was
0), gap 13.48 → **26.08 mm**, camera clears the mirror by 2 mm along the −Z fold leg.

## Verification

- **Guard** `validate_open3d_lens_swap_auto_refocus` (phase 326): injected displayed bounds win
  over a (deliberately wrong) live-bundle placement, `obstacle_center_source=inspector_actor`,
  deficit ~12.6, obstacle equals the injected bounds. Stale/live-bundle/mesh/0388–0392 cases all
  still hold.
- Inspector `_row_display_world_bounds` present; helpers no-op safely headless.

## The full saga

0391 datum flange → crash; 0392 mesh clearance → 0 live (input empty); 0393 record fallback +
**instrumentation**; 0394 re-centre on bundle placement → wrong frame; **0395 inject the real
displayed actor bounds**. Each pass was pinned by the flag's `swap_clearance_diagnostics` — the
diagnostic-first move (0393) is what converged it.

## Files

- `KrakenOS/UI/open3d_inspector.py` — `_row_display_world_bounds` + capture/clear around the swap.
- `KrakenOS/UI/services/layout_table_workbench.py` — deficit prefers the injected displayed AABB.
- `KrakenOS/UI/validate_open3d_lens_swap_auto_refocus.py` — injected-bounds test.

## In-app eyeball still owed

The inspector capture runs only in-app. Confirm on a real AZ85 swap: `swap_clearance_diagnostics`
should read `obstacle_center_source: inspector_actor`, a non-zero deficit, and the camera pins
~2 mm clear of the mirror.
