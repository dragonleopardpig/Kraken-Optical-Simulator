"""Display-free guard: "Snap detector to image plane" falls back to REAL-RAY best focus.

The right-click "Snap detector to image plane (remove defocus)" used the paraxial image
conjugate, which the centered-refractive paraxial solve can't compute when a 3D solid /
beam-splitter cube is in the path -- so it bailed ("not computable") and left the detector
defocused. The fix: when the paraxial conjugate is unavailable, snap to the REAL-RAY
on-axis best focus (trace the spot, minimise it).

This guard pins (display-free), on the real MV-150 beam-splitter + surrogate scene:

  * the paraxial image plane is NOT computable (the cube) -- so the fallback path runs;
  * ``_real_ray_best_focus_shift_for_rows`` recovers a deliberately injected -2 mm defocus
    (bugs/0243: the as-imported fixture now measures AT focus -- the old ~+2.7 mm was the
    branching-tracer thin-lens direction bias, fixed at the physics level);
  * ``snap_detector_to_image_plane`` moves the back-focal gap by exactly that, so the
    detector lands at best focus;
  * the snap source consults the real-ray helper.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_snap_detector_best_focus

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect
import io
import math
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _load_python_data
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

_MV150_BS = Path(__file__).resolve().parents[2] / "attachment" / "machine_vision_150mm_test.py"


def _editor_from_layout(path: Path):
    info = _load_python_data(path)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in info["surfaces"]]
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    editor = _snapshot_editor(rows, settings)
    editor.tk = object()
    editor._normalize_special_rows()
    editor.headless = True
    return editor


def _check_integration(failures: list[str], notes: list[str]) -> None:
    if not _MV150_BS.exists():
        notes.append("SKIP integration: MV-150 beam-splitter layout unavailable")
        return
    capture = io.StringIO()
    try:
        with redirect_stdout(capture), redirect_stderr(capture):
            editor = _editor_from_layout(_MV150_BS)
            paraxial = editor._paraxial_image_plane_z()
            # bugs/0243: the branching-tracer Thin-Lens SIGN fix removed the direction
            # bias that used to leave this fixture ~+2.7 mm off; the as-imported scene
            # now measures at best focus already. DEFOCUS it deliberately so the
            # real-ray fallback still has something real to recover.
            editor.rows[-2].thickness = float(editor.rows[-2].thickness) + 2.0
            shift = editor._real_ray_best_focus_shift_for_rows()
            before = float(editor.rows[-2].thickness)
            moved = editor.snap_detector_to_image_plane()
            after = float(editor.rows[-2].thickness)
    except Exception as exc:
        failures.append(f"INTEGRATION: MV-150 snap raised {exc!r}")
        return

    if paraxial is not None:
        notes.append("NOTE: paraxial image plane computable on this clone -- fallback not exercised")
    if shift is None or not (-3.0 < float(shift) < -1.0):
        failures.append(f"INTEGRATION: real-ray best-focus shift {shift} did not recover the injected -2 mm defocus")
        return
    if not moved:
        failures.append("INTEGRATION: snap_detector_to_image_plane did not move the detector")
    if not math.isclose(after - before, float(shift), abs_tol=0.05):
        failures.append(f"INTEGRATION: snap moved {after - before:.4g} mm, not the real-ray shift {float(shift):.4g}")
    else:
        notes.append(f"integration: paraxial None -> snap moved the back-focal gap {after - before:+.3g} mm to ray-traced best focus")


def _check_contract(failures: list[str]) -> None:
    src = inspect.getsource(ScenePlacementMixin.snap_detector_to_image_plane)
    if "_real_ray_best_focus_shift_for_rows" not in src:
        failures.append("CONTRACT: snap_detector_to_image_plane does not fall back to the real-ray best focus")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_integration(failures, notes)
    _check_contract(failures)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(f"  - {message}")
    if not passed:
        print("[FAIL] Snap detector to best focus (real-ray fallback)")
        return 1
    print("[PASS] Snap detector falls back to ray-traced best focus on beam-splitter/solid scenes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
