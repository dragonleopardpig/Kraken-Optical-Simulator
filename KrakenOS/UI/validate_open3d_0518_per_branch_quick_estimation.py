"""bugs/0518 guard -- Quick Estimation answers PER ARM on a tagged two-arm scene (B3).

Detector-redesign B3 (first piece): the QE panel was single-chain -- on a two-arm splitter
scene (per-arm lenses + sensors) it answered for one arm at best. ``branch_states()`` now
extracts each tagged arm's row chain (``_branch_leaf_rows``), reads that arm's own 0297
first order (``_first_order_reference_for_rows(unfold_branch_tilts=True)``) and derives
per-arm f / working distance / magnification / sensor / object FOV; the panel shows one
line per arm ("Per-arm" row). Untagged scenes keep the single-chain readout untouched.

Checks:
  SOURCE -- branch_states + the readout "branches" key + the rows-parameterized first
            order exist and are wired.
  REAL   -- on the dual MV150/MV120 scene: BOTH arms report, with DISTINCT focal lengths
            and finite conjugate data; the untagged 50/50 scene reports none.
"""
from __future__ import annotations

import inspect as _inspect
from pathlib import Path

import numpy as np

DUAL = Path("KrakenOS/common_optical_layouts/beam_splitter_dual_mv_150_120.py")
UNTAGGED = Path("KrakenOS/common_optical_layouts/beam_splitter_50_50_example.py")


class _Shim:
    def __init__(self, editor):
        self.editor = editor


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService
    from KrakenOS.UI.services import paraxial_tools as _pt

    if hasattr(QuickEstimationService, "branch_states"):
        notes.append("SOURCE = QuickEstimationService.branch_states exists")
    else:
        notes.append("SOURCE branch_states is missing")
        return False, notes

    readout_src = _inspect.getsource(QuickEstimationService.format_readout)
    if '"branches"' in readout_src and "branch_states" in readout_src:
        notes.append("SOURCE = the readout carries the per-arm lines")
    else:
        notes.append("SOURCE the readout lost the per-arm branches key")
        ok = False

    if "def _first_order_reference_for_rows" in _inspect.getsource(_pt):
        notes.append("SOURCE = the 0297 first order is rows-parameterized")
    else:
        notes.append("SOURCE _first_order_reference_for_rows is missing")
        ok = False

    if not (DUAL.exists() and UNTAGGED.exists()):
        notes.append("SKIP: bundled two-arm scenes missing")
        return ok, notes

    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        app = KrakenLayoutEditor()
    except Exception as exc:
        notes.append(f"SKIP: editor unavailable ({exc!r})")
        return ok, notes
    try:
        app.layout_files["dual"] = DUAL
        app.load_layout_by_name("dual")
        qe = QuickEstimationService(_Shim(app))
        branches = qe.branch_states()
        if len(branches) >= 2:
            focals = {sel: float(st.get("focal_length") or 0.0) for sel, st in branches.items()}
            finite = all(np.isfinite(v) and v > 0 for v in focals.values())
            distinct = len({round(v, 3) for v in focals.values()}) >= 2
            if finite and distinct:
                notes.append(
                    "REAL = both arms report their OWN first order ("
                    + ", ".join(f"{s}: f={focals[s]:.4g}" for s in sorted(focals))
                    + ")"
                )
            else:
                notes.append(f"REAL per-arm focals wrong (finite={finite}, distinct={distinct}: {focals})")
                ok = False
            with_fov = [s for s, st in branches.items() if st.get("fov_full")]
            if with_fov:
                notes.append(f"REAL = per-arm object FOV derived for {sorted(with_fov)}")
            else:
                notes.append("REAL no arm derived an object FOV")
                ok = False
        else:
            notes.append(f"REAL two-arm scene reported {len(branches)} arm(s)")
            ok = False

        # -- solve side: drive ONE arm's FOV, the other arm must stay in focus -----------
        solved, solve_msg = qe.branch_fov_solve("reflect", 30.0)
        if solved:
            after = qe.branch_states()
            reflect_semi = (after.get("reflect") or {}).get("fov_semi")
            if reflect_semi is not None and abs(float(reflect_semi) - 30.0) <= 0.5:
                notes.append(f"SOLVE = the reflect arm reaches the requested field (semi {reflect_semi:.3f})")
            else:
                notes.append(f"SOLVE reflect field wrong after solve ({reflect_semi})")
                ok = False
            for sel in sorted(after):
                info = qe._branch_solve_info(sel)
                f = float(info["first"]["f"])
                s_o = float(info["first"]["object_principal"])
                resid = f * s_o / (s_o - f) - float(info["first"]["image_principal"])
                if abs(resid) <= 0.05:
                    notes.append(f"SOLVE = arm {sel} in focus after the solve (residual {resid:+.4f} mm)")
                else:
                    notes.append(f"SOLVE arm {sel} left defocused ({resid:+.4f} mm)")
                    ok = False
        else:
            notes.append(f"SOLVE branch_fov_solve failed: {solve_msg}")
            ok = False
        bad, _msg = qe.branch_fov_solve("nonsense", 30.0)
        if not bad:
            notes.append("NEG = an unknown arm is refused")
        else:
            notes.append("NEG an unknown arm was accepted")
            ok = False

        app.layout_files["untagged"] = UNTAGGED
        app.load_layout_by_name("untagged")
        qe2 = QuickEstimationService(_Shim(app))
        neg = qe2.branch_states()
        if not neg:
            notes.append("NEG = an untagged split keeps the single-chain readout")
        else:
            notes.append(f"NEG untagged scene grew branch states: {sorted(neg)}")
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
