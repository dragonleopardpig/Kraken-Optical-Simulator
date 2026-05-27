"""Validate the CAD/STEP service boundary is ready for CadQuery study."""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _source(relative: str) -> str:
    return (PROJECT_ROOT / relative).read_text(encoding="utf-8")


def main() -> int:
    failures: list[str] = []

    required_modules = (
        "KrakenOS/UI/services/cad_cache_paths.py",
        "KrakenOS/UI/services/cad_scene_cache.py",
        "KrakenOS/UI/services/step_overlay_labels.py",
        "KrakenOS/UI/services/layout_literals.py",
        "KrakenOS/UI/services/step_face_direction.py",
        "KrakenOS/UI/services/cad_step_export.py",
        "KrakenOS/UI/diagnose_open3d_hover_latency.py",
    )
    for relative in required_modules:
        if not (PROJECT_ROOT / relative).is_file():
            failures.append(f"Missing CAD/STEP service boundary module: {relative}")

    bridge_free_modules = (
        "KrakenOS/UI/services/layout_file_writer.py",
        "KrakenOS/UI/services/step_overlay_promotion.py",
        "KrakenOS/UI/services/scene_placement_commands.py",
    )
    for relative in bridge_free_modules:
        source = _source(relative)
        for token in ("def _layout_module(", "from KrakenOS.UI import layout_editor", "_layout_module()"):
            if token in source:
                failures.append(f"{relative} still bridges through layout_editor via {token!r}")

    label_definition = 'STEP_OVERLAY_LABELS = ("lens", "optical", "led", "camera")'
    duplicate_label_modules = (
        "KrakenOS/UI/layout_editor.py",
        "KrakenOS/UI/open3d_inspector.py",
        "KrakenOS/UI/services/three_d_scene_tools.py",
    )
    for relative in duplicate_label_modules:
        if label_definition in _source(relative):
            failures.append(f"{relative} must import STEP overlay labels from services/step_overlay_labels.py")

    if "CAD_CACHE_DIR = Path.home()" in _source("KrakenOS/UI/layout_editor.py"):
        failures.append("layout_editor.py must import CAD_CACHE_DIR from services/cad_cache_paths.py")

    scene_cache_source = _source("KrakenOS/UI/services/cad_scene_cache.py")
    for token in ("CadSceneCache", "CadDocumentCache", "CadPickCache", "face_outline"):
        if token not in scene_cache_source:
            failures.append(f"CAD scene-cache service is missing {token}.")
    hover_diagnostic_source = _source("KrakenOS/UI/diagnose_open3d_hover_latency.py")
    for token in ("PASSIVE_HOVER_TARGET_P95_MS", "CadSceneCache", "passive_hover_uses_rotation_handle_pick_list"):
        if token not in hover_diagnostic_source:
            failures.append(f"Open 3D hover-latency diagnostic is missing {token}.")

    branch_readme = _source("BRANCH_README.md")
    if "CadQuery/OCP topology study" not in branch_readme:
        failures.append("BRANCH_README.md must keep the CadQuery/OCP topology study milestone visible.")
    if "Responsive STEP Handling Architecture" not in branch_readme:
        failures.append("BRANCH_README.md must link the STEP responsiveness architecture note.")

    manual_index = _source("docs/source/manual/index.rst")
    if "cad_step_responsiveness" not in manual_index:
        failures.append("Sphinx manual index must include cad_step_responsiveness.")

    responsiveness_doc = PROJECT_ROOT / "docs/source/manual/cad_step_responsiveness.rst"
    if not responsiveness_doc.is_file():
        failures.append("Missing Sphinx architecture note: docs/source/manual/cad_step_responsiveness.rst")
    else:
        doc_source = responsiveness_doc.read_text(encoding="utf-8")
        required_phrases = (
            "persistent CAD scene cache",
            "CadDocumentCache",
            "CadPickCache",
            "BRepMesh_IncrementalMesh",
            "make it a required runtime dependency",
            "rotation-handle actor pick list",
        )
        for phrase in required_phrases:
            if phrase not in doc_source:
                failures.append(f"STEP responsiveness architecture note is missing {phrase!r}")

    if failures:
        print("CadQuery readiness validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("CadQuery readiness validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
