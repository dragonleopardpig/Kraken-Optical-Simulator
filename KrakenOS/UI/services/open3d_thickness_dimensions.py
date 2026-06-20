"""Open 3D editable Thickness dimension overlays.

The service owns row-to-row dimension geometry and the row-scoped edit action.
The embedded Tk/VTK inspector still owns renderer actor registration, picking,
and scene refresh.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import tkinter as tk
from tkinter import ttk


class Open3DThicknessDimensionService:
    """Render and edit Open 3D dimensions backed by table Thickness rows."""

    # bugs/0009: the dimension shaft + leader lines read too thin against the
    # lens body. These knobs are shared by the persistent overlay (arrow_mesh /
    # _emit_span_dimension) and the live drag readout
    # (Kraken3DInspector._draw_step_translate_gap_overlay, which reads
    # DIMENSION_LEADER_LINE_WIDTH and calls arrow_mesh), so bumping them here
    # thickens *both* distances the user compared.
    DIMENSION_TUBE_RADIUS_FACTOR = 0.36
    DIMENSION_TUBE_RADIUS_FLOOR = 0.06
    DIMENSION_LEADER_LINE_WIDTH = 2.2

    def __init__(
        self,
        inspector: Any,
        *,
        pv_module: Any,
        billboard_text_actor_cls: Any,
    ) -> None:
        self.inspector = inspector
        self.editor = inspector.editor
        self.pv = pv_module
        self.billboard_text_actor_cls = billboard_text_actor_cls
        self._inline_editor_window: tk.Toplevel | None = None
        self._inline_editor_row_index: int | None = None
        self._inline_editor_committing = False

    def arrow_mesh(
        self,
        start: np.ndarray,
        end: np.ndarray,
        *,
        scene_span: float,
        thickness_scale: float = 1.0,
    ) -> Any | None:
        # ``thickness_scale`` fattens the shaft tube + arrowheads without
        # changing their length. The persistent dimension overlay leaves it at
        # 1.0 (geometry unchanged); the live drag readout passes >1 so the
        # moving gap arrow reads thicker than the static dimensions (#65).
        pv = self.pv
        if pv is None:
            return None
        start = np.asarray(start, dtype=float).reshape(3)
        end = np.asarray(end, dtype=float).reshape(3)
        delta = end - start
        length = float(np.linalg.norm(delta))
        if not np.isfinite(length) or length <= 1e-9:
            return None
        direction = delta / length
        scale = max(float(thickness_scale), 1.0e-3)
        base_head = min(max(float(scene_span) * 0.018, 0.75), max(length * 0.28, 0.75))
        head = base_head * (0.6 + 0.4 * scale)
        radius = max(base_head * 0.20, 0.12) * scale
        tube_radius = max(radius * self.DIMENSION_TUBE_RADIUS_FACTOR, self.DIMENSION_TUBE_RADIUS_FLOOR)
        parts: list[Any] = []
        try:
            line = pv.Line(tuple(float(value) for value in start), tuple(float(value) for value in end))
            try:
                parts.append(line.tube(radius=float(tube_radius), n_sides=10))
            except Exception:
                parts.append(line)
        except Exception:
            return None
        for tip, cone_direction in ((start, -direction), (end, direction)):
            try:
                center = np.asarray(tip, dtype=float) - np.asarray(cone_direction, dtype=float) * (head * 0.5)
                parts.append(
                    pv.Cone(
                        center=tuple(float(value) for value in center),
                        direction=tuple(float(value) for value in cone_direction),
                        height=float(head),
                        radius=float(radius),
                        resolution=24,
                    )
                )
            except Exception:
                pass
        merged = parts[0]
        for part in parts[1:]:
            try:
                merged = merged.merge(part)
            except Exception:
                pass
        return merged

    @staticmethod
    def offset_direction(
        segment_direction: np.ndarray,
        view_normal: np.ndarray | None = None,
        screen_up: np.ndarray | None = None,
    ) -> np.ndarray:
        """Unit direction to push a dimension arrow off the segment it measures.

        With a camera ``view_normal`` the offset is forced into the screen plane:
        ``cross(view, segment)`` is perpendicular to *both* the view direction and
        the segment, so it reads as a visible sideways offset in the rendered
        view. The purely geometric perpendicular (no camera) put an optical-axis
        (Z) dimension along world -X, which is exactly the depth axis of the
        default side view -- so the arrow vanished into the screen and the label
        landed on the axis (bugs/0007). ``screen_up`` (optional) only fixes the
        sign so the dimension sits consistently below the axis on screen.
        """
        direction = np.asarray(segment_direction, dtype=float).reshape(3)
        norm = float(np.linalg.norm(direction))
        if not np.isfinite(norm) or norm <= 1e-12:
            direction = np.asarray((0.0, 0.0, 1.0), dtype=float)
        else:
            direction = direction / norm

        view = None
        if view_normal is not None:
            candidate = np.asarray(view_normal, dtype=float).reshape(3)
            candidate_norm = float(np.linalg.norm(candidate))
            if np.isfinite(candidate_norm) and candidate_norm > 1e-12:
                view = candidate / candidate_norm

        up_unit = None
        if screen_up is not None:
            up_candidate = np.asarray(screen_up, dtype=float).reshape(3)
            up_norm = float(np.linalg.norm(up_candidate))
            if np.isfinite(up_norm) and up_norm > 1e-12:
                up_unit = up_candidate / up_norm

        if view is not None:
            side = np.cross(view, direction)
            side_norm = float(np.linalg.norm(side))
            if np.isfinite(side_norm) and side_norm > 1e-6:
                side = side / side_norm
            elif up_unit is not None:
                # Segment runs (almost) along the view axis -> it projects to a
                # point; any in-screen direction reads as an offset.
                side = up_unit
            else:
                trial = np.asarray((0.0, 0.0, 1.0), dtype=float)
                if abs(float(np.dot(view, trial))) > 0.90:
                    trial = np.asarray((0.0, 1.0, 0.0), dtype=float)
                side = np.cross(view, trial)
                side_norm = float(np.linalg.norm(side))
                side = side / side_norm if side_norm > 1e-12 else np.asarray((0.0, 1.0, 0.0), dtype=float)
            if up_unit is not None and float(np.dot(side, up_unit)) > 0.0:
                side = -side
            return side

        reference = np.asarray((0.0, 0.0, 1.0), dtype=float)
        if abs(float(np.dot(direction, reference))) > 0.90:
            reference = np.asarray((0.0, 1.0, 0.0), dtype=float)
        side = np.cross(direction, reference)
        side_norm = float(np.linalg.norm(side))
        if not np.isfinite(side_norm) or side_norm <= 1e-12:
            return np.asarray((1.0, 0.0, 0.0), dtype=float)
        return side / side_norm

    @staticmethod
    def _perp_label_orientation(axis, screen_right, screen_up) -> float:
        """Billboard text angle so a label reads PERPENDICULAR to its arrow on screen.

        The arrow runs along ``axis``; project it to the screen (right, up) and rotate the text
        90 deg off it. A horizontal arrow (transmit) -> 90 (vertical text, as before); a vertical
        arrow (the folded reflect arm) -> ~0 (horizontal text). The old hardcoded 90 made the
        reflect labels run PARALLEL to their arrows (the user's "not perpendicular")."""
        if screen_right is None or screen_up is None:
            return 90.0
        try:
            a = np.asarray(axis, dtype=float).reshape(3)
            sx = float(np.dot(a, np.asarray(screen_right, dtype=float).reshape(3)))
            sy = float(np.dot(a, np.asarray(screen_up, dtype=float).reshape(3)))
            if abs(sx) < 1e-9 and abs(sy) < 1e-9:
                return 90.0
            orient = float(np.degrees(np.arctan2(sy, sx))) + 90.0
            while orient > 90.0:
                orient -= 180.0
            while orient < -90.0:
                orient += 180.0
            return orient
        except Exception:
            return 90.0

    def _fold_detector_for_terminal_row(self, end_row_index: int, p1, scene_bundle):
        """If gap ends at a superseded prescription Detector/Image row, return the FOLD detector
        (physical focus) it was superseded by, so the thickness reads to where rays converge -- not
        the stale prescription plane (0110 part 2). Else None (gap unchanged)."""
        rows = getattr(self.editor, "rows", None) or []
        if not (0 <= int(end_row_index) < len(rows)):
            return None
        row = rows[int(end_row_index)]
        surface = str(getattr(row, "surface", "") or "").strip().lower()
        name = str(getattr(row, "name", "") or "").strip().lower()
        if not (surface == "image" or "detector" in name):
            return None
        centers = [
            np.asarray(t.center_world, dtype=float).reshape(3)
            for t in (getattr(scene_bundle, "targets", []) or [])
            if bool(getattr(t, "is_detector", False)) and getattr(t, "center_world", None) is not None
        ]
        if not centers:
            return None
        p1 = np.asarray(p1, dtype=float).reshape(3)
        best = min(centers, key=lambda c: float(np.linalg.norm(c - p1)))
        # The physical focus shift off the prescription plane is ~20mm; guard against grabbing an
        # unrelated arm's detector.
        return best if float(np.linalg.norm(best - p1)) < 60.0 else None

    def _register_drag_actor(self, actor: Any, row_index: int, start: np.ndarray, end: np.ndarray) -> None:
        actor_key = self.inspector._actor_key(actor)
        if actor_key is None:
            return
        try:
            start_values = np.asarray(start, dtype=float).reshape(-1)[:3]
            end_values = np.asarray(end, dtype=float).reshape(-1)[:3]
        except Exception:
            return
        if start_values.size < 3 or end_values.size < 3:
            return
        if not (np.all(np.isfinite(start_values[:3])) and np.all(np.isfinite(end_values[:3]))):
            return
        try:
            initial = float(getattr(self.editor.rows[int(row_index)], "thickness", 0.0) or 0.0)
        except Exception:
            initial = 0.0
        self.inspector._thickness_dimension_drag_map[actor_key] = {
            "row_index": int(row_index),
            "start": tuple(float(value) for value in start_values[:3]),
            "end": tuple(float(value) for value in end_values[:3]),
            "initial_thickness": float(initial),
        }

    def add_label_actor(
        self,
        row_index: int,
        position: np.ndarray,
        text: str,
        *,
        drag_start: np.ndarray | None = None,
        drag_end: np.ndarray | None = None,
        orientation_deg: float = 0.0,
    ) -> bool:
        actor_cls = self.billboard_text_actor_cls
        if self.inspector._renderer is None or actor_cls is None:
            return False
        try:
            actor = actor_cls()
            actor.SetInput(str(text))
            point = np.asarray(position, dtype=float).reshape(3)
            actor.SetPosition(float(point[0]), float(point[1]), float(point[2]))
            try:
                text_prop = actor.GetTextProperty()
                text_prop.SetFontSize(13)
                text_prop.SetColor(0.02, 0.16, 0.32)
                text_prop.SetBackgroundColor(1.0, 1.0, 1.0)
                text_prop.SetBackgroundOpacity(0.82)
                text_prop.SetFrame(1)
                text_prop.SetFrameColor(0.05, 0.42, 0.70)
                # bugs/0093: rotate the billboard text so it reads PERPENDICULAR to
                # the (horizontal) thickness arrows -- lets adjacent labels stack on
                # one row without overlapping.
                if abs(float(orientation_deg)) > 1e-6:
                    text_prop.SetOrientation(float(orientation_deg))
                    try:
                        text_prop.SetJustificationToCentered()
                        text_prop.SetVerticalJustificationToCentered()
                    except Exception:
                        pass
            except Exception:
                pass
            self.inspector._register_thickness_dimension_actor(actor, int(row_index))
            if drag_start is not None and drag_end is not None:
                self._register_drag_actor(actor, int(row_index), drag_start, drag_end)
            self.inspector._add_renderer_view_prop(actor)
            return True
        except Exception as exc:
            self.editor.append_debug(f"3D thickness label skipped: {exc}")
            return False

    @staticmethod
    def _dimension_runs_to_superseded_image(rows, row_index, *, has_branch_detector) -> bool:
        """bugs/0093: True when this row's thickness dimension would terminate at a
        sequential Image that a branch detector has superseded -- skip it so the
        distance overlay doesn't draw an arrow out to the stale image plane."""
        if not has_branch_detector:
            return False
        nxt = int(row_index) + 1
        if not (0 <= nxt < len(rows)):
            return False
        return str(getattr(rows[nxt], "surface", "") or "") == "Image"

    # bugs/0093: teal marks a per-branch exit->detector distance, distinct from the
    # blue sequential model-thickness arrows and the green live-gap labels.
    BRANCH_DISTANCE_COLOR = (0.06, 0.52, 0.46)

    @staticmethod
    def _branch_arm_label(branch_path) -> str:
        """A short arm name for a branch overlay label, e.g.
        'S4:BS/transmit -> S7:BS2/reflect' -> 'reflect'."""
        text = str(branch_path or "").strip()
        if not text:
            return "branch"
        last = text.split("->")[-1].strip()
        last = last.split("/")[-1].strip()
        return last.split(":")[-1].strip() or "branch"

    def _branch_distance_overlays(self, scene_bundle, *, scene_span, base_offset, view_normal, screen_up) -> int:
        """bugs/0093: one distance dimension per branch detector, from where the arm
        EXITS the cube (the branch's mean exit-ray origin) to its detector focus --
        the per-arm 'exit face -> detector' measurement (the user's transmit AND
        reflect thickness overlays). Display-only; no draggable row binding."""
        pv = self.pv
        if pv is None:
            return 0
        count = 0
        for target in (getattr(scene_bundle, "targets", []) or []):
            meta = getattr(target, "metadata", None)
            if not (isinstance(meta, dict) and str(meta.get("target_source", "") or "") == "branch_detector"):
                continue
            exit_pt = meta.get("exit_point_world")
            if exit_pt is None:
                continue
            try:
                p0 = np.asarray(exit_pt, dtype=float).reshape(3)
                p1 = np.asarray(getattr(target, "center_world", None), dtype=float).reshape(3)
            except Exception:
                continue
            if not (np.all(np.isfinite(p0)) and np.all(np.isfinite(p1))):
                continue
            segment = p1 - p0
            distance = float(np.linalg.norm(segment))
            if not np.isfinite(distance) or distance <= 1e-6:
                continue
            side = self.offset_direction(segment, view_normal=view_normal, screen_up=screen_up)
            offset = side * base_offset
            start = p0 + offset
            end = p1 + offset
            mesh = self.arrow_mesh(start, end, scene_span=scene_span)
            if mesh is None:
                continue
            actor = self.inspector._add_mesh_actor(
                mesh, color=self.BRANCH_DISTANCE_COLOR, opacity=0.92,
                flat_shading=True, backface_culling=False,
            )
            if actor is None:
                continue
            count += 1
            try:
                for tip, anchor in ((p0, start), (p1, end)):
                    self.inspector._add_mesh_actor(
                        pv.Line(tuple(float(v) for v in tip), tuple(float(v) for v in anchor)),
                        color=(0.45, 0.72, 0.66), opacity=0.5,
                        line_width=self.DIMENSION_LEADER_LINE_WIDTH, backface_culling=False,
                    )
            except Exception:
                pass
            arm = self._branch_arm_label(meta.get("branch_path", ""))
            label = f"{arm}: exit→detector = {distance:.4g} mm"
            label_pos = 0.5 * (start + end) + side * max(base_offset * 0.22, 0.8)
            if self.add_label_actor(int(getattr(target, "row_index", 100000) or 100000), label_pos, label):
                count += 1
        return count

    @staticmethod
    def _row_optical_solid_stl(row) -> str:
        """bugs/0093: the source STL of a promoted optical-solid row ('' if none)."""
        try:
            from KrakenOS.UI.scene_builder import _row_optical_solid_source_stl
            return _row_optical_solid_source_stl(row)
        except Exception:
            advanced = getattr(row, "advanced", {}) or {}
            src = str((advanced.get("Solid_3d_stl", "") if isinstance(advanced, dict) else "") or "").strip()
            return "" if src == "None" else src

    @staticmethod
    def _row_branch_selector(row) -> str:
        """bugs/0097: which beam-splitter arm a row belongs to ('' = common / global),
        from the element metadata (e.g. beam_splitter_two_arm_doublets tags rows
        'transmit' / 'reflect')."""
        advanced = getattr(row, "advanced", None) or {}
        if not isinstance(advanced, dict):
            return ""
        element = advanced.get("Element")
        if isinstance(element, dict) and element.get("branch_selector"):
            return str(element.get("branch_selector") or "").strip()
        return str(advanced.get("branch_selector", "") or "").strip()

    @classmethod
    def _is_cross_arm_gap(cls, rows, row_index) -> bool:
        """True when the gap row_index -> row_index+1 crosses between two splitter arms
        (the last transmit row to the first reflect row, or an arm row back to the global
        image). The linear table puts those rows adjacent, but the gap is not a real axial
        spacing -- measuring it draws a dimension spanning transmit->reflect (bugs/0097)."""
        if not (0 <= row_index < len(rows) - 1):
            return False
        here = cls._row_branch_selector(rows[row_index])
        nxt = cls._row_branch_selector(rows[row_index + 1])
        return bool(here) and here != nxt

    @staticmethod
    def _row_short_name(row) -> str:
        name = str(getattr(row, "name", "") or "").strip()
        if name and len(name) <= 16:
            return name
        low = name.lower()
        if "split" in low:
            return "splitter"
        if "prism" in low:
            return "prism"
        return "solid"

    def _optical_solid_entry_point(self, row_index, axis, p0):
        """bugs/0093: world point at the ENTRY (near) face of a promoted optical-solid
        row body, on the line through ``p0`` along ``axis`` -- so a preceding surface's
        dimension reads the real air gap to the solid's first face (the 'doublet last
        surface -> beam-splitter first surface' distance), not its stale stored
        thickness. Returns None headless / when the body has no rendered actors."""
        try:
            keys = self.inspector._all_actor_keys_for_row(int(row_index))
        except Exception:
            keys = None
        if not keys:
            return None
        ext = self.inspector._axial_extent_from_actor_keys(keys, axis)
        if not isinstance(ext, dict):
            return None
        try:
            pmin = float(ext["proj_min"])
            pmax = float(ext["proj_max"])
        except Exception:
            return None
        p0 = np.asarray(p0, dtype=float).reshape(3)
        axis = np.asarray(axis, dtype=float).reshape(3)
        a0 = float(np.dot(p0, axis))
        near = pmin if abs(pmin - a0) <= abs(pmax - a0) else pmax  # the face nearer p0
        return p0 + axis * (near - a0)

    def _optical_solid_span_points(self, row_index, axis, p_on_axis):
        """bugs/0093: world points at the FRONT (min) and BACK (max) faces of a
        promoted optical-solid body along ``axis``, on the line through
        ``p_on_axis``. The row reference point is the desp_z body CENTRE, so the
        solid's own thickness dimension started mid-body (a 50 mm cube measured
        ~25 mm); span its rendered front->back instead. None headless / no actors."""
        try:
            keys = self.inspector._all_actor_keys_for_row(int(row_index))
        except Exception:
            keys = None
        if not keys:
            return None
        axis = np.asarray(axis, dtype=float).reshape(3)
        ext = self.inspector._axial_extent_from_actor_keys(keys, axis)
        if not isinstance(ext, dict):
            return None
        try:
            pmin = float(ext["proj_min"])
            pmax = float(ext["proj_max"])
        except Exception:
            return None
        if not (np.isfinite(pmin) and np.isfinite(pmax)) or (pmax - pmin) <= 1e-9:
            return None
        p = np.asarray(p_on_axis, dtype=float).reshape(3)
        a0 = float(np.dot(p, axis))
        return p + axis * (pmin - a0), p + axis * (pmax - a0)

    def add_overlays(self, system: Any, scene_bundle: Any = None) -> int:
        pv = self.pv
        if pv is None:
            return 0
        show_var = getattr(self.editor, "show_physical_distances_var", None)
        if show_var is None or not bool(show_var.get()):
            return 0
        rows = list(getattr(self.editor, "rows", []) or [])
        if len(rows) < 2:
            return 0
        # bugs/0093: when a split derived a branch detector at the true focus, the
        # sequential Image is superseded AND displaced back by the inserted
        # element's thickness. Don't draw the thickness dimension that runs out to
        # it ("the distance overlay still shows the old image plane behind the
        # detector") -- skip the span whose NEXT row is that superseded Image. The
        # Image's plane curve + label are dropped in build_scene_bundle; this is the
        # matching dimension suppression. No-op without a branch detector.
        scene_has_branch_detector = any(
            isinstance(getattr(t, "metadata", None), dict)
            and str(getattr(t, "metadata", {}).get("target_source", "") or "") == "branch_detector"
            for t in (getattr(scene_bundle, "targets", []) or [])
        )
        _center, scene_span = self.inspector._row_scene_bounds()
        # Match the 2D layout's physical-distance arrows, which stand ~8% of the
        # view span off the axis -- a clearly readable margin (bugs/0007). At the
        # old 0.045 the double-ended arrow hugged the optical-axis line.
        base_offset = max(float(scene_span) * 0.08, 2.0)
        color = (0.05, 0.42, 0.70)
        # Offset the dimension into the screen plane so it reads to the side of
        # the optical axis instead of vanishing into depth (bugs/0007).
        try:
            view_normal = self.inspector._camera_view_normal()
        except Exception:
            view_normal = None
        try:
            screen_axes = self.inspector._camera_screen_world_axes()
        except Exception:
            screen_axes = None
        screen_up = screen_axes[1] if screen_axes else None
        screen_right = screen_axes[0] if screen_axes else None
        count = 0
        for row_index, row in enumerate(rows[:-1]):
            try:
                thickness = float(getattr(row, "thickness", 0.0) or 0.0)
            except Exception:
                continue
            if not np.isfinite(thickness) or abs(thickness) <= 1e-9:
                continue
            if self._is_cross_arm_gap(rows, row_index):
                # bugs/0097: the surface table is one linear list but a beam splitter
                # forks into two arms (branch_selector tags). The gap from the last
                # transmit row to the first reflect row (or an arm row back to the
                # global image) is NOT a real axial spacing -- it jumped across the two
                # arms and drew a dimension spanning transmit->reflect. Skip it; the
                # per-branch exit->detector overlays measure each arm cleanly.
                continue
            try:
                p0 = np.asarray(self.editor._surface_reference_world_point(row_index, system=system), dtype=float).reshape(3)
                p1 = np.asarray(self.editor._surface_reference_world_point(row_index + 1, system=system), dtype=float).reshape(3)
            except Exception as exc:
                self.editor.append_debug(f"3D thickness dimension skipped for S{row_index}: {exc}")
                continue
            if not (np.all(np.isfinite(p0)) and np.all(np.isfinite(p1))):
                continue
            # 0110 part 2: a gap ending at a superseded prescription Detector/Image is redirected to
            # the FOLD detector (physical focus), so the last thickness reads to where the rays
            # converge (615.1 / 411.0), not the removed prescription plane (595.8 / 390.9).
            terminal_target = self._fold_detector_for_terminal_row(row_index + 1, p1, scene_bundle)
            if terminal_target is not None:
                p1 = terminal_target
                thickness = float(np.linalg.norm(p1 - p0))
            # bugs/0093: a promoted optical solid's OWN thickness dimension. Its row
            # reference point is the desp_z body CENTRE, so S{row} started mid-body
            # and a 50 mm cube measured ~25 mm (recording flag_20260618_180621).
            # Anchor the arrow to the solid's rendered FRONT->BACK faces and emit a
            # SINGLE span -- don't let _overlay_axial_spans_within carve the body's
            # own dimension around itself. Headless-safe (no actors -> fall through).
            if self._row_optical_solid_stl(row):
                seg_s = p1 - p0
                ns = float(np.linalg.norm(seg_s))
                if ns > 1e-9:
                    span = self._optical_solid_span_points(row_index, seg_s / ns, p0)
                    if span is not None:
                        front, back = (np.asarray(v, dtype=float).reshape(3) for v in span)
                        extent = float(np.linalg.norm(back - front))
                        if np.isfinite(extent) and extent > 1e-6:
                            side_s = self.offset_direction(back - front, view_normal=view_normal, screen_up=screen_up)
                            count += self._emit_span_dimension(
                                row_index=row_index,
                                base_lo=front,
                                base_hi=back,
                                side=side_s,
                                offset=side_s * base_offset,
                                base_offset=base_offset,
                                scene_span=scene_span,
                                color=color,
                                label=f"S{row_index} Thickness = {extent:.4g} mm",
                                drag_start=front,
                                drag_end=back,
                                label_orientation_deg=90.0,
                            )
                            continue
            # bugs/0093: skip the sequential dimension that would run out to a
            # branch-detector-superseded Image (the splitter displaced it past the
            # true focus). The per-branch exit->detector overlay (_add_branch_
            # distance_overlays, below) measures each arm instead -- cleanly, from
            # the cube exit face to its detector -- so there is no arrow to the
            # stale image plane and no redundant sequential arrow on the transmit
            # arm. No-op without a branch detector (plain sequential scenes keep it).
            if self._dimension_runs_to_superseded_image(
                rows, row_index, has_branch_detector=scene_has_branch_detector
            ):
                continue
            # bugs/0093: when the NEXT row is a promoted optical solid (e.g. a beam-
            # splitter cube), its stored thickness is stale -- snapping the solid into
            # place never reconciled the preceding gap, and post-promotion the gap-
            # split can't carve it (it only scans imported STEP overlays, not solid
            # rows). Measure the REAL air gap from this surface to the solid's ENTRY
            # face -- the "doublet last surface -> beam-splitter first surface"
            # distance -- and label THAT instead of the stale stored thickness.
            solid_gap_label = None
            if self._row_optical_solid_stl(rows[row_index + 1]):
                seg0 = p1 - p0
                n0 = float(np.linalg.norm(seg0))
                if n0 > 1e-9:
                    entry = self._optical_solid_entry_point(row_index + 1, seg0 / n0, p0)
                    if entry is not None and np.all(np.isfinite(entry)):
                        gap = float(np.linalg.norm(np.asarray(entry, dtype=float).reshape(3) - p0))
                        if np.isfinite(gap) and gap > 1e-6:
                            p1 = np.asarray(entry, dtype=float).reshape(3)
                            solid_gap_label = f"gap to {self._row_short_name(rows[row_index + 1])} = {gap:.4g} mm"
            # bugs/0053: a re-anchored row is a direct MEASUREMENT to a picked
            # surface/edge z -- draw a single arrow to it (no gap-splitting) and
            # label the measured distance, visually distinct from a model thickness.
            override = None
            try:
                override = self.editor._dimension_anchor_override_for_row(row_index)
            except Exception:
                override = None
            if isinstance(override, dict):
                count += self._emit_reanchored_dimension(
                    row_index, p0, p1, override,
                    base_offset=base_offset, scene_span=scene_span,
                    view_normal=view_normal, screen_up=screen_up,
                )
                continue
            segment = p1 - p0
            segment_length = float(np.linalg.norm(segment))
            if not np.isfinite(segment_length) or segment_length <= 1e-9:
                continue
            axis = segment / segment_length
            a0 = float(np.dot(p0, axis))
            a1 = float(np.dot(p1, axis))
            # bugs/0009: an imported optical body sitting between S{row} and the
            # next surface used to be painted straight through -- the dimension
            # "skipped the lens and measured the next element". Break the span at
            # any overlay so each arrow reads the real edge-to-edge gap (the same
            # quantity the live drag readout shows), instead of one row->row arrow.
            overlay_spans = self._overlay_axial_spans_within(axis, a0, a1)
            gaps = self.split_span_at_overlays(a0, a1, overlay_spans)
            split = len(gaps) > 1
            side = self.offset_direction(segment, view_normal=view_normal, screen_up=screen_up)
            # bugs/0093: all thickness arrows on ONE row, adjacent (was staggered into
            # 3 bands by `row_index % 3`); labels read perpendicular so adjacent ones
            # don't collide on the single row.
            row_band = 1.0
            offset = side * base_offset * row_band
            for gap_lo, gap_hi in gaps:
                gap_mm = float(gap_hi - gap_lo)
                if gap_mm <= max(segment_length * 1e-3, 1e-6):
                    continue
                frac_lo = (gap_lo - a0) / (a1 - a0)
                frac_hi = (gap_hi - a0) / (a1 - a0)
                base_lo = p0 + segment * frac_lo
                base_hi = p0 + segment * frac_hi
                if solid_gap_label is not None:
                    label = solid_gap_label
                elif split:
                    label = f"gap = {gap_mm:.4g} mm"
                else:
                    label = f"S{row_index} Thickness = {thickness:.6g} mm"
                count += self._emit_span_dimension(
                    row_index=row_index,
                    base_lo=base_lo,
                    base_hi=base_hi,
                    side=side,
                    offset=offset,
                    base_offset=base_offset,
                    scene_span=scene_span,
                    color=color,
                    label=label,
                    drag_start=p0,
                    drag_end=p1,
                    label_orientation_deg=self._perp_label_orientation(axis, screen_right, screen_up),
                )
        # bugs/0093: per-branch exit->detector distance overlays (transmit + reflect).
        count += self._branch_distance_overlays(
            scene_bundle, scene_span=scene_span, base_offset=base_offset,
            view_normal=view_normal, screen_up=screen_up,
        )
        return count

    def _overlay_axial_spans_within(
        self, axis: np.ndarray, a0: float, a1: float
    ) -> list[tuple[float, float]]:
        """Axial ``[min, max]`` spans of imported STEP overlays whose center
        falls strictly between the two surface projections ``a0``/``a1`` along
        ``axis``.

        Only imported solid bodies can lie between two *consecutive* table rows,
        so these are the bodies the row->row dimension must not paint across
        (bugs/0009). Spans are clamped to the row span.
        """
        lo, hi = (a0, a1) if a0 <= a1 else (a1, a0)
        margin = max((hi - lo) * 1e-3, 1e-6)
        spans: list[tuple[float, float]] = []
        step_map = getattr(self.inspector, "_step_actor_map", {}) or {}
        for actor_keys in list(step_map.values()):
            try:
                extent = self.inspector._axial_extent_from_actor_keys(actor_keys, axis)
            except Exception:
                extent = None
            if extent is None:
                continue
            # bugs/0093: only carve overlays actually ON the beam (straddling the
            # optical axis). A randomly-parked, off-axis cube overlaps in z but
            # isn't in the light path, so the dimension must NOT split around it
            # ("the gap thickness still includes the random-placed beam splitter").
            if not bool(extent.get("straddles_axis", True)):
                continue
            center = float(extent.get("proj_center", float("nan")))
            if not np.isfinite(center) or center <= lo + margin or center >= hi - margin:
                continue
            pmin = max(float(extent.get("proj_min", lo)), lo)
            pmax = min(float(extent.get("proj_max", hi)), hi)
            if pmax - pmin > margin:
                spans.append((pmin, pmax))
        return spans

    @staticmethod
    def split_span_at_overlays(
        a0: float,
        a1: float,
        overlay_spans: list[tuple[float, float]],
        *,
        min_gap: float = 1e-6,
    ) -> list[tuple[float, float]]:
        """Clear-gap intervals of a row span ``[a0, a1]`` once the solid
        ``overlay_spans`` are carved out.

        No overlays -> ``[(a0, a1)]`` (the original row->row dimension). One
        overlay between the surfaces -> ``[(a0, near), (far, a1)]`` -- the
        physical gaps on each side of the lens, so the dimension never paints
        across it (bugs/0009). If overlays cover the whole span, falls back to
        the full span so something is still drawn.
        """
        lo, hi = (a0, a1) if a0 <= a1 else (a1, a0)
        spans = sorted(
            (
                (max(float(s), lo), min(float(e), hi))
                for s, e in overlay_spans
                if float(e) > float(s)
            ),
            key=lambda se: se[0],
        )
        gaps: list[tuple[float, float]] = []
        cursor = lo
        for s, e in spans:
            if s - cursor > min_gap:
                gaps.append((cursor, s))
            cursor = max(cursor, e)
        if hi - cursor > min_gap:
            gaps.append((cursor, hi))
        if not gaps:
            return [(lo, hi)]
        return gaps

    def _emit_span_dimension(
        self,
        *,
        row_index: int,
        base_lo: np.ndarray,
        base_hi: np.ndarray,
        side: np.ndarray,
        offset: np.ndarray,
        base_offset: float,
        scene_span: float,
        color: tuple[float, float, float],
        label: str,
        drag_start: np.ndarray,
        drag_end: np.ndarray,
        label_orientation_deg: float = 0.0,
    ) -> int:
        """Draw one dimension (shaft + leaders + label) between ``base_lo`` and
        ``base_hi``, offset to ``side``.

        Editing/drag always maps back to the table thickness of ``row_index``
        (``drag_start``/``drag_end`` span the whole row), so a split lens-gap
        arrow still edits the row it belongs to (bugs/0009). Returns the number
        of pickable dimension actors added.
        """
        pv = self.pv
        start = base_lo + offset
        end = base_hi + offset
        mesh = self.arrow_mesh(start, end, scene_span=scene_span)
        if mesh is None:
            return 0
        actor = self.inspector._add_mesh_actor(
            mesh,
            color=color,
            opacity=0.92,
            pick_thickness_dimension=row_index,
            flat_shading=True,
            backface_culling=False,
        )
        if actor is None:
            return 0
        self._register_drag_actor(actor, row_index, drag_start, drag_end)
        count = 1
        try:
            for tip, anchor in ((base_lo, start), (base_hi, end)):
                self.inspector._add_mesh_actor(
                    pv.Line(
                        tuple(float(value) for value in tip),
                        tuple(float(value) for value in anchor),
                    ),
                    color=(0.62, 0.72, 0.80),
                    opacity=0.52,
                    line_width=self.DIMENSION_LEADER_LINE_WIDTH,
                    backface_culling=False,
                )
        except Exception:
            pass
        # bugs/0093: label centred on the segment but pushed well CLEAR of the arrow
        # row (the perpendicular labels are tall, so a small offset let them cross
        # the arrows). `start`/`end` already sit `base_offset` off the axis, so this
        # drops the label most of another `base_offset` past the arrow line.
        label_position = 0.5 * (start + end) + side * max(base_offset * 0.85, 5.0)
        if self.add_label_actor(
            row_index, label_position, label,
            drag_start=drag_start, drag_end=drag_end,
            orientation_deg=label_orientation_deg,
        ):
            count += 1
        return count

    # bugs/0053: warm magenta tone marks a re-anchored MEASUREMENT, distinct from
    # the blue model-thickness arrows and the green live-gap labels.
    REANCHOR_DIMENSION_COLOR = (0.62, 0.18, 0.58)

    def reanchored_endpoints(
        self, p0: np.ndarray, p1: np.ndarray, override: dict
    ) -> tuple[np.ndarray, np.ndarray, float] | None:
        """Apply an endpoint override to (p0, p1): move the chosen end's axial z
        to the picked reference. Returns (q0, q1, measured_mm) or None."""
        try:
            ref_z = float(override.get("ref_z"))
        except Exception:
            return None
        if not np.isfinite(ref_z):
            return None
        endpoint = "start" if str(override.get("endpoint", "end")) == "start" else "end"
        q0 = np.asarray(p0, dtype=float).reshape(3).copy()
        q1 = np.asarray(p1, dtype=float).reshape(3).copy()
        if endpoint == "start":
            q0[2] = ref_z
        else:
            q1[2] = ref_z
        measured = abs(float(q1[2] - q0[2]))
        return q0, q1, measured

    def _emit_reanchored_dimension(
        self,
        row_index: int,
        p0: np.ndarray,
        p1: np.ndarray,
        override: dict,
        *,
        base_offset: float,
        scene_span: float,
        view_normal,
        screen_up,
    ) -> int:
        result = self.reanchored_endpoints(p0, p1, override)
        if result is None:
            return 0
        q0, q1, measured = result
        segment = q1 - q0
        if not np.isfinite(float(np.linalg.norm(segment))) or float(np.linalg.norm(segment)) <= 1e-9:
            return 0
        side = self.offset_direction(segment, view_normal=view_normal, screen_up=screen_up)
        row_band = 1.0 + 0.38 * float(row_index % 3)
        offset = side * base_offset * row_band
        label = f"S{row_index} measured = {measured:.6g} mm"
        return self._emit_span_dimension(
            row_index=row_index,
            base_lo=q0,
            base_hi=q1,
            side=side,
            offset=offset,
            base_offset=base_offset,
            scene_span=scene_span,
            color=self.REANCHOR_DIMENSION_COLOR,
            label=label,
            drag_start=q0,
            drag_end=q1,
        )

    def _display_direction_for_drag(self, start: np.ndarray, end: np.ndarray) -> tuple[np.ndarray, float]:
        try:
            start_display = self.inspector._world_to_display_2d(start)
            end_display = self.inspector._world_to_display_2d(end)
        except Exception:
            start_display = None
            end_display = None
        if start_display is not None and end_display is not None:
            delta = np.asarray(end_display, dtype=float).reshape(-1)[:2] - np.asarray(start_display, dtype=float).reshape(-1)[:2]
            display_length = float(np.linalg.norm(delta))
            if np.isfinite(display_length) and display_length > 1e-6:
                return delta / display_length, display_length
        segment = np.asarray(end, dtype=float).reshape(-1)[:3] - np.asarray(start, dtype=float).reshape(-1)[:3]
        axis = int(np.nanargmax(np.abs(segment[:3]))) if segment.size >= 3 else 2
        fallback = {
            0: np.asarray((1.0, 0.0), dtype=float),
            1: np.asarray((0.0, 1.0), dtype=float),
            2: np.asarray((1.0, 1.0), dtype=float) / np.sqrt(2.0),
        }.get(axis, np.asarray((1.0, 0.0), dtype=float))
        return fallback, 80.0

    def drag_state_from_current_pick(self) -> dict[str, object] | None:
        if self.inspector._picker is None or self.inspector._renderer is None or self.inspector._vtk_interactor is None:
            return None
        try:
            if int(self.inspector._vtk_interactor.GetControlKey()):
                return None
        except Exception:
            pass
        try:
            x, y = self.inspector._vtk_interactor.GetEventPosition()
            self.inspector._picker.Pick(x, y, 0.0, self.inspector._renderer)
            actor = self.inspector._picker.GetActor()
            if actor is None:
                get_view_prop = getattr(self.inspector._picker, "GetViewProp", None)
                if callable(get_view_prop):
                    actor = get_view_prop()
            actor_key = self.inspector._actor_key(actor)
        except Exception:
            return None
        if actor_key is None:
            return None
        record = self.inspector._thickness_dimension_drag_map.get(actor_key)
        if not isinstance(record, dict):
            return None
        try:
            row_index = int(record.get("row_index", -1))
        except Exception:
            return None
        if not (0 <= row_index < len(self.editor.rows) - 1):
            return None
        try:
            start = np.asarray(record.get("start"), dtype=float).reshape(-1)[:3]
            end = np.asarray(record.get("end"), dtype=float).reshape(-1)[:3]
        except Exception:
            return None
        if start.size < 3 or end.size < 3 or not (np.all(np.isfinite(start[:3])) and np.all(np.isfinite(end[:3]))):
            return None
        segment_length = float(np.linalg.norm(end[:3] - start[:3]))
        if not np.isfinite(segment_length) or segment_length <= 1e-12:
            return None
        display_direction, display_length = self._display_direction_for_drag(start[:3], end[:3])
        try:
            initial = float(getattr(self.editor.rows[row_index], "thickness", record.get("initial_thickness", 0.0)) or 0.0)
        except Exception:
            initial = 0.0
        mm_per_pixel = segment_length / max(float(display_length), 1.0)
        if not np.isfinite(mm_per_pixel) or mm_per_pixel <= 1e-12:
            mm_per_pixel = max(abs(float(initial)), 1.0) / 80.0
        self.inspector.status_var.set(
            f"Drag S{row_index} Thickness along the dimension arrow; release to apply, click to edit numerically."
        )
        # Quick Estimation: remember the conjugate partner gap so a live drag can
        # restore both on release (so undo brackets the whole drag, not the last
        # increment).
        partner_row = None
        partner_initial = None
        try:
            qe = self.inspector._quick_estimation_service()
            if qe.is_enabled():
                if row_index == qe.object_thickness_row():
                    partner_row = qe.image_thickness_row()
                elif row_index == qe.image_thickness_row():
                    partner_row = qe.object_thickness_row()
                if partner_row is not None:
                    partner_initial = float(self.editor.rows[partner_row].thickness)
        except Exception:
            partner_row = None
            partner_initial = None
        return {
            "row_index": row_index,
            "initial_thickness": float(initial),
            "pending_thickness": float(initial),
            "display_direction": tuple(float(value) for value in display_direction[:2]),
            "mm_per_pixel": float(mm_per_pixel),
            "signed_pixels": 0.0,
            "moved": False,
            "partner_row": partner_row,
            "partner_initial": partner_initial,
            "live_committed": False,
        }

    def apply_drag_motion(self, state: dict[str, object] | None, dx: int | float, dy: int | float) -> None:
        if state is None:
            return
        try:
            cursor_delta = np.asarray((float(dx), -float(dy)), dtype=float)
            direction = np.asarray(state.get("display_direction"), dtype=float).reshape(-1)[:2]
            signed_pixels = float(np.dot(cursor_delta, direction))
            mm_per_pixel = float(state.get("mm_per_pixel", 0.0))
            initial = float(state.get("initial_thickness", 0.0))
        except Exception:
            return
        if not np.isfinite(signed_pixels) or not np.isfinite(mm_per_pixel) or mm_per_pixel <= 0.0:
            return
        total_pixels = float(state.get("signed_pixels", 0.0)) + signed_pixels
        pending = initial + total_pixels * mm_per_pixel
        if not np.isfinite(pending):
            return
        state["signed_pixels"] = float(total_pixels)
        state["pending_thickness"] = float(pending)
        state["moved"] = bool(abs(float(pending) - initial) > 1e-9)
        try:
            row_index = int(state.get("row_index", -1))
        except Exception:
            row_index = -1
        status = f"S{row_index} Thickness drag: {initial:.6g} -> {pending:.6g} mm. Release to apply."
        # Quick Estimation: live conjugate + FOV feedback while dragging a
        # conjugate gap. With Live Mode on, commit the move into the model and
        # schedule a debounced live retrace so the geometry follows; otherwise
        # just preview the readout. A forbidden value (WD<FL) flashes the arrow.
        try:
            qe = self.inspector._quick_estimation_service()
        except Exception:
            qe = None
        try:
            live = bool(self.inspector._live_mode_enabled())
        except Exception:
            live = False
        try:
            if qe is not None and qe.is_enabled():
                is_object_gap = int(row_index) == qe.object_thickness_row()
                forbidden = bool(is_object_gap and qe.forbidden_for_object_distance(float(pending)))
                if forbidden:
                    self.inspector._start_thickness_forbidden_flash(
                        int(row_index),
                        f"Working distance {pending:.6g} mm below focal length -- no real image.",
                    )
                else:
                    self.inspector._stop_thickness_forbidden_flash()
                if live and not forbidden:
                    # commit pending + solve partner so the live retrace shows it.
                    self.editor.rows[int(row_index)].thickness = float(pending)
                    qe.solve_dependent(int(row_index))
                    qe.update_readout()
                    state["live_committed"] = True
                    self.inspector.schedule_live_refresh("thickness drag")
                    status = f"S{row_index} Thickness drag (live): {initial:.6g} -> {pending:.6g} mm."
                else:
                    preview = qe.preview_state(int(row_index), float(pending))
                    if preview is not None:
                        qe.update_readout(preview)
                        img = preview.get("image_distance")
                        fov = preview.get("fov_full")
                        if img is not None and fov is not None:
                            status = (
                                f"Quick Estimation: object {pending:.6g} mm -> image {img:.6g} mm, "
                                f"FOV {fov:.6g} mm. Release to apply."
                            )
                    if forbidden:
                        status = f"⛔ Working distance {pending:.6g} mm < focal length -- no real image."
        except Exception:
            pass
        self.inspector.status_var.set(status)

    def finish_drag(self, state: dict[str, object] | None) -> None:
        if state is None:
            return
        try:
            self.inspector._stop_thickness_forbidden_flash()
        except Exception:
            pass
        try:
            row_index = int(state.get("row_index", -1))
            pending = float(state.get("pending_thickness", state.get("initial_thickness", 0.0)))
            initial = float(state.get("initial_thickness", 0.0))
        except Exception:
            return
        # If Live Mode committed the move into the model during the drag, restore
        # both conjugate gaps to their pre-drag values first, so the single
        # history capture inside apply_dimension_value brackets the whole drag.
        if state.get("live_committed"):
            try:
                self.editor.rows[row_index].thickness = initial
                partner_row = state.get("partner_row")
                partner_initial = state.get("partner_initial")
                if partner_row is not None and partner_initial is not None:
                    self.editor.rows[int(partner_row)].thickness = float(partner_initial)
            except Exception:
                pass
        if not bool(state.get("moved", False)) or abs(pending - initial) <= 1e-9:
            if state.get("live_committed"):
                self.inspector.refresh_from_editor(force_retrace=True)
            self.inspector.status_var.set(f"S{row_index} Thickness drag: no change.")
            return
        self.apply_dimension_value(row_index, pending)

    def _destroy_inline_editor(self) -> None:
        window = self._inline_editor_window
        self._inline_editor_window = None
        self._inline_editor_row_index = None
        self._inline_editor_committing = False
        if window is None:
            return
        try:
            if window.winfo_exists():
                window.destroy()
        except Exception:
            pass

    def has_inline_editor(self) -> bool:
        window = self._inline_editor_window
        if window is None:
            return False
        try:
            return bool(window.winfo_exists())
        except Exception:
            return False

    def cancel_inline_editor(self) -> None:
        self._destroy_inline_editor()
        try:
            self.inspector.status_var.set("Thickness edit cancelled.")
        except Exception:
            pass

    def _position_inline_editor(self, window: tk.Toplevel) -> None:
        # Reuse the proven LED-import centering helper: withdraw -> set geometry
        # -> deiconify -> re-apply geometry after_idle + after(80ms). The re-apply
        # after the window is mapped is what makes it land on screen centre
        # reliably under Wayland / layer-shell (a one-shot geometry() is ignored).
        try:
            self.editor._show_centered_dialog(window)
            return
        except Exception:
            pass
        try:
            window.update_idletasks()
            width = max(int(window.winfo_reqwidth()), 260)
            height = max(int(window.winfo_reqheight()), 80)
            screen_w = max(int(window.winfo_screenwidth()), width)
            screen_h = max(int(window.winfo_screenheight()), height)
            x = max((screen_w - width) // 2, 0)
            y = max((screen_h - height) // 2, 0)
            window.geometry(f"{width}x{height}+{x}+{y}")
            window.deiconify()
            window.lift()
        except Exception:
            pass

    def _row_label(self, row_index: int) -> str:
        if not (0 <= int(row_index) < len(self.editor.rows)):
            return f"S{int(row_index)}"
        row = self.editor.rows[int(row_index)]
        return f"S{int(row_index)}: {row.name or row.surface or 'Surface'}"

    def apply_dimension_value(self, row_index: int, next_value: float) -> bool:
        row_index = int(row_index)
        if not (0 <= row_index < len(self.editor.rows) - 1):
            self.inspector.status_var.set("Thickness dimension: choose a non-terminal table row.")
            return False
        try:
            next_value = float(next_value)
        except Exception:
            self.inspector.status_var.set("Thickness must be a finite number.")
            return False
        if not np.isfinite(next_value):
            self.inspector.status_var.set("Thickness must be a finite number.")
            return False
        # A re-anchored dimension spans Previous->Next elements: editing its value
        # MOVES the Next (downstream) element by one gap, NOT rows[row_index] with a
        # Quick-Estimation re-solve (which used to shift the wrong element). The
        # editor routine performs the sequential move; we only refresh on success.
        override = None
        try:
            override = self.editor._dimension_anchor_override_for_row(row_index)
        except Exception:
            override = None
        if isinstance(override, dict):
            applied = False
            try:
                applied = bool(
                    self.editor.apply_reanchored_dimension_value(row_index, next_value)
                )
            except Exception as exc:  # pragma: no cover - defensive
                self.editor.append_debug(f"re-anchored dimension edit failed: {exc}")
                applied = False
            if applied:
                self.inspector.refresh_from_editor(force_retrace=True)
            else:
                self.inspector.status_var.set(
                    f"S{row_index} re-anchored value couldn't move an element "
                    "(end not on an optical surface). Re-pick onto a surface to move it."
                )
            return applied
        self.editor._begin_history_capture()
        self.editor.rows[row_index].thickness = next_value
        # Quick Estimation: setting one conjugate gap re-solves the other so the
        # image stays focused on the pinned sensor; FOV updates from the new
        # magnification. The dragged/typed gap becomes the independent variable.
        qe_note = ""
        try:
            qe = self.inspector._quick_estimation_service()
            if qe.is_enabled():
                _ok, qe_note = qe.solve_dependent(int(row_index))
        except Exception as exc:  # pragma: no cover - defensive
            self.editor.append_debug(f"Quick Estimation solve skipped: {exc}")
            qe_note = ""
        self.editor._sync_table()
        self.editor._select_table_row(row_index)
        self.editor._commit_history_capture()
        self.editor._invalidate_preview_scene_trace()
        self.editor._sync_trace_state_badge()
        base_msg = f"S{row_index} Thickness set to {next_value:.6g} mm."
        if qe_note:
            base_msg = f"{base_msg} {qe_note}"
        self.editor.status_var.set(f"{base_msg} Other table thickness values are unchanged.")
        self.inspector.status_var.set(base_msg)
        self.inspector.refresh_from_editor(force_retrace=True)
        try:
            self.inspector._quick_estimation_service().update_readout()
        except Exception:
            pass
        return True

    def edit_dimension(self, row_index: int) -> None:
        row_index = int(row_index)
        if not (0 <= row_index < len(self.editor.rows) - 1):
            self.inspector.status_var.set("Thickness dimension: choose a non-terminal table row.")
            return
        row = self.editor.rows[row_index]
        try:
            current = float(getattr(row, "thickness", 0.0) or 0.0)
        except Exception:
            current = 0.0
        # bugs/0054: a re-anchored row's editable quantity is the MEASURED distance
        # shown on the magenta arrow (|ref_z - fixed_z|), not the model gap
        # thickness -- prefill that so the value the user edits matches what they
        # clicked (and what the move targets). Earlier this showed rows[i].thickness
        # (e.g. the 275 mm object gap instead of the 212.6 mm object->LED measure).
        try:
            override = self.editor._dimension_anchor_override_for_row(row_index)
        except Exception:
            override = None
        if isinstance(override, dict):
            try:
                ref_z = float(override.get("ref_z"))
                fixed_z = override.get("fixed_z")
                if fixed_z is not None:
                    fixed_z = float(fixed_z)
                    if np.isfinite(ref_z) and np.isfinite(fixed_z):
                        current = abs(ref_z - fixed_z)
            except Exception:
                pass
        self._destroy_inline_editor()
        value_var = tk.StringVar(value=f"{current:.6g}")
        window = tk.Toplevel(self.inspector)
        self._inline_editor_window = window
        self._inline_editor_row_index = row_index
        try:
            window.withdraw()  # appear directly centred (no top-left flicker)
            window.title("Edit Thickness")
            window.transient(self.inspector)
            window.resizable(False, False)
        except Exception:
            pass
        frame = ttk.Frame(window, padding=8)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text=self._row_label(row_index)).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(frame, text="Thickness [mm]").grid(row=1, column=0, sticky="w", pady=(6, 0))
        entry = ttk.Entry(frame, textvariable=value_var, width=16)
        entry.grid(row=1, column=1, sticky="ew", padx=(8, 6), pady=(6, 0))

        def commit(_event=None):
            if self._inline_editor_committing:
                return "break"
            self._inline_editor_committing = True
            try:
                next_value = float(value_var.get())
            except Exception:
                self._inline_editor_committing = False
                self.inspector.status_var.set("Thickness must be a finite number.")
                try:
                    entry.focus_set()
                    entry.selection_range(0, "end")
                except Exception:
                    pass
                return "break"
            if not np.isfinite(next_value):
                self._inline_editor_committing = False
                self.inspector.status_var.set("Thickness must be a finite number.")
                try:
                    entry.focus_set()
                    entry.selection_range(0, "end")
                except Exception:
                    pass
                return "break"
            self._destroy_inline_editor()
            self.apply_dimension_value(row_index, next_value)
            return "break"

        def cancel(_event=None):
            self.cancel_inline_editor()
            return "break"

        def keep_focus_in_window(_event=None):
            # bugs/0053 #5: moving the mouse over the embedded VTK canvas used to
            # steal keyboard focus (focus-follows-mouse), which fired <FocusOut>
            # and committed/closed the editor mid-type -- "the window disappears if
            # the mouse moves a little." Don't commit on focus loss; pull focus
            # back to the entry so the user can keep typing. Committing is now
            # Enter / OK only (Esc / window-close cancels). If focus moved to a
            # child of this window (e.g. the OK button) leave it alone.
            try:
                if not window.winfo_exists():
                    return None
                focus = window.focus_get()
                if focus is not None and focus.winfo_toplevel() is window:
                    return None
                entry.focus_set()
            except Exception:
                pass
            return None

        ttk.Button(frame, text="OK", command=commit, width=6).grid(row=1, column=2, sticky="e", pady=(6, 0))
        window.bind("<Return>", commit, add="+")
        window.bind("<KP_Enter>", commit, add="+")
        window.bind("<Escape>", cancel, add="+")
        entry.bind("<FocusOut>", keep_focus_in_window, add="+")
        try:
            window.protocol("WM_DELETE_WINDOW", cancel)
        except Exception:
            pass
        self._position_inline_editor(window)
        # Grab input so the embedded VTK canvas can't take focus-follows-mouse
        # focus while the user is typing (the root cause of the vanishing editor).
        try:
            window.grab_set()
        except Exception:
            pass
        try:
            entry.focus_set()
            entry.selection_range(0, "end")
        except Exception:
            pass
        self.inspector.status_var.set(f"Editing {self._row_label(row_index)} Thickness. Press Enter to apply or Esc to cancel.")
