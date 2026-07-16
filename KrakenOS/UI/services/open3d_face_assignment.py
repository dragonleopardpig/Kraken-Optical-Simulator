"""Open 3D face-assignment context menu service."""

from __future__ import annotations

from typing import Any

import tkinter as tk

import numpy as np


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


class Open3DFaceAssignmentService:
    """Handle Open 3D right-click face-function assignment workflows."""

    def __init__(self, inspector: Any) -> None:
        object.__setattr__(self, "_inspector", inspector)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inspector, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_inspector":
            object.__setattr__(self, name, value)
            return
        setattr(self._inspector, name, value)

    def _show_surface_function_context_menu(self, event) -> str:
        le = _layout_module()
        STEP_OVERLAY_LABEL_SET = le.STEP_OVERLAY_LABEL_SET
        _short_error_message = le._short_error_message
        _optical_solid_face_function_display = le._optical_solid_face_function_display
        # bugs/0108: right-clicking a manual measurement opens its menu (delete /
        # hide this / show all). The measure overlays are PickableOff, so this
        # resolves by screen-space proximity; claim it before the face menus.
        try:
            if self._maybe_show_measure_menu(event):
                return "break"
        except Exception:
            pass
        # Right-clicking a blue Thickness dimension arrow opens its overlay menu
        # (turn off / re-anchor to a surface-edge / Quick Estimation role). This
        # claims the arrow before the QE-role menu, which still handles the
        # Object/Image plane bodies and branch detectors.
        try:
            if self._maybe_show_thickness_dimension_menu(event):
                return "break"
        except Exception:
            pass
        # Quick Estimation: right-clicking a conjugate thickness handle assigns
        # its role (Independent / Dependent / Constant) instead of a CAD face.
        try:
            if self._maybe_show_quick_estimation_role_menu(event):
                return "break"
        except Exception:
            pass
        context = self._right_click_pick_context(event)
        if context is None:
            self._debug_trace(
                "right_click_no_context",
                x=getattr(event, "x", None),
                y=getattr(event, "y", None),
                counts=self._debug_actor_counts(),
                modes=self._debug_mode_state(),
            )
            self.status_var.set("Right-click a CAD/STL optical face to assign its surface function.")
            return "break"
        row_index = context.get("row_index")
        step_label = str(context.get("step_label") or "").strip().lower()
        point = np.asarray(context.get("point_world", ()), dtype=float).reshape(-1)
        normal = context.get("normal_world")
        self._debug_trace(
            "right_click_context",
            x=getattr(event, "x", None),
            y=getattr(event, "y", None),
            row_index=row_index,
            step_label=step_label or None,
            actor_key=context.get("actor_key"),
            cell_id=context.get("cell_id"),
            point_world=self._debug_vector(point),
            normal_world=self._debug_vector(normal),
            counts=self._debug_actor_counts(),
            modes=self._debug_mode_state(),
        )
        if row_index is None and step_label not in STEP_OVERLAY_LABEL_SET:
            self.status_var.set("Right-click assignment is available on optical CAD/STL rows or imported STEP bodies.")
            return "break"
        if point.size < 3 or not np.all(np.isfinite(point[:3])):
            self.status_var.set("Could not resolve the picked CAD/STL face point.")
            return "break"

        menu = tk.Menu(self, tearoff=False)
        title = ""
        face_id = ""
        cell_id = int(context.get("cell_id", -1))
        if row_index is not None and self.editor._file_backed_stl_row_at(int(row_index)) is not None:
            try:
                through_pick = self._row_face_ray_pick_for_display_xy(int(row_index), context.get("display_xy"))
                if through_pick is not None:
                    face = through_pick.face
                    point = np.asarray(through_pick.point_world, dtype=float).reshape(3)
                    normal = np.asarray(through_pick.normal_world, dtype=float).reshape(3)
                    face_lookup_method = "display_ray_internal" if through_pick.internal else "display_ray_face"
                else:
                    face = self.editor.optical_solid_face_record_for_mesh_cell(int(row_index), cell_id)
                    face_lookup_method = "mesh_cell_triangle"
                if face is None:
                    face = self.editor.optical_solid_face_record_at_world_point(
                        int(row_index),
                        point[:3],
                        normal_world=normal,
                        assigned_only=False,
                    )
                    face_lookup_method = "point_normal"
            except Exception as exc:
                self.status_var.set(f"CAD/STL face lookup failed: {_short_error_message(exc)}")
                self.editor.append_debug(f"Open 3D right-click face lookup failed: {exc}")
                return "break"
            trace_hit = self._traced_row_face_hit_near_display_xy(int(row_index), context.get("display_xy"))
            trace_face_id = str((trace_hit or {}).get("face_id", "") or "").strip()
            if trace_face_id:
                traced_face = trace_hit.get("face") if isinstance(trace_hit, dict) else None
                if isinstance(traced_face, dict):
                    face = traced_face
                face_id = trace_face_id
                point = np.asarray(trace_hit.get("point_world", point[:3]), dtype=float).reshape(3)
                trace_normal = trace_hit.get("normal_world")
                if trace_normal is not None:
                    try:
                        normal_candidate = np.asarray(trace_normal, dtype=float).reshape(-1)[:3]
                        if normal_candidate.size >= 3 and np.all(np.isfinite(normal_candidate[:3])):
                            normal = normal_candidate[:3]
                    except Exception:
                        pass
                face_lookup_method = f"{face_lookup_method}+trace_event"
            if face is not None and not trace_face_id:
                face_id = str(face.get("face_id", "") or "").strip()
            self._debug_trace(
                "right_click_face_match",
                row_index=int(row_index),
                face_id=face_id or None,
                lookup_method=face_lookup_method,
                cell_id=cell_id,
                through_body=face_lookup_method.startswith("display_ray"),
                trace_face_id=trace_face_id or None,
                trace_distance_px=round(float(trace_hit.get("distance_px", 0.0)), 3) if isinstance(trace_hit, dict) else None,
                face_function=_optical_solid_face_function_display(face.get("function"), legacy_role=face.get("role")) if face is not None else None,
                face_role=face.get("role") if face is not None else None,
                face_port_role=face.get("port_role") if face is not None else None,
            )
            try:
                feature = context.get("feature")
                actor_key = str(context.get("actor_key") or "")
                if feature is not None and actor_key:
                    outline = self._hover_overlay_for_row_face(int(row_index), face) if face is not None else None
                    if outline is None:
                        outline = self._hover_overlay_for_feature(feature[0], feature[1])
                    self._set_step_hover_outline(outline, ("row", actor_key, cell_id))
            except Exception:
                pass
            title = f"S{int(row_index)} {face_id or 'picked face'}"
            menu.add_command(label=title, state="disabled")
            for label in self._open3d_surface_function_menu_items():
                menu.add_command(
                    label=f"Set {label}",
                    command=lambda value=label, idx=int(row_index), picked_face_id=face_id, picked_point=point[:3].copy(), picked_normal=normal: self._assign_row_face_function_from_context(
                        idx,
                        picked_point,
                        picked_normal,
                        value,
                        face_id=picked_face_id,
                    ),
                )
            menu.add_command(
                label="Set as Illumination Source",
                command=lambda idx=int(row_index), picked_face_id=face_id, picked_point=point[:3].copy(), picked_normal=normal: self._assign_row_face_illumination_from_context(
                    idx,
                    picked_point,
                    picked_normal,
                    face_id=picked_face_id,
                ),
            )
            menu.add_separator()
            self.append_element_context_actions(menu, row_index=int(row_index))
        elif row_index is not None and self.editor._is_any_promoted_optical_solid_row(self.editor.rows[int(row_index)]):
            group = self.editor._lens_row_group_for_row(int(row_index))
            label_text = (
                f"Lens (S{group[0]}-S{group[-1]})" if len(group) >= 2 else f"S{int(row_index)}"
            )
            menu.add_command(label=f"Row Actions for {label_text}", state="disabled")
            menu.add_separator()
            self.append_element_context_actions(menu, row_index=int(row_index))
        elif step_label in STEP_OVERLAY_LABEL_SET:
            try:
                feature_pick = self._step_feature_pick_for_display_xy(
                    step_label,
                    context.get("display_xy"),
                    actor=context.get("actor"),
                    actor_key=str(context.get("actor_key") or "") or None,
                    cell_id=cell_id,
                )
                through_pick = feature_pick.get("through_pick") if isinstance(feature_pick, dict) else None
                if through_pick is not None:
                    face = through_pick.face
                    point = np.asarray(through_pick.point_world, dtype=float).reshape(3)
                    normal = np.asarray(through_pick.normal_world, dtype=float).reshape(3)
                    face_lookup_method = "display_feature_internal" if through_pick.internal else "display_feature_face"
                else:
                    through_pick = self._step_face_ray_pick_for_display_xy(step_label, context.get("display_xy"))
                    if through_pick is not None:
                        face = through_pick.face
                        point = np.asarray(through_pick.point_world, dtype=float).reshape(3)
                        normal = np.asarray(through_pick.normal_world, dtype=float).reshape(3)
                        face_lookup_method = "display_ray_internal" if through_pick.internal else "display_ray_face"
                    else:
                        face = None
                        face_lookup_method = "mesh_cell_or_point"
                if face is None:
                    face = self.editor.optical_solid_step_overlay_face_record_at_world_point(
                        step_label,
                        point[:3],
                        normal_world=normal,
                        cell_id=cell_id,
                    )
            except Exception as exc:
                self.status_var.set(f"Imported STEP face lookup failed: {_short_error_message(exc)}")
                self.editor.append_debug(f"Open 3D imported STEP face lookup failed: {exc}")
                face = None
                face_lookup_method = "failed"
            face_center = np.asarray(point, dtype=float).reshape(3)
            if face is not None:
                face_id = str(face.get("face_id", "") or "").strip()
                # bugs/0120: "Center Picked Face -> Optical Axis" must bring the
                # window's CENTRE to the axis, not wherever the cursor happened to
                # land on the face. Resolve the face centroid (world) from the pick;
                # fall back to the raw click point if no centroid is available.
                if through_pick is not None:
                    try:
                        face_center = np.asarray(
                            self._surface_center_from_face_ray_pick(through_pick), dtype=float
                        ).reshape(3)
                    except Exception:
                        face_center = np.asarray(point, dtype=float).reshape(3)
                else:
                    try:
                        candidate = np.asarray(face.get("centroid_world"), dtype=float).reshape(-1)[:3]
                    except Exception:
                        candidate = np.asarray([], dtype=float)
                    if candidate.size >= 3 and np.all(np.isfinite(candidate[:3])):
                        face_center = candidate[:3]
            self._debug_trace(
                "right_click_step_face_match",
                label=step_label,
                face_id=face_id or None,
                cell_id=cell_id,
                lookup_method=face_lookup_method,
                through_body=face_lookup_method.startswith("display_ray"),
                face_function=_optical_solid_face_function_display(face.get("function"), legacy_role=face.get("role")) if face is not None else None,
                face_role=face.get("role") if face is not None else None,
                face_port_role=face.get("port_role") if face is not None else None,
            )
            try:
                if face is not None:
                    outline = self._hover_overlay_for_step_face(step_label, face)
                    self._set_step_hover_outline(outline, ("step", step_label, face_id or cell_id))
            except Exception:
                pass
            display = self.editor._step_overlay_display_label(step_label).upper()
            decoration = le.is_step_overlay_decoration(step_label)
            title = f"{display} STEP {face_id or 'picked face'}"
            menu.add_command(label=title, state="disabled")
            if decoration:
                # A camera body / LED source is a decoration, not an optical
                # element: promoting it or assigning a surface function would,
                # e.g., turn the LED into a 160-face "beam splitter" and stall
                # the non-seq trace. Offer Hide so the user can clear the
                # decoration off the optical solid it overlaps before assigning.
                menu.add_command(
                    label=f"{display} STEP is a decoration (not an optical element)",
                    state="disabled",
                )
                menu.add_command(
                    label=f"Hide {display} STEP",
                    command=lambda picked_label=step_label: self._hide_step_overlay_from_context(picked_label),
                )
            else:
                for label in self._open3d_surface_function_menu_items():
                    menu.add_command(
                        label=f"Promote and set {label}",
                        command=lambda value=label, picked_label=step_label, picked_face_id=face_id, picked_point=point[:3].copy(), picked_normal=normal: self._promote_step_and_assign_face_function(
                            picked_label,
                            picked_point,
                            picked_normal,
                            value,
                            face_id=picked_face_id,
                        ),
                    )
            menu.add_separator()
            menu.add_command(
                label="Center Picked Face -> Optical Axis",
                command=lambda picked_label=step_label, picked_center=face_center[:3].copy(): self._center_step_face_to_optical_axis_from_context(
                    picked_label, picked_center
                ),
            )
            # bugs/0134: a dedicated clear-aperture pick. The coarse face pick above
            # grabs whatever planar cluster the cursor lands on (often a housing
            # face, not the CA window); this arms a one-click fine-face pick whose
            # hover highlights the CA edge precisely, then persists it.
            menu.add_command(
                label="Set Clear Aperture (pick window face)...",
                command=lambda picked_label=step_label: self.start_step_clear_aperture_pick(picked_label),
            )
            if self.editor.step_clear_aperture(step_label) is not None:
                menu.add_command(
                    label="Center Clear Aperture -> Optical Axis",
                    command=lambda picked_label=step_label: self._center_clear_aperture_from_context(picked_label),
                )
                menu.add_command(
                    label="Forget Clear Aperture",
                    command=lambda picked_label=step_label: self._clear_clear_aperture_from_context(picked_label),
                )
            self.append_element_context_actions(menu, step_label=step_label)
        else:
            self.status_var.set("Right-click assignment requires a file-backed optical CAD/STL row.")
            return "break"

        try:
            menu.tk_popup(int(event.x_root), int(event.y_root))
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass
        return "break"

    def append_element_context_actions(self, menu, *, row_index=None, step_label=None) -> bool:
        """Append the *element-level* right-click actions -- the ones keyed only by
        the element's identity (a row index or a STEP-overlay label), never by a
        picked face. Shared by the 3D-canvas right-click menu and the Scene
        Components tree right-click so the two stay in sync. The tree path uses it
        to offer the same CAD actions without the canvas's per-pixel face pick
        (which is slow and ambiguous when bodies overlap -- bugs/0102). Face-
        specific actions ("Set {function}", "Center Picked Face") stay canvas-only;
        the tree reaches face assignment through "Open Face Editor...". Returns
        True when it added at least one command."""
        le = _layout_module()
        if step_label is not None:
            step_label = str(step_label).strip().lower()
            if step_label not in le.STEP_OVERLAY_LABEL_SET:
                return False
            decoration = le.is_step_overlay_decoration(step_label)
            menu.add_command(
                label=self._step_surrogate_reset_label(step_label),
                command=lambda picked_label=step_label: self._glue_step_to_surrogate_from_context(picked_label),
            )
            # Item 3: BS<->LED two-body glue. The UNGLUE control must stay reachable
            # whenever a glue is ACTIVE -- including after the beam splitter ("optical")
            # overlay was promoted away, which used to hide it and leave the glue stuck
            # on (bugs/0103). The LED is a decoration (never promoted, bugs/0101), so its
            # overlay is a stable anchor for unglue. Only the GLUE direction needs both
            # overlays still imported as overlays.
            if step_label in ("optical", "led"):
                if self.editor.optical_led_glued():
                    menu.add_command(label="Unglue BS from LED", command=lambda: self._set_optical_led_glue(False))
                elif self._optical_led_glue_available():
                    menu.add_command(label="Glue BS to LED (move together)", command=lambda: self._set_optical_led_glue(True))
            menu.add_separator()
            menu.add_command(
                label="Resize Solid...",
                command=lambda picked_label=step_label: self._open_step_overlay_resize_popup(picked_label),
            )
            # bugs/0319: one-click "Add Beam Splitter to LED". Only on the LED overlay --
            # it generates a parametric BS, centres it on the LED clear-aperture opening,
            # glues, promotes, and auto-flags the 45-degree diagonal coating.
            # bugs/0320: these are DIRECT commands, not an "... > Cube/Plate" cascade. In
            # the VTK-embedded 3D inspector the render-window interactor competes for the
            # pointer, so a cascade's submenu often never posts on hover -- the user clicks
            # the parent label, nothing opens, nothing fires, no status line (exactly the
            # 07:47 recording). A single-click command needs no hover-to-post and fires
            # reliably -- the same reason the direct "Hide <STEP>" items always worked in
            # this menu. (The 2D main table's cascades are fine; there is no VTK there.)
            if step_label == "led":
                menu.add_command(
                    label="Add Beam Splitter to LED (Cube)",
                    command=lambda: self._add_beam_splitter_to_led_from_context("cube"),
                )
                menu.add_command(
                    label="Add Beam Splitter to LED (Plate)",
                    command=lambda: self._add_beam_splitter_to_led_from_context("plate"),
                )
            if not decoration:
                menu.add_command(
                    label="Promote to Optical Element",
                    command=lambda picked_label=step_label: self._promote_step_from_context(picked_label),
                )
            return True
        if row_index is not None:
            row_index = int(row_index)
            rows = list(getattr(self.editor, "rows", []) or [])
            if not (0 <= row_index < len(rows)):
                return False
            if self.editor._file_backed_stl_row_at(row_index) is not None:
                menu.add_command(
                    label="Open Face Editor...",
                    command=lambda idx=row_index: self.editor.open_optical_solid_face_role_editor(idx),
                )
                if self._row_has_step_overlay_promotion(row_index):
                    menu.add_command(
                        label="Unpromote to STEP overlay",
                        command=lambda idx=row_index: self._unpromote_step_solid_from_context(idx),
                    )
                if self._row_is_glued_optical_bs(row_index):
                    menu.add_command(label="Unglue BS from LED", command=lambda: self._set_optical_led_glue(False))
                elif self._row_is_glueable_optical_bs(row_index):
                    menu.add_command(label="Glue BS to LED (move together)", command=lambda: self._set_optical_led_glue(True))
                menu.add_separator()
                self._build_row_actions_cascade(menu, row_index)
                return True
            if self.editor._is_any_promoted_optical_solid_row(rows[row_index]):
                if self._row_has_step_overlay_promotion(row_index):
                    menu.add_command(
                        label="Unpromote to STEP overlay",
                        command=lambda idx=row_index: self._unpromote_step_solid_from_context(idx),
                    )
                    menu.add_separator()
                if self._row_is_glued_optical_bs(row_index):
                    menu.add_command(label="Unglue BS from LED", command=lambda: self._set_optical_led_glue(False))
                    menu.add_separator()
                elif self._row_is_glueable_optical_bs(row_index):
                    menu.add_command(label="Glue BS to LED (move together)", command=lambda: self._set_optical_led_glue(True))
                    menu.add_separator()
                self._build_row_actions_cascade(menu, row_index)
                return True
        return False

    def _assign_row_face_function_from_context(
        self,
        row_index: int,
        point_world,
        normal_world,
        function_label: str,
        *,
        face_id: str = "",
    ) -> None:
        le = _layout_module()
        STEP_OVERLAY_LABEL_SET = le.STEP_OVERLAY_LABEL_SET
        _short_error_message = le._short_error_message
        _optical_solid_face_function_display = le._optical_solid_face_function_display
        refresh_sampling_mode = self._active_refresh_sampling_mode()
        face_id = str(face_id or "").strip()
        self._debug_trace(
            "face_assignment_start",
            row_index=int(row_index),
            face_id=face_id or None,
            function_label=function_label,
            point_world=self._debug_vector(point_world),
            normal_world=self._debug_vector(normal_world),
            counts_before=self._debug_actor_counts(),
        )
        try:
            if face_id:
                result = self.editor.assign_optical_solid_face_function(
                    int(row_index),
                    face_id,
                    function_label,
                    direct_context=True,
                )
            else:
                result = self.editor.assign_optical_solid_face_function_at_world_point(
                    int(row_index),
                    point_world,
                    function_label,
                    normal_world=normal_world,
                    direct_context=True,
                )
        except Exception as exc:
            self.status_var.set(f"Face assignment failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Open 3D face assignment failed: {exc}")
            self._debug_trace(
                "face_assignment_failed",
                row_index=int(row_index),
                face_id=face_id or None,
                error=_short_error_message(exc),
            )
            return
        face_id = str(result.get("face_id", "") or "picked face")
        display = str(result.get("function_display", function_label) or function_label)
        self.editor._select_table_row(int(row_index))
        self._stl_placement_dirty = True
        self._debug_trace(
            "face_assignment_metadata_saved",
            row_index=int(row_index),
            face_id=face_id,
            function_display=display,
            metadata=self._debug_face_metadata_summary(result.get("metadata")),
        )
        message = f"S{int(row_index)} {face_id}: set {display}. Rebuilt trace with assigned-face overlay."
        try:
            self.refresh_from_editor(sampling_mode=refresh_sampling_mode, force_retrace=True)
            self.highlight_row(int(row_index))
        except Exception as exc:
            self.editor.append_debug(f"Open 3D refresh after face assignment failed: {exc}")
            self._debug_trace("face_assignment_refresh_failed", row_index=int(row_index), face_id=face_id, error=_short_error_message(exc))
        self._debug_trace(
            "face_assignment_done",
            row_index=int(row_index),
            face_id=face_id,
            function_display=display,
            counts_after=self._debug_actor_counts(),
        )
        self.status_var.set(message)

    def _assign_row_face_illumination_from_context(
        self,
        row_index: int,
        point_world,
        normal_world,
        *,
        face_id: str = "",
    ) -> None:
        """Right-click "Set as Illumination Source": bind a face-anchored illumination emitter to the
        picked CAD/STL face and retrace so the "Illum rays" overlay lights up. A raw (unassigned) face
        has no world-anchor record yet, so register it with the default face function first, then bind."""
        le = _layout_module()
        _short_error_message = le._short_error_message
        refresh_sampling_mode = self._active_refresh_sampling_mode()
        face_id = str(face_id or "").strip()
        try:
            source_id = self.editor.create_illumination_source_at_face(
                int(row_index),
                face_id=face_id,
                point_world=point_world,
                normal_world=normal_world,
            )
            if not source_id:
                assigned = self.editor.assign_optical_solid_face_function_at_world_point(
                    int(row_index),
                    point_world,
                    le.OPTICAL_SOLID_FACE_FUNCTION_DEFAULT,
                    normal_world=normal_world,
                    direct_context=True,
                )
                resolved_face_id = str((assigned or {}).get("face_id", "") or face_id).strip()
                source_id = self.editor.create_illumination_source_at_face(
                    int(row_index),
                    face_id=resolved_face_id,
                    point_world=point_world,
                    normal_world=normal_world,
                )
        except Exception as exc:
            self.status_var.set(f"Set as Illumination Source failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Open 3D illumination-source bind failed: {exc}")
            return
        if not source_id:
            self.status_var.set(f"S{int(row_index)}: could not bind an illumination source to that face.")
            return
        self.editor._select_table_row(int(row_index))
        self._stl_placement_dirty = True
        try:
            self.refresh_from_editor(sampling_mode=refresh_sampling_mode, force_retrace=True)
            self.highlight_row(int(row_index))
        except Exception as exc:
            self.editor.append_debug(f"Open 3D refresh after illumination bind failed: {exc}")
        self.status_var.set(
            f"S{int(row_index)}: bound illumination source {source_id}. Toggle 'Illum rays' to see the emission."
        )

    def _hide_step_overlay_from_context(self, label: str) -> None:
        """Hide a decoration STEP overlay (LED source / camera body) from the
        right-click menu -- e.g. to clear it off an overlapping optical solid
        before assigning faces. While hidden the heavy CAD is skipped in the
        rebuild, so this also removes it from the trace/refresh cost."""
        label = str(label).strip().lower()
        display = self.editor._step_overlay_display_label(label).upper()
        try:
            self.set_step_label_hidden(label, True)
        except Exception as exc:
            self.editor.append_debug(f"Open 3D hide {label} STEP failed: {exc}")
            self.status_var.set(f"Could not hide {display} STEP.")
            return
        self._debug_trace("hide_step_overlay_from_context", label=label)
        self.status_var.set(f"Hid {display} STEP. Re-show it from the Scene Components panel.")

    def _promote_step_from_context(self, label: str) -> None:
        le = _layout_module()
        STEP_OVERLAY_LABEL_SET = le.STEP_OVERLAY_LABEL_SET
        _short_error_message = le._short_error_message
        _optical_solid_face_function_display = le._optical_solid_face_function_display
        label = str(label).strip().lower()
        if le.is_step_overlay_decoration(label):
            display = self.editor._step_overlay_display_label(label).upper()
            self.status_var.set(
                f"{display} STEP is a decoration and cannot be promoted to an optical element."
            )
            self._debug_trace("promote_step_from_context_decoration_blocked", label=label)
            return
        self.editor.select_step_component(label)
        self._debug_trace("promote_step_from_context", label=label, counts_before=self._debug_actor_counts())
        self.promote_selected_step_to_optical_solid_row()

    def _add_beam_splitter_to_led_from_context(self, kind: str) -> None:
        """Right-click "Add Beam Splitter to LED (Cube/Plate)" (bugs/0319): run the
        one-click pipeline (generate BS -> overlay -> centre on the LED clear-aperture
        opening -> glue -> promote -> auto-flag the diagonal coating).

        bugs/0322 -- "right click add BS cube still shows nothing": every outcome of the
        command (success, graceful stop, exception) is reported ONLY on the editor's
        main-window status bar (`editor.status_var`). But the user is looking at the 3D
        inspector Toplevel, whose own visible bar is `self.status_var` (the service proxies
        attribute access to the inspector). So a graceful stop -- e.g. no clear-aperture
        opening -- or an error read as "nothing happened": no BS AND no message. Mirror the
        command's own message onto the VISIBLE inspector bar so the click is never silent."""
        _short_error_message = _layout_module()._short_error_message
        try:
            result = self.editor.add_beam_splitter_to_led(str(kind))
        except Exception as exc:
            self.editor.append_debug(f"Add Beam Splitter to LED ({kind}) failed: {exc}")
            self._set_inspector_status(f"Add Beam Splitter to LED failed: {_short_error_message(exc)}")
            return
        # The command narrates on `editor.status_var` (main window). Read that back and
        # echo it to the inspector's visible bar; fall back to a computed line if empty.
        message = ""
        try:
            message = str(self.editor.status_var.get() or "").strip()
        except Exception:
            message = ""
        if not message:
            message = (
                f"Added {kind} beam splitter to the LED (S{result.get('row_index')})."
                if isinstance(result, dict)
                else "Add Beam Splitter to LED: nothing was added (no clear-aperture opening found)."
            )
        if result is None:
            self.editor.append_debug(f"Add Beam Splitter to LED ({kind}) added nothing: {message}")
        self._set_inspector_status(message)

    def _set_inspector_status(self, message: str) -> None:
        """Show ``message`` on the 3D-inspector's OWN status bar (the visible one in the
        Toplevel). `self.status_var` proxies through to the inspector, unlike
        `self.editor.status_var`, which is the main window's bar hidden behind it (0322)."""
        try:
            self.status_var.set(str(message))
        except Exception:
            pass

    def _row_has_step_overlay_promotion(self, row_index: int) -> bool:
        """bugs/0093: a promoted optical-solid row that came from a STEP overlay (so
        it can be reverted to a decorative overlay via the right-click 'Unpromote')."""
        try:
            advanced = getattr(self.editor.rows[int(row_index)], "advanced", {}) or {}
        except Exception:
            return False
        return isinstance(advanced, dict) and isinstance(advanced.get("StepOverlayPromotion"), dict)

    def _unpromote_step_solid_from_context(self, row_index: int) -> None:
        """Right-click "Unpromote to STEP overlay": revert the promoted optical solid
        back to an imported STEP overlay at its current pose (bugs/0093)."""
        try:
            self.editor.unpromote_optical_solid_to_overlay(int(row_index))
        except Exception as exc:
            self.editor.append_debug(f"Unpromote of S{row_index} failed: {exc}")
            try:
                self.editor.status_var.set(f"Unpromote failed: {exc}")
            except Exception:
                pass

    @staticmethod
    def _step_surrogate_reset_label(step_label: str) -> str:
        """The "Glue STEP to Surrogate" action actually RESETS an overlay to its
        automatic optical station (zeroes the drag offsets); it is NOT the two-body
        BS<->LED glue. Give it an action-accurate, per-element label so it never reads
        as a second "Glue ..." item beside "Glue BS to LED" (bugs/0127)."""
        return {
            "led": "Reset LED to Object Station",
            "camera": "Reset Camera to Image Plane",
            "optical": "Reset BS to Auto Placement",
        }.get(str(step_label or "").strip().lower(), "Glue STEP to Surrogate")

    def _glue_step_to_surrogate_from_context(self, label: str) -> None:
        """Right-click surrogate reset: select the clicked overlay and re-apply its
        automatic optical-surrogate placement (bugs/0077 lens centring etc.)."""
        self.editor.select_step_component(label)
        self._debug_trace("glue_step_to_surrogate_from_context", label=label)
        self.glue_selected_step_to_surrogate()

    def _optical_led_glue_available(self) -> bool:
        """Item 3: the LED overlay plus a beam-splitter BODY (the 'optical' overlay OR a
        promoted optical solid) are present, so the two-body glue is meaningful. After the
        BS is promoted its overlay is gone, but the promoted solid row is still a valid glue
        partner -- without this the glue item vanished and the user got funnelled into the
        misnamed surrogate reset (bugs/0127)."""
        try:
            if self.editor._step_path_for_label("led") is None:
                return False
            if self.editor._step_path_for_label("optical") is not None:
                return True
            return self.editor._promoted_optical_solid_row_index("optical") is not None
        except Exception:
            return False

    def _row_is_glued_optical_bs(self, row_index: int) -> bool:
        """bugs/0103: True when this promoted row IS the beam splitter (the 'optical'
        overlay that was promoted) and it is currently glued to the LED. Lets the
        promoted-row right-click offer "Unglue BS from LED" even though the 'optical'
        overlay no longer exists -- the user looks for unglue where they last saw the
        body (the promoted solid), not only on the LED overlay."""
        try:
            if not self.editor.optical_led_glued():
                return False
            rows = list(getattr(self.editor, "rows", []) or [])
            if not (0 <= int(row_index) < len(rows)):
                return False
            row = rows[int(row_index)]
            if not self.editor._is_open3d_promoted_optical_solid_row(row):
                return False
            label = str(self.editor._open3d_step_label_for_optical_solid_row(row) or "").strip().lower()
            return label == "optical"
        except Exception:
            return False

    def _row_is_glueable_optical_bs(self, row_index: int) -> bool:
        """bugs/0127: True when this promoted row IS the beam splitter and an LED overlay
        is present to glue it to, but they are not glued yet -- so the promoted-row
        right-click can offer "Glue BS to LED" where the user sees the body, not only on
        the LED overlay."""
        try:
            if self.editor.optical_led_glued():
                return False
            if self.editor._promoted_optical_solid_row_index("optical") != int(row_index):
                return False
            return self.editor._step_path_for_label("led") is not None
        except Exception:
            return False

    def _set_optical_led_glue(self, glued: bool) -> None:
        """Right-click "Glue/Unglue BS to LED": glue the beam-splitter (optical) STEP to the LED STEP
        so they move as one rigid unit (item 3)."""
        try:
            changed = bool(self.editor.set_optical_led_glue(bool(glued)))
        except Exception as exc:
            self.status_var.set(f"Glue BS to LED failed: {exc}")
            return
        try:
            self.status_var.set(self.editor.status_var.get())
        except Exception:
            pass
        if changed:
            try:
                self.refresh_from_editor()
            except Exception:
                pass

    def _center_step_face_to_optical_axis_from_context(self, label: str, face_center_world) -> None:
        """Right-click "Center Picked Face -> Optical Axis": translate the picked
        STEP face's CENTROID onto the GLOBAL optical axis -- one click,
        TRANSLATE-ONLY (no rotation), so a "window" stays square while it slides
        onto the axis (bugs/0119). The normal-aligning snap still lives in the top
        STEP menu; users who right-clicked a face and reached for the only axis
        item kept getting an unwanted tilt.

        bugs/0120: the caller now hands us the face centroid (not the raw cursor
        hit), and the editor centre targets the global x=0/y=0 axis (not the
        nearest traced ray), so the window's centre actually comes to rest on the
        axis. Delegates to the tested editor centre (axis_frame=None -> global
        axis)."""
        le = _layout_module()
        _short_error_message = le._short_error_message
        label = str(label).strip().lower()
        self._debug_trace(
            "center_step_face_to_optical_axis_from_context",
            label=label,
            point_world=self._debug_vector(face_center_world),
        )
        try:
            result = self.editor.center_step_feature_on_optical_axis(label, face_center_world)
        except Exception as exc:
            self.status_var.set(f"Center face -> Optical Axis failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Open 3D right-click face->axis center failed: {exc}")
            return
        if result is None:
            self.status_var.set(self.editor.status_var.get())
            return
        # Clear the STEP selection so the post-center refresh does not re-add the
        # rotation handles (same guard as the snap path in open3d_inspector).
        try:
            self.editor._selected_step_label = None
        except Exception:
            pass
        try:
            self.refresh_from_editor(force_retrace=True)
        except Exception as exc:
            self.editor.append_debug(f"Open 3D face->axis center refresh failed: {exc}")

    def _center_clear_aperture_from_context(self, label: str) -> None:
        """Right-click "Center Clear Aperture -> Optical Axis": translate the body
        so its PERSISTED clear-aperture window centre lands on the global optical
        axis. Translate-only, reusing the same tested centre as the picked-face
        path -- the difference is the centre comes from the stored CA face, so the
        user need not re-pick the window every time (bugs/0134)."""
        le = _layout_module()
        _short_error_message = le._short_error_message
        label = str(label).strip().lower()
        try:
            result = self.editor.center_clear_aperture_on_optical_axis(label)
        except Exception as exc:
            self.status_var.set(f"Center Clear Aperture -> Optical Axis failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Open 3D clear-aperture center failed: {exc}")
            return
        if result is None:
            self.status_var.set(self.editor.status_var.get())
            return
        try:
            self.editor._selected_step_label = None
        except Exception:
            pass
        try:
            self.refresh_from_editor(force_retrace=True)
        except Exception as exc:
            self.editor.append_debug(f"Open 3D clear-aperture center refresh failed: {exc}")
        self.status_var.set(f"{label.upper()} clear aperture centred on the optical axis.")

    def _clear_clear_aperture_from_context(self, label: str) -> None:
        """Right-click "Forget Clear Aperture": drop the persisted CA record."""
        label = str(label).strip().lower()
        removed = None
        try:
            removed = self.editor.clear_step_clear_aperture(label)
        except Exception as exc:
            self.editor.append_debug(f"Open 3D clear-aperture forget failed: {exc}")
        try:
            self.refresh_from_editor()
        except Exception:
            pass
        if removed is not None:
            self.status_var.set(f"{label.upper()} clear aperture forgotten.")
        else:
            self.status_var.set(f"No clear aperture was set for the {label.upper()} STEP.")

    def _promote_step_and_assign_face_function(
        self,
        label: str,
        point_world,
        normal_world,
        function_label: str,
        *,
        face_id: str = "",
    ) -> None:
        # bugs/0145: hold the table-event-driven Open 3D row highlight off for the
        # whole promote+refresh. The inner body inserts the new solid row, fires
        # `_sync_table`/`_select_table_indices` and runs the heavy retrace -- all
        # while the inspector's actor map still describes the PRE-promote scene, so
        # a deferred `<<TreeviewSelect>>` sync landing in that window would pink the
        # upstream imaging-lens datum (see `_sync_surface_selection`). The inner
        # body does its own authoritative highlight against the rebuilt map, so the
        # suppressed sync is purely the stale flash. ``finally`` guarantees the flag
        # is cleared on every exit path -- a stuck flag would mute ALL later
        # selection highlighting.
        self.editor._suppress_3d_row_selection_sync = True
        try:
            self._promote_step_and_assign_face_function_inner(
                label,
                point_world,
                normal_world,
                function_label,
                face_id=face_id,
            )
        finally:
            self.editor._suppress_3d_row_selection_sync = False

    def _promote_step_and_assign_face_function_inner(
        self,
        label: str,
        point_world,
        normal_world,
        function_label: str,
        *,
        face_id: str = "",
    ) -> None:
        le = _layout_module()
        STEP_OVERLAY_LABEL_SET = le.STEP_OVERLAY_LABEL_SET
        _short_error_message = le._short_error_message
        _optical_solid_face_function_display = le._optical_solid_face_function_display
        label = str(label).strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET:
            return
        if le.is_step_overlay_decoration(label):
            display = self.editor._step_overlay_display_label(label).upper()
            self.status_var.set(
                f"{display} STEP is a decoration and cannot be assigned an optical surface function."
            )
            self._debug_trace("promote_step_face_assignment_decoration_blocked", label=label)
            return
        refresh_sampling_mode = self._active_refresh_sampling_mode()
        face_id = str(face_id or "").strip()
        self._debug_trace(
            "promote_step_face_assignment_start",
            label=label,
            face_id=face_id or None,
            function_label=function_label,
            point_world=self._debug_vector(point_world),
            normal_world=self._debug_vector(normal_world),
            counts_before=self._debug_actor_counts(),
        )
        # bugs/0232: a SECOND (trailing) fold mirror -- a free-placed RA mirror the user
        # dropped near the camera and is now assigning a Full-Reflecting face -- must land as
        # the LAST optical element before the sensor, so its fold moves ONLY the camera. The
        # default insert (table selection -> max(selected)+1) put it right after the FIRST
        # mirror (row 2), BEFORE the lens group, so the pose-override swept the whole lens
        # chain onto the fold branch (the flag "after second RA promoted, it should only fold
        # the camera"). When the scene ALREADY has a promoted mirror fold and this assignment
        # is a full mirror, insert at the end (a large index; _step_overlay_insert_index clamps
        # it to before-Image). The FIRST fold has no existing mirror -> keeps its place.
        promote_insert_at = None
        try:
            from KrakenOS.UI.optical_solid_metadata import (
                OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_MIRROR,
            )

            is_full_mirror_assignment = (
                str(function_label).strip() == OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_MIRROR
            )
            existing_folds = self.editor._promoted_mirror_fold_row_indices()
            if is_full_mirror_assignment and existing_folds:
                promote_insert_at = len(self.editor.rows)
                self._debug_trace(
                    "promote_step_face_assignment_trailing_fold_end_insert",
                    label=label,
                    existing_folds=[int(i) for i in existing_folds],
                    insert_at=int(promote_insert_at),
                )
        except Exception:
            promote_insert_at = None
        try:
            result = self.editor.promote_imported_step_to_optical_solid_row(
                label,
                insert_at=promote_insert_at,
                open_face_editor=False,
                clear_overlay=True,
                refresh_open_3d=False,
                # bugs/0079: the direct face-assign right-click is a UI promote of
                # an on-axis in-path solid too -- hold the detector fixed (faces
                # refract for the t(1-1/n) shift) instead of shoving it by the raw
                # thickness.
                inpath_axial_placement=True,
            )
        except Exception as exc:
            self.status_var.set(f"Promote STEP failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Open 3D STEP promotion for face assignment failed: {exc}")
            self._debug_trace("promote_step_face_assignment_failed", label=label, error=_short_error_message(exc))
            return
        if result is None:
            self.status_var.set(self.editor.status_var.get())
            self._debug_trace("promote_step_face_assignment_no_result", label=label, status=self.editor.status_var.get())
            return
        self._stl_placement_dirty = True
        row_index = int(result.get("row_index", -1))
        self._debug_trace(
            "promote_step_face_assignment_promoted",
            label=label,
            row_index=row_index,
            overlay_face_id=face_id or None,
            result={key: str(value) for key, value in dict(result).items()},
        )
        assigned_by = "world_point"
        try:
            # Imported STEP overlays and promoted row-backed STL solids are
            # generated as different cached meshes. Their planar face labels can
            # differ even when they describe the same physical surface, so the
            # first promote-and-assign action must rematch by picked world
            # geometry instead of trusting the temporary overlay face ID.
            try:
                assigned = self.editor.assign_optical_solid_face_function_at_world_point(
                    row_index,
                    point_world,
                    function_label,
                    normal_world=normal_world,
                    direct_context=True,
                )
            except Exception:
                if not face_id:
                    raise
                assigned_by = "overlay_face_id_fallback"
                assigned = self.editor.assign_optical_solid_face_function(
                    row_index,
                    face_id,
                    function_label,
                    direct_context=True,
                )
        except Exception as exc:
            self.status_var.set(f"Promoted STEP, but face assignment failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Open 3D promoted STEP face assignment failed: {exc}")
            self._debug_trace("promoted_step_face_assignment_failed", label=label, row_index=row_index, face_id=face_id or None, error=_short_error_message(exc))
            return
        self._debug_trace(
            "promoted_step_face_assignment_metadata_saved",
            label=label,
            row_index=row_index,
            face_id=str(assigned.get("face_id", "") or ""),
            overlay_face_id=face_id or None,
            assigned_by=assigned_by,
            function_display=str(assigned.get("function_display", function_label) or function_label),
            metadata=self._debug_face_metadata_summary(assigned.get("metadata")),
        )
        self._clear_step_overlay_interaction_state(label)
        # bugs/0139: select the new solid in the TABLE only -- do NOT eagerly
        # highlight it in 3D here. ``_select_table_row`` would synchronously call
        # ``highlight_row`` against the 3D actor map that is still STALE (the
        # promote ran with refresh_open_3d=False), so the index of the just-inserted
        # row maps to whatever actor occupied that index in the PRE-promote scene --
        # the upstream lens "Lens Front Datum" -- flashing a distant, unrelated
        # element pink during promotion. ``_select_table_indices`` sets the same
        # table selection without the synchronous stale-map highlight; the rebuild
        # below (and ``highlight_row`` after it) repaint the real solid against the
        # FRESH map.
        self.editor._select_table_indices([row_index], focus_index=row_index)
        try:
            # bugs/0116: a direct right-click face assignment IS a promote of an
            # in-path optical solid, so its forced retrace is the same ~44s full
            # branched physics trace the plain promote already clamps (bugs/0105).
            # Clamp THIS retrace to the same sparse 3-ray fan so face-assign lands
            # fast instead of freezing the UI; cleared in finally so the next
            # explicit trace restores full ray density. Only the displayed ray
            # COUNT changes -- the assigned face, branch detectors and reconciled
            # prescription are unaffected.
            self.editor._promote_preview_ray_count_override = 3
            try:
                self.refresh_from_editor(sampling_mode=refresh_sampling_mode, force_retrace=True)
            finally:
                self.editor._promote_preview_ray_count_override = None
            self.highlight_row(row_index)
        except Exception as exc:
            self.editor.append_debug(f"Open 3D refresh after promoted STEP face assignment failed: {exc}")
            self._debug_trace("promoted_step_face_assignment_refresh_failed", label=label, row_index=row_index, error=_short_error_message(exc))
        face_id = str(assigned.get("face_id", "") or "picked face")
        display = str(assigned.get("function_display", function_label) or function_label)
        self._debug_trace(
            "promoted_step_face_assignment_done",
            label=label,
            row_index=row_index,
            face_id=face_id,
            function_display=display,
            counts_after=self._debug_actor_counts(),
        )
        self.status_var.set(
            f"Promoted {label.upper()} STEP to S{row_index} and set {face_id} to {display}. "
            "The row now participates in non-sequential tracing."
        )

    def _build_row_actions_cascade(self, parent_menu, row_index: int) -> None:
        """Mirror 2D row-context actions inside the 3D right-click menu."""
        editor = self.editor
        if not (0 <= int(row_index) < len(editor.rows)):
            return
        group = editor._lens_row_group_for_row(int(row_index))
        is_group = len(group) >= 2
        try:
            row = editor.rows[int(row_index)]
        except Exception:
            row = None
        single_row_scene_flip = bool(
            not is_group
            and row is not None
            and (
                editor._file_backed_stl_row_at(int(row_index)) is not None
                or editor._is_any_promoted_optical_solid_row(row)
            )
        )

        def _select_group() -> None:
            try:
                editor._select_table_indices(group, focus_index=group[0])
            except Exception:
                try:
                    editor._select_table_row(int(row_index))
                except Exception:
                    pass

        def _refresh_3d() -> None:
            try:
                self.refresh_from_editor(force_retrace=True)
                self.highlight_row(group[0])
            except Exception as exc:
                editor.append_debug(f"Open 3D refresh after row action failed: {exc}")

        def _do(action) -> None:
            _select_group()
            try:
                action()
            except Exception as exc:
                from KrakenOS.UI.layout_editor import _short_error_message
                self.status_var.set(f"Row action failed: {_short_error_message(exc)}")
                editor.append_debug(f"Open 3D row action failed: {exc}")
                return
            _refresh_3d()

        def _flip_or_reverse() -> object:
            if is_group:
                return editor.flip_rows(group)
            if single_row_scene_flip:
                return editor.rotate_scene_row_pose_world_axis(int(row_index), "y", 180.0)
            return editor.flip_rows(group)

        actions = tk.Menu(parent_menu, tearoff=False)
        flip_label = "Flip Lens (reverse element)" if is_group else "Flip / reverse selected element"
        flip_state = "normal" if (is_group or single_row_scene_flip) else "disabled"
        actions.add_command(
            label=flip_label,
            state=flip_state,
            command=lambda: _do(_flip_or_reverse),
        )
        actions.add_separator()
        actions.add_command(label="Move element up", command=lambda: _do(editor.move_up))
        actions.add_command(label="Move element down", command=lambda: _do(editor.move_down))
        actions.add_separator()
        actions.add_command(label="Duplicate", command=lambda: _do(editor.duplicate_selected))
        actions.add_command(label="Delete", command=lambda: _do(editor.delete_selected))
        actions.add_separator()
        actions.add_command(
            label="Group as element",
            state=("normal" if is_group else "disabled"),
            command=lambda: _do(editor.group_selected_as_element),
        )
        actions.add_command(
            label="Ungroup element",
            command=lambda: _do(editor.ungroup_selected_elements),
        )
        actions.add_separator()
        actions.add_command(
            label="Element settings...",
            command=lambda: (_select_group(), editor.open_element_settings()),
        )
        parent_menu.add_cascade(label="Row Actions", menu=actions)
