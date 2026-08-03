"""Display-free guard for coupled coaxial-LED imaging launches.

The physical side LED is additive: KrakenOS keeps the primary imaging trace
object-driven, but limits finite Object-plane field origins to the folded
illumination footprint.  For the MV-150 fixture that footprint is
``55*cos(45) x min(74, 39) = 38.890873 x 39 mm``.

This guard covers the pure coupling predicate, the real launch-bound sampler,
the Lambertian direction law shared by live and saved traces, and the source
frame of a 55 x 74 mm rectangle aimed along world -X.  When the gitignored
``attachment/machine_vision_150mm_test.py`` is present, it also checks the
authored LED and the Uncoated/Transmit entry face without opening a renderer.

Run::

    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_coaxial_imaging_launch

Exit status is 0 on pass (including an absent optional attachment), else 1.
"""

from __future__ import annotations

import ast
import contextlib
import io
import os
from pathlib import Path

import numpy as np

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MPLBACKEND", "Agg")


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ATTACHMENT = _PROJECT_ROOT / "attachment" / "machine_vision_150mm_test.py"
_FOLD_HALF = 0.5 * 55.0 * float(np.cos(np.deg2rad(45.0)))
_FOV_HALF = 19.5


def _coaxial_descriptor_spec() -> dict[str, object]:
    return {
        "source_id": "source:coaxial-side-led",
        "model": "Random rectangle source",
        "role": "illumination",
        "physical": True,
        "enabled": True,
        "coaxial_illuminator": True,
        "coaxial_aperture_fold_mm": 55.0,
        "coaxial_aperture_perp_mm": 74.0,
        "coaxial_fold_angle_deg": 45.0,
        "coaxial_fold_axis": "x",
        "couple_to_imaging_launch": True,
    }


def _check_coupling_predicate(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI.scene_geometry import SceneSource3D
    from KrakenOS.UI.scene_source_analysis import (
        scene_source_spec_couples_to_imaging_launch as is_coupled,
    )

    base = _coaxial_descriptor_spec()
    for alias in (
        "couple_to_imaging_launch",
        "couple_to_imaging",
        "imaging_launch_coupled",
    ):
        spec = dict(base)
        for key in (
            "couple_to_imaging_launch",
            "couple_to_imaging",
            "imaging_launch_coupled",
        ):
            spec.pop(key, None)
        spec[alias] = "true"
        if not is_coupled(spec):
            failures.append(f"PREDICATE: valid descriptor using alias {alias!r} was not coupled")

    source = SceneSource3D(settings=dict(base))
    if not is_coupled(source):
        failures.append("PREDICATE: SceneSource3D.settings form lost the coupling descriptor")

    no_descriptor = {"couple_to_imaging_launch": True}
    if is_coupled(no_descriptor):
        failures.append("PREDICATE: a bare coupling flag fabricated geometry without a descriptor")
    invalid_descriptor = dict(base)
    invalid_descriptor["coaxial_aperture_fold_mm"] = 0.0
    if is_coupled(invalid_descriptor):
        failures.append("PREDICATE: a zero-width coaxial descriptor was accepted")
    descriptor_only = dict(base)
    descriptor_only.pop("couple_to_imaging_launch")
    if is_coupled(descriptor_only):
        failures.append("PREDICATE: a descriptor without an opt-in coupling flag was coupled")
    explicitly_off = dict(base)
    explicitly_off["couple_to_imaging_launch"] = "false"
    if is_coupled(explicitly_off):
        failures.append("PREDICATE: string false did not disable launch coupling")

    if not [item for item in failures if item.startswith("PREDICATE:")]:
        notes.append("predicate: aliases + SceneSource3D work; descriptor and explicit opt-in are both required")


class _Row:
    def __init__(self, diameter: float) -> None:
        self.diameter = float(diameter)


class _LaunchEditor:
    """Small editor double bound to the production finite-field sampling methods."""

    def __init__(self) -> None:
        from KrakenOS.UI.scene_source_analysis import normalize_scene_source_specs
        from KrakenOS.UI.services.trace_preview_sampling import TracePreviewSamplingMixin as Sampling

        self.layout_scene_source_specs = [_coaxial_descriptor_spec()]
        # The real attachment's Object display disc.  Coupled launch bounds intentionally do not
        # clip to this smaller disc; the registered camera images a 39 x 39 mm rectangle.
        self.rows = [_Row(32.5834804774)]
        self._normalize = normalize_scene_source_specs
        self._sampling = Sampling

    def _normalize_scene_source_specs(self, value):
        return self._normalize(value)

    def _current_object_mode(self) -> str:
        return "Finite"

    def _current_field_height(self) -> float:
        # Radial corner of a 39 x 39 mm authored field rectangle.
        return _FOV_HALF * float(np.sqrt(2.0))

    def _current_field_count(self) -> int:
        return 3

    def _current_camera_sensor_active_mm(self) -> tuple[float, float]:
        return 23.04, 23.04

    def _current_finite_paraxial_magnification(self) -> float:
        return 23.04 / 39.0

    def _coupled_imaging_launch_descriptor(self):
        return self._sampling._coupled_imaging_launch_descriptor(self)

    def _coupled_imaging_launch_half_extents(self):
        return self._sampling._coupled_imaging_launch_half_extents(self)

    def _camera_fov_object_half_extents(self):
        return self._sampling._camera_fov_object_half_extents(self)

    def _camera_fov_inscribed_object_radius(self):
        return self._sampling._camera_fov_inscribed_object_radius(self)

    def _launch_field_radial_max(self):
        return self._sampling._launch_field_radial_max(self)

    def _sample_field_values(self, maximum: float):
        return self._sampling._sample_field_values(self, maximum)

    def _sample_field_grid_pairs(self, maximum: float):
        return self._sampling._sample_field_grid_pairs(self, maximum)

    def _sample_imaging_field_grid_pairs(self):
        return self._sampling._sample_imaging_field_grid_pairs(self)

    def _imaging_fov_half_extents(self):
        # bugs/0523: the grid resolves its rectangle through this helper now; the fake
        # delegates like every other sampler shim (the qe_object_locked fixture lesson).
        return self._sampling._imaging_fov_half_extents(self)

    def _current_finite_paraxial_magnification(self):
        return None

    def _current_camera_sensor_active_mm(self):
        return None


def _check_launch_geometry(failures: list[str], notes: list[str]) -> None:
    editor = _LaunchEditor()
    half = editor._coupled_imaging_launch_half_extents()
    expected_half = np.asarray((_FOLD_HALF, _FOV_HALF), dtype=float)
    if half is None or not np.allclose(np.asarray(half), expected_half, atol=1e-9):
        failures.append(f"LAUNCH: half extents are {half!r}, expected {tuple(expected_half)!r}")
        return

    pairs = np.asarray(editor._sample_imaging_field_grid_pairs(), dtype=float)
    if pairs.shape != (9, 2):
        failures.append(f"LAUNCH: field_count=3 produced grid shape {pairs.shape}, expected (9, 2)")
    else:
        mins = np.min(pairs, axis=0)
        maxs = np.max(pairs, axis=0)
        full = maxs - mins
        expected_full = np.asarray((55.0 * np.cos(np.deg2rad(45.0)), 39.0))
        if not np.allclose(mins, -expected_half, atol=1e-9):
            failures.append(f"LAUNCH: Object-plane grid minima {mins.tolist()} != {-expected_half}")
        if not np.allclose(maxs, expected_half, atol=1e-9):
            failures.append(f"LAUNCH: Object-plane grid maxima {maxs.tolist()} != {expected_half}")
        if not np.allclose(full, expected_full, atol=1e-9):
            failures.append(f"LAUNCH: Object-plane grid is {full.tolist()} mm, expected {expected_full.tolist()} mm")
        unique_x = np.unique(np.round(pairs[:, 0], 12))
        unique_y = np.unique(np.round(pairs[:, 1], 12))
        if unique_x.size != 3 or unique_y.size != 3:
            failures.append("LAUNCH: the coupled field is not a full 3 x 3 Cartesian grid")

    editor.layout_scene_source_specs[0]["enabled"] = False
    if editor._coupled_imaging_launch_half_extents() is not None:
        failures.append("LAUNCH: disabling the LED did not remove the coupled launch bound")
    disabled_pairs = np.asarray(editor._sample_imaging_field_grid_pairs(), dtype=float)
    legacy_pairs = np.asarray(
        editor._sample_field_grid_pairs(editor._launch_field_radial_max()), dtype=float
    )
    if disabled_pairs.shape != legacy_pairs.shape or not np.allclose(disabled_pairs, legacy_pairs):
        failures.append("LAUNCH: disabled LED did not fall back exactly to legacy finite-field sampling")
    if disabled_pairs.size and np.isclose(np.max(np.abs(disabled_pairs[:, 0])), _FOLD_HALF, atol=1e-6):
        failures.append("LAUNCH: disabled LED retained the 55*cos45 fold-axis extent")

    if not [item for item in failures if item.startswith("LAUNCH:")]:
        notes.append(
            f"launch: enabled grid = {2.0 * _FOLD_HALF:.6f} x 39.000000 mm (3 x 3); disabled -> legacy"
        )


def _check_angular_laws(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI.source_trace_helpers import random_cone_directions

    count = 160_000
    cosine = random_cone_directions(
        count,
        90.0,
        np.random.default_rng(17),
        angular_weight="Cosine-weighted",
    )
    uniform = random_cone_directions(
        count,
        90.0,
        np.random.default_rng(17),
        angular_weight="Uniform solid angle",
    )
    cosine_dirs = np.column_stack(cosine)
    uniform_dirs = np.column_stack(uniform)
    cosine_mean = float(np.mean(cosine_dirs[:, 2]))
    uniform_mean = float(np.mean(uniform_dirs[:, 2]))
    if not np.isclose(cosine_mean, 2.0 / 3.0, atol=0.006):
        failures.append(f"LAMBERTIAN: cosine-weighted hemisphere mean cos={cosine_mean:.5f}, expected 2/3")
    if not np.isclose(uniform_mean, 0.5, atol=0.006):
        failures.append(f"LAMBERTIAN: uniform-solid-angle hemisphere mean cos={uniform_mean:.5f}, expected 1/2")
    if cosine_mean <= uniform_mean + 0.12:
        failures.append("LAMBERTIAN: cosine-weighted and uniform samplers are not materially distinct")
    for label, directions in (("cosine", cosine_dirs), ("uniform", uniform_dirs)):
        norms = np.linalg.norm(directions, axis=1)
        if not np.allclose(norms, 1.0, atol=1e-12):
            failures.append(f"LAMBERTIAN: {label} sampler returned non-unit directions")
        if float(np.min(directions[:, 2])) < -1e-12:
            failures.append(f"LAMBERTIAN: {label} hemisphere emitted behind the source plane")

    if not [item for item in failures if item.startswith("LAMBERTIAN:")]:
        notes.append(
            f"Lambertian: full-hemisphere mean cos={cosine_mean:.4f} (~2/3), uniform={uniform_mean:.4f} (~1/2)"
        )


class _LiveBundleBuilder:
    """Bind only the production methods needed by ``_build_scene_source_bundle``."""

    from KrakenOS.UI.services.source_modeling import SourceModelingMixin as _SourceModeling

    _build_scene_source_bundle = _SourceModeling._build_scene_source_bundle
    _source_spec_float = staticmethod(_SourceModeling._source_spec_float)
    _random_cone_directions = staticmethod(_SourceModeling._random_cone_directions)
    _orient_source_points_and_dirs_for_source = staticmethod(
        _SourceModeling._orient_source_points_and_dirs_for_source
    )


def _check_live_saved_rectangle(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI.scene_source_analysis import scene_source_from_spec
    from KrakenOS.UI.source_trace_helpers import build_scene_source_bundle

    spec = {
        "source_id": "source:bundle-law",
        "name": "55 x 74 mm Lambertian rectangle",
        "model": "Random rectangle source",
        "role": "illumination",
        "physical": True,
        "enabled": True,
        "source_x": 28.6,
        "source_y": 0.0,
        "source_z": 229.64618504048343,
        "source_l": -1.0,
        "source_m": 0.0,
        "source_n": 0.0,
        # For -X, source-frame X -> world Y and source-frame Y -> world Z.
        "radius_x": 37.0,
        "radius_y": 27.5,
        "radius": 37.0,
        "cone_deg": 90.0,
        "angular_weight": "Cosine-weighted",
        "ray_count": 12_000,
        "wavelength": 0.546,
        "seed": 7,
    }
    source = scene_source_from_spec(spec, 0, wavelength=0.546)
    live = _LiveBundleBuilder()._build_scene_source_bundle(source)
    saved = build_scene_source_bundle(source)
    if live is None or saved is None:
        failures.append("BUNDLE: live or saved rectangle builder returned None")
        return
    if len(live) != 6 or len(saved) != 6:
        failures.append("BUNDLE: source builders did not return six coordinate/direction arrays")
        return
    if not all(np.array_equal(np.asarray(a), np.asarray(b)) for a, b in zip(live, saved)):
        failures.append("BUNDLE: live and saved seeded rectangle bundles are not byte-identical")

    points = np.column_stack(live[:3])
    directions = np.column_stack(live[3:])
    if points.shape != (12_000, 3):
        failures.append(f"BUNDLE: rectangle produced point array shape {points.shape}, expected (12000, 3)")
    if not np.allclose(points[:, 0], 28.6, atol=1e-12):
        failures.append("BUNDLE: -X rectangle is not planar at world X=28.6 mm")
    y_min, y_max = float(np.min(points[:, 1])), float(np.max(points[:, 1]))
    z_offset = points[:, 2] - float(spec["source_z"])
    z_min, z_max = float(np.min(z_offset)), float(np.max(z_offset))
    if y_min < -37.0 - 1e-12 or y_max > 37.0 + 1e-12 or (y_max - y_min) < 73.5:
        failures.append(f"BUNDLE: radius_x=37 did not span world Y as 74 mm ({y_min:.3f}..{y_max:.3f})")
    if z_min < -27.5 - 1e-12 or z_max > 27.5 + 1e-12 or (z_max - z_min) < 54.6:
        failures.append(f"BUNDLE: radius_y=27.5 did not span world Z as 55 mm ({z_min:.3f}..{z_max:.3f})")
    norms = np.linalg.norm(directions, axis=1)
    mean_axis_cos = float(np.mean(-directions[:, 0]))
    if not np.allclose(norms, 1.0, atol=1e-12):
        failures.append("BUNDLE: oriented Lambertian directions are not unit vectors")
    if float(np.min(-directions[:, 0])) < -1e-12:
        failures.append("BUNDLE: a full-hemisphere ray emitted behind the -X rectangle")
    if not np.isclose(mean_axis_cos, 2.0 / 3.0, atol=0.012):
        failures.append(f"BUNDLE: oriented mean cos={mean_axis_cos:.4f}, expected Lambertian ~2/3")

    if not [item for item in failures if item.startswith("BUNDLE:")]:
        notes.append(
            f"bundle: live == saved; -X frame spans Y={y_max-y_min:.3f} mm, Z={z_max-z_min:.3f} mm"
        )


def _literal_optical_faces(path: Path) -> list[dict[str, object]]:
    """Read the human-readable ``sN.OpticalSolidFaces`` assignments without executing the layout."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    records: list[dict[str, object]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Attribute) and target.attr == "OpticalSolidFaces" for target in node.targets):
            continue
        try:
            metadata = ast.literal_eval(node.value)
        except Exception:
            continue
        if not isinstance(metadata, dict):
            continue
        records.extend(face for face in metadata.get("faces", []) if isinstance(face, dict))
    return records


def _check_optional_attachment(failures: list[str], notes: list[str]) -> None:
    if not _ATTACHMENT.exists():
        notes.append("attachment: SKIP machine_vision_150mm_test.py absent (gitignored fixture)")
        return

    try:
        from KrakenOS.UI.layout_library import load_python_data
        from KrakenOS.UI.render_layout_snapshot import (
            _build_runtime_system,
            _rows_from_layout_info,
            _snapshot_editor,
        )

        # KrakenOS catalog initialization is not relevant to this display-free metadata guard.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            info = load_python_data(_ATTACHMENT)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"ATTACHMENT: could not load {_ATTACHMENT.name}: {exc!r}")
        return

    settings = info.get("settings", {}) if isinstance(info, dict) else {}
    specs = settings.get("scene_sources", []) if isinstance(settings, dict) else []
    coupled = [
        spec
        for spec in specs
        if isinstance(spec, dict) and bool(spec.get("couple_to_imaging_launch", False))
    ]
    if len(coupled) != 1:
        failures.append(f"ATTACHMENT: expected one coupled LED spec, found {len(coupled)}")
    else:
        from KrakenOS.UI.scene_source_analysis import (
            coaxial_illuminator_descriptor,
            scene_source_spec_couples_to_imaging_launch,
        )

        source = coupled[0]
        expected_text = {
            "model": "Random rectangle source",
            "role": "illumination",
            "angular_weight": "Cosine-weighted",
            "coaxial_fold_axis": "x",
        }
        for key, expected in expected_text.items():
            if str(source.get(key, "")) != expected:
                failures.append(f"ATTACHMENT: LED {key}={source.get(key)!r}, expected {expected!r}")
        expected_numbers = {
            "source_x": 28.6,
            "source_y": 0.0,
            "source_z": 229.64618504048343,
            "source_l": -1.0,
            "source_m": 0.0,
            "source_n": 0.0,
            "radius_x": 37.0,
            "radius_y": 27.5,
            "cone_deg": 90.0,
            "coaxial_aperture_fold_mm": 55.0,
            "coaxial_aperture_perp_mm": 74.0,
            "coaxial_fold_angle_deg": 45.0,
        }
        for key, expected in expected_numbers.items():
            try:
                got = float(source.get(key))
            except (TypeError, ValueError):
                got = float("nan")
            if not np.isclose(got, expected, atol=1e-9):
                failures.append(f"ATTACHMENT: LED {key}={source.get(key)!r}, expected {expected}")
        if not (bool(source.get("enabled", False)) and bool(source.get("physical", False))):
            failures.append("ATTACHMENT: coupled LED is not enabled + physical")
        if not scene_source_spec_couples_to_imaging_launch(source):
            failures.append("ATTACHMENT: authored LED does not satisfy the production coupling predicate")
        descriptor = coaxial_illuminator_descriptor(source)
        if descriptor is None:
            failures.append("ATTACHMENT: authored LED has no valid coaxial descriptor")

    surfaces = info.get("surfaces", []) if isinstance(info, dict) else []
    runtime_faces: list[dict[str, object]] = []
    for surface in surfaces:
        if not isinstance(surface, dict):
            continue
        advanced = surface.get("advanced", {})
        metadata = advanced.get("OpticalSolidFaces", {}) if isinstance(advanced, dict) else {}
        faces = metadata.get("faces", []) if isinstance(metadata, dict) else []
        runtime_faces.extend(face for face in faces if isinstance(face, dict))
    runtime_f002 = [face for face in runtime_faces if face.get("face_id") == "S001/F002"]
    literal_f002 = [
        face for face in _literal_optical_faces(_ATTACHMENT) if face.get("face_id") == "S001/F002"
    ]
    for label, records in (("runtime serialized", runtime_f002), ("readable assignment", literal_f002)):
        if not records:
            failures.append(f"ATTACHMENT: {label} has no S001/F002 record")
            continue
        for face in records:
            if face.get("function") != "Transmit/Port" or face.get("role") != "Output":
                failures.append(
                    f"ATTACHMENT: {label} S001/F002 remains {face.get('function')!r}/{face.get('role')!r}, "
                    "expected Transmit/Port + Output (UI: Uncoated)"
                )
            if face.get("port_role") != "Interaction Surface":
                failures.append(
                    f"ATTACHMENT: {label} S001/F002 port_role={face.get('port_role')!r}, "
                    "expected Interaction Surface"
                )

    # Exercise the target's additive trace contract with a reduced, deterministic
    # LED sample. The primary bundle builder must stay empty (so imaging remains
    # Object-driven), while the isolated coupled builder must launch real LED rays
    # that enter the now-Uncoated wall and fold downward toward/crossing z=0.
    try:
        editor = _snapshot_editor(_rows_from_layout_info(info), settings)
        editor.current_layout_file = _ATTACHMENT
        editor._normalize_special_rows()
        editor.layout_scene_source_specs[0]["ray_count"] = 400
        wavelength = float(editor._current_wavelength())
        primary_bundles, _ = editor._build_scene_source_bundles(wavelength)
        coupled_bundles, coupled_sources = editor._build_coupled_illumination_source_bundles(
            wavelength
        )
        collected = editor._collect_scene_sources(wavelength=wavelength)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            system = _build_runtime_system(_ATTACHMENT, editor.rows)
            ray_records = editor._isolated_scene_source_records(system, wavelength)
    except Exception as exc:  # noqa: BLE001
        failures.append(f"ATTACHMENT: additive physical trace raised {exc!r}")
    else:
        if primary_bundles:
            failures.append("ATTACHMENT: coupled LED entered the primary imaging bundle builder")
        if len(coupled_bundles) != 1 or len(coupled_sources) != 1:
            failures.append(
                "ATTACHMENT: isolated coupled builder did not return exactly one physical LED bundle"
            )
        if not collected or bool(collected[0].physical):
            failures.append("ATTACHMENT: Object-driven imaging reference is not the primary source record")
        polylines = [
            np.asarray(record.get("traced_polyline_world", []), dtype=float)
            for record in ray_records
        ]
        polylines = [points for points in polylines if points.ndim == 2 and len(points) >= 2]
        downward = sum(
            bool(np.any(np.diff(points, axis=0)[:, 2] < -1e-6)) for points in polylines
        )
        crosses_object = sum(bool(np.min(points[:, 2]) <= 1e-3) for points in polylines)
        if not ray_records or not polylines:
            failures.append("ATTACHMENT: isolated LED trace produced no ray records/polylines")
        if downward <= 0:
            failures.append("ATTACHMENT: no LED branch reflected downward from the diagonal splitter")
        if crosses_object <= 0:
            failures.append("ATTACHMENT: no reflected LED branch reached/crossed the Object plane z=0")
        if downward > 0 and crosses_object > 0:
            notes.append(
                f"attachment trace: {downward} branches fold toward -Z; {crosses_object} reach/cross Object z=0"
            )

    if not [item for item in failures if item.startswith("ATTACHMENT:")]:
        notes.append("attachment: coupled 55 x 74 Lambertian LED + Uncoated S001/F002 metadata are live")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_coupling_predicate(failures, notes)
    _check_launch_geometry(failures, notes)
    _check_angular_laws(failures, notes)
    _check_live_saved_rectangle(failures, notes)
    _check_optional_attachment(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(("OK   " if passed else "NOTE ") + message)
    print(f"\n=== validate_open3d_coaxial_imaging_launch: {'PASS' if passed else 'FAIL'} ===")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
