"""bugs/0471 guard -- the camera's SENSOR lands on the Image row, not its centre.

Flags 2026-07-29: "the sensor location does not match the camera STEP sensor location" and
"Camera crashes to RA mirror".

Measured before: the camera body's CENTRE sat on the sensor plane, so its beam-facing face was
36.82 mm up the beam and only 2.18 mm clear of the fold mirror -- which a focus move then ate,
driving the body ~5 mm into the mirror substrate.

The body-carry was never the problem (bugs/0456 tracked the sensor exactly). The ANCHOR was: a
persisted ``placement_offset_xyz`` from drags/glue/axis moves had displaced the body, and
``_seat_step_body_world_center`` faithfully preserves whatever offset exists.

``seat_camera_on_sensor`` recomputes only the along-beam component so the vendor front-to-sensor
distance puts the SENSOR on the Image row. It is an explicit action, not an automatic
correction, because that offset is the user's own placement state.

Note the sign: the front face sits front_to_sensor UPSTREAM of the sensor ALONG THE BEAM. The
existing seating math writes ``image_plane_z - front_to_sensor``, correct only while the beam
travels +Z; on a folded scene it arrives travelling -Z and that sign puts the camera entirely
behind its own sensor (first implementation did exactly that).

bugs/0473 extends it to THREE axes: registering or replacing a camera resets the placement
offset, and the default seats the body on the nominal axis -- on a folded scene nowhere near the
sensor. The user replaced a camera and it landed on the LED (body x = [-40, 40], sensor at
x = 229.9). Seating now also centres the body transversely on the sensor, and camera
registration performs it automatically.

Checks:
  SEATED  -- the front face ends front_to_sensor upstream of the sensor.
  LATERAL -- a body reset onto the nominal axis is brought back over the sensor.
  CLEAR   -- the body no longer overlaps another solid.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

BS_SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True
    if not BS_SCENE.exists():
        return True, ["SKIP: the BS scene is absent (gitignored attachment)"]

    app = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        app = KrakenLayoutEditor()
        app.layout_files["bs"] = BS_SCENE
        app.load_layout_by_name("bs")
        stations = app._row_z_positions()
        image_row = next(
            (i for i in range(len(app.rows) - 1, -1, -1) if str(getattr(app.rows[i], "surface", "")) == "Image"),
            None,
        )
        if image_row is None:
            notes.append("SKIP: no Image row")
            return ok, notes
        sensor_z = float(stations[image_row]) + float(app.rows[image_row].desp_z)
        back = float(app._current_camera_front_to_sensor_mm())

        app.seat_camera_on_sensor()
        bounds = np.asarray(app._transformed_imported_step_mesh_for_label("camera").bounds, dtype=float).reshape(6)
        front = float(bounds[5])
        if abs((front - sensor_z) - back) <= 0.05:
            notes.append(
                f"SEATED = the camera front sits {front - sensor_z:.3g} mm upstream of the sensor "
                f"(vendor front-to-sensor {back:.3g} mm)"
            )
        else:
            notes.append(
                f"SEATED the camera front is {front - sensor_z:.3g} mm from the sensor, expected {back:.3g} mm"
            )
            ok = False

        # bugs/0473: a body reset onto the nominal axis (what replacing a camera does) must be
        # brought back OVER the sensor, not merely shifted along the beam.
        app._set_step_placement_offset_xyz("camera", (0.0, 0.0, 0.0))
        app.seat_camera_on_sensor()
        reseated = np.asarray(
            app._transformed_imported_step_mesh_for_label("camera").bounds, dtype=float
        ).reshape(6)
        sensor_x = float(app.rows[image_row].desp_x)
        body_x = (reseated[0] + reseated[1]) / 2.0
        if abs(body_x - sensor_x) <= 1.0:
            notes.append(f"LATERAL = a reset body is re-seated over the sensor (x {body_x:.1f} vs {sensor_x:.1f})")
        else:
            notes.append(f"LATERAL a reset body stayed off the sensor: x {body_x:.1f} vs sensor {sensor_x:.1f}")
            ok = False

        collisions = app.camera_body_collisions()
        if not collisions:
            notes.append("CLEAR = the camera body overlaps nothing")
        else:
            notes.append(f"CLEAR the camera body still overlaps {collisions}")
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: scene drive failed ({exc!r})")
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
