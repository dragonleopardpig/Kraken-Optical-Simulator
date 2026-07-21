# 0391 — swap auto-refocus must reserve the whole camera BODY, not just the sensor plane

**Flag:** `flag_20260721_153325_838` — "After swapping the lens, the camera crash into the RA
mirror." (scene `machine_vision_AZ85_RA_Mirror.py`).

## The gap in 0388

0388 added a constraint-aware auto-refocus after a lens swap: it re-solves best focus and
CLAMPS the image gap to a mechanical minimum so the sensor can't be driven into the upstream
RA mirror. But `_swap_refocus_min_gap` only protected the **sensor plane** (a 2 mm floor). A
camera's sensor sits **behind** the body's front (flange) face, so the body reaches forward
toward the mirror: the hr25MCX flange-to-sensor depth is **11.48 mm**. Best focus pulled the
sensor to a "safe" 2 mm, but the camera body then crashed **11.48 mm into the mirror**
(measured on the flag: camera body `x[200.9, 270.9]` overlapped the mirror to `x=248.6`).

## Fix

`_swap_refocus_min_gap` now reserves the **whole camera body** when a camera is glued:

```python
standoff = float(self._current_camera_front_to_sensor_mm() or 0.0)   # 0 if no camera glued
if 0.0 < standoff < 1.0e6:            # bounds also reject NaN/inf
    return clearance + standoff       # sensor floor + flange-to-sensor depth
# else: no camera -> the sensor floor, capped by a thin fold mirror's own reserve (0388)
```

`camera_front_to_sensor_mm` is the vendor flange/C-mount depth already carried in the camera
record (hr25MCX 11.48, C-mount 17.526, …). So the sensor is held `clearance + standoff` from
the mirror, and the body front face clears it by `clearance`. Crucially the camera-body depth
**overrides** the thin-fold-mirror reserve cap that 0388 used — a 0.8 mm mirror reserve must
not shrink the clamp below the 11.48 mm body depth. With no camera glued, behaviour is
unchanged (2 mm floor / thin-mirror reserve). The flag message now names the camera body.

## Verification

- **Real AZ85 scene:** `_current_camera_front_to_sensor_mm()` → 11.48, `_swap_refocus_min_gap()`
  → **13.48** mm (was 2.0). The camera body clears the mirror by 2 mm instead of crashing in.
- **Guard** `validate_open3d_lens_swap_auto_refocus` (penta phase 326), display-free: a glued
  camera's min-gap = clearance + flange depth; a 3 mm sensor-safe-but-body-colliding best focus
  clamps to that and flags "camera body"; the body depth wins over a thin-mirror reserve; the
  no-camera / thin-mirror / no-op / safe-solve cases from 0388 still hold; the standoff lookup
  raising is safe (falls to the floor).

## Files

- `KrakenOS/UI/services/layout_table_workbench.py` — `_swap_refocus_min_gap` reserves the
  camera body; the flag message names it.
- `KrakenOS/UI/validate_open3d_lens_swap_auto_refocus.py` — camera-body test case (phase 326).

## In-app eyeball still owed

Verified headlessly (the folded best-focus solve runs live only). Confirm on a real AZ85 swap
that a shorter-BFD lens pins the camera short of the mirror and fires the "camera body" flag.
