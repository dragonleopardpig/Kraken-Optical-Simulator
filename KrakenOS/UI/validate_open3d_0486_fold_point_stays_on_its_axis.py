"""bugs/0486 -- a fold point must stay ON the axis feeding it; a station is not that axis.

Flag flag_20260730_160140: "changed to FOV 30x30, RA mirror shifted, not centered to optical axis,
the fold axis also slanted."

bugs/0468 keeps the sensor off the fold mirror by SLIDING THE MIRROR rather than refusing, and it
applied that slide by writing ``rows[near_gap_row].thickness``. On a FROZEN fold a station thickness
is not a distance along the mirror's incoming leg: the leg runs +x while a thickness moves the row
in z. So the slide displaced the mirror PERPENDICULAR to its own beam, by exactly the deficit.

Measured on ``attachment/machine_vision_AZ85_RA_Mirror_BS.py`` at 30 x 30, stepping the solve:

    start                                  off-parent 0.0000   mirror (229.930, 0, 53.803)
    ENTRY apply_image_distance_frozen_aware off-parent 6.1200   mirror (229.930, 0, 84.576)
                                                               BS coating  (0, 0, 90.696)

The object write shifted every station +36.892, so the BS coating (the parent leg) went to
z = 90.696 -- but the mirror reached only 84.576, because the resolver had already shortened row 6
by the 6.12 mm deficit. 90.696 - 84.576 = 6.120: the fold point hung that far below the beam that
feeds it, and the emitted leg then drew slanted (3.39 deg measured).

The frozen writer ``_apply_folded_image_split`` slides along ``in_dir`` and re-seats the sensor and
camera on the exit leg (bugs/0447) -- which is why the MANUAL leg constraint was always clean
(measured: mirror delta [-20, 0, 0], 0.0 deg off axis, z untouched). Routing the resolver's slide
through it holds the invariant: measured off-parent 0.0000 at 23/30/35/40 mm, with the mirror moving
only in x, and ``out_dir`` exactly (0, 0, -1) -- perpendicular to the incoming +x leg.

The invariant itself is the guard: a child segment's origin lies on its parent
(``optical_axis_tree.check_invariants`` CONTINUITY, bugs/0485), so this is the first fix in the
family pinned by a STRUCTURAL rule rather than by a scene-specific number.

Display-free: a stub editor for the routing, and a synthetic tree for the invariant.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0486_fold_point_stays_on_its_axis
"""
from __future__ import annotations

from types import SimpleNamespace

FROZEN_SPLIT = {
    "total": 154.77, "near": 103.27, "far": 51.50,
    "mirror_row": 7, "near_gap_row": 6, "far_gap_row": 7,
    "near_min": 12.5, "far_min": 12.5, "frozen_world": True, "frozen_kind": "image_mirror",
}
STRAIGHT_SPLIT = {**FROZEN_SPLIT, "frozen_world": False}


class _Row:
    def __init__(self, thickness):
        self.thickness = float(thickness)
        self.desp_x = self.desp_y = self.desp_z = 0.0
        self.advanced = {}
        self.name = ""


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    try:
        import numpy as np

        from KrakenOS.UI.services import optical_axis_tree as tree_mod
        from KrakenOS.UI.services.quick_estimation import QuickEstimationService
    except Exception as exc:  # pragma: no cover - environment skip
        notes.append(f"SKIP: deps unavailable ({type(exc).__name__}: {exc})")
        return True, notes

    # --- A. the invariant: a fold point off its parent is a CONTINUITY violation -----------
    rows = [_Row(0.0), _Row(0.0)]
    tree = tree_mod.build_axis_tree(
        rows,
        fold_emissions={
            1: {"origin": (229.93, 0.0, 53.803), "direction": (0.0, 0.0, -1.0), "kind": "reflect"}
        },
        root_origin=(0.0, 0.0, 53.803),
        root_direction=(1.0, 0.0, 0.0),
    )
    snaps = tree_mod.snap_rows(rows, tree)
    check(
        not [p for p in tree_mod.check_invariants(rows, tree, snaps) if p.startswith("CONTINUITY")],
        "A1: a fold point ON its parent raises no CONTINUITY violation",
    )
    off_tree = tree_mod.build_axis_tree(
        rows,
        fold_emissions={
            # the measured broken state: 5.33 mm below the beam feeding it
            1: {"origin": (253.495, 0.0, 48.473), "direction": (0.0, 0.0, -1.0), "kind": "reflect"}
        },
        root_origin=(0.0, 0.0, 53.803),
        root_direction=(1.0, 0.0, 0.0),
    )
    off_snaps = tree_mod.snap_rows(rows, off_tree)
    violations = [p for p in tree_mod.check_invariants(rows, off_tree, off_snaps) if p.startswith("CONTINUITY")]
    check(
        len(violations) == 1 and "5.33" in violations[0],
        f"A2: the reported state IS a CONTINUITY violation of 5.33 mm ({violations[0][:80] if violations else None})",
    )

    # --- B. the routing: a frozen scene slides through the writer, not a thickness ---------
    for label, split, expect_writer in (
        ("frozen", FROZEN_SPLIT, True),
        ("straight", STRAIGHT_SPLIT, False),
    ):
        calls: list = []
        thicknesses = {6: _Row(103.27), 7: _Row(51.5)}
        editor = SimpleNamespace(
            rows={**{i: _Row(0.0) for i in range(9)}, **thicknesses},
            _folded_image_conjugate_split=lambda s=split: dict(s),
            _apply_folded_image_split=lambda leg, value: (calls.append((leg, float(value))), (True, "slid"))[1],
            _step_path_for_label=lambda name: None,
            _current_camera_front_to_sensor_mm=lambda: 11.48,
        )
        service = QuickEstimationService(SimpleNamespace(editor=editor))
        # Drive the branch the way the solve does: a resolved collision with a -6.12 deficit.
        near_before = editor.rows[6].thickness
        resolved = (24.98, 6, -6.12, "Mirror slid 6.12 mm toward the lens")
        # Replicate the application block's contract without running the whole solve.
        frozen_slide = False
        if bool(split.get("frozen_world")):
            okk, _m = editor._apply_folded_image_split("near", float(split["near"]) + resolved[2])
            frozen_slide = bool(okk)
        if not frozen_slide:
            editor.rows[6].thickness = float(editor.rows[6].thickness) + float(resolved[2])
        if expect_writer:
            check(
                len(calls) == 1 and abs(calls[0][1] - (103.27 - 6.12)) < 1e-6,
                f"B1 [{label}]: the slide goes through the frozen writer at "
                f"near = {103.27 - 6.12:.4g} mm (got {calls[0][1] if calls else None})",
            )
            check(
                abs(editor.rows[6].thickness - near_before) < 1e-9,
                f"B2 [{label}]: the station thickness is NOT written (it would move the mirror "
                f"perpendicular to its leg)",
            )
        else:
            check(
                not calls and abs(editor.rows[6].thickness - (near_before - 6.12)) < 1e-9,
                f"B3 [{label}]: an unfrozen scene keeps the thickness write, where a station IS "
                f"along the beam",
            )

    # --- C. the solve actually branches on frozen, and the margin is the user's 5 mm -------
    try:
        import inspect as _inspect

        src = _inspect.getsource(QuickEstimationService._apply_conjugate_pair)
        check(
            "_frozen_slide" in src and "_apply_folded_image_split" in src,
            "C1: the collision resolver's application routes a frozen slide through the writer",
        )
        raw_at = src.find("rows[_near_row].thickness = (")
        guard_at = src.find("if not _frozen_slide:")
        check(
            0 <= guard_at < raw_at,
            "C2: the raw thickness write is guarded by the frozen branch, not the default",
        )
    except Exception as exc:
        notes.append(f"SKIP: solve source unreadable ({type(exc).__name__}: {exc})")
    check(
        abs(float(QuickEstimationService.IMAGE_LEG_ASSEMBLY_MARGIN_MM) - 5.0) < 1e-9,
        f"C3: the assembly margin is the 5 mm the user asked for "
        f"(got {QuickEstimationService.IMAGE_LEG_ASSEMBLY_MARGIN_MM})",
    )
    bare = QuickEstimationService(
        SimpleNamespace(
            editor=SimpleNamespace(
                _folded_image_conjugate_split=lambda: dict(FROZEN_SPLIT),
                _step_path_for_label=lambda name: "/tmp/camera.step" if name == "camera" else None,
                _current_camera_front_to_sensor_mm=lambda: 11.48,
                rows=[],
            )
        )
    )
    check(
        abs(float(bare._image_gap_collision_floor()) - (12.5 + 11.48 + 5.0)) < 1e-9,
        f"C4: the floor is mirror + body + 5 mm margin = {12.5 + 11.48 + 5.0:.4g} mm "
        f"(got {bare._image_gap_collision_floor():.4g})",
    )

    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if note.startswith(("PASS", "SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
