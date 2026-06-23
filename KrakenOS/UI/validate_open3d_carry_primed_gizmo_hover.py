"""Guard for bugs/0117 — a carry-primed STEP (a freshly imported LED) must be
able to hover-highlight its move/rotate gizmo, not only its edges.

Regression context
------------------
A freshly imported/selected STEP is carry-primed (`_step_carry_active_label` is
set), so `_step_carry_label()` is non-None at idle. In `_on_mouse_move` that
makes `target_label` non-None, which skips the idle-hover block -- the only one
that hover-picks gizmo handles via the overlay-aware
`_passive_hover_pick_rotation_handle`. The carry-primed branch instead picked the
MAIN renderer (`self._picker` / `self._renderer`), which is blind to the gizmo
overlay layer (bugs/0112: handles register only on `_gizmo_overlay_renderer`), so
the four handle-map lookups always returned None and the gizmo never
hover-highlighted -- "can highlight LED edges, but not the gizmo".

Fix: in the carry-primed branch, resolve the gizmo maps from an overlay-aware
`_passive_hover_pick_rotation_handle` pick (gated on a `carry_primed_target` flag
so the explicit axis-pick / led-edge hover paths are unchanged), reading all four
handle maps with the overlay `handle_key`.

This guard is display-free (source contracts) because an embedded-VTK hover pick
cannot be driven headless; the gold highlight itself is verified in-app.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_carry_primed_gizmo_hover

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import re


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    from KrakenOS.UI.services.open3d_interaction import Open3DInteractionService

    try:
        move_src = inspect.getsource(Open3DInteractionService._on_mouse_move)
    except Exception as exc:
        move_src = ""
        notes.append(f"FAIL: cannot read _on_mouse_move source: {exc!r}")
        passed = False

    try:
        hover_src = inspect.getsource(Open3DInteractionService._passive_hover_pick_rotation_handle)
    except Exception as exc:
        hover_src = ""
        notes.append(f"FAIL: cannot read _passive_hover_pick_rotation_handle source: {exc!r}")
        passed = False

    # A. The carry branch must set a carry_primed_target flag exactly where it
    #    adopts the carry label (so an explicit axis-pick target is NOT treated
    #    as carry-primed).
    if move_src:
        if "carry_primed_target = False" not in move_src:
            notes.append("FAIL: _on_mouse_move never initialises carry_primed_target = False")
            passed = False
        if not re.search(r"target_label = str\(carry_label\)\s+carry_primed_target = True", move_src):
            notes.append(
                "FAIL: carry_primed_target is not set to True alongside the carry-label adoption "
                "(target_label = str(carry_label)) -- the gizmo-hover gate is wrong"
            )
            passed = False

    # B. The carry-primed branch must resolve the gizmo maps from the
    #    overlay-aware handle pick, gated on carry_primed_target, reading all four
    #    handle maps with handle_key.
    if move_src:
        if "if carry_primed_target:" not in move_src:
            notes.append("FAIL: the gizmo-hover overlay pick is not gated on carry_primed_target")
            passed = False
        if "handle_key, _handle_cell = self._passive_hover_pick_rotation_handle" not in move_src:
            notes.append(
                "FAIL: the carry-primed branch does not derive handle_key from "
                "_passive_hover_pick_rotation_handle (the overlay-aware pick)"
            )
            passed = False
        for map_name in (
            "_actor_step_rotate_map",
            "_actor_step_translate_map",
            "_actor_placement_rotate_map",
            "_actor_placement_move_map",
        ):
            if f"self.{map_name}.get(handle_key)" not in move_src:
                notes.append(
                    f"FAIL: the carry-primed gizmo branch reads {map_name} with the main-renderer "
                    f"actor_key, not the overlay handle_key -- the handle never hover-highlights"
                )
                passed = False

    # C. _on_mouse_move must hover-pick handles via the overlay-aware helper in
    #    BOTH the idle block and the carry-primed block (>= 2 references).
    if move_src:
        n_overlay_pick = move_src.count("_passive_hover_pick_rotation_handle")
        if n_overlay_pick < 2:
            notes.append(
                f"FAIL: _on_mouse_move calls _passive_hover_pick_rotation_handle {n_overlay_pick} "
                f"time(s); expected >= 2 (idle block + carry-primed block)"
            )
            passed = False

    # D. The handle pick helper must genuinely be overlay-aware (pick from the
    #    gizmo overlay renderer), else B above would be picking the wrong layer.
    if hover_src and "_gizmo_overlay_renderer" not in hover_src:
        notes.append(
            "FAIL: _passive_hover_pick_rotation_handle does not pick from _gizmo_overlay_renderer "
            "-- it is not overlay-aware, so the carry-primed fix would still miss the handles"
        )
        passed = False

    if verbose:
        notes.append(
            "checked: carry adoption sets carry_primed_target; the carry-primed hover branch "
            "resolves all four gizmo maps from the overlay-aware handle pick (handle_key); the "
            "helper picks from the gizmo overlay renderer; both hover branches use it"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] bugs/0117: a carry-primed STEP hover-highlights its gizmo (overlay-aware)")
        return 0
    print("[FAIL] bugs/0117 carry-primed gizmo-hover guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
