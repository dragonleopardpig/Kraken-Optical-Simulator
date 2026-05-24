"""Validate Open 3D STEP face-direction alignment controls."""

from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor
from KrakenOS.UI.panels.open3d_step_admin import Open3DStepAdminPanel


def _close(a, b) -> bool:
    return bool(np.allclose(np.asarray(a, dtype=float), np.asarray(b, dtype=float)))


def main() -> int:
    admin_source = inspect.getsource(Open3DStepAdminPanel)
    inspector_source = inspect.getsource(Kraken3DInspector.orient_selected_step_face_to_direction)
    editor_source = inspect.getsource(KrakenLayoutEditor.orient_step_feature_normal_to_direction)
    direction_source = inspect.getsource(KrakenLayoutEditor._step_orientation_direction_vector)
    checks = [
        (
            "right-panel exposes all STEP face-direction labels",
            '"Face direction"' in admin_source
            and all(f'"{label}"' in admin_source for label in ("Left", "Right", "Up", "Down", "Front", "Back"))
            and "orient_selected_step_face_to_direction" in admin_source,
        ),
        (
            "inspector uses selected STEP face center and normal",
            "require_surface_center=True" in inspector_source
            and "require_normal=True" in inspector_source
            and "orient_step_feature_normal_to_direction" in inspector_source
            and "step_feature_selection(" in inspector_source,
        ),
        (
            "editor live-updates imported STEP pose while anchoring selected face",
            "_rotation_matrix_between_vectors(feature_normal, target_normal)" in editor_source
            and "placement_delta = feature_center[:3] - np.asarray(rotated_feature_center" in editor_source
            and "_set_step_rotation_deg_tuple(label, next_angles)" in editor_source
            and "_set_step_placement_offset_xyz(label, next_offset)" in editor_source
            and "_refresh_open_3d_views(step_label=label)" in editor_source,
        ),
        (
            "face-direction vectors match Open 3D YZ convention",
            _close(KrakenLayoutEditor._step_orientation_direction_vector("Left"), (0.0, 0.0, -1.0))
            and _close(KrakenLayoutEditor._step_orientation_direction_vector("Right"), (0.0, 0.0, 1.0))
            and _close(KrakenLayoutEditor._step_orientation_direction_vector("Up"), (0.0, 1.0, 0.0))
            and _close(KrakenLayoutEditor._step_orientation_direction_vector("Down"), (0.0, -1.0, 0.0))
            and _close(KrakenLayoutEditor._step_orientation_direction_vector("Front"), (1.0, 0.0, 0.0))
            and _close(KrakenLayoutEditor._step_orientation_direction_vector("Back"), (-1.0, 0.0, 0.0))
            and KrakenLayoutEditor._step_orientation_direction_vector("bad") is None,
        ),
        (
            "direction helper keeps explicit labels documented in source",
            all(label.lower() in direction_source for label in ("Left", "Right", "Up", "Down", "Front", "Back")),
        ),
    ]
    failed = [name for name, ok in checks if not ok]
    if failed:
        print("Open 3D STEP face-direction validation failed:")
        for name in failed:
            print(f"- {name}")
        return 1
    print("Open 3D STEP face-direction validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
