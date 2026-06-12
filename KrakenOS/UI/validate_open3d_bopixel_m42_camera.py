"""Guard: the 65 MP Bopixel camera is the M42-mount variant, edge-to-sensor 11.5 mm.

The user runs the M42 version of the Japan Bopixel BC-GM65M12X4 (not the F-mount
version): "The Bopixel camera 65MP, can change to M42? ... I am using M42 version,
not F-mount version" and "The distance between the edge to the camera sensor is
11.5mm". The F-mount entry in the camera database was *replaced* (not duplicated)
with the M42 variant: lens mount ``M42 Mount``, ``camera_front_to_sensor_mm`` 11.5
(the F-mount flange sat 46.5 mm in front of the sensor), the M42 STEP body
(66.3 x 80.6 x 80.0 mm vs the F-mount 92 x 80 x 80), and the M42 STEP path. The
sensor itself is unchanged (29.9 x 22.4 mm, 65 MP).

The camera *database* lives in tracked source, so check A always runs. The layout
that mounts it (``attachment/machine_vision_120mm_65M.py``) and the vendor STEP are
gitignored user attachments, so check B is skip-if-absent.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_bopixel_m42_camera

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import os
from pathlib import Path

_M42_NAME = "Japan Bopixel BC-GM65M12X4-M42"
_F_NAME = "Japan Bopixel BC-GM65M12X4-F"
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    def skip(label: str) -> None:
        notes.append("SKIP " + label)

    from KrakenOS.UI import camera_database as cdb

    # --- A. the M42 camera database entry (always runs; tracked source) -------
    record = cdb.camera_record(_M42_NAME)
    ok(record is not None, f"A0: camera DB has '{_M42_NAME}'")
    ok(_F_NAME not in cdb.CAMERA_DATABASE,
       f"A1: the old F-mount key '{_F_NAME}' was replaced (not duplicated)")
    if record is not None:
        ok(str(record.get("lens_mount")) == "M42 Mount",
           f"A2: lens_mount is 'M42 Mount' (got {record.get('lens_mount')!r})")
        front = record.get("camera_front_to_sensor_mm")
        ok(front is not None and abs(float(front) - 11.5) <= 1e-9,
           f"A3: camera_front_to_sensor_mm is 11.5 (got {front!r})")
        ok(str(record.get("model")) == "BC-GM65M12X4-M42",
           f"A4: model is 'BC-GM65M12X4-M42' (got {record.get('model')!r})")
        sensor = cdb.camera_sensor_active_mm(_M42_NAME)
        ok(sensor is not None
           and abs(sensor[0] - 29.90) <= 1e-6 and abs(sensor[1] - 22.40) <= 1e-6,
           f"A5: sensor active area unchanged at 29.9 x 22.4 mm (got {sensor})")
        ok(sensor is not None and sensor[0] > sensor[1],
           "A6: sensor is landscape (width > height)")
        step = str(record.get("step_path") or "")
        ok(os.path.basename(step) == "BC-GMC65M12X4-M42.STEP",
           f"A7: step_path points at the M42 STEP (got {os.path.basename(step)!r})")
        body = record.get("body_dimensions_lwh_mm")
        ok(isinstance(body, tuple) and len(body) == 3
           and abs(float(body[0]) - 66.3) <= 1e-6
           and abs(float(body[1]) - 80.6) <= 1e-6
           and abs(float(body[2]) - 80.0) <= 1e-6,
           f"A8: body L x W x H is the M42 STEP bbox 66.3 x 80.6 x 80.0 (got {body})")

    # No remaining camera may still be the F-mount 65M (mount or flange distance).
    f_mount_leftover = any(
        str(rec.get("model", "")).startswith("BC-GM65M12X4")
        and (str(rec.get("lens_mount")) == "F Mount"
             or abs(float(rec.get("camera_front_to_sensor_mm", 0.0)) - 46.5) <= 1e-9)
        for rec in cdb.CAMERA_DATABASE.values()
    )
    ok(not f_mount_leftover,
       "A9: no 65M Bopixel entry is still the F-mount variant (F Mount / 46.5 mm flange)")

    # --- B. layout wiring (skip-if-absent; gitignored user attachment) --------
    layout = _PROJECT_ROOT / "attachment" / "machine_vision_120mm_65M.py"
    if not layout.exists():
        skip("B: layout attachment/machine_vision_120mm_65M.py absent (gitignored)")
    else:
        text = layout.read_text(encoding="utf-8", errors="ignore")
        ok(_M42_NAME in text,
           "B1: the 65M layout mounts the M42 camera_model")
        ok("BC-GMC65M12X4-M42.STEP" in text,
           "B2: the 65M layout points camera_step_path at the M42 STEP")
        ok(_F_NAME not in text and "BC-GM(C)65M12X4-F" not in text,
           "B3: the 65M layout no longer references the F-mount camera/STEP")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Bopixel M42 camera validation passed.")
        return 0
    print("Bopixel M42 camera validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
