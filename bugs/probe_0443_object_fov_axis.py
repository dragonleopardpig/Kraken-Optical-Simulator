"""bugs/0443 -- the object FOV plate must face the OBJECT's own axis (+Z in its frame).

flag_20260726_153531 ("everything almost work except now the FOV plate is tilted"): on the
round-3 frozen+snapped AZ85 scene the detector-coverage object_axis was derived as
``row 1 world point - object world point``. Row 1 is a baked off-axis row after the
0433 freeze/snap, so the derived axis went diagonal (measured [0.461, 0, 0.888], ~27
degrees) and the green FOV rectangle drew tilted. The axis is now +Z rotated by the
OBJECT row's own tilts (the object is never frozen/snapped), with the legacy row-1
derivation as fallback only.

Run: DISPLAY=:N .devenv/state/venv/bin/python bugs/probe_0443_object_fov_axis.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(("ok " if ok else "XX "), label, (" " + detail if detail else ""))
    if not ok:
        FAILURES.append(label)


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.optical_solid_metadata import rotation_matrix_from_kraken_tilts
    from KrakenOS.UI.services.detector_coverage_overlay import (
        detector_coverage_metrics,
        detector_coverage_overlay_specs,
    )

    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")

        def object_axis_as_shipped() -> np.ndarray:
            obj = app.rows[0]
            rot = rotation_matrix_from_kraken_tilts(
                float(obj.tilt_x), float(obj.tilt_y), float(obj.tilt_z)
            )
            return np.asarray(rot @ np.array((0.0, 0.0, 1.0)), dtype=float).reshape(3)

        # 1: pristine folded scene -- the new derivation matches the legacy one (+Z).
        p0 = np.asarray(app._surface_reference_world_point(0, system=None), float).reshape(3)
        p1 = np.asarray(app._surface_reference_world_point(1, system=None), float).reshape(3)
        legacy = p1 - p0
        legacy = legacy / (np.linalg.norm(legacy) or 1.0)
        axis = object_axis_as_shipped()
        check(
            "pristine scene: object-frame +Z agrees with the legacy row-1 derivation",
            bool(np.allclose(axis, (0, 0, 1), atol=1e-9) and np.allclose(legacy, (0, 0, 1), atol=1e-6)),
            f"axis={axis.round(6).tolist()} legacy={legacy.round(6).tolist()}",
        )

        # 2: the user's round-3 workflow -- BS add, mirror delete (freeze), chain snap.
        app.add_beam_splitter_to_led(kind="plate")
        mirror1 = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
        app.delete_optical_step_rows([mirror1])
        rows = [
            i
            for i, r in enumerate(app.rows)
            if getattr(r, "surface", None) in ("Standard", "Thin Lens", "Aperture", "Image")
            and i > 0
            and "next gap" not in str(getattr(r, "name", ""))
        ]
        rec = {
            "axis_id": "axis:global:split",
            "points": np.array([(0.0, 0.0, 59.5), (348.0, 0.0, 59.5)]),
            "picked_world": np.array([77.0, 0.0, 59.5]),
        }
        app.snap_rows_to_axis(rows, rec)

        p0 = np.asarray(app._surface_reference_world_point(0, system=None), float).reshape(3)
        p1 = np.asarray(app._surface_reference_world_point(1, system=None), float).reshape(3)
        legacy = p1 - p0
        legacy = legacy / (np.linalg.norm(legacy) or 1.0)
        axis = object_axis_as_shipped()
        check(
            "frozen+snapped: legacy derivation is DIAGONAL (the bug this probe pins)",
            bool(abs(float(legacy[0])) > 0.2),
            f"legacy={legacy.round(3).tolist()}",
        )
        check(
            "frozen+snapped: shipped object axis stays exactly +Z",
            bool(np.allclose(axis, (0, 0, 1), atol=1e-9)),
            f"axis={axis.round(6).tolist()}",
        )

        # 3: the emitted object_fov_rect plane is perpendicular to the object axis.
        metrics = detector_coverage_metrics(23.0, 23.0, 16.3, 1.15, sensor_is_real=True)
        specs = detector_coverage_overlay_specs(
            p0,
            np.array([313.0, 0.0, -18.0]),
            metrics,
            object_mode_finite=True,
            object_axis=axis,
            image_axis=np.array([0.0, 0.0, -1.0]),
        )
        rect = next(s for s in specs if s["kind"] == "object_fov_rect")
        pts = np.asarray(rect["points"], float)
        normal = np.cross(pts[1] - pts[0], pts[2] - pts[1])
        normal = normal / (np.linalg.norm(normal) or 1.0)
        check(
            "object_fov_rect plane normal is +/-Z (the plate faces the source axis)",
            bool(np.allclose(np.abs(normal), (0, 0, 1), atol=1e-9)),
            f"normal={normal.round(6).tolist()}",
        )
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    if FAILURES:
        print(f"FAIL: {FAILURES}")
        return 1
    print("RESULT: PASS -- object FOV plate faces the object's own axis on frozen/snapped scenes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
