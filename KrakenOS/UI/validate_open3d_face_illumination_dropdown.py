"""Display-free guard for the Face Editor "Illumination Source" dropdown value (bugs/0268).

A user marked a CAD/STL face as an illumination source but the Face Editor still showed the face as
"Absorbing" and offered no "Illumination Source" option in its function dropdown -- the illumination
SceneSource3D and the face optical-function metadata are two disjoint systems that never talked. This
bridges them: "Illumination Source" is a UI-ONLY sentinel added to the function dropdown. Selecting it
binds a face illumination source (NOT a coating -- it is intercepted before the coating apply, which would
otherwise reset the face to Unassigned); selecting a real coating while a marker is bound unbinds it; and
the dropdown preselects "Illumination Source" when a marker is already bound (instead of the underlying
coating). The sentinel is absent from the internal VALUES + the UI<->internal maps, so it normalizes to the
default if it ever reaches persistence.

Three display-free parts:

* METADATA -- the sentinel is in OPTICAL_SOLID_FACE_FUNCTION_UI_VALUES (so the combobox + parse_form accept
  it) but NOT in the internal VALUES / UI<->internal maps, and normalize_optical_solid_face_function() maps
  it to the default.
* WIRING (source inspection) -- the editor exposes face_bound_illumination_source_id + unbind; the Face
  Editor references the sentinel + binds via create_illumination_source_at_face + unbinds on change-away +
  preselects a bound marker.
* BEHAVIOUR (headless, STEP-free hand-built specs, always runs) -- the reverse-lookup finds a bound marker
  (and only for the exact row+face), unbind removes it (leaving other sources intact) and is idempotent.
"""

from __future__ import annotations

import inspect
import os

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")


def _marker_spec(row_index: int, face_id: str, source_id: str = "illum:test") -> dict:
    return {
        "source_id": source_id,
        "name": f"Illumination @ R{row_index} {face_id}",
        "source_model": "Collimated disk source",
        "role": "illumination",
        "physical": True,
        "enabled": True,
        "source_x": 0.0, "source_y": 0.0, "source_z": 0.0,
        "source_l": 0.0, "source_m": 0.0, "source_n": 1.0,
        "radius": 2.0, "ray_count": 200,
        "face_anchor_row": int(row_index),
        "face_anchor_face_id": str(face_id),
    }


def _deliberate_spec() -> dict:
    return {
        "source_id": "source:deliberate", "name": "Deliberate emitter",
        "source_model": "Collimated disk source", "physical": True, "enabled": True,
        "source_x": 0.0, "source_y": 0.0, "source_z": -60.0,
        "source_l": 0.0, "source_m": 0.0, "source_n": 1.0,
        "radius": 6.0, "ray_count": 12,
    }


def _check_metadata(failures: list[str]) -> None:
    from KrakenOS.UI import optical_solid_metadata as M

    label = M.OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_ILLUMINATION
    if label not in M.OPTICAL_SOLID_FACE_FUNCTION_UI_VALUES:
        failures.append("METADATA: 'Illumination Source' is not in OPTICAL_SOLID_FACE_FUNCTION_UI_VALUES (dropdown)")
    if label in M.OPTICAL_SOLID_FACE_FUNCTION_VALUES:
        failures.append("METADATA: the sentinel must NOT be an internal coating token")
    if label in M.OPTICAL_SOLID_FACE_FUNCTION_UI_TO_INTERNAL or label in M.OPTICAL_SOLID_FACE_FUNCTION_INTERNAL_TO_UI:
        failures.append("METADATA: the sentinel must NOT be in the UI<->internal maps")
    if M.normalize_optical_solid_face_function(label) != M.OPTICAL_SOLID_FACE_FUNCTION_DEFAULT:
        failures.append("METADATA: the sentinel must normalize to the default function if it leaks to persistence")
    # It must reach the actual combobox values (the aliased tuple the dialog uses).
    from KrakenOS.UI.services import optical_solid_geometry as G
    if label not in G.OPTICAL_SOLID_FACE_FUNCTION_VALUES:
        failures.append("METADATA: the sentinel did not propagate to the Face Editor combobox values alias")


def _check_wiring(failures: list[str]) -> None:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.panels import main_optical_solid_face_roles_dialog as dialog

    for name in ("face_bound_illumination_source_id", "unbind_face_illumination_source", "create_illumination_source_at_face"):
        if not hasattr(KrakenLayoutEditor, name):
            failures.append(f"WIRING: editor is missing {name}()")

    try:
        dialog_src = inspect.getsource(dialog)
    except Exception as exc:  # pragma: no cover - defensive
        dialog_src = ""
        failures.append(f"WIRING: could not read the Face Editor dialog source ({exc!r})")
    for token, why in (
        ("OPTICAL_SOLID_FACE_FUNCTION_UI_LABEL_ILLUMINATION", "reference the sentinel"),
        ("create_illumination_source_at_face", "bind on selecting Illumination Source"),
        ("unbind_face_illumination_source", "unbind on change-away"),
        ("face_bound_illumination_source_id", "preselect / detect a bound marker"),
    ):
        if token not in dialog_src:
            failures.append(f"WIRING: the Face Editor dialog must {why} (missing {token!r})")


def _check_behaviour(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor(headless=True)
    try:
        app.layout_scene_source_specs = [
            _marker_spec(1, "S001/F002", "illum:a"),
            _deliberate_spec(),
        ]
        # Reverse-lookup finds the marker for the exact (row, face) only.
        sid = app.face_bound_illumination_source_id(1, "S001/F002")
        if not sid:
            failures.append("BEHAVIOUR: face_bound_illumination_source_id did not find the bound marker")
        if app.face_bound_illumination_source_id(1, "S001/F999") is not None:
            failures.append("BEHAVIOUR: reverse-lookup matched a different face_id")
        if app.face_bound_illumination_source_id(2, "S001/F002") is not None:
            failures.append("BEHAVIOUR: reverse-lookup matched a different row")

        # Unbind removes the marker but leaves the deliberate source intact.
        if not app.unbind_face_illumination_source(1, "S001/F002"):
            failures.append("BEHAVIOUR: unbind_face_illumination_source returned False for a bound face")
        if app.face_bound_illumination_source_id(1, "S001/F002") is not None:
            failures.append("BEHAVIOUR: the marker was still bound after unbind")
        if not any(str(s.get("source_id", "")) == "source:deliberate" for s in app.layout_scene_source_specs):
            failures.append("BEHAVIOUR: unbind removed the deliberate source too (it must only drop the marker)")

        # Idempotent: unbinding again removes nothing.
        if app.unbind_face_illumination_source(1, "S001/F002"):
            failures.append("BEHAVIOUR: unbind on an already-unbound face must return False")

        if not failures:
            notes.append("behaviour OK: reverse-lookup exact-match, unbind drops only the marker + is idempotent")
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
    _check_behaviour(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(("OK   " if passed else "NOTE ") + message)
    if not passed:
        print("[FAIL] Face Editor illumination-source dropdown")
        return 1
    print("[PASS] the Face Editor exposes + reflects the Illumination Source role")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
