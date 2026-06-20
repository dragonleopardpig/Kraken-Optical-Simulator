"""Two-arm beam-splitter display-fold architecture (production wiring).

See ``bugs/proto_two_arm_display_fold.py`` and the memory note
``two-arm-display-fold-architecture``. The user's insight ended the long non-sequential
beam-splitter fight: folding an arm INSIDE the scene forced a non-seq trace across the
splitter cube, the root of every bug (focus-before-lens seam, ray bounce, cross-arm strays,
exit-pupil detector). The right model:

  * trace each imaging arm STRAIGHT and SEQUENTIAL (optics always correct),
  * make the splitter a DISPLAY fold (bend the folded arm 90 deg at the splitter plane),
  * apply the GLASS-PLATE focus correction t(1-1/n) for the cube the beam passes through.

``build_two_arm_fold_parts`` returns the per-arm folded ``RayPath3D`` list plus a detector
``SceneTarget3D`` per arm; ``_build_scene_bundle`` overrides the bundle with them. Each arm's
straight trace runs in an isolated headless ``_snapshot_editor`` (fake Tk vars), so it is safe
to call from the live app.
"""
from __future__ import annotations

import numpy as np

from KrakenOS.UI.scene_geometry import SceneTarget3D

_CUBE_GLASS = "BK7"
_CUBE_INDEX = 1.5168  # N-BK7 near 0.55 um; t(1-1/n) ~= 0.341 t
_CUBE_THICKNESS_MM = 50.0


def fold_points(points: np.ndarray, splitter_z: float) -> np.ndarray:
    """Bend a straight polyline 90 deg +Y at the splitter (display only), continuously.

    A 45 deg splitter reflects about the TILTED plane ``z = splitter_z + y`` (not the flat
    plane ``z = splitter_z``): a ray at height y hits it at ``z = splitter_z + y``. Reflecting
    the portion past that plane -- ``(x, y, z) -> (x, z - z_s, z_s + y)`` -- is the identity ON
    the plane, so the fold is continuous. We insert the exact crossing vertex on each segment
    that straddles the plane so the ray bends right on it. Folding about the flat plane instead
    (the old behavior) left the splitter-side ends at z=z_s while the lens-side ends spread in
    z by their height, so top/bottom rays crossed -- the twist the user flagged.
    """
    pts = np.asarray(points, dtype=float)
    if pts.shape[0] < 2:
        return pts.copy()

    def _side(p):                      # > 0 on the lens side of the tilted plane
        return float(p[2] - (splitter_z + p[1]))

    def _reflect(p):                   # reflection about z = splitter_z + y
        return np.array([p[0], p[2] - splitter_z, splitter_z + p[1]], dtype=float)

    out: list = []
    prev = pts[0]
    out.append(_reflect(prev) if _side(prev) > 0.0 else prev.copy())
    for cur in pts[1:]:
        sp, sc = _side(prev), _side(cur)
        if sp * sc < 0.0:              # segment straddles the plane -> insert the crossing vertex
            cross = prev + (sp / (sp - sc)) * (cur - prev)
            out.append(cross)         # on the plane: _reflect(cross) == cross
        out.append(_reflect(cur) if sc > 0.0 else cur.copy())
        prev = cur
    return np.asarray(out, dtype=float)


def _leaf_folds(leaf_rows) -> bool:
    """A leaf's display bends iff its lens prescription is decentred off-axis.

    The shared splitter's 45 deg tilt is NOT a fold (both arms carry it); only a real
    transverse decenter of the downstream lens (the reflect arm's large desp_y/desp_z that
    positions it on the folded branch) marks the arm whose display must bend.
    """
    for row in leaf_rows:
        if abs(float(getattr(row, "desp_y", 0.0) or 0.0)) > 1.0:
            return True
        if abs(float(getattr(row, "desp_z", 0.0) or 0.0)) > 1.0:
            return True
    return False


def build_two_arm_fold_parts(leaves, settings, wavelength: float, max_radius: float):
    """Build per-arm folded ray paths + detectors for a >=2-imaging-arm splitter scene.

    ``leaves`` is ``{selector: leaf_rows}`` (from ``_imaging_branch_leaves``). Returns
    ``(ray_paths, targets)`` or ``None`` when it is not a two-arm scene / a leaf trace fails.
    """
    if not leaves or len(leaves) < 2:
        return None
    import KrakenOS as Kos
    from KrakenOS.UI.layout_editor import SurfaceRow, _build_system_from_specs
    from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
    from KrakenOS.UI.services.paraxial_tools import ParaxialToolsMixin

    ray_paths: list = []
    targets: list = []
    for selector, leaf_rows in leaves.items():
        try:
            reference, _ = ParaxialToolsMixin._paraxial_reference_rows_for_layout(
                None, leaf_rows, unfold_branch_tilts=True
            )
            ref_rows = [
                SurfaceRow(**{f.name: getattr(r, f.name) for f in r.__dataclass_fields__.values()})
                for r in reference
            ]
            fold = _leaf_folds(leaf_rows)
            splitter_z = float(ref_rows[0].thickness)  # object -> splitter (the shared path)
            # GLASS-PLATE CORRECTION: the splitter is a glass cube, not air. Trace the reference
            # THROUGH the cube glass (split its air plate into [glass cube] + [residual air gap]);
            # it pushes the focus further by t(1-1/n) so the detector lands at the real image.
            bs_index = 1  # object, splitter, lens, ...
            original_thickness = float(ref_rows[bs_index].thickness)
            glass_shift = 0.0
            if original_thickness > _CUBE_THICKNESS_MM:
                ref_rows[bs_index].thickness = _CUBE_THICKNESS_MM
                ref_rows[bs_index].glass = _CUBE_GLASS
                ref_rows.insert(bs_index + 1, SurfaceRow(
                    surface="Standard", name="bs_air_gap",
                    thickness=original_thickness - _CUBE_THICKNESS_MM,
                    diameter=float(ref_rows[bs_index].diameter), glass="AIR"))
                glass_shift = _CUBE_THICKNESS_MM * (1.0 - 1.0 / _CUBE_INDEX)
                # IMAGE-AT-FOCUS (cf. bug 0093): the cube pushes the real focus +glass_shift PAST
                # the prescription image, so the traced rays terminate ~glass_shift short of the
                # detector ("Sensor and image plane detached"). Extend the IMAGE's preceding gap
                # so the IMAGE row -- and the rays -- land ON the real focus = the detector.
                if len(ref_rows) >= 2:
                    ref_rows[-2].thickness = float(ref_rows[-2].thickness) + glass_shift

            cfg = dict(settings)
            cfg["trace_mode"] = "Sequential"
            editor = _snapshot_editor(ref_rows, cfg)
            editor.branch_detector_camera_assignments = {}
            system = _build_system_from_specs(editor._serializable_row_specs(), build=0)
            rays = Kos.raykeeper(system)
            leaf_radius = max(float(r.diameter) for r in ref_rows) / 2.0
            editor._trace_preview_rays(system, rays, wavelength, leaf_radius)
            bundle = editor._build_scene_bundle(system, rays, leaf_radius)
        except Exception as exc:  # surfaced + logged + degraded gracefully by _two_arm_fold_parts
            raise RuntimeError(f"two-arm leaf '{selector}' trace failed: {exc}") from exc

        for path in (getattr(bundle, "ray_paths", []) or []):
            pts = np.asarray(getattr(path, "points_world", np.empty((0, 3))), dtype=float)
            if pts.shape[0] < 2:
                continue
            if fold:
                path.points_world = fold_points(pts, splitter_z)
            path.branch_path = f"twoarm/{selector}"
            path.reaches_image = True
            ray_paths.append(path)

        image_z = sum(float(r.thickness) for r in ref_rows[:-1])  # gap already extended by glass_shift
        # Per-arm quick-estimation inputs (the leaf editor still holds THIS arm's straight,
        # sequential state): its paraxial magnification + real-image-circle radius. The
        # detector-coverage / object-FOV overlay otherwise reads the WHOLE folded scene --
        # magnification is None (so no object FOV is drawn) and the image plane is the scene's
        # last row, not this arm's folded detector.
        try:
            arm_magnification = editor._current_finite_paraxial_magnification()
        except Exception:
            arm_magnification = None
        try:
            arm_image_circle = float(editor._field_metrics_summary().get("max_real_image_height"))
        except Exception:
            arm_image_circle = None
        if fold:
            center = np.array([0.0, image_z - splitter_z, splitter_z], dtype=float)
            normal = np.array([0.0, 1.0, 0.0], dtype=float)
        else:
            center = np.array([0.0, 0.0, image_z], dtype=float)
            normal = np.array([0.0, 0.0, 1.0], dtype=float)
        targets.append(SceneTarget3D(
            target_id=f"twoarm_{selector}", name=f"{selector} detector", role="detector",
            is_detector=True, is_active_target=True,
            center_world=center, normal_world=normal, tangent_world=np.array([1.0, 0.0, 0.0]),
            diameter=2.0 * max_radius, active_width_mm=2.0 * max_radius, active_height_mm=2.0 * max_radius,
            metadata={
                "two_arm_selector": selector,
                "two_arm_magnification": None if arm_magnification is None else float(arm_magnification),
                "two_arm_image_circle_radius": arm_image_circle,
            }))

    if not ray_paths:
        return None
    return ray_paths, targets
