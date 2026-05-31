"""Open 3D STEP overlay promotion service."""

from __future__ import annotations

from typing import Any
import hashlib

import numpy as np

from KrakenOS.UI.optical_solid_metadata import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    normalize_optical_solid_face_metadata,
)
from KrakenOS.UI.scene_placement import SCENE_PLACEMENT_ADVANCED_ATTR, normalize_scene_placement_settings
from KrakenOS.UI.services import cad_cache_paths
from KrakenOS.UI.services.optical_solid_geometry import (
    format_stl_mesh_diagnostics,
    inspect_stl_mesh,
    short_stl_mesh_diagnostics,
)
from KrakenOS.UI.services.step_native_reconstruction import reconstruct_step_native_surfaces
from KrakenOS.UI.services.step_overlay_analytic_fit import (
    PlaneFit,
    SphereFit,
    ToroidFit,
    fit_plane,
    fit_step_overlay_analytic_surfaces,
    maybe_split_full_sphere_face,
)
from KrakenOS.UI.services.step_overlay_labels import STEP_OVERLAY_LABEL_SET
from KrakenOS.UI.surface_table_model import SurfaceRow


def _refine_face_normals_from_mesh(
    faces: list[dict[str, Any]],
    mesh: Any,
) -> None:
    """Replace each face's metadata normal with body-centroid-derived normal.

    Some STEP files (e.g. the Edmund 34754 plano-cylindrical lens)
    arrive with face metadata where most faces report the same normal
    direction even though they're actually perpendicular to different
    body axes. The importer's centroid-area-weighting collapses badly
    on bodies whose native frame doesn't align with world axes.

    For axisymmetric optical bodies (lenses, prisms with paired flat
    sides), the OUTWARD normal at each face's centroid is reliably
    given by

        face_outward_normal = normalize(face_centroid - body_centroid)

    where body_centroid is the mean of all face centroids. This holds
    for spheres, plano-convex, plano-concave, biconcave, biconvex,
    cemented doublets, and plano-cylindrical lenses -- every face's
    centroid sits on the outside of the body, so the offset direction
    from the body interior IS the face's outward normal.

    The refined normals are written in place; the original metadata
    normal is preserved as ``normal_metadata`` for diagnostics.

    Faces whose centroids sit essentially AT the body centroid
    (radially-symmetric annulus faces, etc.) are left untouched
    because the offset direction is degenerate. The same applies
    when the mesh is missing.
    """
    if mesh is None or not faces:
        return
    # Guard: only refine when the metadata normals are missing the
    # anti-parallel pair that would let the optical-axis detection
    # work. If the metadata already has a pair (e.g. an achromat
    # whose front and back sphere faces have opposite normals), the
    # metadata is trustworthy and any "refine" would replace the
    # rim's correctly-perpendicular normals with axis-pointing ones,
    # making the rim incorrectly qualify as an optical face.
    metadata_normals: list[np.ndarray] = []
    for f in faces:
        try:
            n = np.asarray(f.get("normal") or (), dtype=float).reshape(-1)[:3]
        except Exception:
            n = np.empty((0,), dtype=float)
        if n.size != 3:
            continue
        norm = float(np.linalg.norm(n))
        if norm < 1e-9:
            metadata_normals.append(np.zeros(3))
        else:
            metadata_normals.append(n / norm)
    has_pair = False
    for i in range(len(metadata_normals)):
        for j in range(i + 1, len(metadata_normals)):
            ni = metadata_normals[i]
            nj = metadata_normals[j]
            if float(np.linalg.norm(ni)) < 1e-6 or float(np.linalg.norm(nj)) < 1e-6:
                continue
            if float(np.dot(ni, nj)) < -0.95:
                has_pair = True
                break
        if has_pair:
            break
    if has_pair:
        return  # metadata is trustworthy, leave alone

    face_centroids: list[np.ndarray] = []
    keep_indices: list[int] = []
    for index, f in enumerate(faces):
        c = f.get("centroid")
        if c is None:
            continue
        try:
            cv = np.asarray(c, dtype=float).reshape(3)
        except Exception:
            continue
        if not np.all(np.isfinite(cv)):
            continue
        face_centroids.append(cv)
        keep_indices.append(index)
    if len(face_centroids) < 2:
        return
    body_centroid = np.mean(np.asarray(face_centroids), axis=0)
    for face_idx, fcentroid in zip(keep_indices, face_centroids):
        offset = fcentroid - body_centroid
        norm = float(np.linalg.norm(offset))
        if norm < 1e-6:
            continue  # face sits at body centroid - degenerate
        outward = offset / norm
        f = faces[face_idx]
        if "normal_metadata" not in f:
            f["normal_metadata"] = list(f.get("normal") or [])
        f["normal"] = [float(outward[0]), float(outward[1]), float(outward[2])]


def _auto_assign_lens_face_functions(faces: list[dict[str, Any]]) -> int:
    """Conservatively assign Transmit/Port to the refractive faces of a lens.

    Heuristic (revised): every preserved face whose centroid normal
    is parallel-or-anti-parallel to a shared optical axis is treated
    as a refractive optical surface. The shared optical axis is
    inferred from the largest-area face's normal -- it's the most
    reliable indicator of the body's optical axis direction. Faces
    whose normals are within ``cos > 0.95`` of ``+axis`` or
    ``cos < -0.95`` of ``-axis`` are flagged ``Transmit/Port``;
    everything else (cylinder side walls, oblique facets) becomes
    ``Absorber/Mechanical``.

    Compared to the previous "two largest faces only" rule, this
    correctly handles:
      * singlets (2 axis-aligned faces -> 2 Transmit/Port surfaces)
      * cemented doublets (3 axis-aligned faces if the importer
        surfaces the interior cement face; otherwise only the 2
        outer faces fire and the cement layer needs the OCC native
        path)
      * any body where the cement / interior faces happen to be
        smaller than the side cylinder

    Bodies whose largest face isn't paired with at least one
    anti-parallel partner (e.g. a single-face sphere or a prism)
    fall through to the existing ``Unassigned`` default so the
    manual face-roles dialog still applies.

    Returns the number of faces touched. Caller re-normalizes the
    metadata afterward so role/function fields end up canonical.
    """
    if not faces:
        return 0
    # Only act when every face is currently Unassigned so a previous
    # manual or upstream assignment survives a re-promote.
    target_indices: list[int] = []
    for index, face in enumerate(faces):
        if not isinstance(face, dict):
            continue
        function = str(face.get("function") or face.get("role") or "Unassigned").strip()
        if function and function != "Unassigned":
            return 0
        target_indices.append(index)
    if len(target_indices) < 2:
        return 0
    # Normalize every face's normal once and stash beside its index.
    normalized_normals: list[tuple[int, np.ndarray, float]] = []
    for index in target_indices:
        try:
            normal = np.asarray(faces[index].get("normal") or (), dtype=float).reshape(-1)[:3]
        except Exception:
            continue
        if normal.size < 3 or not np.all(np.isfinite(normal)):
            continue
        norm = float(np.linalg.norm(normal))
        if norm < 1e-9:
            continue
        normalized_normals.append((index, normal / norm, float(faces[index].get("area_mm2", 0.0) or 0.0)))
    if len(normalized_normals) < 2:
        return 0
    # Optical-axis direction: find the largest PAIR of faces with
    # anti-parallel normals -- those are a true front/back optical
    # pair. The single-largest-face heuristic broke on parts where
    # the cylindrical RIM happens to have more area than each curved
    # cap (e.g. Edmund DCV 32992: rim 497 mm^2 > each curved face
    # 479 mm^2). Picking the rim's normal misaligns the axis 90 deg
    # from the actual optical axis and the curved faces get
    # rejected.
    #
    # Algorithm: for every pair (i,j) with anti-parallel normals
    # (cos(theta) < -0.95), record max(area_i, area_j) + min(...).
    # The pair with the largest combined area defines the axis;
    # the front of that pair is whichever has axial_pos < the other.
    pair_axis: np.ndarray | None = None
    best_pair_area = -1.0
    for i in range(len(normalized_normals)):
        idx_i, n_i, area_i = normalized_normals[i]
        for j in range(i + 1, len(normalized_normals)):
            idx_j, n_j, area_j = normalized_normals[j]
            if float(np.dot(n_i, n_j)) > -0.95:
                continue
            combined = area_i + area_j
            if combined > best_pair_area:
                best_pair_area = combined
                # Convention: axis points along the light-propagation
                # direction. -n_i if i is the "front" (smaller
                # axial_pos along axis = -n_i). If i and j are on
                # opposite sides of the body centroid, either choice
                # works topologically; we pick -n_i and let the
                # later sort by axial_pos canonicalise the front.
                pair_axis = -n_i
    if pair_axis is None:
        # No anti-parallel pair survived; fall back to the previous
        # single-largest-face heuristic so a sphere / single-face
        # body still gets a chance.
        largest = max(normalized_normals, key=lambda t: t[2])
        axis = -largest[1]
    else:
        axis = pair_axis
    # An optical face has its normal parallel-or-anti-parallel to the
    # axis (within ~18 deg). Compute axial position (signed projection
    # of the centroid onto the axis) so faces at the same axial depth
    # can be clustered -- a real lens surface tends to come with a
    # small annular edge ring sitting at the SAME axial depth; only
    # the largest face per cluster is the refractive surface.
    axis_aligned: list[dict[str, Any]] = []
    for index, normal, area in normalized_normals:
        if abs(float(np.dot(normal, axis))) < 0.95:
            continue
        try:
            centroid = np.asarray(faces[index].get("centroid") or (), dtype=float).reshape(-1)[:3]
        except Exception:
            continue
        if centroid.size < 3 or not np.all(np.isfinite(centroid)):
            continue
        axial_pos = float(np.dot(centroid, axis))
        axis_aligned.append({"index": index, "axial_pos": axial_pos, "area": area})
    if len(axis_aligned) < 2:
        return 0
    # Drop tiny annular edge rings BEFORE clustering. The DCV's STEP
    # decomposes each end into a big concave surface (~474 mm²) and a
    # small annular ring on the edge (~23 mm²), and their centroids
    # are far enough apart axially (~1.45 mm) that a clustering
    # tolerance can't merge them without also fusing the front and
    # back surfaces of a thin lens. Filtering by relative area is a
    # cleaner separation: optical surfaces are by definition large
    # compared to side-edge facets.
    max_aligned_area = max(entry["area"] for entry in axis_aligned)
    if max_aligned_area > 0:
        axis_aligned = [
            entry for entry in axis_aligned
            if entry["area"] >= 0.1 * max_aligned_area
        ]
    if len(axis_aligned) < 2:
        return 0
    # Cluster by axial position. Tolerance is 0.5 mm absolute -- small
    # enough that the front and back of a thin lens stay separate
    # (DCV is 2.5 mm thick), big enough that a planar face split into
    # several coplanar patches by the importer still merges.
    axis_aligned.sort(key=lambda entry: entry["axial_pos"])
    tolerance = 0.5
    clusters: list[list[dict[str, Any]]] = [[axis_aligned[0]]]
    for entry in axis_aligned[1:]:
        if abs(entry["axial_pos"] - clusters[-1][-1]["axial_pos"]) < tolerance:
            clusters[-1].append(entry)
        else:
            clusters.append([entry])
    if len(clusters) < 2:
        return 0
    # Confirm the body has a genuine front+back: there must be one
    # cluster with negative axial position (relative to the axis-aligned
    # group) AND one with positive. Equivalently the largest face from
    # the first cluster and the largest from the last cluster must
    # have anti-parallel normals.
    rep_indices: list[int] = [
        max(cluster, key=lambda entry: entry["area"])["index"] for cluster in clusters
    ]
    def _unit(vec_obj):
        try:
            arr = np.asarray(vec_obj or (), dtype=float).reshape(3)
        except Exception:
            return None
        if arr.size != 3 or not np.all(np.isfinite(arr)):
            return None
        norm = float(np.linalg.norm(arr))
        if norm < 1e-9:
            return None
        return arr / norm

    front_normal = _unit(faces[rep_indices[0]].get("normal"))
    back_normal = _unit(faces[rep_indices[-1]].get("normal"))
    if front_normal is None or back_normal is None:
        return 0
    if float(np.dot(front_normal, back_normal)) > -0.95:
        return 0
    assigned = 0
    transmit_set = set(rep_indices)
    for order, idx in enumerate(rep_indices):
        face = faces[idx]
        face["function"] = "Transmit/Port"
        # First face along the axis becomes Input; the rest are
        # Output / interior. The renderer doesn't gate refraction on
        # the role text -- it's purely cosmetic.
        face["role"] = "Input" if order == 0 else "Output"
        face["assignment_origin"] = "auto_lens_promotion"
        assigned += 1
    for index, face in enumerate(faces):
        if index in transmit_set:
            continue
        if not isinstance(face, dict):
            continue
        face["function"] = "Absorber/Mechanical"
        face["role"] = "Absorber/Mechanical"
        face["assignment_origin"] = "auto_lens_promotion"
        assigned += 1
    return assigned


class StepOverlayPromotionService:
    """Plan and promote imported STEP overlays into row-backed optical solids."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    @staticmethod
    def _normalize_glass_sequence(value: object) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            parts = value.replace(";", ",").split(",")
        else:
            try:
                parts = list(value)  # type: ignore[arg-type]
            except Exception:
                parts = [value]
        return tuple(str(item).strip() for item in parts if str(item).strip())

    @staticmethod
    def _promoted_local_step_face_metadata(
        metadata: object,
        *,
        center_world: np.ndarray,
        promoted_path,
        source_path,
        max_triangle_index: int,
    ) -> dict[str, object] | None:
        """Convert imported STEP face metadata from world to promoted-row local coordinates."""

        if not isinstance(metadata, dict):
            return None
        try:
            center = np.asarray(center_world, dtype=float).reshape(-1)[:3]
        except Exception:
            return None
        if center.size < 3 or not np.all(np.isfinite(center[:3])):
            return None
        faces: list[dict[str, object]] = []
        for face in list(metadata.get("faces", []) or []):
            if not isinstance(face, dict):
                continue
            record = dict(face)
            try:
                centroid = np.asarray(record.get("centroid", ()), dtype=float).reshape(-1)[:3]
            except Exception:
                centroid = np.asarray([], dtype=float)
            if centroid.size >= 3 and np.all(np.isfinite(centroid[:3])):
                local_centroid = centroid[:3] - center[:3]
                record["centroid"] = [float(value) for value in local_centroid[:3]]
            record.pop("centroid_world", None)
            record.pop("normal_world", None)
            indices: list[int] = []
            for value in list(record.get("triangle_indices", record.get("cell_indices", ())) or []):
                try:
                    index = int(value)
                except Exception:
                    continue
                if 0 <= index < int(max_triangle_index):
                    indices.append(index)
            if not indices:
                continue
            record["triangle_indices"] = indices
            record["triangle_count"] = len(indices)
            try:
                normal = np.asarray(record.get("normal", ()), dtype=float).reshape(-1)[:3]
            except Exception:
                normal = np.asarray([], dtype=float)
            try:
                centroid = np.asarray(record.get("centroid", ()), dtype=float).reshape(-1)[:3]
            except Exception:
                centroid = np.asarray([], dtype=float)
            if normal.size >= 3 and centroid.size >= 3 and np.all(np.isfinite(normal[:3])) and np.all(np.isfinite(centroid[:3])):
                record["plane_offset_mm"] = float(np.dot(normal[:3], centroid[:3]))
            faces.append(record)
        if not faces:
            return None

        virtual_planes: list[dict[str, object]] = []
        for plane in list(metadata.get("virtual_planes", []) or []):
            if not isinstance(plane, dict):
                continue
            record = dict(plane)
            try:
                point = np.asarray(record.get("point", ()), dtype=float).reshape(-1)[:3]
            except Exception:
                point = np.asarray([], dtype=float)
            if point.size >= 3 and np.all(np.isfinite(point[:3])):
                record["point"] = [float(value) for value in (point[:3] - center[:3])]
            virtual_planes.append(record)

        # Auto-assign Transmit/Port + Absorber/Mechanical to lens-shaped
        # bodies BEFORE normalization runs. The trace path consumes the
        # normalized face function to decide refract-vs-block, so
        # without this every freshly promoted STL refracts per triangle
        # and rays bend erratically (captured in 3D.png after the
        # penta-telescope cascade build). Prisms and any body whose two
        # largest faces aren't anti-parallel fall through to the
        # Unassigned default and still need a manual face-roles pass.
        try:
            auto_assigned_count = _auto_assign_lens_face_functions(faces)
        except Exception:
            auto_assigned_count = 0
        source_stl = str(promoted_path)
        normalized = normalize_optical_solid_face_metadata(
            {
                "source_stl": source_stl,
                "faces": faces,
                "virtual_planes": virtual_planes,
            },
            source_stl=source_stl,
        )
        for key in (
            "source_backend",
            "source_face_count",
            "outer_face_count",
            "interior_duplicate_count",
        ):
            if key in metadata:
                normalized[key] = metadata[key]
        normalized["source_step"] = str(source_path)
        normalized["promoted_face_metadata_source"] = "open3d_step_overlay"
        normalized["metadata_coordinates"] = "local_centered_promoted_row"
        if auto_assigned_count:
            normalized["auto_assigned_lens_face_count"] = int(auto_assigned_count)
        return normalized

    def _step_overlay_insert_index(self, insert_at: int | None, *, use_current_selection: bool = True) -> tuple[int, str]:
        arm_key = ""
        if insert_at is None:
            selected_indices = self._selected_table_indices() if use_current_selection else []
            arm_key = self._current_arm_view_key() if use_current_selection else ""
            if selected_indices:
                resolved_insert_at = max(selected_indices) + 1
            elif arm_key:
                resolved_insert_at = self._default_insert_index_for_arm_key(arm_key)
            else:
                resolved_insert_at = len(self.rows)
                if self.rows and self.rows[-1].surface == "Image":
                    resolved_insert_at -= 1
        else:
            resolved_insert_at = int(insert_at)
            arm_key = self._current_arm_view_key() if use_current_selection else ""
        resolved_insert_at = max(
            1,
            min(resolved_insert_at, len(self.rows) - (1 if self.rows and self.rows[-1].surface == "Image" else 0)),
        )
        return int(resolved_insert_at), str(arm_key or "")

    @staticmethod
    def _native_step_anchor_local_z(reconstruction, face_id: str) -> dict[str, object] | None:
        requested = str(face_id or "").strip()
        if not requested:
            return None
        fits = list(getattr(reconstruction, "surface_fits", ()) or ())
        if not fits:
            return None
        try:
            min_z = min(float(fit.vertex_z_mm) for fit in fits)
        except Exception:
            return None
        for fit in fits:
            fit_face_ids = [str(value).strip() for value in list(getattr(fit, "face_ids", ()) or []) if str(value).strip()]
            if requested not in fit_face_ids and not any(
                face_id.endswith(f"/{requested}") or requested.endswith(f"/{face_id}") for face_id in fit_face_ids
            ):
                continue
            try:
                local_z = float(fit.vertex_z_mm) - float(min_z)
            except Exception:
                return None
            return {
                "face_id": requested,
                "matched_surface_id": str(getattr(fit, "surface_id", "") or ""),
                "matched_face_ids": fit_face_ids,
                "anchor_local_z_mm": float(local_z),
            }
        return None

    def _native_step_overlay_row_pose(self, label: str, reconstruction, insert_at: int) -> dict[str, object]:
        x_deg = float(self._step_x_rotation_deg(label))
        y_deg = float(self._step_y_rotation_deg(label))
        z_deg = float(self._step_roll_deg(label))
        rotation = self._step_rotation_matrix_from_angles(x_deg, y_deg, z_deg)
        try:
            row_tilts = tuple(float(value) for value in self._kraken_tilts_from_rotation_matrix(rotation))
        except Exception:
            row_tilts = (x_deg, y_deg, -z_deg)

        native_center_z = 0.0
        native_span_z = 0.0
        try:
            z_values = sorted(
                float(fit.vertex_z_mm)
                for fit in list(getattr(reconstruction, "surface_fits", ()) or ())
                if np.isfinite(float(fit.vertex_z_mm))
            )
            if z_values:
                native_span_z = max(float(z_values[-1] - z_values[0]), 0.0)
                native_center_z = 0.5 * native_span_z
        except Exception:
            native_center_z = 0.0
            native_span_z = 0.0

        z_station = float(sum(float(getattr(row, "thickness", 0.0) or 0.0) for row in self.rows[: int(insert_at)]))
        mesh_bounds: dict[str, object] = {}
        center_world = None
        try:
            mesh = self._transformed_imported_step_mesh_for_label(label)
            points = np.asarray(getattr(mesh, "points", np.empty((0, 3))), dtype=float)
            if points.ndim == 2 and points.shape[0] > 0 and points.shape[1] >= 3 and np.all(np.isfinite(points[:, :3])):
                bounds_min = np.min(points[:, :3], axis=0)
                bounds_max = np.max(points[:, :3], axis=0)
                center_world = 0.5 * (bounds_min + bounds_max)
                mesh_bounds = {
                    "bounds_min_world": [float(value) for value in bounds_min[:3]],
                    "bounds_max_world": [float(value) for value in bounds_max[:3]],
                    "center_world": [float(value) for value in center_world[:3]],
                    "source": "transformed_overlay_mesh_bounds",
                }
        except Exception as exc:
            mesh_bounds = {"source": "fallback_no_overlay_mesh", "error": str(exc).splitlines()[0][:220]}

        if center_world is None:
            placement_offset = np.asarray(self._step_placement_offset_xyz(label), dtype=float).reshape(3)
            axis_offset_x, axis_offset_y = self._step_axis_offset_xy(label)
            center_world = np.asarray(
                (
                    float(placement_offset[0]) - float(axis_offset_x),
                    float(placement_offset[1]) - float(axis_offset_y),
                    float(z_station) + float(native_center_z) + float(placement_offset[2]),
                ),
                dtype=float,
            )
            mesh_bounds = {
                **mesh_bounds,
                "center_world": [float(value) for value in center_world[:3]],
                "source": str(mesh_bounds.get("source", "fallback_step_offsets")),
            }

        anchor = self._step_overlay_axis_anchor(label)
        if isinstance(anchor, dict):
            anchor_match = self._native_step_anchor_local_z(reconstruction, str(anchor.get("face_id", "") or ""))
            try:
                target_point = np.asarray(anchor.get("target_point", ()), dtype=float).reshape(-1)[:3]
            except Exception:
                target_point = np.asarray([], dtype=float)
            if anchor_match is not None and target_point.size >= 3 and np.all(np.isfinite(target_point[:3])):
                anchor_local_z = float(anchor_match["anchor_local_z_mm"])
                row_decenter = (
                    float(target_point[0]),
                    float(target_point[1]),
                    float(target_point[2] - z_station - anchor_local_z),
                )
                return {
                    "row_tilts_deg": [float(value) for value in row_tilts],
                    "row_decenter_mm": [float(value) for value in row_decenter],
                    "z_station_mm": float(z_station),
                    "native_axis_center_z_mm": float(native_center_z),
                    "native_axis_span_z_mm": float(native_span_z),
                    "pose_source": "stored_step_axis_anchor_face_center",
                    "axis_anchor": dict(anchor),
                    **anchor_match,
                    **mesh_bounds,
                }

        row_decenter = (
            float(center_world[0]),
            float(center_world[1]),
            float(center_world[2] - z_station - native_center_z),
        )
        return {
            "row_tilts_deg": [float(value) for value in row_tilts],
            "row_decenter_mm": [float(value) for value in row_decenter],
            "z_station_mm": float(z_station),
            "native_axis_center_z_mm": float(native_center_z),
            "native_axis_span_z_mm": float(native_span_z),
            "pose_source": "transformed_overlay_bounds_center",
            **mesh_bounds,
        }

    @staticmethod
    def _default_live_native_glass_sequence(reconstruction) -> tuple[str, ...]:
        try:
            surface_count = len(list(reconstruction.component_rows()))
        except Exception:
            surface_count = 0
        if surface_count <= 0:
            try:
                surface_count = len(list(getattr(reconstruction, "surface_fits", ()) or ()))
            except Exception:
                surface_count = 0
        if surface_count <= 0:
            return ()
        if surface_count == 1:
            return ("AIR",)
        return tuple("BK7" for _ in range(surface_count - 1)) + ("AIR",)

    def _step_overlay_native_live_trace_plan(
        self,
        label: str,
        source_path,
        *,
        resolved_insert_at: int,
        arm_key: str,
        quiet: bool,
    ) -> dict[str, object] | None:
        try:
            probe = reconstruct_step_native_surfaces(source_path)
            material_sequence = self._default_live_native_glass_sequence(probe)
            if not material_sequence:
                return None
            reconstruction = reconstruct_step_native_surfaces(source_path, glass_sequence=material_sequence)
        except Exception as exc:
            if not quiet:
                self.append_debug(f"{label.upper()} STEP native live trace skipped: {exc}")
            return None
        if not bool(getattr(reconstruction, "trace_ready", False)):
            if not quiet:
                diagnostics = [
                    str(getattr(diagnostic, "message", "") or "")
                    for diagnostic in list(getattr(reconstruction, "diagnostics", ()) or ())
                    if str(getattr(diagnostic, "severity", "") or "").lower() == "error"
                ]
                self.append_debug(
                    f"{label.upper()} STEP native live trace not ready: "
                    + ("; ".join(diagnostics) if diagnostics else "inspect reconstruction diagnostics")
                )
            return None
        native_rows = list(reconstruction.component_rows())
        if not native_rows:
            return None
        display_label = self._step_overlay_display_label(label)
        element_name = f"Live {display_label.upper()} native STEP"
        applied_pose = self._native_step_overlay_row_pose(label, reconstruction, int(resolved_insert_at))
        row_tilts = tuple(float(value) for value in list(applied_pose.get("row_tilts_deg", (0.0, 0.0, 0.0)))[:3])
        row_decenter = tuple(float(value) for value in list(applied_pose.get("row_decenter_mm", (0.0, 0.0, 0.0)))[:3])
        row_indices = list(range(int(resolved_insert_at), int(resolved_insert_at) + len(native_rows)))
        pose_metadata = {
            "step_label": label,
            "source_step_path": str(source_path.resolve()),
            "material_sequence": list(material_sequence),
            "step_rotation_deg": [
                float(self._step_x_rotation_deg(label)),
                float(self._step_y_rotation_deg(label)),
                float(self._step_roll_deg(label)),
            ],
            "axis_offset_xy": [float(value) for value in self._step_axis_offset_xy(label)],
            "placement_offset_xyz": [float(value) for value in self._step_placement_offset_xyz(label)],
            "row_coordinates": "native_reconstructed_prescription_with_open3d_pose",
            "applied_row_pose": applied_pose,
            "trace_ready": bool(reconstruction.trace_ready),
            "transient_live_trace": True,
        }
        for offset, row in enumerate(native_rows):
            if arm_key:
                self._apply_arm_key_metadata_to_row(row, arm_key)
            row.element = element_name
            row.name = f"Live {display_label.upper()} native STEP S{offset + 1}: {row.name}"
            row.tilt_x, row.tilt_y, row.tilt_z = row_tilts
            row.desp_x, row.desp_y, row.desp_z = row_decenter
            row.axis_move = 0.0
            row.advanced = dict(row.advanced or {})
            row.advanced["StepNativePromotion"] = {
                **pose_metadata,
                "row_index_offset": int(offset),
                "row_indices": row_indices,
                "reconstruction": reconstruction.as_record() if offset == 0 else {"see_first_row": True},
            }
            row.advanced["LiveStepOverlayTrace"] = {
                "enabled": True,
                "step_label": label,
                "trace_backend": "native_analytic_rows",
                "source_step_path": str(source_path.resolve()),
                "row_indices": row_indices,
            }
            row.advanced[SCENE_PLACEMENT_ADVANCED_ATTR] = normalize_scene_placement_settings(
                {
                    "enabled": True,
                    "anchor": "row_pose",
                    "snap_enabled": True,
                    "snap_mm": max(float(row.diameter) / 20.0, 0.1),
                    "snap_deg": 5.0,
                    "grid_visible": False,
                    "grid_spacing_mm": max(float(row.diameter) / 10.0, 0.5),
                    "grid_extent_mm": max(float(row.diameter) * 2.0, 25.0),
                    "promotion_source": "open3d_step_native_live_trace",
                    "promotion_step_label": label,
                    "promotion_source_step_path": str(source_path.resolve()),
                    "promotion_row_coordinates": "native_reconstructed_prescription_with_open3d_pose",
                    "transient_live_trace": True,
                }
            )
            row.advanced["Note"] = (
                "Transient Open 3D live trace rebuilt this imported STEP as KrakenOS-native analytic rows. "
                "This avoids tracing refractive lens physics against faceted STL triangle normals. "
                "The default live material sequence uses BK7 for internal media and AIR after the last surface; "
                "promote to native rows and set exact glasses for production prescriptions."
            )
        return {
            "label": label,
            "row_index": int(resolved_insert_at),
            "row_indices": row_indices,
            "row_count": len(native_rows),
            "rows": native_rows,
            "source_step_path": str(source_path.resolve()),
            "material_sequence": material_sequence,
            "reconstruction": reconstruction,
            "applied_row_pose": applied_pose,
            "transient_live_trace": True,
            "trace_backend": "native_analytic_rows",
        }

    def _step_overlay_optical_solid_row_plan(
        self,
        label: str,
        *,
        insert_at: int | None = None,
        cache_subdir: str = "promoted_step_overlays",
        transient_live_trace: bool = False,
        use_current_selection: bool = True,
        quiet: bool = False,
    ) -> dict[str, object] | None:
        label = str(label).strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET:
            return None
        source_path = self._step_path_for_label(label)
        if source_path is None:
            if not quiet:
                self.status_var.set(f"No {label} STEP is imported.")
            return None
        mesh = self._transformed_imported_step_mesh_for_label(label)
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            if not quiet:
                self.status_var.set(f"{label.upper()} STEP mesh unavailable for optical-solid promotion.")
            return None
        try:
            mesh = mesh.extract_surface(algorithm="dataset_surface").triangulate().copy(deep=True)
        except Exception:
            try:
                mesh = mesh.extract_surface(algorithm="dataset_surface").copy(deep=True)
            except Exception:
                mesh = mesh.copy(deep=True)
        points = np.asarray(getattr(mesh, "points", np.empty((0, 3))), dtype=float)
        if points.ndim != 2 or points.shape[0] == 0 or points.shape[1] < 3 or not np.all(np.isfinite(points[:, :3])):
            if not quiet:
                self.status_var.set(f"{label.upper()} STEP promotion found no finite mesh points.")
            return None

        bounds_min = np.min(points[:, :3], axis=0)
        bounds_max = np.max(points[:, :3], axis=0)
        center_world = 0.5 * (bounds_min + bounds_max)
        extents = np.maximum(bounds_max - bounds_min, 0.0)
        local_mesh = mesh.copy(deep=True)
        local_mesh.points = points[:, :3] - center_world[:3]

        digest = hashlib.sha1()
        digest.update(str(source_path.resolve()).encode("utf-8", errors="ignore"))
        digest.update(str(label).encode("utf-8"))
        digest.update(np.ascontiguousarray(local_mesh.points, dtype=np.float64).tobytes())
        digest.update(
            repr(
                {
                    "rot_x": self._step_x_rotation_deg(label),
                    "rot_y": self._step_y_rotation_deg(label),
                    "rot_z": self._step_roll_deg(label),
                    "axis_offset_xy": None if transient_live_trace else self._step_axis_offset_xy(label),
                    "placement_offset_xyz": None if transient_live_trace else self._step_placement_offset_xyz(label),
                    "largest_component_only": bool(getattr(self, "lens_step_largest_component_only", True))
                    if label == "lens"
                    else None,
                    "transient_live_trace": bool(transient_live_trace),
                }
            ).encode("utf-8")
        )
        mesh_path = cad_cache_paths.CAD_CACHE_DIR / str(cache_subdir or "promoted_step_overlays") / f"{label}_{digest.hexdigest()[:16]}.stl"
        if not mesh_path.exists() or mesh_path.stat().st_size <= 0:
            mesh_path.parent.mkdir(parents=True, exist_ok=True)
            local_mesh.save(str(mesh_path))
        diagnostics = inspect_stl_mesh(mesh_path)

        resolved_insert_at, arm_key = self._step_overlay_insert_index(insert_at, use_current_selection=use_current_selection)
        z_station = float(sum(float(getattr(row, "thickness", 0.0) or 0.0) for row in self.rows[:resolved_insert_at]))
        if transient_live_trace:
            native_plan = self._step_overlay_native_live_trace_plan(
                label,
                source_path.resolve(),
                resolved_insert_at=int(resolved_insert_at),
                arm_key=arm_key,
                quiet=quiet,
            )
            if native_plan is not None:
                return native_plan

        row = self._optical_stl_solid_row(
            mesh_path.resolve(),
            source_path=source_path.resolve(),
            source_format="STEP",
        )
        if arm_key:
            self._apply_arm_key_metadata_to_row(row, arm_key)
        span = float(max(float(np.max(extents)), 1.0))
        axial_span = float(max(float(extents[2]) if extents.size >= 3 else 0.0, 0.0))
        axial_reserve = max(
            float(row.thickness),
            axial_span,
            float(bounds_max[2] - z_station) if np.isfinite(float(bounds_max[2] - z_station)) else 0.0,
            1.0,
        )
        display_label = self._step_overlay_display_label(label)
        row.element = f"{display_label.upper()} STEP solid"
        row.name = (
            f"Live {display_label.upper()} STEP optical solid"
            if transient_live_trace
            else f"Promoted {display_label.upper()} STEP optical solid"
        )
        row.thickness = float(axial_reserve)
        row.diameter = span
        row.tilt_x = 0.0
        row.tilt_y = 0.0
        row.tilt_z = 0.0
        row.desp_x = float(center_world[0])
        row.desp_y = float(center_world[1])
        row.desp_z = float(center_world[2] - z_station)
        row.axis_move = 0.0
        row.advanced = dict(row.advanced or {})
        row.advanced["Note"] = (
            "Transient Open 3D live-trace optical STEP overlay. The cached Solid_3d_stl mesh is "
            "not inserted in the editable table until the user promotes or accepts placement. "
            "Face metadata, material, and placement are the same row-backed contract used by "
            "promoted STEP optical solids."
            if transient_live_trace
            else "Promoted from an Open 3D imported STEP overlay. The cached Solid_3d_stl mesh is saved "
            "in local coordinates around the overlay center, while row Desp stores the scene/world "
            "center. AxisMove stays zero so the scene object's placement does not move downstream "
            "Object/Image rows; explicit output ports provide the separate follower-row workflow. "
            "Review material and CAD/STL optical face roles before relying on traced physics."
        )
        row.advanced["StepOverlayPromotion"] = {
            "step_label": label,
            "source_step_path": str(source_path.resolve()),
            "promoted_mesh_path": str(mesh_path.resolve()),
            "mesh_coordinates": "local_centered_from_open3d_overlay",
            "center_world": [float(value) for value in center_world[:3]],
            "bounds_min_world": [float(value) for value in bounds_min[:3]],
            "bounds_max_world": [float(value) for value in bounds_max[:3]],
            "row_thickness_mm": float(row.thickness),
            "axial_reserve_mm": float(axial_reserve),
            "step_rotation_deg": [
                float(self._step_x_rotation_deg(label)),
                float(self._step_y_rotation_deg(label)),
                float(self._step_roll_deg(label)),
            ],
            "axis_offset_xy": [float(value) for value in self._step_axis_offset_xy(label)],
            "placement_offset_xyz": [float(value) for value in self._step_placement_offset_xyz(label)],
            "largest_component_only": bool(getattr(self, "lens_step_largest_component_only", True))
            if label == "lens"
            else None,
            "transient_live_trace": bool(transient_live_trace),
        }
        row.advanced["LiveStepOverlayTrace"] = {
            "enabled": bool(transient_live_trace),
            "step_label": label,
            "cache_mesh_path": str(mesh_path.resolve()),
        }
        placement = normalize_scene_placement_settings(
            {
                "enabled": True,
                "anchor": "row_pose",
                "snap_enabled": True,
                "snap_mm": max(span / 20.0, 0.1),
                "snap_deg": 5.0,
                "grid_visible": not bool(transient_live_trace),
                "grid_spacing_mm": max(span / 10.0, 0.5),
                "grid_extent_mm": max(span * 2.0, 25.0),
                "promotion_source": "open3d_step_overlay",
                "promotion_step_label": label,
                "promotion_source_step_path": str(source_path.resolve()),
                "promotion_mesh_coordinates": "local_centered_from_open3d_overlay",
                "transient_live_trace": bool(transient_live_trace),
            }
        )
        row.advanced[SCENE_PLACEMENT_ADVANCED_ATTR] = placement
        return {
            "label": label,
            "row_index": int(resolved_insert_at),
            "row": row,
            "mesh_path": str(mesh_path.resolve()),
            "source_step_path": str(source_path.resolve()),
            "center_world": tuple(float(value) for value in center_world[:3]),
            "bounds_min_world": tuple(float(value) for value in bounds_min[:3]),
            "bounds_max_world": tuple(float(value) for value in bounds_max[:3]),
            "diagnostics": diagnostics,
            "transient_live_trace": bool(transient_live_trace),
        }

    def promote_imported_step_to_optical_solid_row(
        self,
        label: str,
        *,
        insert_at: int | None = None,
        open_face_editor: bool = True,
        clear_overlay: bool = False,
        refresh_open_3d: bool = True,
    ) -> dict[str, object] | None:
        label = str(label).strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET:
            return None
        source_path = self._step_path_for_label(label)
        if source_path is None:
            self.status_var.set(f"No {label} STEP is imported.")
            return None
        mesh = self._transformed_imported_step_mesh_for_label(label)
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            self.status_var.set(f"{label.upper()} STEP mesh unavailable for optical-solid promotion.")
            return None
        try:
            mesh = mesh.extract_surface(algorithm="dataset_surface").triangulate().copy(deep=True)
        except Exception:
            try:
                mesh = mesh.extract_surface(algorithm="dataset_surface").copy(deep=True)
            except Exception:
                mesh = mesh.copy(deep=True)
        points = np.asarray(getattr(mesh, "points", np.empty((0, 3))), dtype=float)
        if points.ndim != 2 or points.shape[0] == 0 or points.shape[1] < 3 or not np.all(np.isfinite(points[:, :3])):
            self.status_var.set(f"{label.upper()} STEP promotion found no finite mesh points.")
            return None
        bounds_min = np.min(points[:, :3], axis=0)
        bounds_max = np.max(points[:, :3], axis=0)
        center_world = 0.5 * (bounds_min + bounds_max)
        extents = np.maximum(bounds_max - bounds_min, 0.0)
        try:
            overlay_face_metadata = self._step_overlay_face_metadata(label)
        except Exception as exc:
            overlay_face_metadata = None
            self.append_debug(f"{label.upper()} STEP promotion could not preserve imported face metadata: {exc}")
        local_mesh = mesh.copy(deep=True)
        local_mesh.points = points[:, :3] - center_world[:3]

        digest = hashlib.sha1()
        digest.update(str(source_path.resolve()).encode("utf-8", errors="ignore"))
        digest.update(str(label).encode("utf-8"))
        digest.update(np.ascontiguousarray(local_mesh.points, dtype=np.float64).tobytes())
        digest.update(
            repr(
                {
                    "rot_x": self._step_x_rotation_deg(label),
                    "rot_y": self._step_y_rotation_deg(label),
                    "rot_z": self._step_roll_deg(label),
                    "axis_offset_xy": self._step_axis_offset_xy(label),
                    "placement_offset_xyz": self._step_placement_offset_xyz(label),
                    "largest_component_only": bool(getattr(self, "lens_step_largest_component_only", True))
                    if label == "lens"
                    else None,
                }
            ).encode("utf-8")
        )
        promoted_path = cad_cache_paths.CAD_CACHE_DIR / "promoted_step_overlays" / f"{label}_{digest.hexdigest()[:16]}.stl"
        if not promoted_path.exists() or promoted_path.stat().st_size <= 0:
            promoted_path.parent.mkdir(parents=True, exist_ok=True)
            local_mesh.save(str(promoted_path))
        diagnostics = inspect_stl_mesh(promoted_path)

        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            raise RuntimeError(f"Could not read the surface table: {exc}") from exc

        resolved_insert_at, arm_key = self._step_overlay_insert_index(insert_at)
        z_station = float(sum(float(getattr(row, "thickness", 0.0) or 0.0) for row in self.rows[:resolved_insert_at]))

        row = self._optical_stl_solid_row(
            promoted_path.resolve(),
            source_path=source_path.resolve(),
            source_format="STEP",
        )
        if arm_key:
            self._apply_arm_key_metadata_to_row(row, arm_key)
        span = float(max(float(np.max(extents)), 1.0))
        axial_span = float(max(float(extents[2]) if extents.size >= 3 else 0.0, 0.0))
        axial_reserve = max(
            float(row.thickness),
            axial_span,
            float(bounds_max[2] - z_station) if np.isfinite(float(bounds_max[2] - z_station)) else 0.0,
            1.0,
        )
        display_label = self._step_overlay_display_label(label)
        row.element = f"{display_label.upper()} STEP solid"
        row.name = f"Promoted {display_label.upper()} STEP optical solid"
        row.thickness = float(axial_reserve)
        row.diameter = span
        row.tilt_x = 0.0
        row.tilt_y = 0.0
        row.tilt_z = 0.0
        row.desp_x = float(center_world[0])
        row.desp_y = float(center_world[1])
        row.desp_z = float(center_world[2] - z_station)
        row.axis_move = 0.0
        row.advanced = dict(row.advanced or {})
        row.advanced["Note"] = (
            "Promoted from an Open 3D imported STEP overlay. The cached Solid_3d_stl mesh is saved "
            "in local coordinates around the overlay center, while row Desp stores the scene/world "
            "center. AxisMove stays zero so the scene object's placement does not move downstream "
            "Object/Image rows; explicit output ports provide the separate follower-row workflow. "
            "Review material and CAD/STL optical face roles before relying on traced physics."
        )
        row.advanced["StepOverlayPromotion"] = {
            "step_label": label,
            "source_step_path": str(source_path.resolve()),
            "promoted_mesh_path": str(promoted_path.resolve()),
            "mesh_coordinates": "local_centered_from_open3d_overlay",
            "center_world": [float(value) for value in center_world[:3]],
            "bounds_min_world": [float(value) for value in bounds_min[:3]],
            "bounds_max_world": [float(value) for value in bounds_max[:3]],
            "row_thickness_mm": float(row.thickness),
            "axial_reserve_mm": float(axial_reserve),
            "step_rotation_deg": [
                float(self._step_x_rotation_deg(label)),
                float(self._step_y_rotation_deg(label)),
                float(self._step_roll_deg(label)),
            ],
            "axis_offset_xy": [float(value) for value in self._step_axis_offset_xy(label)],
            "placement_offset_xyz": [float(value) for value in self._step_placement_offset_xyz(label)],
            "largest_component_only": bool(getattr(self, "lens_step_largest_component_only", True))
            if label == "lens"
            else None,
        }
        preserved_face_metadata = self._promoted_local_step_face_metadata(
            overlay_face_metadata,
            center_world=center_world,
            promoted_path=promoted_path.resolve(),
            source_path=source_path.resolve(),
            max_triangle_index=int(getattr(local_mesh, "n_cells", 0) or 0),
        )
        if preserved_face_metadata is not None:
            row.advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = preserved_face_metadata
            row.advanced["StepOverlayPromotion"]["preserved_face_count"] = int(
                len(list(preserved_face_metadata.get("faces", []) or []))
            )
        placement = normalize_scene_placement_settings(
            {
                "enabled": True,
                "anchor": "row_pose",
                "snap_enabled": True,
                "snap_mm": max(span / 20.0, 0.1),
                "snap_deg": 5.0,
                "grid_visible": True,
                "grid_spacing_mm": max(span / 10.0, 0.5),
                "grid_extent_mm": max(span * 2.0, 25.0),
                "promotion_source": "open3d_step_overlay",
                "promotion_step_label": label,
                "promotion_source_step_path": str(source_path.resolve()),
                "promotion_mesh_coordinates": "local_centered_from_open3d_overlay",
            }
        )
        row.advanced[SCENE_PLACEMENT_ADVANCED_ATTR] = placement

        self._begin_history_capture()
        self.rows.insert(resolved_insert_at, row)
        if clear_overlay:
            self._clear_imported_step_overlay_state(label)
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_indices([resolved_insert_at], focus_index=resolved_insert_at)
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.append_debug(
            "Promoted {label} STEP overlay to optical solid S{row}: center=({x:.6g},{y:.6g},{z:.6g}) "
            "mesh={mesh}\n{diag}".format(
                label=label.upper(),
                row=int(resolved_insert_at),
                x=float(center_world[0]),
                y=float(center_world[1]),
                z=float(center_world[2]),
                mesh=promoted_path,
                diag=format_stl_mesh_diagnostics(diagnostics),
            )
        )
        if diagnostics.errors or diagnostics.warnings:
            self.status_var.set(
                f"Promoted {label.upper()} STEP to S{resolved_insert_at}; mesh diagnostics need review "
                f"({short_stl_mesh_diagnostics(diagnostics)})."
            )
        else:
            self.status_var.set(
                f"Promoted {label.upper()} STEP to optical solid row S{resolved_insert_at}. Assign faces/material, then Update."
            )
        if refresh_open_3d:
            self._refresh_open_3d_views()
        if open_face_editor:
            self.after(120, lambda idx=resolved_insert_at: self.open_optical_solid_face_role_editor(idx))
        return {
            "label": label,
            "row_index": int(resolved_insert_at),
            "mesh_path": str(promoted_path.resolve()),
            "source_step_path": str(source_path.resolve()),
            "center_world": tuple(float(value) for value in center_world[:3]),
            "diagnostics": diagnostics,
        }

    def _cache_promoted_step_body_mesh(
        self,
        label: str,
        source_path: Path,
    ) -> str | None:
        """Save the imported overlay's mesh to the STEP STL cache.

        Returns the absolute path string (suitable for storing in a
        row's advanced dict) or ``None`` when the mesh is missing.
        Renderer reuse: see ``_iter_3d_optical_surface_meshes`` -- it
        loads this STL via ``_stl_mesh_from_path_with_world_transform``
        so the analytic-promoted lens body shows its ACTUAL STEP
        geometry instead of KrakenOS's rotationally-symmetric
        analytic mesh.
        """
        mesh = self._transformed_imported_step_mesh_for_label(label)
        if mesh is None or int(getattr(mesh, "n_points", 0) or 0) <= 0:
            return None
        try:
            mesh = mesh.extract_surface(algorithm="dataset_surface").triangulate().copy(deep=True)
        except Exception:
            try:
                mesh = mesh.extract_surface(algorithm="dataset_surface").copy(deep=True)
            except Exception:
                mesh = mesh.copy(deep=True)
        points = np.asarray(getattr(mesh, "points", np.empty((0, 3))), dtype=float)
        if points.ndim != 2 or points.shape[0] == 0 or points.shape[1] < 3:
            return None
        if not np.all(np.isfinite(points[:, :3])):
            return None
        # Centre on the body centroid so the cached STL is BODY-LOCAL.
        # The render branch then translates it by the row's desp + the
        # row's tilt, matching the analytic-row placement. This is the
        # same conventions used by the existing optical-solid path.
        bounds_min = np.min(points[:, :3], axis=0)
        bounds_max = np.max(points[:, :3], axis=0)
        center_world = 0.5 * (bounds_min + bounds_max)
        local_mesh = mesh.copy(deep=True)
        local_mesh.points = points[:, :3] - center_world[:3]
        digest = hashlib.sha1()
        digest.update(str(source_path.resolve()).encode("utf-8", errors="ignore"))
        digest.update(str(label).encode("utf-8"))
        digest.update(np.ascontiguousarray(local_mesh.points, dtype=np.float64).tobytes())
        digest.update(b"analytic-body")
        cache_dir = cad_cache_paths.CAD_CACHE_DIR / "promoted_step_overlays"
        mesh_path = cache_dir / f"{label}_analytic_{digest.hexdigest()[:16]}.stl"
        if not mesh_path.exists() or mesh_path.stat().st_size <= 0:
            mesh_path.parent.mkdir(parents=True, exist_ok=True)
            local_mesh.save(str(mesh_path))
        return str(mesh_path.resolve())

    def preview_imported_step_analytic_surfaces(
        self,
        label: str,
    ) -> dict[str, Any] | None:
        """Return the fitted analytic-surface plan without modifying the editor.

        Used by the inspector dialog before the user commits the
        promotion: show what was detected, ask for the glass sequence.
        Returns ``None`` when the overlay is missing or the auto-
        assignment heuristic can't find a clean front/back pair.
        """
        label = str(label).strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET:
            return None
        if self._step_path_for_label(label) is None:
            return None
        try:
            mesh = self._transformed_imported_step_mesh_for_label(label)
            face_md = self._step_overlay_face_metadata(label) or {}
        except Exception:
            return None
        if mesh is None or int(getattr(mesh, "n_points", 0) or 0) <= 0:
            return None
        # Pre-process: split any full-sphere face into front/back
        # hemispheres so a ball lens (one face, area = 4 pi R^2) can be
        # promoted. The splitter returns None for non-spherical faces
        # and for spherical caps that aren't anywhere near full
        # coverage (lens-cap front surfaces have area << 4 pi R^2).
        raw_faces = list(face_md.get("faces") or [])
        faces: list[dict[str, Any]] = []
        for f in raw_faces:
            split = maybe_split_full_sphere_face(mesh, f, source_axis=(0.0, 0.0, 1.0))
            if split is None:
                faces.append(f)
            else:
                faces.extend(split)
        # Some STEP files (e.g. Edmund 34754 plano-cylindrical) ship
        # with all face normals reporting the same direction. Refine
        # those from the mesh point clouds so the pair-axis optical
        # detection has reliable signals to work with.
        _refine_face_normals_from_mesh(faces, mesh)
        face_copies = [dict(f) for f in faces]
        _auto_assign_lens_face_functions(face_copies)
        transmit_faces = [
            faces[i]
            for i, f in enumerate(face_copies)
            if f.get("function") == "Transmit/Port"
        ]
        if not transmit_faces:
            return None
        # Derive the body's actual optical axis from the auto-assigned
        # transmit faces: the first face (lowest axial_pos in the
        # auto-assign sort) has its OUTWARD normal pointing UPSTREAM
        # (toward the incoming ray). So optical axis = -first_normal.
        # For most STEP files this works out to +Z, but for bodies
        # whose native frame puts the optical axis along Y or X (e.g.
        # the rectangular plano-cylindrical lens in
        # attachment/Lens/cylinder_lens_rectangle/) the actual axis
        # differs. Falling back to (0,0,1) keeps the old behaviour
        # when normals are missing.
        try:
            first_normal = np.asarray(
                transmit_faces[0].get("normal") or (0.0, 0.0, -1.0),
                dtype=float,
            ).reshape(3)
            first_normal /= max(float(np.linalg.norm(first_normal)), 1e-9)
            optical_axis = (-first_normal).tolist()
        except Exception:
            optical_axis = [0.0, 0.0, 1.0]
        fit = fit_step_overlay_analytic_surfaces(
            mesh,
            transmit_faces,
            source_axis=tuple(float(v) for v in optical_axis),
        )
        specs = list(fit.specs)
        if not specs:
            return None
        # The user provides one glass per air-or-glass region between
        # adjacent surfaces. N surfaces -> N regions, but the LAST
        # region is always AIR (the row's glass after the back face).
        # Number of user-provided glasses = N - 1 (one per interior /
        # lens-body region). For a singlet (2 surfaces) that's 1 glass;
        # for a cemented doublet (3 surfaces) that's 2 glasses.
        required_glass_count = max(len(specs) - 1, 1)
        rows_preview: list[dict[str, Any]] = []
        for index, spec in enumerate(specs):
            fit_info = spec.fit
            cylinder_rxy_ratio = 1.0
            rotation_z_deg = 0.0
            if isinstance(fit_info, SphereFit):
                rc = float(getattr(fit_info, "signed_rc", 0.0))
                kind = "sphere"
                residual = float(fit_info.residual_mm)
            elif isinstance(fit_info, ToroidFit):
                rc = float(getattr(fit_info, "signed_rc", 0.0)) or float(fit_info.radius_meridional)
                kind = "toroid" if fit_info.cylinder_rxy_ratio > 1e-6 else "cylinder"
                residual = float(fit_info.residual_mm)
                cylinder_rxy_ratio = float(fit_info.cylinder_rxy_ratio)
                rotation_z_deg = float(fit_info.rotation_z_deg)
            else:
                rc = 0.0
                kind = "plane"
                residual = float(getattr(fit_info, "residual_mm", 0.0))
            if index < len(specs) - 1:
                thickness = float(specs[index + 1].axial_position - spec.axial_position)
            else:
                thickness = 0.0
            rows_preview.append(
                {
                    "face_id": spec.face_id,
                    "kind": kind,
                    "rc_mm": rc,
                    "thickness_mm": float(max(thickness, 0.0)),
                    "diameter_mm": float(spec.diameter_mm),
                    "residual_mm": residual,
                    "cylinder_rxy_ratio": cylinder_rxy_ratio,
                    "rotation_z_deg": rotation_z_deg,
                }
            )
        return {
            "label": label,
            "row_count": len(rows_preview),
            "rows": rows_preview,
            "required_glass_count": int(required_glass_count),
            "source_step_path": str(self._step_path_for_label(label) or ""),
        }

    def promote_imported_step_to_analytic_surfaces(
        self,
        label: str,
        *,
        glass_sequence: object,
        insert_at: int | None = None,
        clear_overlay: bool = True,
        refresh_open_3d: bool = True,
        chain_exit_direction: tuple[float, float, float] | None = None,
    ) -> dict[str, Any] | None:
        """Promote a STEP overlay into analytic Standard rows fit from geometry.

        Counterpart to ``promote_imported_step_to_optical_solid_row``
        (which keeps the STL body and traces per-triangle) and
        ``promote_imported_step_to_native_surface_rows`` (which reads
        the STEP B-rep via OpenCascade). This path runs a least-
        squares sphere/plane fit on each preserved face of the
        already-loaded overlay mesh and emits analytic Standard
        surface rows so refraction uses ``Rc``/``k`` instead of the
        local triangle normal. Works on STL imports as well as STEP
        files whose B-rep can't be reconstructed.

        ``glass_sequence`` lists one material per interior region
        between fitted surfaces (a comma-separated string or list of
        names). For a singlet (2 surfaces) the sequence has one entry
        (e.g. ``"N-BK7"``); for a cemented doublet (3 surfaces)
        provide two glasses (e.g. ``"N-BAF10, N-SF10"``). The trailing
        region after the back face is always set to ``AIR``.
        """
        label = str(label).strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET:
            return None
        source_path = self._step_path_for_label(label)
        if source_path is None:
            self.status_var.set(f"No {label} STEP is imported.")
            return None
        preview = self.preview_imported_step_analytic_surfaces(label)
        if preview is None:
            raise RuntimeError(
                "Analytic STEP promotion: could not auto-detect a front/back "
                "optical pair on this overlay. Use Faces... to assign roles "
                "manually, or fall back to Promote STEP to Optical Solid Row."
            )
        rows_preview = list(preview["rows"])
        required = int(preview["required_glass_count"])
        materials = self._normalize_glass_sequence(glass_sequence)
        # Cache the imported mesh as an STL so the renderer can show
        # the body's ACTUAL geometry (rectangular for plano-cyl, etc)
        # instead of KrakenOS's rotationally-symmetric analytic mesh.
        # Stored on the first row's advanced dict as
        # ``StepAnalyticBodyStlPath`` -- the renderer (see
        # _iter_3d_optical_surface_meshes) checks for it and loads the
        # STL when present. Trace is unaffected because we never
        # write Solid_3d_stl, so the surface still uses Rc / k /
        # Cylinder_Rxy_Ratio for refraction.
        try:
            body_stl_path = self._cache_promoted_step_body_mesh(label, source_path)
        except Exception as exc:
            self.append_debug(f"Analytic body mesh cache failed for {label}: {exc}")
            body_stl_path = None
        if len(materials) < required:
            raise RuntimeError(
                f"Analytic STEP promotion: need {required} glass name(s) for the "
                f"{len(rows_preview)} fitted surface(s); got {len(materials)}. "
                "Provide one glass per region between adjacent surfaces "
                "(comma-separated). The trailing region after the back surface "
                "is always AIR."
            )
        materials = list(materials)[:required] + ["AIR"]

        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            raise RuntimeError(f"Could not read the surface table: {exc}") from exc
        resolved_insert_at, arm_key = self._step_overlay_insert_index(insert_at)
        display_label = self._step_overlay_display_label(label)
        element_name = f"{display_label.upper()} analytic STEP"
        # Carry over the overlay's pose so the rows land where the
        # body was sitting. The first analytic row owns the placement
        # offset and rotations; subsequent rows ride on its thickness.
        rotation_x = float(self._step_x_rotation_deg(label))
        rotation_y = float(self._step_y_rotation_deg(label))
        rotation_z = float(self._step_roll_deg(label))
        placement = tuple(float(v) for v in self._step_placement_offset_xyz(label))
        # The fit module reports each face's axial_position (signed
        # projection of the centroid onto the source axis = local +Z).
        # The first row needs desp_z shifted so its surface aligns with
        # the front face's axial coordinate.
        z_station = float(sum(float(getattr(row, "thickness", 0.0) or 0.0) for row in self.rows[:resolved_insert_at]))
        front_axial = float(rows_preview[0].get("axial_position_mm", 0.0)) if "axial_position_mm" in rows_preview[0] else 0.0
        # Derive the chain-frame tilt that aligns the analytic rows
        # with the upstream beam direction. If ``chain_exit_direction``
        # is supplied (e.g. the caller measured it from a live trace
        # of the cascade), translate it into Euler tilts via the same
        # cardinal-axis mapping the penta-telescope harness uses.
        # The overlay's own rotation (rotation_x/y/z) is composed on
        # TOP of the cascade tilt so a user-snapped lens still
        # behaves correctly.
        # Orient each row so its surface normal faces the incoming
        # ray. KrakenOS Standard surfaces have the surface normal
        # along local +Z; rotating the row's tilt brings that normal
        # into alignment with the cascade exit direction.
        #
        # The chain frame stays world-aligned (AxisMove=0 everywhere)
        # because rotating the chain via AxisMove=2 makes "thickness"
        # advance along the rotated axis, but our trailing rows are
        # also Standard surfaces that want their position set in
        # world coordinates -- mixing world-coord desp with
        # rotated-chain advance puts trailing rows in the wrong
        # place. Cleaner: every row carries its own world placement
        # and orientation, chain stays simple. Per-row world X
        # offsets along the exit beam are applied by the caller
        # AFTER promote returns.
        chain_tilt = (0.0, 0.0, 0.0)
        if chain_exit_direction is not None:
            try:
                axis_vec = np.asarray(chain_exit_direction, dtype=float).reshape(3)
            except Exception:
                axis_vec = None
            if axis_vec is not None and float(np.linalg.norm(axis_vec)) > 1e-9:
                axis_vec = axis_vec / float(np.linalg.norm(axis_vec))
                dominant = int(np.argmax(np.abs(axis_vec)))
                snapped = np.zeros(3, dtype=float)
                snapped[dominant] = float(np.sign(axis_vec[dominant]))
                # Map local +Z (the Standard surface's chain-z
                # forward direction) ONTO exit_direction. KrakenOS
                # places the sphere centre at vertex + Rc * (local
                # +Z), so aligning local +Z with the ray direction
                # makes Rc>0 centres land downstream of the vertex
                # (inside the body) -- a ball lens's two hemispheres
                # then share a single centre and render as a sphere.
                if np.allclose(snapped, (0.0, 0.0, 1.0)):
                    chain_tilt = (0.0, 0.0, 0.0)
                elif np.allclose(snapped, (0.0, 0.0, -1.0)):
                    chain_tilt = (180.0, 0.0, 0.0)
                elif np.allclose(snapped, (1.0, 0.0, 0.0)):
                    chain_tilt = (0.0, 90.0, 0.0)
                elif np.allclose(snapped, (-1.0, 0.0, 0.0)):
                    chain_tilt = (0.0, -90.0, 0.0)
                elif np.allclose(snapped, (0.0, 1.0, 0.0)):
                    chain_tilt = (-90.0, 0.0, 0.0)
                elif np.allclose(snapped, (0.0, -1.0, 0.0)):
                    chain_tilt = (90.0, 0.0, 0.0)
        new_rows: list[SurfaceRow] = []
        for index, row_info in enumerate(rows_preview):
            row = SurfaceRow(
                label=str(resolved_insert_at + index),
                surface="Standard",
                element=element_name,
                name=f"{display_label.upper()} analytic S{index + 1}: {row_info.get('kind', 'surface')}",
                rc=float(row_info.get("rc_mm", 0.0)),
                thickness=float(row_info.get("thickness_mm", 0.0)),
                diameter=float(row_info.get("diameter_mm", 0.0)),
                glass=str(materials[min(index, len(materials) - 1)]),
            )
            # AxisMove=0 everywhere: chain stays world-aligned, every
            # row carries its own world-frame placement and tilt.
            row.axis_move = 0.0
            # Anchor sits at the caller-provided world target; every
            # trailing row inherits the SAME world position by default.
            # The caller (e.g. build_penta_analytic_telescope_layout)
            # is responsible for shifting trailing rows along the
            # exit beam to physically separate the surfaces. This
            # default keeps standalone promote (no cascade caller)
            # rendering correctly as one collapsed lens body.
            row.desp_x = float(placement[0])
            row.desp_y = float(placement[1])
            row.desp_z = float(placement[2] - z_station)
            # Every row gets the same surface-normal orientation: the
            # overlay's own rotation composed with the chain_tilt that
            # aligns local +Z with -exit_direction (so the surface
            # faces the incoming ray). Trailing rows MUST share this
            # tilt; if they keep (0,0,0) their normals point world +Z
            # and the ray either grazes or misses.
            row.tilt_x = (rotation_x + chain_tilt[0]) % 360.0
            row.tilt_y = (rotation_y + chain_tilt[1]) % 360.0
            # For toroidal / cylindrical surfaces the tilt about the
            # optical (chain-z) axis sets the orientation of the
            # meridional (high-curvature) axis. fit_torus returned
            # this in row_info["rotation_z_deg"].
            torus_rotation_z = float(row_info.get("rotation_z_deg", 0.0) or 0.0)
            row.tilt_z = (rotation_z + chain_tilt[2] + torus_rotation_z) % 360.0
            # Encode the cylinder/torus ratio in the row's advanced
            # dict so KrakenOS's conic__surf uses the right anamorphic
            # scaling (Cylinder_Rxy_Ratio = 0 means pure plano-cyl,
            # 0<gamma<1 means torus, 1 is sphere-equivalent).
            # NB: `or 1.0` would silently treat gamma=0.0 (pure
            # plano-cyl, the most common case) as "missing -> default
            # to spherical", swallowing the cylindrical refraction.
            # Read the value EXPLICITLY and only fall back when truly
            # absent.
            raw_ratio = row_info.get("cylinder_rxy_ratio")
            cylinder_ratio = float(raw_ratio) if raw_ratio is not None else 1.0
            if arm_key:
                self._apply_arm_key_metadata_to_row(row, arm_key)
            row.advanced = dict(row.advanced or {})
            if abs(cylinder_ratio - 1.0) > 1e-6:
                row.advanced["Cylinder_Rxy_Ratio"] = cylinder_ratio
            # Renderer hook: the FIRST row of each promoted lens
            # carries a path to the cached STEP-derived body mesh.
            # Trailing rows DELIBERATELY skip the path so the body
            # is drawn once, not once per surface. Trace ignores
            # this key (only the renderer reads it).
            if body_stl_path and index == 0:
                row.advanced["StepAnalyticBodyStlPath"] = body_stl_path
            row.advanced["StepAnalyticPromotion"] = {
                "step_label": label,
                "source_step_path": str(source_path.resolve()),
                "face_id": str(row_info.get("face_id", "?")),
                "fit_kind": str(row_info.get("kind", "")),
                "fit_residual_mm": float(row_info.get("residual_mm", 0.0)),
                "glass_sequence": list(materials),
                "row_offset": int(index),
                "row_count": len(rows_preview),
            }
            new_rows.append(row)

        for offset, row in enumerate(new_rows):
            self.rows.insert(int(resolved_insert_at) + offset, row)
        self._sync_table()
        if clear_overlay:
            self._clear_imported_step_overlay_state(label)
        if refresh_open_3d:
            try:
                self._refresh_open_3d_views(step_label=label)
            except Exception:
                pass
        rc_summary = ", ".join(
            f"Rc={float(r.get('rc_mm', 0.0)):+.3g} mm" for r in rows_preview
        )
        self.status_var.set(
            f"Promoted {display_label.upper()} STEP to {len(new_rows)} analytic Standard "
            f"surface(s): {rc_summary}. Glass: {', '.join(materials)}."
        )
        return {
            "label": label,
            "row_indices": list(range(int(resolved_insert_at), int(resolved_insert_at) + len(new_rows))),
            "row_count": len(new_rows),
            "rows_preview": rows_preview,
            "materials": list(materials),
            "source_step_path": str(source_path.resolve()),
        }

    def promote_imported_step_to_native_surface_rows(
        self,
        label: str,
        *,
        glass_sequence: object,
        insert_at: int | None = None,
        clear_overlay: bool = False,
        refresh_open_3d: bool = True,
    ) -> dict[str, object] | None:
        """Promote a STEP overlay into native KrakenOS analytic surface rows."""

        label = str(label).strip().lower()
        if label not in STEP_OVERLAY_LABEL_SET:
            return None
        source_path = self._step_path_for_label(label)
        if source_path is None:
            self.status_var.set(f"No {label} STEP is imported.")
            return None
        material_sequence = self._normalize_glass_sequence(glass_sequence)
        if not material_sequence:
            raise RuntimeError("Native STEP promotion requires a comma-separated glass/material sequence.")

        # Drop unsupported (cone/etc) faces here only: vendor lens
        # STEP files often have mechanical chamfer cones at the rim
        # that we want to ignore so the optical sphere stack can be
        # recovered. Other reconstruction call sites (saved-STEP-row
        # tracing, live overlay tracing) keep the default strict
        # behavior so prism STEP files with cone/plane envelopes
        # correctly fall back to STL per-triangle tracing.
        reconstruction = reconstruct_step_native_surfaces(
            source_path,
            glass_sequence=material_sequence,
            drop_unsupported_faces=True,
        )
        if not reconstruction.trace_ready:
            errors = [
                str(diagnostic.message)
                for diagnostic in reconstruction.diagnostics
                if str(diagnostic.severity).lower() == "error"
            ]
            raise RuntimeError(
                "Native STEP reconstruction is not trace-ready: "
                + ("; ".join(errors) if errors else "inspect reconstruction diagnostics")
            )
        native_rows = reconstruction.component_rows()
        if not native_rows:
            raise RuntimeError("Native STEP reconstruction did not produce surface rows.")

        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            raise RuntimeError(f"Could not read the surface table: {exc}") from exc
        resolved_insert_at, arm_key = self._step_overlay_insert_index(insert_at)
        display_label = self._step_overlay_display_label(label)
        element_name = f"{display_label.upper()} native STEP"
        applied_pose = self._native_step_overlay_row_pose(label, reconstruction, resolved_insert_at)
        row_tilts = tuple(float(value) for value in list(applied_pose.get("row_tilts_deg", (0.0, 0.0, 0.0)))[:3])
        row_decenter = tuple(float(value) for value in list(applied_pose.get("row_decenter_mm", (0.0, 0.0, 0.0)))[:3])
        pose_metadata = {
            "step_label": label,
            "source_step_path": str(source_path.resolve()),
            "material_sequence": list(material_sequence),
            "step_rotation_deg": [
                float(self._step_x_rotation_deg(label)),
                float(self._step_y_rotation_deg(label)),
                float(self._step_roll_deg(label)),
            ],
            "axis_offset_xy": [float(value) for value in self._step_axis_offset_xy(label)],
            "placement_offset_xyz": [float(value) for value in self._step_placement_offset_xyz(label)],
            "row_coordinates": "native_reconstructed_prescription_with_open3d_pose",
            "applied_row_pose": applied_pose,
            "trace_ready": bool(reconstruction.trace_ready),
        }
        row_indices = list(range(int(resolved_insert_at), int(resolved_insert_at) + len(native_rows)))
        for offset, row in enumerate(native_rows):
            if arm_key:
                self._apply_arm_key_metadata_to_row(row, arm_key)
            row.element = element_name
            row.name = f"{display_label.upper()} native STEP S{offset + 1}: {row.name}"
            row.tilt_x, row.tilt_y, row.tilt_z = row_tilts
            row.desp_x, row.desp_y, row.desp_z = row_decenter
            row.axis_move = 0.0
            row.advanced = dict(row.advanced or {})
            row.advanced["StepNativePromotion"] = {
                **pose_metadata,
                "row_index_offset": int(offset),
                "row_indices": row_indices,
                "reconstruction": reconstruction.as_record() if offset == 0 else {"see_first_row": True},
            }
            row.advanced[SCENE_PLACEMENT_ADVANCED_ATTR] = normalize_scene_placement_settings(
                {
                    "enabled": True,
                    "anchor": "row_pose",
                    "snap_enabled": True,
                    "snap_mm": max(float(row.diameter) / 20.0, 0.1),
                    "snap_deg": 5.0,
                    "grid_visible": True,
                    "grid_spacing_mm": max(float(row.diameter) / 10.0, 0.5),
                    "grid_extent_mm": max(float(row.diameter) * 2.0, 25.0),
                    "promotion_source": "open3d_step_native_overlay",
                    "promotion_step_label": label,
                    "promotion_source_step_path": str(source_path.resolve()),
                    "promotion_row_coordinates": "native_reconstructed_prescription_with_open3d_pose",
                }
            )
            row.advanced["Note"] = (
                "Promoted from OpenCascade STEP topology into KrakenOS-native analytic rows. "
                "Geometry is reconstructed from STEP faces; glass/material sequence is user-supplied. "
                "Open 3D overlay placement/orientation is applied as row Tilt/Desp. "
                "Review fit diagnostics before treating vendor spline reconstruction as production optics."
            )
        self._begin_history_capture()
        for offset, row in enumerate(native_rows):
            self.rows.insert(resolved_insert_at + offset, row)
        if clear_overlay:
            self._clear_imported_step_overlay_state(label)
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_indices(row_indices, focus_index=row_indices[0])
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.append_debug(
            "Promoted {label} STEP overlay to native KrakenOS rows {rows}: materials={materials} "
            "tilt=({tx:.6g},{ty:.6g},{tz:.6g}) desp=({dx:.6g},{dy:.6g},{dz:.6g})".format(
                label=label.upper(),
                rows=row_indices,
                materials=", ".join(material_sequence),
                tx=float(row_tilts[0]),
                ty=float(row_tilts[1]),
                tz=float(row_tilts[2]),
                dx=float(row_decenter[0]),
                dy=float(row_decenter[1]),
                dz=float(row_decenter[2]),
            )
        )
        self.status_var.set(
            f"Promoted {label.upper()} STEP to {len(native_rows)} native analytic rows "
            f"({', '.join(material_sequence)})."
        )
        if refresh_open_3d:
            self._refresh_open_3d_views()
        return {
            "label": label,
            "row_indices": row_indices,
            "row_index": row_indices[0],
            "row_count": len(native_rows),
            "source_step_path": str(source_path.resolve()),
            "material_sequence": material_sequence,
            "reconstruction": reconstruction,
            "applied_row_pose": applied_pose,
        }
