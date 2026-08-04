"""bugs/0531 follow-up -- is the traced ghost physically right for a PLATE BS?
Dump the ghost family's geometry: hit separation (plate thickness vs cube leg), exit
direction vs the main reflected beam, and the promoted solid's face flags."""
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
        _s, _r, bundle = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=False, trace_rays=True
        )
        paths = list(bundle.ray_paths)
        ghosts = [p for p in paths if "transmit -> " in str(getattr(p, "branch_path", ""))
                  and str(p.termination_reason) == "no_next_intersection"]
        mains = [p for p in paths if str(getattr(p, "branch_path", "")) == "S3:S3/reflect"
                 and str(p.termination_reason) == "target_termination"]
        print(f"ghost family: {len(ghosts)}   imaging family: {len(mains)}")

        def seg_dirs(p):
            pts = np.asarray(p.points_world, float)[:, :3]
            dirs = np.diff(pts, axis=0)
            dirs = dirs / np.maximum(np.linalg.norm(dirs, axis=1, keepdims=True), 1e-12)
            return pts, dirs

        main_pts, main_dirs = seg_dirs(mains[len(mains) // 2])
        print(f"main ray pts[:4]:\n{np.round(main_pts[:4], 2)}")
        print(f"main reflected dir (after S3): {np.round(main_dirs[1], 4)}")

        for tag, p in (("ghost mid", ghosts[len(ghosts) // 2]), ("ghost first", ghosts[0])):
            pts, dirs = seg_dirs(p)
            hit_sep = float(np.linalg.norm(pts[2] - pts[1]))
            print(f"\n[{tag}] n_pts={pts.shape[0]}  branch={getattr(p, 'branch_path', None)}"
                  f"  power={getattr(p, 'branch_power', None):.4f}")
            print(f"  points:\n{np.round(pts, 2)}")
            print(f"  launch dir      : {np.round(dirs[0], 4)}")
            print(f"  in-glass dir    : {np.round(dirs[1], 4)}  (front-hit -> second-hit, sep {hit_sep:.2f} mm)")
            print(f"  after-reflect dir: {np.round(dirs[2], 4)}")
            ang = np.degrees(np.arccos(np.clip(np.dot(dirs[2], main_dirs[1]), -1, 1)))
            print(f"  angle ghost-exit vs main-reflected: {ang:.1f} deg")

        # Face flags of the promoted BS solid.
        try:
            row_idx = app._promoted_optical_solid_row_index("optical")
        except Exception:
            row_idx = None
        print(f"\npromoted optical row: {row_idx}")
        for attr in ("_step_face_role_overrides", "_promoted_face_flags", "_step_face_flags"):
            val = getattr(app, attr, None)
            if val:
                print(f"  {attr}: {str(val)[:400]}")
        try:
            spec = app._serializable_row_specs()[row_idx]
            interesting = {k: v for k, v in spec.items() if any(
                t in str(k).lower() for t in ("face", "coat", "split", "reflect", "glass", "solid", "flag"))}
            print(f"  row spec keys: {sorted(spec.keys())}")
            print(f"  interesting: {str(interesting)[:800]}")
        except Exception as exc:
            print(f"  row spec unavailable: {exc!r}")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
