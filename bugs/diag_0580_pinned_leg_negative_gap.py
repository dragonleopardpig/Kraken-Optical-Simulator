"""Replay recording_20260807_073557 (flags 072907/073042/073242/073438) headlessly.

The user's morning sequence on machine_vision_Apo75.py, all on build 423052ec:

  1. load Apo75, swap to PYRITE 45-85            -> "works"           (flag 072907)
  2. fov_solve object/thickness 55x55
     + image_segment pin ("far", 30.0)           -> "works"           (flag 073042)
  3. swap to ELS-85                              -> "works" (visually)
  4. fov_solve object/thickness 23x23 (no pin)   -> defocus at sensor (flag 073242)
  5. right-click remove defocus                  -> no-op; lens + RA mirror OFF AXIS (flag 073438)

What the two flag states already measure (promoted rows 6 = BS solid, 7 = RA prism):

  flag 073042 ("works"): row6.thickness 52.6084, row7.thickness -5.0269  <-- NEGATIVE frozen gap
  flag 073242/073438   : row6.thickness 47.5815, row7.thickness  0.0
                          sum preserved (sensor stayed), but the PRISM dropped z 54.33 -> 49.31
                          -- 5.03 mm off its leg, exactly the redistributed amount.

So the suspicion is a two-writer story: the ("far", 30.0) PIN wrote a negative row7 gap without
complaint (the poison), and something during the ELS swap/solve "cleaned it up" by clamping row7
to 0 and pushing -5.03 into row6 -- which moves the PRISM along the station axis, off its leg
(a fold-leg position lives in desp, bugs/0499 -- thickness moves stations).

This script prints the row6/row7 gaps, the prism's world z against the leg z, the sensor, the
lens attach error and the landed-ray count after EVERY step, plus the relevant debug lines, so
each writer indicts itself.

Run (capped -- one heavy job at a time, the desktop keeps cores):
    taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python bugs/diag_0580_pinned_leg_negative_gap.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Apo75.py"
PYRITE = PROJECT_ROOT / "attachment" / "Lens" / "PYRITE_45_85_05x-20x_V38_1072517"
ELS85 = PROJECT_ROOT / "attachment" / "Lens" / "ELS-85-4.5V16K"

EXPECT = {
    "after 55x55 + far=30 pin": {"row6": 52.6084, "row7": -5.0269},
    "after ELS-85 swap + 23x23 solve": {"row6": 47.5815, "row7": 0.0},
}


def _ray_hits(app) -> int:
    try:
        _s, _r, bundle = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=True, trace_rays=True
        )
    except Exception:
        return -1
    return sum(
        1
        for p in list(getattr(bundle, "ray_paths", None) or [])
        if str(getattr(p, "termination_reason", "")) == "target_termination"
    )


def _leg_z(app):
    """z of the BS-reflect leg the lens block and the prism must sit on."""
    try:
        for rec in app._optical_axis_guide_records():
            if str(rec.get("axis_id")) == "axis:global:split":
                return float(np.asarray(rec["points"], dtype=float)[0][2])
    except Exception:
        pass
    return None


def _report(app, tag: str) -> dict:
    from KrakenOS.UI.services import row_placement

    rows = app.rows
    n = len(rows)
    r6 = float(rows[6].thickness)
    r7 = float(rows[7].thickness)
    prism = np.asarray(row_placement.world_pose(app, 7).position, dtype=float)
    sensor = np.asarray(row_placement.world_pose(app, n - 1).position, dtype=float)
    leg = _leg_z(app)
    body = None
    datum = None
    try:
        mesh = app._transformed_imported_step_mesh_for_label("lens")
        b = np.asarray(mesh.bounds, dtype=float)
        body = np.array([(b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2])
    except Exception:
        pass
    try:
        datum = np.asarray(app._lens_surrogate_datum_mid_world(), dtype=float).reshape(3)
    except Exception:
        pass
    hits = _ray_hits(app)
    print(f"\n--- {tag}")
    print(f"    row6.thickness {r6:+10.4f}   row7.thickness {r7:+10.4f}   sum {r6 + r7:+10.4f}")
    off = None if leg is None else prism[2] - leg
    print(f"    prism world    {np.round(prism, 4).tolist()}   leg z {leg}   OFF-LEG dz {off if off is None else f'{off:+.4f}'} mm")
    print(f"    sensor world   {np.round(sensor, 4).tolist()}")
    if body is not None and datum is not None:
        print(f"    lens body mid  {np.round(body, 4).tolist()}   datum mid {np.round(datum, 4).tolist()}")
    print(f"    rays landed    {hits}")
    return {"row6": r6, "row7": r7, "prism_z": float(prism[2]), "leg": leg, "hits": hits}


def _debug_tail(app, count: int = 18) -> None:
    try:
        text = str(app.debug_text.get("1.0", "end")).splitlines()
    except Exception:
        return
    keys = ("snap detector iter", "lens leg slide", "fold arm slide", "image split",
            "near leg", "frozen image", "deferred", "re-measured", "reverting",
            "Center lens body", "clearance", "floor")
    for line in [l for l in text if any(k in l for k in keys)][-count:]:
        print("    |", line.strip())


def main() -> int:
    if not SCENE.exists() or not PYRITE.exists() or not ELS85.exists():
        print("SKIP: scene or a lens folder is missing")
        return 0

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

    app = KrakenLayoutEditor()
    try:
        app.layout_files["scene"] = SCENE
        app.load_layout_by_name("scene")
        inspector = _open_inspector(app)
        qe = inspector._quick_estimation_service()

        _report(app, "AS LOADED (Apo75)")

        app.swap_imaging_lens_from_folder(str(PYRITE), refresh=False)
        _report(app, "AFTER PYRITE SWAP (flag 072907)")

        ok, msg = qe.fov_solve("object", "thickness", 55.0, 55.0, None)
        print(f"\nfov_solve 55x55 -> {ok}: {str(msg)[:140]}")
        ok_pin, msg_pin = app._apply_folded_image_split("far", 30.0)
        print(f"image pin far=30 -> {ok_pin}: {str(msg_pin)[:140]}")
        # The inspector's _apply_quick_estimation_fov_solve syncs the table after every solve.
        # A headless replay must too: swap_imaging_lens_from_folder BEGINS with
        # _read_rows_from_table(), which rebuilds the model from the DISPLAYED cells -- skip the
        # sync and that re-read reverts every row write since the last one (measured: it moved
        # the fold mirror back to its pre-pin seat, x 334.37 -> 281.76, mid-swap).
        app._sync_table()
        _debug_tail(app)
        s1 = _report(app, "AFTER 55x55 + far=30 pin (flag 073042 'works')")

        app.swap_imaging_lens_from_folder(str(ELS85), refresh=False)
        _debug_tail(app)
        s2 = _report(app, "AFTER ELS-85 SWAP")

        ok, msg = qe.fov_solve("object", "thickness", 23.0, 23.0, None)
        print(f"\nfov_solve 23x23 (no pin) -> {ok}: {str(msg)[:160]}")
        _debug_tail(app)
        s3 = _report(app, "AFTER 23x23 SOLVE (flag 073242 'defocus at sensor')")

        moved = False
        try:
            moved = bool(app.snap_detector_to_image_plane())
        except Exception as exc:
            print(f"snap raised {type(exc).__name__}: {exc}")
        print(f"\nremove defocus -> moved={moved}  status={app.status_var.get()!r}")
        _debug_tail(app)
        _report(app, "AFTER REMOVE DEFOCUS (flag 073438 'not working, off axis')")

        print("\n" + "=" * 74)
        print("FLAG COMPARISON (recorded live values in brackets):")
        print(f"  073042: row6 {s1['row6']:+.4f} [{EXPECT['after 55x55 + far=30 pin']['row6']:+.4f}]  "
              f"row7 {s1['row7']:+.4f} [{EXPECT['after 55x55 + far=30 pin']['row7']:+.4f}]")
        print(f"  073242: row6 {s3['row6']:+.4f} [{EXPECT['after ELS-85 swap + 23x23 solve']['row6']:+.4f}]  "
              f"row7 {s3['row7']:+.4f} [{EXPECT['after ELS-85 swap + 23x23 solve']['row7']:+.4f}]")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
