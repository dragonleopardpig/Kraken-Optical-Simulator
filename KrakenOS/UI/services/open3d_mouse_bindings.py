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

    # ------------------------------------------------------------------
    # bugs/0156: route left-clicks to the custom FreeCAD-style navigation cube.
    #
    # The app owns every left-click at the Tk level -- _install_pick_only_left_
    # click_bindings REPLACES the vtkTkRenderWindowInteractor's own button
    # bindings and dispatches a plain pick by calling _on_left_button_press
    # directly, so the interactor's button events never fire. The NavigationCube
    # widget therefore does its own picking: left_press asks it for first refusal
    # (via the inspector's _handle_navigation_cube_left_press) after set_event_info,
    # and the cube consumes the click when the cursor is over its upper-right gizmo
    # (a face/edge/corner snap or a discrete-step arrow). It is a single instant
    # gesture -- no button-held drag/release forwarding is needed.
    # ------------------------------------------------------------------
    def _install_pick_only_left_click_bindings(self) -> None:
        """Left click selects; left drag rotates; middle (or Shift+Left) drag pans the camera."""
        if self._vtk_widget is None:
            return

        # bugs/0323: a left-click select tolerates a little hand jitter before it
        # is treated as a camera orbit. At 4 px a small wobble during the press
        # flipped the click into an orbit (should_pick went false) and abandoned
        # the selection; 8 px keeps ordinary clicks as picks without making a
        # deliberate drag feel sticky.
        drag_threshold_px = 8

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
            # bugs/0323: capture the click-time Alt state so the committed pick
            # honours face-vs-edge intent even if the user released Alt after the
            # last hover motion (the pick fires on release; a click has no motion
            # between, so the press-time modifier is the authoritative read).
            self._edge_pick_alt_active = self._event_alt_pressed(event)
            # bugs/0156: a click over the navigation cube snaps the view (a
            # face/edge/corner orientation) or applies a discrete-step arrow. The
            # cube owns the click, so skip the scene pick/drag entirely.
            if self._handle_navigation_cube_left_press():
                return "break"
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
                self._measure_offset_drag_state = None
                # bugs/0053: Ctrl-click on a dimension arrow toggles a modal
                # re-anchor of its nearer endpoint -- the endpoint then follows the
                # BARE mouse (no button held) and a plain click commits. Ctrl on
                # empty space still orbits the camera.
                if self._dimension_anchor_pick_mode:
                    # Already re-anchoring: keep the mode, don't orbit. The bare
                    # mouse drives it; a plain (non-Ctrl) click commits.
                    self._ctrl_left_camera_active = False
                    self._dimension_anchor_drag_state = self._dimension_anchor_pick_state
                elif self._begin_dimension_anchor_pick_from_current_pick():
                    self._ctrl_left_camera_active = False
                    self._dimension_anchor_drag_state = self._dimension_anchor_pick_state
                else:
                    self._dimension_anchor_drag_state = None
            elif self._dimension_anchor_pick_mode:
                # bugs/0053: a plain click while re-anchoring commits the pick
                # (handled in left_release). Don't arm any drag/carry detector --
                # the click must not also select or carry the surface under it.
                self._dimension_anchor_drag_state = None
                self._step_translate_drag_state = None
                self._axis_slide_drag_state = None
                self._placement_drag_state = None
                self._thickness_drag_state = None
                self._step_carry_drag_state = None
                self._row_carry_drag_state = None
                self._measure_offset_drag_state = None
            elif getattr(self, "_measure_offset_adjust_mode", False):
                # bugs/0115 (CAD-flow step 3): a plain click while adjusting the
                # offset commits it (handled in left_release). Don't arm any
                # drag/carry detector -- the click must not select, carry, or grab
                # the midpoint handle under it.
                self._dimension_anchor_drag_state = None
                self._step_translate_drag_state = None
                self._axis_slide_drag_state = None
                self._placement_drag_state = None
                self._thickness_drag_state = None
                self._step_carry_drag_state = None
                self._row_carry_drag_state = None
                self._measure_offset_drag_state = None
            else:
                self._dimension_anchor_drag_state = None
                # bugs/0115 (Commit 2): a left-press on a dimension midpoint handle
                # grabs that segment's lane standoff for a perpendicular drag; it
                # takes priority over the body-move / thickness drag detectors.
                self._measure_offset_drag_state = self._measure_offset_drag_state_from_current_pick()
                if self._measure_offset_drag_state is not None:
                    self._step_translate_drag_state = None
                    self._axis_slide_drag_state = None
                    self._placement_drag_state = None
                    self._thickness_drag_state = None
                    self._step_carry_drag_state = None
                    self._row_carry_drag_state = None
                    return "break"
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
                if self._dimension_anchor_pick_mode:
                    # bugs/0053: while re-anchoring, a held Ctrl-drag also live-moves
                    # the endpoint (so it works whether or not the user keeps the
                    # button down); this must not fall through to the orbit branch.
                    self._cancel_step_carry_hold_timer()
                    self._apply_dimension_anchor_pick_motion()
                    self._left_drag_last_xy = current
                    return "break"
                if getattr(self, "_measure_offset_adjust_mode", False):
                    # bugs/0115 (CAD-flow step 3): a held drag during offset-adjust
                    # also live-moves the standoff (same as the bare mouse) and must
                    # never fall through to the camera-orbit branch.
                    self._cancel_step_carry_hold_timer()
                    self._cancel_row_carry_hold_timer()
                    self._apply_measure_offset_adjust_motion()
                    self._left_drag_last_xy = current
                    return "break"
                if ctrl_pressed:
                    self._cancel_step_carry_hold_timer()
                    self._ctrl_left_camera_active = True
                    self._rotate_camera_fixed_drag(dx, dy)
                elif self._measure_offset_drag_state is not None:
                    # bugs/0115 (Commit 2): drag the lane handle perpendicular.
                    self._cancel_step_carry_hold_timer()
                    self._cancel_row_carry_hold_timer()
                    self._apply_measure_offset_drag_motion(current)
                    self._left_drag_last_xy = current
                    return "break"
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
            dimension_anchor_was_drag = self._left_drag_active and self._left_drag_moved
            ctrl_active = self._ctrl_left_camera_active or control_pressed(event)
            placement_drag_state = self._placement_drag_state
            thickness_drag_state = self._thickness_drag_state
            step_carry_drag_state = self._step_carry_drag_state
            step_carry_follow_state = self._step_carry_follow_state
            row_carry_drag_state = self._row_carry_drag_state
            axis_slide_drag_state = self._axis_slide_drag_state
            step_translate_drag_state = self._step_translate_drag_state
            dimension_anchor_drag_state = self._dimension_anchor_drag_state
            measure_offset_drag_state = self._measure_offset_drag_state
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
            self._dimension_anchor_drag_state = None
            self._measure_offset_drag_state = None
            self._ctrl_left_camera_active = False
            # bugs/0053: the Ctrl gesture that entered (or kept) the modal
            # re-anchor must NOT commit on release -- the endpoint keeps following
            # the bare mouse until a plain (non-Ctrl) click commits it below.
            if self._dimension_anchor_pick_mode:
                # A drag of the arrow endpoint onto a surface/edge commits on
                # release -- the natural "drag the dimension to point at a face"
                # gesture (Ctrl-drag to enter+move, or a drag after the menu
                # entry). _commit_dimension_anchor_pick cancels cleanly when the
                # release lands over empty space, so this is always safe.
                if dimension_anchor_was_drag:
                    self._commit_dimension_anchor_pick()
                    return "break"
                if dimension_anchor_drag_state is not None or ctrl_active:
                    return "break"
                # A plain click while the mode is active commits the re-anchor.
                if should_pick:
                    self._commit_dimension_anchor_pick()
                    return "break"
                return "break"
            if getattr(self, "_measure_offset_adjust_mode", False):
                # bugs/0115 (CAD-flow step 3): any release (a click, or the end of a
                # drag-adjust) finishes the offset-adjust and keeps the standoff. The
                # release must not also pick/select the surface under the cursor.
                self._finish_measure_offset_adjust()
                return "break"
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
            elif measure_offset_drag_state is not None and not ctrl_active:
                # bugs/0115 (Commit 2): a drag commits the new lane standoff; a bare
                # click on the handle keeps it (don't fall through to a scene pick).
                if not should_pick:
                    self._finish_measure_offset_drag(measure_offset_drag_state)
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

        def double_left_press(event):
            # bugs/0055: double-left-click on the Object/Image plane opens the
            # FOV box (type a horizontal field width; solve thickness or sensor).
            # The first click of the pair still selects the row normally.
            record_mouse("mouse_press", event, 1)
            set_event_info(event)
            try:
                self._maybe_open_fov_popup_from_double_click(event)
            except Exception:
                pass
            return "break"

        def hover_motion(event):
            # bugs/0323: Alt held during hover promotes whole-face highlight to
            # the nearest DRAWN feature edge; plain hover stays whole-face. Record
            # the live modifier here (the passive <Motion> that also drives the
            # VTK-side feature hover) so step_feature_pick_for_display_xy can gate
            # its edge refinement. Set before any early return so orbit/idle frames
            # don't leave a stale mode.
            self._edge_pick_alt_active = self._event_alt_pressed(event)
            # bugs/0323: a bare <Motion> means no button is held, so the right
            # button has been released -- self-heal the freeze flag here in case
            # the <ButtonRelease-3> went to the popped context menu (grab) instead
            # of the widget and never cleared it.
            self._right_button_active = False
            # Passive hover (no button held): highlight a thickness-dimension
            # handle under the cursor so it reads as draggable/clickable.
            if self._left_drag_active or self._middle_drag_active:
                return
            # bugs/0053: while re-anchoring, the bare mouse moves the endpoint;
            # drive the live arrow + snap highlight instead of the resting hover.
            # Push the cursor into the VTK interactor first so the picker reads
            # the live position (bare <Motion> doesn't set it otherwise).
            if self._dimension_anchor_pick_mode:
                set_event_info(event)
                try:
                    self._apply_dimension_anchor_pick_motion()
                except Exception:
                    pass
                return
            # bugs/0115 (CAD-flow step 3): after the 2nd Measure click the bare
            # mouse moves the new dimension's offset (resize cursor) until a plain
            # click finishes; drive it the same bare-mouse way as the re-anchor.
            if getattr(self, "_measure_offset_adjust_mode", False):
                set_event_info(event)
                try:
                    self._apply_measure_offset_adjust_motion()
                except Exception:
                    pass
                return
            # bugs/0250: highlight the navigation-cube facet (face/edge/corner) under the
            # cursor. Push the live cursor into the interactor first (like left_press), then
            # ask the cube; if it's highlighting, the pointer is over the cube -- skip the
            # scene's thickness-handle hover. Otherwise clear any cube highlight and fall
            # through to the normal scene hover.
            try:
                set_event_info(event)
                if self._handle_navigation_cube_hover():
                    return
                self._clear_navigation_cube_hover()
            except Exception:
                pass
            try:
                self._update_thickness_hover_highlight(int(event.x), int(event.y))
            except Exception:
                pass

        def right_press(event):
            # bugs/0323: freeze the scene hover the instant the right button goes
            # down so the highlight the context menu is about to act on cannot be
            # re-picked away by a tiny press-time wobble. The flag self-heals on
            # the next bare <Motion> (see hover_motion) since a grabbed menu can
            # swallow the matching <ButtonRelease-3>.
            self._right_button_active = True
            record_mouse("mouse_press", event, 3)
            return self._show_surface_function_context_menu(event)

        def right_motion(event):
            # Swallow right-drag: without this the unbound <B3-Motion> falls to
            # the VTK interactor default, which re-hovers and drops the highlight.
            return "break"

        def right_release(event):
            self._right_button_active = False

        try:
            self._vtk_widget.bind("<ButtonPress-1>", left_press)
            self._vtk_widget.bind("<B1-Motion>", left_motion)
            self._vtk_widget.bind("<ButtonRelease-1>", left_release)
            self._vtk_widget.bind("<Double-Button-1>", double_left_press)
            self._vtk_widget.bind("<Control-ButtonPress-1>", left_press)
            self._vtk_widget.bind("<Control-B1-Motion>", left_motion)
            self._vtk_widget.bind("<Control-ButtonRelease-1>", left_release)
            self._vtk_widget.bind("<ButtonPress-2>", middle_press)
            self._vtk_widget.bind("<B2-Motion>", middle_motion)
            self._vtk_widget.bind("<ButtonRelease-2>", middle_release)
            # Touchpad-friendly pan: Shift+Left drag mirrors the middle-button
            # pan so laptop users without a middle button (or three-finger
            # gesture) can still slide the scene. Reuses the middle handlers so
            # the behavior is identical; the Shift modifier keeps it distinct
            # from plain left-drag rotate / left-click pick.
            self._vtk_widget.bind("<Shift-ButtonPress-1>", middle_press)
            self._vtk_widget.bind("<Shift-B1-Motion>", middle_motion)
            self._vtk_widget.bind("<Shift-ButtonRelease-1>", middle_release)
            self._vtk_widget.bind("<ButtonPress-3>", right_press)
            self._vtk_widget.bind("<B3-Motion>", right_motion)
            self._vtk_widget.bind("<ButtonRelease-3>", right_release)
            self._vtk_widget.bind("<Motion>", hover_motion, add="+")
        except Exception as exc:
            self.editor.append_debug(f"3D mouse binding override failed: {exc}")
