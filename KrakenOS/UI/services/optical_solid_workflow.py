from __future__ import annotations

from pathlib import Path

import numpy as np

from KrakenOS.UI.optical_solid_metadata import OPTICAL_SOLID_FACE_PORT_DEFAULT


_PROTECTED_GLOBALS = {
    "LayoutOpticalSolidWorkflowMixin",
    "_PROTECTED_GLOBALS",
    "_sync_layout_globals",
}


def _sync_layout_globals(source: dict[str, object]) -> None:
    target = globals()
    for name, value in source.items():
        if name.startswith("__") or name in _PROTECTED_GLOBALS:
            continue
        target[name] = value


class LayoutOpticalSolidWorkflowMixin:
    @staticmethod
    def _rigid_affine_from_point_sets(source_points: np.ndarray, target_points: np.ndarray) -> np.ndarray | None:
        source = np.asarray(source_points, dtype=float)
        target = np.asarray(target_points, dtype=float)
        if source.ndim != 2 or target.ndim != 2 or source.shape != target.shape or source.shape[0] < 3:
            return None
        source = source[:, :3]
        target = target[:, :3]
        if not np.all(np.isfinite(source)) or not np.all(np.isfinite(target)):
            return None
        source_center = np.mean(source, axis=0)
        target_center = np.mean(target, axis=0)
        source_zero = source - source_center
        target_zero = target - target_center
        try:
            u, _sigma, vt = np.linalg.svd(source_zero.T @ target_zero)
        except Exception:
            return None
        rotation = vt.T @ u.T
        if float(np.linalg.det(rotation)) < 0.0:
            vt[-1, :] *= -1.0
            rotation = vt.T @ u.T
        if not np.all(np.isfinite(rotation)):
            return None
        translation = target_center - rotation @ source_center
        matrix = np.eye(4, dtype=float)
        matrix[:3, :3] = rotation
        matrix[:3, 3] = translation
        return matrix

    @staticmethod
    def _mesh_face_centroids_from_metadata(mesh, metadata: dict[str, object] | None) -> np.ndarray | None:
        if metadata is None or not isinstance(metadata, dict):
            return None
        face_records = list(metadata.get("faces", []) or [])
        try:
            faces = np.asarray(mesh.faces, dtype=int).reshape(-1)
            points = np.asarray(mesh.points, dtype=float)
        except Exception:
            return None
        if faces.size == 0 or points.ndim != 2 or points.shape[1] < 3:
            return None
        triangles: list[np.ndarray] = []
        cursor = 0
        while cursor < int(faces.size):
            vertex_count = int(faces[cursor])
            ids = np.asarray(faces[cursor + 1: cursor + 1 + vertex_count], dtype=int)
            cursor += vertex_count + 1
            if vertex_count >= 3:
                triangles.append(ids[:3])
        centroids: list[np.ndarray] = []
        for record in face_records:
            if not isinstance(record, dict):
                continue
            indices = [int(value) for value in list(record.get("triangle_indices", []) or []) if isinstance(value, (int, float))]
            if not indices:
                continue
            weighted_centroid = np.zeros(3, dtype=float)
            total_area = 0.0
            for triangle_index in indices:
                if not (0 <= triangle_index < len(triangles)):
                    continue
                tri_points = points[triangles[triangle_index], :3]
                area = 0.5 * float(np.linalg.norm(np.cross(tri_points[1] - tri_points[0], tri_points[2] - tri_points[0])))
                if area <= 1e-12 or not np.isfinite(area):
                    continue
                weighted_centroid += np.mean(tri_points, axis=0) * area
                total_area += area
            if total_area > 1e-12:
                centroids.append(weighted_centroid / total_area)
        if len(centroids) < 3:
            return None
        return np.asarray(centroids, dtype=float)

    @staticmethod
    def _mesh_icp_affine(source_mesh, target_mesh, *, max_landmarks: int = 4000) -> np.ndarray | None:
        try:
            import vtk
        except Exception:
            return None
        try:
            source_poly = source_mesh.extract_surface(algorithm="dataset_surface")
            target_poly = target_mesh.extract_surface(algorithm="dataset_surface")
        except Exception:
            return None
        try:
            if int(getattr(source_poly, "n_points", 0)) < 3 or int(getattr(target_poly, "n_points", 0)) < 3:
                return None
        except Exception:
            return None
        icp = vtk.vtkIterativeClosestPointTransform()
        icp.SetSource(source_poly)
        icp.SetTarget(target_poly)
        icp.GetLandmarkTransform().SetModeToRigidBody()
        icp.StartByMatchingCentroidsOn()
        icp.SetMaximumNumberOfIterations(80)
        icp.SetMaximumNumberOfLandmarks(int(max_landmarks))
        icp.CheckMeanDistanceOn()
        icp.SetMaximumMeanDistance(1e-6)
        try:
            icp.Modified()
            icp.Update()
        except Exception:
            return None
        matrix_vtk = icp.GetMatrix()
        if matrix_vtk is None:
            return None
        matrix = np.eye(4, dtype=float)
        try:
            for row in range(4):
                for column in range(4):
                    matrix[row, column] = float(matrix_vtk.GetElement(row, column))
        except Exception:
            return None
        if not np.all(np.isfinite(matrix)):
            return None
        return matrix

    @staticmethod
    def _mesh_with_affine_copy(mesh, matrix: np.ndarray):
        transformed = mesh.copy(deep=True)
        transformed.transform(np.asarray(matrix, dtype=float), inplace=True)
        return transformed

    @classmethod
    def _alignment_distance_stats(cls, source_mesh, target_mesh, matrix: np.ndarray) -> dict[str, float] | None:
        try:
            transformed = cls._mesh_with_affine_copy(source_mesh, matrix)
            source_points = np.asarray(transformed.points, dtype=float)
            target_points = np.asarray(target_mesh.points, dtype=float)
        except Exception:
            return None
        if source_points.ndim != 2 or target_points.ndim != 2 or source_points.shape[0] == 0 or target_points.shape[0] == 0:
            return None
        if not np.all(np.isfinite(source_points)) or not np.all(np.isfinite(target_points)):
            return None
        if source_points.shape[0] > 600:
            indices = np.linspace(0, source_points.shape[0] - 1, 600, dtype=int)
            source_points = source_points[indices]
        if target_points.shape[0] > 2000:
            indices = np.linspace(0, target_points.shape[0] - 1, 2000, dtype=int)
            target_points = target_points[indices]
        deltas = source_points[:, None, :3] - target_points[None, :, :3]
        distances = np.linalg.norm(deltas, axis=2)
        nearest = np.min(distances, axis=1)
        return {
            "max": float(np.max(nearest)),
            "p95": float(np.percentile(nearest, 95.0)),
            "mean": float(np.mean(nearest)),
        }

    @classmethod
    def _best_alignment_affine(cls, source_mesh, target_mesh, candidates: list[np.ndarray | None]) -> np.ndarray | None:
        best_matrix: np.ndarray | None = None
        best_score: tuple[float, float, float] | None = None
        for candidate in candidates:
            if candidate is None:
                continue
            matrix = np.asarray(candidate, dtype=float)
            if matrix.shape != (4, 4) or not np.all(np.isfinite(matrix)):
                continue
            stats = cls._alignment_distance_stats(source_mesh, target_mesh, matrix)
            if stats is None:
                continue
            score = (float(stats["p95"]), float(stats["mean"]), float(stats["max"]))
            if best_score is None or score < best_score:
                best_score = score
                best_matrix = matrix
        return best_matrix

    def _optical_stl_solid_row(
        self,
        path: Path,
        *,
        source_path: Path | None = None,
        source_format: str = "STL",
    ) -> SurfaceRow:
        display_path = Path(source_path) if source_path is not None else Path(path)
        stem = display_path.stem.replace("_", " ").strip() or "Optical solid"
        source_label = str(source_format).upper() if source_format else "STL"
        source_note = (
            f" Original {source_label} CAD source: {source_path}."
            if source_path is not None
            else ""
        )
        note = (
            "Optical CAD/STL solid import. KrakenOS traces this through Solid_3d_stl in "
            "non-sequential scene mode; STEP/IGES sources are meshed to a cached STL. "
            "Use Material, Thickness, Tilt, and Decenter to align the closed mesh "
            f"in millimetres.{source_note}"
        )
        advanced = {
            "Solid_3d_stl": str(path),
            "Note": note,
        }
        if source_path is not None:
            advanced["OpticalSolidSourcePath"] = str(source_path)
            advanced["OpticalSolidSourceFormat"] = source_label
        default_metadata = self._default_uncoated_optical_solid_face_metadata(path)
        if default_metadata is not None:
            advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = default_metadata
        return SurfaceRow(
            surface="Standard",
            element=f"Solid {stem}",
            name=f"Optical solid: {stem}",
            glass="BK7",
            thickness=40.0,
            diameter=25.0,
            axis_move=0.0,
            advanced=advanced,
        )

    @staticmethod
    def _default_uncoated_optical_solid_face_metadata(
        path: Path,
        existing: object | None = None,
    ) -> dict[str, object] | None:
        from KrakenOS.UI.services.optical_solid_geometry import optical_solid_metadata_is_brep
        from KrakenOS.UI.services.step_optical_solid_brep import load_face_sidecar

        # Prefer native OCC B-Rep faces over STL plane-clustering: a curved
        # optical surface is one B-Rep face but shatters into ~160 planar
        # clusters. Already-B-Rep `existing` wins (keeps user roles); else the
        # OCC sidecar written beside the cached STL; else cluster the STL.
        metadata: dict[str, object] | None = None
        if optical_solid_metadata_is_brep(existing):
            metadata = normalize_optical_solid_face_metadata(existing, source_stl=str(path))
        else:
            sidecar = load_face_sidecar(Path(path))
            if optical_solid_metadata_is_brep(sidecar):
                metadata = normalize_optical_solid_face_metadata(sidecar, source_stl=str(path))
        if metadata is None:
            try:
                candidates = cluster_optical_solid_planar_faces(Path(path))
            except Exception:
                return None
            if not candidates:
                return None
            metadata = normalize_optical_solid_face_metadata(existing or {}, candidates, source_stl=str(path))
        faces: list[dict[str, object]] = []
        for face in list(metadata.get("faces", []) or []):
            if not isinstance(face, dict):
                continue
            record = normalize_optical_solid_face_record(face)
            source = str(record.get("assignment_source", "") or "").strip()
            function = _normalize_optical_solid_face_function(record.get("function"), legacy_role=record.get("role"))
            if source == OPTICAL_SOLID_FACE_ASSIGNMENT_MANUAL:
                faces.append(record)
                continue
            # Every non-manually-authored face defaults to Uncoated
            # (Transmit/Port). This also heals a stale auto "Absorber/Mechanical"
            # role baked into an older sidecar by the previous promotion
            # classifier, which used to condemn non-axis faces of a cube / prism
            # / beam-splitter to a hard mechanical block and silently kill the
            # trace (bug 0016). User-authored faces carry assignment_source ==
            # MANUAL and are never touched here.
            if (
                function in {OPTICAL_SOLID_FACE_FUNCTION_DEFAULT, "Absorber/Mechanical"}
                or source == OPTICAL_SOLID_FACE_ASSIGNMENT_DEFAULT_UNCOATED
            ):
                record["function"] = OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT
                record["role"] = _legacy_role_from_optical_solid_face_function(OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT)
                record["port_role"] = OPTICAL_SOLID_FACE_PORT_INTERACTION
                record["assignment_source"] = OPTICAL_SOLID_FACE_ASSIGNMENT_DEFAULT_UNCOATED
            faces.append(record)
        return normalize_optical_solid_face_metadata(
            {
                "faces": faces,
                "virtual_planes": metadata.get("virtual_planes", []),
                "source_stl": str(path),
            },
            source_stl=str(path),
        )

    def import_optical_stl_solid(self) -> None:
        initial_dir = ATTACHMENT_DIR if ATTACHMENT_DIR.exists() else EXAMPLES_DIR if EXAMPLES_DIR.exists() else PROJECT_ROOT
        path_text = filedialog.askopenfilename(
            title="Import Optical CAD/STL Solid",
            initialdir=str(initial_dir),
            filetypes=OPTICAL_SOLID_FILETYPES,
            parent=self,
        )
        if not path_text:
            return
        source_path = Path(path_text).expanduser()
        try:
            mesh_path, cad_source_path, source_format = _optical_solid_mesh_path_from_source(source_path)
        except Exception as exc:
            messagebox.showerror("Import Optical CAD/STL Solid", f"Could not prepare optical solid:\n\n{exc}", parent=self)
            return
        diagnostics = inspect_stl_mesh(mesh_path)
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Import Optical CAD/STL Solid", f"Could not read the surface table:\n\n{exc}", parent=self)
            return

        selected_indices = self._selected_table_indices()
        arm_key = self._current_arm_view_key()
        if selected_indices:
            insert_at = max(selected_indices) + 1
        elif arm_key:
            insert_at = self._default_insert_index_for_arm_key(arm_key)
        else:
            insert_at = len(self.rows)
            if self.rows and self.rows[-1].surface == "Image":
                insert_at -= 1
        insert_at = max(1, min(insert_at, len(self.rows) - (1 if self.rows and self.rows[-1].surface == "Image" else 0)))

        row = self._optical_stl_solid_row(
            mesh_path.resolve(),
            source_path=cad_source_path.resolve() if cad_source_path is not None else None,
            source_format=source_format,
        )
        if arm_key:
            self._apply_arm_key_metadata_to_row(row, arm_key)
        self._begin_history_capture()
        self.rows.insert(insert_at, row)
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_indices([insert_at], focus_index=insert_at)
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.status_var.set(
            f"Imported optical solid {source_path.name} at S{insert_at}; {short_stl_mesh_diagnostics(diagnostics)}. Click Update."
        )
        report_text = f"S{insert_at}: {row.name}\n{format_stl_mesh_diagnostics(diagnostics)}"
        if cad_source_path is not None:
            report_text += f"\n\nOriginal CAD source: {cad_source_path}\nCached STL mesh: {mesh_path}"
        self.append_debug(report_text)
        if diagnostics.errors or diagnostics.warnings:
            self.status_var.set(
                f"Imported {source_path.name} at S{insert_at}; mesh diagnostics need review ({short_stl_mesh_diagnostics(diagnostics)})."
            )
        else:
            self.status_var.set(
                f"Imported {source_path.name} at S{insert_at}. Opening CAD/STL face assignment."
            )
        self.after(120, lambda idx=insert_at: self.open_optical_solid_face_role_editor(idx))

    def convert_row_to_optical_stl_solid(self, row_index: int) -> None:
        if not (0 <= row_index < len(self.rows)):
            return
        if self.rows[row_index].surface in {"Object", "Image"}:
            messagebox.showinfo("Optical CAD/STL Solid", "Object/Image rows cannot be converted to optical CAD/STL solids.", parent=self)
            return
        initial_dir = ATTACHMENT_DIR if ATTACHMENT_DIR.exists() else EXAMPLES_DIR if EXAMPLES_DIR.exists() else PROJECT_ROOT
        path_text = filedialog.askopenfilename(
            title="Convert Row to Optical CAD/STL Solid",
            initialdir=str(initial_dir),
            filetypes=OPTICAL_SOLID_FILETYPES,
            parent=self,
        )
        if not path_text:
            return
        source_path = Path(path_text).expanduser()
        try:
            mesh_path, cad_source_path, source_format = _optical_solid_mesh_path_from_source(source_path)
        except Exception as exc:
            messagebox.showerror("Optical CAD/STL Solid", f"Could not prepare optical solid:\n\n{exc}", parent=self)
            return
        diagnostics = inspect_stl_mesh(mesh_path)
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Optical CAD/STL Solid", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        previous = self.rows[row_index]
        replacement = self._optical_stl_solid_row(
            mesh_path.resolve(),
            source_path=cad_source_path.resolve() if cad_source_path is not None else None,
            source_format=source_format,
        )
        replacement.element = previous.element or replacement.element
        replacement.thickness = max(float(previous.thickness), replacement.thickness)
        replacement.diameter = max(float(previous.diameter), replacement.diameter)
        replacement.tilt_x = float(previous.tilt_x)
        replacement.tilt_y = float(previous.tilt_y)
        replacement.tilt_z = float(previous.tilt_z)
        replacement.desp_x = float(previous.desp_x)
        replacement.desp_y = float(previous.desp_y)
        replacement.desp_z = float(previous.desp_z)
        self._begin_history_capture()
        self.rows[row_index] = replacement
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_row(row_index)
        self._commit_history_capture()
        self._mark_plot_update_pending()
        report_text = f"S{row_index}: {replacement.name}\n{format_stl_mesh_diagnostics(diagnostics)}"
        if cad_source_path is not None:
            report_text += f"\n\nOriginal CAD source: {cad_source_path}\nCached STL mesh: {mesh_path}"
        self.append_debug(report_text)
        self.status_var.set(
            f"Converted S{row_index} to optical solid {source_path.name}; opening CAD/STL face assignment."
        )
        self.after(120, lambda idx=row_index: self.open_optical_solid_face_role_editor(idx))

    def _stl_path_from_row(self, row: SurfaceRow) -> Path | None:
        advanced = row.advanced or {}
        if not isinstance(advanced, dict):
            return None
        value = advanced.get("Solid_3d_stl")
        if not self._scene_graph_value_present(value):
            return None
        if isinstance(value, (str, Path)):
            text = str(value).strip()
            if text and text.lower() != "none":
                return Path(text).expanduser()
        return None

    def _main_optical_solid_dialogs(self) -> MainOpticalSolidDialogs:
        dialog = self.__dict__.get("_main_optical_solid_dialogs_instance")
        if dialog is None:
            dialog = MainOpticalSolidDialogs(
                self,
                short_error_message=_short_error_message,
                axis_to_layout_z_tilts=STL_AXIS_TO_LAYOUT_Z_TILTS,
            )
            self._main_optical_solid_dialogs_instance = dialog
        return dialog

    def _optical_stl_diagnostics_text(self) -> str:
        return self._main_optical_solid_dialogs()._optical_stl_diagnostics_text()

    def open_optical_stl_diagnostics(self) -> None:
        self._main_optical_solid_dialogs().open_optical_stl_diagnostics()

    @staticmethod
    def _optical_solid_faces_summary(row_index: int, row: SurfaceRow) -> str:
        metadata = normalize_optical_solid_face_metadata((row.advanced or {}).get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}))
        return optical_solid_metadata.optical_solid_faces_summary_text(row_index, row.name, row.surface, metadata)

    def _main_optical_solid_face_roles_dialog(self) -> MainOpticalSolidFaceRolesDialog:
        dialog = self.__dict__.get("_main_optical_solid_face_roles_dialog_instance")
        if dialog is None:
            dialog = MainOpticalSolidFaceRolesDialog(self)
            self._main_optical_solid_face_roles_dialog_instance = dialog
        return dialog

    def _open_optical_solid_faces_for_row(self, row_index: int, row: SurfaceRow, path: Path) -> None:
        self._main_optical_solid_face_roles_dialog()._open_optical_solid_faces_for_row(row_index, row, path)

    def open_optical_solid_face_role_editor(self, row_index: int | None = None) -> None:
        title = "Assign CAD/STL Optical Faces"
        if row_index is None:
            selected = self._selected_file_backed_stl_row(title)
            if selected is None:
                return
            row_index, row, path = selected
        else:
            self._commit_pending_table_edit()
            try:
                self._read_rows_from_table()
            except Exception as exc:
                messagebox.showerror(title, f"Could not read the surface table:\n\n{exc}", parent=self)
                return
            item = self._file_backed_stl_row_at(row_index)
            if item is None:
                messagebox.showinfo(title, "The selected row does not contain a file-backed Solid_3d_stl value.", parent=self)
                return
            row, path = item
        self._open_optical_solid_faces_for_row(int(row_index), row, path)

    def _selected_file_backed_stl_row(self, title: str) -> tuple[int, SurfaceRow, Path] | None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror(title, f"Could not read the surface table:\n\n{exc}", parent=self)
            return None
        row_index = self._selected_surface_row_index()
        if row_index is None or row_index < 0 or row_index >= len(self.rows):
            messagebox.showinfo(title, "Select an STL solid row first.", parent=self)
            return None
        row = self.rows[row_index]
        path = self._stl_path_from_row(row)
        if path is None:
            messagebox.showinfo(title, "The selected row does not contain a file-backed Solid_3d_stl value.", parent=self)
            return None
        if not path.exists():
            messagebox.showerror(title, f"STL file does not exist:\n\n{path}", parent=self)
            return None
        return row_index, row, path

    def _file_backed_stl_row_at(self, row_index: int) -> tuple[SurfaceRow, Path] | None:
        try:
            row_index = int(row_index)
        except Exception:
            return None
        if not (0 <= row_index < len(self.rows)):
            return None
        row = self.rows[row_index]
        path = self._stl_path_from_row(row)
        if path is None or not path.exists():
            return None
        return row, path

    @staticmethod
    def _direct_indexed_optical_solid_face_metadata(value: object, path: Path) -> dict[str, object] | None:
        if not isinstance(value, dict):
            return None
        faces = [face for face in list(value.get("faces", []) or []) if isinstance(face, dict)]
        if not faces:
            return None
        direct_source = (
            str(value.get("metadata_coordinates", "") or "").strip() == "local_centered_promoted_row"
            or str(value.get("promoted_face_metadata_source", "") or "").strip() == "open3d_step_overlay"
        )
        if not direct_source:
            return None
        if not any(list(face.get("triangle_indices", face.get("cell_indices", ())) or []) for face in faces):
            return None
        normalized = normalize_optical_solid_face_metadata(value, source_stl=str(path))
        if not list(normalized.get("faces", []) or []):
            return None
        for key in (
            "source_step",
            "source_backend",
            "source_face_count",
            "outer_face_count",
            "interior_duplicate_count",
            "promoted_face_metadata_source",
            "metadata_coordinates",
        ):
            if key in value:
                normalized[key] = value[key]
        return normalized

    def _optical_solid_face_metadata_for_row(self, row_index: int) -> tuple[SurfaceRow, Path, dict[str, object]]:
        item = self._file_backed_stl_row_at(int(row_index))
        if item is None:
            raise RuntimeError(f"S{int(row_index)} is not a file-backed optical CAD/STL solid.")
        row, path = item
        existing = (row.advanced or {}).get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {})
        direct_metadata = self._direct_indexed_optical_solid_face_metadata(existing, path)
        if direct_metadata is not None:
            return row, path, direct_metadata
        candidates = cluster_optical_solid_planar_faces(path)
        if not candidates:
            raise RuntimeError(f"S{int(row_index)} has no planar CAD/STL face candidates.")
        metadata = normalize_optical_solid_face_metadata(
            existing,
            candidates,
            source_stl=str(path),
        )
        return row, path, metadata

    def optical_solid_face_record_at_world_point(
        self,
        row_index: int,
        point_world,
        *,
        normal_world=None,
        assigned_only: bool = False,
    ) -> dict[str, object] | None:
        row, _path, metadata = self._optical_solid_face_metadata_for_row(int(row_index))
        temp_row = SurfaceRow(**asdict(row))
        temp_row.advanced = dict(temp_row.advanced or {})
        temp_row.advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata
        faces = optical_solid_face_world_records(
            temp_row,
            self._stl_row_z_station(int(row_index)),
            assigned_only=bool(assigned_only),
        )
        return match_optical_solid_world_face(faces, point_world, normal_world)

    @staticmethod
    def _optical_solid_face_record_for_triangle_index(
        faces: list[dict[str, object]],
        triangle_index: int,
    ) -> dict[str, object] | None:
        try:
            triangle_index = int(triangle_index)
        except Exception:
            return None
        if triangle_index < 0:
            return None
        for face in list(faces or []):
            if not isinstance(face, dict):
                continue
            try:
                triangle_indices = optical_solid_metadata.nonnegative_int_list(
                    face.get("triangle_indices", face.get("cell_indices"))
                )
            except Exception:
                triangle_indices = []
            if triangle_index in set(int(value) for value in triangle_indices):
                return dict(face)
        return None

    def _optical_solid_face_records_for_temp_row(
        self,
        row: SurfaceRow,
        row_index: int,
        metadata: dict[str, object],
    ) -> list[dict[str, object]]:
        temp_row = SurfaceRow(**asdict(row))
        temp_row.advanced = dict(temp_row.advanced or {})
        temp_row.advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata
        z_station = float(
            sum(
                float(getattr(existing_row, "thickness", 0.0) or 0.0)
                for existing_row in self.rows[: max(int(row_index), 0)]
            )
        )
        return optical_solid_face_world_records(
            temp_row,
            z_station,
            assigned_only=False,
        )

    def optical_solid_face_record_for_mesh_cell(
        self,
        row_index: int,
        cell_id: int,
    ) -> dict[str, object] | None:
        row, _path, metadata = self._optical_solid_face_metadata_for_row(int(row_index))
        faces = self._optical_solid_face_records_for_temp_row(row, int(row_index), metadata)
        return self._optical_solid_face_record_for_triangle_index(faces, int(cell_id))

    def optical_solid_step_overlay_face_record_at_world_point(
        self,
        label: str,
        point_world,
        *,
        normal_world=None,
        cell_id: int = -1,
    ) -> dict[str, object] | None:
        plan = self._step_overlay_optical_solid_row_plan(
            label,
            use_current_selection=False,
            quiet=True,
        )
        if plan is None:
            return None
        row = plan.get("row")
        if not isinstance(row, SurfaceRow):
            return None
        try:
            row_index = int(plan.get("row_index", 0))
        except Exception:
            row_index = 0
        metadata = normalize_optical_solid_face_metadata(
            (row.advanced or {}).get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {})
        )
        faces = self._optical_solid_face_records_for_temp_row(row, row_index, metadata)
        face = self._optical_solid_face_record_for_triangle_index(faces, int(cell_id))
        if face is not None:
            return face
        return match_optical_solid_world_face(faces, point_world, normal_world)

    def _default_port_role_for_face_function(self, function: str, existing: object = OPTICAL_SOLID_FACE_PORT_DEFAULT) -> str:
        existing_role = _normalize_optical_solid_face_port_role(existing)
        normalized = _normalize_optical_solid_face_function(function)
        if normalized == OPTICAL_SOLID_FACE_FUNCTION_DEFAULT:
            return OPTICAL_SOLID_FACE_PORT_DEFAULT
        if existing_role in {OPTICAL_SOLID_FACE_PORT_INPUT, OPTICAL_SOLID_FACE_PORT_OUTPUT}:
            return existing_role
        if normalized in {"Mirror", "Beam Splitter", "Absorber/Mechanical"}:
            return OPTICAL_SOLID_FACE_PORT_INTERACTION
        return OPTICAL_SOLID_FACE_PORT_DEFAULT

    def _direct_context_port_role_for_face_function(self, function: str, existing: object = OPTICAL_SOLID_FACE_PORT_DEFAULT) -> str:
        existing_role = _normalize_optical_solid_face_port_role(existing)
        normalized = _normalize_optical_solid_face_function(function)
        if normalized == OPTICAL_SOLID_FACE_FUNCTION_DEFAULT:
            return OPTICAL_SOLID_FACE_PORT_DEFAULT
        if existing_role == OPTICAL_SOLID_FACE_PORT_INPUT:
            return OPTICAL_SOLID_FACE_PORT_INPUT
        if normalized in {
            OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
            "TIR",
            "Mirror",
            "Beam Splitter",
            "Absorber/Mechanical",
        }:
            return OPTICAL_SOLID_FACE_PORT_INTERACTION
        return OPTICAL_SOLID_FACE_PORT_DEFAULT

    def assign_optical_solid_face_function(
        self,
        row_index: int,
        face_id: str,
        function_label: str,
        *,
        port_role: str | None = None,
        direct_context: bool = False,
    ) -> dict[str, object]:
        row_index = int(row_index)
        face_id = str(face_id or "").strip()
        if not face_id:
            raise RuntimeError("No CAD/STL face ID was selected.")
        row, path, metadata = self._optical_solid_face_metadata_for_row(row_index)
        function = _optical_solid_face_function_from_ui_value(function_label)
        role = _legacy_role_from_optical_solid_face_function(function)
        normalized_faces = [
            normalize_optical_solid_face_record(face)
            for face in list(metadata.get("faces", []) or [])
            if isinstance(face, dict)
        ]
        target_record = next(
            (
                record
                for record in normalized_faces
                if str(record.get("face_id", "") or "").strip() == face_id
            ),
            None,
        )
        if target_record is None:
            raise RuntimeError(f"CAD/STL face {face_id} is not available on S{row_index}.")
        extent_mm = _optical_solid_face_metadata_extent(normalized_faces, row)
        updated_faces: list[dict[str, object]] = []
        matched: dict[str, object] | None = None
        related_face_ids: list[str] = []
        for face in list(metadata.get("faces", []) or []):
            if not isinstance(face, dict):
                continue
            record = normalize_optical_solid_face_record(face)
            record_face_id = str(record.get("face_id", "") or "").strip()
            same_physical_face = (
                record_face_id == face_id
                or _optical_solid_face_records_share_plane(record, target_record, extent_mm=extent_mm)
            )
            if same_physical_face:
                record["function"] = function
                record["role"] = role
                record["port_role"] = (
                    _normalize_optical_solid_face_port_role(port_role)
                    if port_role is not None
                    else (
                        self._direct_context_port_role_for_face_function(function, record.get("port_role"))
                        if direct_context
                        else self._default_port_role_for_face_function(function, record.get("port_role"))
                    )
                )
                record["assignment_source"] = OPTICAL_SOLID_FACE_ASSIGNMENT_MANUAL
                updated = normalize_optical_solid_face_record(record)
                if record_face_id == face_id:
                    matched = updated
                elif record_face_id:
                    related_face_ids.append(record_face_id)
                record = updated
            updated_faces.append(record)
        # Preserve the "direct" provenance markers so the next metadata read
        # takes the _direct_indexed_optical_solid_face_metadata fast path,
        # keeping the prefixed S{idx}/F{nn} face IDs that user code captured
        # before the assignment. Without this, subsequent reads fall back to
        # cluster_optical_solid_planar_faces which emits bare F{nn} IDs --
        # so a follow-up assign with a previously valid "S001/F002" id would
        # raise "CAD/STL face S001/F002 is not available on S{idx}".
        passthrough = {
            key: metadata[key]
            for key in (
                "source_step",
                "source_backend",
                "source_face_count",
                "outer_face_count",
                "interior_duplicate_count",
                "promoted_face_metadata_source",
                "metadata_coordinates",
            )
            if isinstance(metadata, dict) and key in metadata
        }
        metadata_to_save = normalize_optical_solid_face_metadata(
            {"faces": updated_faces, "virtual_planes": metadata.get("virtual_planes", []), "source_stl": str(path)},
            source_stl=str(path),
        )
        for key, value in passthrough.items():
            metadata_to_save[key] = value
        self._begin_history_capture()
        target = self.rows[row_index]
        target.advanced = dict(target.advanced or {})
        target.advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata_to_save
        self._sync_table()
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self._invalidate_optical_solid_face_assignment_trace(row_index, face_id, function)
        display = _optical_solid_face_function_display(function)
        summary = self._optical_solid_faces_summary(row_index, target)
        if related_face_ids:
            summary += "\n" + (
                f"Direct Open 3D assignment also updated coplanar face records: "
                f"{', '.join(related_face_ids)}"
            )
        self.append_debug(summary)
        related_suffix = f" (+{len(related_face_ids)} coplanar)" if related_face_ids else ""
        self.status_var.set(f"S{row_index} {face_id}: set CAD/STL face function to {display}{related_suffix}.")
        return {
            "row_index": row_index,
            "face_id": face_id,
            "function": function,
            "function_display": display,
            "port_role": matched.get("port_role", OPTICAL_SOLID_FACE_PORT_DEFAULT),
            "related_face_ids": tuple(related_face_ids),
            "metadata": metadata_to_save,
        }

    def assign_optical_solid_face_function_at_world_point(
        self,
        row_index: int,
        point_world,
        function_label: str,
        *,
        normal_world=None,
        port_role: str | None = None,
        direct_context: bool = False,
    ) -> dict[str, object]:
        face = self.optical_solid_face_record_at_world_point(
            int(row_index),
            point_world,
            normal_world=normal_world,
            assigned_only=False,
        )
        if face is None:
            raise RuntimeError(f"Could not match the picked point to a CAD/STL face on S{int(row_index)}.")
        face_id = str(face.get("face_id", "") or "").strip()
        result = self.assign_optical_solid_face_function(
            int(row_index),
            face_id,
            function_label,
            port_role=port_role,
            direct_context=direct_context,
        )
        result["matched_face"] = face
        return result

    def _stl_row_z_station(self, row_index: int) -> float:
        z_positions = self._row_z_positions()
        if 0 <= int(row_index) < len(z_positions):
            return float(z_positions[int(row_index)])
        return 0.0

    def _apply_stl_row_pose(
        self,
        row_index: int,
        *,
        tilts: tuple[float, float, float] | None = None,
        desp: tuple[float, float, float] | None = None,
        action: str,
    ) -> None:
        selected = self._file_backed_stl_row_at(row_index)
        if selected is None:
            raise RuntimeError("Selected row is not a file-backed optical STL solid")
        row, _path = selected
        self._begin_history_capture()
        if tilts is not None:
            row.tilt_x, row.tilt_y, row.tilt_z = (float(value) for value in tilts)
        if desp is not None:
            row.desp_x, row.desp_y, row.desp_z = (float(value) for value in desp)
        self._sync_table()
        self._select_table_row(int(row_index))
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.append_debug(
            "STL 3D placement {action} S{idx}: Tilt=({tx:.6g},{ty:.6g},{tz:.6g}) "
            "Desp=({dx:.6g},{dy:.6g},{dz:.6g})".format(
                action=action,
                idx=int(row_index),
                tx=float(row.tilt_x),
                ty=float(row.tilt_y),
                tz=float(row.tilt_z),
                dx=float(row.desp_x),
                dy=float(row.desp_y),
                dz=float(row.desp_z),
            )
        )

    def apply_stl_axis_fit(self, row_index: int, axis: str) -> None:
        selected = self._file_backed_stl_row_at(row_index)
        if selected is None:
            raise RuntimeError("Selected row is not a file-backed optical STL solid")
        _row, path = selected
        axis = str(axis or "+Z").strip()
        tilts = STL_AXIS_TO_LAYOUT_Z_TILTS.get(axis, STL_AXIS_TO_LAYOUT_Z_TILTS["+Z"])
        bounds_min, _bounds_max, center = rotated_stl_bounds(path, tilts)
        desp = (-float(center[0]), -float(center[1]), -float(bounds_min[2]))
        self._apply_stl_row_pose(row_index, tilts=tilts, desp=desp, action=f"fit {axis}->+Z")

    def rotate_stl_row_pose(self, row_index: int, axis: str, delta_deg: float) -> None:
        selected = self._file_backed_stl_row_at(row_index)
        if selected is None:
            raise RuntimeError("Selected row is not a file-backed optical STL solid")
        row, _path = selected
        tilts = [float(row.tilt_x), float(row.tilt_y), float(row.tilt_z)]
        axis_index = {"x": 0, "y": 1, "z": 2}.get(str(axis).strip().lower())
        if axis_index is None:
            raise RuntimeError(f"Unknown STL rotation axis: {axis}")
        tilts[axis_index] += float(delta_deg)
        self._apply_stl_row_pose(row_index, tilts=tuple(tilts), action=f"rotate {axis.upper()} {float(delta_deg):+.0f} deg")

    def center_stl_row_xy(self, row_index: int) -> None:
        selected = self._file_backed_stl_row_at(row_index)
        if selected is None:
            raise RuntimeError("Selected row is not a file-backed optical STL solid")
        row, path = selected
        tilts = (float(row.tilt_x), float(row.tilt_y), float(row.tilt_z))
        _bounds_min, _bounds_max, center = rotated_stl_bounds(path, tilts)
        desp = (-float(center[0]), -float(center[1]), float(row.desp_z))
        self._apply_stl_row_pose(row_index, desp=desp, action="center X/Y")

    def place_stl_row_front_on_station(self, row_index: int) -> None:
        selected = self._file_backed_stl_row_at(row_index)
        if selected is None:
            raise RuntimeError("Selected row is not a file-backed optical STL solid")
        row, path = selected
        tilts = (float(row.tilt_x), float(row.tilt_y), float(row.tilt_z))
        bounds_min, _bounds_max, _center = rotated_stl_bounds(path, tilts)
        desp = (float(row.desp_x), float(row.desp_y), -float(bounds_min[2]))
        self._apply_stl_row_pose(row_index, desp=desp, action="front on row")

    def translate_scene_row_pose(self, row_index: int, axis: str, delta_mm: float) -> dict[str, object]:
        try:
            row_index = int(row_index)
        except Exception as exc:
            raise RuntimeError("Invalid row index for 3D placement translation") from exc
        if not (0 <= row_index < len(self.rows)):
            raise RuntimeError("3D placement translation row is outside the table")
        axis_key = str(axis or "").strip().lower()
        attr = {"x": "desp_x", "y": "desp_y", "z": "desp_z"}.get(axis_key)
        if attr is None:
            raise RuntimeError(f"Unknown 3D placement translation axis: {axis}")
        try:
            delta = float(delta_mm)
        except Exception as exc:
            raise RuntimeError("Invalid 3D placement translation step") from exc
        if not np.isfinite(delta) or abs(delta) <= 1e-12:
            raise RuntimeError("3D placement translation step is zero or non-finite")
        row = self.rows[row_index]
        before = float(getattr(row, attr))
        history_started = False
        if "_history_restoring" in self.__dict__ and "_history_pending_state" in self.__dict__:
            try:
                self._begin_history_capture()
                history_started = True
            except Exception:
                history_started = False
        setattr(row, attr, before + delta)
        row.advanced = dict(row.advanced or {})
        settings = normalize_scene_placement_settings(row.advanced.get(SCENE_PLACEMENT_ADVANCED_ATTR, {}))
        settings["last_translate_axis"] = axis_key
        settings["last_translate_delta_mm"] = float(delta)
        settings["last_translate_step_mm"] = abs(float(delta))
        row.advanced[SCENE_PLACEMENT_ADVANCED_ATTR] = settings
        if "table" in self.__dict__:
            try:
                self._sync_table()
                self._select_table_row(row_index)
            except Exception:
                pass
        if history_started:
            self._commit_history_capture()
        try:
            self._mark_plot_update_pending()
        except Exception:
            pass
        self.append_debug(
            "3D placement translate S{row}: axis={axis} delta={delta:.6g} mm "
            "Desp=({x:.6g},{y:.6g},{z:.6g})".format(
                row=row_index,
                axis=axis_key.upper(),
                delta=float(delta),
                x=float(row.desp_x),
                y=float(row.desp_y),
                z=float(row.desp_z),
            )
        )
        return {
            "row_index": row_index,
            "axis": axis_key,
            "delta_mm": float(delta),
            "before_mm": before,
            "after_mm": float(getattr(row, attr)),
            "scene_placement_settings": settings,
        }


    def _step_roll_deg(self, label: str) -> float:
        if label == "lens":
            return float(getattr(self, "lens_step_rotation_z_deg", 0.0))
        if label == "optical":
            return float(getattr(self, "optical_step_rotation_z_deg", 0.0))
        if label == "camera":
            return float(getattr(self, "camera_step_rotation_z_deg", 0.0))
        if label == "led":
            return float(getattr(self, "led_step_rotation_z_deg", 0.0))
        return 0.0

    def _step_x_rotation_deg(self, label: str) -> float:
        if label == "lens":
            return float(getattr(self, "lens_step_rotation_x_deg", 0.0))
        if label == "optical":
            return float(getattr(self, "optical_step_rotation_x_deg", 0.0))
        if label == "camera":
            return float(getattr(self, "camera_step_rotation_x_deg", 0.0))
        if label == "led":
            return float(getattr(self, "led_step_rotation_x_deg", 0.0))
        return 0.0

    def _step_y_rotation_deg(self, label: str) -> float:
        if label == "lens":
            return float(getattr(self, "lens_step_rotation_y_deg", 0.0))
        if label == "optical":
            return float(getattr(self, "optical_step_rotation_y_deg", 0.0))
        if label == "camera":
            return float(getattr(self, "camera_step_rotation_y_deg", 0.0))
        if label == "led":
            return float(getattr(self, "led_step_rotation_y_deg", 0.0))
        return 0.0

    def _step_target_front_z(self, label: str) -> float:
        if label == "lens":
            return float(self._lens_front_datum_z())
        if label == "camera":
            return float(self._current_image_plane_z() - self._current_camera_front_to_sensor_mm())
        if label == "led":
            return float(self._led_step_z_translation())
        return 0.0

    def apply_step_axis_pick(self, label: str, feature_center_xyz: np.ndarray) -> None:
        label = str(label).strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET:
            return
        feature_center = np.asarray(feature_center_xyz, dtype=float)
        if feature_center.size < 2 or not np.all(np.isfinite(feature_center[:2])):
            self.status_var.set(f"Invalid {label} CAD feature center.")
            return
        current = np.asarray(self._step_axis_offset_xy(label), dtype=float)
        # Offsets translate the whole aligned STEP in the transverse frame. To
        # make the picked feature center land on the optical axis, cancel its
        # current world-space X/Y residual after undoing only the final Z roll.
        delta = np.asarray(self._step_offset_delta_for_world_xy(label, feature_center[:2]), dtype=float)
        new_offset = current + delta
        self._begin_history_capture()
        self._set_step_axis_offset_xy(label, (float(new_offset[0]), float(new_offset[1])))
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = False
        self._cad_led_object_edge_pick = False
        self._selected_step_label = label
        self._commit_history_capture()
        self.status_var.set(
            f"{label.upper()} STEP feature center moved to optical axis "
            f"(picked X/Y={feature_center[0]:.3g}, {feature_center[1]:.3g} mm; "
            f"offset={new_offset[0]:.3g}, {new_offset[1]:.3g} mm)."
        )
        self._refresh_open_3d_views(step_label=label)

    def clear_step_axis_offsets(self) -> None:
        self._begin_history_capture()
        self.lens_step_axis_offset_xy = (0.0, 0.0)
        self.optical_step_axis_offset_xy = (0.0, 0.0)
        self.camera_step_axis_offset_xy = (0.0, 0.0)
        self.led_step_axis_offset_xy = (0.0, 0.0)
        self.lens_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.optical_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.camera_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.led_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self._live_step_overlay_trace_plan_cache = {}
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = False
        self._cad_led_object_edge_pick = False
        self._commit_history_capture()
        self._invalidate_preview_scene_trace()
        self.status_var.set("CAD STEP optical-axis offsets cleared.")
        self._refresh_open_3d_views()

    def clear_step_imports(self) -> None:
        self._begin_history_capture()
        self.imported_camera_step_path = None
        self.imported_lens_step_path = None
        self.imported_optical_step_path = None
        self.imported_led_step_path = None
        self.lens_step_largest_component_only = True
        self.camera_step_rotation_x_deg = 0.0
        self.lens_step_rotation_x_deg = 0.0
        self.optical_step_rotation_x_deg = 0.0
        self.led_step_rotation_x_deg = 0.0
        self.camera_step_rotation_y_deg = 0.0
        self.lens_step_rotation_y_deg = 0.0
        self.optical_step_rotation_y_deg = 0.0
        self.led_step_rotation_y_deg = 0.0
        self.camera_step_rotation_z_deg = 0.0
        self.lens_step_rotation_z_deg = 0.0
        self.optical_step_rotation_z_deg = 0.0
        self.led_step_rotation_z_deg = 0.0
        self.led_object_edge_distance_mm = 0.0
        self.led_step_object_edge_local_z = None
        self.lens_step_axis_offset_xy = (0.0, 0.0)
        self.optical_step_axis_offset_xy = (0.0, 0.0)
        self.camera_step_axis_offset_xy = (0.0, 0.0)
        self.led_step_axis_offset_xy = (0.0, 0.0)
        self.lens_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.optical_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.camera_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.led_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = False
        self._cad_led_object_edge_pick = False
        self._selected_step_label = None
        self._commit_history_capture()
        self._live_step_overlay_trace_plan_cache = {}
        self._invalidate_preview_scene_trace()
        self.status_var.set("Camera/lens/optical/LED STEP imports cleared.")
        self._refresh_open_3d_views()

    def _has_imported_step_cad(self) -> bool:
        if any(
            path is not None
            for path in (
                self.imported_lens_step_path,
                self.imported_optical_step_path,
                self.imported_led_step_path,
                self.imported_camera_step_path,
            )
        ):
            return True
        for row in getattr(self, "rows", ()):
            if self._resolve_row_saved_step_source_path(row) is not None:
                return True
        return False

    def _step_export_alignment_params(self, label: str) -> dict[str, object] | None:
        label = str(label).strip().lower()
        if label == "lens":
            if self.imported_lens_step_path is None:
                return None
            cylinder_axis = self._step_primary_cylinder_axis(self.imported_lens_step_path)
            return {
                "path": self.imported_lens_step_path,
                "largest_component": bool(getattr(self, "lens_step_largest_component_only", True)),
                "source_axis": cylinder_axis if cylinder_axis is not None else "pca0",
                "front_face": "max",
                "target_front_z": self._lens_front_datum_z(),
                "label": "Lens STEP",
                "roll_deg": float(getattr(self, "lens_step_rotation_z_deg", 0.0)),
                "x_rotation_deg": float(getattr(self, "lens_step_rotation_x_deg", 0.0)),
                "y_rotation_deg": float(getattr(self, "lens_step_rotation_y_deg", 0.0)),
                "axis_offset_xy": self._step_axis_offset_xy("lens"),
                "placement_offset_xyz": self._step_placement_offset_xyz("lens"),
            }
        if label == "camera":
            if self.imported_camera_step_path is None:
                return None
            camera_front_z = self._current_image_plane_z() - self._current_camera_front_to_sensor_mm()
            return {
                "path": self.imported_camera_step_path,
                "largest_component": True,
                "source_axis": "z",
                "front_face": "max",
                "target_front_z": camera_front_z,
                "label": "Camera STEP",
                "roll_deg": float(getattr(self, "camera_step_rotation_z_deg", 0.0)),
                "x_rotation_deg": float(getattr(self, "camera_step_rotation_x_deg", 0.0)),
                "y_rotation_deg": float(getattr(self, "camera_step_rotation_y_deg", 0.0)),
                "axis_offset_xy": self._step_axis_offset_xy("camera"),
                "placement_offset_xyz": self._step_placement_offset_xyz("camera"),
            }
        if label == "optical":
            if self.imported_optical_step_path is None:
                return None
            return {
                "path": self.imported_optical_step_path,
                "largest_component": False,
                "source_axis": "z",
                "front_face": "min",
                "target_front_z": 0.0,
                "label": "Optical STEP",
                "roll_deg": float(getattr(self, "optical_step_rotation_z_deg", 0.0)),
                "x_rotation_deg": float(getattr(self, "optical_step_rotation_x_deg", 0.0)),
                "y_rotation_deg": float(getattr(self, "optical_step_rotation_y_deg", 0.0)),
                "axis_offset_xy": self._step_axis_offset_xy("optical"),
                "placement_offset_xyz": self._step_placement_offset_xyz("optical"),
            }
        if label == "led":
            if self.imported_led_step_path is None:
                return None
            return {
                "path": self.imported_led_step_path,
                "largest_component": False,
                "source_axis": "z",
                "front_face": "min",
                "target_front_z": self._led_step_z_translation(),
                "label": "LED STEP",
                "roll_deg": float(getattr(self, "led_step_rotation_z_deg", 0.0)),
                "x_rotation_deg": float(getattr(self, "led_step_rotation_x_deg", 0.0)),
                "y_rotation_deg": float(getattr(self, "led_step_rotation_y_deg", 0.0)),
                "axis_offset_xy": self._step_axis_offset_xy("led"),
                "placement_offset_xyz": self._step_placement_offset_xyz("led"),
            }
        return None

    def _step_alignment_affine(self, params: dict[str, object]) -> np.ndarray | None:
        path = Path(params["path"])
        source_mesh = self._load_step_mesh(
            path,
            largest_component=bool(params.get("largest_component", False)),
        )
        aligned_mesh = self._cad_mesh_aligned_to_optical_axis(
            source_mesh,
            source_axis=params.get("source_axis", "z"),
            front_face=str(params.get("front_face", "min")),
            target_front_z=float(params.get("target_front_z", 0.0)),
            label=str(params.get("label", "STEP")),
            roll_deg=float(params.get("roll_deg", 0.0)),
            x_rotation_deg=float(params.get("x_rotation_deg", 0.0)),
            y_rotation_deg=float(params.get("y_rotation_deg", 0.0)),
            axis_offset_xy=params.get("axis_offset_xy"),
            placement_offset_xyz=params.get("placement_offset_xyz"),
        )
        if aligned_mesh is None:
            return None
        matrix = _affine_from_point_sets(
            np.asarray(source_mesh.points, dtype=float),
            np.asarray(aligned_mesh.points, dtype=float),
        )
        return matrix

    def _resolve_row_saved_step_source_path(self, row) -> Path | None:
        advanced = getattr(row, "advanced", {})
        if not isinstance(advanced, dict):
            return None
        source_path_text = str(advanced.get("OpticalSolidSourcePath", "") or "").strip()
        if not source_path_text:
            return None
        source_format = str(advanced.get("OpticalSolidSourceFormat", "") or "").strip().upper()
        source_suffix = Path(source_path_text).suffix.lower()
        if source_format not in {"STEP", "STP"} and source_suffix not in {".step", ".stp"}:
            return None
        candidates: list[Path] = []
        try:
            candidates.append(Path(source_path_text).expanduser())
        except Exception:
            pass
        try:
            candidates.append(_resolve_project_file_path(source_path_text))
        except Exception:
            pass
        try:
            basename = Path(source_path_text).name
        except Exception:
            basename = ""
        if basename:
            for root in (
                PROJECT_ROOT / "attachment" / "prisms",
                PROJECT_ROOT / "attachment",
                PROJECT_ROOT,
            ):
                try:
                    if not root.exists():
                        continue
                except Exception:
                    continue
                try:
                    candidates.extend(sorted(root.rglob(basename)))
                except Exception:
                    continue
        seen: set[str] = set()
        for candidate in candidates:
            try:
                resolved = Path(candidate).expanduser()
            except Exception:
                continue
            key = str(resolved)
            if key in seen:
                continue
            seen.add(key)
            try:
                if resolved.exists():
                    return resolved.resolve()
            except Exception:
                continue
        return None

    def _row_native_step_alignment_affine(self, source_path: Path, row_index: int, system) -> np.ndarray | None:
        try:
            from KrakenOS.UI.scene_builder import _runtime_optical_solid_transform
        except Exception:
            _runtime_optical_solid_transform = None
        try:
            from KrakenOS.UI.nonseq_output_ports import _source_to_runtime_world_transform
        except Exception:
            _source_to_runtime_world_transform = None
        try:
            from KrakenOS.UI.optical_solid_metadata import rotation_matrix_from_kraken_tilts
        except Exception:
            rotation_matrix_from_kraken_tilts = None
        if rotation_matrix_from_kraken_tilts is not None:
            try:
                z_station = 0.0
                for previous_row in self.rows[: int(row_index)]:
                    z_station += float(getattr(previous_row, "thickness", 0.0) or 0.0)
                source_to_trace = np.eye(4, dtype=float)
                source_to_trace[:3, :3] = np.asarray(
                    rotation_matrix_from_kraken_tilts(
                        float(getattr(self.rows[row_index], "tilt_x", 0.0) or 0.0),
                        float(getattr(self.rows[row_index], "tilt_y", 0.0) or 0.0),
                        float(getattr(self.rows[row_index], "tilt_z", 0.0) or 0.0),
                    ),
                    dtype=float,
                )
                source_to_trace[:3, 3] = np.asarray(
                    [
                        float(getattr(self.rows[row_index], "desp_x", 0.0) or 0.0),
                        float(getattr(self.rows[row_index], "desp_y", 0.0) or 0.0),
                        float(z_station) + float(getattr(self.rows[row_index], "desp_z", 0.0) or 0.0),
                    ],
                    dtype=float,
                )
                if source_to_trace.shape == (4, 4) and np.all(np.isfinite(source_to_trace)):
                    return source_to_trace
            except Exception:
                pass
        if _runtime_optical_solid_transform is not None:
            matrix = _runtime_optical_solid_transform(system, int(row_index))
            if matrix is not None:
                try:
                    matrix = np.asarray(matrix, dtype=float).reshape(4, 4)
                except Exception:
                    matrix = None
                if matrix is not None and np.all(np.isfinite(matrix)):
                    return matrix
        _load_3d_backends()
        if pv is None:
            return None
        surfaces = getattr(system, "AAA", None)
        if surfaces is None:
            return None
        try:
            target_mesh = pv.wrap(surfaces[row_index]).copy(deep=True)
            if int(getattr(target_mesh, "n_points", 0)) <= 0:
                target_mesh = pv.wrap(surfaces[row_index]).extract_surface(
                    algorithm="dataset_surface"
                ).copy(deep=True)
        except Exception:
            return None
        if _source_to_runtime_world_transform is not None:
            try:
                runtime_meshes = getattr(system, "EEE", None)
                runtime_mesh = (
                    runtime_meshes[int(row_index)]
                    if runtime_meshes is not None and 0 <= int(row_index) < len(runtime_meshes)
                    else target_mesh
                )
                matrix = _source_to_runtime_world_transform(self.rows[row_index], runtime_mesh)
            except Exception:
                matrix = None
            if matrix is not None:
                try:
                    matrix = np.asarray(matrix, dtype=float).reshape(4, 4)
                except Exception:
                    matrix = None
                if matrix is not None and np.all(np.isfinite(matrix)):
                    return matrix
        try:
            source_mesh = self._load_step_mesh(source_path, largest_component=False)
        except Exception:
            source_mesh = None
        advanced = getattr(self.rows[row_index], "advanced", {})
        bridge_mesh = None
        bridge_path_text = str(advanced.get("Solid_3d_stl", "") or "").strip() if isinstance(advanced, dict) else ""
        metadata = advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR) if isinstance(advanced, dict) else None
        if bridge_path_text:
            try:
                bridge_path = _resolve_project_file_path(bridge_path_text)
                if bridge_path.exists():
                    bridge_mesh = pv.read(str(bridge_path)).extract_surface(
                        algorithm="dataset_surface"
                    ).copy(deep=True)
            except Exception:
                bridge_mesh = None
        if bridge_mesh is not None:
            source_centroids = self._mesh_face_centroids_from_metadata(bridge_mesh, metadata)
            target_centroids = self._mesh_face_centroids_from_metadata(target_mesh, metadata)
        else:
            source_centroids = None
            target_centroids = None
        if source_mesh is None:
            return None
        candidates: list[np.ndarray | None] = []
        if bridge_mesh is not None:
            candidates.extend(
                [
                    self._rigid_affine_from_point_sets(
                        np.asarray(bridge_mesh.points, dtype=float),
                        np.asarray(target_mesh.points, dtype=float),
                    ),
                    _affine_from_point_sets(
                        np.asarray(bridge_mesh.points, dtype=float),
                        np.asarray(target_mesh.points, dtype=float),
                    ),
                ]
            )
        if source_centroids is not None and target_centroids is not None:
            candidates.append(self._rigid_affine_from_point_sets(source_centroids, target_centroids))
        candidates.extend(
            [
                _affine_from_point_sets(
                    np.asarray(source_mesh.points, dtype=float),
                    np.asarray(target_mesh.points, dtype=float),
                ),
                self._rigid_affine_from_point_sets(
                    np.asarray(source_mesh.points, dtype=float),
                    np.asarray(target_mesh.points, dtype=float),
                ),
                self._mesh_icp_affine(source_mesh, target_mesh),
            ]
        )
        candidates.append(
            _affine_from_point_sets(
                np.asarray(source_mesh.points, dtype=float),
                np.asarray(target_mesh.points, dtype=float),
            )
        )
        if bridge_mesh is not None:
            source_to_bridge = _affine_from_point_sets(
                np.asarray(source_mesh.points, dtype=float),
                np.asarray(bridge_mesh.points, dtype=float),
            )
            if source_to_bridge is not None:
                bridge_to_trace = _affine_from_point_sets(
                    np.asarray(bridge_mesh.points, dtype=float),
                    np.asarray(target_mesh.points, dtype=float),
                )
                if bridge_to_trace is not None:
                    candidates.append(bridge_to_trace @ source_to_bridge)
        source_to_trace = self._mesh_icp_affine(source_mesh, target_mesh)
        if source_to_trace is not None:
            candidates.append(source_to_trace)
        if bridge_mesh is not None:
            source_to_bridge = self._mesh_icp_affine(source_mesh, bridge_mesh)
            if source_to_bridge is not None:
                bridge_to_trace = self._mesh_icp_affine(bridge_mesh, target_mesh)
                if bridge_to_trace is not None:
                    candidates.append(bridge_to_trace @ source_to_bridge)
        return self._best_alignment_affine(source_mesh, target_mesh, candidates)

    def _collect_row_native_step_export_shapes(self, system, progress_callback=None) -> list[tuple[str, object]]:
        shape_items: list[tuple[str, object]] = []
        surfaces = getattr(system, "AAA", None)
        transforms = getattr(system, "TRANS_2A", None)
        if surfaces is None or transforms is None:
            return shape_items
        try:
            surface_count = len(surfaces)
        except Exception:
            surface_count = int(getattr(surfaces, "n_blocks", 0) or 0)
        hidden_rows, _hidden_labels, _rays_hidden = self._step_export_hidden_state()
        block_count = min(len(self.rows), int(surface_count), len(transforms))
        for row_index in range(block_count):
            if row_index in hidden_rows:  # skip hidden rows from the export
                continue
            row = self.rows[row_index]
            if getattr(row, "surface", "") in {"Object", "Image"}:
                continue
            source_path = self._resolve_row_saved_step_source_path(row)
            if source_path is None:
                continue
            if progress_callback is not None:
                progress_callback(
                    f"Preparing S{row_index} {(row.name or row.surface or 'STEP solid')}",
                    row_index + 1,
                    block_count,
                )
            try:
                matrix = self._row_native_step_alignment_affine(source_path, row_index, system)
                if matrix is None:
                    _load_3d_backends()
                    if pv is not None:
                        source_mesh = self._load_step_mesh(source_path, largest_component=False)
                        target_mesh = pv.wrap(surfaces[row_index]).copy(deep=True)
                        matrix = self._mesh_icp_affine(source_mesh, target_mesh)
                if matrix is None:
                    raise RuntimeError("could not compute saved-row CAD placement affine")
                shape = _read_step_shape(source_path)
                label = f"S{row_index} {row.name or row.element or row.surface or 'STEP solid'}"
                shape_items.append((label, _shape_with_affine(shape, matrix)))
            except Exception as exc:
                self.append_debug(
                    f"3D STEP native row export skipped for S{row_index} "
                    f"{row.name or row.surface}: {exc}"
                )
        return shape_items

    def _step_export_hidden_state(self):
        """Hidden rows / STEP labels + whether rays are hidden, from the 3D
        inspector, so the STEP export only writes non-hidden geometry."""
        inspector = getattr(self, "_three_d_inspector", None)
        if inspector is None:
            return frozenset(), frozenset(), False
        hidden_rows = frozenset(int(r) for r in (getattr(inspector, "_hidden_scene_rows", None) or ()))
        hidden_labels = frozenset(
            str(label).strip().lower() for label in (getattr(inspector, "_hidden_step_labels", None) or ())
        )
        rays_var = getattr(inspector, "show_rays_var", None)
        rays_hidden = bool(rays_var is not None and not rays_var.get())
        return hidden_rows, hidden_labels, rays_hidden

    def _export_mesh_label_hidden(self, label, hidden_rows, hidden_labels) -> bool:
        label = str(label)
        for prefix in ("surface_", "edge_"):
            if label.startswith(prefix):
                head = label[len(prefix):].split("_", 1)[0]
                if head.isdigit() and int(head) in hidden_rows:
                    return True
        for step_label in ("lens", "camera", "optical", "led"):
            if label == f"{step_label}_step" and step_label in hidden_labels:
                return True
        return False

    def _collect_native_step_export_shapes(self, system=None, progress_callback=None) -> list[tuple[str, object]]:
        shape_items: list[tuple[str, object]] = []
        hidden_rows, hidden_labels, _rays_hidden = self._step_export_hidden_state()
        labels = STEP_OVERLAY_LABELS
        for index, label in enumerate(labels, start=1):
            if str(label).strip().lower() in hidden_labels:  # skip hidden STEP overlays
                continue
            params = self._step_export_alignment_params(label)
            if params is None:
                continue
            if progress_callback is not None:
                progress_callback(
                    f"Preparing {params.get('label', label)} native STEP",
                    index,
                    len(labels),
                )
            try:
                matrix = self._step_alignment_affine(params)
                if matrix is None:
                    raise RuntimeError("could not compute CAD placement affine")
                shape = _read_step_shape(Path(params["path"]))
                shape_items.append((str(params.get("label", label)), _shape_with_affine(shape, matrix)))
            except Exception as exc:
                self.append_debug(f"3D STEP native {label} export skipped: {exc}")
        if system is not None:
            shape_items.extend(
                self._collect_row_native_step_export_shapes(
                    system,
                    progress_callback=progress_callback,
                )
            )
        return shape_items

    def _step_export_ray_polylines(self, system) -> list[np.ndarray]:
        if self._step_export_hidden_state()[2]:  # rays hidden in the browser
            return []
        previous_ray_count = getattr(self, "_preview_field_ray_count", None)
        previous_bundle_count = getattr(self, "_preview_field_bundle_count", None)
        rays_per_group = previous_ray_count
        try:
            wavelength = self._current_wavelength()
            max_radius = max((max(float(row.diameter) / 2.0, 0.5) for row in self.rows), default=1.0)
            rays = Kos.raykeeper(system)
            self._trace_preview_rays(
                system,
                rays,
                wavelength,
                max_radius,
                allow_full_pupil=True,
                sampling_mode="world_envelope",
            )
            rays_per_group = getattr(self, "_preview_field_ray_count", previous_ray_count)
        except Exception as exc:
            self.append_debug(f"3D STEP ray export skipped: {exc}")
            rays = self.last_rays
        finally:
            if previous_ray_count is not None:
                self._preview_field_ray_count = previous_ray_count
            if previous_bundle_count is not None:
                self._preview_field_bundle_count = previous_bundle_count
        polylines: list[np.ndarray] = []
        for ray in getattr(rays, "CC", ()) if rays is not None else ():
            pts = np.asarray(ray, dtype=float)
            if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 3:
                continue
            if not np.any(np.all(np.isfinite(pts[:, :3]), axis=1)):
                continue
            polylines.append(pts[:, :3].copy())
        envelope = _ray_bundle_envelope_polylines(
            polylines,
            rays_per_group,
        )
        if len(envelope) < len(polylines):
            self.append_progress(
                f"STEP ray export reduced to envelope: {len(envelope)}/{len(polylines)} traced rays"
            )
        return envelope

    def _collect_3d_step_export_meshes(self, system) -> list[tuple[str, object]]:
        _load_3d_backends()
        if pv is None:
            raise RuntimeError("PyVista is required to collect 3D export geometry")

        mesh_items: list[tuple[str, object]] = []
        hidden_rows, hidden_labels, _rays_hidden = self._step_export_hidden_state()

        def add_mesh(label: str, mesh) -> None:
            if mesh is None:
                return
            if self._export_mesh_label_hidden(label, hidden_rows, hidden_labels):
                return  # skip hidden rows / STEP overlays
            try:
                surface = mesh.extract_surface(algorithm="dataset_surface").copy(deep=True)
            except Exception:
                try:
                    surface = mesh.copy(deep=True)
                except Exception:
                    return
            try:
                if int(getattr(surface, "n_points", 0)) > 0:
                    mesh_items.append((label, surface))
            except Exception:
                pass

        transforms = getattr(system, "TRANS_2A", None)
        surfaces = getattr(system, "AAA", None)
        if transforms is not None and surfaces is not None:
            block_count = min(len(self.rows), getattr(surfaces, "n_blocks", 0), len(transforms))
            for index in range(block_count):
                row = self.rows[index]
                if row.surface in {"Object", "Image"}:
                    continue
                add_mesh(
                    f"surface_{index}_{row.name or row.surface}",
                    Kraken3DInspector._mesh_with_transform(surfaces[index], transforms[index]),
                )

        side_index = 0
        for row_index in getattr(system, "side_number", []):
            try:
                body = pv.wrap(system.BBB[side_index]).extract_surface(algorithm="dataset_surface").copy(deep=True)
            except Exception:
                side_index += 1
                continue
            side_index += 1
            if 0 <= int(row_index) < len(self.rows):
                row = self.rows[int(row_index)]
                add_mesh(f"edge_{int(row_index)}_{row.name or row.surface}", body)
            else:
                add_mesh(f"edge_{int(row_index)}", body)

        try:
            add_mesh("external_camera", self._transformed_external_camera_mesh())
        except Exception as exc:
            self.append_debug(f"3D STEP export external camera skipped: {exc}")

        for label, builder in (
            ("lens_step", self._transformed_imported_lens_step_mesh),
            ("optical_step", self._transformed_imported_optical_step_mesh),
            ("led_step", self._transformed_imported_led_step_mesh),
            ("camera_step", self._transformed_imported_camera_step_mesh),
        ):
            try:
                add_mesh(label, builder())
            except Exception as exc:
                self.append_debug(f"3D STEP export {label} skipped: {exc}")

        return mesh_items

    def _collect_step_edge_and_extra_meshes(self, system) -> list[tuple[str, object]]:
        """Collect edge geometry and imported meshes, excluding optical surface
        faces (which are handled analytically)."""
        _load_3d_backends()
        if pv is None:
            return []

        mesh_items: list[tuple[str, object]] = []
        hidden_rows, hidden_labels, _rays_hidden = self._step_export_hidden_state()

        def add_mesh(label: str, mesh) -> None:
            if mesh is None:
                return
            if self._export_mesh_label_hidden(label, hidden_rows, hidden_labels):
                return  # skip hidden rows / STEP overlays
            try:
                surface = mesh.extract_surface(algorithm="dataset_surface").copy(deep=True)
            except Exception:
                try:
                    surface = mesh.copy(deep=True)
                except Exception:
                    return
            try:
                if int(getattr(surface, "n_points", 0)) > 0:
                    mesh_items.append((label, surface))
            except Exception:
                pass

        side_index = 0
        for row_index in getattr(system, "side_number", []):
            try:
                body = pv.wrap(system.BBB[side_index]).extract_surface(
                    algorithm="dataset_surface"
                ).copy(deep=True)
            except Exception:
                side_index += 1
                continue
            side_index += 1
            if 0 <= int(row_index) < len(self.rows):
                row = self.rows[int(row_index)]
                add_mesh(f"edge_{int(row_index)}_{row.name or row.surface}", body)
            else:
                add_mesh(f"edge_{int(row_index)}", body)

        try:
            add_mesh("external_camera", self._transformed_external_camera_mesh())
        except Exception:
            pass

        for label, builder in (
            ("lens_step", self._transformed_imported_lens_step_mesh),
            ("optical_step", self._transformed_imported_optical_step_mesh),
            ("led_step", self._transformed_imported_led_step_mesh),
            ("camera_step", self._transformed_imported_camera_step_mesh),
        ):
            try:
                add_mesh(label, builder())
            except Exception:
                pass

        return mesh_items

    def _ask_step_file(self, title: str, initial_dir: Path, *, parent: tk.Misc | None = None) -> Path | None:
        default_dir = Path(globals().get("ATTACHMENT_DIR", Path.home()))
        preferred_dir = Path(initial_dir) if initial_dir is not None else default_dir
        if not preferred_dir.exists():
            preferred_dir = default_dir if default_dir.exists() else Path.home()
        path = filedialog.askopenfilename(
            title=title,
            initialdir=str(preferred_dir),
            filetypes=[
                ("STEP files", "*.step *.stp *.ste *.STEP *.STP *.STE"),
                ("All files", "*"),
            ],
            parent=parent or self,
        )
        if not path:
            return None
        selected = Path(path).expanduser()
        if not selected.exists():
            messagebox.showerror("STEP file not found", f"File does not exist:\n\n{selected}", parent=parent or self)
            return None
        return selected

    def _refresh_open_3d_views(
        self,
        *,
        camera_only: bool = False,
        step_label: str | None = None,
        force_retrace: bool = False,
    ) -> None:
        if camera_only:
            step_label = "camera"
        if self._three_d_inspector is not None:
            try:
                if self._three_d_inspector.winfo_exists():
                    self._three_d_inspector.refresh_from_editor(force_retrace=force_retrace)
            except Exception:
                pass
        if self._legacy_3d_plotter is not None:
            labels = [step_label] if step_label else list(STEP_OVERLAY_LABELS)
            refreshed = False
            for label in labels:
                if label and self._refresh_legacy_step_actor(self._legacy_3d_plotter, label):
                    refreshed = True
            if refreshed:
                return
            self.status_var.set("STEP change saved. Close and reopen legacy 3D view to redraw.")

    def _clear_open3d_face_metadata_hover_state(self, row_index: int | None = None) -> None:
        inspector = getattr(self, "_three_d_inspector", None)
        if inspector is None:
            return
        try:
            if not inspector.winfo_exists():
                return
        except Exception:
            return
        try:
            inspector.clear_face_metadata_hover_state(row_index)
        except Exception as exc:
            self.append_debug(f"Open 3D face metadata hover clear failed: {exc}")

    def _refresh_legacy_camera_step_actor(self, plotter) -> bool:
        return self._refresh_legacy_step_actor(plotter, "camera")

    def _refresh_legacy_step_actor(self, plotter, label: str) -> bool:
        if plotter is None:
            return False
        scene = dict(getattr(plotter, "_kraken_scene", {}) or {})
        cad_step_actors = dict(scene.get("cad_step_actors", {}) or {})
        cad_step_actor_map = dict(scene.get("cad_step_actor_map", {}) or {})
        step_actors = list(cad_step_actors.get(label, []) or [])
        visibility = dict(getattr(plotter, "_kraken_visibility", {}) or {})
        visible = bool(visibility.get(f"step_{label}", True))
        try:
            builders = {
                "camera": self._transformed_imported_camera_step_mesh,
                "led": self._transformed_imported_led_step_mesh,
                "lens": self._transformed_imported_lens_step_mesh,
                "optical": self._transformed_imported_optical_step_mesh,
            }
            builder = builders.get(label)
            if builder is None:
                return False
            cad_mesh = builder()
        except Exception as exc:
            self.append_debug(f"Legacy 3D {label} STEP refresh failed: {exc}")
            return False
        if cad_mesh is None or int(getattr(cad_mesh, "n_points", 0)) <= 0:
            if not step_actors:
                return False
            hidden = False
            for _kind, actor in step_actors:
                try:
                    actor.SetVisibility(False)
                    hidden = True
                except Exception:
                    pass
            if hidden:
                try:
                    plotter.render()
                except Exception:
                    pass
            return hidden
        try:
            edges = cad_mesh.extract_feature_edges(
                feature_angle=20,
                boundary_edges=True,
                feature_edges=True,
                manifold_edges=False,
            )
        except Exception:
            edges = None
        if not step_actors:
            try:
                color, opacity = {
                    "lens": ("#4b5563", 0.22),
                    "optical": ("#0891b2", 0.30),
                    "led": ("#f59e0b", 0.35),
                    "camera": ("#6b7280", 0.32),
                }.get(label, ("#6b7280", 0.32))
                helper_actors = list(scene.get("helper_actors", []) or [])
                cad_step_actors.setdefault(label, [])
                actor = plotter.add_mesh(
                    cad_mesh,
                    color=color,
                    opacity=opacity,
                    smooth_shading=False,
                    show_edges=False,
                    pickable=True,
                )
                try:
                    actor.SetPickable(True)
                except Exception:
                    pass
                actor_key = Kraken3DInspector._actor_key(actor)
                if actor_key is not None:
                    cad_step_actor_map[actor_key] = label
                try:
                    actor.SetVisibility(visible)
                except Exception:
                    pass
                cad_step_actors[label].append(("mesh", actor))
                if edges is not None and int(getattr(edges, "n_points", 0)) > 0:
                    edge_actor = plotter.add_mesh(edges, color="#111827", line_width=0.8, pickable=False)
                    try:
                        edge_actor.SetVisibility(visible)
                    except Exception:
                        pass
                    cad_step_actors[label].append(("edges", edge_actor))
                scene["helper_actors"] = helper_actors
                scene["cad_step_actors"] = cad_step_actors
                scene["cad_step_actor_map"] = cad_step_actor_map
                setattr(plotter, "_kraken_scene", scene)
                try:
                    plotter.render()
                except Exception:
                    pass
                return True
            except Exception as exc:
                self.append_debug(f"Legacy 3D {label} STEP add failed: {exc}")
                return False
        refreshed = False
        for kind, actor in step_actors:
            try:
                mapper = actor.GetMapper()
                if mapper is None:
                    continue
                if kind == "edges":
                    if edges is None or int(getattr(edges, "n_points", 0)) <= 0:
                        actor.SetVisibility(False)
                        continue
                    mapper.SetInputData(edges)
                    actor.SetVisibility(visible)
                else:
                    mapper.SetInputData(cad_mesh)
                    actor.SetVisibility(visible)
                mapper.Modified()
                refreshed = True
            except Exception as exc:
                self.append_debug(f"Legacy 3D {label} actor update failed: {exc}")
        if refreshed:
            try:
                plotter.render()
            except Exception:
                pass
            if label == "camera":
                self.status_var.set(
                    f"Camera STEP rotation: X={self.camera_step_rotation_x_deg:.0f}, "
                    f"Y={self.camera_step_rotation_y_deg:.0f}, "
                    f"Z={self.camera_step_rotation_z_deg:.0f} deg"
                )
            elif label == "lens":
                self.status_var.set(
                    f"Lens STEP rotation: X={self.lens_step_rotation_x_deg:.0f}, "
                    f"Y={self.lens_step_rotation_y_deg:.0f}, "
                    f"Z={self.lens_step_rotation_z_deg:.0f} deg"
                )
            elif label == "optical":
                self.status_var.set(
                    f"Optical STEP rotation: X={self.optical_step_rotation_x_deg:.0f}, "
                    f"Y={self.optical_step_rotation_y_deg:.0f}, "
                    f"Z={self.optical_step_rotation_z_deg:.0f} deg"
                )
            elif label == "led":
                reference_text = (
                    "unset"
                    if getattr(self, "led_step_object_edge_local_z", None) is None
                    else f"{float(self.led_step_object_edge_local_z):.3g} mm"
                )
                self.status_var.set(
                    f"LED STEP: x rotation={self.led_step_rotation_x_deg:.0f} deg, "
                    f"y rotation={self.led_step_rotation_y_deg:.0f} deg, "
                    f"z rotation={self.led_step_rotation_z_deg:.0f} deg, "
                    f"edge distance={self.led_object_edge_distance_mm:.3g} mm, "
                    f"edge ref={reference_text}"
                )
        return refreshed
