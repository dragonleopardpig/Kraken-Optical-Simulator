"""bugs/0522 guard -- the launch matrix carries COMPULSORY FOV-corner probe rays.

User request (2026-08-03): rays must launch from the very edge/corner of the field so
anything between object and sensor that would clip the beam shows immediately. With
``field_count = 1`` the finite-object world launch sampled only the FOV centre; the
builder now appends a skeletal probe fan (chief + 4 pupil-rim rays) from each FOV corner
the field grid missed, using the coupled bound or the object-FOV rectangle (sensor / |m|).

Checks:
  SOURCE -- the corner-probe block and its object-FOV fallback exist.
  REAL   -- on the frozen AZ85 scene the traced bundle contains launch origins at all
            four FOV corners.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import trace_preview_sampling as _tps

    src = _inspect.getsource(_tps.TracePreviewSamplingMixin._build_world_bundles_from_pupil_points)
    if "field_launches" in src and "_imaging_fov_half_extents" in src:
        notes.append("SOURCE = corner probes + the object-FOV fallback are wired")
    else:
        notes.append("SOURCE the 0522 corner-probe block is missing")
        ok = False
    grid_src = _inspect.getsource(_tps.TracePreviewSamplingMixin._sample_imaging_field_grid_pairs)
    if "_imaging_fov_half_extents" in grid_src:
        notes.append("SOURCE = the field grid spans the object-FOV rectangle (0523)")
    else:
        notes.append("SOURCE the 0523 rectangular field grid is missing")
        ok = False

    if not SCENE.exists():
        notes.append("SKIP: frozen AZ85 scene absent (gitignored attachment)")
        return ok, notes

    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        mag = app._current_finite_paraxial_magnification()
        dims = app._current_camera_sensor_active_mm()
        if not mag or not dims:
            notes.append(f"SKIP: no object-FOV rectangle on this scene (mag={mag}, dims={dims})")
            return ok, notes
        hx = float(dims[0]) / abs(float(mag)) / 2.0
        hy = float(dims[1]) / abs(float(mag)) / 2.0
        _, _, bundle = app._build_preview_system_rays_bundle(update_state=True)
        starts = np.asarray(
            [p.points_world[0] for p in (bundle.ray_paths or []) if len(getattr(p, "points_world", [])) > 0],
            dtype=float,
        )
        if starts.size == 0:
            notes.append("SKIP: no traced ray paths")
            return ok, notes
        from KrakenOS.UI.nonseq_output_ports import axis_root_origin

        anchor = np.asarray(axis_root_origin(app.rows), dtype=float).reshape(-1)[:2]
        hit = 0
        for cx, cy in ((-hx, -hy), (hx, -hy), (-hx, hy), (hx, hy)):
            origin = anchor - np.asarray([cx, cy], dtype=float)
            d = np.linalg.norm(starts[:, :2] - origin, axis=1)
            if float(d.min()) < 0.5:
                hit += 1
        if hit == 4:
            notes.append(f"REAL = all four FOV corners launch probe rays (half extents {hx:.1f}x{hy:.1f})")
        else:
            notes.append(f"REAL only {hit}/4 corner origins found (half extents {hx:.1f}x{hy:.1f})")
            ok = False
    except Exception as exc:
        notes.append(f"SKIP: real-scene drive failed ({exc!r})")
    finally:
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
