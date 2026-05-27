"""Validate saved STEP optical solids reappear in the Open 3D browser."""

from __future__ import annotations

from dataclasses import dataclass, field

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.panels.open3d_step_admin import Open3DStepAdminPanel


@dataclass
class _Row:
    name: str = "Saved STEP"
    advanced: dict[str, object] = field(default_factory=dict)


class _Editor:
    def __init__(self) -> None:
        self.rows = [
            _Row(
                "Saved penta prism",
                {
                    "Solid_3d_stl": "/tmp/promoted_penta.stl",
                    "OpticalSolidSourcePath": "/tmp/penta.step",
                    "OpticalSolidSourceFormat": "STEP",
                },
            ),
            _Row(
                "Saved lens STEP",
                {
                    "Solid_3d_stl": "/tmp/promoted_lens.stl",
                    "StepOverlayPromotion": {"step_label": "lens", "source_step_path": "/tmp/lens.step"},
                    "OpticalSolidSourcePath": "/tmp/lens.step",
                    "OpticalSolidSourceFormat": "STEP",
                },
            ),
            _Row(
                "Plain STL",
                {
                    "Solid_3d_stl": "/tmp/plain.stl",
                    "OpticalSolidSourcePath": "/tmp/plain.stl",
                    "OpticalSolidSourceFormat": "STL",
                },
            ),
        ]

    @staticmethod
    def _is_open3d_promoted_optical_solid_row(row: _Row) -> bool:
        return KrakenLayoutEditor._is_open3d_promoted_optical_solid_row(row)

    @staticmethod
    def _open3d_step_label_for_optical_solid_row(row: _Row) -> str:
        return KrakenLayoutEditor._open3d_step_label_for_optical_solid_row(row)

    @staticmethod
    def _step_path_for_label(_label: str):
        return None


class _Inspector:
    def __init__(self) -> None:
        self.editor = _Editor()
        self._row_actor_map = {0: ["actor0"], 1: ["actor1"], 2: ["actor2"]}


def main() -> int:
    saved_item = {
        "surface": "Standard",
        "name": "Reloaded prism",
        "advanced": {
            "Solid_3d_stl": "/tmp/reloaded_mesh.stl",
            "OpticalSolidSourcePath": "/tmp/reloaded_prism.step",
            "OpticalSolidSourceFormat": "STEP",
            "StepOverlayPromotion": {"step_label": "optical", "source_step_path": "/tmp/reloaded_prism.step"},
        },
    }
    reloaded_row = KrakenLayoutEditor._row_from_layout_item(saved_item)
    panel = Open3DStepAdminPanel(_Inspector())
    records = panel._promoted_step_rows()
    scene_records = panel._scene_row_records()
    checks = [
        (
            "layout loader preserves STEP promotion metadata",
            isinstance(reloaded_row.advanced.get("StepOverlayPromotion"), dict),
        ),
        (
            "saved STEP rows without promotion metadata still qualify for browser",
            KrakenLayoutEditor._is_open3d_promoted_optical_solid_row(panel.editor.rows[0])
            and KrakenLayoutEditor._open3d_step_label_for_optical_solid_row(panel.editor.rows[0]) == "optical",
        ),
        (
            "promotion metadata still controls browser category",
            KrakenLayoutEditor._open3d_step_label_for_optical_solid_row(panel.editor.rows[1]) == "lens",
        ),
        (
            "plain STL rows are not listed as STEP browser elements",
            not KrakenLayoutEditor._is_open3d_promoted_optical_solid_row(panel.editor.rows[2]),
        ),
        (
            "Open 3D browser lists both saved STEP rows",
            records == [(0, "optical", "Saved penta prism"), (1, "lens", "Saved lens STEP")],
        ),
        (
            "Open 3D browser also lists visible non-STEP editable-table rows",
            scene_records == [(2, "layout", "Plain STL")],
        ),
    ]
    failed = [name for name, ok in checks if not ok]
    if failed:
        print("Open 3D saved STEP browser validation failed:")
        for name in failed:
            print(f"- {name}")
        return 1
    print("Open 3D saved STEP browser validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
