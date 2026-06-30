"""Guard: the promoted right-angle MIRROR folds the lens chain AND the STEP overlays.

Flag ``20260630_133944_068`` asked, of the folded AZURE ELS-85 layout
(``machine_vision_AZ85_RA_Mirror.py``): *"Why the camera and lens are still in old
location? They should have automatically relocate to the reflected path."*

The mirror is a PROMOTED STEP optical solid: its ``S001/F002`` face carries
``function = "Mirror"`` so the traced rays physically reflect (+Z -> +X), but a
right-angle mirror CUBE reads all of its outer faces as inferred ``Transmit/Port``
outputs. ``select_optical_solid_output_face`` therefore picks the +Z face as a
"straight-through" exit (the bugs/0084 axial preference), and the non-folding skip
guard in ``build_optical_solid_output_port_pose_overrides`` left the downstream lens
rows -- and the lens/camera STEP overlays (seated on the straight +Z axis by
``_cad_mesh_aligned_to_optical_axis``) -- on the old optical axis while the beam
folded away.

The fix has two halves and this guard checks both, display-free:

1. ROWS -- a solid whose primary interaction face is a full Mirror has no
   straight-through transmit, so the follower builder now reflects the downstream
   chain onto the +X branch instead of skipping. The image/sensor row must land on
   the reflected branch (large +X, mirror height z, optical axis +X).
2. OVERLAYS -- ``_optical_axis_fold_world_transform_for_row`` carries the
   straight-axis lens-barrel and camera meshes onto the anchor row's folded pose, so
   the lens STEP front datum and the camera STEP both sit on the +X branch.

Regression direction: a BEAM-SPLITTER cube keeps its real straight-through (its
interaction face is a Beam Splitter, not a Mirror), so the same RA-mirror faces with
the function flipped to "Beam Splitter" must NOT be treated as a fold.

Standalone check (mirrors the other AZ85 guards), not a penta phase.
"""

from __future__ import annotations

import copy
from pathlib import Path

import numpy as np

import KrakenOS.UI.nonseq_output_ports as nop
from KrakenOS.UI.layout_library import load_python_data
from KrakenOS.UI.services.layout_polyline_display import LayoutPolylineDisplayMixin


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYOUT_PATH = PROJECT_ROOT / "KrakenOS" / "common_optical_layouts" / "machine_vision_AZ85_RA_Mirror.py"

MIRROR_HEIGHT_Z = 71.8971  # world z of the reflected branch (mirror centre)


class _FoldStub:
    """Minimal carrier for the display mixin's geometry-only fold helpers."""

    _row_z_positions = LayoutPolylineDisplayMixin._row_z_positions
    _lens_front_datum_z = LayoutPolylineDisplayMixin._lens_front_datum_z
    _lens_front_datum_row_index = LayoutPolylineDisplayMixin._lens_front_datum_row_index
    _image_plane_row_index = LayoutPolylineDisplayMixin._image_plane_row_index
    _optical_axis_fold_world_transform_for_row = (
        LayoutPolylineDisplayMixin._optical_axis_fold_world_transform_for_row
    )

    def __init__(self, rows):
        self.rows = rows


def _apply(transform, point):
    vec = np.asarray([point[0], point[1], point[2], 1.0], dtype=float)
    return (np.asarray(transform, dtype=float).reshape(4, 4) @ vec)[:3]


def run_checks():
    """Return (passed, failures) without printing -- usable as a phase body."""
    info = load_python_data(LAYOUT_PATH)
    raw_rows = info["surfaces"]

    # --- 1. ROW FOLD ---------------------------------------------------------
    overrides = nop.build_optical_solid_output_port_pose_overrides(raw_rows)
    image_index = None
    for index, row in enumerate(raw_rows):
        if str(row.get("surface", "")) == "Image":
            image_index = index
    image_pose = overrides.get(image_index) if image_index is not None else None
    image_center = (
        np.asarray(image_pose["center"], dtype=float)
        if isinstance(image_pose, dict)
        else None
    )
    image_axis = (
        np.asarray(image_pose["normal"], dtype=float)
        if isinstance(image_pose, dict)
        else None
    )

    # --- 2. MIRROR GATE (and beam-splitter regression direction) -------------
    prepared = [nop._row_like(row) for row in raw_rows]
    z_positions = nop.row_z_positions(prepared)
    mirror_world_faces = nop.optical_solid_face_world_records(
        prepared[1], float(z_positions[1]), assigned_only=True
    )
    mirror_is_fold = nop._solid_has_full_mirror_interaction_face(mirror_world_faces)

    splitter_world_faces = copy.deepcopy(mirror_world_faces)
    for face in splitter_world_faces:
        if str(face.get("function", "")) == "Mirror":
            face["function"] = "Beam Splitter"
            face["role"] = "Beam Splitter"
    splitter_is_fold = nop._solid_has_full_mirror_interaction_face(splitter_world_faces)

    # --- 3. OVERLAY FOLD TRANSFORMS -----------------------------------------
    stub = _FoldStub(prepared)
    lens_index = stub._lens_front_datum_row_index()
    cam_index = stub._image_plane_row_index()
    lens_fold = stub._optical_axis_fold_world_transform_for_row(lens_index)
    cam_fold = stub._optical_axis_fold_world_transform_for_row(cam_index)

    lens_front_world = None
    lens_axis = None
    if lens_fold is not None and lens_index is not None:
        lens_front_world = _apply(lens_fold, (0.0, 0.0, float(z_positions[lens_index])))
        lens_axis = np.asarray(lens_fold, dtype=float).reshape(4, 4)[:3, 2]
    cam_sensor_world = None
    cam_axis = None
    if cam_fold is not None and cam_index is not None:
        cam_sensor_world = _apply(cam_fold, (0.0, 0.0, float(z_positions[cam_index])))
        cam_axis = np.asarray(cam_fold, dtype=float).reshape(4, 4)[:3, 2]

    def _on_reflected_branch(point) -> bool:
        # On the straight +Z axis every downstream station has x == 0 and a large
        # +Z; after the fold it sits at the mirror height with a clearly positive
        # +X (the lens front datum is ~82 mm along the branch, the sensor ~288 mm).
        return (
            point is not None
            and float(point[0]) > 50.0
            and abs(float(point[2]) - MIRROR_HEIGHT_Z) < 2.0
        )

    def _is_plus_x(axis) -> bool:
        return axis is not None and abs(float(axis[0])) > 0.99

    checks = [
        ("layout file exists", LAYOUT_PATH.exists()),
        ("mirror solid is recognised as a full specular fold", mirror_is_fold),
        (
            "a beam-splitter face is NOT treated as a mirror fold",
            not splitter_is_fold,
        ),
        ("downstream rows receive fold overrides", len(overrides) >= 6),
        ("image/sensor row folds onto the +X reflected branch", _on_reflected_branch(image_center)),
        ("image/sensor optical axis is +X after the fold", _is_plus_x(image_axis)),
        (
            "image fold matches the overlay anchor transform",
            image_center is not None
            and cam_sensor_world is not None
            and float(np.linalg.norm(image_center - cam_sensor_world)) < 1e-6,
        ),
        ("lens STEP front datum folds onto the +X branch", _on_reflected_branch(lens_front_world)),
        ("lens STEP optical axis is +X after the fold", _is_plus_x(lens_axis)),
        ("camera STEP sensor end folds onto the +X branch", _on_reflected_branch(cam_sensor_world)),
        ("camera STEP optical axis is +X after the fold", _is_plus_x(cam_axis)),
    ]
    failures = [name for name, ok in checks if not ok]
    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("RA-mirror fold-follows-reflection validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "RA-mirror fold-follows-reflection validation passed: the full-mirror solid "
        "folds the lens chain and the lens/camera STEP overlays onto the +X reflected "
        "branch; a beam-splitter face keeps its straight-through."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
