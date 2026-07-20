"""Display-free guard for bugs/0363 -- the scene source as a general 3D element.

``update_scene_source_spec`` edits a source's name/position/aim/size/cone/rays/power
in place (both spec key forms, editable-key filter, radius refresh) through the
standard row-action apply path; ``seat_scene_source_on_face`` is the one-shot glue
(origin = picked face centroid, aim INTO the solid). WIRING: the browser source row
offers "Edit Source...", the 3D face menu offers per-source "Seat ... on This Face",
and the dialog writes through the same helper.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_scene_source_edit
"""

from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor


class _Fake:
    SCENE_SOURCE_EDITABLE_KEYS = KrakenLayoutEditor.SCENE_SOURCE_EDITABLE_KEYS
    update_scene_source_spec = KrakenLayoutEditor.update_scene_source_spec
    seat_scene_source_on_face = KrakenLayoutEditor.seat_scene_source_on_face
    _normalize_scene_source_specs = KrakenLayoutEditor._normalize_scene_source_specs

    def __init__(self, specs):
        self.layout_scene_source_specs = list(specs)
        self.applied = None
        self.applied_status = ""

    def _apply_scene_source_row_action_specs(self, specs, *, record_history=True, status=""):
        self.applied = [dict(spec) for spec in specs]
        self.applied_status = str(status)


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    base = {
        "source_id": "source:led-1",
        "name": "LED",
        "model": "Random rectangle source",
        "role": "illumination",
        "physical": True,
        "enabled": True,
        "origin": [10.0, 0.0, 5.0],
        "direction": [0.0, 0.0, 1.0],
        "radius_x": 27.5,
        "radius_y": 37.0,
        "radius": 37.0,
        "cone_deg": 90.0,
        "ray_count": 2000,
        "power": 1.0,
    }

    fake = _Fake([dict(base)])
    ok = fake.update_scene_source_spec(
        "source:led-1",
        {
            "origin": [1.0, 2.0, 3.0],
            "source_x": 1.0, "source_y": 2.0, "source_z": 3.0,
            "radius_x": 10.0, "radius_y": 4.0,
            "role": "imaging",  # NOT editable -- must be filtered
        },
    )
    if not ok or fake.applied is None:
        failures.append("update_scene_source_spec must apply through the row-action path")
    else:
        spec = fake.applied[0]
        if spec.get("origin") != [1.0, 2.0, 3.0] or float(spec.get("source_x", 0)) != 1.0:
            failures.append("origin must update in BOTH spec key forms")
        if float(spec.get("radius", 0.0)) != 10.0:
            failures.append("radius must refresh to max(radius_x, radius_y)")
        if str(spec.get("role")) != "illumination":
            failures.append("non-editable keys must be filtered (role changed!)")
    if _Fake([dict(base)]).update_scene_source_spec("source:missing", {"power": 2.0}):
        failures.append("an unknown source_id must return False")

    fake2 = _Fake([dict(base)])
    ok = fake2.seat_scene_source_on_face("source:led-1", (27.5, 0.0, 229.6), (2.0, 0.0, 0.0))
    if not ok or fake2.applied is None:
        failures.append("seat_scene_source_on_face must apply")
    else:
        spec = fake2.applied[0]
        if spec.get("origin") != [27.5, 0.0, 229.6]:
            failures.append(f"seat must place the origin at the face centroid, got {spec.get('origin')}")
        direction = np.asarray(spec.get("direction"), dtype=float)
        if not np.allclose(direction, [-1.0, 0.0, 0.0]):
            failures.append(f"seat must aim INTO the solid (-normal, unit), got {direction}")
    if _Fake([dict(base)]).seat_scene_source_on_face("source:led-1", (0, 0, 0), (0, 0, 0)):
        failures.append("a degenerate face normal must return False")

    # WIRING
    from KrakenOS.UI.panels.open3d_step_admin import Open3DStepAdminPanel

    menu_src = inspect.getsource(Open3DStepAdminPanel._show_element_context_menu)
    if "Edit Source" not in menu_src or "_edit_scene_source" not in menu_src:
        failures.append("the browser source row lost its Edit Source entry")
    import KrakenOS.UI.panels.open3d_source_edit_dialog as dialog_module

    dialog_src = inspect.getsource(dialog_module)
    if "update_scene_source_spec" not in dialog_src:
        failures.append("the edit dialog must write through update_scene_source_spec")
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    face_src = inspect.getsource(Open3DFaceAssignmentService)
    if "seat_scene_source_on_face" not in face_src or "Seat " not in face_src:
        failures.append("the 3D face menu lost its Seat-source entries")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Scene-source edit validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Scene-source edit validation passed: sources edit in place (both key forms, "
        "editable-key filter, radius refresh) and seat onto a picked face (centroid + "
        "into-the-solid aim), wired through the browser Edit Source dialog and the 3D "
        "face menu's Seat entries."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
