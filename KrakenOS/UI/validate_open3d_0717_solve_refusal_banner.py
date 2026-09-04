"""Guard for bugs/0717 -- USER DIRECTIVE: "The UI shouldn't silently fail and
display as though it is working. If it crashes, alert the customer with all
parameters shown in the 3D scene. ... give an option to bypass constraint and
let user actually see the lens crashes to other component."

Checks:
  A  formatter behavior: empty input -> no banner; a refusal dict renders every
     number (request, target |m|, lens move vs room, delivered, hint); a forced
     negative penetration renders the PENETRATES line.
  B  wiring pins: fov_solve clears the stash at entry and stashes on refusal;
     the lens-leg slide carries the force bypass on BOTH room checks; the
     banner paints from the scene refresh; the Device menu offers the force
     entry keyed on the stash.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0717_solve_refusal_banner
"""

from __future__ import annotations

import inspect


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.system_info_hud import format_solve_refusal_lines

    ok(
        format_solve_refusal_lines(None) == [] and format_solve_refusal_lines({}) == [],
        "A1: no refusal -> no banner",
    )
    lines = format_solve_refusal_lines(
        {
            "requested_fov_wh": (21.0, 21.0),
            "target_m": 1.097,
            "lens_move_needed_mm": -171.3,
            "leg_room_mm": 56.4,
            "delivered_m": 0.366,
            "delivered_fov_wh": (63.0, 63.0),
            "reason": "that field needs the lens further from the object",
        }
    )
    text = "\n".join(lines)
    ok(
        "SOLVE REFUSED" in text
        and "21" in text
        and "1.097" in text
        and "-171.3" in text
        and "56.4" in text
        and "0.366" in text
        and "Force FOV" in text,
        f"A2: the banner carries request/target/move/room/delivered/hint ({len(lines)} lines)",
    )
    forced = "\n".join(
        format_solve_refusal_lines(
            {"forced_penetration_mm": -36.4, "forced_obstacle": "RA mirror 1 (50 mm)"}
        )
    )
    ok(
        "PENETRATES RA mirror 1 (50 mm) by 36.4 mm" in forced,
        "A3: a forced negative clearance renders the penetration line",
    )

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    solve_src = inspect.getsource(QuickEstimationService.fov_solve)
    ok(
        "self.editor._fov_solve_refusal_info = None" in solve_src
        and "requested_fov_wh" in solve_src
        and "force: bool = False" in solve_src,
        "B1: fov_solve clears the stash at entry, enriches on refusal, threads force",
    )
    apply_src = inspect.getsource(QuickEstimationService._apply_conjugate_pair)
    ok(
        "lens_move_needed_mm" in apply_src
        and "slide_lens_block_along_its_leg(\n                        float(folded[\"object_delta\"]), force=force" in apply_src,
        "B2: the conjugate writer stashes the core refusal and threads force to the slide",
    )

    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    slide_src = inspect.getsource(ScenePlacementMixin.slide_lens_block_along_its_leg)
    ok(
        slide_src.count("if force") >= 2 and "FORCED past the room check" in slide_src,
        "B3: the lens-leg slide bypasses BOTH room checks under force (overlap intended)",
    )

    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services import open3d_scene_refresh

    ok(
        hasattr(Kraken3DInspector, "_update_solve_refusal_banner")
        and "_update_solve_refusal_banner()" in inspect.getsource(open3d_scene_refresh),
        "B4: the banner paints from the scene refresh (survives every rebuild)",
    )

    from KrakenOS.UI.panels.open3d_step_admin import Open3DStepAdminPanel

    menu_src = inspect.getsource(Open3DStepAdminPanel._show_inspection_part_context_menu)
    ok(
        "Force FOV" in menu_src and "_fov_solve_refusal_info" in menu_src,
        "B5: the Device menu offers the force entry when a refusal is stashed",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0717 solve-refusal banner validation PASSED")
        return 0
    print("0717 solve-refusal banner validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
