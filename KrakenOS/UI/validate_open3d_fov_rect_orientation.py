"""Guard: the 3D FOV / sensor rectangles render LANDSCAPE, not transposed.

Reported (attachment/3D.png): the green object-FOV rectangle and the orange
image-sensor rectangle were drawn portrait -- the long 29.9 mm sensor *width*
ran along the VERTICAL screen axis -- even though their numeric labels correctly
read ``29.9 x 22.4``. The user: "the FOV numerical value is correct, but the
rectangle drawn is reverse ... both object and image WxH seems reverse."

Root cause: every in-plane rectangle producer fed the sensor *width* to the
vertical in-plane axis.
  * scene_geometry.scene_target_active_footprint_polylines -- the shared detector
    footprint (orange sensor rect; also the 2D layout) mapped width -> tangent,
    the +Y vertical/meridional axis.
  * detector_coverage_overlay.detector_coverage_overlay_specs -- the green
    object-FOV rect mapped width -> u, and ``_basis`` returns u = +Y (vertical).
  * quick_estimation_overlay -- the yellow recommended-sensor rect, same ``_basis``.

Fix (display-only -- the optical solve is untouched): width spans the HORIZONTAL
in-plane axis (bitangent / v) and height the vertical axis (tangent / u), so a
landscape sensor reads landscape. The shared 2D footprint test
(validate_layout_plot_controller) was updated to the corrected orientation.

This guard is DISPLAY-FREE and portable (pure geometry; no vendor assets):
  * A -- the shared footprint, on a non-square (landscape) detector, puts width
    on the horizontal X axis and height on the vertical Y axis.
  * B -- the detector-coverage object-FOV rect (green) does the same.
  * C (fail-before/pass-after) -- source wiring: footprint maps width->bitangent
    (not tangent), and both overlay rects build with width->v.
  * D (bugs/0072) -- the faint *pickable* FOV fill (a separate actor) coincides
    with the green object-FOV edge; it lagged the 0069 fix and rendered
    transposed against its own outline ("shaded light rectangle not matching the
    green edge").

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_fov_rect_orientation

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

import numpy as np


def _extents(points) -> tuple[float, float, float]:
    p = np.asarray(points, dtype=float)
    return float(np.ptp(p[:, 0])), float(np.ptp(p[:, 1])), float(np.ptp(p[:, 2]))


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    from KrakenOS.UI.scene_geometry import (
        SceneTarget3D,
        scene_target_active_footprint_polylines,
    )
    from KrakenOS.UI.services import detector_coverage_overlay as dco
    from KrakenOS.UI.services import quick_estimation_overlay as qeo

    W, H = 30.0, 20.0  # non-square (landscape) so a transposition is visible

    # --- A. shared detector footprint (orange sensor rect + the 2D layout) ----
    target = SceneTarget3D(
        center_world=np.asarray((0.0, 0.0, 100.0), dtype=float),
        normal_world=np.asarray((0.0, 0.0, 1.0), dtype=float),   # optical axis +Z
        tangent_world=np.asarray((0.0, 1.0, 0.0), dtype=float),  # vertical +Y
        diameter=float((W * W + H * H) ** 0.5),
        active_width_mm=W,
        active_height_mm=H,
        is_detector=True,
    )
    rect = scene_target_active_footprint_polylines(target)[0]
    ax, ay, _az = _extents(rect)
    ok(abs(ax - W) <= 1e-6, f"A1: footprint width {W:g} spans horizontal X (ptpX={ax:.3f})")
    ok(abs(ay - H) <= 1e-6, f"A2: footprint height {H:g} spans vertical Y (ptpY={ay:.3f})")
    ok(ax > ay, f"A3: footprint reads landscape (X {ax:.1f} > Y {ay:.1f})")

    # --- B. detector-coverage object-FOV rectangle (green) -------------------
    mag = 0.5
    image_radius = 0.5 * float((W * W + H * H) ** 0.5) + 5.0  # comfortably covers
    metrics = dco.detector_coverage_metrics(W, H, image_radius, mag)
    obj_pt = (0.0, 0.0, 0.0)
    img_pt = (0.0, 0.0, 100.0)                                # axis along +Z
    specs = dco.detector_coverage_overlay_specs(obj_pt, img_pt, metrics, object_mode_finite=True)
    fov = next((s for s in specs if s["kind"] == "object_fov_rect"), None)
    ok(fov is not None, "B0: object_fov_rect emitted for a finite object")
    if fov is not None:
        bx, by, _bz = _extents(fov["points"])
        exp_w, exp_h = W / mag, H / mag                       # FOV = sensor / |m|
        ok(abs(bx - exp_w) <= 1e-6, f"B1: FOV width {exp_w:g} spans horizontal X (ptpX={bx:.3f})")
        ok(abs(by - exp_h) <= 1e-6, f"B2: FOV height {exp_h:g} spans vertical Y (ptpY={by:.3f})")
        ok(bx > by, f"B3: object FOV rect reads landscape (X {bx:.1f} > Y {by:.1f})")

    # --- C. source wiring (fail-before / pass-after) -------------------------
    foot_src = inspect.getsource(scene_target_active_footprint_polylines)
    # Anchor on ``bitangent`` (the longer token): ``tangent * X`` is a substring
    # of ``bitangent * X``, so only bitangent-anchored markers discriminate.
    ok("bitangent * half_w" in foot_src,
       "C1: footprint maps width(half_w)->bitangent (horizontal)")
    ok("bitangent * half_h" not in foot_src,
       "C2: footprint no longer maps height(half_h)->bitangent (old portrait)")
    cov_src = inspect.getsource(dco.detector_coverage_overlay_specs)
    ok("_rect_points(obj_pt, v, u," in cov_src,
       "C3: object FOV rect builds width->v (horizontal)")
    qe_src = inspect.getsource(qeo.QuickEstimationOverlayService.add_overlays)
    ok("_rect_points(img_pt, v, u," in qe_src,
       "C4: QE recommended-sensor rect builds width->v (horizontal)")

    # --- D. the faint pickable FOV fill matches the green edge (bugs/0072) -----
    # The shaded fill is a separate actor (DetectorCoverageOverlayService.
    # _pick_fill_actor) built from pick_fill_rect_points. Its corners must coincide
    # with the green object_fov_rect or the shaded plane reads transposed against
    # its own outline -- the reported "shaded light rectangle not matching the
    # green edge". This is a behavioral check on the shared corner helper.
    if fov is not None:
        u, v = dco._basis(np.asarray(img_pt, dtype=float) - np.asarray(obj_pt, dtype=float))
        fill = np.asarray(
            dco.pick_fill_rect_points(
                np.asarray(obj_pt, dtype=float), u, v,
                metrics.object_fov_half_width, metrics.object_fov_half_height,
            ),
            dtype=float,
        )
        green_corners = np.asarray(fov["points"], dtype=float)[:4]
        ok(fill.shape == (4, 3) and np.allclose(fill, green_corners, atol=1e-6),
           "D1: pickable FOV fill corners coincide with the green object-FOV edge")
        fx, fy, _fz = _extents(fill)
        ok(fx > fy, f"D2: pickable FOV fill reads landscape (X {fx:.1f} > Y {fy:.1f})")
    fill_src = inspect.getsource(dco.DetectorCoverageOverlayService._pick_fill_actor)
    ok("pick_fill_rect_points(" in fill_src,
       "D3: pick fill builds via pick_fill_rect_points (shares the edge orientation)")
    ok("corners = _rect_points(" not in fill_src,
       "D4: pick fill no longer maps width->u inline (old transposed fill)")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("FOV/sensor rectangle orientation validation passed.")
        return 0
    print("FOV/sensor rectangle orientation validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
