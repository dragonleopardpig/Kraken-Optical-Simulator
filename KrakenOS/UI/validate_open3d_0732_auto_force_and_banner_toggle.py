"""Guard for bugs/0732 -- apply the forced move without a second click, and let the banner go.

Two live asks on build ce8c82d3:
  * "There is no need to have additional click on Force, just do it." -- a COLLISION refusal used
    to stop and wait for the user to pick "Force FOV (show collision)" from a right-click menu.
  * "I think the red banner is kind of static on the screen, blocking the view."

Now a collision applies the move directly (the banner already says the lens penetrates and by how
much, and bugs/0718 defers the trace on a crashed geometry), and the banner has an off switch,
a lighter background, and no longer repeats a finished FORCED-fits result beside a no-op.

Measured on om05a: FOV 5 x 5 needs 192.3 mm of leg against 158.9 mm of room. Before it refused;
now it returns ok=True with "FORCED SOLVE APPLIED -- the lens PENETRATES hardware", 21.53 mm of
penetration, the cap note, and the trace deferred.

Checks (display-free):
  A  the escalation is wired to the ROOM refusal only, runs after the plain attempt, and says the
     move was applied without a Force click.
  B  the trace deferral follows what actually happened (a forced crash defers even when the
     caller passed force=False).
  C  the banner has a toggle var, a menu entry, and honours it; the background is lighter.
  D  a no-op keeps only a forced CRASH banner -- a finished "fits" result is not repeated beside
     "the lens did not move".

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0732_auto_force_and_banner_toggle
"""

from __future__ import annotations

import inspect


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    solve = inspect.getsource(QuickEstimationService.fov_solve)

    # ---- A: the escalation -------------------------------------------------------------------
    # bugs/0735 changed the image semi from the diagonal sensor semi to the rectangular target
    plain_at = solve.find("ok, msg = self._apply_conjugate_pair(semi, image_semi / correction, force=force)")
    escalate_at = solve.find("if not ok and not force:")
    ok(
        0 <= plain_at < escalate_at,
        "A1: the escalation runs AFTER the plain attempt (a solve that fits never forces)",
    )
    # bugs/0740 SUPERSEDES the auto-force half of this bug. Applying an infeasible move destroys
    # the working geometry: the crashed scene blocks the rays, bugs/0737 then correctly draws no
    # focus plane, and the user gets "Crash + no image formed" from a scene that traced a moment
    # earlier -- and a SAVED crash persists (om05a shipped with its lens 11.03 mm inside RA
    # mirror 1, which made every later solve report a collision it had not caused). The branch
    # still fires only on the room refusal; it now draws the request instead of applying it.
    ok(
        'str(refusal_info.get("kind")) == "physical_room"' in solve,
        "A2: it still acts only on the ROOM refusal -- the real collision, not any refusal -- "
        "and detects it STRUCTURALLY, not by matching the refusal's prose (bugs/0740)",
    )
    window = solve[escalate_at: escalate_at + 2400]
    ok(
        "self.editor._fov_solve_ghost_info = self._infeasible_fov_ghost_info" in window
        and "force=True" not in solve,
        "A3: an infeasible field is DRAWN, not applied -- there is no forced move left anywhere "
        "in the solve (bugs/0740)",
    )
    ok(
        "ok = False" in window,
        "A4: and the solve still reports failure, so the refusal banner paints",
    )

    # ---- B: the trace deferral ------------------------------------------------------------------
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    entry = inspect.getsource(LayoutTableWorkbenchMixin.solve_fov_to_inspection_face)
    ok(
        "solve_banner_outcome" in entry and 'crashed = solve_banner_outcome' in entry
        and "defer_trace=bool(ok and (force or crashed))" in entry,
        "B1: the trace is deferred on an ACTUAL forced crash, not just on the force flag "
        "(bugs/0718: a crashed geometry hangs the non-sequential trace)",
    )

    # ---- C: the banner ---------------------------------------------------------------------------
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    banner = inspect.getsource(Kraken3DInspector._update_solve_refusal_banner)
    ok(
        "show_solve_banner_var" in banner and 'text = ""' in banner,
        "C1: the banner honours its toggle (hidden = no text, so the actor is removed)",
    )
    ok(
        "SetBackgroundOpacity(0.78)" in banner,
        "C2: the background is lighter so the scene shows through",
    )
    inspector_source = inspect.getsource(Kraken3DInspector)
    ok(
        "self.show_solve_banner_var = tk.BooleanVar(value=True)" in inspector_source
        and 'label="Solve / focus banner"' in inspector_source
        and "def _on_solve_banner_toggled" in inspector_source,
        "C3: the toggle exists, defaults ON, and has a menu entry that re-renders",
    )
    # bugs/0736 (user: "I can't find the off button for the banner in 3D UI"): it was only in the
    # image-plane ANALYSES submenu. A display switch belongs in the Overlays sweep.
    from KrakenOS.UI.panels import open3d_top_controls

    ok(
        'MenuCheckbutton("Solve banner", self.inspector.show_solve_banner_var' in inspect.getsource(open3d_top_controls),
        "C4: the toggle is in the top toolbar's Overlays menu, where the other drawn-over-scene "
        "switches live -- not buried in an analyses submenu",
    )

    # ---- D: no stale FORCED-fits beside a no-op ------------------------------------------------------
    ok(
        'if str(solve_banner_outcome(_prior)) == "forced_crash":' in solve,
        "D1: a no-op preserves ONLY a forced crash (an overlap still on screen), never a "
        "finished 'fits' result",
    )
    from KrakenOS.UI.services.system_info_hud import solve_banner_outcome

    fits = {"forced_penetration_mm": 8.9, "forced_moved_mm": 138.6, "forced_obstacle": "RA mirror 1"}
    crash = {"forced_penetration_mm": -21.5, "forced_moved_mm": 180.5, "forced_obstacle": "RA mirror 1"}
    ok(
        solve_banner_outcome(fits) == "forced_fits" and solve_banner_outcome(crash) == "forced_crash",
        "D2: the two are distinguishable, so the rule above can tell them apart",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0732 auto-force + banner-toggle validation PASSED")
        return 0
    print("0732 auto-force + banner-toggle validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
