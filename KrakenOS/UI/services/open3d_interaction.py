"""Open 3D mouse interaction service."""

from __future__ import annotations

from typing import Any

import numpy as np

from KrakenOS.UI.services.open3d_interaction_event import (
    InteractionEventData,
    PickClassifier,
)
from KrakenOS.UI.services.open3d_timing import (
    open3d_trace_enabled,
    open3d_trace_event,
)


def _traced_pick(picker, x: float, y: float, z: float, renderer, *, site: str) -> None:
    """Run picker.Pick with a deep-trace span when tracing is on.

    The fast path -- tracing disabled -- is a single ``if`` and one
    method call, identical in cost to the original inline ``Pick``.
    When tracing is on, we log the cell id and actor type of whatever
    the picker hit so the post-mortem can tell whether one specific
    actor (the heavy camera body, a translucent ray, the orientation
    widget) is dominating hover cost.
    """
    if not open3d_trace_enabled():
        picker.Pick(x, y, z, renderer)
        return
    import time as _time

    start = _time.perf_counter()
    picker.Pick(x, y, z, renderer)
    duration_ms = (_time.perf_counter() - start) * 1000.0
    try:
        cell_id = int(picker.GetCellId())
    except Exception:
        cell_id = -1
    actor_name = ""
    try:
        actor = picker.GetActor()
        if actor is not None:
            actor_name = type(actor).__name__
    except Exception:
        pass
    open3d_trace_event(
        "vtk_picker_pick",
        site=str(site),
        x=int(x),
        y=int(y),
        duration_ms=round(float(duration_ms), 3),
        cell_id=int(cell_id),
        actor=actor_name,
    )


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


def _timed_open3d_interaction(method):
    def wrapper(self, *args, **kwargs):
        token = None
        fields: dict[str, object] = {"handler": method.__name__}
        try:
            if getattr(self, "_vtk_interactor", None) is not None:
                x, y = self._vtk_interactor.GetEventPosition()
                fields["x"] = int(x)
                fields["y"] = int(y)
        except Exception:
            pass
        try:
            token = self._timing_start("interaction_handler", **fields)
        except Exception:
            token = None
        try:
            return method(self, *args, **kwargs)
        finally:
            try:
                self._timing_finish(token, handler=method.__name__)
            except Exception:
                pass

    return wrapper


class Open3DInteractionService:
    """Handle Open 3D pick and hover interactions for the inspector."""

    def __init__(self, inspector: Any) -> None:
        object.__setattr__(self, "_inspector", inspector)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inspector, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_inspector":
            object.__setattr__(self, name, value)
            return
        setattr(self._inspector, name, value)

    @_timed_open3d_interaction
    def _on_left_button_press(self, obj, _event) -> None:
        le = _layout_module()
        STEP_OVERLAY_LABEL_SET = le.STEP_OVERLAY_LABEL_SET
        _short_error_message = le._short_error_message
        _optical_solid_face_function_display = le._optical_solid_face_function_display
        if self._picker is None or self._renderer is None or self._vtk_interactor is None:
            return
        if self._ctrl_left_camera_active:
            return
        try:
            if int(self._vtk_interactor.GetControlKey()):
                return
        except Exception:
            pass
        # Shift+click is intentional multi-select for STEP rotation gizmos;
        # Ctrl stays the camera modifier (handled above), so it is not
        # overloaded. A plain click collapses back to a single selection.
        try:
            shift_additive = bool(int(self._vtk_interactor.GetShiftKey()))
        except Exception:
            shift_additive = False
        x, y = self._vtk_interactor.GetEventPosition()
        pick_start = self._timing_start("left_click_vtk_pick", x=int(x), y=int(y))
        actor = None
        try:
            _traced_pick(self._picker, x, y, 0.0, self._renderer, site="left_click")
            actor = self._picker.GetActor()
            if actor is None:
                get_view_prop = getattr(self._picker, "GetViewProp", None)
                if callable(get_view_prop):
                    try:
                        actor = get_view_prop()
                    except Exception:
                        actor = None
        finally:
            self._timing_finish(pick_start, actor_found=actor is not None)
        actor_key = self._actor_key(actor)
        active_pick_mode = bool(
            self._source_target_pick_mode
            or self._center_row_to_ray_mode
            or self._placement_target_pick_mode
            or self._placement_orient_pick_mode
            or self._placement_orient_ray_mode
            or self._step_carry_snap_ray_mode
            or self._step_carry_snap_target_mode
            or self._step_normal_axis_pick_mode
            or self._step_surface_center_axis_pick_mode
            or bool(getattr(self.editor, "_cad_axis_pick_any", False))
        )
        if active_pick_mode and actor_key is not None and (
            actor_key in self._actor_step_rotate_map
            or actor_key in self._actor_step_rotate_visual_keys
            or actor_key in self._actor_placement_move_map
            or actor_key in self._actor_placement_rotate_map
            or actor_key in self._actor_thickness_dimension_map
        ):
            actor = None
            actor_key = None
        self._debug_trace(
            "left_click_pick",
            **self._debug_pick_payload(actor_key, x=int(x), y=int(y)),
            counts=self._debug_actor_counts(),
            modes=self._debug_mode_state(),
        )
        # Widget pipeline dispatch (Phase 6+). Concrete widgets in
        # _widget_registry get first crack at the event; if any of them
        # consumes it, skip the inline ladders below.
        registry = getattr(self._inspector, "_widget_registry", None)
        if registry is not None:
            classifier = PickClassifier(self._inspector)
            target, payload = classifier.classify(actor_key)
            try:
                cell_id = int(self._picker.GetCellId())
            except Exception:
                cell_id = -1
            event_data = InteractionEventData(
                event_type="mouse_press",
                display_xy=(float(x), float(y)),
                actor=actor,
                actor_key=actor_key,
                cell_id=cell_id if cell_id >= 0 else None,
                pick_target=target,
                target_payload=payload,
            )
            try:
                consumed = registry.dispatch(event_data)
            except Exception:
                consumed = None
            if consumed is not None:
                return
        # Phase 6-7 migrated the STEP-rotation, placement-rotate,
        # placement-translate, and thickness-dimension click ladders to
        # WidgetRegistry-routed AbstractWidgets above. They now consume
        # every event that previously fell into the inline ladders here,
        # so the ladders have been removed; the widget-fallback covers
        # the visual-only handle variants by bidding nothing and letting
        # the rest of this handler run.
        if self._center_row_to_ray_mode and self._center_row_to_ray_index is None:
            source_pick = self._center_axis_source_pick_ignoring_axis_overlays(x, y)
            row_index = source_pick.get("row_index") if source_pick is not None else None
            step_label = source_pick.get("step_label") if source_pick is not None else None
            if row_index is not None:
                row_index = int(row_index)
                if not (0 <= row_index < len(self.editor.rows)):
                    self.status_var.set("Center Row->Optical Axis: ignored stale trace-only display pick. Click the visible CAD/STL body again.")
                    self.render()
                    return
                if self.editor.rows[row_index].surface in {"Object", "Image"}:
                    self.status_var.set("Center Row->Optical Axis: Object/Image rows are references; choose a physical surface or CAD/STL row.")
                    self.render()
                    return
                self._set_row_highlight(row_index)
                self._set_ray_highlight(None)
                self._set_optical_axis_highlight(None)
                self.editor._select_table_row(row_index)
                row_name = self.editor.rows[row_index].name if 0 <= row_index < len(self.editor.rows) else "Surface"
                self._center_row_to_ray_index = row_index
                row_face_pick = source_pick.get("row_face_pick") if isinstance(source_pick, dict) else None
                picked_face_id = ""
                if row_face_pick is not None:
                    picked_face_id = str(row_face_pick.face.get("face_id", "") or "").strip()
                self._center_row_to_ray_face_id = picked_face_id or self._picked_scene_face_id_for_row(row_index)
                stl_note = " assigned optical-face anchor or" if self.editor._file_backed_stl_row_at(row_index) is not None else ""
                face_note = f" face {self._center_row_to_ray_face_id}" if self._center_row_to_ray_face_id else ""
                message = f"Center Row->Optical Axis: selected S{row_index}{face_note}: {row_name}. Now click the dotted Optical Axis guide for its{stl_note} center."
                self._update_mode_badge()
                self.refresh_from_editor()
                self.highlight_row(row_index)
                self.status_var.set(message)
                self.render()
                return
            if step_label is not None:
                actor = source_pick.get("actor")
                source_actor_key = source_pick.get("actor_key")
                try:
                    cell_id = int(source_pick.get("cell_id", -1))
                except Exception:
                    cell_id = -1
                step_label = str(step_label)
                feature_pick = source_pick.get("feature_pick") if isinstance(source_pick, dict) else None
                if not isinstance(feature_pick, dict):
                    feature_pick = self._step_feature_pick_for_display_xy(
                        step_label,
                        (x, y),
                        actor=actor,
                        actor_key=str(source_actor_key) if source_actor_key else None,
                        cell_id=cell_id,
                    )
                feature = feature_pick.get("feature") if feature_pick is not None else None
                surface_center = feature_pick.get("surface_center") if feature_pick is not None else None
                picked_face_id = str(feature_pick.get("face_id", "") if feature_pick is not None else "").strip()
                if not self._remember_selected_step_feature(step_label, feature, surface_center_world=surface_center, face_id=picked_face_id):
                    self.status_var.set("Center Row->Optical Axis: click a planar imported STEP face or a KrakenOS surface row.")
                    self.render()
                    return
                self._center_row_to_ray_mode = False
                self._center_row_to_ray_index = None
                self._center_row_to_ray_face_id = ""
                self._set_row_highlight(None)
                # Don't call `select_step_component(label)` /
                # `_set_step_highlight(label)` here. They flip
                # `editor._selected_step_label` to the picked STEP,
                # and the next scene refresh sees that and re-adds the
                # rotation-handle ring around the body. The user
                # reported "the rotation handles appeared after I
                # clicked Place -> Center -> Optical Axis" for the
                # second imported item -- this auto-chain is the
                # source. `_remember_selected_step_feature` above is
                # enough for the snap commit to find the right face,
                # and `start_step_normal_axis_pick` takes the label
                # explicitly so it doesn't need the editor-side
                # selection bit set.
                self._set_step_hover_outline(None, None)
                self.start_step_normal_axis_pick(step_label)
                self.render()
                return
            if actor_key is None and self.cancel_active_3d_operation():
                return
            self.status_var.set("Center Row->Optical Axis: click a surface/CAD row or imported STEP face before choosing Optical Axis.")
            self.render()
            return
        axis_info = self._actor_optical_axis_map.get(actor_key) if actor_key is not None else None
        # Wider proximity radius for axis picks: VTK's vtkCellPicker has tight
        # spatial tolerance for the dotted-line dashes, so the picker often
        # misses clicks that look on-target. 40 px (~2 cm on a typical display)
        # makes the axis a forgiving target for the snap workflows without
        # encroaching on the body click hit-box. Don't auto-cancel the pick
        # mode when the user clicks empty space -- they probably meant to hit
        # the axis but missed; show the "click the dotted Optical Axis guide"
        # nudge instead, so a stray click can't silently lose the workflow.
        AXIS_PICK_TOLERANCE_PX = 40.0
        if self._center_row_to_ray_mode:
            if self._center_row_to_ray_index is not None:
                axis_info = axis_info or self._optical_axis_info_near_display_xy((x, y), tolerance_px=AXIS_PICK_TOLERANCE_PX)
                if axis_info is not None:
                    axis_id = str(axis_info.get("axis_id", "") or "").strip()
                    self._set_optical_axis_highlight(axis_id)
                    self._apply_center_row_to_optical_axis(axis_info)
                    self.render()
                    return
                self.status_var.set("Center Row->Optical Axis: click the dotted Optical Axis guide.")
                self.render()
                return
            if axis_info is not None:
                self.status_var.set("Center Row->Optical Axis: click the surface/CAD row to move before choosing an Optical Axis.")
                self.render()
                return
        if self._step_normal_axis_pick_mode:
            axis_info = axis_info or self._optical_axis_info_near_display_xy((x, y), tolerance_px=AXIS_PICK_TOLERANCE_PX)
            if axis_info is not None:
                axis_id = str(axis_info.get("axis_id", "") or "").strip()
                self._set_optical_axis_highlight(axis_id)
                self._apply_step_normal_axis_pick(axis_info)
                self.render()
                return
            self.status_var.set("Snap STEP Normal->Optical Axis: click the dotted Optical Axis guide.")
            self.render()
            return
        if self._step_surface_center_axis_pick_mode:
            axis_info = axis_info or self._optical_axis_info_near_display_xy((x, y), tolerance_px=AXIS_PICK_TOLERANCE_PX)
            if axis_info is not None:
                axis_id = str(axis_info.get("axis_id", "") or "").strip()
                self._set_optical_axis_highlight(axis_id)
                self._apply_step_surface_center_axis_pick(axis_info)
                self.render()
                return
            self.status_var.set("Center Surface->Optical Axis: click the dotted Optical Axis guide.")
            self.render()
            return
        if axis_info is not None:
            axis_id = str(axis_info.get("axis_id", "") or "").strip()
            axis_label = str(axis_info.get("axis_label", "Optical Axis") or "Optical Axis")
            self._clear_open3d_selection(render=False)
            self._set_optical_axis_highlight(axis_id)
            self._set_row_highlight(None)
            self._set_ray_highlight(None)
            self.status_var.set(f"Selected {axis_label}. To align a STEP face, click the face first, then Snap STEP Normal->Optical Axis.")
            self.render()
            return
        step_label = self._actor_step_map.get(actor_key) if actor_key is not None else None
        fallback_step_pick = None
        if step_label is None:
            fallback_labels = None
            requested_label = getattr(self.editor, "_cad_axis_pick_label", None)
            axis_pick_any = bool(getattr(self.editor, "_cad_axis_pick_any", False))
            if requested_label is not None:
                fallback_labels = (requested_label,)
            fallback_step_pick = self._step_feature_pick_any_for_display_xy((x, y), labels=fallback_labels)
            if fallback_step_pick is not None:
                step_label = str(fallback_step_pick.get("label"))
        axis_pick_any = bool(getattr(self.editor, "_cad_axis_pick_any", False))
        if self._source_target_pick_mode and step_label is not None:
            self.status_var.set("Source Target: pick a KrakenOS surface/CAD solid row, not external STEP hardware.")
            return
        if self._placement_target_pick_mode and step_label is not None:
            self.status_var.set("Snap Row->Target: pick a KrakenOS surface/CAD solid row, not external STEP hardware.")
            return
        if self._placement_orient_pick_mode and step_label is not None:
            self.status_var.set("Orient Row->Target: pick a KrakenOS surface/CAD solid row, not external STEP hardware.")
            return
        if self._placement_orient_ray_mode and step_label is not None:
            self.status_var.set("Orient Row->Ray: pick a KrakenOS surface/CAD solid row or traced ray, not external STEP hardware.")
            return
        if self._step_carry_snap_ray_mode and step_label is not None:
            self.status_var.set("Snap STEP->Ray: click a traced ray, not external STEP hardware.")
            return
        if self._step_carry_snap_target_mode and step_label is not None:
            self.status_var.set("Snap STEP->Target: click a detector/object/active target row or CAD/STL face anchor.")
            return
        if step_label is not None:
            try:
                step_cell_id = int(self._picker.GetCellId()) if self._picker is not None else -1
            except Exception:
                step_cell_id = -1
            if self.editor._cad_led_object_edge_pick:
                if step_label != "led":
                    self.status_var.set("Pick an edge on the LED STEP for Object-to-LED distance.")
                    return
                feature = self._picked_feature_info_cached(actor, self._picker, actor_key=actor_key, cell_id=step_cell_id)
                if feature is None:
                    try:
                        center = np.asarray(self._picker.GetPickPosition(), dtype=float)
                    except Exception:
                        center = None
                else:
                    center = feature[0]
                if center is None or center.size < 3 or not np.all(np.isfinite(center[:3])):
                    self.status_var.set("Could not detect LED object-edge center.")
                    return
                self._set_step_hover_outline(None, None)
                self._set_axis_pick_cursor(False)
                self.editor.apply_led_object_edge_pick(center[:3])
                self.status_var.set("LED object-edge feature captured.")
                return
            requested_label = self.editor._cad_axis_pick_label
            if requested_label is None and not axis_pick_any:
                feature_pick = fallback_step_pick.get("feature_pick") if isinstance(fallback_step_pick, dict) else None
                if not isinstance(feature_pick, dict):
                    feature_pick = self._step_feature_pick_for_display_xy(
                        str(step_label),
                        (x, y),
                        actor=actor,
                        actor_key=actor_key,
                        cell_id=step_cell_id,
                    )
                feature = feature_pick.get("feature") if feature_pick is not None else None
                surface_center = feature_pick.get("surface_center") if feature_pick is not None else None
                picked_face_id = str(feature_pick.get("face_id", "") if feature_pick is not None else "").strip()
                remembered = self._remember_selected_step_feature(step_label, feature, surface_center_world=surface_center, face_id=picked_face_id)
                self.editor.select_step_component(step_label)
                self.show_step_rotation_handler(step_label, additive=shift_additive)
                if remembered:
                    self.status_var.set(
                        f"Selected {step_label.upper()} STEP face. Rotation handles remain active; "
                        "use Snap STEP Normal->Optical Axis or Center Surface->Optical Axis when ready."
                    )
                else:
                    self.status_var.set(f"Selected {step_label.upper()} STEP. Use the colored rotation handles or Center STEP Axis.")
                return
            if requested_label is not None and requested_label != step_label:
                self.status_var.set(f"CAD STEP picked: {step_label}. Center mode is armed for {str(requested_label).upper()}.")
                return
            feature_pick = fallback_step_pick.get("feature_pick") if isinstance(fallback_step_pick, dict) else None
            if not isinstance(feature_pick, dict):
                feature_pick = self._step_feature_pick_for_display_xy(
                    str(step_label),
                    (x, y),
                    actor=actor,
                    actor_key=actor_key,
                    cell_id=step_cell_id,
                )
            feature = feature_pick.get("feature") if feature_pick is not None else None
            picked_face_id = str(feature_pick.get("face_id", "") if feature_pick is not None else "").strip()
            if feature is None:
                try:
                    center = np.asarray(self._picker.GetPickPosition(), dtype=float)
                except Exception:
                    center = None
            else:
                center = feature[0]
            if center is None or center.size < 3 or not np.all(np.isfinite(center[:3])):
                self.status_var.set(f"Could not detect {step_label} feature center.")
                return
            self._remember_selected_step_feature(
                step_label,
                feature,
                surface_center_world=feature_pick.get("surface_center") if feature_pick is not None else None,
                face_id=picked_face_id,
            )
            self._set_step_hover_outline(None, None)
            self._set_axis_pick_cursor(False)
            self.editor._cad_axis_pick_any = False
            self.editor.apply_step_axis_pick(step_label, center[:3])
            self.show_step_rotation_handler(step_label)
            self.status_var.set(f"{step_label.upper()} feature center aligned to the optical axis. Rotation handles remain active.")
            return
        row_index = self._actor_row_map.get(actor_key) if actor_key is not None else None
        ray_index = self._actor_ray_map.get(actor_key) if actor_key is not None else None
        requested_label = self.editor._cad_axis_pick_label
        surface_target_label = requested_label
        if surface_target_label is None and axis_pick_any:
            selected_label = getattr(self.editor, "_selected_step_label", None)
            if selected_label in STEP_OVERLAY_LABEL_SET and self.editor._step_path_for_label(str(selected_label)) is not None:
                surface_target_label = str(selected_label)
        if surface_target_label is not None and row_index is not None:
            if self.editor._cad_led_object_edge_pick:
                self.status_var.set("Pick an edge on the LED STEP for Object-to-LED distance.")
                self.render()
                return
            try:
                result = self.editor.center_step_axis_on_surface(str(surface_target_label), int(row_index))
            except Exception as exc:
                self.status_var.set(f"Axis {str(surface_target_label).upper()} failed: {_short_error_message(exc)}")
                self.editor.append_debug(f"3D STEP surface-axis pick failed: {exc}")
                self.render()
                return
            self._set_axis_pick_cursor(False)
            self._set_step_hover_outline(None, None)
            self._set_row_highlight(int(row_index))
            self._set_ray_highlight(None)
            row_name = self.editor.rows[int(row_index)].name if 0 <= int(row_index) < len(self.editor.rows) else "Surface"
            if result is not None:
                target = result.get("target", (float("nan"), float("nan"), float("nan")))
                self.status_var.set(
                    f"{str(surface_target_label).upper()} STEP axis centered on S{int(row_index)}: {row_name} "
                    f"at X/Y=({float(target[0]):.6g}, {float(target[1]):.6g}) mm. Rotation handles remain active."
                )
                self.show_step_rotation_handler(str(surface_target_label))
            self.render()
            return
        if axis_pick_any and row_index is not None:
            self.status_var.set("Center STEP Axis: click a STEP feature, or select a STEP component before clicking a KrakenOS surface.")
            self.render()
            return
        if ray_index is not None:
            if self._step_carry_snap_ray_mode:
                try:
                    target = np.asarray(self._picker.GetPickPosition(), dtype=float).reshape(-1)[:3]
                except Exception:
                    target = np.asarray((float("nan"), float("nan"), float("nan")), dtype=float)
                if target.size < 3 or not np.all(np.isfinite(target)):
                    self.status_var.set("Snap STEP->Ray: could not resolve the picked 3D ray point.")
                    self.render()
                    return
                self._apply_step_carry_snap_ray(target, ray_index=int(ray_index))
                self.render()
                return
            if self._step_carry_snap_target_mode:
                self.status_var.set("Snap STEP->Target: click a detector/object/active target row or CAD/STL face anchor, not a ray.")
                self.render()
                return
            if self._placement_target_pick_mode:
                self.status_var.set("Snap Row->Target: pick a surface/CAD solid row, not a ray.")
                self.render()
                return
            if self._placement_orient_pick_mode:
                self.status_var.set("Orient Row->Target: pick a surface/CAD solid row/face normal, not a ray.")
                self.render()
                return
            if self._placement_orient_ray_mode:
                self._apply_placement_orient_ray_pick(int(ray_index))
                self.render()
                return
            if self._source_target_pick_mode:
                self.status_var.set("Source Target: pick a surface/CAD solid, not a ray.")
                self.render()
                return
            if self._center_row_to_ray_mode:
                self.status_var.set("Center Row->Optical Axis: regular rays are ignored; click the dotted Optical Axis guide.")
                self.render()
                return
            if not self._ray_pick_enabled():
                self._set_ray_highlight(None)
                self.status_var.set("Ray picking is disabled. Enable Pick rays in the toolbar before inspecting ray events.")
                self.render()
                return
            self._clear_open3d_selection(render=False)
            self._set_row_highlight(None)
            self._set_ray_highlight(int(ray_index))
            self.editor._select_ray_inspector_ray(int(ray_index))
            self.status_var.set(self.editor._ray_terminal_hint_text(int(ray_index), label=f"Selected ray {int(ray_index)} in Ray Inspector"))
            self.render()
            return
        if row_index is None:
            if actor_key is None and self._active_3d_operation_labels():
                if self.cancel_active_3d_operation():
                    return
            if self._placement_target_pick_mode:
                self.status_var.set("Snap Row->Target: click a surface/CAD solid row.")
                self.render()
                return
            if self._placement_orient_pick_mode:
                self.status_var.set("Orient Row->Target: click a surface/CAD solid row.")
                self.render()
                return
            if self._placement_orient_ray_mode:
                self.status_var.set("Orient Row->Ray: click a surface/CAD solid row or traced ray.")
                self.render()
                return
            if self._source_target_pick_mode:
                self.status_var.set("Source Target: click a surface/CAD solid row.")
                self.render()
                return
            if self._step_carry_snap_ray_mode:
                self.status_var.set("Snap STEP->Ray: click a traced ray.")
                self.render()
                return
            if self._step_carry_snap_target_mode:
                self.status_var.set("Snap STEP->Target: click a detector/object/active target row or CAD/STL face anchor.")
                self.render()
                return
            if self._clear_open3d_selection(render=False):
                self.status_var.set("Open 3D selection cleared.")
            else:
                self.status_var.set("3D scene ready")
            self.render()
            return
        if self._source_target_pick_mode:
            self._apply_source_target_pick(int(row_index))
            self.render()
            return
        if self._placement_target_pick_mode:
            self._apply_placement_target_pick(int(row_index))
            self.render()
            return
        if self._placement_orient_pick_mode:
            self._apply_placement_orient_pick(int(row_index))
            self.render()
            return
        if self._placement_orient_ray_mode:
            self._apply_placement_orient_ray_row_pick(int(row_index))
            self.render()
            return
        if self._step_carry_snap_ray_mode:
            self.status_var.set("Snap STEP->Ray: click a traced ray, not a surface row.")
            self.render()
            return
        if self._step_carry_snap_target_mode:
            face_id = self._picked_scene_face_id_for_row(int(row_index))
            self._apply_step_carry_snap_target(int(row_index), face_id=face_id)
            self.render()
            return
        self._clear_open3d_selection(render=False)
        self._set_row_highlight(row_index)
        self._set_ray_highlight(None)
        self.editor._select_table_row(row_index)
        row_name = self.editor.rows[row_index].name if 0 <= row_index < len(self.editor.rows) else "Surface"
        if self._center_row_to_ray_mode:
            if self.editor.rows[row_index].surface in {"Object", "Image"}:
                self.status_var.set("Center Row->Optical Axis: Object/Image rows are references; choose a physical surface or CAD/STL row.")
                self.render()
                return
            self._center_row_to_ray_index = int(row_index)
            source_pick = self._center_axis_source_pick_ignoring_axis_overlays(x, y)
            row_face_pick = source_pick.get("row_face_pick") if isinstance(source_pick, dict) else None
            picked_face_id = ""
            if row_face_pick is not None:
                picked_face_id = str(row_face_pick.face.get("face_id", "") or "").strip()
            self._center_row_to_ray_face_id = picked_face_id or self._picked_scene_face_id_for_row(int(row_index))
            stl_note = " assigned optical-face anchor or" if self.editor._file_backed_stl_row_at(int(row_index)) is not None else ""
            self._set_ray_highlight(None)
            self._set_optical_axis_highlight(None)
            face_note = f" face {self._center_row_to_ray_face_id}" if self._center_row_to_ray_face_id else ""
            message = f"Center Row->Optical Axis: selected S{row_index}{face_note}: {row_name}. Now click the dotted Optical Axis guide for its{stl_note} center."
            self._update_mode_badge()
            self.refresh_from_editor()
            self.highlight_row(row_index)
            self.status_var.set(message)
            self.render()
            return
        if self.editor._file_backed_stl_row_at(row_index) is not None:
            self._stl_placement_row_index = int(row_index)
            self._placement_handle_selected_row_index = int(row_index)
            self._update_stl_placement_handler_state()
            if self._show_rotation_handles():
                self.refresh_from_editor()
                self.highlight_row(row_index)
            self.status_var.set(
                f"Selected CAD/STL row {row_index}: {row_name}. "
                "Right-click a face to assign physics, or use Place controls for pose changes."
            )
        else:
            self._close_stl_placement_handler()
            self.status_var.set(f"Selected row {row_index}: {row_name}")
        self.render()

    def _passive_hover_pick_rotation_handle(self, x: int | float, y: int | float):
        """Pick only lightweight rotation handles during passive mouse motion.

        Dense CAD/STEP bodies are intentionally excluded here. Full body/face
        picking still happens on explicit click, right-click, and active
        placement commands.
        """
        picker = getattr(self, "_prop_picker", None) or self._picker
        if picker is None or self._renderer is None:
            return None, None, -1
        handle_keys = set(getattr(self, "_actor_step_rotate_map", {}) or {})
        handle_keys.update(set(getattr(self, "_actor_step_translate_map", {}) or {}))
        handle_keys.update(set(getattr(self, "_actor_placement_rotate_map", {}) or {}))
        # bugs/0019: the placement MOVE (slide) handle was absent from the hover
        # pick set, so hovering it never highlighted. Include it so it gets the
        # same gold hover affordance as the rotate/translate handles.
        handle_keys.update(set(getattr(self, "_actor_placement_move_map", {}) or {}))
        if not handle_keys:
            return None, None, -1
        pick_from_list = False
        try:
            picker.InitializePickList()
            for actor_key in sorted(str(key) for key in handle_keys):
                actor = self._actor_by_key.get(actor_key)
                if actor is not None:
                    picker.AddPickList(actor)
                    pick_from_list = True
            if not pick_from_list:
                return None, None, -1
            picker.PickFromListOn()
        except Exception:
            return None, None, -1
        try:
            picker.Pick(float(x), float(y), 0.0, self._renderer)
            actor = picker.GetActor()
        except Exception:
            return None, None, -1
        finally:
            try:
                picker.PickFromListOff()
                picker.InitializePickList()
            except Exception:
                pass
        actor_key = self._actor_key(actor)
        cell_id = -1
        if picker is self._picker:
            try:
                cell_id = int(self._picker.GetCellId())
            except Exception:
                cell_id = -1
        return actor, actor_key, cell_id

    def _on_mouse_move(self, obj, _event) -> None:
        # When the deep-trace mode is on, log every entry regardless of
        # the throttle so a hang inside this handler can be located to
        # the exact mouse-move callback. Cheap: one ``if`` per move
        # when tracing is off.
        if open3d_trace_enabled():
            try:
                _x, _y = self._vtk_interactor.GetEventPosition() if self._vtk_interactor is not None else (-1, -1)
            except Exception:
                _x = _y = -1
            open3d_trace_event(
                "on_mouse_move_entry",
                x=int(_x),
                y=int(_y),
                carry_drag=self._step_carry_drag_state is not None,
                carry_follow=self._step_carry_follow_state is not None,
                center_row_to_ray=bool(self._center_row_to_ray_mode),
                step_normal_axis=bool(self._step_normal_axis_pick_mode),
                step_surface_center=bool(self._step_surface_center_axis_pick_mode),
            )
        hover_critical = bool(self._center_row_to_ray_mode or self._step_normal_axis_pick_mode or self._step_surface_center_axis_pick_mode)
        if (
            self._step_carry_drag_state is None
            and self._step_carry_follow_state is None
            and not hover_critical
            and not self._mouse_move_due()
        ):
            open3d_trace_event("on_mouse_move_throttled")
            return
        try:
            x, y = self._vtk_interactor.GetEventPosition() if self._vtk_interactor is not None else (-1, -1)
            self._timing_event("mouse_move_processed", x=int(x), y=int(y), hover_critical=hover_critical)
        except Exception:
            pass
        if self._placement_target_pick_mode:
            self._set_rotation_handle_hover(None)
            self._update_hover_status("", render=False)
            self._set_axis_pick_cursor(True)
            if self._placement_target_row_index is None:
                self.status_var.set("Snap Row->Target: click movable row/face.")
            else:
                self.status_var.set("Snap Row->Target: click target row/face.")
            return
        if self._placement_orient_pick_mode:
            self._set_rotation_handle_hover(None)
            self._update_hover_status("", render=False)
            self._set_axis_pick_cursor(True)
            if self._placement_orient_row_index is None:
                self.status_var.set("Orient Row->Target: click movable row/face.")
            else:
                self.status_var.set("Orient Row->Target: click target row/face normal.")
            return
        if self._placement_orient_ray_mode:
            self._set_rotation_handle_hover(None)
            self._update_hover_status("", render=False)
            self._set_axis_pick_cursor(True)
            if self._placement_orient_ray_row_index is None:
                self.status_var.set("Orient Row->Ray: click movable row/face.")
            else:
                self.status_var.set("Orient Row->Ray: click target ray direction.")
            return
        if self._source_target_pick_mode:
            self._set_rotation_handle_hover(None)
            self._update_hover_status("", render=False)
            self._set_axis_pick_cursor(True)
            self.status_var.set("Source Target: click a surface/CAD solid row.")
            return
        if self._center_row_to_ray_mode:
            self._set_rotation_handle_hover(None)
            self._set_axis_pick_cursor(True)
            if self._center_row_to_ray_index is None:
                row_index = None
                step_label = None
                actor = None
                actor_key = None
                cell_id = -1
                if self._renderer is not None and self._vtk_interactor is not None:
                    try:
                        x, y = self._vtk_interactor.GetEventPosition()
                        source_pick = self._center_axis_source_pick_ignoring_axis_overlays(x, y)
                        if source_pick is not None:
                            actor = source_pick.get("actor")
                            actor_key = source_pick.get("actor_key")
                            row_index = source_pick.get("row_index")
                            step_label = source_pick.get("step_label")
                            try:
                                cell_id = int(source_pick.get("cell_id", -1))
                            except Exception:
                                cell_id = -1
                    except Exception:
                        row_index = None
                        step_label = None
                self._set_optical_axis_highlight(None)
                if step_label is not None:
                    hover_key = (actor_key, int(cell_id))
                    outline = None
                    picked_face_id = ""
                    if hover_key != self._hover_step_cell_key:
                        feature_pick = source_pick.get("feature_pick") if isinstance(source_pick, dict) else None
                        if not isinstance(feature_pick, dict):
                            feature_pick = self._step_feature_pick_for_display_xy(
                                str(step_label),
                                (x, y),
                                actor=actor,
                                actor_key=actor_key,
                                cell_id=cell_id,
                            )
                        feature = feature_pick.get("feature") if feature_pick is not None else None
                        picked_face_id = str(feature_pick.get("face_id", "") if feature_pick is not None else "").strip()
                        if picked_face_id:
                            hover_key = (actor_key, "display", picked_face_id)
                        outline = self._hover_overlay_for_feature(feature[0], feature[1]) if feature is not None else None
                    self._set_step_hover_outline(outline, hover_key)
                    if self._picked_row_index is not None:
                        self._set_row_highlight(None)
                    display = self.editor._step_overlay_display_label(str(step_label)).upper()
                    face_text = f" {picked_face_id}" if picked_face_id else ""
                    self._update_hover_status(
                        f"{display} STEP{face_text} face\nDefault after promotion: Uncoated",
                        display_xy=(x, y) if "x" in locals() and "y" in locals() else None,
                        render=True,
                    )
                    self.status_var.set(f"Center Row->Optical Axis: click this {display} STEP{face_text} face, then click Optical Axis.")
                    return
                self._set_step_hover_outline(None, None)
                self._update_hover_status("", render=False)
                if row_index is not None and 0 <= int(row_index) < len(self.editor.rows):
                    row = self.editor.rows[int(row_index)]
                    if row.surface not in {"Object", "Image"}:
                        row_face_pick = source_pick.get("row_face_pick") if isinstance(source_pick, dict) else None
                        if row_face_pick is not None:
                            face_id = str(row_face_pick.face.get("face_id", "") or "").strip()
                            try:
                                source_cell_id = int(source_pick.get("cell_id", -1)) if isinstance(source_pick, dict) else -1
                            except Exception:
                                source_cell_id = -1
                            hover_key = ("row", int(row_index), face_id or source_cell_id)
                            outline = None
                            if hover_key != self._hover_step_cell_key:
                                outline = self._hover_overlay_for_row_face(int(row_index), row_face_pick.face)
                            self._set_step_hover_outline(outline, hover_key)
                            if self._picked_row_index is not None:
                                self._set_row_highlight(None)
                            self._update_hover_status(
                                f"S{int(row_index)} {row.name or row.surface or 'CAD row'}{(' ' + face_id) if face_id else ''} face",
                                display_xy=(x, y),
                                render=True,
                            )
                            self.status_var.set(f"Center Row->Optical Axis: click S{int(row_index)}{(' ' + face_id) if face_id else ''} face.")
                            return
                        self._set_step_hover_outline(None, None)
                        if self._picked_row_index != int(row_index):
                            self._set_row_highlight(int(row_index))
                            self.render()
                        self.status_var.set(f"Center Row->Optical Axis: click S{int(row_index)} to select this surface/CAD row.")
                        return
                    if self._picked_row_index is not None:
                        self._set_row_highlight(None)
                        self.render()
                    self.status_var.set("Center Row->Optical Axis: Object/Image rows are references; choose a physical surface or CAD/STL row.")
                    return
                if self._picked_row_index is not None:
                    self._set_row_highlight(None)
                    self.render()
                self.status_var.set("Center Row->Optical Axis: click the surface/CAD row to move first.")
                return
            axis_info = None
            if self._renderer is not None and self._vtk_interactor is not None:
                try:
                    x, y = self._vtk_interactor.GetEventPosition()
                    _traced_pick(self._picker, x, y, 0.0, self._renderer, site="hover_center_row_to_ray")
                    actor_key = self._actor_key(self._picker.GetActor())
                    axis_info = self._actor_optical_axis_map.get(actor_key) if actor_key is not None else None
                    axis_info = axis_info or self._optical_axis_info_near_display_xy((x, y), tolerance_px=28.0)
                except Exception:
                    axis_info = None
            if axis_info is not None:
                axis_id = str(axis_info.get("axis_id", "") or "").strip()
                axis_label = str(axis_info.get("axis_label", "Optical Axis") or "Optical Axis")
                self._set_optical_axis_highlight(axis_id)
                self._update_hover_status(f"{axis_label}\nClick to center selected row.", display_xy=(x, y), render=True)
                self.status_var.set(f"Click {axis_label} to center the selected row.")
                return
            self._set_optical_axis_highlight(None)
            self._update_hover_status("", render=False)
            self.render()
            self.status_var.set("Center Row->Optical Axis: click the dotted Optical Axis guide.")
            return
        if self._step_normal_axis_pick_mode:
            self._set_rotation_handle_hover(None)
            self._set_axis_pick_cursor(True)
            if self._picker is not None and self._renderer is not None and self._vtk_interactor is not None:
                try:
                    x, y = self._vtk_interactor.GetEventPosition()
                    _traced_pick(self._picker, x, y, 0.0, self._renderer, site="hover_step_normal_axis")
                    actor_key = self._actor_key(self._picker.GetActor())
                    axis_info = self._actor_optical_axis_map.get(actor_key) if actor_key is not None else None
                    axis_info = axis_info or self._optical_axis_info_near_display_xy((x, y), tolerance_px=28.0)
                except Exception:
                    axis_info = None
                if axis_info is not None:
                    axis_id = str(axis_info.get("axis_id", "") or "").strip()
                    axis_label = str(axis_info.get("axis_label", "Optical Axis") or "Optical Axis")
                    self._set_optical_axis_highlight(axis_id)
                    anchor_text = "picked point" if str(getattr(self, "_step_normal_axis_anchor_mode", "surface_center")).strip().lower() == "pick_point" else "surface center"
                    self._update_hover_status(f"{axis_label}\nClick to align selected STEP face\nAnchor={anchor_text}", display_xy=(x, y), render=True)
                    self.status_var.set(f"Click {axis_label} to align the selected STEP face normal using its {anchor_text}.")
                    return
            self._set_optical_axis_highlight(None)
            self._update_hover_status("", render=False)
            self.render()
            self.status_var.set("Snap STEP Normal->Optical Axis: click the dotted Optical Axis guide.")
            return
        if self._step_surface_center_axis_pick_mode:
            self._set_rotation_handle_hover(None)
            self._set_axis_pick_cursor(True)
            if self._picker is not None and self._renderer is not None and self._vtk_interactor is not None:
                try:
                    x, y = self._vtk_interactor.GetEventPosition()
                    _traced_pick(self._picker, x, y, 0.0, self._renderer, site="hover_step_surface_center")
                    actor_key = self._actor_key(self._picker.GetActor())
                    axis_info = self._actor_optical_axis_map.get(actor_key) if actor_key is not None else None
                    axis_info = axis_info or self._optical_axis_info_near_display_xy((x, y), tolerance_px=28.0)
                except Exception:
                    axis_info = None
                if axis_info is not None:
                    axis_id = str(axis_info.get("axis_id", "") or "").strip()
                    axis_label = str(axis_info.get("axis_label", "Optical Axis") or "Optical Axis")
                    self._set_optical_axis_highlight(axis_id)
                    center_text = self._world_xyz_text(self._selected_step_feature_surface_center_world)
                    self._update_hover_status(
                        f"{axis_label}\nClick to center selected STEP surface\nSurface center={center_text}",
                        display_xy=(x, y),
                        render=True,
                    )
                    self.status_var.set(f"Click {axis_label} to center the selected STEP surface.")
                    return
            self._set_optical_axis_highlight(None)
            self._update_hover_status("", render=False)
            self.render()
            self.status_var.set("Center Surface->Optical Axis: click the dotted Optical Axis guide.")
            return
        if self._step_carry_snap_ray_mode:
            self._set_rotation_handle_hover(None)
            self._update_hover_status("", render=False)
            self._set_axis_pick_cursor(True)
            self.status_var.set("Snap STEP->Ray: click a traced ray.")
            return
        if self._step_carry_snap_target_mode:
            self._set_rotation_handle_hover(None)
            self._update_hover_status("", render=False)
            self._set_axis_pick_cursor(True)
            self.status_var.set("Snap STEP->Target: click detector/object/active target row or CAD/STL face anchor.")
            return
        if self._step_carry_drag_state is not None:
            self._set_rotation_handle_hover(None)
            self._update_hover_status("", render=False)
            self._set_step_carry_cursor(True)
            return
        if self._step_carry_follow_state is not None:
            self._apply_step_carry_follow_motion()
            return
        requested_label = self.editor._cad_axis_pick_label
        axis_pick_any = bool(getattr(self.editor, "_cad_axis_pick_any", False))
        led_edge_pick = bool(getattr(self.editor, "_cad_led_object_edge_pick", False))
        target_label = "led" if led_edge_pick else requested_label
        if target_label is None and not axis_pick_any:
            carry_label = self._step_carry_label()
            if carry_label is not None:
                target_label = str(carry_label)
        if target_label is None and not axis_pick_any:
            if self._picker is not None and self._renderer is not None and self._vtk_interactor is not None:
                try:
                    x, y = self._vtk_interactor.GetEventPosition()
                    actor, actor_key, _cell_id = self._passive_hover_pick_rotation_handle(x, y)
                    step_rotate = self._actor_step_rotate_map.get(actor_key) if actor_key is not None else None
                    step_translate = self._actor_step_translate_map.get(actor_key) if actor_key is not None else None
                    placement_rotate = self._actor_placement_rotate_map.get(actor_key) if actor_key is not None else None
                    placement_move = self._actor_placement_move_map.get(actor_key) if actor_key is not None else None
                    if step_rotate is not None:
                        self._set_step_hover_outline(None, None)
                        self._set_rotation_handle_hover(actor_key)
                        self._update_hover_status("", render=False)
                        label, axis, delta = step_rotate
                        display = self.editor._step_overlay_display_label(str(label)).upper()
                        self.status_var.set(
                            f"{display} STEP rotation handle: click {str(axis).upper()}{float(delta):+.0f} deg."
                        )
                        return
                    if step_translate is not None:
                        self._set_step_hover_outline(None, None)
                        self._set_rotation_handle_hover(actor_key)
                        self._update_hover_status("", render=False)
                        label, axis, _delta = step_translate
                        display = self.editor._step_overlay_display_label(str(label)).upper()
                        self.status_var.set(
                            f"{display} STEP move handle: hold-drag {str(axis).upper()} to translate freely."
                        )
                        return
                    if placement_rotate is not None:
                        self._set_step_hover_outline(None, None)
                        self._set_rotation_handle_hover(actor_key)
                        self._update_hover_status("", render=False)
                        row_index, axis, delta = placement_rotate
                        self.status_var.set(
                            f"S{int(row_index)} rotation handle: click {str(axis).upper()}{float(delta):+.6g} deg."
                        )
                        return
                    if placement_move is not None:
                        self._set_step_hover_outline(None, None)
                        self._set_rotation_handle_hover(actor_key)
                        self._update_hover_status("", render=False)
                        row_index, axis, _delta = placement_move
                        self.status_var.set(
                            f"S{int(row_index)} move handle: hold-drag {str(axis).upper()} to slide."
                        )
                        return
                    self._set_rotation_handle_hover(None)
                    step_label = self._actor_step_map.get(actor_key) if actor_key is not None else None
                    fallback_step_pick = None
                    if step_label is None:
                        fallback_step_pick = self._step_feature_pick_any_for_display_xy((x, y))
                        if fallback_step_pick is not None:
                            step_label = str(fallback_step_pick.get("label"))
                    if step_label is not None:
                        try:
                            cell_id = int(self._picker.GetCellId())
                        except Exception:
                            cell_id = -1
                        feature_pick = fallback_step_pick.get("feature_pick") if isinstance(fallback_step_pick, dict) else None
                        if not isinstance(feature_pick, dict):
                            feature_pick = self._step_feature_pick_for_display_xy(
                                str(step_label),
                                (x, y),
                                actor=actor,
                                actor_key=actor_key,
                                cell_id=cell_id,
                            )
                        feature = feature_pick.get("feature") if feature_pick is not None else None
                        if feature is not None:
                            face_id = str(feature_pick.get("face_id", "") if feature_pick is not None else "").strip()
                            hover_key = (actor_key, "passive", face_id or int(cell_id))
                            outline = None
                            if hover_key != self._hover_step_cell_key:
                                outline = self._hover_overlay_for_feature(feature[0], feature[1])
                            self._set_step_hover_outline(outline, hover_key)
                            face_note = f" {face_id} face" if face_id else " feature"
                            self._update_hover_status(
                                f"{str(step_label).upper()} STEP{face_note}",
                                display_xy=(x, y),
                                render=True,
                            )
                            self._set_axis_pick_cursor(True)
                            return
                except Exception:
                    actor = None
                    actor_key = None
            self._set_step_hover_outline(None, None)
            self._set_rotation_handle_hover(None)
            self._update_hover_status("", render=False)
            self._set_axis_pick_cursor(False)
            return
        if self._picker is None or self._renderer is None or self._vtk_interactor is None:
            return
        try:
            x, y = self._vtk_interactor.GetEventPosition()
            _traced_pick(self._picker, x, y, 0.0, self._renderer, site="hover_default")
            actor = self._picker.GetActor()
        except Exception:
            actor = None
        actor_key = self._actor_key(actor)
        step_rotate = self._actor_step_rotate_map.get(actor_key) if actor_key is not None else None
        step_translate = self._actor_step_translate_map.get(actor_key) if actor_key is not None else None
        placement_rotate = self._actor_placement_rotate_map.get(actor_key) if actor_key is not None else None
        placement_move = self._actor_placement_move_map.get(actor_key) if actor_key is not None else None
        if step_rotate is not None:
            self._set_step_hover_outline(None, None)
            self._set_rotation_handle_hover(actor_key)
            self._update_hover_status("", render=False)
            label, axis, delta = step_rotate
            self._set_axis_pick_cursor(False)
            display = self.editor._step_overlay_display_label(str(label)).upper()
            self.status_var.set(f"{display} STEP rotation handle: click {str(axis).upper()}{float(delta):+.0f} deg.")
            return
        if step_translate is not None:
            self._set_step_hover_outline(None, None)
            self._set_rotation_handle_hover(actor_key)
            self._update_hover_status("", render=False)
            label, axis, _delta = step_translate
            self._set_axis_pick_cursor(False)
            display = self.editor._step_overlay_display_label(str(label)).upper()
            self.status_var.set(f"{display} STEP move handle: hold-drag {str(axis).upper()} to translate freely.")
            return
        if placement_rotate is not None:
            self._set_step_hover_outline(None, None)
            self._set_rotation_handle_hover(actor_key)
            self._update_hover_status("", render=False)
            row_index, axis, delta = placement_rotate
            self._set_axis_pick_cursor(False)
            self.status_var.set(f"S{int(row_index)} rotation handle: click {str(axis).upper()}{float(delta):+.6g} deg.")
            return
        if placement_move is not None:
            self._set_step_hover_outline(None, None)
            self._set_rotation_handle_hover(actor_key)
            self._update_hover_status("", render=False)
            row_index, axis, _delta = placement_move
            self._set_axis_pick_cursor(False)
            self.status_var.set(f"S{int(row_index)} move handle: hold-drag {str(axis).upper()} to slide.")
            return
        self._set_rotation_handle_hover(None)
        step_label = self._actor_step_map.get(actor_key) if actor_key is not None else None
        fallback_step_pick = None
        if step_label is None:
            fallback_labels = None
            if target_label is not None and not axis_pick_any:
                fallback_labels = (target_label,)
            fallback_step_pick = self._step_feature_pick_any_for_display_xy((x, y), labels=fallback_labels)
            if fallback_step_pick is not None:
                step_label = str(fallback_step_pick.get("label"))
        if step_label is not None and (axis_pick_any or step_label == target_label):
            try:
                cell_id = int(self._picker.GetCellId())
            except Exception:
                cell_id = -1
            feature_pick = fallback_step_pick.get("feature_pick") if isinstance(fallback_step_pick, dict) else None
            if not isinstance(feature_pick, dict):
                feature_pick = self._step_feature_pick_for_display_xy(
                    str(step_label),
                    (x, y),
                    actor=actor,
                    actor_key=actor_key,
                    cell_id=cell_id,
                )
            outline = None
            through_pick = feature_pick.get("through_pick") if feature_pick is not None else None
            if feature_pick is not None and str(feature_pick.get("face_id", "") or "").strip():
                face_id = str(feature_pick.get("face_id", "") or "").strip()
                hover_key = (actor_key, "ray", face_id)
                if hover_key != self._hover_step_cell_key:
                    feature = feature_pick.get("feature")
                    outline = self._hover_overlay_for_feature(feature[0], feature[1]) if feature is not None else None
            else:
                hover_key = (actor_key, cell_id)
                if hover_key != self._hover_step_cell_key:
                    feature = feature_pick.get("feature") if feature_pick is not None else None
                    outline = self._hover_overlay_for_feature(feature[0], feature[1]) if feature is not None else None
            self._set_step_hover_outline(outline, hover_key)
            self._set_axis_pick_cursor(True)
            face_note = ""
            coordinate_lines: list[str] = []
            if through_pick is not None:
                face_id = str(through_pick.face.get("face_id", "") or "").strip() or "face"
                face_note = f" {face_id} internal face" if through_pick.internal else f" {face_id} face"
                coordinate_lines.append(f"Pick={self._world_xyz_text(through_pick.point_world)}")
                coordinate_lines.append(f"Center={self._world_xyz_text(self._surface_center_from_face_ray_pick(through_pick))}")
            else:
                try:
                    pick_point = np.asarray(self._picker.GetPickPosition(), dtype=float).reshape(-1)[:3]
                except Exception:
                    pick_point = np.asarray([], dtype=float)
                if pick_point.size >= 3 and np.all(np.isfinite(pick_point[:3])):
                    coordinate_lines.append(f"Pick={self._world_xyz_text(pick_point[:3])}")
            coordinate_text = "\n" + "\n".join(coordinate_lines) if coordinate_lines else ""
            self._update_hover_status(f"{str(step_label).upper()} STEP{face_note or ' feature'}{coordinate_text}", display_xy=(x, y), render=True)
            if led_edge_pick:
                self.status_var.set("Click the LED edge used for Object-to-LED distance.")
            elif axis_pick_any:
                self.status_var.set(f"Click the {step_label} feature to center it on the optical axis.")
            else:
                self.status_var.set(f"Click the {step_label} feature to center it on the optical axis.")
            return
        self._set_step_hover_outline(None, None)
        self._update_hover_status("", render=False)
        self._set_axis_pick_cursor(False)
