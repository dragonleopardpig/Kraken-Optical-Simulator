"""bugs/0292 -- the folded coaxial illuminator's EFFECTIVE illumination area bounds the imaging FOV.

The user's ask: launch the imaging FOV from the folded LED's effective illumination area (fold axis
55*cos45 = 38.9 mm, perp 74 mm) instead of the 39x39 imaging-lens FOV, so the 2 fold-axis dark edges
appear on the sensor.

The folded flood cannot be traced through to foreshorten (a split branch ray never consults the later
limiting aperture -- the bugs/0287/0289 engine wall), so the effective area is built GEOMETRICALLY from a
coaxial-illuminator DESCRIPTOR attached to the LED spec at "Add Illumination Source" time
(source_modeling.add_illumination_led_source): the RAW aperture + fold angle, NOT a pre-computed 38.9.  The
overlay foreshortens the fold axis itself (aperture*cos(fold_angle)) and images the rectangle onto the
sensor at TRUE scale with the scene's own paraxial |m| via the existing bugs/0288
``project_footprint_onto_sensor`` -- under-fill on the fold axis draws the dark edges, over-fill on the
perp axis stays uniform.  Nothing is layout-tuned.

All checks are display-free (no VTK / pyvista window).  The real-vendor-scene check SKIPs when the
gitignored attachment is absent.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_effective_illumination_area

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect
import os

import numpy as np

_ATTACHMENT = "attachment/machine_vision_150mm_test.py"


def _edge_ratios(map_data):
    """(fold_edge, perp_edge) vs centre for a projected sensor map (x = fold axis, y = perp axis)."""
    density = np.asarray(map_data["density"], dtype=float)
    ny, nx = density.shape
    cy, cx = ny // 2, nx // 2
    centre = density[cy, cx] or 1.0
    fold = 0.5 * (float(density[cy, 0]) + float(density[cy, -1])) / centre
    perp = 0.5 * (float(density[0, cx]) + float(density[-1, cx])) / centre
    return fold, perp


# --------------------------------------------------------------------------------------------------
# 1. _aperture_soft_edge -- the diffuse roll-off
# --------------------------------------------------------------------------------------------------
def _check_soft_edge(failures: list[str]) -> None:
    from KrakenOS.UI.services.source_object_coupling import _aperture_soft_edge

    half, pen = 10.0, 2.0
    coords = np.array([0.0, 5.0, half - 0.5 * pen, half, half + 0.5 * pen, half + 5.0])
    vals = _aperture_soft_edge(coords, half, pen)
    if not np.isclose(vals[0], 1.0) or not np.isclose(vals[1], 1.0):
        failures.append("SOFT_EDGE: interior is not fully lit (== 1.0)")
    if not np.isclose(vals[2], 1.0):
        failures.append("SOFT_EDGE: roll-off started before the penumbra band")
    if not np.isclose(vals[3], 0.5, atol=1e-6):
        failures.append(f"SOFT_EDGE: value at the aperture edge is {vals[3]:.3f}, not 0.5")
    if not np.isclose(vals[4], 0.0, atol=1e-6) or not np.isclose(vals[5], 0.0):
        failures.append("SOFT_EDGE: value past the penumbra band is not 0.0")
    # monotone non-increasing across the band
    band = _aperture_soft_edge(np.linspace(half - 0.5 * pen, half + 0.5 * pen, 9), half, pen)
    if not np.all(np.diff(band) <= 1e-9):
        failures.append("SOFT_EDGE: the roll-off is not monotone")
    # a zero penumbra must not divide-by-zero
    hard = _aperture_soft_edge(np.array([half - 1.0, half + 1.0]), half, 0.0)
    if not (np.isclose(hard[0], 1.0) and np.isclose(hard[1], 0.0)):
        failures.append("SOFT_EDGE: zero penumbra did not degrade to a hard step")


# --------------------------------------------------------------------------------------------------
# 2. coaxial_illuminator_footprint_map -- foreshortening, fold axis, degenerate, projection
# --------------------------------------------------------------------------------------------------
def _check_footprint_map(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI.services.source_object_coupling import (
        coaxial_illuminator_footprint_map,
        project_footprint_onto_sensor,
    )

    # FORESHORTENING: fold half = 0.5*aperture*cos(angle); perp half = 0.5*aperture (unchanged).
    m = coaxial_illuminator_footprint_map(55.0, 74.0, 45.0, fold_axis="x")
    if m is None:
        failures.append("MAP: a valid folded aperture produced no map")
        return
    expect_fold = 0.5 * 55.0 * np.cos(np.radians(45.0))
    if not np.isclose(m["fold_half_mm"], expect_fold, atol=1e-6):
        failures.append(f"MAP: fold half {m['fold_half_mm']:.3f} != 55*cos45/2 = {expect_fold:.3f}")
    if not np.isclose(m["perp_half_mm"], 37.0, atol=1e-6):
        failures.append(f"MAP: perp half {m['perp_half_mm']:.3f} != 74/2 (foreshortened the wrong axis?)")
    if m["fold_axis"] != "x" or float(np.max(m["density"])) != 1.0:
        failures.append("MAP: fold axis / peak-normalisation wrong")
    if not (m["penumbra_mm"] > 0.0):
        failures.append("MAP: default diffuse penumbra is not positive")

    # FOLD AXIS 'y' swaps which sensor axis under-fills.
    my = coaxial_illuminator_footprint_map(55.0, 74.0, 45.0, fold_axis="y")
    if my is None or my["fold_axis"] != "y":
        failures.append("MAP: fold_axis='y' not honoured")
    else:
        # x_edges now carry the (larger) perp half, y_edges the (smaller) fold half
        if not (float(my["x_edges"][-1]) > float(my["y_edges"][-1])):
            failures.append("MAP: fold_axis='y' did not put the foreshortened axis on y")

    # ON-AXIS (fold_angle 0): no foreshortening -> fold half == 0.5*aperture.
    m0 = coaxial_illuminator_footprint_map(55.0, 74.0, 0.0, fold_axis="x")
    if m0 is None or not np.isclose(m0["fold_half_mm"], 27.5, atol=1e-6):
        failures.append("MAP: fold_angle=0 must not foreshorten (fold half should be 27.5)")

    # DEGENERATE inputs -> None (never fabricate a footprint).
    for bad in (
        coaxial_illuminator_footprint_map(0.0, 74.0, 45.0),
        coaxial_illuminator_footprint_map(55.0, -1.0, 45.0),
        coaxial_illuminator_footprint_map(float("nan"), 74.0, 45.0),
    ):
        if bad is not None:
            failures.append("MAP: a degenerate aperture must yield None")

    # PROJECTION on the real scene's own conjugates: fold under-fills -> dark, perp over-fills -> uniform.
    mag, half_sensor = 0.5908, 11.52
    fov_half = half_sensor / mag
    if not (m["fold_half_mm"] < fov_half):  # 19.45 < 19.50
        failures.append(f"MAP: folded aperture {m['fold_half_mm']:.2f} does not under-fill the imaged FOV {fov_half:.2f}")
    proj = project_footprint_onto_sensor(m, mag, half_sensor, half_sensor)
    if proj is None:
        failures.append("MAP: projecting the folded aperture onto the sensor produced None")
        return
    fold_edge, perp_edge = _edge_ratios(proj)
    if not (fold_edge < 0.85):
        failures.append(f"MAP: fold edges not dark on the sensor (edge {fold_edge:.3f})")
    if not (perp_edge >= 0.85):
        failures.append(f"MAP: perp edges not uniform on the sensor (edge {perp_edge:.3f})")

    # OVER-FILL both axes (angle 0, big aperture) -> uniform, no fabricated edges.
    over = coaxial_illuminator_footprint_map(80.0, 80.0, 0.0, fold_axis="x")
    over_proj = project_footprint_onto_sensor(over, mag, half_sensor, half_sensor)
    if over_proj is not None and float(np.min(over_proj["density"])) < 0.9:
        failures.append("MAP: an over-filling folded aperture fabricated dark edges")

    notes.append(
        f"footprint map: fold half {m['fold_half_mm']:.2f} mm (=55*cos45/2), perp 37.0 mm, "
        f"penumbra {m['penumbra_mm']:.2f} mm -> sensor fold edge {fold_edge:.3f} / perp {perp_edge:.3f}"
    )


# --------------------------------------------------------------------------------------------------
# 3. coaxial_illuminator_descriptor -- the spec reader
# --------------------------------------------------------------------------------------------------
def _check_descriptor_reader(failures: list[str]) -> None:
    from KrakenOS.UI.scene_source_analysis import coaxial_illuminator_descriptor

    spec = {
        "physical": True,
        "coaxial_illuminator": True,
        "coaxial_aperture_fold_mm": 55.0,
        "coaxial_aperture_perp_mm": 74.0,
        "coaxial_fold_angle_deg": 45.0,
        "coaxial_fold_axis": "x",
    }
    d = coaxial_illuminator_descriptor(spec)
    if d is None:
        failures.append("READER: a valid coaxial spec returned None")
    else:
        if not (d["aperture_fold_mm"] == 55.0 and d["aperture_perp_mm"] == 74.0):
            failures.append("READER: aperture dims not parsed")
        if d["fold_angle_deg"] != 45.0 or d["fold_axis"] != "x":
            failures.append("READER: fold angle / axis not parsed")
        if d["penumbra_mm"] is not None:
            failures.append("READER: absent penumbra should read None (overlay picks the default)")

    # non-coaxial / disabled specs -> None
    if coaxial_illuminator_descriptor({"physical": True}) is not None:
        failures.append("READER: a non-coaxial spec must return None")
    if coaxial_illuminator_descriptor({"coaxial_illuminator": False, "coaxial_aperture_fold_mm": 5}) is not None:
        failures.append("READER: coaxial_illuminator False must return None")
    # missing dims -> None (no fabricated aperture)
    if coaxial_illuminator_descriptor({"coaxial_illuminator": True}) is not None:
        failures.append("READER: a coaxial flag with no aperture must return None")
    # fold axis normalisation + explicit penumbra
    d2 = coaxial_illuminator_descriptor(
        {"coaxial_illuminator": True, "coaxial_aperture_fold_mm": 30, "coaxial_aperture_perp_mm": 40,
         "coaxial_fold_axis": "vertical", "coaxial_penumbra_mm": 3.0}
    )
    if d2 is None or d2["fold_axis"] != "y" or d2["penumbra_mm"] != 3.0:
        failures.append("READER: fold-axis alias / explicit penumbra not honoured")


# --------------------------------------------------------------------------------------------------
# 4. _coaxial_illuminator_descriptor_from_module -- the add-time auto-seed
# --------------------------------------------------------------------------------------------------
class _StubMesh:
    def __init__(self, bounds):
        self.bounds = bounds


class _StubModuleEditor:
    def __init__(self, bounds):
        self._bounds = bounds

    def _transformed_imported_led_step_mesh(self):
        return _StubMesh(self._bounds) if self._bounds is not None else None


def _check_descriptor_seed(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI.services.source_modeling import SourceModelingMixin

    seed = SourceModelingMixin._coaxial_illuminator_descriptor_from_module

    # SIDE-mounted LED on +x face: thin along x (thickness), 74 along y, 55 along z (optical axis).
    # Fold plane = x-z (decentred in x). Expect fold_axis x, aperture_fold = z-extent (55), perp = y (74).
    side = seed(
        _StubModuleEditor((88.0, 90.0, -37.0, 37.0, 175.0, 230.0)),
        aperture_fold_fallback=1.0, aperture_perp_fallback=1.0,
    )
    if not (side["coaxial_illuminator"] is True):
        failures.append("SEED: descriptor missing the coaxial flag")
    if side["coaxial_fold_axis"] != "x":
        failures.append(f"SEED: side LED fold axis {side['coaxial_fold_axis']} != x")
    if not np.isclose(side["coaxial_aperture_fold_mm"], 55.0):
        failures.append(f"SEED: side LED fold aperture {side['coaxial_aperture_fold_mm']:.1f} != 55 (z-extent)")
    if not np.isclose(side["coaxial_aperture_perp_mm"], 74.0):
        failures.append(f"SEED: side LED perp aperture {side['coaxial_aperture_perp_mm']:.1f} != 74 (y-extent)")
    if side["coaxial_fold_angle_deg"] != 45.0:
        failures.append("SEED: a decentred (folded) module should default to 45 deg")

    # SIDE-mounted on +y face: thin along y, 74 along x, 55 along z. Fold plane y-z.
    side_y = seed(
        _StubModuleEditor((-37.0, 37.0, 88.0, 90.0, 175.0, 230.0)),
        aperture_fold_fallback=1.0, aperture_perp_fallback=1.0,
    )
    if side_y["coaxial_fold_axis"] != "y" or not np.isclose(side_y["coaxial_aperture_perp_mm"], 74.0):
        failures.append("SEED: +y side LED fold axis / perp aperture wrong")

    # ON-AXIS LED (facing -z): thin along z, centred -> NOT folded -> fold_angle 0.
    on_axis = seed(
        _StubModuleEditor((-27.5, 27.5, -37.0, 37.0, 185.0, 187.0)),
        aperture_fold_fallback=55.0, aperture_perp_fallback=74.0,
    )
    if on_axis["coaxial_fold_angle_deg"] != 0.0:
        failures.append("SEED: an on-axis (centred) module must not be foreshortened (fold_angle 0)")

    # NO module -> fallback dims, still a descriptor (attach wiring proven separately).
    none_mod = seed(_StubModuleEditor(None), aperture_fold_fallback=12.0, aperture_perp_fallback=8.0)
    if not (none_mod["coaxial_aperture_fold_mm"] == 12.0 and none_mod["coaxial_aperture_perp_mm"] == 8.0):
        failures.append("SEED: no-module fallback did not use the supplied aperture dims")

    notes.append(
        "descriptor seed: side LED -> fold axis from decentre, fold aperture = along-axis (z) face dim, "
        "perp = cross-fold face dim; on-axis module -> fold_angle 0"
    )


# --------------------------------------------------------------------------------------------------
# 5. dispatcher + overlay wiring (render-only)
# --------------------------------------------------------------------------------------------------
def _check_wiring(failures: list[str]) -> None:
    from KrakenOS.UI.services.three_d_scene_tools import ThreeDSceneToolsMixin

    for name in ("_live_coaxial_illuminator_descriptor", "_coaxial_illuminator_overlay_spec"):
        if not hasattr(ThreeDSceneToolsMixin, name):
            failures.append(f"WIRING: {name} is missing")

    coupled = inspect.getsource(ThreeDSceneToolsMixin._compute_coupled_object_illumination_overlay_spec)
    if "_live_coaxial_illuminator_descriptor" not in coupled or "_coaxial_illuminator_overlay_spec" not in coupled:
        failures.append("WIRING: coupled compute does not consult the coaxial descriptor branch")

    overlay = inspect.getsource(ThreeDSceneToolsMixin._coaxial_illuminator_overlay_spec)
    for needed in (
        "coaxial_illuminator_footprint_map",
        "project_footprint_onto_sensor",
        "_current_finite_paraxial_magnification",
        "_detector_target_half_extent",
    ):
        if needed not in overlay:
            failures.append(f"WIRING: _coaxial_illuminator_overlay_spec does not use {needed}")
    for forbidden in ("build_system(", "_trace_preview_rays(", "_build_scene_source_bundles("):
        if forbidden in overlay:
            failures.append(f"WIRING: overlay references {forbidden!r} -- it must stay render-only")

    # Add-time attach: the LED spec carries a coaxial descriptor.
    from KrakenOS.UI.services.source_modeling import SourceModelingMixin

    add_src = inspect.getsource(SourceModelingMixin.add_illumination_led_source)
    if "_coaxial_illuminator_descriptor_from_module" not in add_src:
        failures.append("WIRING: add_illumination_led_source does not attach the coaxial descriptor")


# --------------------------------------------------------------------------------------------------
# 6. Real vendor scene -- optional (attachment gitignored; runs on the user's machines)
# --------------------------------------------------------------------------------------------------
def _check_real_vendor_scene(failures: list[str], notes: list[str]) -> None:
    from pathlib import Path

    path = Path(_ATTACHMENT)
    if not path.exists():
        notes.append(f"SKIP real vendor scene: {_ATTACHMENT} absent (gitignored)")
        return
    try:
        import KrakenOS as Kos
        from KrakenOS.UI.layout_editor import _load_python_data
        from KrakenOS.UI.render_layout_snapshot import (
            _build_runtime_system,
            _rows_from_layout_info,
            _snapshot_editor,
        )
    except Exception as exc:  # noqa: BLE001
        notes.append(f"SKIP real vendor scene: import failed ({exc!r})")
        return

    def _load():
        info = _load_python_data(path)
        rows = _rows_from_layout_info(info)
        settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
        editor = _snapshot_editor(rows, settings)
        editor.current_layout_file = path
        editor._normalize_special_rows()
        return editor

    # (a) add_illumination_led_source attaches SOME coaxial descriptor on the real scene.
    try:
        editor = _load()
        editor.add_illumination_led_source(record_history=False)
        attached = editor._live_coaxial_illuminator_descriptor()
    except Exception as exc:  # noqa: BLE001
        failures.append(f"REAL: Add Illumination Source raised {exc!r}")
        return
    if attached is None:
        failures.append("REAL: Add Illumination Source did not attach a coaxial descriptor")

    # (b) an explicit 55x74 / 45deg / x descriptor -> the production overlay draws 2 fold-dark edges.
    #     Set on the spec directly so this does not depend on the gitignored LED STEP module.
    coaxial_led = {
        "source_id": "source:side-led", "name": "Side LED 55x74", "model": "Random rectangle source",
        "role": "illumination", "physical": True, "enabled": True,
        "source_x": 28.6, "source_y": 0.0, "source_z": 229.646,
        "source_l": -1.0, "source_m": 0.0, "source_n": 0.0,
        "radius_x": 37.0, "radius_y": 27.5, "radius": 37.0,
        "cone_deg": 30.0, "ray_count": 400, "power": 1.0, "wavelength": 0.55, "seed": 7,
        "coaxial_illuminator": True, "coaxial_aperture_fold_mm": 55.0, "coaxial_aperture_perp_mm": 74.0,
        "coaxial_fold_angle_deg": 45.0, "coaxial_fold_axis": "x",
    }
    try:
        editor = _load()
        editor.layout_scene_source_specs = [dict(coaxial_led)]
        system = _build_runtime_system(path, editor.rows)
        wavelength = editor._current_wavelength()
        rays = Kos.raykeeper(system)
        max_radius = max((max(r.diameter / 2.0, 0.5) for r in editor.rows), default=1.0)
        editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
        bundle = editor._build_scene_bundle(system, rays, max_radius)
        editor.last_system, editor.last_rays, editor._last_scene_bundle = system, rays, bundle
        editor._last_preview_trace_signature = editor._preview_trace_signature()
        mag = abs(float(editor._current_finite_paraxial_magnification()))
        spec = editor.source_illumination_overlay_spec(system, bundle)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"REAL: driving the vendor overlay raised {exc!r}")
        return

    if not spec:
        failures.append("REAL: coaxial overlay is None -- the effective-illumination footprint did not fire")
        return
    relative = np.asarray(spec["relative"], dtype=float)
    nx, ny = spec["dims"]
    grid = relative.reshape(ny, nx)
    cx, cy = nx // 2, ny // 2
    centre = grid[cy, cx] or 1.0
    fold_edge = 0.5 * (float(grid[cy, 0]) + float(grid[cy, -1])) / centre
    perp_edge = 0.5 * (float(grid[0, cx]) + float(grid[-1, cx])) / centre
    if not (fold_edge < 0.85):
        failures.append(f"REAL: fold edges not dark on the sensor (edge {fold_edge:.3f})")
    if not (perp_edge >= 0.85):
        failures.append(f"REAL: perp edges not uniform on the sensor (edge {perp_edge:.3f})")

    notes.append(
        f"real vendor scene: |m|={mag:.3f}, add-LED attaches a coaxial descriptor, explicit 55x74/45deg "
        f"overlay -> fold edge {fold_edge:.3f} (dark) / perp {perp_edge:.3f} (uniform)"
    )


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_soft_edge(failures)
    _check_footprint_map(failures, notes)
    _check_descriptor_reader(failures)
    _check_descriptor_seed(failures, notes)
    _check_wiring(failures)
    _check_real_vendor_scene(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
    os.environ.setdefault("MPLBACKEND", "Agg")
    passed, messages = run_checks()
    for message in messages:
        print(("OK   " if passed else "NOTE ") + message)
    print(f"\n=== validate_open3d_effective_illumination_area: {'PASS' if passed else 'FAIL'} ===")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
