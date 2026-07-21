# 0387 — lens swap freeze pass 2: cache the read-only pupil-reference system build

Follow-up to bugs/0386 (freeze pass 1). The remaining trace cost is the pupil first-order reference
rebuilding the SAME full-scene system WITH 3D solids several times per folded trace.

## Finding

Instrumenting `_build_system_from_specs` during the AZ85 capture: the full-scene specs (signature
`2d77a7bf`, 10 rows) are built **3×** (plus a 9-row one 2×). Those are the pupil first-order reference
(bugs/0094 per-branch) — and the bugs/0166 comment in `_build_system_from_specs` states that reference
**only runs PupilCalc, never NS-traces the meshes**, and passes `apply_optical_solid_output_ports=False`.
So it is READ-ONLY: a build keyed by its exact specs content is reusable.

## Fix

A bounded, content-keyed cache in `layout_editor.py`, scoped to the **read-only** path only
(`setup is None and not apply_optical_solid_output_ports`):
- `_paraxial_ref_system_cache_key(row_specs, build)` — `sha1` of `json.dumps(row_specs, sort_keys=True)`
  with **no `default=`**, so unserialisable specs return `None` and a hash collision can never return a
  wrong system. Order-independent; the build flag is part of the key.
- `_PARAXIAL_REF_SYSTEM_CACHE` (max 6, FIFO evict). The main NS-traced system (`apply_ports=True`) is
  **never** cached, so no traced-state can leak.

Content-keyed, so any model change (a swap, a thickness solve, an FOV change) mints a new key — the cache
self-invalidates.

## Verification

- **Safety (the load-bearing invariant):** the full `capture_async_trace_payload` output is
  **pickle-identical** with vs without the cache on the real AZ85 scene (`scratchpad/az85_cache.py`) —
  proving the read-only assumption, no state leak, no collision.
- **Speed:** −1.12 s on the warm capture (2.52 → 1.40 s, −44%).
- Guard `validate_open3d_paraxial_ref_system_cache` (phase 325): key is collision-free + None on
  unserialisable specs; store is bounded + evicts.

## Combined with pass 1

Swap-from-3D freeze: pass 1 removed one full redundant 2D trace (~5 s); pass 2 removes ~1.1 s of the
remaining trace's repeated solid build. Remaining: `import_lens_folder` re-parse (~1.5 s) when the
surrogate already exists — a further pass.

## Files

- `KrakenOS/UI/layout_editor.py` — the read-only reference system cache.
- `KrakenOS/UI/validate_open3d_paraxial_ref_system_cache.py` — guard (phase 325).
