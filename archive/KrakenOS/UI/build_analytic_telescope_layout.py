"""Emit an analytic-surface version of the post-cascade telescope chain.

The companion file ``build_penta_telescope_layout.py`` builds the
penta-prism cascade with the four telescope lenses appended as STL
optical-solid rows. STL refraction uses the local triangle normal,
which means curved-lens refraction is per-triangle and rays bend
erratically (captured in the user's "big bending ray" 3D.png).

This script emits a SEPARATE layout with the same lens chain but
each curved lens replaced by analytic Standard surfaces (with rc /
thickness / glass pulled from the Zemax .zmx files). Geometry is
along +Z so KrakenOS's default chain math gives clean physics, no
cascade folding required. Open it alongside the cascade layout to
see the same telescope behave with analytic vs. STL refraction.

Run::

    .devenv/state/venv/bin/python -m KrakenOS.UI.build_analytic_telescope_layout

Output::

    attachment/analytic_telescope_chain.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_LAYOUT = PROJECT_ROOT / "attachment" / "analytic_telescope_chain.py"


# Zemax-derived prescription. CURV is 1/Rc in the .zmx files; we keep
# Rc here. Glass names match the KrakenOS material catalog.
PRESCRIPTION: list[dict[str, Any]] = [
    # Source-side air gap so rays have room to start as a collimated bundle.
    {"role": "object_gap", "thickness": 50.0, "glass": "AIR", "diameter": 20.0},

    # Ball Lens 1 (Edmund 63227, sapphire).
    # CURV1 = +0.20997 (rc = +4.7625 mm), thickness 9.525 mm, AL2O3.
    # CURV2 = -0.20997 (rc = -4.7625 mm).
    {"role": "ball_lens_1_front", "rc":  4.7625, "thickness": 9.525,  "glass": "AL2O3", "diameter": 10.0},
    {"role": "ball_lens_1_back",  "rc": -4.7625, "thickness": 1.435,  "glass": "AIR",   "diameter": 10.0},  # 2f - body = 10.96 - 9.525 = 1.435

    # Ball Lens 2 (same as ball lens 1, focal point at the midpoint of the gap).
    {"role": "ball_lens_2_front", "rc":  4.7625, "thickness": 9.525,  "glass": "AL2O3", "diameter": 10.0},
    {"role": "ball_lens_2_back",  "rc": -4.7625, "thickness": 50.0,   "glass": "AIR",   "diameter": 10.0},  # gap to DCV

    # DCV (Edmund 32996, N-BK7, double-concave, f = -50 mm).
    # CURV1 = -0.01919 (rc = -52.10 mm), thickness 2.5 mm, N-BK7.
    # CURV2 = +0.01919 (rc = +52.10 mm).
    {"role": "dcv_front", "rc": -52.10, "thickness": 2.5,   "glass": "N-BK7", "diameter": 12.0},
    {"role": "dcv_back",  "rc":  52.10, "thickness": 100.0, "glass": "AIR",   "diameter": 12.0},  # gap to achromat

    # Achromat (Edmund 32323, BAF10/SF10 doublet, f = +50 mm).
    # CURV1 = +0.02896 (rc = +34.53 mm), thickness 9 mm, N-BAF10.
    # CURV2 = -0.04550 (rc = -21.98 mm), thickness 2.5 mm, N-SF10.
    # CURV3 = -0.00466 (rc = -214.63 mm).
    {"role": "achromat_s1", "rc":   34.53, "thickness": 9.0,   "glass": "N-BAF10", "diameter": 12.0},
    {"role": "achromat_s2", "rc":  -21.98, "thickness": 2.5,   "glass": "N-SF10",  "diameter": 12.0},
    {"role": "achromat_s3", "rc": -214.63, "thickness": 100.0, "glass": "AIR",     "diameter": 12.0},  # gap to cyl

    # Cylindrical (Edmund 34754, plano-toroidal, N-BK7, f = 50 mm in the curved axis).
    # CURV1 = +0.03870 (rc = +25.84 mm) TOROIDAL, thickness 4.34 mm, N-BK7.
    # CURV2 = 0 (plano).
    # Use Cyl Y axis so the line spot lies along world Y. Modeling the
    # cylindrical with a Standard surface treats both axes as identical
    # power -- the line focus check stays approximate here; the
    # cylindrical's full toroidal physics needs the dedicated Cyl_Y/Cyl_X
    # surface type.
    {"role": "cyl_front", "rc":  25.84,  "thickness": 4.34, "glass": "N-BK7", "diameter": 25.4, "cyl_axis": "y"},
    {"role": "cyl_back",  "rc":  0.0,    "thickness": 50.0, "glass": "AIR",   "diameter": 25.4, "cyl_axis": "y"},  # to focal plane
]


def _build_layout(app: KrakenLayoutEditor) -> dict:
    summary: dict = {"rows": []}

    rows = list(app.rows or [])
    # Replace existing rows with a fresh Object surface + analytic chain
    # + Image surface. Object's thickness defines the first air gap;
    # then each prescription entry becomes a Standard surface.
    from KrakenOS.UI.layout_editor import SurfaceRow

    new_rows = []
    object_row = SurfaceRow(
        label="0",
        surface="Object",
        element="",
        name="Object",
        thickness=0.0,
        diameter=20.0,
        glass="AIR",
    )
    new_rows.append(object_row)

    for idx, entry in enumerate(PRESCRIPTION, start=1):
        row = SurfaceRow(
            label=str(idx),
            surface="Standard",
            element="",
            name=entry["role"],
            rc=float(entry.get("rc", 0.0)),
            thickness=float(entry.get("thickness", 0.0)),
            diameter=float(entry.get("diameter", 0.0)),
            glass=str(entry.get("glass", "AIR")),
        )
        # Toroidal/cylindrical hint -- KrakenOS uses Cyl_Y/Cyl_X surface
        # types for true cylindrical optics. We tag the metadata so a
        # downstream user can swap surface type by hand if they want
        # the exact toroidal physics.
        if "cyl_axis" in entry:
            row.advanced = dict(getattr(row, "advanced", {}) or {})
            row.advanced["CylindricalAxisHint"] = str(entry["cyl_axis"])
        new_rows.append(row)
        summary["rows"].append({
            "index": idx,
            "name": entry["role"],
            "rc": float(entry.get("rc", 0.0)),
            "thickness": float(entry.get("thickness", 0.0)),
            "glass": str(entry.get("glass", "AIR")),
        })

    image_row = SurfaceRow(
        label=str(len(new_rows)),
        surface="Image",
        element="",
        name="Image",
        thickness=0.0,
        diameter=20.0,
        glass="AIR",
    )
    new_rows.append(image_row)

    app.rows = new_rows
    app._sync_table()
    return summary


def _save(app: KrakenLayoutEditor) -> None:
    OUTPUT_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    app.current_layout_file = OUTPUT_LAYOUT
    if not app.save_layout():
        raise RuntimeError("save_layout returned False")


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        app.open_3d_view()
        app.update_idletasks()
        app.update()
        summary = _build_layout(app)
        # The 3D inspector might be open; sync so save reads the right rows.
        try:
            app._read_rows_from_table()
        except Exception:
            pass
        _save(app)
        print("Built analytic telescope chain:")
        print(f"  rows: {len(summary['rows'])} analytic Standard surfaces")
        for r in summary["rows"]:
            print(f"    s{r['index']:2d}  {r['name']:24s}  rc={r['rc']:+8.3f}  t={r['thickness']:6.3f}  glass={r['glass']}")
        print(f"\nSaved layout -> {OUTPUT_LAYOUT}")
        print(
            "\nOpen the analytic chain in the inspector:\n"
            f"  .devenv/state/venv/bin/python -m KrakenOS\n"
            f"  File -> Open -> {OUTPUT_LAYOUT.name}\n"
        )
        return 0
    except Exception as exc:
        import traceback
        print(f"FAILED: {exc}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
