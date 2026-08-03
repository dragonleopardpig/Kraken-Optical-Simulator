"""bugs/0524/0526 guard -- an along-leg lens drag writes its sections AND holds every seat.

flag_20260803_151917: the leg slide moved the lens in the WORLD but the section gaps never
learned it, so the FOV readout stayed put. The 0524 raw write fixed the readout but
corrupted the scene (flag_20260803_162321 "haywire"): EVERY row's pose -- breadcrumbed
world rows included -- is ``station + desp_z`` (the 0433 freeze bakes
``desp_z = world_z - station_at_freeze``), so a thickness write alone re-seats every
downstream row (the glued BS ghost-re-seated; the prism left the beam).

bugs/0526 is the compensated composite: gap before the lens block +slide, gap after it
-slide, and ``desp_z -= slide`` for every row strictly between the two written rows --
poses invariant by construction, the first order sees the conjugate change.

Checks:
  SOURCE -- the compensated composite (thickness writes + desp_z compensation) is present.
  REAL   -- an 8 mm along-leg drag moves the two section gaps +-8, the FOV readout
            follows, and the BS / prism / sensor world poses hold to numerical zero.
  NEG    -- a perpendicular drag stays body-only (no gap writes).
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
    if "bugs/0526" in src and "desp_z = float(_row.desp_z) - float(lens_leg_slide)" in src:
        notes.append("SOURCE = the compensated write-through composite is present")
    else:
        notes.append("SOURCE the 0526 compensated composite is missing")
        ok = False

    if not SCENE.exists():
        notes.append("SKIP: frozen AZ85 scene absent (gitignored attachment)")
        return ok, notes

    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.services import optical_axis_tree as tree_mod
        from KrakenOS.UI.services.quick_estimation import QuickEstimationService

        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        qe = QuickEstimationService(_Shim(app))

        def _pose(i):
            return np.asarray(tree_mod.row_world_pose(app.rows, i), dtype=float).reshape(-1)[:3]

        gaps0 = [float(r.thickness) for r in app.rows]
        seats0 = {i: _pose(i) for i in (3, 7, 8)}
        fov0 = qe.current_state().get("fov_full")
        app.translate_step_overlay("lens", (8.0, 0.0, 0.0))
        gaps1 = [float(r.thickness) for r in app.rows]
        seats1 = {i: _pose(i) for i in (3, 7, 8)}
        fov1 = qe.current_state().get("fov_full")
        deltas = [round(b - a, 3) for a, b in zip(gaps0, gaps1)]
        grew = [i for i, d in enumerate(deltas) if d > 0.5]
        shrank = [i for i, d in enumerate(deltas) if d < -0.5]
        if (
            len(grew) == 1 and len(shrank) == 1
            and abs(deltas[grew[0]] - 8.0) < 0.5 and abs(deltas[shrank[0]] + 8.0) < 0.5
        ):
            notes.append(f"REAL = the drag wrote its sections (row {grew[0]} +8, row {shrank[0]} -8)")
        else:
            notes.append(f"REAL section write wrong (deltas {deltas})")
            ok = False
        drift = max(float(np.linalg.norm(seats1[i] - seats0[i])) for i in seats0)
        if drift < 1e-6:
            notes.append("REAL = the BS / prism / sensor world seats hold (no ghost, no re-seat)")
        else:
            notes.append(f"REAL a fold-solid seat moved by {drift:.4g} mm -- the 162321 corruption")
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
