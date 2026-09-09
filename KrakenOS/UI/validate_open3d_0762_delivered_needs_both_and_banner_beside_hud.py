"""Guard for bugs/0762 -- "delivered" needs BOTH residuals, and the solve banner sits beside the
system HUD.

Flag 20260909_202712_834: "Surprisingly, image still not landed on sensor." The banner read
"the lens did not move -- the field was already delivered" with the image 5.932 mm in front of
the sensor -- the same shape bugs/0761 was meant to close.

bugs/0761 gated idempotence on the FIRST-ORDER residual. That is precisely the reading that can
disagree with the real folded trace (bugs/0745). "Delivered" now requires BOTH the first order
and the MEASURED focus to say the image lands; whichever is worse decides.

Also here, at the user's request: "Can also position the solve banner beside the Magnification,
Resolution banner, side by side?" The offset is the HUD's own RENDERED width, asked of VTK each
update -- the HUD grows with its content, so a fixed x would overlap exactly when the text
matters most. Note vtkTextActor.GetSize takes an OUTPUT array; calling it with one argument
raises, which silently left the banner stacked on the first cut (caught by rendering it, not by
reading the code).

Checks (display-free except where noted):
  A  a scene whose TRACED focus is off is not "already delivered", even when the first order says
     it lands -- the flagged shape;
  B  the first-order gate still works, and both-land still short-circuits;
  C  a scene with no measurement yet does not block on a missing reading;
  D  the banner asks the HUD for its rendered width with the two-argument GetSize, and falls back
     to the stacked anchor rather than running off the right edge.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0762_delivered_needs_both_and_banner_beside_hud
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace


class _Ed:
    def __init__(self, first_order, traced):
        self.rows = []
        self.camera_focus_stage = None
        self._fo = first_order
        if traced is not None:
            self.__dict__["_focused_image_plane_info"] = {"offset_mm": traced}

    def _current_finite_paraxial_magnification(self):
        return 0.7314

    def _folded_conjugate_gaps_for_magnification(self, m):
        return {"image_delta": self._fo}

    def _current_camera_sensor_active_mm(self):
        return (23.04, 23.04)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService as Q

    def delivered(fo, tr):
        return Q(SimpleNamespace(editor=_Ed(fo, tr)))._fov_already_delivered(11.52, 15.75)

    ok(delivered(0.02, 5.932) is None,
       "A1: first order says it lands but the TRACE says 5.932 mm out -> NOT delivered (the "
       "flagged case, which bugs/0761's first-order-only gate waved through)")
    ok(delivered(0.02, 0.153) is None,
       "A2: even one pixel of depth of focus out is not delivered")
    ok(delivered(6.276, 0.03) is None,
       "B1: the first-order gate still refuses on its own (bugs/0761 intact)")
    ok(delivered(0.02, 0.03) is not None,
       "B2: both land -> still short-circuits, so a genuine re-request is still a no-op")
    ok(delivered(0.02, None) is not None,
       "C1: no measurement yet does not block -- a missing reading is not evidence of a miss")

    src = inspect.getsource(Q._fov_already_delivered)
    ok('_focused_image_plane_info' in src and "offset_mm" in src,
       "C2: it reads the MEASURED focus the scene already publishes")
    ok(src.find("_folded_conjugate_gaps_for_magnification") < src.find("_focused_image_plane_info"),
       "C3: both readings are consulted, first order then measured")

    # ---- D: the banner placement ---------------------------------------------------------------
    from KrakenOS.UI import open3d_inspector as oi

    place = inspect.getsource(oi.Kraken3DInspector._place_solve_banner_beside_system_hud)
    ok("hud.GetSize(renderer, size)" in place,
       "D1: GetSize is called with its OUTPUT array -- the one-argument form raises and silently "
       "left the banner stacked")
    ok("size = [0, 0]" in place,
       "D2: the output array is allocated before the call")
    ok("x_norm > 0.72" in place and "0.012, 0.83" in place,
       "D3: it falls back to the stacked anchor rather than running off the right edge")
    ok("_system_info_hud_actor" in place,
       "D4: the offset comes from the HUD's own rendered width, not a guessed constant")
    caller = inspect.getsource(oi.Kraken3DInspector._update_solve_refresh_banner) \
        if hasattr(oi.Kraken3DInspector, "_update_solve_refresh_banner") \
        else inspect.getsource(oi.Kraken3DInspector._update_solve_refusal_banner)
    ok("_place_solve_banner_beside_system_hud(actor)" in caller,
       "D5: and it runs on every banner update, so it tracks a HUD that changes size")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0762 delivered-needs-both + banner-beside-HUD validation PASSED")
        return 0
    print("0762 validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
