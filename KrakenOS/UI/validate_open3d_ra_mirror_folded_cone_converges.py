"""Display-free guard for bugs/0197: on the folded RA-mirror scene the on-axis cone must
CONVERGE onto the drawn detector, not waist at the surrogate lens and diverge to the sensor.

bugs/0187 re-typed the promoted mirror cube as a sequential ``Mirror`` so the rays REACH the
+X sensor station. But that det=-1 frame flip does not preserve the ideal Thin-Lens focus:
the on-axis cone waists AT the surrogate lens (X~82, ~0.39mm) and then opens monotonically to
~5.1mm at the drawn detector (X~295.6) -- "focus before the surrogate, can't focus after"
(flag on machine_vision_AZ85_RA_Mirror.py).

Fix (bugs/0197): for a SINGLE fold, trace the UNFOLDED flat-plate EQUIVALENT (which images
with the real ideal-lens power, since first-order conjugates are invariant under a rigid fold)
and BEND the display rays at the mirror with the editor's own fold transform
(``_optical_axis_fold_world_transform_for_row``), so the folded cone lands CONVERGED, exactly
on the drawn detector. A CHAIN of folds keeps the 0187 sequential-``Mirror`` trace (composes).

This guard drives the REAL editor pipeline ``_build_preview_system_rays_bundle`` on the AZ85
scene (detector snapped to the image plane) and asserts:
  1. the folded-sequential path engaged (``_last_preview_folded_sequential`` is True);
  2. the on-axis cone transverse RMS is STRICTLY DECREASING down the folded +X arm (120mm ->
     the detector) -- the OLD sequential-Mirror cone rises monotonically here (diverges);
  3. the on-axis endpoints land on the DRAWN detector (|dX| < 0.05mm, the editor's own fold
     transform, not a hand-rolled reflection 12.5mm short) and CONVERGE (endpoint RMS < 0.1mm);
  4. both +/-13.7mm edge fields also land on the drawn detector and converge.

This is a STANDALONE guard (NOT a penta phase) -- no penta phase exercises a promoted mirror +
ideal Thin-Lens conjugate. In-app eyeball still owed (headless cannot drive the VTK inspector).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_folded_cone_converges

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import contextlib
import io
import sys

import numpy as np

from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


def _onaxis_paths(bundle) -> list[np.ndarray]:
    out: list[np.ndarray] = []
    for path in list(getattr(bundle, "ray_paths", []) or []):
        pw = np.asarray(getattr(path, "points_world", None), dtype=float)
        if pw.ndim != 2 or pw.shape[0] < 2 or pw.shape[1] < 3:
            continue
        if float(np.linalg.norm(pw[0][:3])) <= 1.0 and float(pw[:, 0].max()) > 250.0:
            out.append(pw)
    return out


def _edge_paths(bundle, sign: float) -> list[np.ndarray]:
    """Rays launched from the +/-13.7mm object field (start Y sign, start X,Z ~ 0)."""
    out: list[np.ndarray] = []
    for path in list(getattr(bundle, "ray_paths", []) or []):
        pw = np.asarray(getattr(path, "points_world", None), dtype=float)
        if pw.ndim != 2 or pw.shape[0] < 2 or pw.shape[1] < 3:
            continue
        start = pw[0][:3]
        if abs(start[0]) < 1.0 and abs(start[2]) < 1.0 and float(np.sign(start[1])) == sign and abs(start[1]) > 5.0:
            if float(pw[:, 0].max()) > 250.0:
                out.append(pw)
    return out


def _interp_transverse(pts: np.ndarray, x: float):
    xa = pts[:, 0]
    for i in range(len(xa) - 1):
        x0, x1 = xa[i], xa[i + 1]
        if (x0 - x) * (x1 - x) <= 0 and abs(x1 - x0) > 1e-9:
            t = (x - x0) / (x1 - x0)
            return pts[i, 1:3] + t * (pts[i + 1, 1:3] - pts[i, 1:3])
    return None


def _rms_at(paths: list[np.ndarray], x: float):
    offs = [_interp_transverse(p, x) for p in paths]
    offs = [o for o in offs if o is not None]
    if len(offs) < 4:
        return None
    arr = np.asarray(offs, dtype=float)
    return float(np.sqrt(((arr - arr.mean(0)) ** 2).sum(1).mean()))


def _endpoint_stats(paths: list[np.ndarray]):
    ends = np.asarray([p[-1][:3] for p in paths], dtype=float)
    x_mean = float(ends[:, 0].mean())
    trms = float(np.sqrt(((ends[:, 1:3] - ends[:, 1:3].mean(0)) ** 2).sum(1).mean()))
    return x_mean, trms


def main() -> int:
    failures: list[str] = []
    notes: list[str] = []

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        editor = _build_editor(_AZ85)
        editor._build_preview_system_rays_bundle(update_state=True)
        editor.snap_detector_to_image_plane()
        system, _rays, bundle = editor._build_preview_system_rays_bundle(update_state=True)
        n = len(editor.rows)
        drawn = np.asarray(
            editor._surface_reference_world_point(n - 1, system=system), dtype=float
        ).reshape(3)
        folded_engaged = bool(getattr(editor, "_last_preview_folded_sequential", False))

    drawn_x = float(drawn[0])

    # (1) the folded-sequential path engaged
    if not folded_engaged:
        failures.append("folded-sequential path did NOT engage (_last_preview_folded_sequential is not True)")

    onaxis = _onaxis_paths(bundle)
    if len(onaxis) < 6:
        failures.append(f"too few on-axis folded display rays ({len(onaxis)}) to test convergence")

    # (2) on-axis cone strictly converges down the folded +X arm
    sweep = [120.0, 160.0, 200.0, 240.0, 270.0, drawn_x - 8.0, drawn_x - 1.0]
    rms_curve: list[tuple[float, float]] = []
    if len(onaxis) >= 6:
        prev = None
        for x in sweep:
            r = _rms_at(onaxis, x)
            if r is None:
                continue
            rms_curve.append((x, r))
            if prev is not None and not (r < prev - 1e-6):
                failures.append(
                    f"on-axis cone did not converge at X={x:.1f}: RMS {r:.4f}mm "
                    f">= previous {prev:.4f}mm (the pre-0197 sequential-Mirror cone RISES here)"
                )
            prev = r
        if len(rms_curve) < 5:
            failures.append(f"on-axis convergence sweep produced too few stations ({len(rms_curve)})")

    # (3) on-axis endpoints land on the drawn detector and converge
    if len(onaxis) >= 6:
        x_mean, trms = _endpoint_stats(onaxis)
        if abs(x_mean - drawn_x) > 0.05:
            failures.append(
                f"on-axis endpoints not on the drawn detector: X mean {x_mean:.3f} vs drawn "
                f"{drawn_x:.3f} (dX {x_mean - drawn_x:+.3f}; a hand-rolled reflection lands ~12.5mm short)"
            )
        if not (trms < 0.1):
            failures.append(
                f"on-axis cone not converged at the detector: endpoint transverse RMS {trms:.4f}mm >= 0.1"
            )
        else:
            notes.append(
                f"on-axis: endpoint X={x_mean:.3f} (drawn {drawn_x:.3f}), transverse RMS={trms:.5f}mm; "
                f"cone {rms_curve[0][1]:.3f} -> {rms_curve[-1][1]:.4f}mm down the +X arm"
            )

    # (4) both edge fields land on the drawn detector and converge
    for sign, label in ((-1.0, "-13.7"), (1.0, "+13.7")):
        edge = _edge_paths(bundle, sign)
        if len(edge) < 6:
            failures.append(f"edge field {label}mm: too few rays ({len(edge)}) to test convergence")
            continue
        x_mean, trms = _endpoint_stats(edge)
        if abs(x_mean - drawn_x) > 0.05:
            failures.append(
                f"edge field {label}mm endpoints not on the drawn detector: X mean {x_mean:.3f} "
                f"vs drawn {drawn_x:.3f}"
            )
        if not (trms < 0.1):
            failures.append(
                f"edge field {label}mm not converged: endpoint transverse RMS {trms:.4f}mm >= 0.1"
            )
        else:
            notes.append(f"edge {label}mm: endpoint X={x_mean:.3f}, transverse RMS={trms:.5f}mm")

    if failures:
        print("FAIL bugs/0197 folded cone convergence:")
        for line in failures:
            print(f"  - {line}")
        return 1
    print("PASS bugs/0197 folded cone convergence:")
    print(f"  - folded-sequential engaged; on-axis cone converges onto the drawn detector at X={drawn_x:.3f}")
    for note in notes:
        print(f"  - {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
