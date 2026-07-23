"""Guard: a scene source (LED) has an interactive MOVE gizmo you drag to place it (bugs/0426).

User: "I need to be able to align this Illumination LED after adding it. Can make it a components which I
can place ... just like optical element?" -> chose the interactive 3D gizmo. Selecting a source in the
Scene Components browser now raises XYZ translate arrows at its origin; dragging one slides the source
(cheap actor-translate during the drag, committed to the origin via update_scene_source_spec on release,
the same deferred-commit trick as the row placement slide).

Checks
------
* HANDLES  -- the source glyph draws `_add_scene_source_translate_handles` when THIS source is selected
  and whole-body handle mode is on; the arrows carry `pick_source_move`, and `_add_mesh_actor` records
  it in `_actor_source_move_map`.
* DRAG     -- `_placement_drag_state_from_current_pick` builds a source drag state (source_id) from that
  map; `_apply_placement_drag_motion` cheap-translates the source actors; `_finish_placement_drag`
  commits via `_commit_source_move`.
* SELECT   -- the browser `source:` click routes to `select_scene_source_from_admin`, which raises the
  gizmo (handle mode + rebuild) and is mutually exclusive with the row gizmo.
* COMMIT   -- the commit slides the origin along the axis (origin += delta * unit-axis).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_source_move_gizmo

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

import numpy as np


def _isrc(method) -> str:
    return inspect.getsource(method)


def _check_handles(failures, notes):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as I
    glyph = _isrc(I._add_one_scene_source_glyph)
    if "_add_scene_source_translate_handles(source_id, origin" not in glyph:
        failures.append("HANDLES: the source glyph must draw the move gizmo for the selected source")
    if "self._selected_source_id" not in glyph or "self._show_rotation_handles()" not in glyph:
        failures.append("HANDLES: the gizmo must gate on the SELECTED source + whole-body handle mode")
    builder = _isrc(I._add_scene_source_translate_handles)
    if "pick_source_move=(source_id, axis" not in builder:
        failures.append("HANDLES: the arrows must be tagged pick_source_move=(source_id, axis, step)")
    add_actor = _isrc(I._add_mesh_actor)
    if "self._actor_source_move_map[actor_key] = (str(source_id), str(axis), float(delta_mm))" not in add_actor:
        failures.append("HANDLES: _add_mesh_actor must record pick_source_move in _actor_source_move_map")
    if not [f for f in failures if f.startswith("HANDLES")]:
        notes.append("handles = selected source draws XYZ move arrows tagged into _actor_source_move_map")


def _check_drag(failures, notes):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as I
    pick = _isrc(I._placement_drag_state_from_current_pick)
    if "self._actor_source_move_map.get(actor_key)" not in pick or '"source_id": str(source_id)' not in pick:
        failures.append("DRAG: the drag-state pick must build a source drag state from _actor_source_move_map")
    apply_src = _isrc(I._apply_placement_drag_motion)
    if 'source_id = state.get("source_id")' not in apply_src or "_translate_source_actors(str(source_id)" not in apply_src:
        failures.append("DRAG: the drag motion must cheap-translate the source actors for a source drag")
    finish = _isrc(I._finish_placement_drag)
    if 'source_id = state.get("source_id")' not in finish or "_commit_source_move(str(source_id)" not in finish:
        failures.append("DRAG: the drag release must commit via _commit_source_move for a source drag")
    if not [f for f in failures if f.startswith("DRAG")]:
        notes.append("drag = source arrow -> cheap-translate during drag -> commit origin on release")


def _check_select(failures, notes):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as I
    sel = _isrc(I.select_scene_source_from_admin)
    if "self._selected_source_id = sid" not in sel or "self.refresh_from_editor()" not in sel:
        failures.append("SELECT: select_scene_source_from_admin must set the selected source + rebuild")
    if "self._placement_handle_selected_row_index = None" not in sel:
        failures.append("SELECT: selecting a source must clear the row gizmo (mutually exclusive)")
    import KrakenOS.UI.panels.open3d_step_admin as admin
    admin_src = inspect.getsource(admin)
    if "select_scene_source_from_admin(iid.split(" not in admin_src:
        failures.append("SELECT: the browser source: click must route to select_scene_source_from_admin")
    if not [f for f in failures if f.startswith("SELECT")]:
        notes.append("select = browser source click raises the gizmo; row/source gizmos are exclusive")


def _check_commit(failures, notes):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector as I
    # the axis unit vectors the commit uses
    for axis, expected in (("x", [1, 0, 0]), ("y", [0, 1, 0]), ("z", [0, 0, 1])):
        v = np.asarray(I._placement_axis_vector(axis), dtype=float).reshape(-1)[:3]
        if not np.allclose(v, expected):
            failures.append(f"COMMIT: _placement_axis_vector({axis!r}) must be {expected}")
    # the commit math: origin += delta * unit-axis (reference reimplementation matching _commit_source_move)
    origin = np.array([10.0, 20.0, 30.0])
    new = origin + np.asarray(I._placement_axis_vector("y"), dtype=float).reshape(3) * 5.0
    if not np.allclose(new, [10.0, 25.0, 30.0]):
        failures.append("COMMIT: a +5 mm Y slide must move the origin to y+5")
    src = _isrc(I._commit_source_move)
    if "update_scene_source_spec" not in src or "origin[:3] + axis_unit * float(delta_mm)" not in src:
        failures.append("COMMIT: _commit_source_move must slide the origin along the axis via update_scene_source_spec")
    if not [f for f in failures if f.startswith("COMMIT")]:
        notes.append("commit = origin += delta * unit-axis, applied via update_scene_source_spec")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (_check_handles, _check_drag, _check_select, _check_commit):
        try:
            check(failures, notes)
        except Exception as exc:
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_source_move_gizmo (bugs/0426) ===")
    for note in notes:
        print(f"  {'ok ' if '=' in note else 'XX '} {note}")
    if not passed:
        n = len([x for x in notes if "=" not in x])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll source-move-gizmo checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
