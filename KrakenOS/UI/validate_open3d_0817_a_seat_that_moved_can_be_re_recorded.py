"""Guard for bugs/0817 -- a placement that moved on purpose can be re-recorded.

`StepOverlayPromotion.center_world` is written once, at promotion. bugs/0760 measured the vendor
clearance on `om05a_26_1_r03_2s_lr_asm.stp` (7.596 mm, against 4.033 mm in the scene) and moved the
big RA mirror 3.563 mm onto it -- a deliberate, correct move that no longer matches the snapshot the
row carries. Nothing could refresh it, so the bugs/0750 audit, the bugs/0816 notice and the authored
cover strips have all been 3.563 mm behind ever since, and phase 505's A8b still reports it.

The right-click verb records the LIVE pose as the row's authored placement. It moves nothing, it is
never automatic, and it only appears on a row that is actually off its seat.

Checks:
  A  LIVE (SKIP when the Filen-synced scene is absent): on the user's scene, re-pinning the big RA
     mirror takes its drift 3.563 -> 0.000 while its desps, its thickness and its live pose are
     untouched, and the old placement stays recorded as `center_world_repinned_from`.
  B  REFUSALS: a row already on its seat, a row with no promotion snapshot and an index outside the
     scene all decline with a reason, and change nothing.
  C  UI: the verb appears only on a drifted row, and the context command confirms first, applies
     through the editor, then routes the redraw through `_apply_model_change`.

Display-free apart from the Tk editor the LIVE section loads (as bugs/0672's guard does).

Run:
    xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0817_a_seat_that_moved_can_be_re_recorded

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io
from pathlib import Path
from types import SimpleNamespace

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment/om05a_folded.py"
TARGET = "RA mirror 1 (50 mm)"


def _drift_for(rows, name):
    from KrakenOS.UI.services.scene_placement_audit import pinned_placement_drifts

    return next(
        (r for r in pinned_placement_drifts(rows) if str(r["name"]) == name), None
    )


def _check_live(ok, skip) -> None:
    if not SCENE.exists():
        skip("A: the om05a folded scene is not on this machine (Filen-synced)")
        return
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = None
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            editor = KrakenLayoutEditor()
            editor._prompt_for_missing_cad_assets = lambda: None
            editor.layout_files["omf"] = SCENE
            editor.load_layout_by_name("omf")
    except Exception as exc:  # pragma: no cover - env dependent
        skip(f"A: the scene could not be loaded here ({type(exc).__name__}: {exc})")
        with contextlib.suppress(Exception):
            editor.destroy()
        return
    try:
        rows = list(editor.rows)
        before = _drift_for(rows, TARGET)
        if before is None or before.get("drift_mm") is None:
            skip(f"A: {TARGET} is not in this scene")
            return
        index = int(before["row"])
        row = rows[index]

        # bugs/0817 was DONE on this scene on 2026-09-18: both big RA mirrors carry the live
        # pose now, so the check cannot rely on finding a drifted row -- it would be asserting
        # that the user has not tidied up yet. Record the outcome, then STAGE a stale snapshot
        # of its own (the snapshot only, never the geometry) so the command is still exercised
        # on a real scene.
        promotion_now = dict((row.advanced or {}).get("StepOverlayPromotion") or {})
        ok(
            float(before["drift_mm"]) <= 1e-9
            and promotion_now.get("center_world_repinned_from") is not None,
            f"A0: {TARGET} sits on its authored placement and says where it used to sit "
            f"({float(before['drift_mm']):.6f} mm, from "
            f"{promotion_now.get('center_world_repinned_from')})",
        )

        stale = [float(v) for v in before["authored"]]
        stale[1] -= 3.563                      # the bugs/0760 move, put back on the SNAPSHOT
        advanced = dict(row.advanced or {})
        promotion = dict(advanced.get("StepOverlayPromotion") or {})
        promotion["center_world"] = list(stale)
        promotion.pop("center_world_repinned_from", None)
        advanced["StepOverlayPromotion"] = promotion
        row.advanced = advanced
        before = _drift_for(list(editor.rows), TARGET)

        pose_before = [float(v) for v in before["live"]]
        geom_before = (
            float(row.thickness), float(row.desp_x), float(row.desp_y), float(row.desp_z),
            float(row.tilt_x), float(row.tilt_y), float(row.tilt_z),
        )
        authored_before = [float(v) for v in before["authored"]]
        ok(
            abs(float(before["drift_mm"]) - 3.563) < 1e-3,
            f"A0b: staging the pre-0760 snapshot makes the row read 3.563 mm adrift again "
            f"({float(before['drift_mm']):.4f})",
        )

        applied, message = editor.pin_row_placement_as_authored(index)
        after = _drift_for(list(editor.rows), TARGET)
        ok(
            applied and after is not None and float(after["drift_mm"]) <= 1e-9,
            f"A1: re-pinning takes the drift {float(before['drift_mm']):.3f} -> "
            f"{'n/a' if after is None else float(after['drift_mm']):.6f} mm ({message[:70]})",
        )
        geom_after = (
            float(row.thickness), float(row.desp_x), float(row.desp_y), float(row.desp_z),
            float(row.tilt_x), float(row.tilt_y), float(row.tilt_z),
        )
        ok(
            geom_after == geom_before
            and after is not None
            and np.allclose(np.asarray(after["live"], float), pose_before, atol=1e-9),
            "A2: NOTHING moved -- thickness, decentres, tilts and the live pose are unchanged",
        )
        promotion = (dict(row.advanced or {}).get("StepOverlayPromotion") or {})
        ok(
            np.allclose(
                np.asarray(promotion.get("center_world_repinned_from", []), float),
                authored_before,
                atol=1e-9,
            ),
            f"A3: the placement it used to record stays in the scene "
            f"({promotion.get('center_world_repinned_from')})",
        )
        applied_again, message_again = editor.pin_row_placement_as_authored(index)
        ok(
            not applied_again and "already sits" in message_again,
            f"A4: re-pinning a row that is now on its seat declines ({message_again[:60]})",
        )
    finally:
        with contextlib.suppress(Exception):
            editor.destroy()


def _check_refusals(ok) -> None:
    """B: the refusals, on a fake editor -- no scene and no Tk needed."""
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    class _Row:
        def __init__(self, name, advanced=None):
            self.name = name
            self.advanced = advanced or {}
            self.thickness = 10.0
            self.desp_x = self.desp_y = self.desp_z = 0.0
            self.tilt_x = self.tilt_y = self.tilt_z = 0.0
            self.surface = "Standard"

    editor = SimpleNamespace(
        rows=[_Row("plain row")],
        append_debug=lambda *_a, **_k: None,
        status_var=SimpleNamespace(set=lambda *_a: None),
    )
    pin = ScenePlacementMixin.pin_row_placement_as_authored.__get__(editor, type(editor))
    applied, message = pin(0)
    ok(
        not applied and "no authored placement" in message,
        f"B1: a row with no promotion snapshot declines with a reason ({message[:50]})",
    )
    applied, message = pin(7)
    ok(
        not applied and "not in this scene" in message,
        f"B2: an index outside the scene declines with a reason ({message[:50]})",
    )
    ok(
        editor.rows[0].advanced == {},
        "B3: a declined re-pin writes nothing",
    )


def _check_ui(ok) -> None:
    """C: the menu offers the verb only where it means something, and the command wiring."""
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    class _Menu:
        def __init__(self):
            self.labels = []

        def add_command(self, label=None, command=None, **_k):
            self.labels.append(str(label))

    class _Row:
        def __init__(self, centre, live_offset):
            self.name = "probe"
            self.advanced = {"StepOverlayPromotion": {"center_world": list(centre)}}
            self._live_offset = live_offset

    def _append(rows, poses):
        service = SimpleNamespace(editor=SimpleNamespace(rows=rows))
        bound = Open3DFaceAssignmentService._append_placement_seat_action.__get__(
            service, type(service)
        )
        menu = _Menu()
        # patch the reading the verb keys on, so this stays a pure UI check
        import KrakenOS.UI.services.scene_placement_audit as audit

        original = audit.pinned_placement_drifts
        audit.pinned_placement_drifts = lambda _rows: poses
        try:
            bound(menu, 0)
        finally:
            audit.pinned_placement_drifts = original
        return menu.labels

    drifted = [{"row": 0, "name": "probe", "authored": [0, 0, 0], "live": [0, 3.563, 0], "drift_mm": 3.563}]
    seated = [{"row": 0, "name": "probe", "authored": [0, 0, 0], "live": [0, 0, 0], "drift_mm": 0.0}]
    labels_drifted = _append([_Row((0, 0, 0), 3.563)], drifted)
    labels_seated = _append([_Row((0, 0, 0), 0.0)], seated)
    ok(
        len(labels_drifted) == 1 and "Pin Current Placement as Authored" in labels_drifted[0]
        and "3.563 mm off" in labels_drifted[0],
        f"C1: a drifted row is offered the verb, with the amount in the label ({labels_drifted})",
    )
    ok(
        labels_seated == [],
        f"C2: a row on its seat is offered nothing ({labels_seated})",
    )
    src = inspect.getsource(Open3DFaceAssignmentService._pin_row_placement_from_context)
    ok(
        "askyesno" in src
        and "pin_row_placement_as_authored" in src
        and "_apply_model_change()" in src,
        "C3: the command confirms with both poses, applies through the editor, and redraws "
        "through the model-change chokepoint",
    )
    menu_src = inspect.getsource(Open3DFaceAssignmentService.append_element_context_actions)
    ok(
        menu_src.count("_append_placement_seat_action(menu, row_index)") == 2,
        "C4: both promoted-row branches of the element menu offer it",
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(cond: bool, label: str) -> None:
        notes.append(("PASS " if cond else "FAIL ") + label)

    def skip(label: str) -> None:
        notes.append("SKIP " + label)

    _check_live(ok, skip)
    _check_refusals(ok)
    _check_ui(ok)

    passed = not any(n.startswith("FAIL") for n in notes)
    if verbose:
        for n in notes:
            print(n)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Open 3D re-record-the-seat validation passed.")
        return 0
    print("Open 3D re-record-the-seat validation FAILED:")
    for n in notes:
        if n.startswith("FAIL"):
            print(f"- {n}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
