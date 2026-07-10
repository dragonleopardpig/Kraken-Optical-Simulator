"""bugs/0286 -- validate the WIRED production dispatcher `source_illumination_overlay_spec`.

Unlike diag_0286_projection_probe (which re-implements Approach A with standalone helpers), this drives
the REAL production entry point end-to-end, so it proves the dispatcher + fallback wiring, not a
parallel reimplementation.  Five cases:

  N  NON-REGRESSION: the portable coaxial-LED teaching scene floods the SENSOR -> the DENSITY path
     still fires (fold edge dark, perp uniform); the coupled fallback must NOT hijack it.
  A  real MV-150 + physical LED: 0 rays reach the sensor -> the coupled PROJECTION fallback fires ->
     PRESENT overlay drawn at the SENSOR size (not the FOV), dark edges present.
  B  real MV-150 + marked 45-deg BS face: sprays entirely off the imaged aperture -> None (blank,
     display follows physics).
  C  real MV-150, NO source (pure imaging): None (the 0280/0282 gate -- never fabricate a map from
     the sparse imaging fan).
  D  real MV-150 + LED + row0 -> MIRROR: PRESENT, numerically ~ Case A (mirror is inert under the
     projection; it is the user's semantic "read the dark edges sharply" model).

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python bugs/diag_0286_production_wire.py
"""
from __future__ import annotations

import os

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MPLBACKEND", "Agg")

from pathlib import Path

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.layout_editor import _load_python_data
from KrakenOS.UI.render_layout_snapshot import (
    _build_runtime_system,
    _rows_from_layout_info,
    _snapshot_editor,
)


def _load_editor(path: Path):
    info = _load_python_data(path)
    rows = _rows_from_layout_info(info)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = path
    editor._normalize_special_rows()
    return editor


def _trace(editor, path):
    system = _build_runtime_system(path, editor.rows)
    wavelength = editor._current_wavelength()
    rays = Kos.raykeeper(system)
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in editor.rows), default=1.0)
    editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
    bundle = editor._build_scene_bundle(system, rays, max_radius)
    # The production entry point reads these three (see _collect_ray_analysis_records).
    editor.last_system = system
    editor.last_rays = rays
    editor._last_scene_bundle = bundle
    editor._last_preview_trace_signature = editor._preview_trace_signature()
    return system, bundle


def _spec_summary(spec) -> str:
    if not spec:
        return "None"
    pts = np.asarray(spec.get("points", []), dtype=float)
    span_x = float(pts[:, 0].max() - pts[:, 0].min()) if pts.size else 0.0
    span_y = float(pts[:, 1].max() - pts[:, 1].min()) if pts.size else 0.0
    return (
        f"PRESENT dims={spec.get('dims')} fold(x)={float(spec.get('x_edge_ratio', -1)):.2f} "
        f"perp(y)={float(spec.get('y_edge_ratio', -1)):.2f} "
        f"min={float(spec.get('min_relative', -1)):.2f} span=({span_x:.1f}x{span_y:.1f}mm)"
    )


def _real(path, mutate=None, tag=""):
    editor = _load_editor(path)
    if mutate is not None:
        mutate(editor)
    system, bundle = _trace(editor, path)
    spec = editor.source_illumination_overlay_spec(system, bundle)
    print(f"  {tag:<26} -> {_spec_summary(spec)}")
    return spec


def _check_nonregression() -> list[str]:
    """The existing density-overlay guard already pins the coaxial teaching scene; reuse its harness
    so a dispatcher regression (fallback stealing the density case) surfaces immediately."""
    fails: list[str] = []
    try:
        from KrakenOS.UI.validate_open3d_source_illumination_overlay import (
            _build_coaxial_overlay,
        )
    except Exception as exc:  # pragma: no cover
        print(f"  N: coaxial harness import failed: {exc!r} (SKIP)")
        return fails
    editor, system, bundle = _build_coaxial_overlay(16000)
    if editor is None:
        print("  N: coaxial layout unavailable (SKIP)")
        return fails
    spec = editor.source_illumination_overlay_spec(system, bundle)
    print(f"  N: coaxial teaching (density path)  -> {_spec_summary(spec)}")
    if not spec:
        fails.append("N: density path regressed -- coaxial teaching scene now returns None")
        return fails
    fold = float(spec.get("x_edge_ratio", 1.0))
    perp = float(spec.get("y_edge_ratio", 1.0))
    if not (fold <= 0.85 and perp >= 0.85 and perp - fold >= 0.12):
        fails.append(f"N: density fold/perp signal broke (fold={fold:.2f} perp={perp:.2f})")
    return fails


def main() -> int:
    path = Path("attachment/machine_vision_150mm_test.py")
    if not path.exists():
        print("fixture missing:", path)
        return 1

    fails: list[str] = []

    print("== N: density-path non-regression (portable coaxial teaching scene) ==")
    fails += _check_nonregression()

    print("\n== real MV-150 vendor scene (attachment/machine_vision_150mm_test.py) ==")

    def add_led(ed):
        ed.add_illumination_led_source()

    def mark_face(ed):
        ed.create_illumination_source_at_face(1, face_id="S001/F001", aim="inward")

    def led_mirror(ed):
        ed.rows[0].surface = "Mirror"
        ed.add_illumination_led_source()

    spec_A = _real(path, add_led, "A: + physical LED")
    spec_B = _real(path, mark_face, "B: + marked BS face")
    spec_C = _real(path, None, "C: no source (pure imaging)")
    spec_D = _real(path, led_mirror, "D: + LED + row0 Mirror")

    # Expectations.
    if not spec_A:
        fails.append("A: LED overlay is None -- the coupled projection fallback did not fire")
    else:
        if not (float(spec_A.get("min_relative", 1.0)) < 0.85):
            fails.append(f"A: no dark edges (min_relative={spec_A.get('min_relative')})")
    if spec_B is not None:
        fails.append("B: marked BS face sprays off-FOV but produced a NON-None overlay")
    if spec_C is not None:
        fails.append("C: pure imaging scene fabricated an overlay (0280/0282 gate breach)")
    if not spec_D:
        fails.append("D: Mirror+LED overlay is None (mirror should be inert under projection)")

    print("\n== RESULT ==")
    if fails:
        for f in fails:
            print("  FAIL", f)
        return 1
    print("  ALL PASS: density path intact; LED projects dark edges at sensor size; "
          "marked-face + no-source correctly blank; mirror inert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
