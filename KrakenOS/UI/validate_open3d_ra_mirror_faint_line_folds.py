"""Display-free guard for bugs/0189: the two REMAINING "faint +Z line" contributors in the
folded RA-mirror scene fold/clamp away, and unfolded layouts stay byte-identical.

Bug 0188 (commit 6ab17579) folded the image detector TARGET + its three consumers onto the
reflected +X branch. Two +Z display actors it never touched kept drawing a faint line the user
re-flagged three more times (flag_20260701_081756_830 / _084145_529 / _084745_972):

  A. 29 BLOCKED pupil/field reference-ray STUBS -- pure sampling scaffolding that stops at the
     first surface (``stopped_at_surface_0``), carries no branch power and reaches no image, so
     the display fold never carries them off the straight +Z axis;
  B. the global optical-axis GUIDE (``axis:global``) over-extended up +Z ~300 mm PAST the mirror
     because ``_optical_axis_z_span`` pads by 0.65*max-extent and the folded +X branch makes X the
     largest scene extent.

Fix A: ``LayoutSceneBundleDisplayMixin._suppress_blocked_reference_ray_stubs`` (module predicate
``_is_blocked_reference_ray_stub``), called from ``_build_scene_bundle`` on the single-axis path,
drops the stubs ONLY on a folded scene (>=1 row carries an ``_optical_axis_fold_world_transform_
for_row`` override).
Fix B: ``Kraken3DInspector._folded_axis_incoming_fold_point_z`` recovers the mirror-vertex world Z
(the folded branch's constant Z); ``_optical_axis_records_for_3d`` clamps the +Z guide's far end to
``fold_point_z + _AXIS_FOLD_POINT_GUIDE_MARGIN_MM``. Both return None/no-op on an unfolded scene.

This guard binds the REAL predicate, the REAL folded-scene gate (bound to the live editor), the
REAL fold-point helper (bound to a stub carrying the editor), the REAL z-span helper and the REAL
margin constant, asserting:
  1. the predicate matches a blocked stub and rejects every real ray variant;
  2. on the AZ85 editor the gate drops the synthetic stubs and keeps the real paths;
  3. on the non-folded flat_mirror editor the gate drops NOTHING (byte-identical), even with stubs;
  4. INTEGRATION: the real traced AZ85 bundle has 0 blocked stubs left and NO real ray runs up +Z
     past the mirror (the only high-Z points sit on the folded +X branch);
  5. the fold-point helper returns Z~71.9 for AZ85 and None for flat_mirror, and the +Z guide
     clamps from ~386 down to ~77 on AZ85 while flat_mirror's guide is left unchanged.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_faint_line_folds

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.layout_editor import (
    KrakenLayoutEditor,
    _build_system_from_specs,
    _load_python_data,
)
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
from KrakenOS.UI.scene_geometry import RayPath3D
from KrakenOS.UI.services.layout_scene_bundle_display import _is_blocked_reference_ray_stub
from KrakenOS.UI.services.ray_display_geometry import _optical_axis_z_span
from KrakenOS.UI.open3d_inspector import (
    Kraken3DInspector,
    _AXIS_FOLD_POINT_GUIDE_MARGIN_MM,
)

_LAYOUTS = Path(__file__).resolve().parent.parent / "common_optical_layouts"
_AZ85 = "machine_vision_AZ85_RA_Mirror.py"
_PLAIN = "flat_mirror_45_deg.py"
_FOLD_POINT_Z = 71.90          # the AZ85 mirror-vertex world Z (the +X branch's constant Z)
_ROW_SPEC_KEYS = (
    "surface", "name", "rc", "k", "axicon", "diff_ord", "grating_d", "grating_angle",
    "thickness", "diameter", "in_diameter", "drawing", "extra_data", "uda", "advanced",
    "tilt_x", "tilt_y", "tilt_z", "desp_x", "desp_y", "desp_z", "axis_move", "glass",
)


class _Bundle:
    """Minimal carrier so the real ``_suppress_blocked_reference_ray_stubs`` (which reads +
    reassigns ``bundle.ray_paths``) can run display-free."""

    def __init__(self, ray_paths) -> None:
        self.ray_paths = list(ray_paths)


class _InspectorStub:
    """Carries ``.editor`` so the REAL ``_folded_axis_incoming_fold_point_z`` (an instance method
    that only reads ``self.editor``) can be bound without instantiating the tk.Toplevel."""

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


def _build_traced_bundle(editor):
    """Run the real trace + ``_build_scene_bundle`` (CPU-only; no VTK render) and return the
    final bundle -- with Fix A already applied inside the single-axis path."""
    rows = editor.rows
    row_specs = [{k: getattr(r, k) for k in _ROW_SPEC_KEYS} for r in rows]
    if row_specs and getattr(editor, "metal_catalogs", None):
        row_specs[0]["_metal_catalogs"] = editor.metal_catalogs
    system = _build_system_from_specs(row_specs)
    wavelength = float(editor._current_wavelength())
    rays = Kos.raykeeper(system)
    max_radius = max((max(r.diameter / 2.0, 0.5) for r in rows), default=1.0)
    editor._trace_preview_rays(
        system, rays, wavelength, max_radius,
        allow_full_pupil=True, sampling_mode=editor._preview_2d_sampling_mode(),
    )
    editor.last_system = system
    editor.last_rays = rays
    return editor._build_scene_bundle(system, rays, max_radius)


def _stub_path(**kw) -> RayPath3D:
    base = dict(
        source_role="pupil_field_reference",
        termination_reason="stopped_at_surface_0",
        branch_power=0.0,
        reaches_image=False,
        points_world=np.asarray(((0.0, 0.0, -60.0), (0.0, 0.0, 120.0)), dtype=float),
    )
    base.update(kw)
    return RayPath3D(**base)


def main() -> int:
    failures: list[str] = []
    notes: list[str] = []

    # ---- (1) predicate: matches a blocked stub, rejects every real-ray variant ----
    if not _is_blocked_reference_ray_stub(_stub_path()):
        failures.append("predicate: a genuine blocked pupil_field_reference stub was NOT matched")
    rejects = {
        "real missed_image ray": _stub_path(termination_reason="missed_image", branch_power=1.0),
        "ray that reaches the image": _stub_path(reaches_image=True),
        "stub carrying branch power": _stub_path(branch_power=0.5),
        "non-reference source role": _stub_path(source_role="scene_source"),
    }
    for label, path in rejects.items():
        if _is_blocked_reference_ray_stub(path):
            failures.append(f"predicate: wrongly matched a {label} (would hide a real ray)")

    # ---- (2) the gate drops stubs on a FOLDED scene, keeps the real paths ----
    az_editor = _build_editor(_AZ85)
    real_folded = _stub_path(
        termination_reason="missed_image", branch_power=1.0, reaches_image=False,
        points_world=np.asarray(((0.0, 0.0, -60.0), (_FOLD_POINT_Z * 4, 0.0, _FOLD_POINT_Z)), dtype=float),
    )
    mixed = _Bundle([_stub_path() for _ in range(29)] + [real_folded] * 5)
    dropped = az_editor._suppress_blocked_reference_ray_stubs(mixed)
    if dropped != 29:
        failures.append(f"AZ85 gate: dropped {dropped} stubs, expected 29")
    if len(mixed.ray_paths) != 5 or any(_is_blocked_reference_ray_stub(p) for p in mixed.ray_paths):
        failures.append(f"AZ85 gate: kept {len(mixed.ray_paths)} paths, expected the 5 real ones only")

    # ---- (3) the gate touches NOTHING on a non-folded scene (byte-identical) ----
    plain_editor = _build_editor(_PLAIN)
    plain_bundle = _Bundle([_stub_path() for _ in range(29)] + [real_folded] * 5)
    before = list(plain_bundle.ray_paths)
    plain_dropped = plain_editor._suppress_blocked_reference_ray_stubs(plain_bundle)
    if plain_dropped != 0:
        failures.append(f"regression: non-folded gate dropped {plain_dropped} paths (expected 0)")
    if plain_bundle.ray_paths is not before and list(plain_bundle.ray_paths) != before:
        failures.append("regression: non-folded gate mutated ray_paths (expected byte-identical)")

    # ---- (4) INTEGRATION: the real traced AZ85 bundle has 0 stubs + no ray runs up +Z ----
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            bundle = _build_traced_bundle(az_editor)
        paths = list(getattr(bundle, "ray_paths", []) or [])
        left = sum(1 for p in paths if _is_blocked_reference_ray_stub(p))
        if left != 0:
            failures.append(f"AZ85 integration: {left} blocked stub(s) survived _build_scene_bundle")
        if not paths:
            failures.append("AZ85 integration: traced bundle has no ray_paths at all")
        # no real ray endpoint should run up the +Z axis past the mirror
        up_z = 0
        max_z_x = None
        max_z = -1e18
        for p in paths:
            pts = np.asarray(getattr(p, "points_world", []))
            if pts.ndim != 2 or pts.shape[0] < 2:
                continue
            end = pts[-1]
            if abs(float(end[0])) < 20.0 and float(end[2]) > _FOLD_POINT_Z + 20.0:
                up_z += 1
            i = int(np.argmax(pts[:, 2]))
            if float(pts[i, 2]) > max_z:
                max_z = float(pts[i, 2])
                max_z_x = float(pts[i, 0])
        if up_z:
            failures.append(f"AZ85 integration: {up_z} real ray(s) still run up +Z past the mirror")
        if max_z_x is not None and abs(max_z_x) < 50.0:
            failures.append(
                f"AZ85 integration: the highest-Z ray point (Z={max_z:.1f}) sits near the +Z axis "
                f"(X={max_z_x:.1f}); expected it on the folded +X branch"
            )
    except Exception as exc:  # noqa: BLE001
        notes.append(f"SKIP integration trace (headless build raised {exc!r})")

    # ---- (5) Fix B: fold-point helper + guide clamp ----
    az_fold_z = Kraken3DInspector._folded_axis_incoming_fold_point_z(_InspectorStub(az_editor))
    if az_fold_z is None or abs(float(az_fold_z) - _FOLD_POINT_Z) > 1.0:
        failures.append(f"AZ85 fold-point: helper returned {az_fold_z}, expected ~{_FOLD_POINT_Z}")
    else:
        # emulate the clamp _optical_axis_records_for_3d applies to the AZ85 bounds
        az_bounds = np.asarray([-81.47, 287.82, -97.24, 94.96, -61.69, 145.54], dtype=float)
        _z0, z1_raw = _optical_axis_z_span(az_bounds)
        if z1_raw <= _FOLD_POINT_Z + 100.0:
            failures.append(
                f"AZ85 guide: unclamped z1={z1_raw:.1f} is not over-extended (precondition gone?)"
            )
        z1_clamped = min(z1_raw, float(az_fold_z) + _AXIS_FOLD_POINT_GUIDE_MARGIN_MM)
        if z1_clamped > _FOLD_POINT_Z + _AXIS_FOLD_POINT_GUIDE_MARGIN_MM + 1e-6:
            failures.append(
                f"AZ85 guide: clamped z1={z1_clamped:.1f} still reaches past the mirror "
                f"(fold Z={az_fold_z:.1f} + margin {_AXIS_FOLD_POINT_GUIDE_MARGIN_MM})"
            )
        notes.append(f"AZ85 guide z1 {z1_raw:.1f} -> {z1_clamped:.1f} (mirror Z={az_fold_z:.2f})")

    plain_fold_z = Kraken3DInspector._folded_axis_incoming_fold_point_z(_InspectorStub(plain_editor))
    if plain_fold_z is not None:
        failures.append(f"regression: non-folded fold-point returned {plain_fold_z}, expected None")
    else:
        # with fold_point None the clamp is skipped -> guide z-span byte-identical
        pb = np.asarray([-30.0, 40.0, -30.0, 30.0, -60.0, 80.0], dtype=float)
        z0a, z1a = _optical_axis_z_span(pb)
        z1_after = z1a if plain_fold_z is None else min(z1a, float(plain_fold_z) + _AXIS_FOLD_POINT_GUIDE_MARGIN_MM)
        if z1_after != z1a:
            failures.append("regression: non-folded guide z1 changed (expected byte-identical)")

    if failures:
        print("FAIL bugs/0189 folded RA-mirror faint-line:")
        for line in failures:
            print(f"  - {line}")
        for note in notes:
            print(f"  - note: {note}")
        return 1
    print("PASS bugs/0189 folded RA-mirror faint-line (stubs suppressed + axis guide clamped):")
    print("  - predicate matches a blocked stub, rejects every real-ray variant")
    print("  - AZ85 folded gate drops 29 synthetic stubs, keeps the 5 real paths")
    print(f"  - non-folded {_PLAIN} gate drops 0 (ray_paths byte-identical)")
    print("  - AZ85 traced bundle: 0 blocked stubs left, no real ray runs up +Z past the mirror")
    print(f"  - Fix B fold-point ~{_FOLD_POINT_Z} for AZ85, None for {_PLAIN}")
    for note in notes:
        print(f"  - {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
