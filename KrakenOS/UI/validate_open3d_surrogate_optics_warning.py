"""Display-free guard: warn when a spot diagram comes from SURROGATE (ideal) optics.

A surrogate lens is built from KrakenOS ``Thin Lens`` (paraxial, ideal) elements -- e.g. a
vendor black-box as two thin lenses between datum planes. Such optics are aberration-free,
so a ray-traced spot / PSF / pixel-grid footprint is DEFOCUS-only (uniform across the
field), never the real lens. The spot views must say so, or a uniform spot map gets
mistaken for image quality.

This guard pins (display-free):

  * PURE (``surrogate_optics.detect_surrogate_optics``): a ``Thin Lens`` element trips it; an
    all-``Standard`` (real) prescription does not; a "Blackbox"-named element trips it.
  * INTEGRATION: the real measured MV-150 surrogate (``Thin Lens`` black-box) -> is_surrogate
    True; a real double-gauss prescription -> False.
  * CONTRACT: the 3-D Spot-map label and the 2-D Spot Diagram both consult
    ``_scene_surrogate_optics_info`` and emit a surrogate warning.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_surrogate_optics_warning

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor, _load_python_data
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
from KrakenOS.UI.services.surrogate_optics import detect_surrogate_optics
from KrakenOS.UI.validate_open3d_best_focus_surface import _double_gauss_editor

_MEASURED_SURROGATE = Path(__file__).resolve().parents[2] / "attachment" / "machine_vision_150mm_measured_test.py"


def _check_pure(failures: list[str]) -> None:
    if not detect_surrogate_optics(["Object", "Thin Lens", "Aperture", "Thin Lens", "Image"])["is_surrogate"]:
        failures.append("PURE: Thin Lens elements did not flag a surrogate")
    if detect_surrogate_optics(["Object", "Standard", "Standard", "Image"])["is_surrogate"]:
        failures.append("PURE: an all-Standard real prescription was wrongly flagged a surrogate")
    if not detect_surrogate_optics(["Standard"], ["Blackbox Group 1"])["is_surrogate"]:
        failures.append("PURE: a Blackbox-named element did not flag a surrogate")


def _editor_from_layout(path: Path):
    info = _load_python_data(path)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in info["surfaces"]]
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    editor = _snapshot_editor(rows, settings)
    editor.tk = object()
    editor._normalize_special_rows()
    return editor


def _check_integration(failures: list[str], notes: list[str]) -> None:
    if not _MEASURED_SURROGATE.exists():
        notes.append("SKIP integration: measured surrogate layout unavailable")
    else:
        cap = io.StringIO()
        try:
            with redirect_stdout(cap), redirect_stderr(cap):
                info = _editor_from_layout(_MEASURED_SURROGATE)._scene_surrogate_optics_info()
        except Exception as exc:
            failures.append(f"INTEGRATION: measured surrogate detection raised {exc!r}")
            info = {}
        if not info.get("is_surrogate"):
            failures.append("INTEGRATION: the measured MV-150 surrogate was not detected as a surrogate")
        elif int(info.get("ideal_lens_count", 0)) < 1:
            failures.append("INTEGRATION: surrogate detected but no ideal Thin Lens counted")
        else:
            notes.append(f"integration: measured surrogate -> {info.get('reason')}")

    editor, _system, _path = _double_gauss_editor()
    if editor is None:
        notes.append("SKIP integration: double-gauss real prescription unavailable")
    else:
        try:
            real = editor._scene_surrogate_optics_info()
        except Exception as exc:
            failures.append(f"INTEGRATION: real-prescription detection raised {exc!r}")
            real = {"is_surrogate": True}
        if real.get("is_surrogate"):
            failures.append("INTEGRATION: a real double-gauss prescription was wrongly flagged a surrogate")
        else:
            notes.append("integration: real double-gauss -> not a surrogate (correct)")


def _check_contracts(failures: list[str]) -> None:
    spot_map_src = inspect.getsource(Kraken3DInspector._add_spot_field_map_overlays)
    if "_scene_surrogate_optics_info" not in spot_map_src or "urrogate" not in spot_map_src:
        failures.append("CONTRACT: the 3-D Spot-map label does not warn on surrogate optics")

    ui_dir = Path(__file__).resolve().parent
    analysis_src = (ui_dir / "services" / "analysis_plot.py").read_text(encoding="utf-8")
    if "_scene_surrogate_optics_info" not in analysis_src or "urrogate" not in analysis_src:
        failures.append("CONTRACT: the 2-D Spot Diagram does not warn on surrogate optics")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_pure(failures)
    _check_integration(failures, notes)
    _check_contracts(failures)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(f"  - {message}")
    if not passed:
        print("[FAIL] surrogate-optics spot warning")
        return 1
    print("[PASS] spot views warn when optics are an ideal surrogate (defocus only, not real aberrations)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
