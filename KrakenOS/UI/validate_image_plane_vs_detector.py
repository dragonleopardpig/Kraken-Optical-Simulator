"""Display-free validator for item 2: the image plane (best focus) is separate from the detector.

  * ``_paraxial_image_plane_z`` is the optics' best focus (robust Gaussian conjugate, NOT the
    ray-RMS focus diagnostic which lands on the exit pupil for multi-field bundles),
  * for a solved prescription it coincides with the detector (Image row) -- in focus,
  * moving the detector (last gap) leaves the image plane put -- that gap is the simulated defocus,
  * ``snap_detector_to_image_plane`` moves the detector back onto best focus.

Run: ``.devenv/state/venv/bin/python -m KrakenOS.UI.validate_image_plane_vs_detector``
"""
from __future__ import annotations

import importlib

from KrakenOS.UI.layout_editor import SurfaceRow
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor

_LAYOUTS = (
    "machine_vision_150mm_datasheet_1x",
    "machine_vision_150mm_datasheet_0_5x",
    "machine_vision_120mm_pyrite_datasheet_1x",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        print(f"[FAIL] {message}")
        raise SystemExit(1)


def _editor(module_name: str):
    module = importlib.import_module(f"KrakenOS.common_optical_layouts.{module_name}")
    rows = [SurfaceRow(**{k: v for k, v in s.items() if k in SurfaceRow.__dataclass_fields__}) for s in module.SURFACES]
    return _snapshot_editor(rows, module.SETTINGS)


def _detector_z(editor) -> float:
    return sum(float(r.thickness) for r in editor.rows[:-1])


def main() -> int:
    for name in _LAYOUTS:
        editor = _editor(name)
        image_z = editor._paraxial_image_plane_z()
        _require(image_z is not None, f"{name}: image plane computable")
        detector_z = _detector_z(editor)
        _require(abs(float(image_z) - detector_z) < 1.0, f"{name}: image plane on detector when in focus (gap {image_z - detector_z:.2f})")
    print("[ok] image plane = paraxial best focus, coincides with the detector for a solved prescription")

    # Defocus: move the detector (last gap); the image plane stays put -> that gap IS the defocus.
    editor = _editor(_LAYOUTS[0])
    image_before = float(editor._paraxial_image_plane_z())
    editor.rows[-2].thickness = float(editor.rows[-2].thickness) + 40.0
    image_after = float(editor._paraxial_image_plane_z())
    detector_after = _detector_z(editor)
    _require(abs(image_after - image_before) < 0.5, f"image plane is OPTICS-driven, unmoved by the detector ({image_before:.2f}->{image_after:.2f})")
    _require(abs(detector_after - image_after - 40.0) < 0.5, f"detector moved +40 -> defocus gap = +40 (got {detector_after - image_after:.2f})")
    print("[ok] moving the detector leaves the image plane put -> the gap is the simulated defocus")

    # Snap: brings the detector back onto best focus.
    moved = editor.snap_detector_to_image_plane()
    _require(moved is True, "snap reports it moved the detector")
    gap = _detector_z(editor) - float(editor._paraxial_image_plane_z())
    _require(abs(gap) < 0.05, f"snap put the detector on the image plane (residual gap {gap:.4f})")
    print("[ok] snap_detector_to_image_plane removes the defocus (detector back on best focus)")

    print("[PASS] image plane vs detector: separate, optics-driven image plane + snap")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
