"""Validate the Open 3D CAD scene-cache contract."""

from __future__ import annotations

from pathlib import Path
import tempfile

import numpy as np

from KrakenOS.UI.services.cad_scene_cache import (
    CadDocumentCache,
    CadPickCache,
    CadSceneCache,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _sample_triangles(offset: float = 0.0) -> np.ndarray:
    return np.asarray(
        [
            [[offset, 0.0, 0.0], [offset + 1.0, 0.0, 0.0], [offset, 1.0, 0.0]],
            [[offset + 1.0, 0.0, 0.0], [offset + 1.0, 1.0, 0.0], [offset, 1.0, 0.0]],
        ],
        dtype=float,
    )


def _validate_document_and_pick_caches() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / "vendor.step.stl"
        source_path.write_text("a", encoding="utf-8")
        calls = {"reader": 0, "outline": 0}

        def reader(path: Path) -> tuple[str, np.ndarray]:
            calls["reader"] += 1
            return "ascii", _sample_triangles(float(calls["reader"]))

        def outline_builder(triangles: np.ndarray) -> object:
            calls["outline"] += 1
            return {
                "outline_call": calls["outline"],
                "point_count": int(np.asarray(triangles, dtype=float).reshape((-1, 3)).shape[0]),
            }

        cache = CadSceneCache(max_documents=2, max_face_entries=8, max_outline_entries=8)
        first = cache.triangle_array(source_path, reader)
        second = cache.triangle_array(source_path, reader)
        if calls["reader"] != 1:
            failures.append("CadSceneCache reread unchanged source triangles.")
        if first is not second:
            failures.append("CadSceneCache did not return the cached CadTriangleArray.")
        if not first.valid or first.all_points is None or first.all_points.shape != (6, 3):
            failures.append("CadTriangleArray validity/all_points contract changed.")

        face = {"face_id": "F001", "triangle_indices": [0, 99, -1, "bad"]}
        if CadPickCache.face_triangle_indices(face) != (0, 99):
            failures.append("CadPickCache face triangle normalization changed.")
        face_triangles = cache.face_triangles(source_path, face, reader)
        if face_triangles.shape != (1, 3, 3):
            failures.append("CadPickCache did not clip face triangles to available source cells.")
        outline_a = cache.face_outline(source_path, face, reader, outline_builder)
        outline_b = cache.face_outline(source_path, face, reader, outline_builder)
        if calls["outline"] != 1 or outline_a is not outline_b:
            failures.append("CadPickCache did not reuse cached face outline artifacts.")

        source_path.write_text("changed-size", encoding="utf-8")
        changed = cache.triangle_array(source_path, reader)
        if calls["reader"] != 2 or changed is first:
            failures.append("CadDocumentCache did not invalidate on source size/timestamp change.")

        cache.clear_path(source_path)
        cache.triangle_array(source_path, reader)
        if calls["reader"] != 3:
            failures.append("CadSceneCache.clear_path did not invalidate the document cache.")

        other_path = Path(tmpdir) / "other.stl"
        other_path.write_text("b", encoding="utf-8")
        document_cache = CadDocumentCache(max_entries=1)
        document_cache.triangle_array(source_path, reader)
        document_cache.triangle_array(other_path, reader)
        document_cache.triangle_array(source_path, reader)
        if calls["reader"] < 6:
            failures.append("CadDocumentCache LRU budget did not evict old document entries.")
    return failures


def _validate_open3d_wiring() -> list[str]:
    failures: list[str] = []
    inspector_source = (PROJECT_ROOT / "KrakenOS/UI/open3d_inspector.py").read_text(encoding="utf-8")
    layout_source = (PROJECT_ROOT / "KrakenOS/UI/layout_editor.py").read_text(encoding="utf-8")
    refresh_source = (PROJECT_ROOT / "KrakenOS/UI/services/open3d_scene_refresh.py").read_text(encoding="utf-8")
    interaction_source = (PROJECT_ROOT / "KrakenOS/UI/services/open3d_interaction.py").read_text(encoding="utf-8")
    required_tokens = (
        "from KrakenOS.UI.services.cad_scene_cache import CadSceneCache",
        "self._cad_scene_cache = CadSceneCache()",
        "self._cad_scene_cache.triangle_array",
        "self._cad_scene_cache.face_triangles",
        "self._cad_scene_cache.face_outline",
    )
    for token in required_tokens:
        if token not in inspector_source:
            failures.append(f"Open 3D inspector is missing CAD scene-cache wiring: {token}")
    if "self._cad_scene_cache.clear()" not in inspector_source:
        failures.append("Open 3D face-metadata reset must clear CAD scene-cache artifacts.")
    try:
        refresh_body = refresh_source.split("def refresh_scene", 1)[1]
    except IndexError:
        refresh_body = refresh_source
    if "self._cad_scene_cache.clear()" in refresh_body:
        failures.append("Open 3D scene refresh must preserve CAD scene-cache artifacts across full actor rebuilds.")
    if "vtkPropPicker" not in layout_source or "self._prop_picker = vtkPropPicker()" not in inspector_source:
        failures.append("Open 3D must provide a prop-level picker for lightweight passive CAD hover.")
    try:
        passive_start = interaction_source.index("if target_label is None and not axis_pick_any:")
        passive_end = interaction_source.index("if self._picker is None or self._renderer is None", passive_start)
        passive_hover_source = interaction_source[passive_start:passive_end]
    except ValueError:
        passive_hover_source = ""
    if not passive_hover_source:
        failures.append("Open 3D passive hover branch could not be located.")
    else:
        for token in ("_step_face_ray_pick_for_display_xy", "_row_face_ray_pick_for_display_xy", "_picked_feature_info_cached"):
            if token in passive_hover_source:
                failures.append(f"Open 3D passive CAD hover must not call heavy face lookup: {token}")
        for token in ("_actor_step_map.get(actor_key)", "_actor_row_map.get(actor_key)", '"step-passive"', '"row-passive"'):
            if token in passive_hover_source:
                failures.append(f"Open 3D passive CAD hover must not pick dense CAD body actors: {token}")
        if "_passive_hover_pick_rotation_handle" not in passive_hover_source:
            failures.append("Open 3D passive hover must pick only the lightweight rotation-handle actor list.")
        if "PickFromListOn" not in interaction_source or "AddPickList" not in interaction_source:
            failures.append("Open 3D passive rotation-handle hover must use a VTK pick list instead of full-scene picking.")
    try:
        right_click_start = inspector_source.index("def _right_click_pick_context")
        right_click_end = inspector_source.index("def _ray_event_mesh_face_id", right_click_start)
        right_click_source = inspector_source[right_click_start:right_click_end]
    except ValueError:
        right_click_source = ""
    if not right_click_source:
        failures.append("Open 3D right-click pick context could not be located.")
    else:
        feature_pos = right_click_source.find("_picked_feature_info_cached")
        row_pos = right_click_source.find("row_index = self._actor_row_map.get(actor_key)")
        if feature_pos >= 0 and row_pos >= 0 and feature_pos < row_pos:
            failures.append("Open 3D right-click context must resolve row/STEP actor identity before expensive feature scans.")
        if "if step_label is None and not persistent_file_backed" not in right_click_source:
            failures.append("Open 3D right-click context must skip feature scans for file-backed CAD rows and imported STEP overlays.")
    return failures


def main() -> int:
    failures = _validate_document_and_pick_caches()
    failures.extend(_validate_open3d_wiring())
    if failures:
        print("CAD scene cache validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("CAD scene cache validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
