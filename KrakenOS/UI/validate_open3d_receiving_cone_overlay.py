"""Display-free guard for bugs/0354 -- the imaging lens's receiving-angle cone.

A faint translucent loft between the imaged-FOV rectangle at the Object plane and
the lens entrance pupil (the acceptance volume). PURE: ring geometry/opacity;
WIRING: the editor spec anchors on the first-order machinery and the render path
gates on the toggle.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_receiving_cone_overlay
"""

from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.services.receiving_cone_overlay import (
    RECEIVING_CONE_OPACITY,
    build_receiving_cone_overlay,
)


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    spec = build_receiving_cone_overlay(19.5, 19.5, 0.0, 180.0, 20.0)
    if not spec:
        failures.append("cone builder returned None for a valid MV-150-like geometry")
    else:
        pts = np.asarray(spec["points"], dtype=float)
        n = pts.shape[0] // 2
        if pts.shape != (2 * n, 3) or n < 8:
            failures.append(f"cone points malformed: {pts.shape}")
        else:
            if not np.allclose(pts[:n, 2], 0.0) or not np.allclose(pts[n:, 2], 180.0):
                failures.append("cone rings are not seated on the Object / pupil planes")
            radii = np.linalg.norm(pts[n:, :2], axis=1)
            if not np.allclose(radii, 20.0, atol=1e-9):
                failures.append("pupil ring radius does not match the entrance pupil")
            fx = np.max(np.abs(pts[:n, 0]))
            fy = np.max(np.abs(pts[:n, 1]))
            if abs(fx - 19.5) > 1e-9 or abs(fy - 19.5) > 1e-9:
                failures.append("FOV ring does not span the imaged FOV half-extents")
        if float(spec["opacity"]) > 0.3:
            failures.append("the cone must stay faint (opacity <= 0.3)")
        faces = np.asarray(spec["faces"], dtype=np.int64)
        if faces.size != 2 * n * 4:
            failures.append(f"cone side skin face count wrong: {faces.size}")
    if build_receiving_cone_overlay(0.0, 19.5, 0.0, 180.0, 20.0) is not None:
        failures.append("degenerate FOV must return None")

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    spec_src = inspect.getsource(KrakenLayoutEditor.receiving_cone_overlay_spec)
    for needle in (
        "_camera_fov_object_half_extents",
        "_object_surface_plane_z",
        "_pupil_model_inputs",
        "PosPupInp",
        "RadPupInp",
        "build_receiving_cone_overlay",
    ):
        if needle not in spec_src:
            failures.append(f"receiving_cone_overlay_spec lost its {needle} anchor")

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService

    add_src = inspect.getsource(Kraken3DInspector._add_receiving_cone_overlays)
    if "receiving_cone_overlay_spec" not in add_src or "_add_mesh_actor" not in add_src:
        failures.append("_add_receiving_cone_overlays does not draw the editor spec")
    refresh_src = inspect.getsource(Open3DSceneRefreshService)
    if "show_receiving_cone_var" not in refresh_src or "_add_receiving_cone_overlays" not in refresh_src:
        failures.append("the refresh path does not gate the cone on its toggle")
    import KrakenOS.UI.panels.open3d_top_controls as top_controls

    if "show_receiving_cone_var" not in inspect.getsource(top_controls):
        failures.append("the Overlays menu has no Accept-cone toggle")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Receiving-cone overlay validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Receiving-cone overlay validation passed: the acceptance volume lofts the "
        "imaged FOV to the entrance pupil as a faint translucent skin, anchored on "
        "the shared first-order machinery and gated on its Overlays toggle."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
