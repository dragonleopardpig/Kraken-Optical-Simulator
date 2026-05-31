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
    CYL_STEP,
    BALL_LENS_GAP_MM,
    PHASE1_CLEARANCE_FROM_PRISM_MM,
    PHASE2_GAP_FROM_BALL_2_MM,
    PHASE3_GAP_FROM_ACHROMAT_MM,
    _load_penta_cascade,
    _open_inspector,
    _set_exit_axis_from_trace,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_LAYOUT = PROJECT_ROOT / "attachment" / "five_penta_prism_analytic_telescope_cascade.py"

# Local DCV + Achromat overrides: the chain validator points at
# f=-50/f=+50 stock parts whose Galilean separation is degenerate
# (DCV+Achromat with f_eye+f_obj = 0 cannot collimate at non-zero
# spacing). We swap in f=-25 DCV + f=+125 Achromat so the existing
# 100 mm gap satisfies the collimation condition f1+f2=d for a 5x
# beam expander (input 3 mm -> output 15 mm, fits 25 mm achromat).
DCV_STEP = PROJECT_ROOT / "attachment" / "Lens" / "DCV" / "32992" / "step_32992.stp"
ACHROMAT_STEP = (
    PROJECT_ROOT
    / "attachment"
    / "Lens"
    / "Achromatic_Lenses"
    / "AC254-125-A"
    / "AC254-125-A-Step.step"
)
# Override the inherited 100 mm so the relationship is explicit
# in this file -- if the user later swaps lens powers, both the
# value and the formula live here.
F_DCV_MM = -25.0
F_ACHROMAT_MM = +125.0
DCV_TO_ACHROMAT_GAP_MM = float(F_ACHROMAT_MM + F_DCV_MM)  # 100 mm


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
        "name": "DCV f=-25 mm (N-SF11)",
        "step": DCV_STEP,
        "glass": "N-SF11",
        "offset_along_exit_mm": (
            PHASE1_CLEARANCE_FROM_PRISM_MM
            + BALL_LENS_GAP_MM
            + PHASE2_GAP_FROM_BALL_2_MM
        ),
        "gap_after_mm": DCV_TO_ACHROMAT_GAP_MM,
    },
    {
        "name": "Achromat f=+125 mm (BK7/SF5)",
        "step": ACHROMAT_STEP,
        # AC254-125-A is a cemented doublet: BK7 front + SF5 cement
        # + AIR back. Three glasses -> promote service auto-routes
        # through OCC Native Rows to preserve the cement-layer Rc.
        "glass": "N-BK7, N-SF5, AIR",
        "offset_along_exit_mm": (
            PHASE1_CLEARANCE_FROM_PRISM_MM
            + BALL_LENS_GAP_MM
            + PHASE2_GAP_FROM_BALL_2_MM
            + DCV_TO_ACHROMAT_GAP_MM
        ),
        "gap_after_mm": PHASE3_GAP_FROM_ACHROMAT_MM,
    },
    {
        # Edmund 34754 plano-cylindrical lens: N-BK7, R=25.84 mm
        # cylindrical (curved in one axis only), f=+50 mm. Promoted
        # via the analytic_parameters fast-path in the analytic-fit
        # service -- OCC preserves surface_type=cylinder with the
        # exact radius_mm, which we encode as a Standard row with
        # Cylinder_Rxy_Ratio=0 (pure plano-cyl, no Y curvature).
        "name": "Cylindrical 1 f=+50 mm (N-BK7, plano-cyl)",
        "step": CYL_STEP,
        "glass": "N-BK7",
        "offset_along_exit_mm": (
            PHASE1_CLEARANCE_FROM_PRISM_MM
            + BALL_LENS_GAP_MM
            + PHASE2_GAP_FROM_BALL_2_MM
            + DCV_TO_ACHROMAT_GAP_MM
            + PHASE3_GAP_FROM_ACHROMAT_MM
        ),
        # Cyl 1 -> Cyl 2 separation = f1 + f2 = 50 + 50 = 100 mm
        # (1:1 Keplerian cyl telescope: cyl 1 focuses parallel
        # input to a LINE focus at +50 mm; cyl 2 collects the
        # diverging beam from that line and re-collimates).
        "gap_after_mm": 100.0,
    },
    {
        # Second Edmund 34754, identical to Cyl 1. Together with
        # Cyl 1 at 100 mm = 2f separation they form a 1:1 cyl
        # Keplerian telescope: parallel input -> parallel output,
        # but inverted in the meridional axis (sign flip of the X
        # field component).
        "name": "Cylindrical 2 f=+50 mm (N-BK7, plano-cyl)",
        "step": CYL_STEP,
        "glass": "N-BK7",
        "offset_along_exit_mm": (
            PHASE1_CLEARANCE_FROM_PRISM_MM
            + BALL_LENS_GAP_MM
            + PHASE2_GAP_FROM_BALL_2_MM
            + DCV_TO_ACHROMAT_GAP_MM
            + PHASE3_GAP_FROM_ACHROMAT_MM
            + 100.0  # Cyl 1 -> Cyl 2 spacing
        ),
        "gap_after_mm": 50.0,
    },
]


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
    # Override the source aperture inherited from the cascade base
    # (4 mm radius) -- too wide for analytic ball lenses (R=4.76 mm),
    # so marginal rays at r/R=0.84 produce ~30 deg spherical
    # aberration fans. 1.5 mm keeps r/R<0.31 inside the paraxial
    # region; the saved layout's traced rays read cleanly through
    # the whole chain instead of fanning out after the ball lenses.
    try:
        app.source_radius_var.set("1.5")
    except Exception:
        pass
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

    # Tilt that aligns local +Z (the Standard surface's chain-z
    # forward direction) with the cascade exit direction. KrakenOS
    # places the sphere centre at vertex + Rc * (local +Z), so
    # mapping local +Z to the ray-propagation direction makes:
    #   * Rc>0 front face -> sphere centre downstream of vertex
    #     (inside the glass body, which is correct -- the cap
    #     bulges upstream into the incoming-ray side and the
    #     hemisphere extends from the vertex toward the body
    #     centre).
    #   * Rc<0 back face -> sphere centre upstream of vertex
    #     (also inside the body), so a ball lens's two hemispheres
    #     share a single centre and render as one sphere.
    if np.allclose(exit_dir, (-1.0, 0.0, 0.0)):
        row_tilt = (0.0, -90.0, 0.0)  # local +Z -> world -X
    elif np.allclose(exit_dir, (1.0, 0.0, 0.0)):
        row_tilt = (0.0, 90.0, 0.0)   # local +Z -> world +X
    elif np.allclose(exit_dir, (0.0, -1.0, 0.0)):
        row_tilt = (90.0, 0.0, 0.0)   # local +Z -> world -Y
    elif np.allclose(exit_dir, (0.0, 1.0, 0.0)):
        row_tilt = (-90.0, 0.0, 0.0)  # local +Z -> world +Y
    elif np.allclose(exit_dir, (0.0, 0.0, -1.0)):
        row_tilt = (180.0, 0.0, 0.0)
    else:
        row_tilt = (0.0, 0.0, 0.0)

    # First row's z_station equals the cumulative thickness of all
    # rows BEFORE the first lens. For the cascade that's
    # Object.thickness + sum(prism thicknesses=0) = 100 mm.
    z_station_before_lenses = sum(
        float(getattr(app.rows[i], "thickness", 0.0) or 0.0)
        for i in range(int(base["row_count"]))
    )

    promoted_rows: list[dict[str, Any]] = []
    for spec in LENS_SPECS:
        try:
            app.clear_step_imports()
        except Exception:
            pass
        # World position of the LENS BODY CENTROID along the exit
        # beam. Each row of the lens will then be shifted further
        # along -exit_dir by its cumulative optical thickness so the
        # surface vertices are positioned correctly.
        anchor_world = exit_pt + exit_dir * float(spec["offset_along_exit_mm"])
        _import_step(
            app,
            spec["step"],
            placement_offset_xyz=(
                float(anchor_world[0]),
                float(anchor_world[1]),
                float(anchor_world[2]),
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

        # Post-promote placement: walk each row of THIS lens and set
        # its world position along the exit beam.
        #
        # The promote service returns rows in optical order (front,
        # [cement,] back) with thickness = optical path through that
        # segment. To make the lens render symmetrically about the
        # anchor (so a ball lens's front and back hemispheres share
        # a centre, not two outward-bulging caps connected by a
        # cylindrical shell), we centre the row group on
        # anchor_world: the midpoint of the first and last row sits
        # at the anchor; each row is then offset from that midpoint
        # by its cumulative optical-path distance from the front,
        # minus half the total optical path.
        #
        # Chain-z stays world +Z (AxisMove=0 everywhere), so each
        # row's desp_z = world_z_target - z_station_for_that_row.
        # We zero the row thicknesses we placed so chain-z stays at
        # z_station_before_lenses for every subsequent row.
        original_thicknesses: list[float] = []
        for row_idx in indices:
            try:
                original_thicknesses.append(
                    float(getattr(app.rows[int(row_idx)], "thickness", 0.0) or 0.0)
                )
            except Exception:
                original_thicknesses.append(0.0)
        # Optical path = sum of all thicknesses EXCEPT the last
        # (the last row's thickness is the gap to the NEXT lens,
        # which is bookkeeping, not a body distance).
        body_segments = original_thicknesses[:-1] if len(original_thicknesses) > 1 else []
        body_thickness = float(sum(body_segments))
        front_to_centre = 0.5 * body_thickness
        cumulative_offset = 0.0
        for idx_in_lens, row_idx in enumerate(indices):
            try:
                row = app.rows[int(row_idx)]
            except Exception:
                continue
            # Offset of THIS row's vertex from the lens centre,
            # measured along the exit beam.
            centre_offset = front_to_centre - cumulative_offset
            row_world = anchor_world + exit_dir * (-centre_offset)
            row.desp_x = float(row_world[0])
            row.desp_y = float(row_world[1])
            row.desp_z = float(row_world[2] - z_station_before_lenses)
            row.tilt_x = float(row_tilt[0])
            row.tilt_y = float(row_tilt[1])
            row.tilt_z = float(row_tilt[2])
            row.axis_move = 0.0
            row.thickness = 0.0
            if idx_in_lens < len(body_segments):
                cumulative_offset += body_segments[idx_in_lens]
        try:
            app._sync_table()
        except Exception:
            pass

        promoted_rows.append(
            {
                "lens": spec["name"],
                "first_row": int(indices[0]),
                "rows_added": len(indices),
                "glass_sequence": spec["glass"],
                "anchor_world": [float(v) for v in anchor_world.tolist()],
                "optical_span_mm": float(cumulative_offset),
            }
        )
        inspector.refresh_from_editor()
        inspector.update_idletasks()

    # When the same STEP fixture is promoted twice (e.g. cyl 1 +
    # cyl 2 for a cyl Keplerian telescope), the second promote
    # sometimes inserts BEFORE the first lens's rows due to the
    # insert_at logic in step_overlay_promotion. The chain rows
    # end up out of geometric order, which breaks sequential
    # trace. Reorder all "interior" rows (Object excluded at the
    # start, Image excluded at the end) by their world-frame
    # axial position along the exit beam so the row sequence
    # matches the ray's actual path.
    if len(app.rows) > 3:
        body_rows = list(app.rows)
        head = body_rows[: int(base["row_count"]) - 1]  # Object + prisms (kept as-is)
        tail = body_rows[-1:]  # Image
        middle = body_rows[int(base["row_count"]) - 1 : -1]
        # Sort middle by axial-position along exit_dir descending.
        def _axial_pos(row) -> float:
            try:
                return float(
                    exit_dir[0] * float(getattr(row, "desp_x", 0.0) or 0.0)
                    + exit_dir[1] * float(getattr(row, "desp_y", 0.0) or 0.0)
                    + exit_dir[2] * float(getattr(row, "desp_z", 0.0) or 0.0)
                )
            except Exception:
                return 0.0
        middle.sort(key=_axial_pos)
        app.rows = head + middle + tail
        try:
            app._sync_table()
        except Exception:
            pass

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
