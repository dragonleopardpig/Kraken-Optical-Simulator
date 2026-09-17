"""0696: which builder reproduces the chain's AIMED launch outside the sampler?

The mirrored faceB launch must reflect the chain's real launch (aimed, 2.9 deg).
Probe, after one full build: the active sampling mode + resolved pupil radius,
the TRACED chain launch signature, and what each candidate builder returns when
called directly in the additive context (the earlier world-builder attempt made
faceB vanish -- see WHY).
"""
from pathlib import Path

import numpy as np


def describe(bundles, label):
    try:
        bundles = list(bundles or [])
        if not bundles:
            print(f"{label}: EMPTY")
            return
        total = sum(int(len(np.asarray(b[0]))) for b in bundles)
        D = np.concatenate([
            np.stack([np.asarray(b[3], float), np.asarray(b[4], float),
                      np.asarray(b[5], float)], axis=1) for b in bundles
        ])
        P = np.concatenate([
            np.stack([np.asarray(b[0], float), np.asarray(b[1], float),
                      np.asarray(b[2], float)], axis=1) for b in bundles
        ])
        mean = D.mean(axis=0)
        mean /= max(np.linalg.norm(mean), 1e-12)
        ang = np.degrees(np.arccos(np.clip(D @ mean, -1, 1)))
        print(f"{label}: {len(bundles)} bundles, {total} rays, launch z "
              f"{P[:, 2].min():.2f}..{P[:, 2].max():.2f}, y {P[:, 1].min():.2f}.."
              f"{P[:, 1].max():.2f}, mean dir {np.round(mean, 3)}, "
              f"half-angle {ang.mean():.3f}/{ang.max():.3f} deg")
    except Exception as exc:
        print(f"{label}: describe FAILED {type(exc).__name__}: {exc}")


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = Path("attachment/om05a_folded.py").resolve()
    editor.load_layout_by_name("p")
    editor._preview_trace_deferred_until_requested = False
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)

    print("active mode:", getattr(editor, "_active_preview_sampling_mode", None))
    print("3d sampling mode:", editor._preview_3d_sampling_mode())
    radius = getattr(editor, "_last_resolved_preview_pupil_radius", None)
    print("resolved pupil radius:", radius)

    # traced chain launch signature (first segments of the CENTRAL field)
    dirs, launches = [], []
    for rp in (getattr(bundle, "ray_paths", None) or []):
        if str(getattr(rp, "source_id", "") or "") == "source:faceB":
            continue
        p = np.asarray(getattr(rp, "points_world", rp), dtype=float)
        if p.ndim != 2 or p.shape[0] < 2 or not np.all(np.isfinite(p[:2])):
            continue
        if abs(float(p[0][0])) > 0.8:
            continue
        d = p[1] - p[0]
        n = float(np.linalg.norm(d))
        if n > 1e-9:
            dirs.append(d / n)
            launches.append(p[0])
    D = np.array(dirs)
    mean = D.mean(axis=0)
    mean /= max(np.linalg.norm(mean), 1e-12)
    ang = np.degrees(np.arccos(np.clip(D @ mean, -1, 1)))
    print(f"TRACED chain central: {len(D)} rays, mean {np.round(mean, 3)}, "
          f"half-angle {ang.mean():.3f}/{ang.max():.3f}")

    stash = getattr(editor, "_last_imaging_launch_bundles", None)
    describe(stash, "stash post-build")

    for name in ("_build_world_envelope_bundles", "_build_world_cone_bundles",
                 "_build_world_sparse_pupil_bundles"):
        fn = getattr(editor, name, None)
        if fn is None:
            print(f"{name}: MISSING")
            continue
        try:
            r = float(radius) if radius is not None else float("nan")
            out = fn(r, system=system)
            describe(out, name)
        except Exception as exc:
            print(f"{name}: RAISED {type(exc).__name__}: {exc}")
    editor.destroy()


if __name__ == "__main__":
    main()
