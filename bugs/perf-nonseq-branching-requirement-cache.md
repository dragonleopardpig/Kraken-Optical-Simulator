# perf — Memoise the non-sequential branching-requirement check

Third NS-trace perf fix (after the cell-normal cache and the decimated proxy).
Profiling the metadata-bearing fine cube with both prior fixes in place revealed a
new dominant cost: **`optical_solid_metadata.nonnegative_int_list` = 77% of the
trace**, called once per ray with ~17.7 M set/list ops.

`pstats` traced the caller: `KrakenSys.system.__NsTraceRequiresBranching` (per
ray) → `__NsTraceHasDeterministicBeamSplitter`, which for every surface calls
`normalize_optical_solid_face_metadata(SDT[j].OpticalSolidFaces)`. That
re-normalises the full face metadata — including each face's huge
`triangle_indices` list (referencing the original fine mesh) — on **every ray**,
to answer the scene-level yes/no "does this scene contain a beam splitter?".

## Fix

The branching requirement (beam-splitter / diffuse-scatter presence) is invariant
for a system instance's lifetime — the trace never edits `OpticalSolidFaces`. So
`__NsTraceRequiresBranching` memoises the boolean in
`_ns_requires_branching_cache`, and the existing prescription-change hooks
`SetData` / `SetSolid` (which already reset the optical-solid caches) clear it. A
fresh `Kos.system` per refresh re-evaluates once.

## Measured result

49 k-cell beam-splitter cube **with face metadata**, 361 rays warm:
**1,758 ms → 970 ms = 1.81×**, transmit focus **|Δ| = 0.000000 mm**.

Combined with the two prior fixes, this metadata-bearing cube trace is now
~15,000 ms → ~970 ms (**~15×**) versus the original full-mesh, un-cached path.

## Lossless verification

The split must still fire — the cached `True` is the same value the per-ray
recompute produced. Confirmed: the beam-splitter scene memoises `True` and yields
2× branch entries; a plate cube memoises `False` and does not branch;
`bugs/repro_0093.py` produces 50 branch entries from 25 rays in all three
experiments; NS-trace regression validators all pass.

## Tests

- `python -m KrakenOS.UI.validate_nonseq_branching_requirement_cache` —
  display-free; checks a BS scene memoises `True` and still splits, a plate
  memoises `False` and does not branch, `SetData` resets the cache, and the source
  wiring. Penta **phase 99** (baseline → 100).
