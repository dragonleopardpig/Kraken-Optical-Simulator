"""Repro for bug 0100 -- non-seq cube/plate-before-lens "beam focuses at the splitter".

ROOT: the finite-object WORLD samplers (envelope/cone/sparse, the Open-3D `world_envelope` mode) aimed
every ray at ``_current_object_distance`` (= rows[0].thickness). An in-path beam-splitter/plate
promotion shrinks that from object->lens to object->cube, so the bundle converged ON the splitter
instead of filling the lens pupil -> transmit rays diverge past the detector, image circle lands at the
cube, etc. (the whole 0100 cascade).

FIX: `_build_world_bundles_from_pupil_points` (finite branch) now aims at the FIRST-ORDER REFERENCE
entrance pupil (`_launch_reference_entrance_pupil_z` -> `Kos.PupilCalc.PosPupInp` on the transmissive
reference), like the grid sampler. This repro builds a plate-before-lens scene (object_distance shrunk
to 100) and asserts the world bundles aim at the LENS (~336), not the plate (100).

Run: .devenv/state/venv/bin/python bugs/repro_0100.py
"""
from pathlib import Path
from dataclasses import replace
import numpy as np
from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
from KrakenOS.UI.render_layout_snapshot import _build_runtime_system
from KrakenOS.common_optical_layouts.machine_vision_150mm_datasheet_1x import SURFACES, SETTINGS

LAYOUT = Path("KrakenOS/common_optical_layouts/machine_vision_150mm_datasheet_1x.py")


def _derived_aim_z(app, bundles, pupil_pts) -> float | None:
    b = bundles[0]
    x, y, z, l, m, nn = [np.asarray(a, dtype=float) for a in b]
    ox = float(x[0])
    aims = [
        (float(pupil_pts[i][0]) - ox) * float(nn[i]) / float(l[i])
        for i in range(min(len(l), len(pupil_pts)))
        if abs(float(l[i])) > 1e-6
    ]
    return float(np.median(aims)) if aims else None


def main() -> int:
    rows = [SurfaceRow(**{k: v for k, v in s.items() if k in SurfaceRow.__dataclass_fields__}) for s in SURFACES]
    orig = float(rows[0].thickness)
    rows[0].thickness = 100.0
    tmpl = rows[1]
    rows.insert(1, replace(tmpl, glass="AIR", thickness=orig - 100.0, rc=0.0, k=0.0, name="plate back"))
    rows.insert(1, replace(tmpl, glass="BK7", thickness=50.0, rc=0.0, k=0.0, name="plate front"))
    app = KrakenLayoutEditor(headless=True)
    app.current_layout_file = LAYOUT
    app.rows = rows
    app._auto_assign_missing_elements(app.rows)
    app._apply_layout_settings(SETTINGS)
    system = _build_runtime_system(LAYOUT, app.rows)

    obj_d = float(app._current_object_distance())
    ep_z = app._launch_reference_entrance_pupil_z(system)
    pr = app._resolved_preview_pupil_radius(13.4, system=system)
    pupil_pts = app._sample_ray_count_pupil_points(pr)
    ok = ep_z is not None and ep_z > 250.0 and obj_d < 150.0
    print(f"object_distance (rows[0].thickness, shrunk) = {obj_d:.1f}")
    print(f"reference entrance-pupil z (the lens)       = {ep_z}")
    for name, fn in (("world_envelope", app._build_world_envelope_bundles), ("world_cone", app._build_world_cone_bundles)):
        aim = _derived_aim_z(app, fn(pr, system=system)[0], pupil_pts)
        hit = aim is not None and aim > 250.0
        ok = ok and hit
        print(f"  {name} bundle aim z = {aim:.1f}  -> aims at LENS not plate: {hit}" if aim is not None else f"  {name}: None")
    app.destroy()
    print("repro_0100:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
