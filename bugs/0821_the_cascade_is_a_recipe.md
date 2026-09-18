# 0821 -- the penta cascade is a recipe, not an asset

User: "I think we only need five_penta_prism_analytic_telescope_cascade.py, the rest of the
five_penta can be retired." Then, when I flagged that one of them is what the whole penta suite
loads: "five_penta_prism_analytic_telescope_cascade.py got more than five_penta_prism_cascade.py."

Measured, that is exactly right, and it makes the retirement free.

## The four files

| file | what it is | retired |
|---|---|---|
| `five_penta_prism_analytic_telescope_cascade.py` | output of `build_penta_analytic_telescope_layout.py` | **kept** |
| `five_penta_prism_telescope_cascade.py` | output of `build_penta_telescope_layout.py`; nothing else loads it | yes |
| `five_penta_prism_cascade_with_lens.py` | one standalone guard, not a penta phase | yes |
| `five_penta_prism_cascade.py` | **the penta suite's base scene** -- phase 0 hard-fails without it, six other modules read it | yes, now DERIVED |

## Why the last one can go

```
plain    7 rows: Object, Penta prism 1..5, Image
analytic 18 rows: Object, Penta prism 1..5, Ball Lens 1, ..., Achromat, Cylindrical, Image
```

Rows 0-5 are **byte-identical** between the two files -- same prisms, same `OpticalSolidFaces`, same
poses. The first difference is at row 6, where the plain file's `Image` (at the origin) meets the
analytic file's `Ball Lens 1 (sapphire)`. The plain cascade IS the analytic one's prism head plus an
Image row at the origin; storing both stored the same geometry twice, which is bugs/0810's doctrine
("a cache is a recipe") applied to a fixture.

## Fix

`services/penta_cascade_fixture.ensure_five_penta_cascade(path, source=...)`:

* returns the fixture when it is there, untouched -- it never rewrites a file it did not create;
* otherwise loads the analytic cascade, keeps rows 0-5, zeroes the Image row's placement and writes
  the 7-row scene through the editor's own writer (`_sync_table` first -- bugs/0815);
* returns None when neither file is present, because the attachment tree is Filen-synced and every
  caller treats a missing scene as SKIP. It never raises.

Wired into penta phase 0 and the five standalone consumers
(`penta_telescope_chain`, `penta_cascade_prism_by_prism`, `five_penta_initial_visual`,
`optical_solid_face_coating`, `0485_axis_fold_emissions`), and the file is untracked -- `.gitignore`
already carries `/attachment/*.py`.

## Verified

* The derived file matches the stored one **row for row** (names, diameters, glasses, thicknesses,
  decentres, tilts, and the prisms' solid metadata).
* Deleted the fixture, ran penta phases 0-60: the suite **regenerated it** and 60 phases passed --
  the same result as with the stored file, including the same single red, phase 52, which the
  2026-08-30 baseline already records as `fail`.
* Phase 600's guard covers the derivation, its idempotence, the no-source case and the wiring.

## Also cleared in this pass

Four tracked scenes had gone missing from the working tree and were restored from git before any of
this was known (`analytic_telescope_chain.py`, the two telescope cascades, the plain cascade). The
user had deleted them deliberately. `analytic_telescope_chain.py` is referenced by nothing and is
kept only because it is not a five_penta file -- it is a candidate for the same treatment.

Eight further fixtures the user deleted are **untracked**, so git cannot bring them back, and the
guards that load them SKIP rather than fail -- coverage disappears without turning the suite red:

| fixture | guards |
|---|---|
| `attachment/machine_vision_AZ85_RA_Mirror_BS.py` | 50 |
| `attachment/machine_vision_AZ85_RA_Mirror.py` | 21 |
| `attachment/machine_vision_150mm_test.py` | 16 |
| `attachment/prisms/cube.stl` | 4 |
| `attachment/machine_vision_150mm_measured_test.py` | 3 |
| `attachment/om05a_two_side.py` | 2 |
| `attachment/doublet.py` | 1 |
| `attachment/part.step` | 1 |
