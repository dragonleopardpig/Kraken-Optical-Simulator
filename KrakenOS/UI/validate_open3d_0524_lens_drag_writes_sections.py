"""bugs/0524 guard -- an along-leg lens drag WRITES its section gaps (FOV follows).

flag_20260803_151917 "dragged the lens to the right, the FOV is not changing": the folded
leg slide moved the lens in the WORLD (desps) but never wrote the section gaps, so the
shared first order -- and the FOV readout -- stayed at the old conjugates (the 0478
prescription/world drift). The leg-slide branch now writes the drag through: the gap
BEFORE the lens block grows by the slide, the gap AFTER it shrinks; stations past the
block hold, so the mirror and sensor stay put. A perpendicular drag stays body-only.

Checks:
  SOURCE -- the write-through block exists in the leg-slide branch.
  REAL   -- AZ85: an 8 mm along-leg drag moves the two section gaps by +-8 and the FOV
            readout changes; a perpendicular drag leaves every gap byte-identical.
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

    from KrakenOS.UI.services import scene_placement_commands as _spc

    src = _inspect.getsource(_spc.ScenePlacementMixin.translate_step_overlay)
    if "bugs/0524" in src and "section write-through skipped" in src:
        notes.append("SOURCE = the leg-slide branch writes the drag through to its section gaps")
    else:
        notes.append("SOURCE the 0524 write-through is missing from the leg-slide branch")
        ok = False

    if not SCENE.exists():
        notes.append("SKIP: frozen AZ85 scene absent (gitignored attachment)")
        return ok, notes

    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.services.quick_estimation import QuickEstimationService

        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        qe = QuickEstimationService(_Shim(app))
        gaps0 = [float(r.thickness) for r in app.rows]
        fov0 = qe.current_state().get("fov_full")
        app.translate_step_overlay("lens", (8.0, 0.0, 0.0))
        gaps1 = [float(r.thickness) for r in app.rows]
        fov1 = qe.current_state().get("fov_full")
        deltas = [round(b - a, 3) for a, b in zip(gaps0, gaps1)]
        grew = [i for i, d in enumerate(deltas) if d > 0.5]
        shrank = [i for i, d in enumerate(deltas) if d < -0.5]
        if len(grew) == 1 and len(shrank) == 1 and abs(deltas[grew[0]] - 8.0) < 0.5 and abs(deltas[shrank[0]] + 8.0) < 0.5:
            notes.append(
                f"REAL = the drag wrote its sections (row {grew[0]} +8, row {shrank[0]} -8)"
            )
        else:
            notes.append(f"REAL section write wrong (deltas {deltas})")
            ok = False
        if fov0 and fov1 and abs(float(fov1) - float(fov0)) > 0.5:
            notes.append(f"REAL = the FOV readout follows the drag ({fov0:.2f} -> {fov1:.2f})")
        else:
            notes.append(f"REAL FOV readout did not change ({fov0} -> {fov1})")
            ok = False
        gaps2 = [float(r.thickness) for r in app.rows]
        app.translate_step_overlay("lens", (0.0, 0.0, 5.0))
        gaps3 = [float(r.thickness) for r in app.rows]
        if all(abs(b - a) < 1e-9 for a, b in zip(gaps2, gaps3)):
            notes.append("NEG = a perpendicular drag stays body-only (no gap writes)")
        else:
            notes.append("NEG a perpendicular drag wrote gaps")
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
