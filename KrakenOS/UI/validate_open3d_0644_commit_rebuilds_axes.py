"""Guard for bugs/0644 — a STEP-overlay COMMIT re-derives the optical axes.

flag_20260824_164820: "the 2nd optical axis stays after the BS+LED+illuminator shifted.
The optical axis should be generated from the BS. Seems the algorithm separate BS with
optical axis generation." Measured from the two flags: the promoted BS row moved +101 mm in
z (row actor bounds 146.7..202.6 -> 247.7..303.6) while the drawn axis records stayed
BYTE-IDENTICAL.

Cause: `translate_step_overlay` ended with `if refresh:` -- but `refresh` is the caller's
RETRACE appetite (the gizmo release passes `physics_requested`, False with Live Mode off).
The optical axes are DISPLAY geometry derived from the model, so the rebuild was skipped
while `_translate_step_overlay_actors` had already carried the bodies live.

Fix: `if refresh or record_history:` -- a COMMIT always re-derives the display; the
per-frame drag calls (record_history=False) still skip it so dragging stays smooth.

Checks (display-free, source contracts):
  A  the commit gate includes record_history (a commit rebuilds even with retrace off).
  B  the per-frame carry/drag call sites still pass record_history=False (smooth drag).
  C  the gizmo-release COMMIT passes record_history=True (so it is covered by A).

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0644_commit_rebuilds_axes
"""

from __future__ import annotations

import inspect
import re


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import scene_placement_commands as spc

    src = inspect.getsource(spc.ScenePlacementMixin.translate_step_overlay)

    # ---------------------------------------------------------------- A: the commit gate
    gate = re.search(r"if\s+refresh\s+or\s+record_history\s*:\s*\n\s*self\._refresh_open_3d_views\(", src)
    if gate is None:
        ok = False
        notes.append(
            "FAIL: A (bugs/0644): translate_step_overlay does not rebuild the display on a COMMIT "
            "-- with Live Mode off the optical axes stay at the pre-drag pose while the bodies move"
        )
    else:
        notes.append("PASS: A: a commit re-derives the display even when no retrace is requested")

    # ---------------------------------------------------------------- B: per-frame stays cheap
    from KrakenOS.UI import open3d_inspector as insp_module

    insp_src = inspect.getsource(insp_module)
    per_frame = re.findall(r"translate_step_overlay\((?:[^()]|\([^()]*\))*record_history=False", insp_src)
    if len(per_frame) < 3:
        ok = False
        notes.append(
            f"FAIL: B (bugs/0644): only {len(per_frame)} per-frame drag call(s) pass "
            "record_history=False -- a live drag would now rebuild the scene every frame"
        )
    else:
        notes.append(f"PASS: B: {len(per_frame)} per-frame drag call sites still skip the rebuild")

    # ---------------------------------------------------------------- C: the commit call site
    finish = inspect.getsource(insp_module.Kraken3DInspector._finish_step_translate_drag)
    if "record_history=True" not in finish:
        ok = False
        notes.append(
            "FAIL: C (bugs/0644): the gizmo-release commit no longer passes record_history=True, "
            "so the bugs/0644 rebuild gate never fires for it"
        )
    else:
        notes.append("PASS: C: the gizmo-release commit is marked as a commit (record_history=True)")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Commit-rebuilds-axes validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
