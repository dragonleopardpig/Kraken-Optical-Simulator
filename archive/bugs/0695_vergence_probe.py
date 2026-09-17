"""0695: per-arm cone vergence along the lens leg. Equal paths but B focuses
19 mm late -- compare each central cone's radius entering the lens (x -215),
leaving it (x -245), and the final-segment convergence point."""
from pathlib import Path

import numpy as np


def cone_at(P, D, x_plane):
    t = (x_plane - P[:, 0]) / D[:, 0]
    pts = P + t[:, None] * D
    c = pts.mean(axis=0)
    r = np.sqrt((pts[:, 1] - c[1]) ** 2 + (pts[:, 2] - c[2]) ** 2)
    return float(r.mean()), c


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path("attachment/om05a_folded.py").resolve()
    editor.load_layout_by_name("p")
    editor._preview_trace_deferred_until_requested = False
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)

    for want_arm in ("A", "B"):
        pre_seg, post_seg = [], []
        for rp in (getattr(bundle, "ray_paths", None) or []):
            sid = str(getattr(rp, "source_id", "") or "")
            arm = "B" if sid == "source:faceB" else "A"
            if arm != want_arm:
                continue
            p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
            if p.ndim != 2 or p.shape[0] < 2 or not np.all(np.isfinite(p)):
                continue
            if abs(float(p[0][0])) > 0.8 or float(p[-1][0]) > -250.0:
                continue
            for a, b in zip(p[:-1], p[1:]):
                if a[0] > -215.0 >= b[0]:
                    pre_seg.append((a, b - a))
                if a[0] > -245.0 >= b[0]:
                    post_seg.append((a, b - a))
        # launch cone: angular spread of first segments
        first_dirs = []
        for rp in (getattr(bundle, "ray_paths", None) or []):
            sid = str(getattr(rp, "source_id", "") or "")
            arm2 = "B" if sid == "source:faceB" else "A"
            if arm2 != want_arm:
                continue
            p2 = np.asarray(getattr(rp, "points_world", rp), dtype=float)
            if p2.ndim != 2 or p2.shape[0] < 2 or not np.all(np.isfinite(p2[:2])):
                continue
            if abs(float(p2[0][0])) > 0.8:
                continue
            d = p2[1] - p2[0]
            n = float(np.linalg.norm(d))
            if n > 1e-9:
                first_dirs.append(d / n)
        if first_dirs:
            Dirs = np.array(first_dirs)
            mean_dir = Dirs.mean(axis=0)
            mean_dir /= np.linalg.norm(mean_dir)
            ang = np.degrees(np.arccos(np.clip(Dirs @ mean_dir, -1, 1)))
            print(f"arm {want_arm} LAUNCH: n={len(Dirs)} mean dir {np.round(mean_dir, 3)} "
                  f"half-angle mean {ang.mean():.3f} max {ang.max():.3f} deg")
        for label, segs, plane in (("pre-lens  x-215", pre_seg, -215.0),
                                   ("post-lens x-245", post_seg, -245.0)):
            if len(segs) < 10:
                print(f"arm {want_arm} {label}: only {len(segs)} rays")
                continue
            P = np.array([s[0] for s in segs])
            D = np.array([s[1] for s in segs])
            r, c = cone_at(P, D, plane)
            print(f"arm {want_arm} {label}: n={len(segs)} radius {r:7.3f} centre "
                  f"y {c[1]:+7.2f} z {c[2]:+7.2f}")
        # convergence of the post-lens segments: scan x for min radius
        if len(post_seg) >= 10:
            P = np.array([s[0] for s in post_seg])
            D = np.array([s[1] for s in post_seg])
            best = (None, np.inf)
            for x in np.linspace(-330.0, -245.0, 341):
                r, _c = cone_at(P, D, x)
                if r < best[1]:
                    best = (x, r)
            print(f"arm {want_arm} post-lens segments converge near x {best[0]:.1f} "
                  f"(radius {best[1] * 1000:.1f}um)")
    editor.destroy()


if __name__ == "__main__":
    main()
