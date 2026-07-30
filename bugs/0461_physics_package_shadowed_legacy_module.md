# 0461 — `KrakenOS/Physics/` (package) silently shadowed `KrakenOS/Physics.py`, killing the tracer

Reported live: every plot refresh died with

    Plot refresh error: NsTraceLoop failed for beam splitter, STL optical solid,
    off-axis/scene geometry: name 'n_wave_dispersion' is not defined
    ...
    File "KrakenOS/KrakenSys.py", line 1688, in __WavePrecalc
        (NP, AP) = n_wave_dispersion(self.SETUP, self.GlobGlass[i], self.Wave)
    NameError: name 'n_wave_dispersion' is not defined

plus, upstream of it, `Pupil pattern preview failed (list index out of range)` and
`[pupil] reference launch failed, geometric fallback`.

## Cause

Commit `b727b7ac` ("Docs: add interactive photodiode physics lab", 2026-07-29 08:12) added
**`KrakenOS/Physics/`** as a PACKAGE (`__init__.py` + `photodiode.py`). Python resolves a package
BEFORE a same-named module, so `KrakenOS/Physics.py` -- the legacy optics helpers -- became
unreachable. Three modules do `from .Physics import *`:

    KrakenOS/KrakenSys.py:9
    KrakenOS/PhysicsClass.py:3
    KrakenOS/__init__.py:268

After the package landed, that star-import delivered only the 12 photodiode names in the package's
`__all__`. Every optics helper the tracer needs -- `n_wave_dispersion` above all -- disappeared from
those namespaces, and the ray trace raised a bare `NameError` the first time it needed a refractive
index. Verified directly:

    import KrakenOS.Physics as P
    P.__file__                     -> KrakenOS/Physics/__init__.py      (the package)
    hasattr(P, "n_wave_dispersion") -> False
    len(P.__all__)                  -> 12  (photodiode names only)

Nothing was wrong with the photodiode code itself; the collision is purely the name.

## Fix

Move the legacy module INTO the package and re-export it:

* `git mv KrakenOS/Physics.py KrakenOS/Physics/optics.py`
* its one relative import becomes `from ..ParaxialMatrix import build_paraxial_matrix_trace`
* `Physics/__init__.py` gains `from .optics import *` and adds the legacy public names to `__all__`

Both APIs now work: `KrakenOS.Physics.n_wave_dispersion` and `KrakenOS.Physics.responsivity`, and
`from .Physics import *` means what it always meant.

Verified:

    n_wave_dispersion present: True     photodiode API intact: True
    visible in KrakenSys:      True     Kos.n_wave_dispersion:  True
    the user's scene traces again: reached_folds=[3,7], 166 of 837 rays within 15 mm of the sensor

## Lesson

A package that takes the name of an existing module removes that module from every namespace that
star-imported it, with no import error anywhere -- the failure surfaces far away as a NameError in
unrelated code, at runtime, only on the paths that use the vanished names. When adding
`package/__init__.py` beside an existing `package.py`, the old module's API must be re-exported in
the same commit.

## Afterword — this came back as 0474

The `git mv` above committed as a **rename with 0 insertions**: the `__init__.py` re-export edits
never made it into the commit, so the shadowing returned verbatim and was re-diagnosed as
bugs/0474 (which also found a second defect hiding behind it, and added
`tests/test_physics_star_import_contract.py` so a hand-written `__all__` cannot drop a helper
again). Read 0474 for the shipped fix; this file is the original diagnosis it refers back to.
The second lesson is the cheaper one: after a commit that mixes `git mv` with edits, check
`git show --stat` for insertions rather than trusting that the edits went along for the ride.
