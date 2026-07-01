"""Guard: a single promoted-mirror fold draws an OUTGOING (reflected) optical-axis guide.

Flag 20260701_201444 ("the reflected path missing optical axis line"): the incoming +Z
dotted guide is clamped at the mirror (bugs/0189), and the +X branch relied on traced ray
segments -- which are absent when no chief ray is traced, leaving the reflected path with no
axis line. `_folded_reflected_axis_guide_record` adds a dotted guide from the fold point
along the folded axis. A CHAIN of folds / unfolded layout returns None (unchanged).

Display-free: drives the real method against a stub inspector holding a headless editor.
Run: ``.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_reflected_axis_guide``
"""
from __future__ import annotations

import types

import numpy as np

from KrakenOS.UI.layout_editor import LAYOUTS_DIR, KrakenLayoutEditor, _load_python_data
from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor

# Scene bounds like ComputeVisiblePropBounds for the folded AZ85 (from the flag state).
_BOUNDS = np.asarray([-248.4, 361.7, -60.8, 34.9, -236.8, 571.8], dtype=float)
_FOLD_Z = 71.897  # the RA-mirror station


def _editor(layout: str):
    info = _load_python_data(LAYOUTS_DIR / layout)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    rows = [KrakenLayoutEditor._row_from_layout_item(i) for i in info["surfaces"]]
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    ed = _snapshot_editor(rows, settings)
    ed.tk = object()
    ed.current_layout_file = LAYOUTS_DIR / layout
    for a in ("imported_lens_step_path", "imported_optical_step_path",
              "imported_led_step_path", "imported_camera_step_path"):
        if not hasattr(ed, a):
            setattr(ed, a, None)
    ed._normalize_special_rows()
    return ed


def _record(ed, bounds, fold_z):
    stub = types.SimpleNamespace(editor=ed)
    stub._folded_reflected_axis_guide_record = types.MethodType(
        Kraken3DInspector._folded_reflected_axis_guide_record, stub
    )
    return stub._folded_reflected_axis_guide_record(bounds, fold_z)


def main() -> int:
    failures: list[str] = []

    rec = _record(_editor("machine_vision_AZ85_RA_Mirror.py"), _BOUNDS, _FOLD_Z)
    if rec is None:
        failures.append("AZ85 single fold: no reflected axis guide was produced")
    else:
        pts = np.asarray(rec["points"], dtype=float)
        start, far = pts[0], pts[1]
        direction = far - start
        direction = direction / (np.linalg.norm(direction) + 1e-30)
        if np.linalg.norm(start - np.asarray([0.0, 0.0, _FOLD_Z])) > 1.0:
            failures.append(f"reflected guide does not start at the fold point: {start.tolist()}")
        if direction[0] < 0.99:
            failures.append(f"reflected guide is not along +X (folded axis): dir={direction.round(3).tolist()}")
        if far[0] < 250.0:
            failures.append(f"reflected guide does not reach the +X branch (far X={far[0]:.1f} < 250)")
        if rec.get("axis_kind") != "dotted_global_guide":
            failures.append("reflected guide is not a dotted_global_guide")

    # Unfolded / non-promoted-mirror layout: no reflected guide (unchanged).
    none_rec = _record(_editor("flat_mirror_45_deg.py"), _BOUNDS, _FOLD_Z)
    if none_rec is not None:
        failures.append("non-promoted-mirror layout wrongly produced a reflected axis guide")

    # No fold point -> None.
    if _record(_editor("machine_vision_AZ85_RA_Mirror.py"), _BOUNDS, None) is not None:
        failures.append("missing fold point still produced a reflected guide")

    if failures:
        print("FAIL bugs/0200 reflected axis guide:")
        for f in failures:
            print("  -", f)
        return 1
    pts = np.asarray(rec["points"], dtype=float)
    print("PASS bugs/0200 reflected optical-axis guide:")
    print(f"  - AZ85 single fold: dotted guide from fold point {pts[0].round(2).tolist()} "
          f"along +X to {pts[1].round(1).tolist()}")
    print("  - non-promoted-mirror layout + missing fold point: no guide (unchanged)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
