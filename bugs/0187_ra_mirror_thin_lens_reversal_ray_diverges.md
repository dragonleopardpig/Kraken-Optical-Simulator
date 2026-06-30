# 0187 — BUG: in the folded RA-mirror scene the rays reverse at the first Thin Lens and never reach the sensor ("ray diverges")

**Status: RESOLVED via fix (3) — the folded-SEQUENTIAL trace. A promoted full-mirror cube is
represented as a sequential `Mirror` for the TRACE only (the display keeps the mesh cube), where
the ideal Thin Lenses work and the full ray cone reaches the +X sensor. Fix (1), the non-seq
tracer SIGN fix, remains documented below as the NEXT-LEVEL most-correct future fix; fix (2) is
discarded as too layout-specific. Generalises to an arbitrary CHAIN of folds (the user's planned
second RA mirror between lens and camera composes natively).**

## Flag

`attachment/recorded_bug_repros/flag_20260630_142846_722/` on the folded AZURE ELS-85 layout
(`KrakenOS/common_optical_layouts/machine_vision_AZ85_RA_Mirror.py`):

> "Sensor and Image plane located in front of the lens. Ray diverges."

This is the second issue on the same flag (the first, the Fan-vs-Cone launch, is bugs/0186).

## Symptom — measured headlessly, not eyeballed

Tracing the layout with its own `build_runtime_system()` + `build_rays()`:

- **0 of 93 rays reach the image surface (index 8).** The maximum surface hit is **4** — the first
  Thin Lens (`Blackbox Group 1`).
- 27 of the rays do a clean **retroreflection**: surface-hit sequence `[1, 2, 3, 4, 3, 2, 1]`.
  They fold +Z → +X at the mirror (surface 1), travel +X through the post-mirror gap (2), the
  Front Optical Vertex Datum (3) and into the first Thin Lens (4), then **bounce straight back**
  out through 3 → 2 → 1. Many rays stop even earlier (`[1]`, `[1,2]`, `[1,2,3]`).

Per-event ray directions for a retroreflecting ray (local = the surface's own frame):

| event | surface | world XYZ | local dir (OST_LMN) |
|-------|---------|-----------|---------------------|
| in    | 4 (Thin Lens) | `[100.09, −2.71, 71.9]` | `[0, −0.079, **+0.997**]` (forward) |
| next  | 3 (Datum)     | `[ 82.45, −4.40, 71.9]` | `[0, +0.096, **−0.995**]` (backward) |

The ray **arrives at the Thin Lens travelling forward** and the very next event has it travelling
**backward**, with the world-X coordinate retreating 100 → 82. The flat AIR reference planes
(surfaces 2 and 3) pass the ray straight through; **only the Thin Lens reverses it.** Because
nothing reaches the sensor at x ≈ 288, the only place the (reversed) bundle re-crosses the axis is
back near the mirror/object — which is what reads in the 3D view as "image/sensor in front of the
lens, ray diverges."

## What is NOT the cause (ruled out)

- **The fold geometry is correct (bugs/0185).** Rows [2..8] and the lens/camera STEP overlays sit
  on the folded +X branch at z = 71.897 (lens datums x 82→137, sensor x 287.82), spacings
  preserved. The mirror reflects +Z → +X as designed.
- **The downstream surface frames are correctly rotated.** The output-port override
  (`apply_optical_solid_output_port_system_overrides`) sets `TRANS_1A/TRANS_2A` for rows [2..8] to
  the folded pose: surface 4's local **+Z axis points along world +X**. The analytic non-seq
  surface trace (`KrakenSys.py` ~L2202 / `InterNormalCalc.InterNormal`) uses those transforms, so
  the ray enters the Thin Lens with **N_loc ≈ +0.997** (forward along the local axis) — the
  thin-lens deflection `P_x2 = (L/N)·f` does **not** divide by a near-zero N. The frame is fine.
- **It is not the launch sampler (bugs/0186).** The cone-vs-fan defect is independent; the rays
  reverse regardless of how the pupil is sampled.

## Root cause — the ideal Thin-Lens deflection mis-handles propagation SIGN after a mesh-mirror reflection

The promoted mirror cube is the only non-sequential element, so the whole trace runs
non-sequentially (`use_nonseq = True`). In `KrakenSys.NsTrace`, a mesh-mirror reflection flips the
propagation bookkeeping sign (`SIGN = SIGN * sign`, with the marching direction taken as
`__NsPhysicalDirection(ResVec, SIGN)`). The surrogate's optics are **ideal `Thin Lens` elements**
(surfaces 4 and 6: `Rc = 0`, `Glass = AIR`, `Thin_Lens = 159.49`). A thin lens has no real
refracting power from glass; KrakenOS fakes it by having `InterNormalCalc.__ParaxCalcObjOut2OrigSpace`
synthesise a **"fake surface normal"** so the downstream `PHYSICS.calculate` Snell step reproduces
the lens deflection. That fake-normal interaction returns a `sign` that, **after the upstream
mesh-mirror reflection has already put `SIGN = −1`, flips the marching direction backward** instead
of continuing the ray forward toward the focus. Net effect: the Thin Lens retro-reflects the ray.

The flat AIR datums survive because they have no fake-normal deflection (`Thin_Lens == 0`,
`Rc == 0`, no index change) — they pass the ray straight through with `sign = +1`. The reversal is
specific to the **ideal-thin-lens fake-normal SIGN bookkeeping interacting with the
already-flipped post-mirror SIGN.** In other words: an **ideal Thin-Lens blackbox is incompatible
with the non-sequential trace that a promoted mesh mirror forces.** (A real refracting prescription
— curved glass surfaces with an index change — refracts through `PHYSICS.calculate` normally and
would not hit this fake-normal path.)

## Candidate fixes (evaluated)

1. **Tracer SIGN fix (most correct, highest blast radius) — NEXT LEVEL, not yet done.** Make the
   non-seq thin-lens fake-normal interaction honour the incoming propagation sense, so a Thin Lens
   downstream of a mesh-mirror reflection deflects forward. Touches `KrakenSys.NsTrace` /
   `InterNormalCalc.__ParaxCalcObjOut2OrigSpace` / `PhysicsClass.calculate` SIGN handling — the same
   path every penta folding-mirror and thin-lens phase exercises. This is the *root* fix: it would
   let an ideal Thin Lens live downstream of ANY mesh interaction (mirror, beam splitter, refractive
   solid) in a genuinely non-sequential trace, not just a pure-mirror fold. It is deferred because it
   must be gated and regression-checked against the full marathon (which currently segfaults under
   Xvfb on the long run — verification is itself a project). **Pick this up when a non-seq scene needs
   ideal optics downstream of a mesh element that is NOT a full mirror (a beam splitter, a diffuser),
   because fix (3) below cannot fold those.**
2. **Surrogate fix (discarded — too layout-specific).** Rebuild the folded AZ85 blackbox from a real
   refractive prescription so the non-seq trace refracts through real glass. Rejected: it fixes only
   *this* layout (and only if a real prescription exists), does nothing for the next surrogate, and
   is not a general engine capability. Discarded per the user.
3. **Folded-SEQUENTIAL trace (CHOSEN + IMPLEMENTED).** When a scene's only non-sequential trigger is
   a promoted FULL mirror (no beam splitter / diffuse / refractive mesh solid), represent each such
   cube as a **sequential `Mirror` surface for the TRACE only** and trace the whole scene
   sequentially — where the ideal Thin Lenses already work. The native sequential tracer folds the
   running coordinate frame on a `Mirror` row (`AxisMove = 2`), so the downstream ideal optics behave
   and an **arbitrary CHAIN** of folds composes natively (no extra machinery for a 2nd, 3rd… mirror —
   the later fold is interpreted in the running, already-folded frame).

### How fix (3) works (implementation)

- **`KrakenOS/UI/services/folded_sequential_fold.py`** (new, pure):
  - `scene_nonseq_trigger_is_only_promoted_full_mirrors(specs)` — the **gate**: True iff ≥1 promoted
    full-mirror fold is present and EVERY non-seq trigger is such a fold. For any other scene it is
    False and nothing changes (contained blast radius; the penta suite and all non-folded layouts are
    untouched).
  - `fold_promoted_mirror_specs_to_sequential(specs) -> (new_specs, records)` — converts each promoted
    mirror cube row into a sequential `Mirror` (`glass="MIRROR"`, `rc=0`, `axis_move=2`, `advanced={}`)
    and **reseats** the cube's axial `desp_z` onto the preceding row's thickness so the AxisMove=2
    reflection folds cleanly from the running axis. Non-folded layouts return a plain copy + `[]`.
  - The per-mirror tilt is solved **convention-free**: the cube's world Mirror-face normal gives the
    target outgoing direction `reflect(d_in, n)`; we trace one chief ray through the partially-built
    chain for each principal half-angle candidate (±half about x/y/z) and keep the tilt whose real
    world exit direction matches (cos > 0.999). No hand-derived Euler/AxisMove sign tables (those
    differ per axis and would silently mis-fold a second mirror the user orients differently).
- **Wiring (`services/three_d_scene_tools.py` `_build_preview_system_rays_bundle`):** when
  `_folded_sequential_trace_rows(self.rows)` returns folded rows, a separate `trace_system` is built
  from the folded specs and the rays come from it; the display **`scene_bundle` is still built from the
  original mesh `system`**, so the cube + bugs/0185 folded overlays draw unchanged. A transient
  `editor._force_sequential_preview_trace` flag is honoured in `services/trace_preview.py`
  `_trace_preview_bundles` to force the **sequential** backend — necessary because a folded `Mirror`
  carries a tilt, which `resolve_trace_intent` would otherwise classify as off-axis (non-seq) geometry.
  (Measured: a non-seq trace of the folded specs still reaches **0** rays; the sequential trace reaches
  the sensor.)

## Verification (done)

`KrakenOS/UI/validate_open3d_ra_mirror_folded_sequential_trace.py` (standalone, display-free; run
`.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_folded_sequential_trace`):

1. the single-mirror AZ85 layout folds +Z → +X and the on-axis ray lands on the sensor at world
   X ≈ 287.82, Z ≈ 71.9 (the flag's measured station);
2. a synthetic SECOND cube before the image (the user's planned RA mirror between lens and camera)
   still reaches the image — the chain composes (on-axis ray at X ≈ 300.32, Z ≈ 111.9);
3. a non-folded layout (`flat_mirror_45_deg.py`) is left byte-identical (gate False, no records);
4. END-TO-END the real editor pipeline (`_build_preview_system_rays_bundle`) folds the AZ85 scene and
   traces it on a `TraceLoop` backend (never `NsTraceLoop`) so the full ray cone lands on the +X
   sensor, while the display row keeps its promoted cube.

This guard is standalone (NOT a penta phase) — no penta phase exercises a promoted mirror + thin-lens
conjugate. In-app eyeball still owed (headless cannot drive the VTK inspector).

## Known limitation — Quick Estimation across a fold (NEXT LEVEL)

With a fold (and more so with a CHAIN), the object path and/or the image path break into multiple
axial **segments** (object→mirror, mirror→lens, lens→…→sensor), each along a different world axis.
The Quick Estimation overlay assumes a single straight axis, so it has no clean way to lay out its
estimate across the broken path yet. Folding the QE onto the running, per-segment frame (the same
frame the sequential tracer already composes) is the next-level follow-up; not addressed here.
