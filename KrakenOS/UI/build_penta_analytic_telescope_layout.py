"""Build a saved layout using the NEW analytic-promote pipeline.

The previous builder ``build_penta_telescope_layout`` was written
before the analytic-promote workflow landed. It used the STL
optical-solid path, so its output ``five_penta_prism_telescope_cascade.py``
shows STL bodies that refract per-triangle on curved surfaces and
produce the "unknown bent ray" the user flagged.

This builder uses every fix landed today:

  * sphere splitter (ball-lens hemispheres)
  * analytic-fit promote with sign-corrected Rc
  * cascade-aware auto-tilt (chain_exit_direction)
  * doublet auto-route to OCC Native Rows for the achromat

Run::

    .devenv/state/venv/bin/python -m KrakenOS.UI.build_penta_analytic_telescope_layout

Output::

    attachment/five_penta_prism_analytic_telescope_cascade.py

Open it in the editor (File -> Open) and you'll see ANALYTIC
Standard surfaces for each lens instead of STL bodies. The bending
"unknown ray" is gone because curved-surface refraction now uses
the row's Rc/k (analytic spherical refraction), not the local
triangle normal.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor, Kraken3DInspector

from KrakenOS.UI.validate_open3d_penta_telescope_chain import (
    PENTA_CASCADE_PATH,
    BALL_LENS_STEP,
    DCV_STEP,
    ACHROMAT_STEP,
    CYL_STEP,
    BALL_LENS_GAP_MM,
    PHASE1_CLEARANCE_FROM_PRISM_MM,
    PHASE2_GAP_FROM_BALL_2_MM,
    DCV_TO_ACHROMAT_GAP_MM,
    PHASE3_GAP_FROM_ACHROMAT_MM,
    _load_penta_cascade,
    _open_inspector,
    _set_exit_axis_from_trace,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_LAYOUT = PROJECT_ROOT / "attachment" / "five_penta_prism_analytic_telescope_cascade.py"


# Each lens is described by its STEP path, the friendly name to give
# the leading row, and a glass sequence. Singlets pass one glass;
# the achromat passes its multi-glass doublet sequence so the
# promote facade auto-routes through OCC Native Rows for cement-layer
# recovery (Rc=-21.98 mm survives instead of getting averaged out).
# Distance from each lens to the next (CENTER-to-CENTER along the
# cascade exit beam). Same layout as build_penta_telescope_layout
# (the STL version), so the analytic and STL files are directly
# comparable in 3D space.
LENS_SPECS: list[dict[str, Any]] = [
    {
        "name": "Ball Lens 1 (sapphire)",
        "step": BALL_LENS_STEP,
        "glass": "AL2O3",
        "offset_along_exit_mm": PHASE1_CLEARANCE_FROM_PRISM_MM,
        "gap_after_mm": 1.435,
    },
    {
        "name": "Ball Lens 2 (sapphire)",
        "step": BALL_LENS_STEP,
        "glass": "AL2O3",
        "offset_along_exit_mm": PHASE1_CLEARANCE_FROM_PRISM_MM + BALL_LENS_GAP_MM,
        "gap_after_mm": PHASE2_GAP_FROM_BALL_2_MM,
    },
    {
        "name": "DCV f=-50 mm (N-BK7)",
        "step": DCV_STEP,
        "glass": "N-BK7",
        "offset_along_exit_mm": (
            PHASE1_CLEARANCE_FROM_PRISM_MM
            + BALL_LENS_GAP_MM
            + PHASE2_GAP_FROM_BALL_2_MM
        ),
        "gap_after_mm": DCV_TO_ACHROMAT_GAP_MM,
    },
    {
        "name": "Achromat f=+50 mm (BAF10/SF10)",
        "step": ACHROMAT_STEP,
        "glass": "N-BAF10, N-SF10, AIR",  # triggers doublet -> Native Rows
        "offset_along_exit_mm": (
            PHASE1_CLEARANCE_FROM_PRISM_MM
            + BALL_LENS_GAP_MM
            + PHASE2_GAP_FROM_BALL_2_MM
            + DCV_TO_ACHROMAT_GAP_MM
        ),
        "gap_after_mm": PHASE3_GAP_FROM_ACHROMAT_MM,
    },
]
# Cylindrical lens stays out of the analytic line-up for now -- its
# toroidal face's centroid-averaged normal is perpendicular to the
# flat face's normal, so the front/back detection can't trigger
# without a proper torus fit (tracked separately).


def _import_step(
    app: KrakenLayoutEditor,
    step_path: Path,
    placement_offset_xyz: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> None:
    """Replicate the import-overlay path without the file dialog.

    ``placement_offset_xyz`` becomes the row's ``desp`` (in chain
    frame) when the overlay is promoted -- it's how we tell the
    promote service WHERE in the world the lens body should sit.
    """
    app.imported_optical_step_path = step_path
    app.optical_step_rotation_x_deg = 0.0
    app.optical_step_rotation_y_deg = 0.0
    app.optical_step_rotation_z_deg = 0.0
    app.optical_step_placement_offset_xyz = tuple(float(v) for v in placement_offset_xyz)
    app.select_step_component("optical")


def _rename_row(app: KrakenLayoutEditor, row_index: int, name: str) -> None:
    """Set a row's friendly name + sync into the table.

    save_layout reads back from the Tk table, so both sides must
    agree or the rename gets clobbered.
    """
    try:
        if 0 <= row_index < len(app.rows):
            app.rows[row_index].name = name
    except Exception:
        return
    try:
        item = app._table_item_for_row_index(row_index)
        if not item:
            return
        cols = list(app.table["columns"])
        if "name" not in cols:
            return
        name_col = cols.index("name")
        current = list(app.table.item(item, "values"))
        while len(current) <= name_col:
            current.append("")
        current[name_col] = name
        app.table.item(item, values=current)
    except Exception:
        pass


def _build_layout(app: KrakenLayoutEditor, inspector: Kraken3DInspector) -> dict:
    summary: dict = {}

    # Phase 0: cascade + initial trace so the chain exit direction
    # comes from the actual ray trace through the prisms.
    base = _load_penta_cascade(app)
    summary["cascade_rows"] = base["row_count"]
    inspector.refresh_from_editor(force_retrace=True)
    inspector.update_idletasks()
    try:
        inspector._trace_live_now()
    except Exception:
        pass
    inspector.update_idletasks()

    # Pull the chain's exit position and direction from the trace
    # so we can place each lens at the correct WORLD position along
    # the cascade exit beam. The penta cascade emits at ~ (37.5, 0,
    # 197.5) going along world -X.
    exit_axis = _set_exit_axis_from_trace(inspector)
    if exit_axis is None:
        raise RuntimeError("Could not derive exit position/direction from cascade trace")
    exit_pt, exit_dir_raw = exit_axis
    # Snap direction to nearest cardinal axis to kill ~1e-6 trace
    # noise that would otherwise confuse downstream tilt mapping.
    dominant = int(np.argmax(np.abs(exit_dir_raw)))
    snapped = np.zeros(3, dtype=float)
    snapped[dominant] = float(np.sign(exit_dir_raw[dominant]))
    exit_dir = snapped
    chain_exit = (float(exit_dir[0]), float(exit_dir[1]), float(exit_dir[2]))
    summary["chain_exit_position"] = exit_pt.tolist()
    summary["chain_exit_direction"] = list(chain_exit)

    promoted_rows: list[dict[str, Any]] = []
    for spec in LENS_SPECS:
        try:
            app.clear_step_imports()
        except Exception:
            pass
        # World position where THIS lens's body centroid should sit.
        target_world = exit_pt + exit_dir * float(spec["offset_along_exit_mm"])
        _import_step(
            app,
            spec["step"],
            placement_offset_xyz=(
                float(target_world[0]),
                float(target_world[1]),
                float(target_world[2]),
            ),
        )
        inspector.refresh_from_editor()
        inspector.update_idletasks()
        try:
            outcome = app.promote_imported_step_to_analytic_surfaces(
                "optical",
                glass_sequence=spec["glass"],
                clear_overlay=True,
                refresh_open_3d=False,
                chain_exit_direction=chain_exit,
            )
        except Exception as exc:
            print(f"WARN: {spec['name']}: promote raised {exc}; skipping", file=sys.stderr)
            continue
        if not outcome:
            print(f"WARN: {spec['name']}: promote returned None; skipping", file=sys.stderr)
            continue
        indices = list(outcome.get("row_indices") or [])
        if not indices:
            continue
        # First row gets the friendly name; subsequent rows keep
        # their auto-generated S2/S3/... suffix so it's still clear
        # they belong to the same body.
        _rename_row(app, int(indices[0]), spec["name"])
        # Set the GAP after this lens by adjusting the LAST row's
        # thickness. KrakenOS chains rows by thickness; the trailing
        # row's thickness is the gap to whatever comes next.
        try:
            app.rows[int(indices[-1])].thickness = float(spec["gap_after_mm"])
            app._sync_table()
        except Exception:
            pass
        promoted_rows.append(
            {
                "lens": spec["name"],
                "first_row": int(indices[0]),
                "rows_added": len(indices),
                "glass_sequence": spec["glass"],
            }
        )
        inspector.refresh_from_editor()
        inspector.update_idletasks()

    summary["promoted"] = promoted_rows
    summary["final_row_count"] = len(app.rows)
    return summary


def _save(app: KrakenLayoutEditor) -> None:
    OUTPUT_LAYOUT.parent.mkdir(parents=True, exist_ok=True)
    app.current_layout_file = OUTPUT_LAYOUT
    if not app.save_layout():
        raise RuntimeError("save_layout returned False")


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        inspector = _open_inspector(app)
        summary = _build_layout(app, inspector)
        try:
            app._read_rows_from_table()
        except Exception:
            pass
        _save(app)
        print("Built ANALYTIC penta-telescope cascade:")
        print(f"  cascade rows : {summary.get('cascade_rows')}")
        print(f"  chain exit   : {summary.get('chain_exit_direction')}")
        print(f"  final rows   : {summary.get('final_row_count')}")
        for item in summary.get("promoted", []):
            print(
                f"    {item['lens']:36s}  rows={item['rows_added']}  "
                f"first_row=S{item['first_row']}  glass={item['glass_sequence']!r}"
            )
        print(f"\nSaved layout -> {OUTPUT_LAYOUT}")
        print(
            "\nCompare with the OLD STL-based layout:\n"
            f"  diff this with attachment/five_penta_prism_telescope_cascade.py\n"
            f"  (old has Solid 3D STL rows, this has Standard analytic rows)\n"
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
