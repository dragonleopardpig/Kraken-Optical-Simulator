"""Display-free guard for bugs/0227 -- the 2D layout must show the SAME sharp folded focus
the 3D inspector shows (attachment/2D.png: "not matching with the 3D -- rays defocus at the
detector").

Root cause: the 3D pipeline follows the folded display bend with the bugs/0217 reconcile
(the detector target + on-axis ray hard-stops snap onto the cone's real waist when the
trailing fold mirror overshoots the prescription Image row). ``refresh_plot`` (the 2D
layout, ``services/plot_refresh.py``) stopped at the bend, so the 2D drew the rays running
a plate PAST their focus to the overshot sensor line while the 3D showed them sharp ON the
detector. The fix mirrors the 3D pipeline exactly: bend -> reconcile.

  (A) PARITY: the 2D pipeline's detector target lands at the SAME world position as the 3D
      bundle's (both reconciled onto the waist).
  (B) SHARP: the 2D on-axis ray endpoints converge ON the 2D detector (gap < 1 mm).
  (C) CAUSAL: the OLD 2D (bend only, no reconcile) parks the detector at the overshot
      fold(prescription) -- tens of mm from the waist -- proving the reconcile is what
      closes the mismatch.
  (D) WIRED: refresh_plot runs the reconcile right after the display bend.

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


def _run_2d_pipeline(editor, *, reconcile: bool):
    """Mirror refresh_plot's phase 2+3 exactly (build -> folded-aware trace with the 2D
    sampling mode -> bundle -> bend [-> reconcile])."""
    wavelength = editor._current_wavelength()
    mode = editor._preview_2d_sampling_mode()
    if mode == "display_slice":
        mode = editor._preview_scene_sampling_mode()
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in editor.rows), default=1.0)
    system = editor.build_system(require_solids=True)
    folded_trace_rows = editor._folded_sequential_trace_rows(editor.rows)
    rays, fold_transform = editor._trace_preview_rays_folded_aware(
        system, wavelength, max_radius,
        sampling_mode=mode, folded_trace_rows=folded_trace_rows,
    )
    bundle = editor._build_scene_bundle(system, rays, max_radius)
    if folded_trace_rows is not None:
        editor._apply_folded_display_bend(bundle, fold_transform)
        if reconcile and fold_transform is not None:
            editor._reconcile_folded_image_to_ray_convergence(bundle)
    return bundle


def validate_2d_layout_matches_3d_focus() -> list[Check]:
    checks: list[Check] = []
    editor = _quiet(_build_editor, _AZ85)
    _quiet(carryover._promote_mirror2, editor)

    _s, _r, bundle_3d = _quiet(editor._build_preview_system_rays_bundle, update_state=True)
    det_3d = _detector(bundle_3d)

    bundle_2d = _quiet(_run_2d_pipeline, editor, reconcile=True)
    det_2d = _detector(bundle_2d)
    ends_2d = np.asarray(
        [np.asarray(p.points_world, dtype=float)[-1][:3] for p in bundle_2d.ray_paths]
    )
    on_axis = (
        ends_2d[np.linalg.norm(ends_2d - det_2d, axis=1) < 5.0]
        if det_2d is not None and len(ends_2d)
        else np.zeros((0, 3))
    )
    gap = (
        float(np.linalg.norm(on_axis.mean(axis=0) - det_2d))
        if len(on_axis) >= 5 and det_2d is not None
        else float("inf")
    )

    checks.append(Check(
        "PARITY: the 2D pipeline's detector lands where the 3D detector sits (both on the waist)",
        bool(det_3d is not None and det_2d is not None and np.allclose(det_3d, det_2d, atol=0.05)),
        f"3D={None if det_3d is None else np.round(det_3d, 3)} "
        f"2D={None if det_2d is None else np.round(det_2d, 3)}",
    ))
    checks.append(Check(
        "SHARP: the 2D on-axis rays converge ON the 2D detector (no defocus at the sensor line)",
        bool(len(on_axis) >= 5 and gap < 1.0),
        f"on_axis_rays={len(on_axis)} centroid_gap={gap:.3f}mm (expect < 1)",
    ))

    # CAUSAL: the pre-fix 2D (bend only) parks the detector at the overshot prescription.
    editor_old = _quiet(_build_editor, _AZ85)
    _quiet(carryover._promote_mirror2, editor_old)
    bundle_old = _quiet(_run_2d_pipeline, editor_old, reconcile=False)
    det_old = _detector(bundle_old)
    overshoot = (
        float(np.linalg.norm(det_old - det_3d))
        if det_old is not None and det_3d is not None
        else 0.0
    )
    checks.append(Check(
        "CAUSAL: without the reconcile the 2D detector sits tens of mm past the waist (the flagged defocus)",
        bool(overshoot > 10.0),
        f"bend-only detector={None if det_old is None else np.round(det_old, 2)} "
        f"overshoot vs waist={overshoot:.2f}mm (expect > 10)",
    ))

    try:
        plot_src = _PLOT_REFRESH_SRC.read_text(encoding="utf-8")
    except Exception:
        plot_src = ""
    bend_index = plot_src.find("self._apply_folded_display_bend(bundle, straight_equivalent_fold_transform)")
    reconcile_index = plot_src.find("self._reconcile_folded_image_to_ray_convergence(bundle)")
    checks.append(Check(
        "WIRED: refresh_plot runs the 0217 reconcile right after the display bend",
        bool(bend_index >= 0 and reconcile_index > bend_index),
        f"bend_at={bend_index} reconcile_at={reconcile_index}",
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
