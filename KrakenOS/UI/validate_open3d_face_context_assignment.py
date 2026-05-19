"""Validate Open 3D direct CAD/STL face-function assignment."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import numpy as np

from KrakenOS.UI import layout_editor as le
from KrakenOS.UI.layout_editor import (
    KrakenLayoutEditor,
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    OPTICAL_SOLID_FACE_PORT_DEFAULT,
    OPTICAL_SOLID_FACE_PORT_INTERACTION,
    SurfaceRow,
    optical_solid_face_world_records,
)
from KrakenOS.UI.optical_solid_metadata import normalize_optical_solid_face_metadata


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRISM_42779_STEP = PROJECT_ROOT / "attachment" / "prisms" / "42779" / "step_42779.step"
VALIDATION_CACHE_DIR = Path("/tmp/kraken-open3d-face-context-cache")


def _first_world_face(app: KrakenLayoutEditor, row_index: int) -> dict[str, object]:
    row = app.rows[int(row_index)]
    _row, _path, metadata = app._optical_solid_face_metadata_for_row(int(row_index))
    temp_row = SurfaceRow(**asdict(row))
    temp_row.advanced = dict(temp_row.advanced or {})
    temp_row.advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata
    faces = optical_solid_face_world_records(temp_row, app._stl_row_z_station(int(row_index)), assigned_only=False)
    if not faces:
        raise AssertionError("Expected promoted optical solid to expose assignable faces.")
    return dict(faces[0])


def main() -> int:
    if not PRISM_42779_STEP.exists():
        raise RuntimeError(f"Expected STEP fixture: {PRISM_42779_STEP}")

    le.CAD_CACHE_DIR = VALIDATION_CACHE_DIR / "cad"
    le.CAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    app = KrakenLayoutEditor(headless=True)
    try:
        app.imported_optical_step_path = PRISM_42779_STEP
        app.optical_step_rotation_x_deg = 90.0
        app.optical_step_rotation_z_deg = 90.0
        app.select_step_component("optical")

        promoted = app.promote_imported_step_to_optical_solid_row(
            "optical",
            insert_at=1,
            open_face_editor=False,
            clear_overlay=True,
        )
        if promoted is None:
            raise AssertionError("STEP promotion returned no result.")
        row_index = int(promoted["row_index"])
        if app.imported_optical_step_path is not None:
            raise AssertionError("Promotion with clear_overlay=True left the display-only optical STEP overlay active.")

        picked = _first_world_face(app, row_index)
        point = np.asarray(picked.get("centroid_world"), dtype=float)
        normal = np.asarray(picked.get("normal_world"), dtype=float)
        assigned = app.assign_optical_solid_face_function_at_world_point(
            row_index,
            point,
            "Full Reflecting",
            normal_world=normal,
        )
        if assigned.get("function") != "Mirror" or assigned.get("port_role") != OPTICAL_SOLID_FACE_PORT_INTERACTION:
            raise AssertionError(f"Reflecting context assignment did not set mirror interaction metadata: {assigned!r}")

        reassigned = app.assign_optical_solid_face_function_at_world_point(
            row_index,
            point,
            "Uncoated",
            normal_world=normal,
        )
        if reassigned.get("function") != OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT:
            raise AssertionError(f"Uncoated context assignment did not map to transmit physics: {reassigned!r}")
        if reassigned.get("port_role") != OPTICAL_SOLID_FACE_PORT_DEFAULT:
            raise AssertionError(f"Uncoated direct assignment should not require an Input/Output/side port: {reassigned!r}")

        metadata = normalize_optical_solid_face_metadata(
            app.rows[row_index].advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {})
        )
        saved = [
            face
            for face in list(metadata.get("faces", []) or [])
            if str(face.get("face_id", "") or "") == str(reassigned.get("face_id", "") or "")
        ]
        if not saved or str(saved[0].get("side_2d")) != "Auto":
            raise AssertionError("Direct Open 3D physics assignment should not require Left/Right/Up/Down side labels.")
    finally:
        app.destroy()

    print("Open 3D face context assignment validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
