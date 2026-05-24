"""Visual CAD/STL placement dialog."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

import numpy as np

pv = None
vtkActor = None
vtkAxesActor = None
vtkDataSetMapper = None
vtkOrientationMarkerWidget = None
vtkRenderer = None
vtkTkRenderWindowInteractor = None


# Layout-editor symbols are loaded lazily because layout_editor imports this dialog.
def _sync_layout_symbols() -> None:
    from KrakenOS.UI import layout_editor as le

    names = (
        "Kraken3DInspector",
        "OPTICAL_SOLID_FACES_ADVANCED_ATTR",
        "OPTICAL_SOLID_FACE_FIT_ROLL_DEFAULT",
        "OPTICAL_SOLID_FACE_FIT_ROLL_VALUES",
        "STL_AXIS_TO_LAYOUT_Z_TILTS",
        "SurfaceRow",
        "StlMeshDiagnostics",
        "_VTK_TK_UNAVAILABLE_REASON",
        "_load_3d_backends",
        "_optical_solid_face_marker_label",
        "_prepare_vtk_tk_widget",
        "_rotation_matrix_from_kraken_tilts",
        "_short_error_message",
        "normalize_optical_solid_face_metadata",
        "normalize_optical_solid_face_record",
        "optical_solid_face_world_markers",
        "optical_solid_face_world_records",
        "optical_solid_virtual_plane_world_markers",
        "rotated_stl_bounds",
        "select_optical_solid_anchor_face",
        "short_stl_mesh_diagnostics",
        "solve_optical_solid_face_fit",
        "pv",
        "vtkActor",
        "vtkAxesActor",
        "vtkDataSetMapper",
        "vtkOrientationMarkerWidget",
        "vtkRenderer",
        "vtkTkRenderWindowInteractor",
    )
    globals().update({name: getattr(le, name) for name in names})


class OpticalStlPlacementDialog(tk.Toplevel):
    """Visual pose editor for a file-backed optical CAD/STL row."""

    def __init__(
        self,
        editor: "KrakenLayoutEditor",
        row_index: int,
        row: SurfaceRow,
        path: Path,
        diagnostics: StlMeshDiagnostics,
    ) -> None:
        _sync_layout_symbols()
        _load_3d_backends()
        if pv is None or vtkTkRenderWindowInteractor is None or vtkRenderer is None:
            raise RuntimeError(_VTK_TK_UNAVAILABLE_REASON or "Embedded VTK/Tk CAD/STL placement preview unavailable")
        super().__init__(editor)
        self.editor = editor
        self.row_index = int(row_index)
        self.path = Path(path).expanduser()
        self.diagnostics = diagnostics
        z_positions = editor._row_z_positions()
        self.z_station = float(z_positions[self.row_index]) if 0 <= self.row_index < len(z_positions) else 0.0
        self._renderer = None
        self._vtk_widget = None
        self._vtk_interactor = None
        self._orientation_widget = None
        self._render_after_id: str | None = None
        self._suspend_trace = False
        self._camera_preset = "iso"
        self.status_var = tk.StringVar(value="CAD/STL placement preview ready")
        self.tilt_x_var = tk.StringVar(value=self._format_pose(row.tilt_x))
        self.tilt_y_var = tk.StringVar(value=self._format_pose(row.tilt_y))
        self.tilt_z_var = tk.StringVar(value=self._format_pose(row.tilt_z))
        self.desp_x_var = tk.StringVar(value=self._format_pose(row.desp_x))
        self.desp_y_var = tk.StringVar(value=self._format_pose(row.desp_y))
        self.desp_z_var = tk.StringVar(value=self._format_pose(row.desp_z))
        self.axis_var = tk.StringVar(value="+Z")
        self._face_metadata = normalize_optical_solid_face_metadata(
            (row.advanced or {}).get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}),
            source_stl=str(self.path),
        )
        self._face_anchor_choices = self._build_face_anchor_choices(self._face_metadata)
        self.face_anchor_var = tk.StringVar(value=self._default_face_anchor_choice())
        self.roll_constraint_var = tk.StringVar(value=OPTICAL_SOLID_FACE_FIT_ROLL_DEFAULT)
        self.title(f"Visual CAD/STL Placement - S{self.row_index}")
        self.geometry("1180x780")
        self.minsize(860, 560)
        self.transient(editor)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(1, weight=1)

        summary = (
            f"S{self.row_index}: {row.name or row.surface} | {self.path.name} | "
            f"{short_stl_mesh_diagnostics(diagnostics)} | row Z={self.z_station:.6g} mm"
        )
        ttk.Label(self, text=summary, padding=(10, 8, 10, 0), wraplength=1120).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
        )

        controls = ttk.Frame(self, padding=10)
        controls.grid(row=1, column=0, sticky="nsw")
        viewer_host = ttk.Frame(self, padding=(0, 10, 10, 10))
        viewer_host.grid(row=1, column=1, sticky="nsew")
        viewer_host.columnconfigure(0, weight=1)
        viewer_host.rowconfigure(0, weight=1)

        self._build_controls(controls)
        _prepare_vtk_tk_widget(viewer_host)
        self._vtk_widget = vtkTkRenderWindowInteractor(viewer_host, width=760, height=660)
        self._vtk_widget.grid(row=0, column=0, sticky="nsew")
        render_window = self._vtk_widget.GetRenderWindow()
        self._renderer = vtkRenderer()
        render_window.AddRenderer(self._renderer)
        self._renderer.SetBackground(1.0, 1.0, 1.0)
        self._vtk_interactor = render_window.GetInteractor()
        if vtkOrientationMarkerWidget is not None and vtkAxesActor is not None and self._vtk_interactor is not None:
            axes = vtkAxesActor()
            self._orientation_widget = vtkOrientationMarkerWidget()
            self._orientation_widget.SetOrientationMarker(axes)
            self._orientation_widget.SetInteractor(self._vtk_interactor)
            self._orientation_widget.SetViewport(0.0, 0.0, 0.16, 0.16)
            self._orientation_widget.SetEnabled(1)
            self._orientation_widget.InteractiveOff()
        self._vtk_widget.Initialize()
        ttk.Label(self, textvariable=self.status_var, padding=(10, 0, 10, 8)).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
        )
        for var in (
            self.tilt_x_var,
            self.tilt_y_var,
            self.tilt_z_var,
            self.desp_x_var,
            self.desp_y_var,
            self.desp_z_var,
        ):
            var.trace_add("write", self._schedule_render)
        self.after(60, lambda: self._render_preview(reset_camera=True))

    @staticmethod
    def _format_pose(value: float) -> str:
        return f"{float(value):.12g}"

    @staticmethod
    def _face_choice_text(face: dict[str, object]) -> str:
        face_id = str(face.get("face_id", "") or "").strip() or "Face"
        label = _optical_solid_face_marker_label(face)
        return f"{face_id}: {label}" if label else face_id

    def _build_face_anchor_choices(self, metadata: dict[str, object]) -> dict[str, str]:
        choices = {"Auto": ""}
        for face in list(metadata.get("faces", []) or []):
            if not isinstance(face, dict):
                continue
            normalized = normalize_optical_solid_face_record(face)
            choices[self._face_choice_text(normalized)] = str(normalized.get("face_id", "") or "").strip()
        return choices

    def _default_face_anchor_choice(self) -> str:
        face = select_optical_solid_anchor_face(self._face_metadata)
        if face is None:
            return "Auto"
        face_id = str(face.get("face_id", "") or "").strip()
        for label, candidate_id in self._face_anchor_choices.items():
            if candidate_id == face_id:
                return label
        return "Auto"

    def _selected_face_anchor_id(self) -> str:
        return str(self._face_anchor_choices.get(self.face_anchor_var.get().strip(), "") or "").strip()

    def _selected_face_record(self) -> dict[str, object] | None:
        return select_optical_solid_anchor_face(self._face_metadata, face_id=self._selected_face_anchor_id())

    def _selected_face_world_record(
        self,
        tilts: tuple[float, float, float] | None = None,
        desp: tuple[float, float, float] | None = None,
    ) -> dict[str, object] | None:
        if tilts is None or desp is None:
            tilts, desp = self._pose_values()
        preview_row = self._preview_face_role_row(tilts, desp)
        face_id = self._selected_face_anchor_id()
        for face in optical_solid_face_world_records(preview_row, self.z_station, assigned_only=False):
            if face_id and str(face.get("face_id", "") or "").strip() == face_id:
                return face
        if face_id:
            return None
        selected = self._selected_face_record()
        if selected is None:
            return None
        selected_id = str(selected.get("face_id", "") or "").strip()
        for face in optical_solid_face_world_records(preview_row, self.z_station, assigned_only=False):
            if str(face.get("face_id", "") or "").strip() == selected_id:
                return face
        return None

    def _reference_anchor_point(
        self,
        tilts: tuple[float, float, float] | None = None,
        desp: tuple[float, float, float] | None = None,
    ) -> np.ndarray:
        if tilts is None or desp is None:
            tilts, desp = self._pose_values()
        face = self._selected_face_world_record(tilts, desp)
        if face is not None:
            centroid = np.asarray(face.get("centroid_world", (np.nan, np.nan, np.nan)), dtype=float)
            if centroid.size >= 3 and np.all(np.isfinite(centroid[:3])):
                return centroid[:3]
        return np.asarray((float(desp[0]), float(desp[1]), self.z_station + float(desp[2])), dtype=float)

    def _build_controls(self, controls: ttk.Frame) -> None:
        row_cursor = 0
        ttk.Label(
            controls,
            text="Pose is previewed in 3D. Apply writes Tilt/Decenter to the selected row; the 2D layout uses the same row pose.",
            wraplength=300,
            justify="left",
        ).grid(row=row_cursor, column=0, columnspan=4, sticky="ew", pady=(0, 10))
        row_cursor += 1

        ttk.Label(controls, text="Camera").grid(row=row_cursor, column=0, sticky="w", pady=(0, 4))
        for label, preset in (("Iso", "iso"), ("ZY", "zy"), ("XY", "xy"), ("XZ", "xz")):
            ttk.Button(controls, text=label, width=5, command=lambda p=preset: self.set_camera_preset(p)).grid(
                row=row_cursor,
                column={"Iso": 1, "ZY": 2, "XY": 3, "XZ": 4}[label],
                sticky="w",
                padx=(4, 0),
                pady=(0, 4),
            )
        row_cursor += 1

        ttk.Separator(controls).grid(row=row_cursor, column=0, columnspan=5, sticky="ew", pady=8)
        row_cursor += 1

        ttk.Label(controls, text="Anchor face").grid(row=row_cursor, column=0, columnspan=2, sticky="w")
        anchor_menu = ttk.Combobox(
            controls,
            textvariable=self.face_anchor_var,
            values=tuple(self._face_anchor_choices.keys()),
            state="readonly",
            width=22,
        )
        anchor_menu.grid(row=row_cursor, column=2, columnspan=3, sticky="ew", padx=(4, 0), pady=(0, 4))
        row_cursor += 1
        ttk.Label(controls, text="Roll constraint").grid(row=row_cursor, column=0, columnspan=2, sticky="w")
        ttk.Combobox(
            controls,
            textvariable=self.roll_constraint_var,
            values=OPTICAL_SOLID_FACE_FIT_ROLL_VALUES,
            state="readonly",
            width=22,
        ).grid(row=row_cursor, column=2, columnspan=3, sticky="ew", padx=(4, 0), pady=(0, 4))
        row_cursor += 1
        ttk.Button(controls, text="Face -> +Z", command=lambda: self.fit_selected_face(+1.0)).grid(
            row=row_cursor,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 2),
        )
        ttk.Button(controls, text="Face -> -Z", command=lambda: self.fit_selected_face(-1.0)).grid(
            row=row_cursor,
            column=2,
            columnspan=3,
            sticky="ew",
            padx=(6, 0),
            pady=(0, 2),
        )
        row_cursor += 1
        ttk.Button(controls, text="Face -> Ray", command=lambda: self.fit_selected_face_to_selected_ray(+1.0)).grid(
            row=row_cursor,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 2),
        )
        ttk.Button(controls, text="Face <- Ray", command=lambda: self.fit_selected_face_to_selected_ray(-1.0)).grid(
            row=row_cursor,
            column=2,
            columnspan=3,
            sticky="ew",
            padx=(6, 0),
            pady=(0, 2),
        )
        row_cursor += 1
        ttk.Button(controls, text="Face -> Path", command=lambda: self.fit_selected_face_to_current_path(+1.0)).grid(
            row=row_cursor,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 2),
        )
        ttk.Button(controls, text="Face <- Path", command=lambda: self.fit_selected_face_to_current_path(-1.0)).grid(
            row=row_cursor,
            column=2,
            columnspan=3,
            sticky="ew",
            padx=(6, 0),
            pady=(0, 2),
        )
        row_cursor += 1
        ttk.Button(controls, text="Anchor X/Y", command=self.center_anchor_xy).grid(
            row=row_cursor,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(0, 2),
        )
        ttk.Button(controls, text="Anchor On Row", command=self.place_anchor_on_row).grid(
            row=row_cursor,
            column=2,
            columnspan=3,
            sticky="ew",
            padx=(6, 0),
            pady=(0, 2),
        )
        row_cursor += 1
        ttk.Label(
            controls,
            text="Face fit aligns the chosen optical face to the optical axis or a traced ray/path frame and solves the anchor onto the row plane or nearest target point.",
            wraplength=300,
            justify="left",
            foreground="#475569",
        ).grid(row=row_cursor, column=0, columnspan=5, sticky="ew", pady=(0, 8))
        row_cursor += 1

        ttk.Label(controls, text="Local axis -> layout +Z").grid(row=row_cursor, column=0, columnspan=2, sticky="w")
        ttk.Combobox(
            controls,
            textvariable=self.axis_var,
            values=tuple(STL_AXIS_TO_LAYOUT_Z_TILTS.keys()),
            state="readonly",
            width=7,
        ).grid(row=row_cursor, column=2, sticky="w", padx=(4, 0))
        ttk.Button(controls, text="Fit", command=self.apply_axis_fit).grid(row=row_cursor, column=3, columnspan=2, sticky="ew", padx=(4, 0))
        row_cursor += 1

        pose_rows = (
            ("TiltX [deg]", self.tilt_x_var),
            ("TiltY [deg]", self.tilt_y_var),
            ("TiltZ [deg]", self.tilt_z_var),
            ("DespX [mm]", self.desp_x_var),
            ("DespY [mm]", self.desp_y_var),
            ("DespZ [mm]", self.desp_z_var),
        )
        for label, var in pose_rows:
            ttk.Label(controls, text=label).grid(row=row_cursor, column=0, columnspan=2, sticky="w", pady=2)
            ttk.Entry(controls, textvariable=var, width=12).grid(row=row_cursor, column=2, columnspan=3, sticky="ew", pady=2)
            row_cursor += 1

        ttk.Separator(controls).grid(row=row_cursor, column=0, columnspan=5, sticky="ew", pady=8)
        row_cursor += 1

        for label, axis, delta in (
            ("X -90", "x", -90.0),
            ("X +90", "x", 90.0),
            ("Y -90", "y", -90.0),
            ("Y +90", "y", 90.0),
            ("Z -90", "z", -90.0),
            ("Z +90", "z", 90.0),
        ):
            ttk.Button(controls, text=label, command=lambda a=axis, d=delta: self.rotate_pose(a, d)).grid(
                row=row_cursor,
                column=(0 if "-90" in label else 2),
                columnspan=2,
                sticky="ew",
                padx=(0 if "-90" in label else 6, 0),
                pady=2,
            )
            if "+90" in label:
                row_cursor += 1

        ttk.Button(controls, text="Center X/Y", command=self.center_xy).grid(row=row_cursor, column=0, columnspan=2, sticky="ew", pady=(8, 2))
        ttk.Button(controls, text="Min Z On Row", command=self.place_front_on_row).grid(row=row_cursor, column=2, columnspan=3, sticky="ew", padx=(6, 0), pady=(8, 2))
        row_cursor += 1
        ttk.Button(controls, text="Reset Row Pose", command=self.reset_pose).grid(row=row_cursor, column=0, columnspan=2, sticky="ew", pady=2)
        ttk.Button(controls, text="Render", command=lambda: self._render_preview(reset_camera=False)).grid(row=row_cursor, column=2, columnspan=3, sticky="ew", padx=(6, 0), pady=2)
        row_cursor += 1
        ttk.Button(controls, text="Assign Optical Faces", command=self.open_face_roles).grid(
            row=row_cursor,
            column=0,
            columnspan=5,
            sticky="ew",
            pady=(2, 2),
        )
        row_cursor += 1

        ttk.Separator(controls).grid(row=row_cursor, column=0, columnspan=5, sticky="ew", pady=8)
        row_cursor += 1
        ttk.Button(controls, text="Apply, Close, Refresh 2D", command=self.apply_and_refresh).grid(
            row=row_cursor,
            column=0,
            columnspan=5,
            sticky="ew",
            pady=(0, 4),
        )
        row_cursor += 1
        ttk.Button(controls, text="Cancel Without Applying", command=self.destroy).grid(row=row_cursor, column=0, columnspan=5, sticky="ew")

    def _pose_values(self) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
        try:
            tilts = (
                float(self.tilt_x_var.get().strip() or "0"),
                float(self.tilt_y_var.get().strip() or "0"),
                float(self.tilt_z_var.get().strip() or "0"),
            )
            desp = (
                float(self.desp_x_var.get().strip() or "0"),
                float(self.desp_y_var.get().strip() or "0"),
                float(self.desp_z_var.get().strip() or "0"),
            )
        except Exception as exc:
            raise ValueError(f"Pose fields must be numeric: {exc}") from exc
        return tilts, desp

    def _set_pose(
        self,
        *,
        tilts: tuple[float, float, float] | None = None,
        desp: tuple[float, float, float] | None = None,
        reset_camera: bool = False,
    ) -> None:
        current_tilts, current_desp = self._pose_values()
        next_tilts = current_tilts if tilts is None else tuple(float(value) for value in tilts)
        next_desp = current_desp if desp is None else tuple(float(value) for value in desp)
        self._suspend_trace = True
        try:
            self.tilt_x_var.set(self._format_pose(next_tilts[0]))
            self.tilt_y_var.set(self._format_pose(next_tilts[1]))
            self.tilt_z_var.set(self._format_pose(next_tilts[2]))
            self.desp_x_var.set(self._format_pose(next_desp[0]))
            self.desp_y_var.set(self._format_pose(next_desp[1]))
            self.desp_z_var.set(self._format_pose(next_desp[2]))
        finally:
            self._suspend_trace = False
        self._render_preview(reset_camera=reset_camera)

    def rotate_pose(self, axis: str, delta_deg: float) -> None:
        tilts, desp = self._pose_values()
        values = list(tilts)
        index = {"x": 0, "y": 1, "z": 2}[axis]
        values[index] += float(delta_deg)
        self._set_pose(tilts=tuple(values), desp=desp)

    def apply_axis_fit(self) -> None:
        tilts = STL_AXIS_TO_LAYOUT_Z_TILTS.get(self.axis_var.get().strip(), STL_AXIS_TO_LAYOUT_Z_TILTS["+Z"])
        _bounds_min, _bounds_max, center = rotated_stl_bounds(self.path, tilts)
        desp = (-float(center[0]), -float(center[1]), -float(_bounds_min[2]))
        self._set_pose(tilts=tilts, desp=desp, reset_camera=True)

    def center_xy(self) -> None:
        tilts, desp = self._pose_values()
        _bounds_min, _bounds_max, center = rotated_stl_bounds(self.path, tilts)
        self._set_pose(desp=(-float(center[0]), -float(center[1]), desp[2]))

    def center_anchor_xy(self) -> None:
        tilts, desp = self._pose_values()
        face = self._selected_face_world_record(tilts, desp)
        if face is None:
            self.status_var.set("Anchor X/Y: assign or select an optical face first.")
            return
        centroid = np.asarray(face.get("centroid_world", (np.nan, np.nan, np.nan)), dtype=float)
        if centroid.size < 3 or not np.all(np.isfinite(centroid[:3])):
            self.status_var.set("Anchor X/Y: selected face centroid is unavailable.")
            return
        new_desp = (
            float(desp[0]) - float(centroid[0]),
            float(desp[1]) - float(centroid[1]),
            float(desp[2]),
        )
        self._set_pose(tilts=tilts, desp=new_desp)
        label = str(face.get("face_id", "") or "")
        self.status_var.set(f"Anchor X/Y: centered {label or 'selected face'} on the optical axis.")

    def place_front_on_row(self) -> None:
        tilts, desp = self._pose_values()
        bounds_min, _bounds_max, _center = rotated_stl_bounds(self.path, tilts)
        self._set_pose(desp=(desp[0], desp[1], -float(bounds_min[2])))

    def place_anchor_on_row(self) -> None:
        tilts, desp = self._pose_values()
        face = self._selected_face_world_record(tilts, desp)
        if face is None:
            self.status_var.set("Anchor On Row: assign or select an optical face first.")
            return
        centroid = np.asarray(face.get("centroid_world", (np.nan, np.nan, np.nan)), dtype=float)
        if centroid.size < 3 or not np.all(np.isfinite(centroid[:3])):
            self.status_var.set("Anchor On Row: selected face centroid is unavailable.")
            return
        delta_z = self.z_station - float(centroid[2])
        new_desp = (
            float(desp[0]),
            float(desp[1]),
            float(desp[2]) + delta_z,
        )
        self._set_pose(tilts=tilts, desp=new_desp)
        label = str(face.get("face_id", "") or "")
        self.status_var.set(f"Anchor On Row: moved {label or 'selected face'} onto the row station.")

    def reset_pose(self) -> None:
        row = self.editor.rows[self.row_index]
        self._set_pose(
            tilts=(float(row.tilt_x), float(row.tilt_y), float(row.tilt_z)),
            desp=(float(row.desp_x), float(row.desp_y), float(row.desp_z)),
            reset_camera=True,
        )

    def open_face_roles(self) -> None:
        self.editor.open_optical_solid_face_role_editor(self.row_index)

    def fit_selected_face(self, direction_sign: float) -> None:
        try:
            solution = solve_optical_solid_face_fit(
                self._face_metadata,
                face_id=self._selected_face_anchor_id(),
                target_normal=(0.0, 0.0, 1.0 if float(direction_sign) >= 0.0 else -1.0),
                roll_mode=self.roll_constraint_var.get().strip() or OPTICAL_SOLID_FACE_FIT_ROLL_DEFAULT,
            )
        except Exception as exc:
            self.status_var.set(f"Face fit failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"CAD/STL face fit failed: {exc}")
            return
        if solution is None:
            self.status_var.set("Face fit: assign or select an optical face first.")
            return
        self._set_pose(
            tilts=tuple(float(value) for value in solution["tilts"]),
            desp=tuple(float(value) for value in solution["desp"]),
            reset_camera=True,
        )
        label = str(solution.get("label", "") or solution.get("face_id", "") or "selected face").strip()
        roll_side = str(solution.get("roll_side", "") or "").strip()
        roll_text = f" with {roll_side} roll" if roll_side else ""
        target_text = "+Z" if float(direction_sign) >= 0.0 else "-Z"
        self.status_var.set(f"Face fit: aligned {label} to {target_text}{roll_text} and centered it on the row plane.")

    def _fit_selected_face_to_target(
        self,
        *,
        target_point,
        target_direction,
        direction_sign: float,
        target_label: str,
        detail: str = "",
    ) -> None:
        sign = 1.0 if float(direction_sign) >= 0.0 else -1.0
        direction = np.asarray(target_direction, dtype=float).reshape(3)
        point = np.asarray(target_point, dtype=float).reshape(3)
        try:
            solution = solve_optical_solid_face_fit(
                self._face_metadata,
                face_id=self._selected_face_anchor_id(),
                target_normal=tuple(float(value) for value in direction * sign),
                target_point=self.editor._row_local_point_from_world(point, self.z_station),
                roll_mode=self.roll_constraint_var.get().strip() or OPTICAL_SOLID_FACE_FIT_ROLL_DEFAULT,
            )
        except Exception as exc:
            self.status_var.set(f"Face fit failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"CAD/STL face fit failed: {exc}")
            return
        if solution is None:
            self.status_var.set("Face fit: assign or select an optical face first.")
            return
        self._set_pose(
            tilts=tuple(float(value) for value in solution["tilts"]),
            desp=tuple(float(value) for value in solution["desp"]),
            reset_camera=True,
        )
        label = str(solution.get("label", "") or solution.get("face_id", "") or "selected face").strip()
        roll_side = str(solution.get("roll_side", "") or "").strip()
        roll_text = f" with {roll_side} roll" if roll_side else ""
        direction_text = "->" if sign >= 0.0 else "<-"
        extra = f" ({detail})" if detail else ""
        self.status_var.set(
            f"Face fit: aligned {label} {direction_text} {target_label}{roll_text} and snapped the anchor to the target point{extra}."
        )

    def fit_selected_face_to_selected_ray(self, direction_sign: float) -> None:
        reference = self._reference_anchor_point()
        try:
            frame = self.editor._selected_ray_frame_near_point(reference)
        except Exception as exc:
            self.status_var.set(f"Face fit to Ray unavailable: {_short_error_message(exc)}")
            self.editor.append_debug(f"CAD/STL face-to-ray fit unavailable: {exc}")
            return
        detail_parts = [f"ray {int(frame.get('ray_index', -1))}"]
        branch_detail = self.editor._branch_path_compact_detail(frame.get("branch_path", ""))
        if branch_detail:
            detail_parts.append(branch_detail)
        self._fit_selected_face_to_target(
            target_point=frame["target_point"],
            target_direction=frame["direction"],
            direction_sign=direction_sign,
            target_label="Ray",
            detail=", ".join(part for part in detail_parts if part),
        )

    def fit_selected_face_to_current_path(self, direction_sign: float) -> None:
        reference = self._reference_anchor_point()
        try:
            frame = self.editor._current_path_view_frame_near_point(reference)
        except Exception as exc:
            self.status_var.set(f"Face fit to Path unavailable: {_short_error_message(exc)}")
            self.editor.append_debug(f"CAD/STL face-to-path fit unavailable: {exc}")
            return
        branch_detail = self.editor._branch_path_compact_detail(frame.get("branch_path", ""))
        detail = branch_detail or f"{int(frame.get('sample_count', 0))} samples"
        self._fit_selected_face_to_target(
            target_point=frame["target_point"],
            target_direction=frame["direction"],
            direction_sign=direction_sign,
            target_label="Path",
            detail=detail,
        )

    def _schedule_render(self, *_args) -> None:
        if self._suspend_trace:
            return
        if self._render_after_id is not None:
            return
        try:
            self._render_after_id = self.after(80, self._render_preview)
        except Exception:
            self._render_after_id = None

    def _add_mesh_actor(
        self,
        mesh,
        *,
        color: tuple[float, float, float],
        opacity: float = 1.0,
        line_width: float = 1.0,
        wireframe: bool = False,
        flat: bool = False,
    ) -> None:
        if self._renderer is None or vtkActor is None or vtkDataSetMapper is None:
            return
        mapper = vtkDataSetMapper()
        mapper.SetInputData(mesh)
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.PickableOff()
        prop = actor.GetProperty()
        prop.SetColor(*color)
        prop.SetOpacity(float(opacity))
        prop.SetLineWidth(float(line_width))
        if wireframe:
            prop.SetRepresentationToWireframe()
        if flat:
            prop.SetInterpolationToFlat()
            prop.SetAmbient(0.55)
            prop.SetDiffuse(0.45)
        else:
            prop.SetInterpolationToPhong()
            prop.SetSpecular(0.15)
            prop.SetSpecularPower(12.0)
        self._renderer.AddActor(actor)

    def _stl_preview_mesh(self, tilts: tuple[float, float, float], desp: tuple[float, float, float]):
        mesh = pv.read(self.path).extract_surface(algorithm="dataset_surface").copy(deep=True)
        pts = np.asarray(mesh.points, dtype=float)
        if pts.ndim != 2 or pts.shape[0] == 0 or pts.shape[1] < 3:
            raise RuntimeError("STL preview mesh has no points")
        rotation = _rotation_matrix_from_kraken_tilts(*tilts)
        transformed = pts[:, :3] @ rotation.T
        transformed[:, 0] += float(desp[0])
        transformed[:, 1] += float(desp[1])
        transformed[:, 2] += self.z_station + float(desp[2])
        mesh.points = transformed
        return mesh

    def _add_reference_geometry(self, bounds_min: np.ndarray, bounds_max: np.ndarray, center: np.ndarray) -> None:
        span = max(float(np.max(bounds_max - bounds_min)), 1.0)
        axis_len = max(span * 1.4, 20.0)
        row_half = max(span * 0.8, 8.0)
        try:
            self._add_mesh_actor(pv.Line((0, 0, self.z_station - axis_len), (0, 0, self.z_station + axis_len)), color=(0.05, 0.05, 0.05), line_width=2.0)
            plane = pv.Plane(center=(0.0, 0.0, self.z_station), direction=(0.0, 0.0, 1.0), i_size=row_half * 2.0, j_size=row_half * 2.0, i_resolution=1, j_resolution=1)
            self._add_mesh_actor(plane, color=(0.86, 0.90, 0.96), opacity=0.22, wireframe=True)
            rotation = _rotation_matrix_from_kraken_tilts(*self._pose_values()[0])
            for vec, color in (
                (rotation @ np.array([1.0, 0.0, 0.0]), (0.85, 0.10, 0.10)),
                (rotation @ np.array([0.0, 1.0, 0.0]), (0.10, 0.62, 0.18)),
                (rotation @ np.array([0.0, 0.0, 1.0]), (0.12, 0.32, 0.86)),
            ):
                start = center
                end = center + vec * axis_len * 0.25
                self._add_mesh_actor(pv.Line(tuple(start), tuple(end)), color=color, line_width=4.0)
        except Exception:
            pass

    def _preview_face_role_row(self, tilts: tuple[float, float, float], desp: tuple[float, float, float]) -> SurfaceRow:
        row = SurfaceRow(**asdict(self.editor.rows[self.row_index]))
        row.tilt_x, row.tilt_y, row.tilt_z = (float(value) for value in tilts)
        row.desp_x, row.desp_y, row.desp_z = (float(value) for value in desp)
        return row

    def _add_face_role_overlays(self, tilts: tuple[float, float, float], desp: tuple[float, float, float], *, scene_radius: float) -> int:
        count = 0
        if pv is None:
            return count
        row = self._preview_face_role_row(tilts, desp)
        for marker in optical_solid_face_world_markers(row, self.z_station, assigned_only=True):
            try:
                start = np.asarray(marker.centroid, dtype=float)
                normal = np.asarray(marker.normal, dtype=float)
                normal_norm = float(np.linalg.norm(normal[:3]))
                if normal_norm <= 1e-12 or not np.isfinite(normal_norm):
                    continue
                normal = normal[:3] / normal_norm
                length = Kraken3DInspector._face_role_marker_scale(marker, scene_radius)
                self._add_mesh_actor(
                    pv.Sphere(radius=max(length * 0.08, 0.18), center=tuple(start[:3])),
                    color=marker.color,
                    opacity=0.98,
                    flat=True,
                )
                self._add_mesh_actor(
                    pv.Arrow(start=tuple(start[:3]), direction=tuple(normal), scale=length),
                    color=marker.color,
                    opacity=0.96,
                    flat=True,
                )
                count += 1
            except Exception as exc:
                self.editor.append_debug(f"CAD/STL placement face marker error: {exc}")
        return count

    def _add_virtual_plane_overlays(self, tilts: tuple[float, float, float], desp: tuple[float, float, float], *, scene_radius: float) -> int:
        count = 0
        if pv is None:
            return count
        row = self._preview_face_role_row(tilts, desp)
        for marker in optical_solid_virtual_plane_world_markers(row, self.z_station, assigned_only=True):
            try:
                center = np.asarray(marker.centroid, dtype=float)
                normal = np.asarray(marker.normal, dtype=float)
                norm = float(np.linalg.norm(normal[:3]))
                if norm <= 1e-12 or not np.isfinite(norm):
                    continue
                normal = normal[:3] / norm
                size = Kraken3DInspector._virtual_plane_marker_scale(marker, scene_radius)
                plane = pv.Plane(center=tuple(center[:3]), direction=tuple(normal), i_size=size, j_size=size, i_resolution=1, j_resolution=1)
                self._add_mesh_actor(plane, color=marker.color, opacity=0.16, flat=True)
                try:
                    edges = plane.extract_feature_edges(boundary_edges=True, feature_edges=False, manifold_edges=False)
                    if int(getattr(edges, "n_points", 0)) > 0:
                        self._add_mesh_actor(edges, color=marker.color, opacity=0.96, line_width=2.0)
                except Exception:
                    pass
                self._add_mesh_actor(
                    pv.Arrow(start=tuple(center[:3]), direction=tuple(normal), scale=max(size * 0.45, 1.0)),
                    color=marker.color,
                    opacity=0.94,
                    flat=True,
                )
                count += 1
            except Exception as exc:
                self.editor.append_debug(f"CAD/STL placement virtual-plane marker error: {exc}")
        return count

    def _render_preview(self, *args, reset_camera: bool = False) -> None:
        self._render_after_id = None
        if self._renderer is None:
            return
        try:
            tilts, desp = self._pose_values()
            mesh = self._stl_preview_mesh(tilts, desp)
            points = np.asarray(mesh.points, dtype=float)
            bounds_min = np.min(points, axis=0)
            bounds_max = np.max(points, axis=0)
            center = 0.5 * (bounds_min + bounds_max)
        except Exception as exc:
            self.status_var.set(f"Preview waiting for valid pose: {_short_error_message(exc)}")
            return
        self._renderer.RemoveAllViewProps()
        self._add_reference_geometry(bounds_min, bounds_max, center)
        self._add_mesh_actor(mesh, color=(0.05, 0.78, 0.86), opacity=0.48, flat=True)
        try:
            edges = mesh.extract_feature_edges(
                feature_angle=15,
                boundary_edges=True,
                feature_edges=True,
                manifold_edges=False,
            )
            if int(getattr(edges, "n_points", 0)) > 0:
                self._add_mesh_actor(edges, color=(0.04, 0.18, 0.25), line_width=1.2)
        except Exception:
            pass
        scene_radius = max(float(np.max(bounds_max - bounds_min)), 1.0)
        marker_count = self._add_face_role_overlays(tilts, desp, scene_radius=scene_radius)
        virtual_plane_count = self._add_virtual_plane_overlays(tilts, desp, scene_radius=scene_radius)
        if reset_camera:
            self._renderer.ResetCamera()
        self.set_camera_preset(self._camera_preset, render=False)
        self.status_var.set(
            "Preview bounds [mm]: min=({:.4g}, {:.4g}, {:.4g}) max=({:.4g}, {:.4g}, {:.4g}) | face roles={} | virtual planes={}".format(
                *bounds_min,
                *bounds_max,
                marker_count,
                virtual_plane_count,
            )
        )
        self.render()

    def _scene_bounds(self) -> tuple[np.ndarray, float, np.ndarray]:
        if self._renderer is None:
            return np.zeros(3, dtype=float), 1.0, np.ones(3, dtype=float)
        bounds = np.asarray(self._renderer.ComputeVisiblePropBounds(), dtype=float)
        if bounds.size != 6 or not np.all(np.isfinite(bounds)) or bounds[0] > bounds[1]:
            return np.zeros(3, dtype=float), 1.0, np.ones(3, dtype=float)
        center = np.array(
            [
                0.5 * (bounds[0] + bounds[1]),
                0.5 * (bounds[2] + bounds[3]),
                0.5 * (bounds[4] + bounds[5]),
            ],
            dtype=float,
        )
        span = np.array([bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4]], dtype=float)
        radius = max(float(np.max(span)), 1.0)
        return center, radius, span

    def set_camera_preset(self, preset: str, *, render: bool = True) -> None:
        self._camera_preset = preset
        if self._renderer is None:
            return
        camera = self._renderer.GetActiveCamera()
        if camera is None:
            return
        center, radius, span = self._scene_bounds()
        distance = max(radius * 2.4, 30.0)
        if preset == "zy":
            position = center + np.array([-distance, 0.0, 0.0], dtype=float)
            view_up = (0.0, 1.0, 0.0)
        elif preset == "xy":
            position = center + np.array([0.0, 0.0, distance], dtype=float)
            view_up = (0.0, 1.0, 0.0)
        elif preset == "xz":
            position = center + np.array([0.0, distance, 0.0], dtype=float)
            view_up = (1.0, 0.0, 0.0)
        else:
            position = center + np.array([-distance * 0.95, distance * 0.55, distance * 0.8], dtype=float)
            view_up = (0.0, 1.0, 0.0)
        camera.SetPosition(*position.tolist())
        camera.SetFocalPoint(*center.tolist())
        camera.SetViewUp(*view_up)
        try:
            camera.SetParallelProjection(1 if preset in {"zy", "xy", "xz"} else 0)
            if preset in {"zy", "xy", "xz"}:
                aspect = 1.4
                try:
                    width, height = self._vtk_widget.GetRenderWindow().GetSize()
                    aspect = max(float(width) / max(float(height), 1.0), 0.1)
                except Exception:
                    pass
                horizontal_span = span[2] if preset in {"zy", "xz"} else span[0]
                vertical_span = span[1] if preset in {"zy", "xy"} else span[0]
                camera.SetParallelScale(max(vertical_span * 0.5, horizontal_span / (2.0 * aspect), 1.0) * 1.08)
        except Exception:
            pass
        self._renderer.ResetCameraClippingRange()
        if render:
            self.render()

    def render(self) -> None:
        try:
            if self._vtk_widget is not None:
                self._vtk_widget.GetRenderWindow().Render()
        except Exception:
            pass

    def apply_and_refresh(self) -> None:
        try:
            tilts, desp = self._pose_values()
        except Exception as exc:
            messagebox.showerror("Visual CAD/STL Placement", str(exc), parent=self)
            return
        if not (0 <= self.row_index < len(self.editor.rows)):
            messagebox.showerror("Visual CAD/STL Placement", "The selected CAD/STL row no longer exists.", parent=self)
            return
        self.editor._begin_history_capture()
        target = self.editor.rows[self.row_index]
        target.tilt_x, target.tilt_y, target.tilt_z = tilts
        target.desp_x, target.desp_y, target.desp_z = desp
        self.editor._sync_table()
        self.editor._select_table_row(self.row_index)
        self.editor._commit_history_capture()
        self.editor._mark_plot_update_pending()
        self.editor.append_debug(
            "Visual CAD/STL placement S{idx}: Tilt=({tx:.6g},{ty:.6g},{tz:.6g}) Desp=({dx:.6g},{dy:.6g},{dz:.6g})".format(
                idx=self.row_index,
                tx=tilts[0],
                ty=tilts[1],
                tz=tilts[2],
                dx=desp[0],
                dy=desp[1],
                dz=desp[2],
            )
        )
        self.destroy()
        try:
            self.editor.refresh_plot(suppress_analysis=True)
            self.editor.status_var.set(f"Applied visual CAD/STL placement to S{self.row_index}.")
        except Exception as exc:
            self.editor.status_var.set(f"CAD/STL pose applied; 2D refresh failed: {_short_error_message(exc)}")
            self.editor.append_debug(f"Visual CAD/STL placement refresh failed: {exc}")
