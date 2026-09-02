"""0692 (user question): can the arms reach the FULL sensor or just strips?

Sweep object-field y (x=0) far beyond the authored band, plus x extremes at a
mid-band y, through the real chain launch. The additive faceB source mirrors the
same grid, so ONE run measures BOTH arms. For every launched field report how
many rays land ON the sensor plane (|end_y + 9.9| < 1, x < -250) and WHERE
(end x/z) -- the sensor-side landing map tells whether the optics could ever
fill the 23.04 x 23.04 sensor or only the split-field strips.

NOTE (census bugs/0692_sweep_census.py): chain rays carry source_id "source:0",
NOT empty -- classify by == "source:faceB" like the 0672 guard, never by truthiness.
"""
from pathlib import Path

import numpy as np


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path("attachment/om05a_folded.py").resolve()
    editor.load_layout_by_name("p")
    editor._preview_trace_deferred_until_requested = False

    ys = [float(y) for y in np.linspace(-16.0, 16.0, 33)]
    x_probe = [(-30.0, -1.0), (-27.5, -1.0), (27.5, -1.0), (30.0, -1.0)]
    editor._sample_imaging_field_grid_pairs = lambda: [(0.0, y) for y in ys] + x_probe

    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
    rows = getattr(editor, "rows", None) or []
    img_pt = np.asarray(
        editor._surface_reference_world_point(len(rows) - 1, system=system), dtype=float
    ).reshape(3)
    print("sensor row centre:", np.round(img_pt, 2), "(square 23.04 x 23.04 in x/z)")
    sensor_y = float(img_pt[1])

    arms = {
        "A": {y: [0, 0, [], []] for y in ys},
        "B": {y: [0, 0, [], []] for y in ys},
    }
    per_x = {x: [0, 0, [], []] for (x, _) in x_probe}
    binned = stray = 0
    for rp in (bundle.ray_paths or []):
        sid = str(getattr(rp, "source_id", "") or "")
        arm = "B" if sid == "source:faceB" else "A"
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim != 2 or p.shape[0] < 2 or not np.all(np.isfinite(p[0])):
            continue
        lx, ly = float(p[0][0]), float(p[0][1])
        end = p[-1]
        on_sensor = (
            bool(np.all(np.isfinite(end)))
            and abs(float(end[1]) - sensor_y) < 1.0
            and float(end[0]) < -250.0
        )
        if abs(lx) < 0.6:
            y0 = min(ys, key=lambda y: abs(y - ly))
            if abs(y0 - ly) > 0.6:
                stray += 1
                continue
            slot = arms[arm][y0]
        elif arm == "A":
            x0 = min(per_x.keys(), key=lambda x: abs(x - lx))
            if abs(x0 - lx) > 0.9:
                stray += 1
                continue
            slot = per_x[x0]
        else:
            stray += 1
            continue
        binned += 1
        slot[0] += 1
        if on_sensor:
            slot[1] += 1
            slot[2].append(float(end[0]))
            slot[3].append(float(end[2]))

    if binned == 0:
        raise SystemExit("FAIL LOUDLY: traced but binned nothing -- filter is wrong again")

    for arm in ("A", "B"):
        print(f"\n--- arm {arm} y-scan (x=0): object y -> sensor landing (z = strip axis) ---")
        band_z = []
        for y in ys:
            launched, hit, exs, ezs = arms[arm][y]
            if not launched:
                continue
            mark = "#" * int(round(10 * hit / launched))
            where = ""
            if ezs:
                where = f"  end z {min(ezs):+7.2f}..{max(ezs):+7.2f} (x~{np.mean(exs):+6.1f})"
                if -5.25 <= y <= 3.1:
                    band_z += ezs
            print(f"  y {y:+6.1f}: {hit:3d}/{launched:3d} {mark:10s}{where}")
        if band_z:
            print(f"  arm {arm} IN-BAND strip: z {min(band_z):+.2f} .. {max(band_z):+.2f}")
    print("\n--- x-probe arm A (y=-1): object x -> sensor landing ---")
    for x in sorted(per_x.keys()):
        launched, hit, exs, ezs = per_x[x]
        if not launched:
            continue
        where = f"  end x {min(exs):+7.2f}..{max(exs):+7.2f}" if exs else ""
        print(f"  x {x:+6.1f}: {hit:3d}/{launched:3d}{where}")
    all_hits_z = [z for arm in arms for y in ys for z in arms[arm][y][3]]
    if all_hits_z:
        print(f"\nall landings z span {min(all_hits_z):+.2f} .. {max(all_hits_z):+.2f} "
              f"(sensor z range {img_pt[2] - 11.52:+.2f} .. {img_pt[2] + 11.52:+.2f})")
    print(f"binned {binned}, stray/unbinned {stray}")
    editor.destroy()


if __name__ == "__main__":
    main()
