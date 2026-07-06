"""Display-free guard for bugs/0227 -- the 2D layout must show the SAME sharp folded focus
the 3D inspector shows (attachment/2D.png: "not matching with the 3D -- rays defocus at the
detector").

bugs/0243 rework: both pipelines now trace the REAL folded system (first-surface mesh
mirrors, folded output-port poses, the KrakenSys Thin-Lens SIGN fix), so 2D/3D parity holds
BY CONSTRUCTION -- there is no display bend and no bugs/0217 reconcile snap any more. The
drawn rays terminate on the folded Image-surface seat, which the off-beam exemption
(``folded_beam_reached_mirror_fold_indices``) keeps at the TRUE prescription station, so
after ``snap_detector_to_image_plane`` the on-axis cone focuses stigmatically ON the drawn
sensor in both views.

  (A) PARITY: the 2D pipeline's detector target lands at the SAME world position as the 3D
      bundle's.
  (B) SHARP: after the paraxial snap, the 2D on-axis ray endpoints converge ON the 2D
      detector (gap < 1 mm) -- with no reconcile involved.
  (C) NATIVE: every sensor-reaching drawn ray terminates ON the folded Image-surface seat
      plane (the trace ends where the display draws the sensor; nothing is snapped).
  (D) WIRED: refresh_plot contains NO display bend and NO reconcile call any more -- the
      bundle is used exactly as traced.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_2d_layout_matches_3d_focus
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import KrakenOS.UI.validate_open3d_second_mirror_same_part_mirror_carryover as carryover
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import (
    _AZ85,
    _build_editor,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PLOT_REFRESH_SRC = PROJECT_ROOT / "KrakenOS" / "UI" / "services" / "plot_refresh.py"


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*args, **kwargs)


def _detector(bundle):
    for target in getattr(bundle, "targets", []) or []:
        if getattr(target, "is_detector", False):
            return np.asarray(target.center_world, dtype=float).reshape(3)
    return None


def _image_seat(editor):
    overrides = getattr(editor.last_system, "_optical_solid_output_port_pose_overrides", {}) or {}
    pose = overrides.get(len(editor.rows) - 1)
    if not isinstance(pose, dict):
        return None, None
    center = np.asarray(pose.get("center"), dtype=float).reshape(3)
    normal = np.asarray(pose.get("rotation"), dtype=float).reshape(3, 3)[:, 2]
    norm = float(np.linalg.norm(normal))
    return center, (normal / norm if norm > 1e-12 else normal)


def _run_2d_pipeline(editor):
    """Mirror refresh_plot's phase 2+3 exactly (build -> folded-aware trace with the 2D
    sampling mode -> bundle, used as traced -- bugs/0243: no bend, no reconcile)."""
    wavelength = editor._current_wavelength()
    mode = editor._preview_2d_sampling_mode()
    if mode == "display_slice":
        mode = editor._preview_scene_sampling_mode()
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in editor.rows), default=1.0)
    system = editor.build_system(require_solids=True)
    folded_trace_rows = editor._folded_sequential_trace_rows(editor.rows)
    rays, _fold_transform = editor._trace_preview_rays_folded_aware(
        system, wavelength, max_radius,
        sampling_mode=mode, folded_trace_rows=folded_trace_rows,
    )
    return editor._build_scene_bundle(system, rays, max_radius)


def validate_2d_layout_matches_3d_focus() -> list[Check]:
    checks: list[Check] = []
    editor = _quiet(_build_editor, _AZ85)
    _quiet(carryover._promote_mirror2, editor)
    # Put the sensor on the paraxial conjugate first -- the honest scene for a focus
    # comparison (the as-imported fixture gaps are legacy-defocused on purpose).
    _quiet(editor._build_preview_system_rays_bundle, update_state=True)
    _quiet(editor.snap_detector_to_image_plane)

    _s, _r, bundle_3d = _quiet(editor._build_preview_system_rays_bundle, update_state=True)
    det_3d = _detector(bundle_3d)
    seat_c, seat_n = _image_seat(editor)

    bundle_2d = _quiet(_run_2d_pipeline, editor)
    det_2d = _detector(bundle_2d)
    ends_2d = np.asarray(
        [np.asarray(p.points_world, dtype=float)[-1][:3] for p in bundle_2d.ray_paths]
    ) if bundle_2d.ray_paths else np.zeros((0, 3))

    checks.append(Check(
        "PARITY: the 2D pipeline's detector lands where the 3D detector sits",
        bool(det_3d is not None and det_2d is not None and np.allclose(det_3d, det_2d, atol=0.05)),
        f"3D={None if det_3d is None else np.round(det_3d, 3)} "
        f"2D={None if det_2d is None else np.round(det_2d, 3)}",
    ))

    reaching = np.zeros((0, 3))
    gap = float("inf")
    if seat_c is not None and len(ends_2d):
        on_plane = np.abs((ends_2d - seat_c[None, :]) @ seat_n) < 1e-6
        reaching = ends_2d[on_plane]
        near_chief = (
            reaching[np.linalg.norm(reaching - det_2d[None, :], axis=1) < 5.0]
            if det_2d is not None and len(reaching)
            else np.zeros((0, 3))
        )
        if len(near_chief) >= 5 and det_2d is not None:
            gap = float(np.linalg.norm(near_chief.mean(axis=0) - det_2d))
    checks.append(Check(
        "SHARP: after the paraxial snap the 2D on-axis rays converge ON the 2D detector "
        "(no reconcile involved)",
        bool(gap < 1.0),
        f"sensor-reaching={len(reaching)} centroid_gap={gap if gap != float('inf') else -1:.3f}mm (expect < 1)",
    ))
    checks.append(Check(
        "NATIVE: sensor-reaching drawn rays terminate ON the folded Image-surface seat "
        "(the trace ends where the display draws the sensor)",
        bool(seat_c is not None and len(reaching) >= 5),
        f"seat={'set' if seat_c is not None else 'missing'} rays_on_seat={len(reaching)}",
    ))

    try:
        plot_src = _PLOT_REFRESH_SRC.read_text(encoding="utf-8")
    except Exception:
        plot_src = ""
    bend_index = plot_src.find("self._apply_folded_display_bend(")
    reconcile_index = plot_src.find("self._reconcile_folded_image_to_ray_convergence(")
    checks.append(Check(
        "WIRED: refresh_plot no longer bends or reconciles the bundle (bugs/0243: the "
        "rays are drawn exactly as traced)",
        bool(bend_index < 0 and reconcile_index < 0),
        f"bend_at={bend_index} reconcile_at={reconcile_index} (expect both -1)",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_2d_layout_matches_3d_focus()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_2d_layout_matches_3d_focus()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("2D-layout-matches-3D-focus validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
