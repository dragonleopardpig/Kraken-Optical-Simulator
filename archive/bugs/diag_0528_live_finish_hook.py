"""bugs/0528 diagnostic B -- replicate the LIVE flow: real inspector attached, per-frame
carry drags totalling the user's +50.54 mm, then the interactive finish hook. Instruments
the snap's measurement chain to see which exit it takes."""
from __future__ import annotations

from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector
    from KrakenOS.UI.services import optical_axis_tree as tree_mod

    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        insp = _open_3d_inspector(app)
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)

        # Instrument the measurement chain.
        calls = []
        real_rr = app._real_ray_best_focus_shift_for_rows
        real_tb = app._traced_bundle_best_focus_shift
        real_split = app._folded_image_conjugate_split
        real_first = app._shared_first_order_reference

        def probe(name, fn):
            def wrapped(*a, **k):
                try:
                    out = fn(*a, **k)
                except Exception as exc:
                    calls.append((name, f"RAISED {exc!r}"))
                    raise
                calls.append((name, out if not isinstance(out, dict) else {kk: out.get(kk) for kk in ("frozen_world", "near", "far", "f", "object_principal", "image_principal") if kk in out}))
                return out
            return wrapped

        app._real_ray_best_focus_shift_for_rows = probe("real_ray", real_rr)
        app._traced_bundle_best_focus_shift = probe("traced_bundle", real_tb)
        app._folded_image_conjugate_split = probe("split", real_split)
        app._shared_first_order_reference = probe("first_order", real_first)

        def sensor_pose():
            return np.round(np.asarray(tree_mod.row_world_pose(app.rows, len(app.rows) - 1), float).reshape(-1)[:3], 3).tolist()

        print(f"sampling mode = {app._preview_3d_sampling_mode()!r}")
        print(f"[fresh] gaps={[round(float(r.thickness), 2) for r in app.rows]} sensor={sensor_pose()}")

        # Per-frame drag like the live carry: 50 frames of ~1.0108 mm along +x.
        frames = 50
        step = 50.542 / frames
        for _ in range(frames):
            app.translate_step_overlay("lens", (step, 0.0, 0.0))
        print(f"[dragged] gaps={[round(float(r.thickness), 2) for r in app.rows]} sensor={sensor_pose()}")
        print(f"  lens offset = {np.round(np.asarray(app._step_placement_offset_xyz('lens'), float), 3).tolist()}")

        calls.clear()
        insp._finish_step_carry_drag({"label": "lens", "applied_steps": 1})
        print("\nmeasurement chain during finish hook:")
        for name, out in calls:
            print(f"  {name}: {out}")
        print(f"\n[after hook] gaps={[round(float(r.thickness), 2) for r in app.rows]} sensor={sensor_pose()}")
        print(f"  status = {insp.status_var.get()!r}")
        print(f"  editor status = {app.status_var.get()!r}")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
