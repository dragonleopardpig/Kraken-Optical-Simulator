# 0310 — Re-importing a camera + entering the flange distance doesn't move the sensor in a running session

Recording `attachment/recorded_bug_repros/flag_20260715_084708_976/` — after importing the BC-OM25M
camera and entering **12 mm** at the flange-to-sensor prompt (**0309**), *"the sensor is not positioned
correctly to the sensor position in the imported camera."*

State snapshot: the camera body sits at `z = [657.087, 690.321]` (mount at the front / min-z, so **0308**'s
orientation is active), but the sensor (row 8) is at `z = 657.087` — **coincident with the mount face**.
If 12 mm had been applied the sensor would be at `z ≈ 669.087`. So the entered 12 mm never took effect.

## Root cause — `refresh_imported_cameras` can't *update* an already-merged camera
`imported_cameras.json` on disk **did** carry `camera_front_to_sensor_mm = 12.0` (0309's write worked). But
the live session kept reading **0**. The culprit is the merge guard:

```python
for name, record in payload.items():
    if not isinstance(record, dict) or str(name) in CAMERA_DATABASE:
        continue          # <-- skips ANY name already in the live DB
```

That skip makes the one-time module-load merge idempotent, but it also makes `refresh_imported_cameras()`
(called right after the folder importer writes the new record) a **no-op for a re-import**: BC-OM25M was
already folded into `CAMERA_DATABASE` at startup (a prior session's import), so the fresh 12 mm record was
skipped. `_current_camera_front_to_sensor_mm` kept returning the stale 0, and
`camera_front_z = image_plane_z − 0` seated the sensor on the mount face. A restart would have picked the
12 mm up (module load reads the JSON) — but the running session never did.

This also bites a single session: import → Cancel the flange prompt (0 mm) → notice the sensor is wrong →
re-import and enter 12 mm. The second import's refresh is skipped because the first already merged the name.

## The fix — key the guard to a built-in snapshot, so refresh UPDATES imported entries
`camera_database.py` now snapshots the built-in camera names **once**, before the module-load merge:

```python
_BUILTIN_CAMERA_NAMES = frozenset(CAMERA_DATABASE)
```

and `_merge_imported_cameras` skips only those:

```python
if str(name) in _BUILTIN_CAMERA_NAMES:
    continue          # never clobber a built-in camera of the same name
merged = dict(record)
...
CAMERA_DATABASE[str(name)] = merged   # add OR update imported entries
```

A built-in is still never overwritten by an imported record, but an imported entry is now **added and
updated** on refresh — so a re-import's flange distance reaches the running session immediately.

## Verified (display-free)
* `KrakenOS/UI/validate_open3d_camera_refresh_update.py` — **PASS** (5 checks): refresh updates an
  already-merged camera 0 → 12; a built-in is never overwritten by an imported record of the same name; a
  genuinely new imported camera is still added; and the structural change (no skip-on-existing, guard keyed
  to `_BUILTIN_CAMERA_NAMES`) is present. Hermetic — it saves/restores `IMPORTED_CAMERAS_JSON` +
  `CAMERA_DATABASE`, never touching the real registry.
* Penta **phase 272** delegates to it; baseline updated (`"272": "pass"`).

## Files
- `KrakenOS/UI/camera_database.py` — `_BUILTIN_CAMERA_NAMES` snapshot + `_merge_imported_cameras` guard.
- `KrakenOS/UI/validate_open3d_camera_refresh_update.py` — new display-free guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_272_camera_refresh_update`.
- `tools/penta_validator_baseline.json` — phase 272 baseline.

## Notes / remaining
- In-app eyeball owed (needs a GLX display): Open 3D → Import Camera from Folder →
  `attachment/Cameras/BC-OM25M`, enter **12** at the prompt, and confirm the sensor / image plane snaps
  12 mm behind the mount face **without a restart** (the whole point of this fix).
