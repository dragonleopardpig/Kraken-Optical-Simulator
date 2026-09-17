"""bugs/0552 diagnostic -- "still have some missed rays after swapped lens"
(recording_20260805_093725, flags _093447_605 and _093659_974).

The pre-swap AZ85 scene terminates ZERO rays as ``missed_image``. After the swap to the 75 mm
lens there are 59; the user's 23x23 object-plane solve brings it to 6. The question this
answers is whether those are EDGE-OF-FIELD grazes (the solved field exactly fills the sensor,
so corner rays land within a hair of the edge -- expected physics) or genuine misses landing
far off the detector (a real defect).

For every ``missed_image`` path it reports the terminal point, the sensor's own half-size, and
the miss expressed in SENSOR HALVES -- the only scale-free way to read it (the 0542 lesson:
"2-8 sensor-halves off-centre is not a near-miss anywhere").

Run:  xvfb-run -a .devenv/state/venv/bin/python bugs/diag_0552_missed_image_rays.py [scene]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

SCENE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("attachment/machine_vision_Apo75.py")


def main() -> int:
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector, _settle
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    try:
        app.layout_files["scene"] = SCENE
        app.load_layout_by_name("scene")
        # The saved file predates bugs/0550; neutralise its negative gap pose-preservingly so
        # this measures the CURRENT (post-fix) state.
        for index, row in enumerate(app.rows):
            thickness = float(getattr(row, "thickness", 0.0) or 0.0)
            if thickness >= 0.0:
                continue
            for follower in range(index + 1, len(app.rows)):
                app.rows[follower].desp_z = float(app.rows[follower].desp_z) + thickness
            row.thickness = 0.0

        insp = _open_3d_inspector(app)
        app._three_d_inspector = insp
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)
        _settle(insp)

        bundle = insp.__dict__.get("_current_scene_bundle")
        paths = list(getattr(bundle, "ray_paths", None) or [])

        # The sensor: the terminal Image row's active size and world centre.
        image_row = None
        for index in range(len(app.rows) - 1, -1, -1):
            if str(getattr(app.rows[index], "surface", "")) == "Image":
                image_row = index
                break
        stations = [0.0]
        total = 0.0
        for row in app.rows[:-1]:
            total += float(getattr(row, "thickness", 0.0) or 0.0)
            stations.append(total)
        row = app.rows[image_row]
        centre = np.asarray(
            [float(row.desp_x), float(row.desp_y), stations[image_row] + float(row.desp_z)],
            dtype=float,
        )
        try:
            settings = app._row_detector_settings(row)
            width = float(settings.get("active_width_mm", 0.0) or 0.0)
            height = float(settings.get("active_height_mm", 0.0) or 0.0)
        except Exception:
            width = height = 0.0
        if width <= 0.0 or height <= 0.0:
            width = height = float(getattr(row, "diameter", 0.0) or 0.0)
        half = 0.5 * max(width, height)
        print(f"scene: {SCENE.name}")
        print(f"sensor: row S{image_row}  centre {np.round(centre, 3)}  active {width:.3f} x {height:.3f} mm  half {half:.3f}")

        misses = []
        census = {}
        for path in paths:
            reason = str(getattr(path, "termination_reason", "") or "")
            census[reason] = census.get(reason, 0) + 1
            if reason != "missed_image":
                continue
            pts = np.asarray(getattr(path, "points_world", np.empty((0, 3))), dtype=float)
            if pts.ndim != 2 or pts.shape[0] < 1:
                continue
            misses.append(pts[-1][:3])
        print("census:", census)

        if not misses:
            print("\nNo missed_image rays in this state.")
            return 0
        # Two units, because ONE of them misleads. `half` above is the terminal row's
        # diameter/2 -- on a square sensor that is the SEMI-DIAGONAL (measured: the Ø32.583
        # "image circle" is exactly 23.04 x sqrt(2), i.e. the same sensor, not a bigger one).
        # A miss is "on the sensor" only if BOTH axes are inside the square half-side, so
        # report the per-axis figure beside the radial one.
        side_half = half / np.sqrt(2.0)
        print(f"\n{len(misses)} missed_image ray(s):   square half-side = {side_half:.3f} mm, "
              f"corner radius = {half:.3f} mm")
        print(f"  {'terminal point':<34}{'|dx|':>9}{'|dy|':>9}{'radial':>9}{'x corner r':>12}")
        worst = 0.0
        for point in misses:
            offset = point - centre
            radial = float(np.linalg.norm(offset[:2]))  # transverse to the sensor normal
            corners = radial / half if half > 1e-9 else float("nan")
            worst = max(worst, corners)
            print(
                f"  {str(np.round(point, 3)):<34}{abs(offset[0]):>9.2f}{abs(offset[1]):>9.2f}"
                f"{radial:>9.2f}{corners:>12.2f}"
            )
        print(f"\nworst miss = {worst:.2f} x the corner radius")
        if worst <= 1.05:
            print(
                "VERDICT: EDGE-OF-FIELD. Every miss lands within ~1 sensor half of centre -- the "
                "solved field exactly fills the sensor, so corner rays graze the edge. Expected."
            )
        elif worst <= 3.0:
            print("VERDICT: MARGINAL -- misses sit just outside the sensor; check the field/sensor match.")
        else:
            print(
                "VERDICT: REAL MISS -- rays land many sensor-halves off. Not an edge graze; "
                "the imaging geometry is wrong."
            )
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
