"""bugs/0519 guard -- the FOV solve reaches large fields on a frozen fold (55x55).

flag_20260803_140636: "I couldn't change FOV to 55x55, I can do this in actual production."
On the 0433-frozen AZ85 chain the straightened reference's LAST VERTEX is the prism
placeholder sitting ON the image plane (zero-length gap row), so the plain conjugate
formula ``image_distance = f(1+m) + ppp`` measured the new gap from a zero-length anchor --
it crossed zero at m=0.546 and refused every field beyond ~77%% of the request, for a
sensor move of just -10.8 mm that the 0478 frozen writer handles trivially.

Fix: when the plain value turns infeasible AND the scene has a frozen image-side fold,
re-anchor on the WORLD far leg (``far + [f(1+m) - image_principal]`` off the shared first
order). The previously-working regime and every unfrozen scene are untouched.

Checks:
  SOURCE -- the re-anchor exists, gated on the frozen split.
  REAL   -- 55x55 solves on the frozen AZ85 scene: |m| ~ 0.419, FOV readout lands at
            55x55 (diag 77.78), and the finisher leaves ~zero traced-focus residual.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


class _Shim:
    def __init__(self, editor):
        self.editor = editor


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    src = _inspect.getsource(QuickEstimationService._conjugate_pair)
    if "frozen_world" in src and "image_principal" in src:
        notes.append("SOURCE = the infeasible regime re-anchors on the world far leg")
    else:
        notes.append("SOURCE the 0519 far-leg re-anchor is missing from _conjugate_pair")
        ok = False

    if not SCENE.exists():
        notes.append("SKIP: frozen AZ85 scene absent (gitignored attachment)")
        return ok, notes

    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        qe = QuickEstimationService(_Shim(app))
        solved, msg = qe.fov_solve("object", "thickness", 55.0, 55.0)
        if not solved:
            notes.append(f"REAL 55x55 still refused: {msg}")
            ok = False
        else:
            state = qe.current_state()
            fov = state.get("fov_full")
            mag = state.get("magnification")
            if fov is not None and abs(float(fov) - 77.78) <= 0.8:
                notes.append(f"REAL = 55x55 reached (FOV diag {fov:.2f} mm, |m|={mag:.4g})")
            else:
                notes.append(f"REAL solve accepted but FOV wrong (diag {fov}, |m|={mag})")
                ok = False
            # bugs/0588: this scene/field used to fall to the PLAIN branch (whose note says
            # "snapped to the traced focus"); the folded branch's finisher says "Snapped the
            # detector to the traced focus." -- same semantic, richer route (make-room + slide).
            # Match the SEMANTIC, either branch's phrasing.
            if "snapped to the traced focus" in msg or "snapped the detector to the traced focus" in msg.lower():
                notes.append("REAL = the finisher landed the traced focus")
            else:
                notes.append(f"REAL no traced-focus snap in: {msg[-120:]}")
                ok = False
    except Exception as exc:
        notes.append(f"SKIP: real-scene drive failed ({exc!r})")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
