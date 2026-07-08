"""Display-free guard for the face-bound illumination source (bugs/0264, feature B).

A user can mark a CAD/STL face as an illumination source: right-click the face in Open 3D ("Set as
Illumination Source") or the "Set as Illumination Source" button in the CAD/STL face-roles dialog. Both
create a real ``SceneSource3D`` (role="illumination", physical, enabled) whose origin sits at the face
centroid and whose direction is the OUTWARD face normal (away from the solid body), tagged with the face
anchor (``face_anchor_row`` + ``face_anchor_face_id``) so it tracks the element on later moves/rotations.
This makes the "Illum rays" overlay (phase 232) light up for a user-authored scene, closing the ergonomic
gap flagged in bugs/0263 (the overlay was robust, but the role only ever got tagged by a pre-built layout).

This guard has two parts:

* WIRING (pure source inspection, no display): the editor exposes ``create_illumination_source_at_face``
  and ``resync_face_bound_scene_sources``; ``_collect_layout_settings`` calls the resync so bound sources
  refresh before every trace/save; the right-click menu offers the item and the face-roles dialog offers
  the button.
* BINDING (real promoted-prism STEP fixture; SKIPs when the STEP is not checked out): create the source
  at a face and assert role/physical/enabled + anchor keys + origin==centroid + unit OUTWARD direction;
  re-marking the same face updates in place (no duplicate); a row move is tracked by the resync; the
  anchor keys survive ``normalize_scene_source_specs`` and the settings round-trip yields an active
  physical illumination emitter (so the rays overlay has something to draw).
"""

from __future__ import annotations

import inspect
import os
from dataclasses import asdict

import numpy as np

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")


def _check_wiring(failures: list[str]) -> None:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.layout_settings import LayoutSettingsService
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    for name in ("create_illumination_source_at_face", "resync_face_bound_scene_sources", "_outward_face_normal"):
        if not hasattr(KrakenLayoutEditor, name):
            failures.append(f"WIRING: editor is missing {name}()")

    # _collect_layout_settings lives on the settings service (the editor method delegates to it); the
    # resync must fire there, before the snapshot packs scene_sources.
    try:
        collect_src = inspect.getsource(LayoutSettingsService._collect_layout_settings)
    except Exception as exc:  # pragma: no cover - defensive
        collect_src = ""
        failures.append(f"WIRING: could not read _collect_layout_settings source ({exc!r})")
    if "resync_face_bound_scene_sources" not in collect_src:
        failures.append(
            "WIRING: _collect_layout_settings must call resync_face_bound_scene_sources so a bound "
            "source tracks its face before the trace/save snapshot packs scene_sources"
        )

    try:
        menu_src = inspect.getsource(Open3DFaceAssignmentService._show_surface_function_context_menu)
        handler_src = inspect.getsource(Open3DFaceAssignmentService._assign_row_face_illumination_from_context)
    except Exception as exc:  # pragma: no cover - defensive
        menu_src = handler_src = ""
        failures.append(f"WIRING: could not read right-click menu source ({exc!r})")
    if "Set as Illumination Source" not in menu_src:
        failures.append("WIRING: the Open 3D face right-click menu does not offer 'Set as Illumination Source'")
    if "create_illumination_source_at_face" not in handler_src:
        failures.append("WIRING: the right-click handler must call create_illumination_source_at_face")

    try:
        from KrakenOS.UI.panels import main_optical_solid_face_roles_dialog as dialog

        dialog_src = inspect.getsource(dialog)
    except Exception as exc:  # pragma: no cover - defensive
        dialog_src = ""
        failures.append(f"WIRING: could not read the face-roles dialog source ({exc!r})")
    if "Set as Illumination Source" not in dialog_src or "create_illumination_source_at_face" not in dialog_src:
        failures.append("WIRING: the CAD/STL face-roles dialog does not offer a 'Set as Illumination Source' button")


def _first_assigned_anchor(app, row_index: int) -> "tuple[str, np.ndarray]":
    from KrakenOS.UI.layout_editor import (
        OPTICAL_SOLID_FACES_ADVANCED_ATTR,
        SurfaceRow,
        optical_solid_face_world_records,
    )

    _row, _path, metadata = app._optical_solid_face_metadata_for_row(int(row_index))
    temp_row = SurfaceRow(**asdict(app.rows[int(row_index)]))
    temp_row.advanced = dict(temp_row.advanced or {})
    temp_row.advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata
    faces = optical_solid_face_world_records(temp_row, app._stl_row_z_station(int(row_index)), assigned_only=False)
    if not faces:
        raise AssertionError("promoted optical solid exposed no assignable faces")
    face_id = str(faces[0].get("face_id", "") or "").strip()
    app.assign_optical_solid_face_function(int(row_index), face_id, "Uncoated", direct_context=True)
    anchor = app._scene_source_face_anchor_record(int(row_index), face_id)
    if anchor is None:
        raise AssertionError(f"assigned face {face_id} did not become a scene-source anchor")
    centroid = np.asarray(anchor.get("anchor_world", anchor.get("centroid_world")), dtype=float).reshape(-1)[:3]
    return face_id, centroid


def _check_binding(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI import layout_editor as le
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.scene_source_analysis import normalize_scene_source_specs
    from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP
    from KrakenOS.UI.source_trace_helpers import scene_sources_from_settings

    if not PRISM_42779_STEP.exists():
        notes.append("SKIP binding: PRISM_42779_STEP fixture not checked out")
        return

    from pathlib import Path

    le.CAD_CACHE_DIR = Path("/tmp/kraken-open3d-face-illum-cache/cad")
    le.CAD_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    app = KrakenLayoutEditor(headless=True)
    try:
        app.imported_optical_step_path = PRISM_42779_STEP
        app.optical_step_rotation_x_deg = 90.0
        app.optical_step_rotation_z_deg = 90.0
        app.select_step_component("optical")
        promoted = app.promote_imported_step_to_optical_solid_row(
            "optical", insert_at=1, open_face_editor=False, clear_overlay=True
        )
        if promoted is None:
            failures.append("BINDING: could not promote the prism STEP to an optical solid row")
            return
        row_index = int(promoted["row_index"])
        face_id, centroid = _first_assigned_anchor(app, row_index)

        source_id = app.create_illumination_source_at_face(row_index, face_id=face_id)
        if not source_id:
            failures.append("BINDING: create_illumination_source_at_face returned no source id")
            return
        bound = [s for s in app.layout_scene_source_specs if str(s.get("face_anchor_face_id", "")) == face_id]
        if len(bound) != 1:
            failures.append(f"BINDING: expected exactly one bound source, got {len(bound)}")
            return
        spec = bound[0]
        if str(spec.get("role")) != "illumination":
            failures.append(f"BINDING: bound source role is {spec.get('role')!r}, not 'illumination'")
        if spec.get("physical") not in (True, 1) or spec.get("enabled") not in (True, 1):
            failures.append("BINDING: bound source must be physical + enabled")
        if int(spec.get("face_anchor_row", -1)) != row_index:
            failures.append("BINDING: bound source did not record face_anchor_row")
        origin = np.array([spec["source_x"], spec["source_y"], spec["source_z"]], dtype=float)
        direction = np.array([spec["source_l"], spec["source_m"], spec["source_n"]], dtype=float)
        if not np.allclose(origin, centroid, atol=1e-6):
            failures.append(f"BINDING: origin {origin.tolist()} is not the face centroid {centroid.tolist()}")
        if abs(float(np.linalg.norm(direction)) - 1.0) > 1e-6:
            failures.append("BINDING: direction is not a unit vector")
        body = np.asarray(app._surface_reference_world_point(row_index), dtype=float).reshape(-1)[:3]
        if float(np.dot(direction, centroid - body)) <= 0.0:
            failures.append("BINDING: direction must point OUTWARD (away from the solid body centre)")

        # Re-marking the same face updates in place; it must not pile up a duplicate.
        app.create_illumination_source_at_face(row_index, face_id=face_id)
        again = [s for s in app.layout_scene_source_specs if str(s.get("face_anchor_face_id", "")) == face_id]
        if len(again) != 1:
            failures.append(f"BINDING: re-marking the same face duplicated the source ({len(again)})")

        # A row move is tracked WITHOUT an explicit resync call: _collect_layout_settings must fire the
        # resync itself, so the stored spec origin follows the face centroid after the settings snapshot.
        app.rows[row_index].desp_y = float(app.rows[row_index].desp_y) + 10.0
        settings = app._collect_layout_settings()
        moved = [s for s in app.layout_scene_source_specs if str(s.get("face_anchor_face_id", "")) == face_id][0]
        dy = float(moved["source_y"]) - float(origin[1])
        if abs(dy - 10.0) > 1e-3:
            failures.append(f"BINDING: _collect_layout_settings did not resync a +10 Y face move (dy={dy:.4f})")

        # Anchor keys survive normalization and the settings round-trip yields an active emitter.
        if not any("face_anchor_row" in dict(x) for x in normalize_scene_source_specs(app.layout_scene_source_specs)):
            failures.append("BINDING: normalize_scene_source_specs dropped the face-anchor keys")
        sources = scene_sources_from_settings(settings, wavelength=0.55)
        emitter = [src for src in sources if str(src.settings.get("face_anchor_face_id", "")) == face_id]
        if not emitter:
            failures.append("BINDING: the bound source is absent from the trace settings round-trip")
        elif not (bool(emitter[0].physical) and bool(emitter[0].enabled) and str(emitter[0].role) == "illumination"):
            failures.append("BINDING: the round-tripped source is not an active physical illumination emitter")
        else:
            notes.append(f"binding OK: {source_id} @ {face_id} tracks the face; emits as illumination")
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_wiring(failures)
    _check_binding(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(("OK   " if passed else "NOTE ") + message)
    if not passed:
        print("[FAIL] face-bound illumination source")
        return 1
    print("[PASS] face-bound illumination source (create + track + emit)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
