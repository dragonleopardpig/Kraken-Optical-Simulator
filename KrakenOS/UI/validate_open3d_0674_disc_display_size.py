"""Guard for bugs/0674 -- flag "let's solve one at a time: the lens surrogate is
oversized" (om05a folded scene).

Two display defects made the folded scene's discs giant:
1. Override-posed (folded) rows draw their surface cap from the core's EEE runtime
   mesh, which renders at TWICE the row diameter (a 48.56 datum drew 97.1; the
   50.8 filter drew 101.5). Straight scenes use the analytic path and never showed
   it. Fix: the runtime disc mesh is rescaled about its centre to row.diameter.
2. The row ``Drawing`` flag was 2D-only: the om05a launch-probe plates
   (diameter 80 kept ONLY because the launch-measure probes need wide first
   apertures -- dia 46 collapsed the aim to 2% reach) still rendered as an 80 mm
   disc stack in 3D. Fix: the 3D surface iterator honors drawing=0.

Check (standalone only -- needs the embedded inspector; skips in-harness and when
the Filen-synced scene is absent): open the folded scene in the REAL inspector and
measure every disc-like actor (flat: thinnest extent < 8 mm): none may span more
than 60 mm (the largest honest disc is the 50.8 filter; the mirror cubes and lens
body are 3D bodies, excluded by the thinness test; axis guide POLYLINES have two
zero extents, excluded).

Run:  xvfb-run -a .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0674_disc_display_size
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment/om05a_folded.py"


def _check_display(ok, notes, app=None, inspector=None) -> None:
    if app is not None or inspector is not None:
        notes.append("SKIP: display check runs standalone only (the harness owns the single inspector)")
        return
    if not SCENE.exists():
        notes.append("SKIP: the om05a folded scene is not on this machine (Filen-synced)")
        return
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector, _settle
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = None
    try:
        editor = KrakenLayoutEditor()
        editor._prompt_for_missing_cad_assets = lambda: None
        editor.layout_files["p"] = SCENE
        editor.load_layout_by_name("p")
        insp = _open_3d_inspector(editor)
        insp.refresh_from_editor(sampling_mode=editor._preview_3d_sampling_mode(), force_retrace=True)
        _settle(insp)
        coll = insp._renderer.GetActors()
        coll.InitTraversal()
        offenders = []
        discs = 0
        for _ in range(coll.GetNumberOfItems()):
            actor = coll.GetNextActor()
            b = actor.GetBounds()
            if not all(np.isfinite(b)):
                continue
            ext = sorted([b[1] - b[0], b[3] - b[2], b[5] - b[4]])
            if ext[0] > 8.0 or ext[1] < 1.0:
                continue  # a 3D body, or a polyline (two near-zero extents)
            if ext[1] / max(ext[2], 1e-9) < 0.6:
                continue  # a flat RIBBON (a dashed axis guide spans one long axis), not a disc
            discs += 1
            span = ext[2]
            if span > 60.0:
                offenders.append((round(span, 1), [round((b[0] + b[1]) / 2, 1), round((b[2] + b[3]) / 2, 1), round((b[4] + b[5]) / 2, 1)]))
        ok(
            discs > 4 and not offenders,
            f"A1: no oversized surface disc in the folded scene ({discs} discs measured; "
            f"offenders {offenders[:4]})",
        )
    finally:
        try:
            if editor is not None:
                editor.destroy()
        except Exception:
            pass


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    try:
        _check_display(ok, notes, app=app, inspector=inspector)
    except Exception as exc:  # pragma: no cover - environment
        notes.append(f"FAIL: guard raised ({type(exc).__name__}: {exc})")

    passed = not any(line.startswith("FAIL") for line in notes)
    if verbose:
        for line in notes:
            print(line)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("Disc-display-size validation passed.")
        return 0
    print("Disc-display-size validation FAILED:")
    for line in notes:
        if line.startswith("FAIL"):
            print(f"- {line}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
