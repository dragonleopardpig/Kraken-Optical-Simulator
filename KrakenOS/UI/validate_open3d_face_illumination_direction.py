"""Display-free guard for the illumination-source AIM direction (bugs/0269).

A face-bound illumination source used to always flood OUTWARD (away from the solid body centre, bugs/0264),
so marking a beam-splitter face aimed the emission into empty space instead of INTO the cube. bugs/0269 adds
a stored aim: "Illumination Source (into solid)" (the DEFAULT -- the coupling case, e.g. lighting into a BS
cube so it folds down to the FOV) and "Illumination Source (outward)". ``create_illumination_source_at_face``
records ``face_anchor_aim`` and computes the normal with ``_face_aimed_normal``; ``resync_face_bound_scene_sources``
respects it (so the resync never re-forces outward); and the Face Editor exposes both dropdown variants,
preselects the bound aim, and shows the role in the left-table Function column.

Three display-free parts:

* METADATA -- both aim variants are in OPTICAL_SOLID_FACE_FUNCTION_UI_VALUES + the combobox alias, and the
  outward variant (like the inward one) is NOT an internal coating token and normalizes to the default.
* WIRING (source inspection) -- the editor exposes _face_aimed_normal + face_bound_illumination_aim + an
  ``aim`` param on create; resync consults face_anchor_aim; the dialog handles both variants, preselects the
  aim, and the tree function column reflects a bound marker.
* BINDING (real promoted-prism STEP fixture; SKIPs when the STEP is not checked out) -- inward aims the
  emission INTO the body, outward aims it away, the aim is stored + reported, and a resync preserves it.
"""

from __future__ import annotations

import inspect
import os
from dataclasses import asdict
from pathlib import Path

import numpy as np

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")


def _check_metadata(failures: list[str]) -> None:
    from KrakenOS.UI import optical_solid_metadata as M
    from KrakenOS.UI.services import optical_solid_geometry as G

    inward = M.OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_ILLUMINATION
    outward = M.OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_ILLUMINATION_OUTWARD
    if inward == outward:
        failures.append("METADATA: the inward and outward illumination labels must differ")
    for label, name in ((inward, "into-solid"), (outward, "outward")):
        if label not in M.OPTICAL_SOLID_FACE_FUNCTION_UI_VALUES:
            failures.append(f"METADATA: the {name} illumination label is not in the dropdown UI values")
        if label not in G.OPTICAL_SOLID_FACE_FUNCTION_VALUES:
            failures.append(f"METADATA: the {name} illumination label did not propagate to the combobox alias")
        if label in M.OPTICAL_SOLID_FACE_FUNCTION_VALUES or label in M.OPTICAL_SOLID_FACE_FUNCTION_UI_TO_INTERNAL:
            failures.append(f"METADATA: the {name} illumination label must NOT be an internal coating token")
        if M.normalize_optical_solid_face_function(label) != M.OPTICAL_SOLID_FACE_FUNCTION_DEFAULT:
            failures.append(f"METADATA: the {name} illumination label must normalize to the default if persisted")


def _check_wiring(failures: list[str]) -> None:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.source_modeling import SourceModelingMixin
    from KrakenOS.UI.panels import main_optical_solid_face_roles_dialog as dialog

    for name in ("_face_aimed_normal", "face_bound_illumination_aim"):
        if not hasattr(KrakenLayoutEditor, name):
            failures.append(f"WIRING: editor is missing {name}()")

    try:
        create_src = inspect.getsource(SourceModelingMixin.create_illumination_source_at_face)
        resync_src = inspect.getsource(SourceModelingMixin.resync_face_bound_scene_sources)
        aimed_src = inspect.getsource(SourceModelingMixin._face_aimed_normal)
    except Exception as exc:  # pragma: no cover - defensive
        create_src = resync_src = aimed_src = ""
        failures.append(f"WIRING: could not read source_modeling source ({exc!r})")
    if "aim" not in create_src or "face_anchor_aim" not in create_src:
        failures.append("WIRING: create_illumination_source_at_face must take an aim + store face_anchor_aim")
    if "face_anchor_aim" not in resync_src or "_face_aimed_normal" not in resync_src:
        failures.append("WIRING: resync_face_bound_scene_sources must respect face_anchor_aim via _face_aimed_normal")
    if "outward" not in aimed_src:
        failures.append("WIRING: _face_aimed_normal must branch on the outward aim")

    try:
        dialog_src = inspect.getsource(dialog)
    except Exception as exc:  # pragma: no cover - defensive
        dialog_src = ""
        failures.append(f"WIRING: could not read the Face Editor dialog source ({exc!r})")
    for token, why in (
        ("OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_ILLUMINATION_OUTWARD", "offer the outward variant"),
        ("face_bound_illumination_aim", "preselect + reflect the aim (combobox + tree)"),
        ("aim=aim", "bind with the chosen aim"),
    ):
        if token not in dialog_src:
            failures.append(f"WIRING: the Face Editor dialog must {why} (missing {token!r})")


def _check_binding(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI import layout_editor as le
    from KrakenOS.UI.layout_editor import (
        KrakenLayoutEditor,
        OPTICAL_SOLID_FACES_ADVANCED_ATTR,
        SurfaceRow,
        optical_solid_face_world_records,
    )
    from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP

    if not PRISM_42779_STEP.exists():
        notes.append("SKIP binding: PRISM_42779_STEP fixture not checked out")
        return

    le.CAD_CACHE_DIR = Path("/tmp/kraken-open3d-illum-direction-cache/cad")
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
            failures.append("BINDING: could not promote the prism STEP")
            return
        row = int(promoted["row_index"])
        _r, _p, md = app._optical_solid_face_metadata_for_row(row)
        tr = SurfaceRow(**asdict(app.rows[row]))
        tr.advanced = dict(tr.advanced or {})
        tr.advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = md
        faces = optical_solid_face_world_records(tr, app._stl_row_z_station(row), assigned_only=False)
        if not faces:
            failures.append("BINDING: promoted solid exposed no faces")
            return
        fid = str(faces[0]["face_id"])
        app.assign_optical_solid_face_function(row, fid, "Uncoated", direct_context=True)
        body = np.asarray(app._surface_reference_world_point(row), dtype=float).reshape(-1)[:3]

        def _dir_dot_outward() -> float:
            spec = [s for s in app.layout_scene_source_specs if str(s.get("face_anchor_face_id", "")) == fid][0]
            origin = np.array([spec["source_x"], spec["source_y"], spec["source_z"]], dtype=float)
            direction = np.array([spec["source_l"], spec["source_m"], spec["source_n"]], dtype=float)
            return float(np.dot(direction, origin - body))

        # Inward (the default): the emission points INTO the body (toward the centre).
        app.create_illumination_source_at_face(row, face_id=fid, aim="inward")
        if _dir_dot_outward() >= 0.0:
            failures.append("BINDING: aim='inward' did not point the emission INTO the solid body")
        if app.face_bound_illumination_aim(row, fid) != "inward":
            failures.append("BINDING: face_bound_illumination_aim did not report 'inward'")
        # A resync must PRESERVE inward (never re-force outward).
        app.resync_face_bound_scene_sources()
        if _dir_dot_outward() >= 0.0:
            failures.append("BINDING: resync re-forced the emission OUTWARD (it must respect the stored aim)")

        # Outward: away from the body.
        app.create_illumination_source_at_face(row, face_id=fid, aim="outward")
        if _dir_dot_outward() <= 0.0:
            failures.append("BINDING: aim='outward' did not point the emission away from the body")
        if app.face_bound_illumination_aim(row, fid) != "outward":
            failures.append("BINDING: face_bound_illumination_aim did not report 'outward'")
        app.resync_face_bound_scene_sources()
        if _dir_dot_outward() <= 0.0:
            failures.append("BINDING: resync did not preserve the outward aim")

        # The DEFAULT (no aim arg) is inward.
        app.unbind_face_illumination_source(row, fid)
        app.create_illumination_source_at_face(row, face_id=fid)
        if app.face_bound_illumination_aim(row, fid) != "inward":
            failures.append("BINDING: the default aim must be 'inward' (into the solid)")

        if not failures:
            notes.append("binding OK: inward aims into the body, outward away, aim stored + preserved by resync, default inward")
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_metadata(failures)
    _check_wiring(failures)
    _check_binding(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(("OK   " if passed else "NOTE ") + message)
    if not passed:
        print("[FAIL] illumination-source aim direction")
        return 1
    print("[PASS] a marked face illuminates into the solid (aim inward default) or outward, and it sticks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
