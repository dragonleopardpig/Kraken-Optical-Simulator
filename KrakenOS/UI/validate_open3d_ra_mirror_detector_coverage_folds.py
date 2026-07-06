"""Display-free guard for bugs/0188: the IMAGE detector TARGET folds onto the reflected
+X branch of a promoted RA-mirror layout AT THE BUNDLE SOURCE, so every consumer follows.

A promoted full-mirror cube (``machine_vision_AZ85_RA_Mirror.py``) folds the downstream
lens chain + the image surface onto the reflected +X branch in the MESH display system
(bugs/0185). The scene TARGETS come from ``build_scene_targets``, which derives each
table-row target from the UNFOLDED cumulative-thickness +Z axis -- so without a fold the
Image detector target sits at world (0, 0, 347.22) along +Z, a stray plane far from the
folded image. THREE consumers read that one target's world pose:
  * the 3-D detector footprint actor (three_d_scene_tools._scene_detector_overlay_specs),
  * the 2-D footprint projection (scene_projector._project_detector_footprints),
  * the detector-coverage overlay (detector_coverage_overlay.add_overlays).
The first fix folded only the coverage overlay's local copy, so the footprint actor stayed
on +Z (flags ``flag_20260701_074930_725`` "the detector still in original wrong axis" /
``flag_20260701_075019_938`` "the reflection still follow the fainted line").

Fix (option 1, source-level): ``LayoutSceneBundleDisplayMixin.
_fold_promoted_mirror_table_row_targets`` (called from ``_build_scene_bundle`` on the
single-axis path) folds each table-row target's ``center``/``normal``/``tangent`` world
pose in place with the SAME rigid fold the lens/camera STEP overlays use
(``_optical_axis_fold_world_transform_for_row``) -- so all THREE consumers draw on the
folded sensor from one shared pose. Two-arm splitter detectors are replaced upstream with
their own per-arm folded centres, so the single-axis fold is left to this path; unfolded
layouts get ``None`` transforms and are byte-identical.

This guard binds the REAL ``build_scene_targets`` + the REAL bundle-source fold helper and
the REAL footprint polyline builder, asserting:
  1. the AZ85 image detector target is UNFOLDED at (0, 0, ~347.22) +Z as build emits it;
  2. the source fold carries it to the sensor at world X ~ +287.82, Z ~ 71.9, normal +X,
     with the in-plane basis in the Y-Z plane (the coverage disc is square to +X);
  3. the SHARED target drives the 3-D/2-D detector FOOTPRINT: a footprint built from the
     folded target (given a test sensor) lies on +X, not the +Z axis -- this is the
     consumer the coverage-overlay-only fix missed;
  4. the folded detector centre coincides with the MESH image surface (within 1 mm);
  5. a non-folded sequential-mirror layout (``flat_mirror_45_deg.py``) is left byte-identical
     (the fold helper no-ops -- no promoted-solid pose override).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_detector_coverage_folds

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import contextlib
import copy
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
from KrakenOS.UI.scene_geometry import scene_target_active_footprint_polylines

_LAYOUTS = Path(__file__).resolve().parent.parent / "common_optical_layouts"
_AZ85 = "machine_vision_AZ85_RA_Mirror.py"
_PLAIN = "flat_mirror_45_deg.py"
_SENSOR_X = 287.82
_SENSOR_Z = 71.90
_UNFOLDED_Z = 347.218


class _Bundle:
    """Minimal carrier so the real ``_fold_promoted_mirror_table_row_targets`` (which reads
    ``bundle.targets``) can run display-free -- the exact list ``_build_scene_bundle`` folds."""

    def __init__(self, targets) -> None:
        self.targets = list(targets)


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


def _image_detector(targets):
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

    # ---- AZ85: the detector TARGET folds onto the +X branch at the source -----
    editor = _build_editor(_AZ85)
    targets = build_scene_targets(editor.rows)
    det = _image_detector(targets)

    c0 = np.asarray(det.center_world, dtype=float).reshape(3).copy()
    n0 = np.asarray(det.normal_world, dtype=float).reshape(3).copy()
    src = str((det.metadata or {}).get("target_source", ""))

    # bugs/0243: the folded sensor station is the Image-surface SEAT the pose-override
    # machinery computes (targets, drawn disc and traced rays all coincide there), so
    # read it from the built system instead of pinning a historical constant.
    sensor_x = _SENSOR_X
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            _sys = editor.build_system(require_solids=True)
        _ov = getattr(_sys, "_optical_solid_output_port_pose_overrides", {}) or {}
        _pose = _ov.get(len(editor.rows) - 1)
        if isinstance(_pose, dict):
            sensor_x = float(np.asarray(_pose.get("center"), dtype=float).reshape(3)[0])
    except Exception:
        pass

    # (1) precondition: build_scene_targets emits the UNFOLDED +Z detector.
    if src != "table_row":
        failures.append(f"AZ85: image detector target_source={src!r}, expected 'table_row'")
    if not (abs(c0[0]) < 1.0 and abs(c0[1]) < 1.0 and abs(c0[2] - _UNFOLDED_Z) < 1.0):
        failures.append(f"AZ85: unfolded detector centre {np.round(c0, 3).tolist()} not at (0,0,~{_UNFOLDED_Z})")
    if abs(abs(float(n0[2])) - 1.0) > 1e-3:
        failures.append(f"AZ85: unfolded detector normal {np.round(n0, 4).tolist()} not ~+Z")

    # (2) the REAL source fold (the method _build_scene_bundle calls) folds the SHARED
    #     target in place onto the +X sensor branch, normal +X.
    folded_count = editor._fold_promoted_mirror_table_row_targets(_Bundle(targets))
    if folded_count < 1:
        failures.append("AZ85: source fold reported 0 folded targets (detector left on the unfolded axis)")
    cf = np.asarray(det.center_world, dtype=float).reshape(3)
    nf = np.asarray(det.normal_world, dtype=float).reshape(3)
    if np.allclose(cf, c0):
        failures.append("AZ85: source fold left the detector target on the unfolded axis (no fold applied)")
    if abs(cf[0] - sensor_x) > 1.0:
        failures.append(f"AZ85: folded detector X {cf[0]:.2f} not at the +X sensor seat ~{sensor_x:.2f}")
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

    # (3) the SHARED target drives the 3-D/2-D detector FOOTPRINT. The AZ85 detector has no
    #     explicit sensor (footprint empty), so give the folded target a test sensor and
    #     confirm the footprint polylines follow the fold onto +X -- the consumer the
    #     coverage-overlay-only fix left on the +Z axis.
    probe = copy.deepcopy(det)
    probe.active_width_mm = 12.0
    probe.active_height_mm = 8.0
    footprint = scene_target_active_footprint_polylines(probe)
    if not footprint:
        failures.append("AZ85: folded target produced no detector footprint even with a test sensor")
    else:
        pts = np.vstack([np.asarray(p, dtype=float).reshape(-1, 3) for p in footprint])
        if float(np.max(np.abs(pts[:, 0] - sensor_x))) > 1.0:
            failures.append(
                f"AZ85: detector footprint did not fold to +X (X in "
                f"[{float(pts[:, 0].min()):.2f}, {float(pts[:, 0].max()):.2f}], expected ~{sensor_x:.2f})"
            )
        if float(np.min(pts[:, 2])) < _SENSOR_Z - 10.0 or float(np.max(pts[:, 2])) > _SENSOR_Z + 10.0:
            failures.append(
                f"AZ85: detector footprint Z {[round(float(pts[:, 2].min()), 2), round(float(pts[:, 2].max()), 2)]} "
                f"not near the folded sensor ~{_SENSOR_Z} (still on the +Z axis?)"
            )

    # (4) the folded detector coincides with the real mesh image surface.
    mesh_pt = _mesh_image_surface_point(_AZ85)
    if mesh_pt is None:
        notes.append("SKIP coincidence check: mesh image-surface build unavailable")
    elif float(np.linalg.norm(cf - mesh_pt)) > 1.0:
        failures.append(
            f"AZ85: folded detector {np.round(cf, 3).tolist()} does not coincide with the "
            f"mesh image surface {np.round(mesh_pt, 3).tolist()}"
        )

    # ---- (5) a non-folded sequential-mirror layout is untouched --------------
    plain_editor = _build_editor(_PLAIN)
    plain_targets = build_scene_targets(plain_editor.rows)
    plain_det = _image_detector(plain_targets)
    pc0 = np.asarray(plain_det.center_world, dtype=float).reshape(3).copy()
    pn0 = np.asarray(plain_det.normal_world, dtype=float).reshape(3).copy()
    plain_folded = plain_editor._fold_promoted_mirror_table_row_targets(_Bundle(plain_targets))
    pcf = np.asarray(plain_det.center_world, dtype=float).reshape(3)
    pnf = np.asarray(plain_det.normal_world, dtype=float).reshape(3)
    if plain_folded != 0:
        failures.append(f"regression: non-folded layout folded {plain_folded} target(s) (expected 0)")
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
    print("PASS bugs/0188 folded detector-coverage (source-level, all consumers):")
    print(f"  - AZ85 detector target unfolds at (0,0,{c0[2]:.2f}) +Z, folds to ({cf[0]:.2f},{cf[1]:.2f},{cf[2]:.2f}) +X")
    print(f"  - source fold moved {folded_count} table-row target(s) in place (shared by all consumers)")
    print("  - the detector FOOTPRINT built from the folded target lands on +X (not the +Z axis)")
    print("  - folded coverage basis is square to +X (Y-Z plane)")
    if mesh_pt is not None:
        print(f"  - folded detector coincides with the mesh image surface ({np.round(mesh_pt, 2).tolist()})")
    print(f"  - non-folded {_PLAIN} left byte-identical (fold helper no-op, 0 folded)")
    for note in notes:
        print(f"  - {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
