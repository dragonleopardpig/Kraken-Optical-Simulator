"""bugs/0627 verification -- a swapped-in bare surrogate draws at its DRAWN size.

flag_20260818_140218: "loaded Apo75, swap lens to pyrite85, lens surrogate grow big."
bugs/0624 builds surrogate-member surfaces at 2x their drawn diameter (trace-only
extension); the display meshes came from the same built geometry, so a bare surrogate
drew doubled discs (hidden on the Apo75 only by its STEP barrel overlay).

Verifies on the real scene:
  1. load Apo75, swap to PYRITE 4.5/85 (programmatic folder -> non-interactive);
  2. every blackbox-member surface/side mesh in the live bundle fits its row's drawn
     diameter (longest bbox side <= diameter x 1.15 -- a disc's longest side is its
     diameter under any orientation; pre-fix it measured ~2x);
  3. the trace is untouched (arrivals present, matching the flag-time census scale);
  4. saves a screenshot for the eyeball.

Run:  taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python -u bugs/diag_0627_swap_surrogate_display_size.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_Apo75.py")
PYRITE = Path("attachment/Lens/PYRITE_45_85_05x-20x_V38_1072517")
OUT = Path("bugs/_0627_pyrite_swap_display_size.png")


def main() -> int:
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import (
        _open_3d_inspector,
        _save_vtk_snapshot,
        _settle,
    )
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    try:
        app.layout_files["scene"] = SCENE
        app.load_layout_by_name("scene")
        print(f"loaded {SCENE.name}")
        result = app.swap_imaging_lens_from_folder(str(PYRITE))
        print(f"swap result: {result}")

        members = app._surrogate_blackbox_member_rows()
        print(f"blackbox member rows: {sorted(members)}")
        if not members:
            print("FAIL: no blackbox members after the swap -- scan broken?")
            return 1

        insp = _open_3d_inspector(app)
        app._three_d_inspector = insp
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)
        _settle(insp)
        bundle = insp.__dict__.get("_current_scene_bundle")
        meshes = list(getattr(bundle, "surface_meshes", []) or [])
        paths = list(getattr(bundle, "ray_paths", None) or [])
        census: dict[str, int] = {}
        for path in paths:
            reason = str(getattr(path, "termination_reason", "") or "(none)")
            census[reason] = census.get(reason, 0) + 1
        print(f"bundle: {len(meshes)} surface meshes, {len(paths)} paths, census {census}")

        oversized = []
        checked = 0
        for item in meshes:
            row_index = int(getattr(item, "row_index", -1))
            if row_index not in members:
                continue
            row = getattr(item, "row", None)
            diameter = float(getattr(row, "diameter", 0.0) or 0.0)
            mesh = getattr(item, "mesh", None)
            if mesh is None or diameter <= 0.0:
                continue
            bounds = np.asarray(mesh.bounds, dtype=float).reshape(3, 2)
            longest = float(np.max(bounds[:, 1] - bounds[:, 0]))
            checked += 1
            marker = ""
            if longest > diameter * 1.15:
                oversized.append((row_index, longest, diameter))
                marker = "   <-- OVERSIZED"
            print(f"  S{row_index} kind={getattr(item, 'kind', '?'):<18} drawn diam {diameter:7.2f}  "
                  f"mesh longest side {longest:7.2f}{marker}")

        _save_vtk_snapshot(insp, OUT)
        print(f"saved {OUT}")

        print("\n--- verdict ---")
        ok = True
        if checked == 0:
            print("FAIL: no member meshes found to check")
            ok = False
        if oversized:
            print(f"FAIL: {len(oversized)} member mesh(es) exceed the drawn diameter: {oversized}")
            ok = False
        if census.get("target_termination", 0) <= 0:
            print("FAIL: no rays arrive after the swap -- the clip must not touch the trace")
            ok = False
        if ok:
            print(f"PASS: {checked} member meshes all within drawn size; "
                  f"{census.get('target_termination', 0)} arrivals")
        return 0 if ok else 1
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
