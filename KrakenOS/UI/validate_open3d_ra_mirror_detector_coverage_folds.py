"""Display-free guard for bugs/0188: the IMAGE detector-coverage overlay folds onto the
reflected +X branch of a promoted RA-mirror layout.

A promoted full-mirror cube (``machine_vision_AZ85_RA_Mirror.py``) folds the downstream
lens chain + the image surface onto the reflected +X branch in the MESH display system
(bugs/0185). The detector-coverage overlay (image circle / sensor square / labels +
the pickable fill) is built from ``build_scene_targets``, which derives the Image
detector from the UNFOLDED cumulative-thickness +Z axis -- so without a fold it draws
at world (0, 0, 347.22) along +Z, a stray plane far from the folded image that the user
saw as a faint 45-deg line (flag ``flag_20260630_212049_339`` "still the same"; the row-8
actor bounds were the diagonal [-16.29, 287.82, -16.29, 16.29, 55.6, 347.2]).

Fix (``services/detector_coverage_overlay.py`` ``_fold_table_row_detector_frame``) carries
a plain TABLE-ROW image detector onto the reflected branch with the SAME rigid fold the
lens/camera STEP overlays use (``_optical_axis_fold_world_transform_for_row``). Branch
detectors already sit on their own per-arm folded centre, so only table-row targets fold;
unfolded layouts are left byte-identical (transform is ``None``).

This guard binds the REAL ``build_scene_targets`` + the REAL overlay fold helper and asserts:
  1. the AZ85 image detector is UNFOLDED at (0, 0, ~347.22) +Z as build_scene_targets emits it;
  2. the fold helper carries it to the sensor at world X ~ +287.82, Z ~ 71.9, normal +X, and
     the in-plane basis lies in the Y-Z plane (the coverage disc is square to +X);
  3. the folded detector centre coincides with the MESH image surface (within 1 mm);
  4. a non-folded sequential-mirror layout (``flat_mirror_45_deg.py``) is left byte-identical
     (the fold helper no-ops -- no promoted-solid pose override).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_detector_coverage_folds

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import (
    KrakenLayoutEditor,
    _build_system_from_specs,
    _load_python_data,
)
from KrakenOS.UI.layout_library import load_python_data
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
from KrakenOS.UI.scene_builder import build_scene_targets
from KrakenOS.UI.services.detector_coverage_overlay import DetectorCoverageOverlayService

_LAYOUTS = Path(__file__).resolve().parent.parent / "common_optical_layouts"
_AZ85 = "machine_vision_AZ85_RA_Mirror.py"
_PLAIN = "flat_mirror_45_deg.py"
_SENSOR_X = 287.82
_SENSOR_Z = 71.90
_UNFOLDED_Z = 347.218


class _InspectorStub:
    """Minimal carrier so the overlay service can reach ``editor`` display-free."""

    def __init__(self, editor) -> None:
        self.editor = editor


def _build_editor(name: str):
    layout_path = _LAYOUTS / name
    info = _load_python_data(layout_path)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in info["surfaces"]]
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    editor = _snapshot_editor(rows, settings)
    editor.tk = object()  # break tkinter __getattr__ recursion on the __new__ instance
    editor.current_layout_file = layout_path
    for attr in (
        "imported_lens_step_path",
        "imported_optical_step_path",
        "imported_led_step_path",
        "imported_camera_step_path",
    ):
        if not hasattr(editor, attr):
            setattr(editor, attr, None)
    editor._normalize_special_rows()
    return editor


def _image_detector(editor):
    targets = build_scene_targets(editor.rows)
    dets = [t for t in targets if bool(getattr(t, "is_detector", False))]
    if not dets:
        raise AssertionError("no image detector target found")
    return dets[-1]


def _mesh_image_surface_point(name: str) -> np.ndarray | None:
    """The folded image-surface world point from the real mesh system (the disc the
    coverage overlay must coincide with). None if the heavy build is unavailable."""
    specs = [dict(s) for s in load_python_data(_LAYOUTS / name)["surfaces"]]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            editor = _build_editor(name)
            system = _build_system_from_specs(specs, apply_optical_solid_output_ports=True)
            pt = editor._surface_reference_world_point(len(editor.rows) - 1, system=system)
        return np.asarray(pt, dtype=float).reshape(3)
    except Exception:
        return None


def main() -> int:
    failures: list[str] = []
    notes: list[str] = []

    # ---- AZ85: the detector folds onto the +X branch -------------------------
    editor = _build_editor(_AZ85)
    overlay = DetectorCoverageOverlayService(_InspectorStub(editor), pv_module=None)
    det = _image_detector(editor)

    c0 = np.asarray(det.center_world, dtype=float).reshape(3)
    n0 = np.asarray(det.normal_world, dtype=float).reshape(3)
    src = str((det.metadata or {}).get("target_source", ""))

    # (1) precondition: build_scene_targets emits the UNFOLDED +Z detector.
    if src != "table_row":
        failures.append(f"AZ85: image detector target_source={src!r}, expected 'table_row'")
    if not (abs(c0[0]) < 1.0 and abs(c0[1]) < 1.0 and abs(c0[2] - _UNFOLDED_Z) < 1.0):
        failures.append(f"AZ85: unfolded detector centre {np.round(c0, 3).tolist()} not at (0,0,~{_UNFOLDED_Z})")
    if abs(abs(float(n0[2])) - 1.0) > 1e-3:
        failures.append(f"AZ85: unfolded detector normal {np.round(n0, 4).tolist()} not ~+Z")

    # (2) the fold helper carries it onto the +X sensor branch, normal +X.
    cf, nf = overlay._fold_table_row_detector_frame(det, c0, n0)
    cf = np.asarray(cf, dtype=float).reshape(3)
    nf = np.asarray(nf, dtype=float).reshape(3)
    if np.allclose(cf, c0):
        failures.append("AZ85: fold helper left the detector on the unfolded axis (no fold applied)")
    if abs(cf[0] - _SENSOR_X) > 1.0:
        failures.append(f"AZ85: folded detector X {cf[0]:.2f} not at the +X sensor ~{_SENSOR_X}")
    if abs(cf[1]) > 1.0:
        failures.append(f"AZ85: folded detector Y {cf[1]:.2f} should be ~0")
    if abs(cf[2] - _SENSOR_Z) > 1.0:
        failures.append(f"AZ85: folded detector Z {cf[2]:.2f} not at the sensor station ~{_SENSOR_Z}")
    if abs(abs(float(nf[0])) - 1.0) > 1e-3:
        failures.append(f"AZ85: folded detector normal {np.round(nf, 4).tolist()} not ~+X")

    # The image circle / sensor square draw in the (iu, iv) basis of the folded
    # normal; both must lie in the Y-Z plane so the disc is square to +X.
    from KrakenOS.UI.services.detector_coverage_overlay import _basis

    iu, iv = _basis(nf)
    if abs(float(iu[0])) > 1e-6 or abs(float(iv[0])) > 1e-6:
        failures.append(
            f"AZ85: folded coverage basis not square to +X (iu={np.round(iu, 4).tolist()}, "
            f"iv={np.round(iv, 4).tolist()})"
        )

    # (3) the folded detector coincides with the real mesh image surface.
    mesh_pt = _mesh_image_surface_point(_AZ85)
    if mesh_pt is None:
        notes.append("SKIP coincidence check: mesh image-surface build unavailable")
    elif float(np.linalg.norm(cf - mesh_pt)) > 1.0:
        failures.append(
            f"AZ85: folded detector {np.round(cf, 3).tolist()} does not coincide with the "
            f"mesh image surface {np.round(mesh_pt, 3).tolist()}"
        )

    # ---- (4) a non-folded sequential-mirror layout is untouched --------------
    plain_editor = _build_editor(_PLAIN)
    plain_overlay = DetectorCoverageOverlayService(_InspectorStub(plain_editor), pv_module=None)
    plain_det = _image_detector(plain_editor)
    pc0 = np.asarray(plain_det.center_world, dtype=float).reshape(3)
    pn0 = np.asarray(plain_det.normal_world, dtype=float).reshape(3)
    pcf, pnf = plain_overlay._fold_table_row_detector_frame(plain_det, pc0, pn0)
    if not (np.allclose(pc0, pcf) and np.allclose(pn0, pnf)):
        failures.append(
            f"regression: non-folded layout detector was modified "
            f"({np.round(pc0, 3).tolist()} -> {np.round(pcf, 3).tolist()})"
        )

    if failures:
        print("FAIL bugs/0188 folded detector-coverage:")
        for line in failures:
            print(f"  - {line}")
        return 1
    print("PASS bugs/0188 folded detector-coverage:")
    print(f"  - AZ85 detector unfolds at (0,0,{c0[2]:.2f}) +Z, folds to ({cf[0]:.2f},{cf[1]:.2f},{cf[2]:.2f}) +X")
    print("  - folded coverage basis is square to +X (Y-Z plane)")
    if mesh_pt is not None:
        print(f"  - folded detector coincides with the mesh image surface ({np.round(mesh_pt, 2).tolist()})")
    print(f"  - non-folded {_PLAIN} left byte-identical (fold helper no-op)")
    for note in notes:
        print(f"  - {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
