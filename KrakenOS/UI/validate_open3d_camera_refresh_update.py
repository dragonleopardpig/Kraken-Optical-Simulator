"""Guard: refreshing the imported-camera registry UPDATES an already-merged
camera in a running session (bugs/0310).

Reported (recording flag_20260715_084708_976): after importing the BC-OM25M
camera and entering 12 mm at the flange-to-sensor prompt (0309), "the sensor is
not positioned correctly to the sensor position in the imported camera." The
12 mm was written to ``imported_cameras.json`` but the sensor still sat on the
mount face.

Root cause: ``_merge_imported_cameras`` skipped any name already in
``CAMERA_DATABASE`` (``str(name) in CAMERA_DATABASE: continue``). That guard
exists so the one-time module-load merge is idempotent, but it also made
``refresh_imported_cameras`` a no-op for a *re-import*: BC-OM25M was already
folded in at startup (a prior session's import), so writing 12 mm to the JSON
and calling refresh never updated the live record. ``_current_camera_front_to_
sensor_mm`` kept reading the stale 0, and ``camera_front_z = image_plane_z - 0``
seated the sensor on the mount face.

Fix: snapshot the built-in camera names once (``_BUILTIN_CAMERA_NAMES``) before
the module-load merge, and key the skip to THAT set. A built-in is still never
clobbered by an imported record of the same name, but an imported entry is now
added AND updated on refresh -- so the 12 mm reaches the running session.

This guard is DISPLAY-FREE (mutates only module globals it restores):
  * A -- refresh UPDATES an already-merged imported camera (0 -> 12 mm).
  * B -- a built-in camera is never overwritten by an imported record of the
    same name.
  * C -- a genuinely new imported camera is still added on refresh.
  * D (structural) -- ``_merge_imported_cameras`` no longer skips on
    ``in CAMERA_DATABASE`` and keys the built-in guard to ``_BUILTIN_CAMERA_NAMES``.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_camera_refresh_update

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import json
import tempfile
from pathlib import Path


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    from KrakenOS.UI import camera_database as cdb

    saved_json = cdb.IMPORTED_CAMERAS_JSON
    saved_db = dict(cdb.CAMERA_DATABASE)
    probe = "__kraken_0310_refresh_probe__"
    try:
        tmp = Path(tempfile.mkdtemp()) / "imported_cameras.json"
        cdb.IMPORTED_CAMERAS_JSON = tmp

        # A -- an already-merged imported camera with a stale 0 mm flange updates
        # to the re-imported 12 mm on refresh.
        cdb.CAMERA_DATABASE[probe] = {"camera_front_to_sensor_mm": 0.0, "sensor_width_mm": 23.04}
        tmp.write_text(
            json.dumps({probe: {"camera_front_to_sensor_mm": 12.0, "sensor_width_mm": 23.04}}),
            encoding="utf-8",
        )
        cdb.refresh_imported_cameras()
        got = cdb.CAMERA_DATABASE.get(probe, {}).get("camera_front_to_sensor_mm")
        ok(got == 12.0, f"A refresh updates an already-merged camera 0->12 (got {got})")

        # B -- a built-in camera is never clobbered by an imported record.
        builtin = next(iter(cdb._BUILTIN_CAMERA_NAMES))
        builtin_before = dict(cdb.CAMERA_DATABASE[builtin])
        tmp.write_text(
            json.dumps(
                {
                    builtin: {"sensor_width_mm": 999.0, "camera_front_to_sensor_mm": 999.0},
                    probe: {"camera_front_to_sensor_mm": 12.0},
                }
            ),
            encoding="utf-8",
        )
        cdb.refresh_imported_cameras()
        ok(cdb.CAMERA_DATABASE[builtin] == builtin_before, f"B built-in {builtin!r} not overwritten")

        # C -- a genuinely NEW imported camera is added on refresh.
        fresh = "__kraken_0310_fresh_probe__"
        cdb.CAMERA_DATABASE.pop(fresh, None)
        tmp.write_text(
            json.dumps({fresh: {"camera_front_to_sensor_mm": 7.5, "sensor_width_mm": 11.0}}),
            encoding="utf-8",
        )
        cdb.refresh_imported_cameras()
        added = cdb.CAMERA_DATABASE.get(fresh, {}).get("camera_front_to_sensor_mm")
        ok(added == 7.5, f"C a new imported camera is added on refresh (got {added})")

        # D -- structural: no skip-on-existing, built-in guard keyed to the snapshot.
        src = inspect.getsource(cdb._merge_imported_cameras)
        ok("in CAMERA_DATABASE:\n            continue" not in src, "D no skip-on-existing (in CAMERA_DATABASE)")
        ok("_BUILTIN_CAMERA_NAMES" in src, "D built-in guard keyed to _BUILTIN_CAMERA_NAMES")
    finally:
        cdb.IMPORTED_CAMERAS_JSON = saved_json
        cdb.CAMERA_DATABASE.clear()
        cdb.CAMERA_DATABASE.update(saved_db)

    passed = all(n.startswith("PASS") for n in notes)
    if verbose or not passed:
        for n in notes:
            print("  " + n)
    return passed, [n for n in notes if not n.startswith("PASS")]


def main() -> int:
    passed, failures = run_checks(verbose=True)
    if not passed:
        print("FAIL: imported-camera refresh update guard (bugs/0310)")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("PASS: imported-camera refresh update guard (bugs/0310)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
