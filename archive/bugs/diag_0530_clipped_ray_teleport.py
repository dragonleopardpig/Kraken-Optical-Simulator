"""bugs/0530 diagnostic -- flag_20260804_073933 "enabled clipped overlay, rays not make
sense." Quantifies the missed_image population on the flag's scene state (dragged lens,
sensor at fresh seat): how far each escaped ray was projected to reach the detector plane
(travel distance) and how far off-sensor it landed (radial vs active half), so the fix can
separate genuine near-misses from teleported prism-missers.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        # The flag state: composite written, no refocus (the 0528-era defocused config).
        app.translate_step_overlay("lens", (53.135, 0.0, 0.0))

        system, rays, bundle = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=False, trace_rays=True
        )
        paths = list(getattr(bundle, "ray_paths", []) or [])
        print(f"paths: {len(paths)}")
        census: dict[str, int] = {}
        rows = []
        for p in paths:
            reason = str(getattr(p, "termination_reason", "") or "")
            census[reason] = census.get(reason, 0) + 1
            if reason != "missed_image":
                continue
            events = list(getattr(p, "events", []) or [])
            terminal = events[-1] if events else None
            meta = (getattr(terminal, "metadata", None) or {}) if terminal is not None else {}
            if str(meta.get("terminal_geometry_source", "")) != "detector_miss_plane":
                rows.append(("genuine-contact", 0.0, 0.0, 0.0, 0.0))
                continue
            dist = float(meta.get("detector_miss_distance_mm", float("nan")))
            radial = float(meta.get("detector_miss_radial_mm", float("nan")))
            half = float(meta.get("detector_miss_half_mm", float("nan")))
            pts = np.asarray(p.points_world, dtype=float)
            seg = float(np.linalg.norm(pts[-1, :3] - pts[-2, :3])) if pts.shape[0] >= 2 else float("nan")
            rows.append(("plane-projected", dist, radial, half, seg))
        print("census:", census)
        proj = [r for r in rows if r[0] == "plane-projected"]
        print(f"missed_image: {len(rows)} total, {len(proj)} plane-projected")
        if proj:
            dists = np.asarray([r[1] for r in proj])
            radials = np.asarray([r[2] for r in proj])
            halves = np.asarray([r[3] for r in proj])
            segs = np.asarray([r[4] for r in proj])
            ratio = radials / np.maximum(halves, 1e-9)
            print(f"  projection distance mm: min {dists.min():.1f}  median {np.median(dists):.1f}  max {dists.max():.1f}")
            print(f"  final drawn segment mm: min {segs.min():.1f}  median {np.median(segs):.1f}  max {segs.max():.1f}")
            print(f"  radial/half ratio:      min {ratio.min():.2f}  median {np.median(ratio):.2f}  max {ratio.max():.2f}")
            for lo, hi in ((0, 1), (1, 2), (2, 4), (4, 10), (10, 1e9)):
                n = int(np.sum((ratio >= lo) & (ratio < hi)))
                if n:
                    d_in = dists[(ratio >= lo) & (ratio < hi)]
                    print(f"  ratio [{lo:>2},{hi if hi < 1e9 else 'inf'!s:>3}): {n:4d} rays, distance {d_in.min():.0f}..{d_in.max():.0f} mm")
        # Scene scale for a distance bound.
        try:
            det_gap = float(app.rows[-2].thickness)
            print(f"  image-leg gap (prism->sensor): {det_gap:.1f} mm")
        except Exception:
            pass
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
