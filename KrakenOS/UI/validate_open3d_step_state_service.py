"""Validate Open 3D STEP state service target resolution."""

from __future__ import annotations

from dataclasses import dataclass, field

from KrakenOS.UI.services.open3d_step_state import Open3DStepStateService


@dataclass
class _Row:
    advanced: dict[str, object] = field(default_factory=dict)


class _Editor:
    def __init__(self) -> None:
        self.rows = [
            _Row(),
            _Row({"StepOverlayPromotion": {"step_label": "optical"}}),
            _Row({"Other": True}),
            _Row({"StepOverlayPromotion": {"step_label": "lens"}}),
        ]
        self.step_paths = {"optical": "/tmp/optical.step", "lens": None, "camera": None, "led": None}

    def _step_path_for_label(self, label: str):
        return self.step_paths.get(str(label or "").strip().lower())

    @staticmethod
    def _is_open3d_promoted_optical_solid_row(row: _Row) -> bool:
        return isinstance(dict(row.advanced or {}).get("StepOverlayPromotion"), dict)


def main() -> int:
    editor = _Editor()
    service = Open3DStepStateService(editor, valid_labels=("lens", "optical", "camera", "led"))
    checks = [
        (
            "import overlay wins over row candidates",
            service.resolve_delete_selection(
                import_label_candidates=("lens", "optical"),
                row_index_candidates=(1, 2, 3),
            ).import_label
            == "optical",
        ),
        (
            "promoted rows resolve when no imported overlay is selected",
            service.resolve_delete_selection(
                import_label_candidates=("lens", "camera"),
                row_index_candidates=(2, 3, 1, 1, -1, "bad"),
            ).row_indices
            == (1, 3),
        ),
        (
            "no target stays explicit",
            not service.resolve_delete_selection(
                import_label_candidates=("camera", "led"),
                row_index_candidates=(0, 2, 999),
            ).has_target,
        ),
        (
            "feature selections normalize picked point, surface center, and normal",
            (
                lambda selection: (
                    selection is not None
                    and selection.label == "optical"
                    and selection.pick_point_world == (1.0, 2.0, 3.0)
                    and selection.surface_center_world == (4.0, 5.0, 6.0)
                    and selection.normal_world == (0.0, 0.0, 1.0)
                )
            )(
                service.step_feature_selection(
                    "optical",
                    ((1.0, 2.0, 3.0), object(), (0.0, 0.0, 2.0)),
                    surface_center_world=(4.0, 5.0, 6.0),
                )
            ),
        ),
        (
            "feature action requires matching active imported overlay",
            (
                lambda selection: (
                    service.selected_feature_action(
                        selection,
                        label_candidates=("lens", "camera"),
                        require_surface_center=True,
                        require_normal=True,
                    )
                    is None
                    and service.selected_feature_action(
                        selection,
                        label_candidates=("optical",),
                        require_surface_center=True,
                        require_normal=True,
                    )
                    == selection
                )
            )(
                service.step_feature_selection(
                    "optical",
                    ((1.0, 2.0, 3.0), object(), (0.0, 0.0, 2.0)),
                    surface_center_world=(4.0, 5.0, 6.0),
                )
            ),
        ),
        (
            "invalid feature selections are rejected",
            service.step_feature_selection("optical", ((1.0, 2.0, 3.0), object(), (0.0, 0.0, 0.0))) is None
            and service.step_feature_selection("camera", ((1.0, 2.0, 3.0), object(), (0.0, 0.0, 1.0))) is None,
        ),
    ]
    failed = [name for name, ok in checks if not ok]
    if failed:
        print("Open 3D STEP state service validation failed:")
        for name in failed:
            print(f"- {name}")
        return 1
    print("Open 3D STEP state service validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
