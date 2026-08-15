"""Guard for bugs/0619 — the CAD/Place/Orient commands live on the elements.

flag_20260814 (user request): element-targeted toolbar commands must be reachable from
dynamic interaction — right-click on the element — like 3D CAD software. Contracts:

  A  ROW verbs — the shared element branch appends Place (Move Row->Axis, Snap
     Row->Target) and the full Orient family on movable rows, at ALL THREE row
     classes (file-backed STL, promoted, plain), with the toolbar Axis/Normal
     combobox choices baked into the labels.
  B  STEP-body verbs — Move (carry), Rotate (arc handles), Center-a-Feature,
     Delete, and the LED reference-edge pick on the body's menu.
  C  FACE->AXIS one-step arming — the right-clicked face feeds the snap/center
     variants directly (StepFeatureSelection built from the menu context).
  D  SELECTION verbs — 2+ selected elements offer Snap Selected / Assembly
     actions; EMPTY-space right-click offers the rubber-band/axis-move starters
     instead of dead-ending.
  E  MECHANISM (display-free) — append_row_place_orient_actions on a stub menu
     yields the entries for a movable row and nothing for Object/Image;
     append_selection_actions yields entries only with 2+ picked rows.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0619_contextual_scene_commands
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace


class _StubMenu:
    def __init__(self):
        self.labels: list[str] = []

    def add_command(self, label="", command=None, state=None, **_k):
        self.labels.append(str(label))

    def add_separator(self):
        pass


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService as S

    src_shared = inspect.getsource(S.append_element_context_actions)
    src_rowverbs = inspect.getsource(S.append_row_place_orient_actions)
    src_body = inspect.getsource(S.append_step_body_actions)
    src_canvas = inspect.getsource(S._show_surface_function_context_menu)

    # ---------------------------------------------------------------- A: row verbs
    row_cmds = (
        "start_center_row_to_ray", "start_placement_target_pick", "start_placement_orient_pick",
        "start_placement_orient_ray_pick", "orient_selected_row_to_named_normal_target",
        "orient_selected_row_to_local_axis", "orient_selected_row_to_source_direction",
        "orient_selected_row_to_scene_source", "orient_selected_row_to_path_frame",
        "preview_selected_row_normal_target",
    )
    missing = [c for c in row_cmds if c not in src_rowverbs]
    if missing:
        ok = False
        notes.append(f"FAIL: A (bugs/0619): row menu lost commands {missing}")
    elif src_shared.count("append_row_place_orient_actions") < 3:
        ok = False
        notes.append(
            "FAIL: A (bugs/0619): the Place/Orient verbs are not wired at all three row "
            "classes (STL / promoted / plain) -- plain mirrors lose their context again"
        )
    elif "orient_axis_var" not in src_rowverbs or "normal_target_var" not in src_rowverbs:
        ok = False
        notes.append("FAIL: A: the Axis/Normal combobox choices are no longer baked into the labels")
    else:
        notes.append("PASS: A: Place + full Orient family on all three row classes, combobox-aware")

    # ---------------------------------------------------------------- B: body verbs
    body_cmds = ("start_selected_step_carry", "show_step_rotation_handler",
                 "start_any_step_axis_pick", "delete_selected_step", "start_led_object_edge_pick")
    body_all = src_body + inspect.getsource(S._arm_step_carry_from_context) + inspect.getsource(
        S._show_rotation_handles_from_context) + inspect.getsource(S._delete_step_from_context)
    missing = [c for c in body_cmds if c not in body_all]
    if missing or "append_step_body_actions" not in src_shared:
        ok = False
        notes.append(f"FAIL: B (bugs/0619): body menu lost {missing or 'the shared wiring'}")
    else:
        notes.append("PASS: B: Move/Rotate/Center-feature/Delete/LED-edge on the body menu")

    # ---------------------------------------------------------------- C: face->axis
    src_face = inspect.getsource(S._arm_step_face_axis_action)
    if "StepFeatureSelection" not in src_face or "_arm_step_face_axis_action" not in src_canvas:
        ok = False
        notes.append(
            "FAIL: C (bugs/0619): the right-clicked face no longer feeds the snap/center "
            "axis actions -- the two-click toolbar flow is the only path again"
        )
    else:
        notes.append("PASS: C: the right-clicked face arms the face->axis actions in one step")

    # ---------------------------------------------------------------- D: selection + empty
    src_sel = inspect.getsource(S.append_selection_actions)
    src_scene = inspect.getsource(S._show_scene_context_menu)
    needed_sel = ("start_snap_selected_to_axis", "group_selected_as_assembly",
                  "start_snap_assembly_to_axis", "clear_assembly")
    needed_scene = ("start_rubber_band_select", "start_rubber_band_select_and_snap", "start_axis_to_axis_move")
    if any(c not in src_sel for c in needed_sel):
        ok = False
        notes.append("FAIL: D (bugs/0619): the selection menu lost assembly/snap actions")
    elif any(c not in src_scene for c in needed_scene):
        ok = False
        notes.append("FAIL: D (bugs/0619): the empty-space menu lost its starters")
    elif "_show_scene_context_menu" not in src_canvas:
        ok = False
        notes.append("FAIL: D (bugs/0619): empty-space right-click dead-ends again")
    else:
        notes.append("PASS: D: selection menu + empty-space starters wired")

    # ---------------------------------------------------------------- E: mechanism
    class _Stub(S):
        def __init__(self, rows, picked):
            # The service __getattr__ forwards to _inspector -- seed it FIRST via
            # __dict__ so attribute lookups during init cannot recurse.
            self.__dict__["_inspector"] = SimpleNamespace(
                _picked_row_indices=picked,
                orient_axis_var=SimpleNamespace(get=lambda: "+Z"),
                normal_target_var=SimpleNamespace(get=lambda: "Detector"),
            )
            self.__dict__["editor"] = SimpleNamespace(rows=rows, append_debug=lambda *a, **k: None)

    rows = [SimpleNamespace(surface="Object"), SimpleNamespace(surface="Standard"),
            SimpleNamespace(surface="Image")]
    stub = _Stub(rows, {1, 2})
    menu = _StubMenu()
    if not stub.append_row_place_orient_actions(menu, 1) or len(menu.labels) < 10:
        ok = False
        notes.append(f"FAIL: E (bugs/0619): movable row produced {len(menu.labels)} entries (want >= 10)")
    elif "+Z" not in " ".join(menu.labels) or "Detector" not in " ".join(menu.labels):
        ok = False
        notes.append("FAIL: E: the combobox values are not in the built labels")
    else:
        notes.append(f"PASS: E1: movable row builds {len(menu.labels)} Place/Orient entries with live choices")
    menu = _StubMenu()
    if stub.append_row_place_orient_actions(menu, 0) or stub.append_row_place_orient_actions(menu, 2):
        ok = False
        notes.append("FAIL: E (bugs/0619): Object/Image rows offer Place/Orient (must refuse)")
    else:
        notes.append("PASS: E2: Object/Image rows refuse the Place/Orient section")
    menu = _StubMenu()
    if not stub.append_selection_actions(menu):
        ok = False
        notes.append("FAIL: E: a 2-element selection builds no selection menu")
    else:
        single = _Stub(rows, {1})
        menu = _StubMenu()
        if single.append_selection_actions(menu):
            ok = False
            notes.append("FAIL: E: a single selection wrongly offers the selection menu")
        else:
            notes.append("PASS: E3: selection menu appears at 2+ elements only")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Contextual-scene-commands validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
