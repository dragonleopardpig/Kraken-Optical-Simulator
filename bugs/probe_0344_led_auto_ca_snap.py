"""Probe (bugs/0344): with NO manual clear-aperture record, does the imported LED
still expose an AUTO-DETECTED opening whose centre + normal resolve?

If yes, the right-click "Snap Clear Aperture -> Optical Axis" must be offered from
the auto-detect (the same resolver that lights the hover highlight), not only from
the manual bugs/0134 record -- otherwise the opening highlights but cannot be
snapped ("right click snap still not working").

Loads the AZ85 folded scene but never opens the GL 3D view; auto-detect and the
fine-face centroid/normal are pure-geometry editor methods.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")

        record = app.step_clear_aperture("led")
        print("manual step_clear_aperture('led') =", record)

        cands = app.auto_detect_step_clear_aperture_candidates("led")
        print(f"auto-detect candidates: {len(cands)}")
        if cands:
            top = cands[0]
            resolved = app._step_overlay_fine_face_centroid_normal("led", top.face_index)
            if resolved is None:
                print(f"  top face {top.face_index}: UNRESOLVED on transformed mesh")
            else:
                cen, nrm, area = resolved
                cen = np.asarray(cen, float)
                nrm = np.asarray(nrm, float)
                finite = bool(np.all(np.isfinite(cen)) and np.all(np.isfinite(nrm)))
                print(f"  top face {top.face_index}: center={cen}, normal={nrm}, "
                      f"area={area:.1f}, finite={finite}")
                verdict = (record is None) and finite
                print(f"\nVERDICT: opening snappable WITHOUT a manual record = {verdict}")
    except Exception:
        traceback.print_exc()
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
