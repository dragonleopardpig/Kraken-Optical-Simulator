"""Guard: adding a BEAM SPLITTER must not deviate the mirror optical axis (bugs/0429).

Flag flag_20260723_154034 (a 3-flag before/after recording): before a BS the AZ85 axis is a clean
2-mirror fold (``axis:global`` + ``reflected:1`` + ``reflected`` = 3 segments); after adding a BS plate a
spurious ``reflected:2`` appears (4 segments) and "the RA mirror optical axis deviates from 90 deg ...
doesn't restore".

Root cause: ``_folded_multifold_axis_guide_records`` groups every NON-mirror row into a straight branch by
direction. A BS is not a mirror fold, so it isn't excluded -- but it IS skipped from the fold override, so
it reads as straight +Z while the surrounding folded rows read the leg direction (+X). That mismatch
spawns a spurious extra branch -> an extra fold vertex -> the mirror axis shifts.

Fix: exclude BS rows from the branch grouping (like mirror rows). ``_promoted_beam_splitter_row_indices``
returns them (via ``_optical_solid_faces_have_beam_splitter`` + the explicit BS mark), and the multifold
walk skips them.

Checks
------
* CLASSIFY -- a BS face is a "Beam Splitter", NOT a "Mirror" fold, and vice-versa (so a BS is excluded and
  a mirror is still a fold vertex).
* HELPER   -- ``_promoted_beam_splitter_row_indices`` uses ``_optical_solid_faces_have_beam_splitter`` +
  the explicit BS mark.
* EXCLUDE  -- ``_folded_multifold_axis_guide_records`` skips ``bs_rows`` in the branch grouping.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_bs_not_axis_fold

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


_BS_FACES = {
    "version": 1,
    "faces": [
        {"face_id": "S001/F001", "role": "Output", "function": "Transmit/Port",
         "normal": [1.0, 0.0, 0.0], "centroid": [12.5, 0.0, 0.0], "area_mm2": 625.0, "triangle_indices": [0, 1]},
        {"face_id": "S001/F002", "role": "Beam Splitter", "function": "Beam Splitter",
         "normal": [-0.707, 0.0, -0.707], "centroid": [0.0, 0.0, 0.0], "area_mm2": 883.0, "triangle_indices": [2, 3]},
    ],
}
_MIRROR_FACES = {
    "version": 1,
    "faces": [
        {"face_id": "S001/F001", "role": "Mirror", "function": "Mirror",
         "normal": [-0.707, 0.0, -0.707], "centroid": [0.0, 0.0, 0.0], "area_mm2": 883.0, "triangle_indices": [0, 1]},
    ],
}


def _check_classify(failures, notes):
    from KrakenOS.UI.trace_intent import (
        _optical_solid_faces_have_beam_splitter,
        _optical_solid_faces_have_mirror_fold,
    )
    if not _optical_solid_faces_have_beam_splitter(_BS_FACES):
        failures.append("CLASSIFY: a BS face must classify as a beam splitter")
    if _optical_solid_faces_have_mirror_fold(_BS_FACES):
        failures.append("CLASSIFY: a BS face must NOT classify as a mirror fold (else it becomes a fold vertex)")
    if _optical_solid_faces_have_beam_splitter(_MIRROR_FACES):
        failures.append("CLASSIFY: a Mirror face must NOT classify as a beam splitter")
    if not _optical_solid_faces_have_mirror_fold(_MIRROR_FACES):
        failures.append("CLASSIFY: a Mirror face must still classify as a mirror fold")
    if not [f for f in failures if f.startswith("CLASSIFY")]:
        notes.append("classify = BS face -> beam splitter (not fold); Mirror face -> fold (not BS)")


def _check_helper(failures, notes):
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    src = inspect.getsource(KrakenLayoutEditor._promoted_beam_splitter_row_indices)
    if "_optical_solid_faces_have_beam_splitter" not in src:
        failures.append("HELPER: _promoted_beam_splitter_row_indices must use _optical_solid_faces_have_beam_splitter")
    if "beam_splitter" not in src or "OpticalSolidBeamSplitter" not in src:
        failures.append("HELPER: it must also honour the explicit BS mark (promotion / OpticalSolidBeamSplitter)")
    if not [f for f in failures if f.startswith("HELPER")]:
        notes.append("helper = _promoted_beam_splitter_row_indices detects BS faces + the explicit mark")


def _check_exclude(failures, notes):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    src = inspect.getsource(Kraken3DInspector._folded_multifold_axis_guide_records)
    if "_promoted_beam_splitter_row_indices()" not in src or "bs_rows" not in src:
        failures.append("EXCLUDE: the multifold walk must fetch bs_rows")
    if "row_index in mirror_rows or row_index in bs_rows" not in src:
        failures.append("EXCLUDE: the branch grouping must skip bs_rows (like mirror_rows)")
    if not [f for f in failures if f.startswith("EXCLUDE")]:
        notes.append("exclude = the multifold branch grouping skips BS rows, so a BS can't deviate the mirror axis")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (_check_classify, _check_helper, _check_exclude):
        try:
            check(failures, notes)
        except Exception as exc:
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_bs_not_axis_fold (bugs/0429) ===")
    for note in notes:
        print(f"  {'ok ' if '=' in note else 'XX '} {note}")
    if not passed:
        n = len([x for x in notes if "=" not in x])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll BS-not-axis-fold checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
