"""Open 3D Tk mouse binding service."""

from __future__ import annotations

from typing import Any


class Open3DMouseBindingsService:
    """Install the embedded Open 3D mouse bindings."""

    def __init__(self, inspector: Any) -> None:
        object.__setattr__(self, "_inspector", inspector)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inspector, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_inspector":
            object.__setattr__(self, name, value)
            return
        setattr(self._inspector, name, value)

    def _install_pick_only_left_click_bindings(self) -> None:
        """Left click selects; left drag rotates; middle drag pans the camera."""
        if self._vtk_widget is None:
            return

        drag_threshold_px = 4

        def control_pressed(event) -> bool:
            return self._event_control_pressed(event)

        def set_event_info(event) -> None:
            if self._vtk_interactor is not None:
                try:
                    ctrl = 1 if control_pressed(event) else 0
                    self._vtk_interactor.SetEventInformationFlipY(event.x, event.y, ctrl, 0, chr(0), 0, None)
                except Exception:
                    pass

        def record_mouse(kind: str, event, button: int) -> None:
            recorder = getattr(self._inspector, "_event_recorder", None)
            if recorder is None:
                return
            try:
                recorder.record_mouse(kind, event=event, button=button)
            except Exception:
                pass

        def record_key(kind: str, event) -> None:
            recorder = getattr(self._inspector, "_event_recorder", None)
            if recorder is None:
                return
            try:
                recorder.record_key(
                    kind,
                    keysym=str(getattr(event, "keysym", "") or ""),
                    state=int(getattr(event, "state", 0) or 0),
                )
            except Exception:
                pass

        def left_press(event):
            record_mouse("mouse_press", event, 1)
            set_event_info(event)
            self._cancel_step_carry_hold_timer()
            ctrl_pressed = control_pressed(event)
            if self._step_carry_follow_state is not None and not ctrl_pressed:
                self.stop_step_carry()
                return "break"
            self._left_drag_active = True
            self._left_drag_start_xy = (int(event.x), int(event.y))
            self._left_drag_last_xy = (int(event.x), int(event.y))
            self._left_drag_moved = False
            self._ctrl_left_camera_active = ctrl_pressed
            if ctrl_pressed:
                self._placement_drag_state = None
                self._thickness_drag_state = None
                self._step_carry_drag_state = None
                self._axis_slide_drag_state = None
                self._step_translate_drag_state = None
            else:
                self._step_translate_drag_state = self._step_translate_state_from_current_pick()
                if self._step_translate_drag_state is not None:
                    self._axis_slide_drag_state = None
                    self._placement_drag_state = None
                    self._thickness_drag_state = None
                    self._step_carry_drag_state = None
                    self._row_carry_drag_state = None
                else:
                    self._axis_slide_drag_state = self._axis_slide_state_from_current_pick()
                    if self._axis_slide_drag_state is not None:
                        self._placement_drag_state = None
                        self._thickness_drag_state = None
                        self._step_carry_drag_state = None
                        self._row_carry_drag_state = None
                    else:
                        self._placement_drag_state = self._placement_drag_state_from_current_pick()
                        self._thickness_drag_state = None
                        self._step_carry_drag_state = None
                        self._row_carry_drag_state = None
                        if self._placement_drag_state is None:
                            self._thickness_drag_state = self._thickness_drag_state_from_current_pick()
                        if self._placement_drag_state is None and self._thickness_drag_state is None:
                            step_label = self._step_carry_label_from_current_pick()
                            if step_label is not None:
                                self._arm_step_carry_hold(step_label, (int(event.x), int(event.y)))
                            else:
                                row_index = self._row_carry_index_from_current_pick()
                                if row_index is not None:
                                    self._arm_row_carry_hold(row_index, (int(event.x), int(event.y)))
            return "break"

        def left_motion(event):
            record_mouse("mouse_move", event, 1)
            set_event_info(event)
            if not self._left_drag_active:
                return "break"
            current = (int(event.x), int(event.y))
            start = self._left_drag_start_xy or current
            last = self._left_drag_last_xy or current
            total_dx = current[0] - start[0]
            total_dy = current[1] - start[1]
            if (total_dx * total_dx + total_dy * total_dy) >= drag_threshold_px * drag_threshold_px:
                self._left_drag_moved = True
            if self._left_drag_moved:
                dx = current[0] - last[0]
                dy = current[1] - last[1]
                ctrl_pressed = control_pressed(event)
                if ctrl_pressed:
                    self._cancel_step_carry_hold_timer()
                    self._ctrl_left_camera_active = True
                    self._rotate_camera_fixed_drag(dx, dy)
                elif self._step_translate_drag_state is not None:
                    self._cancel_step_carry_hold_timer()
                    self._apply_step_translate_drag_motion(dx, dy)
                elif self._axis_slide_drag_state is not None:
                    self._cancel_step_carry_hold_timer()
                    self._apply_axis_slide_drag_motion(dx, dy)
                elif self._placement_drag_state is not None:
                    self._cancel_step_carry_hold_timer()
                    self._apply_placement_drag_motion(dx, dy)
                elif self._thickness_drag_state is not None:
                    self._cancel_step_carry_hold_timer()
                    self._cancel_row_carry_hold_timer()
                    self._apply_thickness_drag_motion(dx, dy)
                elif self._step_carry_drag_state is not None:
                    self._apply_step_carry_drag_motion(dx, dy, current_xy=current)
                    # This branch returns early to suppress camera rotation, so
                    # it must update the drag baseline itself.
                    self._left_drag_last_xy = current
                    return "break"
                elif self._row_carry_drag_state is not None:
                    self._apply_row_carry_drag_motion(current_xy=current)
                    self._left_drag_last_xy = current
                    return "break"
                elif self._step_carry_hold_candidate_label is not None:
                    after_id = self._step_carry_hold_after_id
                    self._step_carry_hold_after_id = None
                    if after_id is not None:
                        try:
                            self._vtk_widget.after_cancel(after_id)
                        except Exception:
                            pass
                    self._activate_step_carry_hold()
                    if self._step_carry_drag_state is not None:
                        self._apply_step_carry_drag_motion(dx, dy, current_xy=current)
                        self._left_drag_last_xy = current
                        return "break"
                elif self._row_carry_hold_candidate_index is not None:
                    after_id = self._row_carry_hold_after_id
                    self._row_carry_hold_after_id = None
                    if after_id is not None:
                        try:
                            self._vtk_widget.after_cancel(after_id)
                        except Exception:
                            pass
                    self._activate_row_carry_hold()
                    if self._row_carry_drag_state is not None:
                        self._apply_row_carry_drag_motion(current_xy=current)
                        self._left_drag_last_xy = current
                        return "break"
                else:
                    self._rotate_camera_fixed_drag(dx, dy)
            self._left_drag_last_xy = current
            return "break"

        def left_release(event):
            record_mouse("mouse_release", event, 1)
            set_event_info(event)
            should_pick = self._left_drag_active and not self._left_drag_moved
            ctrl_active = self._ctrl_left_camera_active or control_pressed(event)
            placement_drag_state = self._placement_drag_state
            thickness_drag_state = self._thickness_drag_state
            step_carry_drag_state = self._step_carry_drag_state
            step_carry_follow_state = self._step_carry_follow_state
            row_carry_drag_state = self._row_carry_drag_state
            axis_slide_drag_state = self._axis_slide_drag_state
            step_translate_drag_state = self._step_translate_drag_state
            self._cancel_step_carry_hold_timer()
            self._cancel_row_carry_hold_timer()
            self._left_drag_active = False
            self._left_drag_start_xy = None
            self._left_drag_last_xy = None
            self._left_drag_moved = False
            self._placement_drag_state = None
            self._thickness_drag_state = None
            self._step_carry_drag_state = None
            self._row_carry_drag_state = None
            self._axis_slide_drag_state = None
            self._step_translate_drag_state = None
            self._ctrl_left_camera_active = False
            if step_carry_follow_state is not None:
                if should_pick and not ctrl_active:
                    self.stop_step_carry()
                elif ctrl_active:
                    self.status_var.set("STEP carry remains active after Ctrl camera navigation.")
                return "break"
            if step_carry_drag_state is not None:
                self._finish_step_carry_drag(step_carry_drag_state)
            elif row_carry_drag_state is not None:
                self._finish_row_carry_drag(row_carry_drag_state)
            elif step_translate_drag_state is not None and not should_pick and not ctrl_active:
                self._finish_step_translate_drag(step_translate_drag_state)
            elif axis_slide_drag_state is not None and not should_pick and not ctrl_active:
                self._finish_axis_slide_drag(axis_slide_drag_state)
            elif thickness_drag_state is not None and not should_pick and not ctrl_active:
                self._finish_thickness_drag(thickness_drag_state)
            elif should_pick and not ctrl_active:
                self._on_left_button_press(None, None)
            elif should_pick and ctrl_active:
                self.status_var.set("Ctrl-click left the 3D selection unchanged.")
            elif placement_drag_state is not None:
                self._finish_placement_drag(placement_drag_state)
            return "break"

        def middle_press(event):
            record_mouse("mouse_press", event, 2)
            set_event_info(event)
            self._cancel_step_carry_hold_timer()
            self._cancel_row_carry_hold_timer()
            self._middle_drag_active = True
            self._middle_drag_last_xy = (int(event.x), int(event.y))
            return "break"

        def middle_motion(event):
            record_mouse("mouse_move", event, 2)
            set_event_info(event)
            if not self._middle_drag_active:
                return "break"
            current = (int(event.x), int(event.y))
            last = self._middle_drag_last_xy or current
            dx = current[0] - last[0]
            dy = current[1] - last[1]
            if dx or dy:
                self._pan_camera_fixed_drag(dx, dy)
            self._middle_drag_last_xy = current
            return "break"

        def middle_release(event):
            record_mouse("mouse_release", event, 2)
            set_event_info(event)
            self._middle_drag_active = False
            self._middle_drag_last_xy = None
            return "break"

        def hover_motion(event):
            # Passive hover (no button held): highlight a thickness-dimension
            # handle under the cursor so it reads as draggable/clickable.
            if self._left_drag_active or self._middle_drag_active:
                return
            try:
                self._update_thickness_hover_highlight(int(event.x), int(event.y))
            except Exception:
                pass

        try:
            self._vtk_widget.bind("<ButtonPress-1>", left_press)
            self._vtk_widget.bind("<B1-Motion>", left_motion)
            self._vtk_widget.bind("<ButtonRelease-1>", left_release)
            self._vtk_widget.bind("<Control-ButtonPress-1>", left_press)
            self._vtk_widget.bind("<Control-B1-Motion>", left_motion)
            self._vtk_widget.bind("<Control-ButtonRelease-1>", left_release)
            self._vtk_widget.bind("<ButtonPress-2>", middle_press)
            self._vtk_widget.bind("<B2-Motion>", middle_motion)
            self._vtk_widget.bind("<ButtonRelease-2>", middle_release)
            self._vtk_widget.bind("<ButtonPress-3>", self._show_surface_function_context_menu)
            self._vtk_widget.bind("<Motion>", hover_motion, add="+")
        except Exception as exc:
            self.editor.append_debug(f"3D mouse binding override failed: {exc}")
