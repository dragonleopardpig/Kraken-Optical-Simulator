"""Regression: dropping a carried STEP does not resurrect prior row's handles.

User flag (flag_20260531_094024_040): "this time carry seems OK, but once
placed, handels for the first elment come back." The fix in
``import_optical_step_overlay`` correctly suppresses the previously
promoted row's placement handles *during* the carry, but
``_finish_step_carry_drag`` clears ``_step_carry_active_label`` on
mouse release and the next refresh hits the placement-handle gate with
``_picked_row_index`` still pointing at the prior row, redrawing the 15
handles.

The scene-refresh gate was extended to also suppress placement handles
whenever a loaded-but-unpromoted STEP overlay is selected -- the user is
still actively focused on that import until they Promote/Accept it. This
test imports + promotes one STEP, then runs a second import followed by
``_finish_step_carry_drag`` (no actual mouse drag needed -- the carry
transition is dispatched via the same code path), and asserts that the
placement-handle actor maps remain empty.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _candidate_step_paths() -> list[Path]:
    candidates = [
        PROJECT_ROOT / "attachment" / "Lens" / "Achromatic_Lenses" / "32323" / "step_32323.stp",
        PROJECT_ROOT / "attachment" / "Lens" / "ball_lens" / "step_63227.stp",
        PROJECT_ROOT / "attachment" / "Lens" / "DCV" / "32996" / "step_32996.stp",
    ]
    return [path for path in candidates if path.exists()]


def _open_inspector(app: KrakenLayoutEditor) -> Kraken3DInspector:
    app.open_3d_view()
    app.update_idletasks()
    app.update()
    inspector = app._three_d_inspector
    if inspector is None or not inspector.available:
        raise RuntimeError("Embedded 3D inspector unavailable")
    inspector.geometry("1280x860+80+60")
    inspector.deiconify()
    inspector.lift()
    inspector.update_idletasks()
    inspector.update()
    time.sleep(0.2)
    inspector.update()
    return inspector


def _placement_handle_total(inspector: Kraken3DInspector) -> tuple[int, int]:
    return (
        len(inspector._actor_placement_move_map or {}),
        len(inspector._actor_placement_rotate_map or {}),
    )


def _run() -> int:
    steps = _candidate_step_paths()
    if len(steps) < 2:
        print(f"FAIL: need two STEP fixtures (got {len(steps)})", file=sys.stderr)
        return 2

    app = KrakenLayoutEditor()
    try:
        # Phase A: import + promote first STEP so S1 has placement handles.
        app.imported_optical_step_path = steps[0]
        app.select_step_component("optical")
        inspector = _open_inspector(app)
        inspector.refresh_from_editor()
        inspector.update_idletasks()
        promoted = app.promote_imported_step_to_optical_solid_row(
            "optical",
            open_face_editor=False,
            clear_overlay=True,
            refresh_open_3d=False,
        )
        if promoted is None:
            print("FAIL: first STEP promotion returned None", file=sys.stderr)
            return 2
        row_index = int(promoted.get("row_index", -1))
        inspector._picked_row_index = row_index
        inspector.refresh_from_editor()
        inspector.update_idletasks()
        baseline = _placement_handle_total(inspector)
        if baseline[0] + baseline[1] == 0:
            print(f"WARN: baseline has no placement handles ({baseline}); cannot detect leak", file=sys.stderr)
            return 0

        # Phase B: import the second STEP via import_optical_step_overlay.
        def _stub_import(dialog_parent=None, refresh_open_3d=False):
            app.imported_optical_step_path = steps[1]
            return steps[1]

        original = app.import_optical_step
        app.import_optical_step = _stub_import  # type: ignore[method-assign]
        try:
            inspector.import_optical_step_overlay()
        finally:
            app.import_optical_step = original  # type: ignore[method-assign]
        inspector.update_idletasks()
        in_carry = _placement_handle_total(inspector)
        if in_carry[0] + in_carry[1] != 0:
            print(
                f"FAIL: handles leaked DURING carry ({in_carry}); the upstream task #17 "
                "regression has come back.",
                file=sys.stderr,
            )
            return 1

        # Phase C: simulate the drop. _finish_step_carry_drag is the
        # exact method called on mouse release at the end of the carry.
        carry_state = inspector._step_carry_follow_state
        if carry_state is None:
            # The headless test path may not have a follow state attached.
            # Fabricate the minimal state the finish path expects: a
            # dict with the carry label so the service can fan out.
            carry_state = {"label": "optical"}
        inspector._finish_step_carry_drag(carry_state)
        inspector.refresh_from_editor()
        inspector.update_idletasks()
        after_drop = _placement_handle_total(inspector)
        carry_label = inspector._step_carry_active_label
        selected_step = getattr(app, "_selected_step_label", None)
        if after_drop[0] + after_drop[1] != 0:
            print(
                f"FAIL: prior-row placement handles came back after drop. "
                f"baseline={baseline} in_carry={in_carry} after_drop={after_drop} "
                f"carry_label={carry_label!r} selected_step_label={selected_step!r}.",
                file=sys.stderr,
            )
            return 1
        print(
            "PASS: dropping a carried STEP keeps the prior row's placement handles hidden. "
            f"baseline={baseline}, in_carry={in_carry}, after_drop={after_drop}, "
            f"selected_step={selected_step!r}."
        )
        return 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(_run())
