"""Guard for bugs/0139 -- promoting a STEP solid must not flash a distant element pink.

Regression context
------------------
Promoting an imported STEP overlay (e.g. the beam-splitter cube) to an optical solid
briefly highlighted a SEPARATE, upstream element -- the imaging lens's "Lens Front
Datum" -- pink during the promotion ("the lens surrogate front datum highlight pink
as well during BS promotion ... why there is a link?").

Pink is the app-wide SELECTED-row highlight; a row highlight pinks every actor whose
``_actor_row_map`` value equals the selected index. The promote-and-assign flow
(``_promote_step_and_assign_face_function``) inserts the new solid with
``refresh_open_3d=False`` -- so the 3-D actor->row map is STALE -- and then called
``editor._select_table_row(row_index)``, which SYNCHRONOUSLY drives
``_sync_surface_selection`` -> ``highlight_row`` against that stale map. In the
pre-promote map the new row's index belonged to whatever row sat there before, i.e.
the upstream Lens Front Datum, so it lit up. The rebuild that follows repaints the
real solid, making it a transient flash.

The fix selects the new row via ``editor._select_table_indices([row_index],
focus_index=row_index)`` -- the QUIET selector that sets the same table selection
WITHOUT the synchronous stale-map 3-D highlight -- and lets the rebuild +
``highlight_row`` paint the solid against the FRESH map.

This guard is display-free. It pins the source contracts: the promote-and-assign
selects via ``_select_table_indices`` (not ``_select_table_row``); and the two
selectors still differ in the way the fix relies on -- ``_select_table_row`` syncs
3-D synchronously, ``_select_table_indices`` does not.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_promote_no_stale_highlight

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    try:
        from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService
    except Exception as exc:
        notes.append(f"FAIL: could not import Open3DFaceAssignmentService: {exc!r}")
        return False, notes
    try:
        from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin
    except Exception as exc:
        notes.append(f"FAIL: could not import LayoutTableWorkbenchMixin: {exc!r}")
        return False, notes

    # A. The promote-and-assign selects the new solid with the QUIET selector.
    #    bugs/0145 split the method into a suppression wrapper + the
    #    ``_inner`` body that holds the actual selection logic, so read the body.
    try:
        promote_src = inspect.getsource(
            Open3DFaceAssignmentService._promote_step_and_assign_face_function_inner
        )
    except Exception as exc:
        notes.append(f"FAIL: could not read _promote_step_and_assign_face_function source: {exc!r}")
        return False, notes
    if "_select_table_indices([row_index], focus_index=row_index)" not in promote_src:
        notes.append(
            "FAIL: _promote_step_and_assign_face_function no longer selects the new solid via "
            "_select_table_indices([row_index], focus_index=row_index) -- the quiet selector that "
            "avoids the stale-map highlight (bugs/0139)"
        )
        passed = False
    if "_select_table_row(row_index)" in promote_src:
        notes.append(
            "FAIL: _promote_step_and_assign_face_function still calls _select_table_row(row_index) -- "
            "that synchronously highlights against the STALE pre-rebuild map and flashes the upstream "
            "lens Front Datum pink (bugs/0139)"
        )
        passed = False

    # B. The two selectors still differ exactly the way the fix relies on:
    #    _select_table_row syncs 3-D synchronously; _select_table_indices does not.
    try:
        row_src = inspect.getsource(LayoutTableWorkbenchMixin._select_table_row)
    except Exception as exc:
        notes.append(f"FAIL: could not read _select_table_row source: {exc!r}")
        return False, notes
    if "_sync_surface_selection" not in row_src:
        notes.append(
            "FAIL: _select_table_row no longer calls _sync_surface_selection -- the synchronous 3-D "
            "highlight the fix deliberately avoids is gone, so the guard no longer pins a real "
            "distinction (bugs/0139)"
        )
        passed = False

    try:
        indices_src = inspect.getsource(LayoutTableWorkbenchMixin._select_table_indices)
    except Exception as exc:
        notes.append(f"FAIL: could not read _select_table_indices source: {exc!r}")
        return False, notes
    if "_sync_surface_selection" in indices_src:
        notes.append(
            "FAIL: _select_table_indices now calls _sync_surface_selection too -- the quiet selector "
            "the fix switched to would ALSO highlight against the stale map (bugs/0139)"
        )
        passed = False

    if verbose:
        notes.append(
            "checked: the promote-and-assign selects via _select_table_indices (not _select_table_row); "
            "_select_table_row still syncs 3-D synchronously while _select_table_indices does not"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] bugs/0139: promoting a STEP solid does not flash a distant element pink")
        return 0
    print("[FAIL] bugs/0139 cross-element stale-highlight guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
