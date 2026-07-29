"""bugs/0474 -- the ``from .Physics import *`` contract, guarded as an INVARIANT.

The Physics *package* (added by b727b7ac) sits where the legacy ``Physics.py``
module used to be. Three modules star-import it and then call the legacy optics
helpers unqualified, so the package must re-export everything the old module
did. When it did not, ``n_wave_dispersion`` vanished and every trace died.

These tests are deliberately written against the *whole* optics surface and
against a *discovered* list of star-importers, not against the one name that
broke. A helper added to ``optics.py`` tomorrow, or a fourth module that
star-imports Physics, is covered without anyone remembering to update a list.
"""

import ast
import re
from pathlib import Path

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "KrakenOS"

#: Names that must survive because live trace code calls them unqualified.
LOAD_BEARING_OPTICS_NAMES = (
    "n_wave_dispersion",
    "FresnelEnergy",
    "fresnel_dielectric",
    "fresnel_metal",
    "Abbe_refractive_correction",
    "ParaxCalc",
)


def _optics_public_names():
    import KrakenOS.Physics.optics as optics

    return sorted(n for n in vars(optics) if not n.startswith("_"))


def _star_importing_modules():
    """Every KrakenOS module that does ``from .Physics import *``.

    Discovered from source so a new consumer is covered automatically.
    """
    pattern = re.compile(r"^\s*from\s+\.+Physics\s+import\s+\*", re.MULTILINE)
    found = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:  # pragma: no cover - unreadable file
            continue
        if not pattern.search(text):
            continue
        rel = path.relative_to(PACKAGE_ROOT.parent).with_suffix("")
        parts = list(rel.parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        found.append(".".join(parts))
    return found


def test_optics_submodule_imports_standalone():
    """Guards the relative-import LEVEL.

    ``optics.py`` moved down a directory, so its ``ParaxialMatrix`` import has to
    climb two dots. With one dot this raises ModuleNotFoundError and the package
    silently falls back to exporting photodiode names only.
    """
    import KrakenOS.Physics.optics as optics

    assert callable(optics.n_wave_dispersion)
    assert callable(optics.build_paraxial_matrix_trace)


def test_star_importers_are_discovered():
    """The discovery itself must not silently find nothing."""
    modules = _star_importing_modules()
    assert "KrakenOS" in modules
    assert "KrakenOS.KrakenSys" in modules
    assert len(modules) >= 3, modules


@pytest.mark.parametrize("name", LOAD_BEARING_OPTICS_NAMES)
def test_load_bearing_names_reach_every_star_importer(name):
    import importlib

    missing = []
    for module_name in _star_importing_modules():
        module = importlib.import_module(module_name)
        if not hasattr(module, name):
            missing.append(module_name)
    assert missing == [], f"{name} unreachable from {missing}"


def test_whole_optics_surface_is_re_exported():
    """The package must export everything the legacy module's ``import *`` did."""
    import KrakenOS.Physics as physics

    dropped = [n for n in _optics_public_names() if not hasattr(physics, n)]
    assert dropped == [], f"Physics package dropped optics names: {dropped}"

    not_advertised = [n for n in _optics_public_names() if n not in physics.__all__]
    assert not_advertised == [], f"missing from __all__: {not_advertised}"


def test_photodiode_half_still_exported():
    """The legacy re-export must not have cost the newer photodiode API."""
    import KrakenOS as Kos
    import KrakenOS.Physics as physics

    missing = [n for n in physics.PHOTODIODE_API if not hasattr(physics, n)]
    assert missing == [], missing
    assert not [n for n in physics.PHOTODIODE_API if not hasattr(Kos, n)]


def test_physics_all_has_no_duplicates():
    import KrakenOS.Physics as physics

    assert len(physics.__all__) == len(set(physics.__all__))


def test_dispersion_returns_real_numbers():
    """A smoke check that the restored helper actually computes, not just imports."""
    import KrakenOS as Kos

    n, alpha = Kos.n_wave_dispersion(Kos.Setup(), "BK7", 0.55)
    assert 1.4 < float(n) < 1.7
    assert float(alpha) >= 0.0


def _build_doublet():
    import KrakenOS as Kos

    def surface(rc, thickness, glass, diameter, name=""):
        s = Kos.surf()
        s.Rc = rc
        s.Thickness = thickness
        s.Glass = glass
        s.Diameter = diameter
        if name:
            s.Name = name
        return s

    surfaces = [
        surface(0.0, 100.0, "AIR", 30.0, "P_Obj"),
        surface(92.84706570002484, 6.0, "BK7", 30.0),
        surface(-30.71608670000159, 3.0, "F2", 30.0),
        surface(-78.19730726078505, 97.37604742910693 - 40.0, "AIR", 30.0),
        surface(0.0, 40.0, "AIR", 3.0, "Pupil"),
        surface(0.0, 0.0, "AIR", 20.0, "P_Ima"),
    ]
    return Kos.system(surfaces, Kos.Setup())


def test_pupil_calc_runs():
    """PupilCalc is where the live failure SURFACED (as a bogus IndexError)."""
    import numpy as np
    import KrakenOS as Kos

    pupil = Kos.PupilCalc(_build_doublet(), 4, 0.4, "STOP", 3)
    assert float(np.ravel(pupil.RadPupInp)[0]) > 0.0


def test_non_sequential_beam_splitter_traces():
    """The user's live symptom: NsTraceLoop on a beam-splitter scene."""
    import importlib

    import numpy as np

    demo = importlib.import_module("KrakenOS.Examples.Examp_Beam_Splitter_50_50")
    rays = demo.trace_demo()
    paths = [np.asarray(s, dtype=int) for s in rays.SURFACE]
    assert len(paths) > 0, "no rays traced"
    assert any(len(p) > 2 for p in paths), "beam splitter produced no branching path"


def test_wave_precalc_does_not_poison_its_cache_on_failure(monkeypatch):
    """bugs/0474 amplifier.

    ``__WavePrecalc`` used to publish ``PreWave`` and clear its lists BEFORE the
    dispersion loop. One failure therefore left the precalc empty while marked
    done, and every later trace read ``self.N_Prec[j]`` off an empty list --
    turning the real fault into ``IndexError: list index out of range`` raised
    from an unrelated call site. Any dispersion failure (bad glass, missing
    catalog) hits this path, so the atomicity is guarded on its own.
    """
    import KrakenOS.KrakenSys as KrakenSys

    system = _build_doublet()
    real = KrakenSys.n_wave_dispersion
    calls = {"count": 0}

    def flaky(setup, glass, wave):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("dispersion unavailable")
        return real(setup, glass, wave)

    monkeypatch.setattr(KrakenSys, "n_wave_dispersion", flaky)

    with pytest.raises(RuntimeError):
        system.Trace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)

    # The retry must REBUILD the precalc, not read an empty one.
    system.Trace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)
    assert len(system.N_Prec) == system.n
    assert len(system.AlphaPrecal) == system.n


def test_no_module_shadows_a_package_in_krakenos():
    """The shape of bug 0474, generalised.

    A package and a same-named module cannot coexist: Python resolves the
    package and the module becomes unreachable. Catch the collision at the
    directory level rather than waiting for a NameError in a trace.
    """
    collisions = []
    for directory in [PACKAGE_ROOT, *[p for p in PACKAGE_ROOT.rglob("*") if p.is_dir()]]:
        if "__pycache__" in directory.parts:
            continue
        packages = {p.name for p in directory.iterdir() if p.is_dir() and (p / "__init__.py").exists()}
        modules = {p.stem for p in directory.glob("*.py") if p.stem != "__init__"}
        collisions.extend(f"{directory.name}/{n}" for n in sorted(packages & modules))
    assert collisions == [], f"module shadowed by a same-named package: {collisions}"


def test_optics_module_is_syntactically_whole():
    """Cheap tripwire: the moved file must still parse and define its helpers."""
    source = (PACKAGE_ROOT / "Physics" / "optics.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    defined = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert set(LOAD_BEARING_OPTICS_NAMES) <= defined
