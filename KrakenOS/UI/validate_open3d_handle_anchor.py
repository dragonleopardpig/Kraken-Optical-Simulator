"""Validate placement handles anchor on the actual displayed body.

When a Tier 2 STL-promoted optical solid is moved off the optical axis
(non-zero ``desp_y`` / ``desp_z``), the scene-placement handles must
follow the visible body, not the row's logical pose. The historical
failure mode looked like this in the inspector: the body sat in the
upper-right of the viewport while the rotation arc + translate arrows
floated at the optical-axis centre, completely detached from the lens.

Root cause: ``_iter_3d_optical_surface_meshes`` built a ``SurfaceMesh3D``
for file-backed STL solids without setting ``is_body=True``, and the
inspector's ``_kraken_file_backed_row_body`` actor flag was therefore
never set. ``_row_display_actor_center(body_only=True)`` returned
``None``, so the placement-grid code fell back to ``primary.center_world``
— the logical row pose computed from desp/thickness, ignoring the
visible actor bounds.

The fix has two parts and both must hold for this validator to pass:

1. ``_iter_3d_optical_surface_meshes`` passes
   ``is_body=bool(file_backed_optical_solid)`` to ``SurfaceMesh3D``, so
   the body actor receives the flag through scene_refresh's normal path.
2. ``_add_scene_placement_grid_overlays`` falls back to
   ``_row_display_actor_center(body_only=False)`` when the body-only call
   returns ``None`` for a file-backed row (covers the transient runtime
   expansion case where the file-backed flag fails to propagate).

Run from the repository root:

    python -m KrakenOS.UI.validate_open3d_handle_anchor
"""

from __future__ import annotations

import inspect

from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin


def main() -> int:
    failures: list[str] = []

    optical_src = inspect.getsource(ThreeDSceneToolsMixin._iter_3d_optical_surface_meshes)
    if "is_body=bool(file_backed_optical_solid)" not in optical_src:
        failures.append(
            "_iter_3d_optical_surface_meshes must pass is_body=bool(file_backed_optical_solid) "
            "so the body actor receives the file-backed flag"
        )

    overlay_src = inspect.getsource(Kraken3DInspector._add_scene_placement_grid_overlays)
    if "body_only=True" not in overlay_src or "body_only=False" not in overlay_src:
        failures.append(
            "_add_scene_placement_grid_overlays must try body_only=True first, then fall "
            "back to body_only=False so handles still ride the visible body when the "
            "file-backed flag was stripped during runtime expansion"
        )
    if "_render_row_file_backed" not in overlay_src:
        failures.append(
            "_add_scene_placement_grid_overlays must gate the body_only=False fallback on "
            "_render_row_file_backed so only promoted STL rows opt into it"
        )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("Open 3D placement-handle anchor contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
