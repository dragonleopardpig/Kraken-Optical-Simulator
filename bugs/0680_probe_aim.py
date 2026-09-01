"""0680: find the apparent entrance pupil seen from face B -- the common crossing
point of the B rays that complete to the sensor. Full-count trace of the additive
source in the stage-2 work scene."""
from pathlib import Path

import numpy as np


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path("attachment/om05a_symB_work.py").resolve()
    editor.load_layout_by_name("p")
    cls = type(editor)
    editor._build_additive_imaging_source_bundles = (
        lambda wl, full_count=False: cls._build_additive_imaging_source_bundles(
            editor, wl, full_count=True
        )
    )
    editor._preview_trace_deferred_until_requested = False
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
    starts, dirs = [], []
    n_b = 0
    for rp in (bundle.ray_paths or []):
        if str(getattr(rp, "source_id", "") or "") != "source:faceB":
            continue
        n_b += 1
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim != 2 or len(p) < 2 or not np.all(np.isfinite(p[-1])):
            continue
        end = p[-1]
        if abs(end[0] + 272.7) < 15 and abs(end[1] + 11) < 20:
            d = p[1] - p[0]
            n = np.linalg.norm(d)
            if n > 1e-9:
                starts.append(p[0])
                dirs.append(d / n)
    print(f"faceB rays traced: {n_b}, reaching: {len(starts)}")
    if len(starts) >= 3:
        S = np.asarray(starts)
        D = np.asarray(dirs)
        # least-squares point closest to all launch lines
        A = np.zeros((3, 3))
        b = np.zeros(3)
        for s, d in zip(S, D):
            P = np.eye(3) - np.outer(d, d)
            A += P
            b += P @ s
        aim = np.linalg.solve(A, b)
        print(f"apparent pupil (least-squares crossing): {np.round(aim, 2).tolist()}")
        t = ((aim - S) * D).sum(axis=1)
        print(f"distance from launch plane: mean {t.mean():.1f} mm")
        print(f"launch x span of reaching rays: {S[:,0].min():.1f} .. {S[:,0].max():.1f}")
    editor.destroy()


if __name__ == "__main__":
    main()
