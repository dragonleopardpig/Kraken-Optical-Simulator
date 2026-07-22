"""Guard: Replace a promoted optical solid IN PLACE (bugs/0404).

Right-click a promoted optical solid (e.g. an RA fold mirror) -> "Replace STEP..." swaps its geometry
for a newly chosen STEP file AT THE SAME scene pose (the overlay pose is preserved, like Swap Imaging
Lens), and re-applies the old solid's AUTHORED face functions (Mirror, TIR, ...) onto the matching
faces of the replacement -- by face id (same part re-imported) else by normal+area geometry. A function
with no confident target is reported for a manual re-flag, never mis-assigned.

Display-free (no renderer / no Tk / no llvmpipe segfault): pure-logic checks on the face-rematching
planner + getsource wiring/ordering guards on the service, editor wrapper, and menu.

Checks
------
* MATCH        -- ``plan_face_reassignments_for_replace``: same-part id match; different-part geometry
  match (aligned normal + comparable area); flipped normal still matches (abs dot); no aligned face ->
  reported unmatched (never mis-assigned); two authored faces never collapse onto one; default faces
  are NOT carried (only user-authored functions).
* SERVICE      -- ``replace_promoted_optical_solid_step`` CAPTURES the old faces BEFORE unpromote (which
  deletes the row), then unpromote -> set new path -> promote -> plan + assign; preserves pose (sets the
  imported path, never resets the rotation/offset).
* WRAPPER      -- the editor exposes ``replace_promoted_optical_solid_step`` and it delegates to the
  service (the mixin-wrapper trap: a service-only method silently no-ops via tkinter __getattr__).
* MENU         -- the element context menu offers "Replace STEP..." in BOTH promoted-solid branches;
  the handler delegates to the editor's replace method.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_replace_promoted_solid

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

from KrakenOS.UI.optical_solid_metadata import OPTICAL_SOLID_FACE_FUNCTION_DEFAULT as DEF
from KrakenOS.UI.services.step_overlay_promotion import (
    StepOverlayPromotionService,
    plan_face_reassignments_for_replace,
)


def _face(fid, fn, normal, area):
    return {"face_id": fid, "function": fn, "normal": normal, "area_mm2": area}


def _check_match(failures, notes):
    old = [
        _face("F1", "Mirror", (0.707, 0.0, 0.707), 1000.0),
        _face("F2", DEF, (0.0, 0.0, -1.0), 500.0),
        _face("F3", DEF, (-1.0, 0.0, 0.0), 500.0),
    ]
    # same part re-imported (ids + areas match) -> id match; default faces NOT carried
    plan, un = plan_face_reassignments_for_replace(
        old, [_face("F1", DEF, (0.707, 0.0, 0.707), 1005.0), _face("F2", DEF, (0.0, 0.0, -1.0), 500.0)]
    )
    if plan != [("F1", "Full Reflecting")] or un:
        failures.append(f"MATCH: same-part id match wrong (plan={plan}, unmatched={un})")
    # different part, aligned normal + comparable area -> geometry match
    plan, un = plan_face_reassignments_for_replace(old, [_face("X9", DEF, (0.70, 0.0, 0.71), 980.0)])
    if plan != [("X9", "Full Reflecting")] or un:
        failures.append(f"MATCH: geometry match wrong (plan={plan}, unmatched={un})")
    # flipped normal on re-import (abs dot) still matches
    plan, un = plan_face_reassignments_for_replace(old, [_face("Z1", DEF, (-0.707, 0.0, -0.707), 1010.0)])
    if plan != [("Z1", "Full Reflecting")] or un:
        failures.append(f"MATCH: flipped-normal match wrong (plan={plan}, unmatched={un})")
    # no aligned face -> unmatched, never mis-assigned
    plan, un = plan_face_reassignments_for_replace(
        old, [_face("Q1", DEF, (0.0, 1.0, 0.0), 300.0), _face("Q2", DEF, (0.0, -1.0, 0.0), 300.0)]
    )
    if plan != [] or un != ["Full Reflecting"]:
        failures.append(f"MATCH: no-match must report unmatched, not mis-assign (plan={plan}, unmatched={un})")
    # two authored faces never collapse onto one new face
    plan, un = plan_face_reassignments_for_replace(
        [_face("A", "Mirror", (0, 0, 1), 1000.0), _face("B", "Absorber/Mechanical", (0, 0, 1), 1000.0)],
        [_face("N1", DEF, (0, 0, 1), 1000.0), _face("N2", DEF, (0, 0, 0.99), 990.0)],
    )
    ids = [p[0] for p in plan]
    if len(set(ids)) != len(ids) or len(plan) != 2:
        failures.append(f"MATCH: two authored faces collapsed onto one (plan={plan})")
    if not [f for f in failures if f.startswith("MATCH")]:
        notes.append("match = id/geometry/flipped-normal match; no-match reported; authored-only; no collapse")


def _check_service(failures, notes):
    src = inspect.getsource(StepOverlayPromotionService.replace_promoted_optical_solid_step)
    # capture BEFORE unpromote (unpromote deletes the row)
    cap = src.find("OPTICAL_SOLID_FACES_ADVANCED_ATTR")
    unp = src.find("unpromote_optical_solid_to_overlay")
    prom = src.find("promote_imported_step_to_optical_solid_row")
    if not (0 <= cap < unp < prom):
        failures.append("SERVICE: must capture faces BEFORE unpromote, then unpromote before promote")
    if "imported_" not in src or "_step_path" not in src:
        failures.append("SERVICE: does not set the imported STEP path to the replacement")
    if "plan_face_reassignments_for_replace" not in src or "assign_optical_solid_face_function" not in src:
        failures.append("SERVICE: does not re-apply the captured face functions")
    # pose preservation: it must NOT reset the rotation/offset (that would move the solid)
    if "rotation_x_deg = 0.0" in src or "placement_offset_xyz = self._default" in src:
        failures.append("SERVICE: resets pose -- the replacement must keep the old pose")
    if not [f for f in failures if f.startswith("SERVICE")]:
        notes.append("service = capture->unpromote->set path->promote->re-apply; pose preserved")


def _check_wrapper(failures, notes):
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    if not hasattr(KrakenLayoutEditor, "replace_promoted_optical_solid_step"):
        failures.append("WRAPPER: the editor has no replace_promoted_optical_solid_step wrapper (service-only would no-op)")
        return
    wrap = inspect.getsource(KrakenLayoutEditor.replace_promoted_optical_solid_step)
    if "_step_overlay_promotion_service().replace_promoted_optical_solid_step" not in wrap:
        failures.append("WRAPPER: the editor wrapper does not delegate to the service")
    if not [f for f in failures if f.startswith("WRAPPER")]:
        notes.append("wrapper = editor wrapper delegates to the service (mixin-wrapper trap covered)")


def _check_menu(failures, notes):
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    menu = inspect.getsource(Open3DFaceAssignmentService.append_element_context_actions)
    if menu.count("Replace STEP...") != 2:
        failures.append(f"MENU: 'Replace STEP...' must appear in BOTH promoted-solid branches (got {menu.count('Replace STEP...')})")
    if "_replace_step_solid_from_context" not in menu:
        failures.append("MENU: the Replace entry is not wired to _replace_step_solid_from_context")
    handler = inspect.getsource(Open3DFaceAssignmentService._replace_step_solid_from_context)
    if "replace_promoted_optical_solid_step" not in handler:
        failures.append("MENU: the handler does not call the editor's replace method")
    if not [f for f in failures if f.startswith("MENU")]:
        notes.append("menu = 'Replace STEP...' in both branches; handler -> editor.replace_promoted_optical_solid_step")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (_check_match, _check_service, _check_wrapper, _check_menu):
        try:
            check(failures, notes)
        except Exception as exc:
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_replace_promoted_solid (bugs/0404) ===")
    for note in notes:
        print(f"  {'ok ' if '=' in note else 'XX '} {note}")
    if not passed:
        n = len([x for x in notes if "=" not in x])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll replace-promoted-solid checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
