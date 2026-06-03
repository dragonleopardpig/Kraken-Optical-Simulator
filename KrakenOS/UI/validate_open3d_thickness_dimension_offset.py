"""Display-free contract for bugs/0007: the Open 3D Thickness dimension must be
offset *into the screen plane*, so a double-ended arrow reads to the side of the
optical axis instead of vanishing into depth.

The dimension offset comes from
``Open3DThicknessDimensionService.offset_direction``. Its old purely geometric
perpendicular sent an optical-axis (world-Z) segment along world -X -- which is
exactly the depth axis of the default side view (camera looking along +X) -- so
the arrow projected onto the axis and the label landed unreadably on the glass.

This pins the camera-aware seam: given a view normal, the offset must be
perpendicular to *both* the view direction (i.e. lie in the screen plane, so it
is visible) and the measured segment (a proper dimension offset), at a range of
camera orientations. It also source-couples ``add_overlays`` so a future edit
can't silently drop the camera vectors and revert to the invisible offset. The
rendered-pixel guarantee lives in
``validate_open3d_thickness_dimension_offset_snapshot`` and Phase 14 of the
comprehensive validator.

Run from the repository root:

    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_thickness_dimension_offset
"""

from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.services.open3d_thickness_dimensions import (
    Open3DThicknessDimensionService,
)


def _unit(vec) -> np.ndarray:
    vec = np.asarray(vec, dtype=float).reshape(3)
    norm = float(np.linalg.norm(vec))
    return vec / norm if norm > 1e-12 else vec


# (label, view_normal, screen_up, segment) -- realistic camera/axis combos.
_CAMERA_CASES = [
    # Default Open 3D side view: camera looks along +X, up is +Y, optical axis +Z.
    ("side view, optical axis +Z", (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
    # Same view, axis reversed (surface order flipped) -- offset must stay on one side.
    ("side view, optical axis -Z", (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, -1.0)),
    # Top view: camera looks along -Y, up is +Z, optical axis +Z.
    ("top view, optical axis +Z", (0.0, -1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 0.0, 1.0)),
    # An oblique orbit.
    ("oblique view", (0.6, 0.5, 0.62), (-0.2, 0.9, -0.1), (0.0, 0.0, 1.0)),
]


def _checks() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    offset_direction = Open3DThicknessDimensionService.offset_direction

    for label, view, up, seg in _CAMERA_CASES:
        view_u = _unit(view)
        seg_u = _unit(seg)
        side = offset_direction(np.asarray(seg, dtype=float), view_u, np.asarray(up, dtype=float))
        side = np.asarray(side, dtype=float).reshape(3)
        # In the screen plane: orthogonal to the view direction -> visibly offset.
        in_plane = abs(float(np.dot(side, view_u)))
        checks.append(
            (f"[{label}] offset lies in the screen plane (perp to view)", in_plane < 1e-6, f"|dot(view)|={in_plane:.3e}")
        )
        # A proper dimension offset is perpendicular to the measured segment.
        perp = abs(float(np.dot(side, seg_u)))
        checks.append(
            (f"[{label}] offset is perpendicular to the segment", perp < 1e-6, f"|dot(seg)|={perp:.3e}")
        )
        # Unit length (callers scale by base_offset * row_band).
        mag = float(np.linalg.norm(side))
        checks.append(
            (f"[{label}] offset is a unit vector", abs(mag - 1.0) < 1e-6, f"|side|={mag:.6f}")
        )

    # The default side view must offset straight down on screen (-Y here), the
    # exact regression: the old code returned world -X (depth) and vanished.
    side_default = np.asarray(
        offset_direction(np.asarray((0.0, 0.0, 1.0)), np.asarray((1.0, 0.0, 0.0)), np.asarray((0.0, 1.0, 0.0))),
        dtype=float,
    ).reshape(3)
    checks.append(
        (
            "default side view offsets along screen -Y (not depth -X)",
            bool(np.allclose(side_default, (0.0, -1.0, 0.0), atol=1e-6)),
            f"side={tuple(round(float(v), 4) for v in side_default)}",
        )
    )
    checks.append(
        (
            "default side view offset has no depth (X) component",
            abs(float(side_default[0])) < 1e-6,
            f"x-component={float(side_default[0]):.3e}",
        )
    )

    # Looking straight down the optical axis: the segment projects to a point, so
    # the offset can't be perpendicular to it -- but it must still lie in screen.
    degenerate = np.asarray(
        offset_direction(np.asarray((0.0, 0.0, 1.0)), np.asarray((0.0, 0.0, 1.0)), np.asarray((0.0, 1.0, 0.0))),
        dtype=float,
    ).reshape(3)
    checks.append(
        (
            "axis-aligned view falls back to an in-screen offset (no NaN/zero)",
            abs(float(np.dot(degenerate, (0.0, 0.0, 1.0)))) < 1e-6
            and abs(float(np.linalg.norm(degenerate)) - 1.0) < 1e-6,
            f"side={tuple(round(float(v), 4) for v in degenerate)}",
        )
    )

    # Backward compatibility: with no camera the geometric perpendicular is
    # unchanged, so the non-camera caller (the STEP translate-gap overlay) keeps
    # its existing behaviour.
    legacy = np.asarray(offset_direction(np.asarray((0.0, 0.0, 1.0))), dtype=float).reshape(3)
    checks.append(
        (
            "no-camera call preserves the legacy geometric perpendicular",
            bool(np.allclose(legacy, (-1.0, 0.0, 0.0), atol=1e-6)),
            f"side={tuple(round(float(v), 4) for v in legacy)}",
        )
    )

    # ---- Source coupling: add_overlays must feed the camera vectors through. ----
    overlay_src = inspect.getsource(Open3DThicknessDimensionService.add_overlays)
    checks.append(
        (
            "add_overlays fetches the camera view normal",
            "_camera_view_normal" in overlay_src,
            "missing _camera_view_normal in add_overlays",
        )
    )
    checks.append(
        (
            "add_overlays fetches the camera screen axes",
            "_camera_screen_world_axes" in overlay_src,
            "missing _camera_screen_world_axes in add_overlays",
        )
    )
    checks.append(
        (
            "add_overlays passes camera vectors into offset_direction",
            "offset_direction(segment, view_normal=view_normal, screen_up=screen_up)" in overlay_src,
            "offset_direction call does not forward view_normal/screen_up",
        )
    )

    return checks


def main() -> int:
    checks = _checks()
    failed = [(name, detail) for name, ok, detail in checks if not ok]
    if failed:
        print("Open 3D thickness-dimension offset validation failed:")
        for name, detail in failed:
            print(f"- {name}: {detail}")
        return 1
    print(f"Open 3D thickness-dimension offset validation passed ({len(checks)} checks).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
