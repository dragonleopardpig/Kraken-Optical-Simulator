"""0687 (flag 201645): per-station chief-path check -- where does the beam enter
GLASS before a Mirror flank (second-surface), and where do the field columns land
per field (the red defocus)?"""
from pathlib import Path

import numpy as np


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path("attachment/om05a_folded.py").resolve()
    editor.load_layout_by_name("p")
    editor._preview_trace_deferred_until_requested = False
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)

    paths = [rp for rp in (bundle.ray_paths or [])
             if str(getattr(rp, "source_id", "") or "") != "source:faceB"]
    chief = None
    for rp in paths:
        p = np.asarray(rp.points_world, dtype=float)
        if p.ndim != 2 or not np.all(np.isfinite(p[0])):
            continue
        score = abs(p[0][0]) + abs(p[0][1])
        if chief is None or score < chief[0]:
            chief = (score, p)
    print("chief polyline (world):")
    for q in chief[1]:
        print("  ", np.round(q, 2).tolist())

    # per-field endpoint spread at the sensor (the red-defocus check)
    groups = {}
    for rp in paths:
        if not bool(getattr(rp, "reaches_image", False)):
            continue
        p = np.asarray(rp.points_world, dtype=float)
        x0 = round(float(p[0][0]) / 13.4) * 13.4
        groups.setdefault(x0, []).append(p[-1])
    for x0 in sorted(groups):
        E = np.asarray(groups[x0])
        rms = float(np.sqrt(((E[:, [0, 2]] - E[:, [0, 2]].mean(axis=0)) ** 2).sum(axis=1).mean()))
        print(f"field x0 {x0:+6.1f}: {len(E):3d} rays, sensor spot rms {rms * 1000:7.1f} um, "
              f"centre ({E[:,0].mean():.2f}, {E[:,2].mean():.2f})")
    editor.destroy()


if __name__ == "__main__":
    main()
