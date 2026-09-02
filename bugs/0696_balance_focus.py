"""0696: put the sensor at the BALANCED focus between the two arms' waists
(A -2.10, B -1.30 -> midpoint -1.70): both arms ~19 um instead of 2/38 split."""
from pathlib import Path
import importlib.util
import numpy as np

SCENE = Path("attachment/om05a_folded.py")
spec = importlib.util.spec_from_file_location("refocus0695", "bugs/0695_refocus.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = SCENE.resolve()
    editor.load_layout_by_name("p")
    editor._preview_trace_deferred_until_requested = False

    # measure BOTH arms' central waists
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
    img_row = next(i for i, r in enumerate(editor.rows) if str(r.surface) == "Image")
    sensor_y = float(np.asarray(
        editor._surface_reference_world_point(img_row, system=system), dtype=float)[1])
    waists = {}
    for arm in ("A", "B"):
        segs = []
        for rp in (getattr(bundle, "ray_paths", None) or []):
            is_b = str(getattr(rp, "source_id", "") or "") == "source:faceB"
            if (arm == "B") != is_b:
                continue
            p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
            if p.ndim != 2 or p.shape[0] < 2 or not np.all(np.isfinite(p)):
                continue
            if abs(float(p[0][0])) > 1.5 or float(p[-1][0]) > -250.0:
                continue
            a, b = p[-2], p[-1]
            if abs(float(b[1] - a[1])) > 1e-9:
                segs.append((a, b - a))
        A = np.array([s[0] for s in segs]); D = np.array([s[1] for s in segs])
        best = (None, np.inf)
        for y in np.linspace(sensor_y - 30, sensor_y + 30, 1201):
            t = (y - A[:, 1]) / D[:, 1]
            pts = A + t[:, None] * D
            c = pts.mean(axis=0)
            r = float(np.sqrt(np.mean((pts[:, 1] - c[1]) * 0 + (pts[:, 0] - c[0]) ** 2 + (pts[:, 2] - c[2]) ** 2)))
            if r < best[1]:
                best = (float(y), r)
        waists[arm] = best
        print(f"arm {arm}: waist y {best[0]:.3f} rms {best[1]*1000:.1f}um ({len(segs)} rays)")
    target = 0.5 * (waists["A"][0] + waists["B"][0])
    delta = target - sensor_y
    print(f"sensor {sensor_y:.3f} -> balanced target {target:.3f} (delta {delta:+.3f})")
    if abs(delta) > 0.05:
        m2 = next(i for i, r in enumerate(editor.rows)
                  if str(getattr(r, "name", "")) == "RA mirror 2 (40 mm)")
        old = float(editor.rows[m2].thickness)
        editor.rows[m2].thickness = old - delta
        n = m.rebake_free_placed(editor)
        print(f"mirror2 thickness {old:.3f} -> {editor.rows[m2].thickness:.3f}; re-baked {n}")
        editor._sync_table()
        editor._write_layout_file(SCENE.resolve())
        print("saved")
    editor.destroy()


if __name__ == "__main__":
    main()
