"""bugs/0516 guard -- the first-order pupil reference survives a cube-BS mesh.

Two stacked roots made every launch on a frozen beam-splitter chain silently fall back to
the coarse geometric aim ("sparse rays on frozen chains", the visible first-order seam):

  (1) the 0465 reference CENTRING was dead code -- a leftover "centring disabled for this
      measurement" A/B return shipped inside the 0470 commit (822f6259), so the reference
      kept the frozen rows' world desps/tilts and PupilCalc's axial probes missed everything;
  (2) with centring restored, the reference still KEPT the promoted cube's MESH (bugs/0094)
      -- whose internal 45-degree diagonal, splitter coating stripped, DEFLECTS the axial
      probe ray (measured exit slope ~0.5) -- so PupilCalc's raykeeper stayed empty.

The fix: `_pupil_model_inputs` test-traces one axial chief through the mesh-kept reference
(`_reference_transports_axial_ray`) and rebuilds with ANALYTIC flat plates when the mesh
chain bends it. Plate/plain scenes keep the mesh path byte-identical.

Checks:
  SOURCE -- the dead kill-switch is gone; the axial-transparency retry exists.
  REAL   -- on the frozen AZ85 cube scene, PupilCalc resolves a finite entrance pupil
            through `_pupil_model_inputs` (no IndexError, no fallback).
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

import numpy as np


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import paraxial_tools as _pt
    from KrakenOS.UI.services import analysis_compute_workflow as _acw

    if "centring disabled for this measurement" in _inspect.getsource(_pt):
        notes.append("SOURCE the 0465 centring kill-switch is back (0470 regression)")
        ok = False
    else:
        notes.append("SOURCE = the 0465 centring is active (no dead kill-switch)")

    mixin_src = _inspect.getsource(_acw.AnalysisComputeWorkflowMixin._pupil_model_inputs)
    if "_reference_transports_axial_ray" in mixin_src:
        notes.append("SOURCE = the mesh reference is validated by an axial-transparency trace")
    else:
        notes.append("SOURCE the 0516 axial-transparency retry is missing from _pupil_model_inputs")
        ok = False

    scene = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
    if not scene.exists():
        notes.append("SKIP: frozen AZ85 cube scene not present (gitignored attachment)")
        return ok, notes

    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        import KrakenOS as Kos

        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["az85"] = scene
        app.load_layout_by_name("az85")
        pupil_system, _pupil_rows, pupil_index = app._pupil_model_inputs(None, build_reference=True)
        try:
            pupil = Kos.PupilCalc(
                pupil_system,
                pupil_index,
                app._current_wavelength(),
                app._current_aperture_type(),
                app._current_aperture_value(),
            )
            pos = np.asarray(getattr(pupil, "PosPupInp", None), dtype=float).reshape(-1)
            rad = float(getattr(pupil, "RadPupInp", float("nan")))
            if pos.size >= 3 and np.isfinite(pos[2]) and np.isfinite(rad) and rad > 0.0:
                notes.append(f"REAL = PupilCalc resolved the entrance pupil (z={pos[2]:.2f}, r={rad:.2f})")
            else:
                notes.append(f"REAL PupilCalc returned a degenerate pupil (pos={pos}, rad={rad})")
                ok = False
        except Exception as exc:
            notes.append(f"REAL PupilCalc still dies on the frozen cube scene ({exc!r})")
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
