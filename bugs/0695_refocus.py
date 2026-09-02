"""0695 stage 4: measured refocus after the vendor-true rebuild + re-seat.

Measures the arm-A central-field waist along the final -y leg and moves the
Image row onto it by adjusting mirror2's row thickness (the 0691 mechanism:
thickness -= (waist_y - sensor_y); the leg travels -y). One measured iteration,
then re-verify -- never a one-shot correction without a re-measure (0625).
"""
import os
from pathlib import Path

import numpy as np

SCENE = Path("attachment/om05a_folded.py")


def rebake_free_placed(editor):
    """Changing ANY row thickness shifts the stations of every later row, which
    silently drags free-placed solids (desp = centre - station) off their world
    poses -- the 0691 refocus (-1.46) is exactly how the B-arm got its measured
    1.46 mm asymmetry (0694), and this run's -4.08 killed arm A outright.
    Re-derive desp from the STORED promotion centre at the new stations."""
    from KrakenOS.UI.nonseq_output_ports import row_z_positions

    zs = row_z_positions(editor.rows)
    n = 0
    for index, row in enumerate(editor.rows):
        promo = (row.advanced or {}).get("StepOverlayPromotion")
        centre = (promo or {}).get("center_world") if isinstance(promo, dict) else None
        if centre is None:
            continue
        c = np.asarray(centre, dtype=float).reshape(3)
        z_station = float(zs[index]) if index < len(zs) else 0.0
        row.desp_x, row.desp_y = float(c[0]), float(c[1])
        row.desp_z = float(c[2]) - z_station
        n += 1
    return n
APPLY = os.environ.get("KRAKEN_0695_APPLY", "1") == "1"


def measure(editor):
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
    rows = editor.rows
    img_row = next(i for i, r in enumerate(rows) if str(r.surface) == "Image")
    sensor_y = float(np.asarray(
        editor._surface_reference_world_point(img_row, system=system), dtype=float
    )[1])
    segs = []
    for rp in (getattr(bundle, "ray_paths", None) or []):
        sid = str(getattr(rp, "source_id", "") or "")
        if sid == "source:faceB":
            continue
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim != 2 or p.shape[0] < 2 or not np.all(np.isfinite(p)):
            continue
        if abs(float(p[0][0])) > 1.5:      # central field column only
            continue
        e = p[-1]
        # anchor on the LIGHT, not the sensor row: any ray that made the final
        # leg (x < -250) counts; the previous |end - sensor| < 8 window caught a
        # stray sliver and dragged the sensor 4 mm the wrong way.
        if not (float(e[0]) < -250.0):
            continue
        a, b = p[-2], p[-1]
        if abs(float(b[1] - a[1])) < 1e-9:
            continue
        segs.append((a, b))
    if len(segs) < 20:
        return sensor_y, None, None, len(segs)
    A = np.array([s[0] for s in segs])
    B = np.array([s[1] for s in segs])
    D = B - A
    best = (None, np.inf)
    for y in np.linspace(sensor_y - 60.0, sensor_y + 60.0, 1201):
        t = (y - A[:, 1]) / D[:, 1]
        pts = A + t[:, None] * D
        c = pts.mean(axis=0)
        rms = float(np.sqrt(np.mean((pts[:, 0] - c[0]) ** 2 + (pts[:, 2] - c[2]) ** 2)))
        if rms < best[1]:
            best = (float(y), rms)
    return sensor_y, best[0], best[1], len(segs)


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = SCENE.resolve()
    editor.load_layout_by_name("p")
    editor._preview_trace_deferred_until_requested = False

    n0 = rebake_free_placed(editor)
    print(f"pre-pass rebake of {n0} free-placed rows (heals earlier thickness drags)")
    editor._sync_table()
    editor._write_layout_file(SCENE.resolve())
    for iteration in range(3):
        sensor_y, waist_y, waist_rms, n = measure(editor)
        print(f"[{iteration}] sensor y {sensor_y:.3f}; central waist y {waist_y} rms "
              f"{None if waist_rms is None else round(waist_rms * 1000, 1)}um ({n} rays)")
        if waist_y is None:
            raise SystemExit("FAIL LOUDLY: not enough central-field rays to measure")
        delta = waist_y - sensor_y
        if abs(delta) < 0.1:
            print("focused within 0.1 mm")
            break
        if not APPLY:
            print(f"would adjust mirror2 thickness by {-delta:+.3f}")
            return
        m2 = next(i for i, r in enumerate(editor.rows)
                  if str(getattr(r, "name", "")) == "RA mirror 2 (40 mm)")
        old = float(editor.rows[m2].thickness)
        editor.rows[m2].thickness = old - delta
        print(f"    mirror2 thickness {old:.3f} -> {editor.rows[m2].thickness:.3f}; "
              f"re-baked {rebake_free_placed(editor)} free-placed rows")
        editor._sync_table()
        editor._write_layout_file(SCENE.resolve())
        editor.destroy()
        editor = KrakenLayoutEditor()
        editor._prompt_for_missing_cad_assets = lambda: None
        editor.layout_files["p"] = SCENE.resolve()
        editor.load_layout_by_name("p")
        editor._preview_trace_deferred_until_requested = False
    editor.destroy()


if __name__ == "__main__":
    main()
