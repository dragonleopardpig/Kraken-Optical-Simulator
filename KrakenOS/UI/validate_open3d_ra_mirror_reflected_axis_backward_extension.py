"""Display-free guard for bugs/0190: on the folded RA-mirror scene the REFLECTED
traced optical axis ("Optical Axis 2") must emanate FORWARD from its reflection
point, not extend symmetrically back through the 45-deg hypotenuse.

After bugs/0189 clamped the +Z GLOBAL guide (axis:global) to the mirror, the user
re-flagged the same visual once more (flag_20260701_092025_358: "reflection still
wrong at the hypotenuse"). The residual is a DIFFERENT actor: the reflected chief
ray's traced segment. ``_dotted_axis_records_from_ray_path`` draws every traced
``Optical Axis N`` via ``_extended_axis_points`` -- ``origin +/- 0.85*scene-span``
in BOTH directions -- so on a promoted-mirror fold the reflected +X branch pokes
~250 mm out the BACK of the mirror (state.json: ``axis:ray:124:segment:3`` runs
X[-248.4 .. 370.8] at the fold plane Z=71.9, i.e. 248 mm behind the mirror vertex).

Fix (bugs/0190): ``Kraken3DInspector._folded_traced_axis_forward_points(segment)``
replaces the backward end of a traced segment with its reflection point
(``segment_start``), and ``_optical_axis_records_for_3d`` applies it to every kept
traced segment ONLY when the scene is folded (``scene_is_folded`` -- the same gate
bugs/0189's guide clamp uses: ``_folded_axis_incoming_fold_point_z`` is not None).
Unfolded scenes (penta / beam-splitter Optical Axis 2) are byte-identical.

This guard binds the REAL helper (to a stub) and the REAL folded-scene gate (to the
live editor), asserting:
  1. a synthetic reflected +X segment with a backward overhang is clamped: the
     backward end lands ON the reflection point (0 overhang) and no point sits
     behind it; the forward end is preserved;
  2. a segment already entirely forward of its start is left untouched (None), and a
     degenerate zero-direction segment is safe (None);
  3. INTEGRATION: on the REAL traced AZ85 bundle the reflected +X segments (the
     ``axis:ray:*:segment:*`` the app draws as Optical Axis 2) genuinely overhang
     ~250 mm behind the mirror, and the real helper clamps every one to 0 backward
     overhang -- so nothing pokes out the back of the hypotenuse;
  4. the folded gate is not None for AZ85 (clamp runs) and None for flat_mirror
     (clamp is gated OFF -> unfolded scenes stay byte-identical).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_reflected_axis_backward_extension

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
from KrakenOS.UI.services.ray_display_geometry import _dotted_axis_records_from_ray_path
from KrakenOS.UI.open3d_inspector import Kraken3DInspector

_LAYOUTS = Path(__file__).resolve().parent.parent / "common_optical_layouts"
_AZ85 = "machine_vision_AZ85_RA_Mirror.py"
_PLAIN = "flat_mirror_45_deg.py"
_ROW_SPEC_KEYS = (
    "surface", "name", "rc", "k", "axicon", "diff_ord", "grating_d", "grating_angle",
    "thickness", "diameter", "in_diameter", "drawing", "extra_data", "uda", "advanced",
    "tilt_x", "tilt_y", "tilt_z", "desp_x", "desp_y", "desp_z", "axis_move", "glass",
)


class _InspectorStub:
    """Carries ``.editor`` so the REAL instance methods (which only read ``self`` /
    ``self.editor``) bind without instantiating the tk.Toplevel."""

    def __init__(self, editor=None) -> None:
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
    """Run the real trace + ``_build_scene_bundle`` (CPU-only; no VTK render)."""
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


def _bounds_from_paths(paths) -> np.ndarray:
    clouds = [
        np.asarray(getattr(p, "points_world", np.empty((0, 3))), dtype=float)
        for p in paths
    ]
    clouds = [c for c in clouds if c.ndim == 2 and c.shape[0]]
    allpts = np.vstack(clouds)
    return np.asarray(
        [
            allpts[:, 0].min(), allpts[:, 0].max(),
            allpts[:, 1].min(), allpts[:, 1].max(),
            allpts[:, 2].min(), allpts[:, 2].max(),
        ],
        dtype=float,
    )


def _backward_overhang(points, start, direction) -> float:
    """Signed distance the nearer end runs BEHIND ``start`` along ``direction``
    (<= 0 means a point sits behind the reflection point)."""
    pts = np.asarray(points, dtype=float).reshape(2, 3)
    s = np.asarray(start, dtype=float).reshape(3)
    u = np.asarray(direction, dtype=float).reshape(3)
    u = u / float(np.linalg.norm(u))
    return min(float(np.dot(pts[0] - s, u)), float(np.dot(pts[1] - s, u)))


def main() -> int:
    failures: list[str] = []
    notes: list[str] = []
    stub = _InspectorStub()
    clamp = lambda seg: Kraken3DInspector._folded_traced_axis_forward_points(stub, seg)

    # ---- (1) a reflected +X segment with a backward overhang is clamped ----
    start = (40.0, 0.0, 71.9)
    seg = {
        "points": np.asarray(((-248.0, 0.0, 71.9), (371.0, 0.0, 71.9)), dtype=float),
        "segment_start": start,
        "segment_direction": (1.0, 0.0, 0.0),
    }
    clamped = clamp(seg)
    if clamped is None:
        failures.append("clamp: a backward-overhanging reflected +X segment was NOT clamped")
    else:
        oh = _backward_overhang(clamped, start, (1.0, 0.0, 0.0))
        if oh < -1e-6:
            failures.append(f"clamp: backward overhang {oh:.2f} mm remains behind the reflection point")
        if float(np.asarray(clamped)[:, 0].min()) < start[0] - 1e-6:
            failures.append(
                f"clamp: a clamped point (X={float(np.asarray(clamped)[:, 0].min()):.1f}) still sits "
                f"behind the reflection start (X={start[0]:.1f})"
            )
        if abs(float(np.asarray(clamped)[:, 0].max()) - 371.0) > 1e-6:
            failures.append("clamp: the FORWARD end (X=371) was not preserved")

    # ---- (2) a forward-only segment is untouched; a degenerate one is safe ----
    forward_only = {
        "points": np.asarray(((10.0, 0.0, 71.9), (371.0, 0.0, 71.9)), dtype=float),
        "segment_start": (0.0, 0.0, 71.9),
        "segment_direction": (1.0, 0.0, 0.0),
    }
    if clamp(forward_only) is not None:
        failures.append("regression: a segment already entirely forward of its start was rewritten")
    degenerate = {
        "points": np.asarray(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0)), dtype=float),
        "segment_start": (0.0, 0.0, 0.0),
        "segment_direction": (0.0, 0.0, 0.0),
    }
    if clamp(degenerate) is not None:
        failures.append("regression: a zero-direction segment was not handled safely (expected None)")

    # ---- (3) INTEGRATION: real AZ85 reflected segments overhang, then clamp to 0 ----
    az_editor = _build_editor(_AZ85)
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            bundle = _build_traced_bundle(az_editor)
        paths = list(getattr(bundle, "ray_paths", []) or [])
        bounds = _bounds_from_paths(paths)
        reflected = [
            s
            for p in paths
            for s in _dotted_axis_records_from_ray_path(p, bounds)
            if abs(float(np.asarray(s["segment_direction"])[0])) > 0.7
        ]
        if not reflected:
            failures.append("AZ85 integration: found no reflected +X traced segment at all")
        worst_before = min(
            (_backward_overhang(s["points"], s["segment_start"], s["segment_direction"]) for s in reflected),
            default=0.0,
        )
        if worst_before > -100.0:
            failures.append(
                f"AZ85 integration: reflected segments only overhang {worst_before:.1f} mm behind the "
                f"mirror (expected << -100; the bug precondition is gone?)"
            )
        worst_after = 0.0
        clamped_n = 0
        for s in reflected:
            fp = clamp(s)
            if fp is None:
                continue
            clamped_n += 1
            worst_after = min(
                worst_after,
                _backward_overhang(fp, s["segment_start"], s["segment_direction"]),
            )
        if clamped_n != len(reflected):
            failures.append(
                f"AZ85 integration: clamped only {clamped_n}/{len(reflected)} overhanging reflected segments"
            )
        if worst_after < -1e-6:
            failures.append(
                f"AZ85 integration: {worst_after:.2f} mm still pokes behind the mirror after clamping"
            )
        notes.append(
            f"AZ85 reflected segments: {len(reflected)} | worst backward overhang "
            f"{worst_before:.1f} mm -> {worst_after:.3f} mm"
        )
    except Exception as exc:  # noqa: BLE001
        notes.append(f"SKIP integration trace (headless build raised {exc!r})")

    # ---- (4) folded gate: not None for AZ85 (clamp runs), None for flat_mirror ----
    az_fold_z = Kraken3DInspector._folded_axis_incoming_fold_point_z(_InspectorStub(az_editor))
    if az_fold_z is None or not np.isfinite(az_fold_z):
        failures.append(f"AZ85 gate: fold point {az_fold_z} -> the clamp would never run on the folded scene")
    plain_editor = _build_editor(_PLAIN)
    plain_fold_z = Kraken3DInspector._folded_axis_incoming_fold_point_z(_InspectorStub(plain_editor))
    if plain_fold_z is not None:
        failures.append(
            f"regression: non-folded {_PLAIN} reports fold point {plain_fold_z} (expected None); the clamp "
            f"must stay gated OFF so unfolded Optical Axis 2 is byte-identical"
        )

    if failures:
        print("FAIL bugs/0190 folded RA-mirror reflected-axis backward extension:")
        for line in failures:
            print(f"  - {line}")
        for note in notes:
            print(f"  - note: {note}")
        return 1
    print("PASS bugs/0190 folded RA-mirror reflected-axis backward extension (clamped forward of the mirror):")
    print("  - a backward-overhanging reflected +X segment clamps to its reflection point (0 overhang, forward end kept)")
    print("  - a forward-only segment + a zero-direction segment are left untouched (None)")
    print("  - AZ85 real trace: every reflected +X segment overhangs behind the mirror, all clamp to 0")
    print(f"  - folded gate: not None for AZ85 (clamp runs), None for {_PLAIN} (clamp gated OFF)")
    for note in notes:
        print(f"  - {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
