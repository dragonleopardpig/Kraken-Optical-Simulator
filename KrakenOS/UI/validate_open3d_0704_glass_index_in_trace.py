"""Guard for bugs/0704 -- flag 110804: "Please validate the ray tracing actually
takes into account of glass refractive index."

First-principles, display-free validation that the NON-SEQUENTIAL MESH trace
(the engine the om05a scene runs on: STL solids + row glass) applies the glass
index:

  A  A converging pencil aimed at z=60 is traced twice through the SAME 10 mm
     mesh cube (an STL solid row, exactly how the om05a prisms trace) -- once
     with row glass BK7, once AIR. The marginal-ray crossing (best focus) must
     move by the plate law t*(1 - 1/n) = 10*(1 - 1/1.5168) = +3.407 mm -- a
     trace that ignored the index could not produce it.
  B  An oblique ray's cube-exit point is laterally displaced vs the AIR pass
     (rays really BEND at the mesh faces, not just re-labelled).

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0704_glass_index_in_trace
"""

from __future__ import annotations

import contextlib
import io
import tempfile
from pathlib import Path

import numpy as np

N_BK7 = 1.5168
CUBE_T = 10.0
EXPECT_SHIFT = CUBE_T * (1.0 - 1.0 / N_BK7)  # +3.407 mm
WL = 0.55
AIM_Z = 60.0


def _cube_stl_path() -> str:
    import pyvista as pv

    mesh = pv.Cube(center=(0.0, 0.0, 0.0), x_length=24.0, y_length=24.0, z_length=CUBE_T)
    path = Path(tempfile.gettempdir()) / "kraken_0704_cube.stl"
    mesh.triangulate().save(str(path))
    return str(path)


def _specs(glass: str, stl_path: str) -> list[dict]:
    base = {
        "rc": 0.0, "k": 0.0, "axicon": 0.0, "diff_ord": 0.0, "grating_d": 0.0,
        "grating_angle": 0.0, "in_diameter": 0.0, "drawing": 1.0, "extra_data": 0.0,
        "uda": "None", "tilt_x": 0.0, "tilt_y": 0.0, "tilt_z": 0.0,
        "desp_x": 0.0, "desp_y": 0.0, "desp_z": 0.0, "axis_move": 0.0,
    }
    return [
        dict(base, surface="Object", name="Object", thickness=25.0, diameter=40.0,
             glass="AIR", advanced={}),
        dict(base, surface="Standard", name="cube", thickness=35.0, diameter=40.0,
             glass=glass, advanced={"Solid_3d_stl": stl_path}),
        dict(base, surface="Image", name="Image", thickness=0.0, diameter=40.0,
             glass="AIR", advanced={}),
    ]


def _trace(glass: str, stl_path: str) -> "tuple[float, np.ndarray]":
    import KrakenOS as Kos

    from KrakenOS.UI.layout_editor import _build_system_from_specs

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        system = _build_system_from_specs(_specs(glass, stl_path))
        system.energy_probability = 0
        rays = Kos.raykeeper(system)
        heights = [1.0, 2.0, 3.0, 4.0]
        for h in heights:
            origin = np.array([0.0, h, 0.0])
            direction = np.array([0.0, -h, AIM_Z])
            direction = direction / np.linalg.norm(direction)
            system.NsTrace(origin.tolist(), direction.tolist(), WL)
            rays.push()
    crossings = []
    steep_exit = None
    for arr in rays.CC:
        pts = np.asarray(arr, dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 3:
            continue
        p0, p1 = pts[-2, :3], pts[-1, :3]
        dy = float(p1[1] - p0[1])
        if abs(dy) > 1e-12:
            s = -float(p0[1]) / dy
            crossings.append(float(p0[2] + s * (p1[2] - p0[2])))
        steep_exit = p0
    if not crossings:
        raise RuntimeError(f"no rays crossed the axis for glass={glass}")
    return float(np.median(crossings)), (
        np.asarray(steep_exit, dtype=float) if steep_exit is not None else np.zeros(3)
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    try:
        stl_path = _cube_stl_path()
        z_air, exit_air = _trace("AIR", stl_path)
        z_bk7, exit_bk7 = _trace("BK7", stl_path)
    except Exception as exc:
        notes.append(f"FAIL: trace raised {type(exc).__name__}: {exc}")
        return False, notes

    shift = z_bk7 - z_air
    ok(
        abs(z_air - AIM_Z) < 0.05,
        f"A1: AIR cube leaves the pencil converging at its aim (z={z_air:.3f}, want {AIM_Z})",
    )
    ok(
        abs(shift - EXPECT_SHIFT) < 0.02 * EXPECT_SHIFT + 0.02,
        f"A2: BK7 mesh cube shifts best focus by the plate law t(1-1/n): measured "
        f"{shift:+.3f} mm vs {EXPECT_SHIFT:+.3f} mm -- the NS mesh trace APPLIES the index",
    )
    lateral = float(np.linalg.norm((exit_bk7 - exit_air)[:2])) if exit_bk7.size >= 2 else 0.0
    ok(
        lateral > 1e-3,
        f"B: the steepest ray exits laterally displaced vs AIR ({lateral:.4f} mm) -- "
        f"rays really refract at the mesh faces",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0704 glass-index-in-trace validation PASSED")
        return 0
    print("0704 glass-index-in-trace validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
