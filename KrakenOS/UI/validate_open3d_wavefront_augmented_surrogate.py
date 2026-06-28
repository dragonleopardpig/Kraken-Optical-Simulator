"""Display-free guard for the wavefront-augmented surrogate (bugs/0177, option 2).

An ideal Thin-Lens ("Blackbox") surrogate is aberration-free, so its ray-traced spot is a
sub-diffraction point -- not the real lens. Attaching the vendor's Zemax wavefront (OPD) map
makes the Spot map show the REAL geometric spot (transverse ray aberration of the measured
wavefront) inside the Airy circle, and flips the surrogate verdict to "wavefront-augmented".

This guard pins, on the real MV-150 surrogate + the real `Lens/15056/wavefront/Mag1.0.txt`:

  * IDEAL (no map, focused): per-field spot RMS is sub-diffraction (< ~1.5 um);
  * AUGMENTED (map attached): per-field RMS jumps to the wavefront spot (~1.5-3 um), the
    spot stays INSIDE the (real-NA) Airy radius, `wavefront_augmented` rides the spec, and
    `_scene_surrogate_optics_info().reason` reads "wavefront-augmented";
  * the `WavefrontMap` advanced key is registered so it round-trips a .py reload.

Skips cleanly (exit 0) if the lens layout or the wavefront file is unavailable.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_wavefront_augmented_surrogate
"""

from __future__ import annotations

import io
import shutil
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor, _load_python_data
from KrakenOS.UI.render_layout_snapshot import _build_runtime_system, _snapshot_editor
from KrakenOS.UI.services.advanced_surface_attrs import ADVANCED_SURFACE_ATTR_NAMES

_REPO = Path(__file__).resolve().parents[2]
_LAYOUT = _REPO / "attachment" / "machine_vision_150mm_test.py"
_WAVEFRONT = _REPO / "attachment" / "Lens" / "15056" / "wavefront" / "Mag1.0.txt"


def _focused_editor_system_target():
    info = _load_python_data(_LAYOUT)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in info["surfaces"]]
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    editor = _snapshot_editor(rows, settings)
    editor.tk = object()
    editor._normalize_special_rows()
    editor.headless = True
    editor.current_layout_file = _LAYOUT
    system = _build_runtime_system(_LAYOUT, editor.rows)
    cap = io.StringIO()
    with redirect_stdout(cap), redirect_stderr(cap):
        editor.snap_detector_to_image_plane()  # remove the prescription defocus
    img = len(editor.rows) - 1
    det_z = sum(float(getattr(r, "thickness", 0) or 0) for r in editor.rows[:img])
    target = SimpleNamespace(
        center_world=np.array([0.0, 0.0, det_z]), normal_world=np.array([0.0, 0.0, 1.0]),
        tangent_world=np.array([1.0, 0.0, 0.0]), row_index=img,
    )
    return editor, system, target, cap


def _compute(editor, system, target, cap):
    editor.__dict__.pop("_spot_field_map_cache", None)
    editor.__dict__.pop("_wavefront_spot_cache", None)
    with redirect_stdout(cap), redirect_stderr(cap):
        return editor._compute_spot_field_map_spec(system, target, float(editor._current_wavelength()))


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []

    if "WavefrontMap" not in ADVANCED_SURFACE_ATTR_NAMES:
        failures.append("CONTRACT: 'WavefrontMap' is not registered in ADVANCED_SURFACE_FIELD_GROUPS (won't survive a .py reload)")

    if not (_LAYOUT.exists() and _WAVEFRONT.exists()):
        notes.append("SKIP integration: MV-150 surrogate layout or Lens/15056 wavefront unavailable")
        return (not failures), (failures + notes)

    try:
        editor, system, target, cap = _focused_editor_system_target()
        row = editor._surrogate_thin_lens_row()
        if row is None:
            failures.append("INTEGRATION: no Thin-Lens surrogate row in the MV-150 layout")
            return (not failures), (failures + notes)
        row.advanced = dict(getattr(row, "advanced", {}) or {})

        row.advanced["WavefrontMap"] = {"disabled": True}  # block auto-detect -> the true ideal
        ideal = _compute(editor, system, target, cap)
        if ideal is None:
            failures.append("INTEGRATION: ideal spot map returned None")
            return (not failures), (failures + notes)
        if "wavefront_augmented" in ideal:
            failures.append("INTEGRATION: ideal surrogate wrongly reported wavefront-augmented")
        ideal_rms_um = float(ideal["rms_max_mm"]) * 1000.0
        if ideal_rms_um > 1.5:
            failures.append(f"INTEGRATION: ideal spot not sub-diffraction ({ideal_rms_um:.3g} um)")

        # Isolate the wavefront-ONLY (uniform) path: mirror the real Lens/15056 folder (OPD +
        # prescription, so R is unchanged) into a temp dir but OMIT the 'spot radius/' sibling,
        # so the per-field field-resolution (0178) does not supersede the on-axis blob -- that
        # path is pinned by validate_open3d_field_resolved_surrogate. Explicit path > auto-detect.
        tmp_dir = Path(tempfile.mkdtemp(prefix="wf_aug_"))
        try:
            lens_dir = tmp_dir / "Lens" / "15056"
            wf_only = lens_dir / "wavefront" / "Mag1.0.txt"
            wf_only.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(_WAVEFRONT, wf_only)
            for presc in sorted(_WAVEFRONT.parent.parent.glob("*Presc*Data.txt")):
                shutil.copy(presc, lens_dir / presc.name)
            row.advanced["WavefrontMap"] = {"path": str(wf_only)}
            aug = _compute(editor, system, target, cap)
            if aug is None:
                failures.append("INTEGRATION: augmented spot map returned None")
                return (not failures), (failures + notes)
            if aug.get("field_resolved"):
                failures.append("INTEGRATION: field-resolution leaked into the sibling-less wavefront-only case")
            wf = aug.get("wavefront_augmented")
            aug_rms_um = float(aug["rms_max_mm"]) * 1000.0
            airy_um = float(aug.get("airy_radius_mm", 0.0)) * 1000.0
            if not wf:
                failures.append("INTEGRATION: augmented spec missing wavefront_augmented")
            if not (1.5 <= aug_rms_um <= 3.0):
                failures.append(f"INTEGRATION: augmented spot RMS {aug_rms_um:.3g} um not the expected ~2 um wavefront spot")
            if not (airy_um > 0 and aug_rms_um < airy_um):
                failures.append(f"INTEGRATION: augmented spot ({aug_rms_um:.3g} um) is not inside the Airy radius ({airy_um:.3g} um)")
            reason = editor._scene_surrogate_optics_info().get("reason", "")
            if "wavefront-augmented" not in reason:
                failures.append(f"INTEGRATION: surrogate reason did not flip ({reason!r})")
            notes.append(f"integration: ideal {ideal_rms_um:.2g} um -> wavefront-augmented {aug_rms_um:.2g} um (RMS {wf['rms_waves']:.3g} waves), inside Airy {airy_um:.2g} um")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"INTEGRATION: raised {exc!r}")

    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(f"  - {message}")
    if not passed:
        print("[FAIL] wavefront-augmented surrogate")
        return 1
    print("[PASS] wavefront-augmented surrogate shows the real Zemax OPD spot inside the Airy circle (0177)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
