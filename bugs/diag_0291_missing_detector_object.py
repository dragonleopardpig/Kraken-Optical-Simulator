"""bugs/0291 -- flag_20260713_090936_572 "detector and object plane seem missing" after Add LED.

Hypothesis: adding a physical illumination LED makes the flood reflect off the BS -> branch detectors
are derived -> `drop_superseded_image_display` (bugs/0093/0098) drops the sequential Image/detector
because `has_branch_detector` is True -- but the branch detectors it "supersedes" it with are
`draw_suppressed` illumination-flood phantoms (bugs/0285), so NOTHING draws and the real detector
vanishes.  This probe prints the bundle targets WITHOUT and WITH the added LED on the REAL vendor scene.

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python -u bugs/diag_0291_missing_detector_object.py
"""
from __future__ import annotations

import os
import types

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MPLBACKEND", "Agg")

from pathlib import Path

import KrakenOS as Kos
from KrakenOS.UI.layout_editor import _load_python_data
from KrakenOS.UI.render_layout_snapshot import (
    _build_runtime_system,
    _rows_from_layout_info,
    _snapshot_editor,
)

PATH = Path("attachment/machine_vision_150mm_test.py")
MODULE_BOUNDS = (1.1, 56.1, -39.0, 39.0, 187.0, 265.0)


def _load_editor():
    info = _load_python_data(PATH)
    rows = _rows_from_layout_info(info)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = PATH
    editor._normalize_special_rows()
    return editor


def _bundle(editor):
    system = _build_runtime_system(PATH, editor.rows)
    wavelength = editor._current_wavelength()
    rays = Kos.raykeeper(system)
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in editor.rows), default=1.0)
    editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
    bundle = editor._build_scene_bundle(system, rays, max_radius)
    return bundle


def _dump(tag, editor):
    bundle = _bundle(editor)
    targets = list(getattr(bundle, "targets", []) or [])
    print(f"[{tag}] {len(targets)} scene targets:")
    for t in targets:
        ri = int(getattr(t, "row_index", -1))
        role = getattr(t, "role", "")
        is_det = bool(getattr(t, "is_detector", False))
        is_obj = bool(getattr(t, "is_object", False))
        supp = bool((getattr(t, "metadata", None) or {}).get("draw_suppressed"))
        tid = getattr(t, "target_id", "")
        z = None
        for attr in ("plane_z", "z", "position"):
            v = getattr(t, attr, None)
            if v is not None:
                z = v
                break
        print(f"    row={ri:>7} det={is_det!s:5} obj={is_obj!s:5} supp={supp!s:5} role={role!r} id={tid!r} z={z}")
    # surface curves + labels for object/image
    curves = list(getattr(bundle, "surface_curves", []) or [])
    labels = list(getattr(bundle, "labels", []) or [])
    print(f"[{tag}] surface_curves rows: {sorted({int(getattr(c,'row_index',-1)) for c in curves})}")
    lab_txts = [str(getattr(l, 'text', getattr(l, 'label', ''))) for l in labels]
    print(f"[{tag}] labels: {lab_txts}")
    return bundle


def main() -> int:
    if not PATH.exists():
        print("fixture missing:", PATH)
        return 1

    print("=" * 90)
    print("A. vendor scene, NO LED -- baseline: object + detector present")
    print("=" * 90)
    _dump("no-LED", _load_editor())

    print("=" * 90)
    print("B. vendor scene + module-seeded LED -- do object + detector survive?")
    print("=" * 90)
    editor = _load_editor()
    editor.imported_led_step_path = "synthetic-OPT-CO90-X.STEP"
    editor._transformed_imported_led_step_mesh = lambda: types.SimpleNamespace(bounds=MODULE_BOUNDS)
    editor.add_illumination_led_source(record_history=False)
    _dump("with-LED", editor)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
