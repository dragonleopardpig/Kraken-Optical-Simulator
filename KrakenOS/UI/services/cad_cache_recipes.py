"""bugs/0810 -- a cache is a recipe.

A promoted optical solid's body mesh and a generated beam-splitter template are CACHES under
``attachment/cad_cache``: derived files, synced by Filen, and deleted by it. On this machine 23 of them
were gone -- 132 references across 15 saved scenes -- and the load path could rebuild only one kind
(bugs/0021: a file-backed solid re-meshed from its source STEP). The rest either:

* opened the missing-assets dialog, which is MODAL, so any run without a person hung forever
  (penta phases 449-452, the gate's "hangs"), or
* were neutralised at system build, so an RA-mirror scene lost its mirror and "0 rays folded"
  (phases 181-194), or
* would have been rebuilt WRONG: bugs/0021 re-meshes ``OpticalSolidSourcePath`` in the STEP's native
  frame, but an overlay-promoted body was baked in the overlay's rotated frame.

The scene already records what built each one:

* a beam-splitter template is ``bs_<kind>_<sha1(kind|params)>.step`` and the row carries
  ``beam_splitter_params`` -- the file name itself verifies the recipe;
* an overlay-promoted body is the source STEP through the optical overlay pose
  (``StepOverlayPromotion.step_rotation_deg``), surface-cleaned and centred -- and when the overlay had
  been resized, ``bounds_min_world`` / ``bounds_max_world`` carry the result;
* ``OpticalSolidFaces`` records every face's triangle indices with its area-weighted centroid, area
  and summed normal, in the mesh's own coordinates.

That last record is the proof. A rebuilt mesh is accepted only if every recorded face comes out of
its own triangles again (measured on the originals: centroid 2e-6 mm, area 4e-6 relative, normal
exact). A rebuild that does not reproduce the faces is refused and the row keeps its placeholder --
never a plausible body with the optical roles on the wrong triangles.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np

CENTROID_TOL_MM = 1e-3
AREA_TOL_REL = 1e-4
NORMAL_TOL = 1e-6
_TEMPLATE_NAME = re.compile(r"^bs_(cube|plate)_([0-9a-f]{16})\.step$", re.IGNORECASE)


def _project_path(value: Any) -> "Path | None":
    text = str(value or "").strip()
    if not text or text == "None":
        return None
    try:
        from KrakenOS.UI.layout_editor import _resolve_project_file_path

        return _resolve_project_file_path(text)
    except Exception:
        return Path(text).expanduser()


def _find_key(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for value in obj.values():
            found = _find_key(value, key)
            if found is not None:
                return found
    return None


# ---------------------------------------------------------------------------------------------------
# The proof: the recorded faces
# ---------------------------------------------------------------------------------------------------

def face_table_mismatch(mesh, advanced: dict) -> "tuple[int, str | None]":
    """``(faces_checked, problem)``: does ``mesh`` reproduce the row's ``OpticalSolidFaces``?

    ``problem`` is None when every face with triangle indices matches its recorded centroid, area and
    normal. ``faces_checked`` 0 means there was nothing to check against.
    """
    faces = ((advanced or {}).get("OpticalSolidFaces") or {}).get("faces") or []
    try:
        cells = np.asarray(mesh.faces).reshape(-1, 4)
        if not bool(np.all(cells[:, 0] == 3)):
            return 0, "the mesh is not all triangles"
        triangles = cells[:, 1:]
        points = np.asarray(mesh.points, dtype=float)
    except Exception as exc:
        return 0, f"the mesh cannot be read as triangles ({exc})"
    checked = 0
    for face in faces:
        indices = face.get("triangle_indices") or []
        if not indices:
            continue
        name = face.get("face_id") or f"face {checked}"
        if max(indices) >= len(triangles) or min(indices) < 0:
            return checked, f"{name} indexes triangle {max(indices)} of {len(triangles)}"
        corners = points[triangles[indices]]
        cross = np.cross(corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0])
        areas = 0.5 * np.linalg.norm(cross, axis=1)
        area = float(areas.sum())
        if area <= 0.0:
            return checked, f"{name} has no area"
        centroid = (corners.mean(axis=1) * areas[:, None]).sum(axis=0) / area
        normal = cross.sum(axis=0)
        normal = normal / (float(np.linalg.norm(normal)) or 1.0)
        try:
            want_centroid = np.asarray(face["centroid"], dtype=float).reshape(3)
            want_area = float(face["area_mm2"])
            want_normal = np.asarray(face["normal"], dtype=float).reshape(3)
        except (KeyError, TypeError, ValueError):
            continue
        if float(np.linalg.norm(centroid - want_centroid)) > CENTROID_TOL_MM:
            return checked, (f"{name} centroid {np.round(centroid, 4).tolist()} != recorded "
                             f"{np.round(want_centroid, 4).tolist()}")
        if abs(area - want_area) > AREA_TOL_REL * max(want_area, 1e-9):
            return checked, f"{name} area {area:.6g} != recorded {want_area:.6g}"
        if 1.0 - abs(float(np.dot(normal, want_normal))) > NORMAL_TOL:
            return checked, f"{name} normal {np.round(normal, 5).tolist()} != recorded {np.round(want_normal, 5).tolist()}"
        checked += 1
    return checked, None


# ---------------------------------------------------------------------------------------------------
# Beam-splitter templates
# ---------------------------------------------------------------------------------------------------

def rebuild_beam_splitter_template(path: Path, advanced: dict) -> "tuple[bool, str]":
    """Regenerate a missing ``bs_<kind>_<digest>.step`` from the row's ``beam_splitter_params``.

    The digest in the NAME is sha1(kind + params): the recorded parameters are accepted only if they
    hash to the file the scene asks for, so a stale or edited parameter set can never stand in.
    """
    from KrakenOS.UI.services import beam_splitter_factory as bsf

    path = Path(path)
    match = _TEMPLATE_NAME.match(path.name)
    if match is None:
        return False, f"{path.name} is not a beam-splitter template name"
    kind = match.group(1).lower()
    raw = _find_key(advanced, "beam_splitter_params")
    if not isinstance(raw, dict):
        return False, f"{path.name}: the row records no beam_splitter_params"
    try:
        if kind == "cube":
            params = bsf._normalize_cube_params(raw["side_mm"])
        else:
            params = bsf._normalize_plate_params(
                raw["width_mm"], raw["height_mm"], raw["thickness_mm"], raw.get("tilt_deg", 45.0))
    except Exception as exc:
        return False, f"{path.name}: beam_splitter_params do not describe a {kind} ({exc})"
    if bsf.beam_splitter_cache_path(kind, params).name != path.name:
        return False, f"{path.name}: the recorded parameters hash to a different template"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        bsf._write_shape_step(bsf._build_shape(kind, params), path)
    except Exception as exc:
        return False, f"{path.name}: the template could not be built ({type(exc).__name__}: {exc})"
    return True, f"rebuilt {path.name} from its recorded {kind} parameters"


# ---------------------------------------------------------------------------------------------------
# Overlay-promoted bodies
# ---------------------------------------------------------------------------------------------------

def is_overlay_promoted_body(advanced: dict) -> bool:
    promotion = (advanced or {}).get("StepOverlayPromotion")
    return isinstance(promotion, dict) and str(promotion.get("mesh_coordinates", "")).startswith(
        "local_centered_from_open3d_overlay")


def rebuild_overlay_promoted_body(editor, advanced: dict, target: Path) -> "tuple[bool, str]":
    """Regenerate a missing overlay-promoted body STL at ``target`` from the recorded recipe.

    Recipe = ``step_overlay_promotion.promote_imported_step_to_optical_solid_row``: the source STEP
    through the overlay pose (source axis z, front face min, x -> y -> roll rotations), surface-cleaned
    and centred on its bounding box. A resize applied before promotion is not recorded as a spec, but
    its result is -- ``bounds_*_world`` -- and scaling to it is accepted only if the faces then match.
    """
    from KrakenOS.UI.services.step_overlay_promotion import _clean_surface_triangulate

    target = Path(target)
    promotion = (advanced or {}).get("StepOverlayPromotion") or {}
    source = _project_path(promotion.get("source_step_path") or advanced.get("OpticalSolidSourcePath"))
    if source is None:
        return False, f"{target.name}: the promotion records no source STEP"
    if not source.exists() and _TEMPLATE_NAME.match(source.name):
        built, note = rebuild_beam_splitter_template(source, advanced)
        if not built:
            return False, f"{target.name}: its source template is missing and {note}"
    if not source.exists():
        return False, f"{target.name}: source STEP {source} is missing"
    try:
        rx, ry, rz = (float(v) for v in (promotion.get("step_rotation_deg") or (0.0, 0.0, 0.0))[:3])
    except (TypeError, ValueError):
        return False, f"{target.name}: step_rotation_deg is unreadable"
    largest = bool(promotion.get("largest_component_only")) if promotion.get("step_label") == "lens" else False
    try:
        mesh = editor._load_step_mesh(source, largest_component=largest, allow_slow_import=True)
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            return False, f"{target.name}: {source.name} produced no mesh"
        aligned = editor._cad_mesh_aligned_to_optical_axis(
            mesh, source_axis="z", front_face="min", target_front_z=0.0, label="bugs/0810 rebuild",
            roll_deg=rz, x_rotation_deg=rx, y_rotation_deg=ry)
        body = _clean_surface_triangulate(aligned)
    except Exception as exc:
        return False, f"{target.name}: rebuilding from {source.name} raised {type(exc).__name__}: {exc}"
    points = np.asarray(body.points, dtype=float)
    lo, hi = points.min(axis=0), points.max(axis=0)
    body.points = points - 0.5 * (lo + hi)
    candidates = [("as posed", body)]
    try:
        want = (np.asarray(promotion["bounds_max_world"], dtype=float)
                - np.asarray(promotion["bounds_min_world"], dtype=float)).reshape(3)
        have = hi - lo
        if np.all(have > 1e-9) and np.all(want > 1e-9) and not np.allclose(want, have, rtol=1e-6, atol=1e-6):
            resized = body.copy(deep=True)
            resized.points = np.asarray(body.points, dtype=float) * (want / have)
            candidates.append((f"resized to the recorded {np.round(want, 4).tolist()} mm", resized))
    except (KeyError, TypeError, ValueError):
        want = None
    problems = []
    for how, candidate in candidates:
        checked, problem = face_table_mismatch(candidate, advanced)
        if checked == 0 and problem is None:
            # nothing to prove it with: the recorded extents are the only evidence left
            extents = np.ptp(np.asarray(candidate.points, dtype=float), axis=0)
            if want is None or not np.allclose(extents, want, rtol=1e-4, atol=1e-3):
                problems.append(f"{how}: no face table, and extents {np.round(extents, 4).tolist()} "
                                f"do not match the recorded bounds")
                continue
        elif problem is not None:
            problems.append(f"{how}: {problem}")
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            candidate.save(str(target))
        except Exception as exc:
            return False, f"{target.name}: could not be written ({type(exc).__name__}: {exc})"
        return True, (f"rebuilt {target.name} from {source.name} {how}; "
                      f"{checked} recorded face(s) reproduced")
    return False, f"{target.name}: refused -- " + "; ".join(problems)
