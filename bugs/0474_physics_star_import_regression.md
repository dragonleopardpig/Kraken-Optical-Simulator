# 0474 — the Physics star-import contract regressed, and the cache laundered it into an IndexError

Live report on build `d8531138`: every plot refresh died with

    NsTraceLoop failed for beam splitter, STL optical solid, off-axis/scene geometry:
    name 'n_wave_dispersion' is not defined

raised from `KrakenSys.__WavePrecalc`, preceded by

    Pupil pattern preview failed (list index out of range); using meridional fan.
    [pupil] reference launch failed, geometric fallback: IndexError('list index out of range')
            at PupilTool.py:572:__init__ <- PupilTool.py:243:RMS_Pupil <- KrakenSys.py:2207:Trace

This is bug **0461 coming back**, plus a second defect that had been hiding behind it.

## Why it came back — the 0461 fix was never fully committed

`b727b7ac` added `KrakenOS/Physics/` as a **package**. Python resolves a package
before a same-named module, so `KrakenOS/Physics.py` — the legacy optics helpers —
became unreachable, and `from .Physics import *` started delivering only the 12
photodiode names in the package `__all__`.

`9828e733` ("restore the optics helpers the new Physics PACKAGE shadowed (0461)")
was supposed to fix that. Its commit message describes three changes:

> `git mv KrakenOS/Physics.py -> KrakenOS/Physics/optics.py` (its one relative
> import becomes `..ParaxialMatrix`), and `__init__` now does `from .optics
> import *` and extends `__all__` with the legacy names.

But the commit is **rename-only**:

    $ git show 9828e733 --stat
     KrakenOS/{Physics.py => Physics/optics.py} | 0
     1 file changed, 0 insertions(+), 0 deletions(-)

`git mv` staged the rename; the two content edits were left in the working tree
and never staged. They worked locally all day, then the tree was refreshed and
they were gone. Only the half that made the bug *possible* survived in git.

Confirmed the loss is isolated — `9828e733` is the only zero-content commit in
the last 25:

    9828e733   1 file changed, 0 insertions(+), 0 deletions(-)

Measured on `d8531138` before the fix:

    KrakenOS.Physics.__file__            -> .../KrakenOS/Physics/__init__.py   (the package)
    hasattr(Physics,   'n_wave_dispersion') -> False
    hasattr(Kos,       'n_wave_dispersion') -> False
    hasattr(KrakenSys, 'n_wave_dispersion') -> False
    import KrakenOS.Physics.optics       -> ModuleNotFoundError:
                                            No module named 'KrakenOS.Physics.ParaxialMatrix'

So both lost edits were needed: without the `..` the submodule will not even
import, and without the re-export the star-importers get nothing.

## Why the pupil failed with a *different* exception

The pupil error is the same root cause, disguised. `__WavePrecalc` used to be:

    if (self.Wave != self.PreWave):
        self.N_Prec = []
        self.AlphaPrecal = []
        self.PreWave = self.Wave              # <-- published BEFORE the work
        for i in range(0, self.n):
            (NP, AP) = n_wave_dispersion(...) # <-- raises here

It clears the lists and marks the wavelength done, *then* does the work. The
first call raises `NameError` and leaves the precalc **empty but marked
complete**. On the next call `self.Wave != self.PreWave` is False, the rebuild is
skipped entirely, and `KrakenSys.py:2207`

    (PrevN, alpha) = (self.N_Prec[j], self.AlphaPrecal[j])

indexes an empty list — `IndexError: list index out of range`, reported from
`PupilTool` with no trace of the real fault. That is exactly the pupil message
above, and it is why the two errors looked unrelated.

This laundering is a live hazard independent of 0474: any dispersion failure
(unknown glass, missing catalog) produces the same misleading `IndexError` at a
call site far from the cause.

## Fix

Three changes:

1. `KrakenOS/Physics/optics.py` — `from .ParaxialMatrix` → `from ..ParaxialMatrix`.
   The file moved down a directory; the import has to climb two levels.
2. `KrakenOS/Physics/__init__.py` — `from .optics import *`, and `__all__` is
   built as `PHOTODIODE_API` + the optics names **derived from the module**.
   Derived, not hand-listed: the legacy `Physics.py` had no `__all__`, so
   `import *` delivered every public global. A hand-written list would silently
   drop the next helper added to `optics.py` and reintroduce this bug.
3. `KrakenSys.__WavePrecalc` — build into locals and publish `N_Prec`,
   `AlphaPrecal` and `PreWave` only after every surface resolved. A failure now
   leaves the cache untouched, so the next call retries and the real exception
   surfaces where it happened.

## Verified

    star-importers discovered from source: KrakenSys, PhysicsClass, KrakenOS
    all 6 load-bearing optics names reach all 3                      OK
    n_wave_dispersion(BK7, 0.55 um) -> n = 1.518522, alpha = 1.603e-4
    beam-splitter NsTraceLoop  -> 14 bundles, 7 branching paths      OK
    PupilCalc (doublet, STOP 3) -> RadPupInp = 3.7358               OK
    photodiode API (12 names) intact                                 OK
    injected dispersion failure -> retried, not cached empty         OK

Guards: `tests/test_physics_star_import_contract.py` (17 tests) and penta phase
**383** (`validate_open3d_0474_physics_star_import`, display-free). Both were run
against the broken tree first — 14 of the pytest cases fail there, including the
pre-existing `tests/test_public_api.py`, which already asserted
`n_wave_dispersion` and would have caught this had it been run.

The guards are written against the *invariant*, not the instance: the whole
public surface of `optics` and a **discovered** list of star-importers, so a new
helper or a fourth consumer is covered without anyone updating a list. One
further tripwire (`test_no_module_shadows_a_package_in_krakenos`) fails if any
`X.py` and `X/` ever coexist again — the shape of this bug at its origin.
