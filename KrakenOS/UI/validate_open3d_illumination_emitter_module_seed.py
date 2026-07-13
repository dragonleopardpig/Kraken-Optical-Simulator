"""bugs/0290 -- "Add Illumination Source" seeds the emitter from the physical LED module when present.

Closes flag_20260713_073358_441 ("still a small patch of illumination").  ``add_illumination_led_source``
used to seat the emitter at the imaging Source panel's origin/direction/radius -- a 10x10 mm square on the
object plane aimed +z, AWAY from the object -- so it was decoupled from the big imported LED module the
user placed.  The detector overlay then honestly imaged that tiny default: a ~5.9 mm central patch on the
39x39 mm FOV.

The fix (display follows physics): when a physical LED module is imported (``imported_led_step_path``),
seed the emitter FROM it -- origin at the module's OBJECT-FACING face centre, half-extents from its
transverse world bounds, aim toward the object-plane point on the optical axis -- so the emitter coincides
with the visible LED.  With no module it falls back to today's panel-derived values, so the pure-imaging
path (and the bugs/0288 guard) is unchanged.  All bounds are read from the real transformed CAD mesh --
no hardcoded module size/position.

These checks are display-free (no VTK, no pyvista window).  The real-vendor-scene check drives the actual
dispatcher on ``attachment/machine_vision_150mm_test.py`` with a synthetic module (the gitignored STEP is
not required) and SKIPs when the attachment is absent.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_illumination_emitter_module_seed

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect
import os
import types

import numpy as np

_ATTACHMENT = "attachment/machine_vision_150mm_test.py"

# The real OPT-CO90 placement (memory: 55x78 mm LED, moved +22.9 x, object-facing min-z face at z~187).
_MODULE_BOUNDS = (1.1, 56.1, -39.0, 39.0, 187.0, 265.0)


# --------------------------------------------------------------------------------------------------
# 1. illumination_emitter_seed_from_module_bounds -- the pure geometry
# --------------------------------------------------------------------------------------------------
def _check_seed_math(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI.services.source_modeling import illumination_emitter_seed_from_module_bounds as seed

    # Centred module, object BELOW (plane z=0 < faces): emit from the min-z (object-facing) face,
    # straight down the axis toward the object, sized to the module.
    centred = seed((-27.5, 27.5, -20.0, 20.0, 187.0, 265.0), 0.0)
    if centred is None:
        failures.append("SEED: a valid centred module produced None")
        return
    (origin, direction, half_x, half_y) = centred
    if not np.allclose(origin, [0.0, 0.0, 187.0]):
        failures.append(f"SEED: centred origin {tuple(round(v,2) for v in origin)} != object-facing face centre (0,0,187)")
    if not np.allclose(direction, [0.0, 0.0, -1.0]):
        failures.append(f"SEED: centred aim {tuple(round(v,3) for v in direction)} != straight toward the object (-z)")
    if not (np.isclose(half_x, 27.5) and np.isclose(half_y, 20.0)):
        failures.append(f"SEED: half-extents ({half_x},{half_y}) != module transverse half-bounds (27.5,20.0)")
    if not np.isclose(np.linalg.norm(direction), 1.0):
        failures.append("SEED: direction is not a unit vector")

    # Decentred module (real OPT-CO90 is moved +22.9 x): origin follows the face centre, and the aim
    # tilts BACK toward the optical axis at the object plane (so the flood centres on the imaged FOV).
    dec = seed(_MODULE_BOUNDS, 0.0)
    (o, d, hx, hy) = dec
    if not np.allclose(o, [28.6, 0.0, 187.0], atol=1e-6):
        failures.append(f"SEED: decentred origin {tuple(round(v,2) for v in o)} != face centre (28.6,0,187)")
    if not (d[0] < 0.0 and d[2] < 0.0):
        failures.append(f"SEED: decentred aim {tuple(round(v,3) for v in d)} does not point back toward the object axis")
    if not (np.isclose(hx, 27.5) and np.isclose(hy, 39.0)):
        failures.append(f"SEED: decentred half-extents ({hx},{hy}) != (27.5,39.0)")
    # The aim endpoint is the axis point on the object plane: origin + t*d must reach x=y=0 at z=0.
    t = -o[2] / d[2]
    if not (np.isclose(o[0] + t * d[0], 0.0, atol=1e-6) and np.isclose(o[1] + t * d[1], 0.0, atol=1e-6)):
        failures.append("SEED: the decentred aim does not intersect the optical axis at the object plane")

    # Object ABOVE the module: the object-facing face flips to max-z and the aim flips to +z.  Proves the
    # face/aim are geometry-driven, not a hardcoded "min-z, -z".
    above = seed((-10.0, 10.0, -10.0, 10.0, 100.0, 150.0), 300.0)
    (oa, da, _, _) = above
    if not (np.isclose(oa[2], 150.0) and da[2] > 0.0):
        failures.append(f"SEED: with the object above, face/aim did not flip (origin_z={oa[2]}, dir_z={da[2]:.3f})")

    # A paper-thin transverse axis is floored so the emitter is never a zero-area line.
    thin = seed((5.0, 5.0, -20.0, 20.0, 187.0, 265.0), 0.0)
    if thin is None or thin[2] < 0.5:
        failures.append("SEED: a zero-width transverse axis was not floored to a finite half-extent")

    # Degenerate / non-finite / mis-shaped bounds fall back to None (caller keeps the panel default).
    if seed((0, 0, 0, 0, 0, 0), 0.0) is not None:
        failures.append("SEED: a zero-size module at the object plane must yield None (no launchable ray)")
    if seed((0.0, float("nan"), 0.0, 1.0, 0.0, 1.0), 0.0) is not None:
        failures.append("SEED: non-finite bounds must yield None")
    if seed((1, 2, 3), 0.0) is not None:
        failures.append("SEED: mis-shaped bounds (not 6 values) must yield None")

    notes.append(
        "seed math: object-facing face + aim toward the FOV axis, half-extents from bounds, "
        "geometry-driven face flip, degenerate->None"
    )


# --------------------------------------------------------------------------------------------------
# 2. _illumination_emitter_module_seed -- the instance wiring (no imports of the module STEP)
# --------------------------------------------------------------------------------------------------
class _StubEditor:
    """A minimal host for ``SourceModelingMixin._illumination_emitter_module_seed`` -- stubs only the
    four members that method touches, so the seed can be exercised without a real CAD mesh."""

    def __init__(self, *, path=None, mesh="unset", object_index=0, plane_z=0.0):
        from KrakenOS.UI.services.source_modeling import SourceModelingMixin

        self._seed = SourceModelingMixin._illumination_emitter_module_seed.__get__(self, _StubEditor)
        self.imported_led_step_path = path
        self._mesh = types.SimpleNamespace(bounds=_MODULE_BOUNDS) if mesh == "unset" else mesh
        self._object_index = object_index
        self._plane_z = plane_z
        self.plane_z_calls: list[int] = []

    def _transformed_imported_led_step_mesh(self):
        if isinstance(self._mesh, Exception):
            raise self._mesh
        return self._mesh

    def _source_object_coupling_object_index(self):
        return self._object_index

    def _object_surface_plane_z(self, index):
        self.plane_z_calls.append(index)
        return self._plane_z

    def seed(self):
        return self._seed()


def _check_instance_seed(failures: list[str], notes: list[str]) -> None:
    from KrakenOS.UI.services.source_modeling import illumination_emitter_seed_from_module_bounds as pure

    # No module -> None (this is the branch that keeps the pure-imaging path / bugs/0288 unchanged).
    if _StubEditor(path=None).seed() is not None:
        failures.append("INSTANCE: no imported module must yield None (panel fallback)")

    # Module present -> the instance seed equals the pure function on the mesh bounds + object-plane z.
    ed = _StubEditor(path="m.STEP", plane_z=0.0)
    got = ed.seed()
    want = pure(_MODULE_BOUNDS, 0.0)
    if got is None or not (
        np.allclose(got[0], want[0]) and np.allclose(got[1], want[1])
        and np.isclose(got[2], want[2]) and np.isclose(got[3], want[3])
    ):
        failures.append("INSTANCE: module seed did not match the pure function on the mesh bounds")
    if 0 not in ed.plane_z_calls:
        failures.append("INSTANCE: the object-plane z was not read from _object_surface_plane_z")

    # The object-plane z is genuinely consumed (not a hardcoded 0): a shifted plane tilts the aim.
    flat = _StubEditor(path="m.STEP", plane_z=0.0).seed()
    tilted = _StubEditor(path="m.STEP", plane_z=120.0).seed()
    if flat is not None and tilted is not None and np.allclose(flat[1], tilted[1]):
        failures.append("INSTANCE: moving the object plane did not change the aim -- object_plane_z is ignored")

    # Missing / broken geometry falls back to None rather than raising.
    if _StubEditor(path="m.STEP", mesh=None).seed() is not None:
        failures.append("INSTANCE: a None mesh must yield None")
    if _StubEditor(path="m.STEP", mesh=types.SimpleNamespace(bounds=None)).seed() is not None:
        failures.append("INSTANCE: a mesh without bounds must yield None")
    if _StubEditor(path="m.STEP", mesh=RuntimeError("mesh boom")).seed() is not None:
        failures.append("INSTANCE: a raising mesh accessor must be swallowed to None")

    notes.append("instance seed: gated on imported_led_step_path, reads the transformed mesh bounds + object-plane z, fails soft")


# --------------------------------------------------------------------------------------------------
# 3. add_illumination_led_source -- the rewire (source text, no scene needed)
# --------------------------------------------------------------------------------------------------
def _check_add_source_wiring(failures: list[str]) -> None:
    from KrakenOS.UI.services.source_modeling import SourceModelingMixin

    if not hasattr(SourceModelingMixin, "_illumination_emitter_module_seed"):
        failures.append("WIRING: _illumination_emitter_module_seed is missing")

    src = inspect.getsource(SourceModelingMixin.add_illumination_led_source)
    if "_illumination_emitter_module_seed" not in src:
        failures.append("WIRING: add_illumination_led_source no longer consults the module seed")
    if "module_seed is not None" not in src:
        failures.append("WIRING: add_illumination_led_source lost its module-present branch")
    for panel in ("_current_source_origin", "_current_source_direction", "_current_source_radius"):
        if panel not in src:
            failures.append(f"WIRING: the no-module fallback dropped {panel} (panel default gone)")
    for axis in ('"radius_x"', '"radius_y"'):
        if axis not in src:
            failures.append(f"WIRING: the emitter spec is no longer per-axis (missing {axis})")


# --------------------------------------------------------------------------------------------------
# 4. Real vendor scene -- optional (attachment gitignored; runs on the user's machines)
# --------------------------------------------------------------------------------------------------
def _load_vendor_editor(path):
    from KrakenOS.UI.layout_editor import _load_python_data
    from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor

    info = _load_python_data(path)
    rows = _rows_from_layout_info(info)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = path
    editor._normalize_special_rows()
    return editor


def _overlay_lit_fraction(editor):
    import KrakenOS as Kos
    from KrakenOS.UI.render_layout_snapshot import _build_runtime_system

    path = editor.current_layout_file
    system = _build_runtime_system(path, editor.rows)
    wavelength = editor._current_wavelength()
    rays = Kos.raykeeper(system)
    max_radius = max((max(r.diameter / 2.0, 0.5) for r in editor.rows), default=1.0)
    editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
    bundle = editor._build_scene_bundle(system, rays, max_radius)
    editor.last_system, editor.last_rays, editor._last_scene_bundle = system, rays, bundle
    editor._last_preview_trace_signature = editor._preview_trace_signature()
    spec = editor.source_illumination_overlay_spec(system, bundle)
    if not spec:
        return None, spec
    rel = np.asarray(spec["relative"], dtype=float)
    return float(np.count_nonzero(rel >= 0.5)) / float(rel.size), spec


def _check_real_vendor_scene(failures: list[str], notes: list[str]) -> None:
    from pathlib import Path

    path = Path(_ATTACHMENT)
    if not path.exists():
        notes.append(f"SKIP real vendor scene: {_ATTACHMENT} absent (gitignored -- see bugs/diag_0290c_module_seed)")
        return
    try:
        # (A) No module: the panel default -- the tiny 10x10 mm patch that triggered the flag.
        bare = _load_vendor_editor(path)
        bare.add_illumination_led_source(record_history=False)
        lit_bare, spec_bare = _overlay_lit_fraction(bare)

        # (B) With a synthetic OPT-CO90 module injected (no gitignored STEP needed): the fix seeds the
        # emitter FROM it, so the same dispatcher now fills the FOV.
        mod = _load_vendor_editor(path)
        mod.imported_led_step_path = "synthetic-OPT-CO90-X.STEP"
        mod._transformed_imported_led_step_mesh = lambda: types.SimpleNamespace(bounds=_MODULE_BOUNDS)
        seed = mod._illumination_emitter_module_seed()
        mod.add_illumination_led_source(record_history=False)
        specs = mod._normalize_scene_source_specs(getattr(mod, "layout_scene_source_specs", []) or [])
        lit_mod, spec_mod = _overlay_lit_fraction(mod)
    except Exception as exc:
        failures.append(f"REAL: driving the vendor scene raised {exc!r}")
        return

    if seed is None:
        failures.append("REAL: the injected module produced no emitter seed")
        return

    # The appended source spec is module-seeded, NOT the panel default (0,0,0)/+z/5x5.
    added = next((s for s in specs if str(s.get("source_id", "")).startswith("source:led")), None)
    if added is None:
        failures.append("REAL: no illumination LED spec was appended")
    else:
        if float(added["source_z"]) < 100.0:
            failures.append(f"REAL: emitter z={added['source_z']:.1f} still on the object plane (module seed ignored)")
        if not (float(added["radius_x"]) > 15.0 and float(added["radius_y"]) > 15.0):
            failures.append(
                f"REAL: emitter is still tiny (rx={added['radius_x']:.1f} ry={added['radius_y']:.1f}) -- "
                "not sized to the module"
            )
        if float(added["source_n"]) >= 0.0:
            failures.append(f"REAL: emitter aims source_n={added['source_n']:.3f} -- not toward the object")

    # The overlay must go from the tiny patch to a filled FOV: with the module the lit fraction jumps.
    if lit_mod is None:
        failures.append("REAL: the module-seeded overlay is None -- the emitter lit nothing")
    elif not (lit_mod > 0.5):
        failures.append(f"REAL: the module-seeded FOV is only {lit_mod*100:.0f}% lit -- expected a filled FOV")
    if lit_bare is not None and lit_mod is not None and not (lit_mod > 3.0 * lit_bare):
        failures.append(
            f"REAL: module seed did not materially enlarge the patch (bare {lit_bare*100:.0f}% -> module {lit_mod*100:.0f}%)"
        )

    notes.append(
        f"real vendor scene: panel default lights {(_pct(lit_bare))} of the FOV (tiny patch); "
        f"module-seeded emitter at z={float(seed[0][2]):.0f}, {seed[2]:.0f}x{seed[3]:.0f} mm lights {(_pct(lit_mod))} (filled)"
    )


def _pct(value):
    return "n/a" if value is None else f"{value*100:.0f}%"


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_seed_math(failures, notes)
    _check_instance_seed(failures, notes)
    _check_add_source_wiring(failures)
    _check_real_vendor_scene(failures, notes)
    return (not failures), (failures + notes)


def main() -> int:
    os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
    os.environ.setdefault("MPLBACKEND", "Agg")
    passed, messages = run_checks()
    for message in messages:
        print(("OK   " if passed else "NOTE ") + message)
    print(f"\n=== validate_open3d_illumination_emitter_module_seed: {'PASS' if passed else 'FAIL'} ===")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
