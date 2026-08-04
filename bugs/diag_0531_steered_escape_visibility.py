"""bugs/0531 diagnostic -- flag_20260804_082939 "clipped overlays is off, still have
spurious reflected beam." Inspect the AZ85 bundle: which paths does the 0018-reopen rule
keep visible with Show Clipped Rays OFF, what branch identity do they carry, and do their
branch families reach a detector?"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.scene_geometry import ray_path_visible_without_clipping_from_events

    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        _s, _r, bundle = app._build_preview_system_rays_bundle(
            sampling_mode=None, update_state=False, trace_rays=True
        )
        paths = list(bundle.ray_paths)
        print(f"paths: {len(paths)}")
        sample = paths[0]
        print("path attrs:", sorted(a for a in dir(sample) if not a.startswith("__"))[:40])

        kept = [p for p in paths if ray_path_visible_without_clipping_from_events(p)]
        print(f"visible with overlay OFF (current rule): {len(kept)}")
        by_reason = Counter(str(p.termination_reason) for p in kept)
        print("  kept by reason:", dict(by_reason))

        def describe(p):
            return {
                "reason": str(getattr(p, "termination_reason", "")),
                "branch_path": getattr(p, "branch_path", None),
                "ray_index": getattr(p, "ray_index", None),
                "branch_power": getattr(p, "branch_power", None),
                "n_pts": np.asarray(p.points_world).shape[0],
                "events": [
                    (str(getattr(e, "event_type", "")), str(getattr(e, "surface_id", "")))
                    for e in (p.events or [])
                ][:8],
            }

        strays = [p for p in kept if str(p.termination_reason) != "target_termination"]
        print(f"\nkept NON-target (the spurious beam): {len(strays)}")
        for p in strays[:4]:
            print(" ", describe(p))
        reaching = [p for p in paths if str(p.termination_reason) == "target_termination"]
        print("\nreaching sample:")
        for p in reaching[:2]:
            print(" ", describe(p))
        bp = Counter(str(getattr(p, "branch_path", None)) for p in strays)
        print("\nstray branch_path histogram:", dict(list(bp.items())[:6]))
        bp2 = Counter(str(getattr(p, "branch_path", None)) for p in reaching)
        print("reaching branch_path histogram:", dict(list(bp2.items())[:6]))
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
