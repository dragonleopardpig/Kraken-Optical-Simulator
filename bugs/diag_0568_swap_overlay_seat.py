"""Diagnostic: where does a SWAPPED lens STEP overlay's optical axis actually land?

Flag ``flag_20260805_203837_379`` -- "swap a lens, Lens STEP is not centered to
optical axis, I think because of the screw."  The scene is the user's
``machine_vision_AZ85_RA_Mirror_BS`` (0433-FROZEN: no fold transform, the overlay
is placed by rotation + placement offset), lens swapped ELS-85 (0703) -> PYRITE 45-85.

Replays the REAL display alignment (``_cad_mesh_aligned_to_optical_axis``) with the
scene's own pose numbers for BOTH bodies and reports, for each, the world line the
barrel (optical) axis lands on -- measured by pushing two probe points that lie ON
the CAD cylinder axis through the very same transform.

Run:
    .devenv/state/venv/bin/python bugs/diag_0568_swap_overlay_seat.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

ELS85 = PROJECT_ROOT / "attachment" / "Lens" / "0703-005-000-40-EXC" / "0703-005-000-40_PA_a_STEP.stp"
PYRITE = PROJECT_ROOT / "attachment" / "Lens" / "PYRITE_45_85_05x-20x_V38_1072517" / "1072517_00165969_001.stp"

# --- the flagged scene's own numbers -------------------------------------------------
# attachment/machine_vision_AZ85_RA_Mirror_BS.py (pre-swap, ELS-85 mounted):
POSE = dict(
    reverse=True,          # lens_step_reverse_direction
    rot_x=0.0,             # lens_step_rotation_x_deg
    rot_y=270.0,           # lens_step_rotation_y_deg
    rot_z=180.0,           # lens_step_rotation_z_deg
    placement=(107.78559408193703, 0.0, -94.28301777904986),
)
# _lens_front_datum_z() = the front datum's STATION in the straight chain (Object
# thickness); the swap leaves the Object row alone, so it is the same before/after.
FRONT_DATUM_STATION = 155.520

# The scene's BS-reflect leg (flag: axis:global:split) -- the line the lens sits on.
LEG_AXIS_WORLD_Z = 55.359
LEG_AXIS_WORLD_Y = 0.0

# The flag's recorded lens STEP actor bounds, post-swap (PYRITE mounted).
FLAG_LENS_BOUNDS = (76.574, 124.374, -24.248, 24.250, 23.855, 75.471)


def probe():
    from KrakenOS.UI.services.layout_polyline_display import LayoutPolylineDisplayMixin

    insp = object.__new__(LayoutPolylineDisplayMixin)
    insp.append_debug = lambda *a, **k: None
    insp._external_cad_mesh_cache = {}
    return insp


def seat(insp, step_path: Path, *, largest: bool, front_datum_station: float, pose=POSE):
    """Return (bounds, axis_point_world, axis_dir_world) for one lens body."""
    import pyvista as pv

    mesh = insp._load_step_mesh(step_path, largest_component=largest, allow_slow_import=True)
    axis = insp._step_primary_cylinder_axis(step_path)
    point = insp._step_primary_cylinder_axis_point(step_path)

    # Two probe points ON the CAD cylinder axis, at 25%/75% of the body's axial span,
    # so they are strictly interior and cannot perturb any bbox/extreme the alignment
    # derives its constants from.
    pts = np.asarray(mesh.points, dtype=float)
    t = (pts - point) @ axis
    t0, t1 = float(t.min()), float(t.max())
    probes = np.array([point + axis * (t0 + 0.25 * (t1 - t0)), point + axis * (t0 + 0.75 * (t1 - t0))])
    stacked = pv.PolyData(np.vstack([pts, probes]))

    insp.imported_lens_step_path = step_path
    insp.lens_step_reverse_direction = bool(pose["reverse"])
    insp.lens_step_rotation_x_deg = float(pose["rot_x"])
    insp.lens_step_rotation_y_deg = float(pose["rot_y"])
    insp.lens_step_rotation_z_deg = float(pose["rot_z"])

    flip_shift = insp._lens_step_flip_axial_shift()
    # rot_y != 0 -> _lens_step_display_front_z() short-circuits to the plain datum pin.
    target_front_z = float(front_datum_station)

    aligned = insp._cad_mesh_aligned_to_optical_axis(
        stacked,
        source_axis=axis,
        front_face="min" if pose["reverse"] else "max",
        target_front_z=target_front_z,
        flip_axial_shift=flip_shift,
        label="Lens STEP",
        roll_deg=float(pose["rot_z"]),
        x_rotation_deg=float(pose["rot_x"]),
        y_rotation_deg=float(pose["rot_y"]),
        axis_offset_xy=(0.0, 0.0),
        placement_offset_xyz=tuple(float(v) for v in pose["placement"]),
        optical_axis_point_xyz=point,
    )
    out = np.asarray(aligned.points, dtype=float)
    body, probe_world = out[:-2], out[-2:]
    bounds = (
        float(body[:, 0].min()), float(body[:, 0].max()),
        float(body[:, 1].min()), float(body[:, 1].max()),
        float(body[:, 2].min()), float(body[:, 2].max()),
    )
    direction = probe_world[1] - probe_world[0]
    direction = direction / max(float(np.linalg.norm(direction)), 1e-12)
    return bounds, probe_world[0], direction, flip_shift, target_front_z


def off_axis(point_world, dir_world):
    """Transverse distance from the scene's BS-reflect leg (y=0, z=LEG_AXIS_WORLD_Z,
    running along +x): project the body-axis point onto the plane perpendicular to x."""
    return (
        float(point_world[1] - LEG_AXIS_WORLD_Y),
        float(point_world[2] - LEG_AXIS_WORLD_Z),
    )


def main() -> int:
    insp = probe()
    print("Scene: machine_vision_AZ85_RA_Mirror_BS (0433-frozen, no fold transform)")
    print(f"  leg = axis:global:split -> along +x at y={LEG_AXIS_WORLD_Y}, z={LEG_AXIS_WORLD_Z}")
    print(f"  overlay pose (PRESERVED across the swap by bugs/0381): {POSE}")
    print(f"  target_front_z = _lens_front_datum_z() = {FRONT_DATUM_STATION}")
    print()

    for name, path, largest in (
        ("ELS-85 / 0703 (before the swap)", ELS85, False),
        ("PYRITE 45-85  (after the swap)", PYRITE, True),
    ):
        if not path.exists():
            print(f"SKIP (absent): {path}")
            continue
        bounds, axis_point, axis_dir, flip_shift, tfz = seat(
            insp, path, largest=largest, front_datum_station=FRONT_DATUM_STATION
        )
        dy, dz = off_axis(axis_point, axis_dir)
        print(f"--- {name}  [{path.name}]")
        print(f"    flip_axial_shift {flip_shift:.4f}   target_front_z {tfz:.3f}")
        print(f"    world bounds  x[{bounds[0]:.3f},{bounds[1]:.3f}] "
              f"y[{bounds[2]:.3f},{bounds[3]:.3f}] z[{bounds[4]:.3f},{bounds[5]:.3f}]")
        print(f"    barrel axis   dir {np.round(axis_dir, 4).tolist()}  through "
              f"{np.round(axis_point, 3).tolist()}")
        print(f"    >>> OFF THE LEG by  dy={dy:+.3f} mm   dz={dz:+.3f} mm")
        print()

    if PYRITE.exists():
        bounds, _p, _d, _f, _t = seat(insp, PYRITE, largest=True, front_datum_station=FRONT_DATUM_STATION)
        diff = [abs(a - b) for a, b in zip(bounds, FLAG_LENS_BOUNDS)]
        print("Cross-check against the flag's recorded lens actor bounds:")
        print(f"    replayed {tuple(round(v, 3) for v in bounds)}")
        print(f"    flag     {FLAG_LENS_BOUNDS}")
        print(f"    max |delta| = {max(diff):.4f} mm  "
              f"({'MATCH -- the replay IS the shipped placement' if max(diff) < 0.05 else 'MISMATCH'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
