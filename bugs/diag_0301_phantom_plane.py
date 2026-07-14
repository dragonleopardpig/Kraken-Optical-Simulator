"""bugs/0301: a phantom plane appears between RA prism1 and the imaging lens in the
exported STEP (attachment/STEP2.png). Enumerate every prescription surface with the
flags that gate export (Drawing / Diameter / revolution-compatible) AND the properties
that would tell us it is a dummy/air reference the 3D inspector does not draw as a disc.

Run: .devenv/state/venv/bin/python bugs/diag_0301_phantom_plane.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services import cad_step_export as ce
from KrakenOS.UI.validate_open3d_five_penta_initial_visual import _load_saved_layout

LAYOUT = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


def main() -> int:
    app = KrakenLayoutEditor(headless=True)
    _load_saved_layout(app, LAYOUT)
    system = app.build_system()
    sdt = getattr(system, "SDT", []) or []
    trans = getattr(system, "TRANS_2A", None)

    def _world(j):
        if trans is None or j >= len(trans):
            return None
        m = np.asarray(trans[j], dtype=float).reshape(4, 4)
        return np.round((m @ np.array((0.0, 0.0, 0.0, 1.0)))[:3], 2).tolist()

    print(f"{'j':>2} {'surface':9} {'name':22} {'glass':10} {'Diam':>7} {'Thick':>8} "
          f"{'Draw':>4} {'revol':>5} {'stl?':>4}  world")
    for j, surf in enumerate(sdt):
        row = app.rows[j] if j < len(app.rows) else None
        name = (getattr(row, "name", "") or getattr(row, "element", "")
                or getattr(row, "comment", "") or "") if row else ""
        glass = str(getattr(surf, "Glass", "") or (getattr(row, "glass", "") if row else "") or "")
        diam = float(getattr(surf, "Diameter", 0) or 0)
        thick = getattr(surf, "Thickness", None)
        thick = float(thick) if thick is not None else float("nan")
        draw = bool(getattr(surf, "Drawing", 1))
        revol = ce._is_surface_revolution_compatible(surf)
        stl = app._file_backed_stl_row_at(j) is not None
        print(f"{j:>2} {str(getattr(row,'surface','')):9.9} {name:22.22} {glass:10.10} "
              f"{diam:7.2f} {thick:8.2f} {str(draw):>4} {str(revol):>5} {str(stl):>4}  {_world(j)}")

    print("\nadvanced skip flags per row (what the DISPLAY loop keys off):")
    skip_keys = ("Solid_3d_stl", "StepAnalyticBodyOmitMesh", "InPathTrailingSpacer",
                 "StepAnalyticBodyStlPath", "step_source_path")
    for j, row in enumerate(app.rows):
        adv = row.advanced if isinstance(getattr(row, "advanced", None), dict) else {}
        flags = {k: adv.get(k) for k in skip_keys if adv.get(k)}
        print(f"{j:>2} {str(getattr(row,'surface','')):9.9} advanced_keys={sorted(adv.keys())}")
        if flags:
            print(f"     set-> {flags}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
