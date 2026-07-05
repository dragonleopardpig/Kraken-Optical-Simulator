"""Display-free guard: the Quick-Estimation FOV overlay draws each disc SQUARE to its own plane.

On a folded (promoted-mirror) scene the object plane and the image/detector plane sit on different
legs, so the object->image vector ``img_pt - obj_pt`` is a SLANTED diagonal. The overlay used that
single diagonal as the normal for BOTH the object FOV circle and the image/sensor rectangle, so each
was rendered TILTED off its plane -- a ghost disc floating beside every real plane (the user:
"object plane and image plane: 2 of them each"). bugs/0196.

Fix: quick_estimation_overlay.add_overlays now reads the object / detector TARGET normals from the
scene bundle and draws each disc in its own plane (falling back to the diagonal only when the bundle
has no normals, e.g. a straight system where object and image share an axis anyway).

  (A) OBJECT SQUARE: the object FOV circle is coplanar with the object plane (every point's offset
      along the object normal is ~0) and is NOT coplanar with the object->image diagonal.
  (B) IMAGE SQUARE: the image circle is coplanar with the detector plane and NOT with the diagonal.
  (C) PICK DISKS SQUARE: the two pickable plane disks use the object / detector normals, not the
      diagonal.
  (D) FOLDED DISTINCT: on the folded scene the object normal and the image normal are genuinely
      different directions (so the shared-diagonal bug would have been visible).

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_qe_overlay_square_to_plane
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import io
import types
from dataclasses import dataclass

import numpy as np

from KrakenOS.UI.services.quick_estimation import QuickEstimationService
from KrakenOS.UI.services.quick_estimation_overlay import QuickEstimationOverlayService
from KrakenOS.UI.validate_open3d_ra_mirror_retroreflected_ray_dive import _AZ85, _build_editor


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def _quiet(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        return fn(*args, **kwargs)


def _max_out_of_plane(points: np.ndarray, center: np.ndarray, normal: np.ndarray) -> float:
    normal = normal / (np.linalg.norm(normal) or 1.0)
    return float(np.max(np.abs((points - center) @ normal)))


def validate_overlay_square_to_plane() -> list[Check]:
    checks: list[Check] = []
    editor = _quiet(_build_editor, _AZ85)
    qe = QuickEstimationService(
        types.SimpleNamespace(
            editor=editor,
            quick_estimation_var=types.SimpleNamespace(get=lambda: True),
        )
    )
    # Populate a finite-conjugate target so the overlay draws (object_mode == "Finite").
    _quiet(qe.fov_solve, "object", "thickness", 40.0, 40.0, None)
    system, _rays, bundle = _quiet(editor._build_preview_system_rays_bundle, update_state=True)

    normals: dict[str, np.ndarray] = {}
    for target in bundle.targets:
        n = getattr(target, "normal_world", None)
        if n is None:
            continue
        n = np.asarray(n, dtype=float).reshape(3)
        if getattr(target, "is_detector", False):
            normals["img"] = n
        elif getattr(target, "is_object", False):
            normals["obj"] = n

    obj_pt = np.asarray(editor._surface_reference_world_point(0, system=system), dtype=float).reshape(3)
    img_pt = np.asarray(
        editor._surface_reference_world_point(len(editor.rows) - 1, system=system), dtype=float
    ).reshape(3)
    diag = img_pt - obj_pt
    diag = diag / (np.linalg.norm(diag) or 1.0)

    # Capture the circle point-sets and the pick-disk normals without a real VTK backend.
    captured_circles: list[np.ndarray] = []
    captured_disks: list[tuple[np.ndarray, np.ndarray]] = []

    class _StubInspector:
        def __init__(self, ed, service):
            self.editor = ed
            self._service = service

        def _quick_estimation_service(self):
            return self._service

    overlay = QuickEstimationOverlayService(_StubInspector(editor, qe), pv_module=types.SimpleNamespace())
    overlay._solid_line_actor = lambda pts, color, width: captured_circles.append(np.asarray(pts, dtype=float))
    overlay._dashed_line_actor = lambda pts, color, width: None
    overlay._pick_disk_actor = lambda center, normal, r, color, ri: captured_disks.append(
        (np.asarray(center, dtype=float).reshape(3), np.asarray(normal, dtype=float).reshape(3))
    )
    drawn = _quiet(overlay.add_overlays, system, bundle)

    obj_normal = normals.get("obj")
    img_normal = normals.get("img")
    have_inputs = (
        drawn > 0
        and obj_normal is not None
        and img_normal is not None
        and len(captured_circles) >= 2
        and len(captured_disks) >= 2
    )

    # ---- (A) object FOV circle square to the object plane ----------------------------------- #
    object_circle = captured_circles[0] if captured_circles else np.zeros((0, 3))
    obj_in_plane = _max_out_of_plane(object_circle, obj_pt, obj_normal) if have_inputs else 9e9
    obj_vs_diag = _max_out_of_plane(object_circle, obj_pt, diag) if have_inputs else 0.0
    checks.append(Check(
        "OBJECT SQUARE: the FOV circle lies in the object plane, not perpendicular to the diagonal",
        have_inputs and obj_in_plane < 1e-6 and obj_vs_diag > 1.0,
        f"in_object_plane={round(obj_in_plane, 5)} vs_diagonal={round(obj_vs_diag, 3)}",
    ))

    # ---- (B) image circle square to the detector plane -------------------------------------- #
    image_circle = next(
        (c for c in captured_circles[1:] if np.linalg.norm(c.mean(axis=0) - img_pt) < 1.0),
        None,
    )
    img_in_plane = (
        _max_out_of_plane(image_circle, img_pt, img_normal) if have_inputs and image_circle is not None else 9e9
    )
    img_vs_diag = (
        _max_out_of_plane(image_circle, img_pt, diag) if have_inputs and image_circle is not None else 0.0
    )
    checks.append(Check(
        "IMAGE SQUARE: the image circle lies in the detector plane, not perpendicular to the diagonal",
        image_circle is not None and img_in_plane < 1e-6 and img_vs_diag > 1.0,
        f"in_detector_plane={round(img_in_plane, 5)} vs_diagonal={round(img_vs_diag, 3)}",
    ))

    # ---- (C) the pickable disks use each plane's own normal --------------------------------- #
    def _parallel(a, b):
        a = a / (np.linalg.norm(a) or 1.0)
        b = b / (np.linalg.norm(b) or 1.0)
        return abs(abs(float(np.dot(a, b))) - 1.0) < 1e-6

    disks_square = (
        have_inputs
        and _parallel(captured_disks[0][1], obj_normal)
        and _parallel(captured_disks[1][1], img_normal)
    )
    checks.append(Check(
        "PICK DISKS SQUARE: the object/image pick disks use the plane normals, not the diagonal",
        disks_square,
        f"obj_disk={np.round(captured_disks[0][1], 3).tolist() if captured_disks else None} "
        f"img_disk={np.round(captured_disks[1][1], 3).tolist() if len(captured_disks) > 1 else None}",
    ))

    # ---- (D) the two plane normals are genuinely different on a fold ------------------------ #
    distinct = have_inputs and not _parallel(obj_normal, img_normal)
    checks.append(Check(
        "FOLDED DISTINCT: object and image plane normals differ on the folded scene",
        distinct,
        f"obj_normal={np.round(obj_normal, 3).tolist() if obj_normal is not None else None} "
        f"img_normal={np.round(img_normal, 3).tolist() if img_normal is not None else None}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_overlay_square_to_plane()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_overlay_square_to_plane()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("QE-overlay-square-to-plane validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
