"""Validate Open 3D STEP state service target resolution."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

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
        self._live_step_overlay_trace_plan_cache = {"stale": object()}
        self.promotions: list[dict[str, object]] = []

    def _step_path_for_label(self, label: str):
        return self.step_paths.get(str(label or "").strip().lower())

    @staticmethod
    def _is_open3d_promoted_optical_solid_row(row: _Row) -> bool:
        return isinstance(dict(row.advanced or {}).get("StepOverlayPromotion"), dict)

    def promote_imported_step_to_optical_solid_row(
        self,
        label: str,
        *,
        open_face_editor: bool,
        clear_overlay: bool,
        refresh_open_3d: bool,
    ) -> dict[str, object]:
        record = {
            "label": str(label),
            "open_face_editor": bool(open_face_editor),
            "clear_overlay": bool(clear_overlay),
            "refresh_open_3d": bool(refresh_open_3d),
        }
        self.promotions.append(record)
        return {
            "label": str(label),
            "row_index": 4,
            "mesh_path": "/tmp/promoted-optical.stl",
            "source_step_path": "/tmp/optical.step",
        }


def _promotion_rejects_unloaded(service: Open3DStepStateService) -> bool:
    try:
        service.promote_imported_overlay_to_row("camera", open_face_editor=False, action_label="Accept")
    except ValueError as exc:
        return "select or import" in str(exc)
    return False


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
        (
            "STEP carry start resolves only loaded imported overlays",
            (
                lambda loaded, unloaded: (
                    loaded.has_label
                    and loaded.label == "optical"
                    and "hold on the STEP" in loaded.status
                    and not unloaded.has_label
                    and "select or import" in unloaded.status
                )
            )(
                service.resolve_carry_start(("camera", "optical")),
                service.resolve_carry_start(("camera", "led")),
            ),
        ),
        (
            "active STEP carry label and drop status are service-owned",
            service.resolve_active_carry_label("optical") == "optical"
            and service.resolve_active_carry_label("lens") == ""
            and service.carry_drop_status("optical") == "STEP carry dropped for OPTICAL."
            and service.carry_drop_status("") == "STEP carry dropped.",
        ),
        (
            "STEP carry spacing and motion axes are service-owned",
            (
                lambda state: (
                    state is not None
                    and state["label"] == "optical"
                    and state["spacing"] == 0.5
                    and state["snap_enabled"] is False
                    and state["ray_snap_enabled"] is False
                    and np.allclose(state["right_axis"], (0.0, -1.0, 0.0))
                    and np.allclose(state["up_axis"], (0.0, 0.0, 1.0))
                    and service.carry_motion_state(
                        "lens",
                        screen_axes=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
                        spacing=0.5,
                    )
                    is None
                )
            )(
                service.carry_motion_state(
                    "optical",
                    screen_axes=((0.2, -0.9, 0.1), (0.1, 0.3, 0.95)),
                    spacing=service.carry_spacing_for_scene(scene_span=36.0, step_extent=0.0),
                )
            ),
        ),
        (
            "STEP carry drag deltas are service-owned",
            (
                lambda pixel_state, plane_state: (
                    (
                        lambda pixel_delta, plane_delta: (
                            pixel_delta is not None
                            and pixel_delta.label == "optical"
                            and pixel_delta.applied_steps == 1
                            and np.allclose(pixel_delta.delta_xyz, (0.0, -0.5, 0.0))
                            and pixel_state["applied_steps"] == 1
                            and plane_delta is not None
                            and plane_delta.label == "optical"
                            and plane_delta.applied_steps == 6
                            and np.allclose(plane_delta.delta_xyz, (1.0, 2.0, 0.0))
                            and plane_delta.force_refresh is True
                            and plane_delta.live_refresh_message == "optical STEP carry moved"
                            and plane_state["raw_drag_delta_world"] == (1.0, 2.0, 0.0)
                        )
                    )(
                        service.carry_pixel_motion_delta(
                            pixel_state,
                            dx=22,
                            dy=0,
                            pixels_per_step=22,
                        ),
                        service.carry_plane_motion_delta(
                            plane_state,
                            cursor_world=(1.0, 2.0, 0.0),
                            scene_span=50.0,
                        ),
                    )
                )
            )(
                service.carry_motion_state(
                    "optical",
                    screen_axes=((0.2, -0.9, 0.1), (0.1, 0.3, 0.95)),
                    spacing=0.5,
                ),
                {
                    "label": "optical",
                    "spacing": 0.5,
                    "start_center_world": (0.0, 0.0, 0.0),
                    "center_world": (0.0, 0.0, 0.0),
                    "drag_plane_origin": (0.0, 0.0, 0.0),
                    "drag_plane_normal": (0.0, 0.0, 1.0),
                    "drag_anchor_world": (0.0, 0.0, 0.0),
                    "applied_steps": 0,
                },
            ),
        ),
        (
            "STEP carry finish transitions are service-owned",
            (
                lambda moved, still: (
                    moved is not None
                    and moved.label == "optical"
                    and moved.applied_steps == 3
                    and moved.moved is True
                    and moved.status == "OPTICAL STEP dropped after free drag movement."
                    and moved.live_refresh_message == "OPTICAL STEP carry dropped"
                    and still is not None
                    and still.label == "optical"
                    and still.applied_steps == 0
                    and still.moved is False
                    and still.status == "OPTICAL STEP dropped: no movement."
                    and still.live_refresh_message == ""
                )
            )(
                service.carry_finish_transition({"label": "optical", "applied_steps": 3}),
                service.carry_finish_transition({"label": "optical", "applied_steps": 0}),
            ),
        ),
        (
            "STEP carry hold state preparation is service-owned",
            (
                lambda state: (
                    (
                        lambda transition, unavailable, inactive: (
                            transition.has_state
                            and transition.label == "optical"
                            and transition.state is state
                            and transition.has_grip_world
                            and transition.grip_world == (1.0, 2.0, 3.0)
                            and transition.status
                            == "OPTICAL STEP center gripped: drag freely on the 3D plane; release to drop."
                            and state["hold_carry"] is True
                            and state["last_xy"] == (5, 6)
                            and state["grip_world"] == (1.0, 2.0, 3.0)
                            and state["center_world"] == (1.0, 2.0, 3.0)
                            and state["start_center_world"] == (1.0, 2.0, 3.0)
                            and state["drag_plane_origin"] == (1.0, 2.0, 3.0)
                            and state["drag_plane_normal"] == (0.0, 0.0, 1.0)
                            and state["drag_anchor_world"] == (2.0, 2.0, 3.0)
                            and not unavailable.has_state
                            and "move the camera once" in unavailable.status
                            and not inactive.has_state
                            and inactive.status == ""
                        )
                    )(
                        service.prepare_carry_hold_state(
                            "optical",
                            state,
                            left_drag_active=True,
                            press_xy=(3, 4),
                            last_xy=(5, 6),
                            center_world=(1.0, 2.0, 3.0),
                            pick_world=(9.0, 9.0, 9.0),
                            plane_normal=(0.0, 0.0, 1.0),
                            anchor_world=(2.0, 2.0, 3.0),
                        ),
                        service.prepare_carry_hold_state(
                            "optical",
                            None,
                            left_drag_active=True,
                        ),
                        service.prepare_carry_hold_state(
                            "optical",
                            state,
                            left_drag_active=False,
                        ),
                    )
                )
            )({"label": "optical", "spacing": 0.5, "snap_enabled": False, "ray_snap_enabled": False}),
        ),
        (
            "STEP carry follow state preparation is service-owned",
            (
                lambda state: (
                    (
                        lambda transition: (
                            transition is not None
                            and transition.state is state
                            and transition.has_initial_delta
                            and np.allclose(transition.initial_delta_xyz, (1.0, 2.0, 0.0))
                            and state["attach_to_cursor_on_next_motion"] is False
                            and state["center_world"] == (2.0, 4.0, 3.0)
                            and state["start_center_world"] == (2.0, 4.0, 3.0)
                            and state["drag_plane_origin"] == (2.0, 4.0, 3.0)
                            and state["drag_plane_normal"] == (0.0, 0.0, 1.0)
                            and state["drag_anchor_world"] == (2.0, 4.0, 3.0)
                            and state["grip_world"] == (2.0, 4.0, 3.0)
                        )
                    )(
                        service.prepare_carry_follow_state(
                            state,
                            center_world=(1.0, 2.0, 3.0),
                            plane_normal=(0.0, 0.0, 1.0),
                            anchor_world=(2.0, 4.0, 3.0),
                            attach_to_cursor_on_next_motion=False,
                        )
                    )
                )
            )({"label": "optical", "spacing": 0.5}),
        ),
        (
            "STEP overlay promotion transition is service-owned",
            (
                lambda transition: (
                    transition is not None
                    and transition.label == "optical"
                    and transition.row_index == 4
                    and transition.mesh_path == "/tmp/promoted-optical.stl"
                    and editor._live_step_overlay_trace_plan_cache == {}
                    and editor.promotions[-1]
                    == {
                        "label": "optical",
                        "open_face_editor": False,
                        "clear_overlay": True,
                        "refresh_open_3d": False,
                    }
                )
            )(
                service.promote_imported_overlay_to_row(
                    "optical",
                    open_face_editor=False,
                    action_label="Accept",
                )
            ),
        ),
        (
            "STEP overlay promotion rejects unloaded labels",
            _promotion_rejects_unloaded(service),
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
