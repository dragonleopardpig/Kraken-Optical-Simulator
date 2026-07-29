"""bugs/0474 -- guard the ``from .Physics import *`` contract.

Deliberately display-free: this is a pure import/namespace contract plus two
small headless traces, so it needs no Tk app and no VTK render window. It is
the cheapest phase in the harness and it cannot segfault.

What it guards, in order of how the bug actually unfolded:

1. ``KrakenOS.Physics.optics`` imports standalone -- catches the relative-import
   LEVEL (the file moved down a directory, so ``ParaxialMatrix`` needs ``..``).
2. Every public name in ``optics`` is reachable from the Physics package AND
   from every module that star-imports it. The star-importer list is
   DISCOVERED from source, so a new consumer is covered automatically.
3. The photodiode half still exports.
4. ``__WavePrecalc`` commits atomically -- a dispersion failure must not leave
   an empty precalc marked done, which is what turned bug 0474 into a bogus
   ``IndexError`` inside PupilTool.
5. A real non-sequential beam-splitter trace and a real PupilCalc still run.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path


LOAD_BEARING = (
    "n_wave_dispersion",
    "FresnelEnergy",
    "fresnel_dielectric",
    "fresnel_metal",
    "Abbe_refractive_correction",
    "ParaxCalc",
)


def _package_root() -> Path:
    import KrakenOS

    return Path(KrakenOS.__file__).resolve().parent


def _star_importers() -> list[str]:
    pattern = re.compile(r"^\s*from\s+\.+Physics\s+import\s+\*", re.MULTILINE)
    root = _package_root()
    found = []
    for path in sorted(root.rglob("*.py")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if not pattern.search(text):
            continue
        parts = list(path.relative_to(root.parent).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        found.append(".".join(parts))
    return found


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


def run_checks() -> tuple[bool, list[str]]:
    ok = True
    notes: list[str] = []

    # 1 -- the moved module imports on its own
    try:
        optics = importlib.import_module("KrakenOS.Physics.optics")
        notes.append(f"IMPORT = KrakenOS.Physics.optics loads ({Path(optics.__file__).name})")
    except Exception as exc:
        notes.append(f"IMPORT KrakenOS.Physics.optics failed: {exc!r}")
        return False, notes

    public = sorted(n for n in vars(optics) if not n.startswith("_"))
    notes.append(f"SURFACE = optics exports {len(public)} public names")

    # 2 -- the package re-exports the whole legacy surface
    physics = importlib.import_module("KrakenOS.Physics")
    dropped = [n for n in public if not hasattr(physics, n)]
    if dropped:
        notes.append(f"REEXPORT Physics package dropped {dropped}")
        ok = False
    else:
        notes.append("REEXPORT = the Physics package re-exports every optics name")

    not_advertised = [n for n in public if n not in getattr(physics, "__all__", ())]
    if not_advertised:
        notes.append(f"ALL __all__ omits {not_advertised}")
        ok = False
    else:
        notes.append(f"ALL = __all__ advertises all {len(physics.__all__)} names")

    # 2b -- every star-importer actually receives them
    importers = _star_importers()
    if len(importers) < 3:
        notes.append(f"DISCOVERY only found star-importers {importers}")
        ok = False
    else:
        notes.append(f"DISCOVERY = star-importers {importers}")

    for module_name in importers:
        module = importlib.import_module(module_name)
        missing = [n for n in LOAD_BEARING if not hasattr(module, n)]
        if missing:
            notes.append(f"UNQUALIFIED {module_name} cannot see {missing}")
            ok = False
    if ok:
        notes.append(f"UNQUALIFIED = all {len(LOAD_BEARING)} load-bearing names reach every importer")

    # 3 -- the photodiode half survived
    photo_missing = [n for n in getattr(physics, "PHOTODIODE_API", ()) if not hasattr(physics, n)]
    if photo_missing or not getattr(physics, "PHOTODIODE_API", ()):
        notes.append(f"PHOTODIODE half broken: missing={photo_missing}")
        ok = False
    else:
        notes.append(f"PHOTODIODE = {len(physics.PHOTODIODE_API)} photodiode names intact")

    # 4 -- the precalc cache commits atomically
    try:
        KrakenSys = importlib.import_module("KrakenOS.KrakenSys")
        system = _build_doublet()
        real = KrakenSys.n_wave_dispersion
        state = {"count": 0}

        def flaky(setup, glass, wave):
            state["count"] += 1
            if state["count"] == 1:
                raise RuntimeError("dispersion unavailable (injected)")
            return real(setup, glass, wave)

        KrakenSys.n_wave_dispersion = flaky
        try:
            try:
                system.Trace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)
                notes.append("ATOMIC injected dispersion failure did not propagate")
                ok = False
            except RuntimeError:
                pass
            system.Trace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)
        finally:
            KrakenSys.n_wave_dispersion = real

        if len(system.N_Prec) == system.n and len(system.AlphaPrecal) == system.n:
            notes.append(f"ATOMIC = a failed precalc is retried, not cached empty (n={system.n})")
        else:
            notes.append(
                f"ATOMIC precalc left poisoned: N_Prec={len(system.N_Prec)} "
                f"AlphaPrecal={len(system.AlphaPrecal)} n={system.n}"
            )
            ok = False
    except Exception as exc:
        notes.append(f"ATOMIC guard raised: {exc!r}")
        ok = False

    # 5 -- the live paths that failed for the user
    try:
        import numpy as np

        demo = importlib.import_module("KrakenOS.Examples.Examp_Beam_Splitter_50_50")
        rays = demo.trace_demo()
        paths = [np.asarray(s, dtype=int) for s in rays.SURFACE]
        branching = sum(1 for p in paths if len(p) > 2)
        if paths and branching:
            notes.append(f"NSTRACE = beam-splitter NsTraceLoop: {len(paths)} bundles, {branching} branching")
        else:
            notes.append(f"NSTRACE beam splitter produced {len(paths)} bundles / {branching} branching")
            ok = False
    except Exception as exc:
        notes.append(f"NSTRACE beam-splitter trace raised: {exc!r}")
        ok = False

    try:
        import numpy as np
        import KrakenOS as Kos

        pupil = Kos.PupilCalc(_build_doublet(), 4, 0.4, "STOP", 3)
        radius = float(np.ravel(pupil.RadPupInp)[0])
        if radius > 0.0:
            notes.append(f"PUPIL = PupilCalc runs, RadPupInp={radius:.4f}")
        else:
            notes.append(f"PUPIL PupilCalc returned a non-positive radius {radius}")
            ok = False
    except Exception as exc:
        notes.append(f"PUPIL PupilCalc raised: {exc!r}")
        ok = False

    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
