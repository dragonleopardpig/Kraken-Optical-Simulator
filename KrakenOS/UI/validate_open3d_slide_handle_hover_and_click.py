"""Guard for bugs/0019 — the placement MOVE (slide) handle must highlight on
hover, and a bare click on it must NOT slide / retrace.

Regression context
------------------
A promoted optical-solid row shows a Move (slide) handle and a Rotate handle.
Two things were wrong (flag_20260605_153157_448):

1. Hovering the slide handle did not highlight it. The passive hover pick set
   (`_passive_hover_pick_rotation_handle`) was built from the step-rotate,
   step-translate and placement-ROTATE maps, but NOT `_actor_placement_move_map`,
   and neither hover-decision branch in `_on_mouse_move` handled a placement-move
   pick -- so the slide handle never got the gold hover affordance.
2. A bare left click (no drag) on the slide handle "computed hard and jerked":
   `PlacementTranslateWidget.process` applied a discrete `delta_mm` translate via
   `_apply_scene_placement_translate_handle`, which forces a full promoted-solid
   retrace (~0.5 s) and nudged the element one step. Sliding is a hold-drag
   gesture (the drag path is already cheap, bugs/0012); a bare click should be a
   no-op hint.

Fix: add `_actor_placement_move_map` to the hover pick set and a `placement_move`
branch (gold highlight + drag hint) to both hover-decision paths; make
`PlacementTranslateWidget.process` consume a click with a hold-drag hint instead
of translating.

This guard is display-free (source contracts + a mock-inspector widget test), so
it always runs.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_slide_handle_hover_and_click

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    from KrakenOS.UI.services.open3d_interaction import Open3DInteractionService
    from KrakenOS.UI.services.open3d_placement_widget import PlacementTranslateWidget
    from KrakenOS.UI.services.open3d_interaction_event import InteractionEventData, PickTarget
    from KrakenOS.UI.services.open3d_interaction_mode import InteractionMode

    # A. The passive hover pick set must include the placement-MOVE handle.
    try:
        hover_src = inspect.getsource(Open3DInteractionService._passive_hover_pick_rotation_handle)
    except Exception as exc:
        hover_src = ""
        notes.append(f"FAIL: cannot read _passive_hover_pick_rotation_handle source: {exc!r}")
        passed = False
    if hover_src and "_actor_placement_move_map" not in hover_src:
        notes.append("FAIL: hover pick set omits _actor_placement_move_map — the slide handle never hover-highlights")
        passed = False

    # B. Both hover-decision paths (axis-pick + default) must highlight a
    #    placement-move pick.
    try:
        move_src = inspect.getsource(Open3DInteractionService._on_mouse_move)
    except Exception as exc:
        move_src = ""
        notes.append(f"FAIL: cannot read _on_mouse_move source: {exc!r}")
        passed = False
    if move_src:
        n_branch = move_src.count("if placement_move is not None:")
        n_read = move_src.count("placement_move = self._actor_placement_move_map.get(")
        if n_branch < 2:
            notes.append(f"FAIL: _on_mouse_move has {n_branch} placement_move hover branch(es); expected 2 (axis-pick + default)")
            passed = False
        if n_read < 2:
            notes.append(f"FAIL: _on_mouse_move reads the placement-move map {n_read} time(s); expected 2")
            passed = False

    # C. A bare click on the slide handle must NOT apply a translate.
    try:
        proc_src = inspect.getsource(PlacementTranslateWidget.process)
    except Exception as exc:
        proc_src = ""
        notes.append(f"FAIL: cannot read PlacementTranslateWidget.process source: {exc!r}")
        passed = False
    # Match the CALL form (trailing "(") so the explanatory comment that names
    # the old handler doesn't count as a regression.
    if proc_src and "_apply_scene_placement_translate_handle(" in proc_src:
        notes.append("FAIL: PlacementTranslateWidget.process still applies a translate on click (the jerk + ~0.5s retrace)")
        passed = False

    # D. Behavioural: a placement-translate click is consumed with a drag hint
    #    and does NOT call the translate handler (no retrace).
    class _StatusVar:
        def __init__(self) -> None:
            self.value = ""

        def set(self, value) -> None:
            self.value = str(value)

    class _MockInspector:
        def __init__(self) -> None:
            self.status_var = _StatusVar()
            self.render_calls = 0
            self.translate_calls: list = []

        def current_interaction_mode(self):
            return InteractionMode.IDLE

        def render(self) -> None:
            self.render_calls += 1

        def _apply_scene_placement_translate_handle(self, *args, **kwargs) -> None:
            # Sentinel: the fixed click path must never reach this.
            self.translate_calls.append((args, kwargs))

    mock = _MockInspector()
    widget = PlacementTranslateWidget(mock)
    event = InteractionEventData(
        event_type="mouse_press",
        actor_key="placement_move::S6::z",
        pick_target=PickTarget.PLACEMENT_TRANSLATE,
        target_payload=(6, "z", 5.0),
    )
    try:
        bid = float(widget.can_process(event))
    except Exception as exc:
        bid = -1.0
        notes.append(f"FAIL: PlacementTranslateWidget.can_process raised {exc!r}")
        passed = False
    if bid < 0.0:
        notes.append(f"FAIL: PlacementTranslateWidget does not bid on a placement-translate click (bid={bid})")
        passed = False
    try:
        consumed = widget.process(event)
    except Exception as exc:
        consumed = None
        notes.append(f"FAIL: PlacementTranslateWidget.process raised {exc!r}")
        passed = False
    if consumed is not True:
        notes.append(f"FAIL: PlacementTranslateWidget.process did not consume the click (returned {consumed!r})")
        passed = False
    if mock.translate_calls:
        notes.append(f"FAIL: a bare click applied {len(mock.translate_calls)} placement translate(s) — the slide must be hold-drag only")
        passed = False
    if "move handle" not in mock.status_var.value.lower():
        notes.append(f"FAIL: a slide-handle click gave no hold-drag hint (status={mock.status_var.value!r})")
        passed = False

    if verbose:
        notes.append(
            "checked: hover pick set includes the move handle; both hover paths "
            "highlight it; click no longer translates (source + mock-widget behaviour)"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] bugs/0019: slide handle hover-highlights; bare click does not slide/retrace")
        return 0
    print("[FAIL] bugs/0019 slide-handle hover/click guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
