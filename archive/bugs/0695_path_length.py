"""0695: measure each arm's geometric path length from launch to the lens front
datum plane (x = -214.92) and to the sensor plane -- arm B focuses 19.2 mm
later than arm A; find where the length divides."""
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

    shown = {"A": 0, "B": 0}
    for rp in (getattr(bundle, "ray_paths", None) or []):
        sid = str(getattr(rp, "source_id", "") or "")
        arm = "B" if sid == "source:faceB" else "A"
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim != 2 or p.shape[0] < 2 or not np.all(np.isfinite(p)):
            continue
        if abs(float(p[0][0])) > 0.8 or float(p[-1][0]) > -250.0:
            continue
        if shown[arm] >= 2:
            continue
        shown[arm] += 1
        total = 0.0
        at_datum = None
        print(f"--- arm {arm} launch {np.round(p[0], 2)}")
        for a, b in zip(p[:-1], p[1:]):
            seg = float(np.linalg.norm(b - a))
            # crossing the lens-front datum plane x=-214.92 during this segment?
            if at_datum is None and a[0] > -214.92 >= b[0]:
                f = (a[0] - (-214.92)) / (a[0] - b[0])
                at_datum = total + f * seg
            total += seg
        print(f"    length to lens-front datum: {at_datum}; total to end: {total:.2f}; "
              f"end {np.round(p[-1], 2)}")
    editor.destroy()


if __name__ == "__main__":
    main()
