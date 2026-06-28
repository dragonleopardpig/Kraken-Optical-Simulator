"""Display-free guard: the augmented surrogate is FIELD-RESOLVED from Zemax spot-radius data.

The wavefront-augmented surrogate (0177) rides the on-axis OPD blob on every field. A vendor's
per-field Zemax "Spot Diagram Data" export (``Lens/<id>/spot radius/Mag*.txt``) carries the RMS
spot size -- and the RMS X (sagittal) / Y (tangential) sizes separately -- per field, so the
spot grows AND elongates with field: round on-axis, a radial coma/astigmatism ellipse at the
edge. This guard pins (display-free):

  * PURE (``zemax_field_spot``): the real export parses to 3 fields with RMS radius growing
    1.3 -> 4.0 -> 7.4 um; ``field_resolved_scatter`` is round on-axis (RMS-x ~ RMS-y) and
    elongated TANGENTIALLY (radially) off-axis -- and the elongation rotates with azimuth (a
    +Y field stretches in v, a +X field stretches in u).
  * INTEGRATION on the real MV-150 surrogate + the real ``Lens/15056`` data: the spot map auto-
    detects the spot-radius sibling, marks the spec ``field_resolved``, the per-field RMS varies
    (min < max), and the verdict flips to "field-resolved".
  * CONTRACT: the spot-map label prefers the field-resolved verdict.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_field_resolved_surrogate

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect
import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from KrakenOS.UI.layout_editor import Kraken3DInspector, KrakenLayoutEditor, _load_python_data
from KrakenOS.UI.render_layout_snapshot import _build_runtime_system, _snapshot_editor
from KrakenOS.UI.services.zemax_field_spot import field_resolved_scatter, parse_zemax_spot_radius

_SPOT_RADIUS = Path(__file__).resolve().parents[2] / "attachment" / "Lens" / "15056" / "spot radius" / "Mag1.0.txt"
_MV150 = Path(__file__).resolve().parents[2] / "attachment" / "machine_vision_150mm_test.py"


def _rms(arr, col):
    return float(np.sqrt(np.mean(np.asarray(arr)[:, col] ** 2)))


def _check_pure(failures: list[str], notes: list[str]) -> None:
    if not _SPOT_RADIUS.exists():
        notes.append("SKIP pure: spot-radius export unavailable")
        return
    recs = parse_zemax_spot_radius(_SPOT_RADIUS)
    if not recs or len(recs) < 3:
        failures.append(f"PURE: parsed {len(recs) if recs else 0} fields, expected >= 3")
        return
    radii = [r["rms_radius_um"] for r in recs]
    if not (radii[0] < radii[-1] and radii[0] < 2.0 < radii[-1]):
        failures.append(f"PURE: RMS radius does not grow with field ({radii})")
    # field_resolved_scatter: on-axis round; +Y elongates in v; +X elongates in u (radial).
    out = field_resolved_scatter([0.0, 0.0, 16.5], [0.0, 16.5, 0.0], recs)
    if out is None:
        failures.append("PURE: field_resolved_scatter returned None")
        return
    scatters, _rms_radius = out
    on_axis, plus_y, plus_x = scatters
    if not np.isclose(_rms(on_axis, 0), _rms(on_axis, 1), rtol=0.05):
        failures.append("PURE: on-axis spot is not round")
    if not (_rms(plus_y, 1) > 1.5 * _rms(plus_y, 0)):
        failures.append("PURE: +Y field spot is not elongated tangentially (in v)")
    if not (_rms(plus_x, 0) > 1.5 * _rms(plus_x, 1)):
        failures.append("PURE: +X field spot did not rotate its elongation to u (radial)")
    notes.append(f"pure: RMS radius {radii[0]:.2g}->{radii[-1]:.2g} µm; +Y v/u={_rms(plus_y,1)/max(_rms(plus_y,0),1e-9):.1f}x")


def _build_mv150():
    if not _MV150.exists():
        return None, None
    info = _load_python_data(_MV150)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in info["surfaces"]]
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    editor = _snapshot_editor(rows, settings)
    editor.tk = object()
    editor._normalize_special_rows()
    editor.headless = True
    editor.current_layout_file = _MV150
    system = _build_runtime_system(_MV150, editor.rows)
    return editor, system


def _check_integration(failures: list[str], notes: list[str]) -> None:
    if not (_MV150.exists() and _SPOT_RADIUS.exists()):
        notes.append("SKIP integration: MV-150 layout or Lens/15056 data unavailable")
        return
    capture = io.StringIO()
    try:
        with redirect_stdout(capture), redirect_stderr(capture):
            editor, system = _build_mv150()
            if editor is None:
                notes.append("SKIP integration: MV-150 build failed")
                return
            editor.snap_detector_to_image_plane()
            img = len(editor.rows) - 1
            det_z = sum(float(getattr(r, "thickness", 0) or 0) for r in editor.rows[:img])
            target = SimpleNamespace(
                center_world=np.array([0.0, 0.0, det_z]), normal_world=np.array([0.0, 0.0, 1.0]),
                tangent_world=np.array([1.0, 0.0, 0.0]), row_index=img,
            )
            spec = editor._compute_spot_field_map_spec(system, target, float(editor._current_wavelength()))
            verdict = editor._scene_surrogate_optics_info()
    except Exception as exc:
        failures.append(f"INTEGRATION: MV-150 field-resolved spot raised {exc!r}")
        return
    if spec is None or not spec.get("field_resolved"):
        failures.append("INTEGRATION: spot map did not auto-detect the per-field spot-radius data")
        return
    rms_lo = float(spec.get("rms_min_mm", 0.0)) * 1000.0
    rms_hi = float(spec.get("rms_max_mm", 0.0)) * 1000.0
    if not (0.0 < rms_lo < rms_hi):
        failures.append(f"INTEGRATION: per-field RMS does not grow ({rms_lo:.2g}..{rms_hi:.2g} µm)")
    if "field-resolved" not in str(verdict.get("reason", "")):
        failures.append(f"INTEGRATION: verdict did not flip to field-resolved ({verdict.get('reason')!r})")
    # The surrogate vignettes (even the chief) before the field edge, so the traced grid stops at
    # ~11.5 mm/~4.8 µm; the geometric grid must reach the configured edge (~16.3 mm) so the edge
    # coma/astig (~7 µm) actually shows. Pin both the grid reach and the edge spot magnitude.
    edge_mm = float((spec.get("field_resolved") or {}).get("edge_image_mm", 0.0))
    if edge_mm < 14.0:
        failures.append(f"INTEGRATION: field grid did not reach the field edge (edge_image_mm={edge_mm:.3g} mm, expect ~16.3)")
    if rms_hi < 6.0:
        failures.append(f"INTEGRATION: edge coma/astig not shown -- RMS max only {rms_hi:.2g} µm (expect ~7 at the ~16.3 mm edge, not the vignetted ~4.8)")
    if int(spec.get("n_spots", 0)) < 13:
        failures.append(f"INTEGRATION: geometric grid is not the full round field ({spec.get('n_spots')} spots, expect 13)")
    notes.append(f"integration: field-resolved RMS {rms_lo:.2g}->{rms_hi:.2g} µm to the {edge_mm:.1f} mm edge ({spec.get('n_spots')} spots); reason={verdict.get('reason')!r}")


def _check_contract(failures: list[str]) -> None:
    label_src = inspect.getsource(Kraken3DInspector._add_spot_field_map_overlays)
    if "field_resolved" not in label_src:
        failures.append("CONTRACT: the spot-map label does not surface the field-resolved verdict")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_pure(failures, notes)
    _check_integration(failures, notes)
    _check_contract(failures)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(f"  - {message}")
    if not passed:
        print("[FAIL] field-resolved surrogate (per-field Zemax spot data)")
        return 1
    print("[PASS] surrogate spot grows + elongates with field from Zemax per-field spot data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
