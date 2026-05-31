"""Build a saved layout: penta-prism cascade + telescope chain along -X.

This script side-steps the two outstanding product bugs (#10 row
thickness doesn't move promoted bodies, #15 STEP body vs promoted
mesh Z desync) by building the layout programmatically through the
exact code path the headless Open 3D harness already verifies, then
serializing the final rows + SETTINGS to a self-contained Python
layout file the user can open via ``File -> Open`` in the layout
editor.

Run::

    .devenv/state/venv/bin/python -m KrakenOS.UI.build_penta_telescope_layout

The resulting file is written to::

    attachment/five_penta_prism_telescope_cascade.py

Layout (from the prism-cascade exit along world -X):

    five-prism cascade  ->  ball lens 1  ->  ball lens 2  (confocal pair, 2f=10.96 mm)
                            -> 50 mm gap -> DCV  -> 100 mm -> Achromat (f=+50)
                            -> 100 mm -> Cylindrical lens (toroidal, f=50)

Each post-cascade body is placed on the cascade's last-segment optical
axis with tilts so its local optical axis aligns with world -X.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor, Kraken3DInspector

# Reuse helpers from the validator -- same code path, same data.
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
    EXIT_POSITION,
    EXIT_DIRECTION,
    _load_penta_cascade,
    _open_inspector,
    _set_exit_axis_from_trace,
    _tilts_to_align_local_axis_to_world,
    _import_position_promote,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_LAYOUT = PROJECT_ROOT / "attachment" / "five_penta_prism_telescope_cascade.py"


def _rename_row(app: KrakenLayoutEditor, row_index: int, name: str) -> None:
    """Rename a promoted row in the editor table and the rows list.

    Promotion gives every body the same generic "Promoted OPTICAL STEP
    optical solid" name. Replace it with a friendly label so the saved
    layout reads cleanly when opened in the editor. We update both
    `app.rows[i].name` and the Tk table cell so a later
    `_read_rows_from_table` (called by `save_layout`) doesn't revert
    the rename. The table's iid scheme isn't positional, so use the
    editor's `_table_item_for_row_index` lookup instead of indexing
    `table.get_children()`.
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
    """Drive the same phases the validator runs, return a build report."""
    summary: dict = {}

    # Phase 0: cascade + initial trace so EXIT_POSITION/EXIT_DIRECTION
    # are pinned from the actual last-segment of the central ray.
    base = _load_penta_cascade(app)
    summary["cascade_rows"] = base["row_count"]
    inspector.refresh_from_editor(force_retrace=True)
    inspector.update_idletasks()
    exit_axis = _set_exit_axis_from_trace(inspector)
    if exit_axis is None:
        raise RuntimeError(
            "Could not derive exit axis from the cascade trace -- "
            "the runtime ray bundle is empty."
        )
    exit_pt, exit_dir = exit_axis
    # Snap the runtime-derived direction to the nearest cardinal axis.
    # The trace returns the direction with floating-point noise on the
    # order of 1e-6 on the off-axis components; that noise breaks
    # _tilts_to_align_local_axis_to_world's np.allclose match against
    # the canonical (-1, 0, 0) and silently returns (0, 0, 0), which
    # leaves every post-cascade lens un-rotated (optical axis along
    # world +Z instead of -X). Snap to the dominant axis and override
    # the global EXIT_DIRECTION so downstream helpers also see a clean
    # vector.
    dominant = int(np.argmax(np.abs(exit_dir)))
    snapped = np.zeros(3, dtype=float)
    snapped[dominant] = float(np.sign(exit_dir[dominant]))
    exit_dir = snapped
    import KrakenOS.UI.validate_open3d_penta_telescope_chain as _vptc
    _vptc.EXIT_DIRECTION = snapped
    summary["exit_position_world"] = exit_pt.tolist()
    summary["exit_direction_world"] = exit_dir.tolist()

    # Same tilt for every post-cascade body: align local +Z with the
    # exit beam direction (world -X for this fixture). The cylindrical
    # uses a different local axis because its toroidal power is in
    # local +Y, not +Z; see CYL_LOCAL_AXIS below.
    tilts_z = _tilts_to_align_local_axis_to_world((0.0, 0.0, 1.0), exit_dir)
    pre_rot_z = tuple((axis, deg) for axis, deg in zip("xyz", tilts_z) if abs(deg) > 1e-9)

    # Phase 1: two ball lenses (confocal pair).
    ball1_target = exit_pt + exit_dir * PHASE1_CLEARANCE_FROM_PRISM_MM
    ball2_target = ball1_target + exit_dir * BALL_LENS_GAP_MM
    r1 = _import_position_promote(
        app, inspector,
        step_path=BALL_LENS_STEP,
        target_world=ball1_target,
        label_name="ball_lens_1",
        pre_rotations=pre_rot_z,
    )
    _rename_row(app, int(r1["row_index"]), "Ball Lens 1 (sapphire)")
    r2 = _import_position_promote(
        app, inspector,
        step_path=BALL_LENS_STEP,
        target_world=ball2_target,
        label_name="ball_lens_2",
        pre_rotations=pre_rot_z,
    )
    _rename_row(app, int(r2["row_index"]), "Ball Lens 2 (sapphire)")
    summary["ball_lens_rows"] = [r1["row_index"], r2["row_index"]]

    # Phase 2: DCV + Achromat.
    ball2_offset = PHASE1_CLEARANCE_FROM_PRISM_MM + BALL_LENS_GAP_MM
    dcv_target = exit_pt + exit_dir * (ball2_offset + PHASE2_GAP_FROM_BALL_2_MM)
    achromat_target = dcv_target + exit_dir * DCV_TO_ACHROMAT_GAP_MM
    r3 = _import_position_promote(
        app, inspector,
        step_path=DCV_STEP,
        target_world=dcv_target,
        label_name="dcv",
        pre_rotations=pre_rot_z,
    )
    _rename_row(app, int(r3["row_index"]), "DCV f=-50 mm (N-BK7)")
    r4 = _import_position_promote(
        app, inspector,
        step_path=ACHROMAT_STEP,
        target_world=achromat_target,
        label_name="achromat",
        pre_rotations=pre_rot_z,
    )
    _rename_row(app, int(r4["row_index"]), "Achromat f=+50 mm")
    summary["telescope_pair_rows"] = [r3["row_index"], r4["row_index"]]

    # Phase 3: cylindrical (line focus). The toroidal lens has its
    # curved axis along local +Y -- align that with the exit direction
    # so the cyl power acts along the beam, leaving a line spot in the
    # orthogonal axis.
    achromat_offset = ball2_offset + PHASE2_GAP_FROM_BALL_2_MM + DCV_TO_ACHROMAT_GAP_MM
    cyl_target = exit_pt + exit_dir * (achromat_offset + PHASE3_GAP_FROM_ACHROMAT_MM)
    tilts_cyl = _tilts_to_align_local_axis_to_world((0.0, 1.0, 0.0), exit_dir)
    pre_rot_cyl = tuple((axis, deg) for axis, deg in zip("xyz", tilts_cyl) if abs(deg) > 1e-9)
    r5 = _import_position_promote(
        app, inspector,
        step_path=CYL_STEP,
        target_world=cyl_target,
        label_name="cyl",
        pre_rotations=pre_rot_cyl,
    )
    _rename_row(app, int(r5["row_index"]), "Cylindrical f=50 mm (toroidal)")
    summary["cyl_row"] = r5["row_index"]

    inspector.refresh_from_editor(force_retrace=True)
    inspector.update_idletasks()
    summary["final_row_count"] = len(app.rows)
    return summary


def _save_layout_py(app: KrakenLayoutEditor, output_path: Path) -> None:
    """Persist the editor state to a self-contained ``.py`` layout file.

    Uses the same writer the File -> Save menu invokes; no Tk file
    dialog because we set ``current_layout_file`` first.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    app.current_layout_file = output_path
    if not app.save_layout():
        raise RuntimeError("save_layout returned False -- writer rejected the file path")


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        inspector = _open_inspector(app)
        summary = _build_layout(app, inspector)
        # Force the editor to read back the rows it has so the writer
        # sees the post-promote table state.
        try:
            app._read_rows_from_table()
        except Exception:
            pass
        _save_layout_py(app, OUTPUT_LAYOUT)
        print("Built penta-prism + telescope cascade:")
        for key, value in summary.items():
            print(f"  {key}: {value}")
        print(f"\nSaved layout -> {OUTPUT_LAYOUT}")
        print(
            "\nOpen the layout in the inspector:\n"
            f"  .devenv/state/venv/bin/python -m KrakenOS\n"
            f"  File -> Open  ->  {OUTPUT_LAYOUT.name}\n"
        )
        return 0
    except Exception as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
