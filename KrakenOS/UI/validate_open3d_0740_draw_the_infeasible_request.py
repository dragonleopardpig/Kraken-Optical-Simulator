"""Guard for bugs/0740 -- draw an infeasible field request; never apply it.

User: "the solve evolved from No Crash + Image in front of sensor to Crash + No image formed. I
don't know what to trust now."

bugs/0732's auto-force applied a move that buried the lens in vendor hardware; the crashed scene
blocked the rays, bugs/0737 then correctly drew no focus plane, and a scene that traced a moment
earlier was left showing nothing. A SAVED crash persisted -- om05a shipped with its lens 11.03 mm
inside RA mirror 1, so every later solve reported a collision it had not caused (penetration minus
move was a constant 13.03 mm).

Now the geometry is kept and the REQUEST is drawn: a ghost lens where the field demands, inside the
body that blocks it, plus the DELIVERED object field beside the requested one. The user rejected a
text-only version in advance: "human being is influence by picture stronger than words."

Checks (display-free):
  A  the solve keeps the geometry: no forced move survives anywhere in fov_solve, the branch still
     fires only on the room refusal, it stashes a ghost, and it reports failure.
  B  the room refusal is matched STRUCTURALLY, not by its prose -- rewording the sentence once
     silently stopped the ghost being drawn -- and the structured stash is cleared every attempt.
  C  the ghost info carries what the picture needs, and is cleared by a solve that fits.
  D  the drawing: the ghost barrel and the delivered object field are drawn on every refresh,
     NOT behind the detector-overlay toggle, and draw nothing without a ghost.
  E  a zero clearance is reported as "none", not as 1.203e-11 mm.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0740_draw_the_infeasible_request
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    solve = inspect.getsource(QuickEstimationService.fov_solve)
    branch = solve.find("if not ok and not force:")

    # ---- A: the geometry survives --------------------------------------------------------------
    ok(
        "force=True" not in solve,
        "A1: no forced move survives anywhere in fov_solve -- an infeasible request never "
        "mutates the scene (bugs/0732's auto-force is superseded)",
    )
    window = solve[branch: branch + 2400] if branch >= 0 else ""
    ok(
        branch >= 0 and "self.editor._fov_solve_ghost_info = self._infeasible_fov_ghost_info" in window,
        "A2: the branch stashes a ghost for the scene to draw",
    )
    ok(
        "ok = False" in window,
        "A3: and still reports failure, so the refusal banner paints",
    )
    plain = solve.find("_apply_conjugate_pair(semi, image_semi / correction")
    ok(
        0 <= plain < branch,
        "A4: the plain attempt still runs first -- a field that FITS is applied untouched",
    )

    # ---- B: structural detection, not prose ----------------------------------------------------
    ok(
        'str(refusal_info.get("kind")) == "physical_room"' in solve
        and "physical room is left before its body reaches" not in solve,
        "B1: the room refusal is matched on the STRUCTURED stash, not on its sentence "
        "(rewording the sentence once silently stopped the ghost being drawn)",
    )
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    mover = inspect.getsource(ScenePlacementMixin.translate_lens_block_along_leg)
    ok(
        '"kind": "physical_room"' in mover
        and all(k in mover for k in ('"required_mm"', '"room_mm"', '"obstacle"', '"leg_unit"')),
        "B2: the move primitive stamps the numbers the picture needs (how far, how much room, "
        "what is in the way, along which leg)",
    )
    ok(
        "self._lens_move_refusal_info = None" in mover,
        "B3: and clears it at entry, so a later attempt can never inherit a stale ghost",
    )
    ok(
        "self.editor._fov_solve_ghost_info = None" in solve,
        "B4: the solve clears the ghost at entry -- a request that now fits must not leave a "
        "ghost lens standing from the previous one",
    )

    # ---- C: the ghost payload ---------------------------------------------------------------------
    ghost_src = inspect.getsource(QuickEstimationService._infeasible_fov_ghost_info)
    for key in ("requested_fov_wh", "required_move_mm", "room_mm", "shortfall_mm", "obstacle",
                "leg_unit", "delivered_fov_wh", "delivered_m"):
        ok(f'"{key}"' in ghost_src, f"C[{key}]: the ghost carries {key}")
    ok(
        'str(info.get("kind")) != "physical_room"' in ghost_src and "return None" in ghost_src,
        "C1: any OTHER refusal returns no ghost, so every other refusal keeps its own reporting",
    )

    # ---- D: the drawing ----------------------------------------------------------------------------
    from KrakenOS.UI.services.detector_coverage_overlay import DetectorCoverageOverlayService

    barrel = inspect.getsource(DetectorCoverageOverlayService.add_infeasible_fov_ghost)
    ok(
        '_fov_solve_ghost_info' in barrel and "return 0" in barrel,
        "D1: the ghost draws nothing unless a solve stashed one",
    )
    ok(
        "_GHOST_COLLISION" in barrel and "_circle_points" in barrel,
        "D2: it draws a lens barrel in collision colour at the demanded position",
    )
    field = inspect.getsource(DetectorCoverageOverlayService._add_delivered_object_field)
    ok(
        "_rect_points" in field and "delivered" in field,
        "D3: and the DELIVERED object field beside the requested band -- the half of the picture "
        "that still read as 'fine' (user: 'if the lens stay + Object FOV changed + Image "
        "detached, what is visually wrong, am I right?')",
    )
    ok(
        "labelled" in field,
        "D4: labelled once, not once per band (two labels landed on top of each other)",
    )
    from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService

    refresh = inspect.getsource(Open3DSceneRefreshService)
    hook = refresh.find("_add_infeasible_fov_ghost_overlay()")
    toggle = refresh.find("if self.show_detector_overlays_var.get():")
    ok(
        hook >= 0 and "_update_solve_refusal_banner()" in refresh,
        "D5: the ghost is refreshed with the scene, beside the solve banner",
    )
    ok(
        hook >= 0 and (toggle < 0 or hook > toggle),
        "D6: and NOT inside the detector-overlay toggle -- a refusal the user has to switch on "
        "is a refusal they will not see",
    )

    # ---- E: a zero clearance reads as none -----------------------------------------------------------
    from KrakenOS.UI.services.system_info_hud import format_solve_refusal_lines

    lines = format_solve_refusal_lines(
        {"requested_fov_wh": [10.5, 10.5], "lens_move_needed_mm": -13.65,
         "leg_room_mm": 1.203e-11, "reason": "blocked"}
    )
    ok(
        any("no room at all" in line for line in lines)
        and not any("e-11" in line for line in lines),
        f"E1: a zero clearance reads as 'no room at all', not '1.203e-11 mm' ({lines[1] if len(lines) > 1 else None!r})",
    )
    real = format_solve_refusal_lines(
        {"requested_fov_wh": [5.0, 5.0], "lens_move_needed_mm": -178.8,
         "leg_room_mm": 145.5, "reason": "blocked"}
    )
    ok(
        any("145.5" in line and "short by 33.3" in line for line in real),
        "E2: a REAL clearance is still printed with its shortfall",
    )
    ok(
        "no physical room is left at all" in mover,
        "E3: and the refusal text itself says it too",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0740 draw-the-infeasible-request validation PASSED")
        return 0
    print("0740 draw-the-infeasible-request validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
