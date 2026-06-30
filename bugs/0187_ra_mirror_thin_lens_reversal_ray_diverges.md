# 0187 — BUG: in the folded RA-mirror scene the rays reverse at the first Thin Lens and never reach the sensor ("ray diverges")

**Status: DIAGNOSED — fix direction NOT yet chosen (deep non-seq tracer change, high blast
radius). Awaiting go-ahead.**

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

## Candidate fixes (need a direction before implementing)

1. **Tracer fix (correct, highest blast radius):** make the non-seq thin-lens fake-normal
   interaction honour the incoming propagation sense, so a Thin Lens downstream of a mesh-mirror
   reflection deflects forward. Touches `KrakenSys.NsTrace` / `InterNormalCalc.__ParaxCalcObjOut2OrigSpace`
   / `PhysicsClass.calculate` SIGN handling — the same path every penta folding-mirror and
   thin-lens phase exercises. Must be gated and regression-checked against the full marathon
   (which currently segfaults under Xvfb on the long run — verification is itself a project).
2. **Surrogate fix (lower risk, changes the layout, not the engine):** rebuild the folded AZ85
   blackbox from a **real refractive prescription** (the actual ELS-85 glass, or the
   wavefront-augmented surrogate path) instead of two ideal `Thin Lens` elements, so the non-seq
   trace refracts through real surfaces. The promoted mesh mirror + real glass downstream is the
   combination the non-seq tracer is built for.
3. **Trace-mode fix (medium risk):** when a scene's only non-sequential element is a promoted FULL
   mirror (no beam splitter / diffuse / refractive mesh solid), trace it as a **folded SEQUENTIAL**
   pass (`use_folded`) rather than non-seq, where ideal thin lenses already work. Requires teaching
   the folded-sequential machinery to fold on an `OpticalSolidFaces` Mirror face (today it expects a
   sequential `Mirror` surface), so it is not a drop-in.

## Verification owed (once a direction is chosen)

A display-free guard that builds the runtime system and asserts **≥1 ray reaches the image surface
on +X at z ≈ 71.9** (and, ideally, that the on-axis bundle converges to a small spot at x ≈ 288),
plus a non-folded regression. No penta phase yet exercises a promoted mirror + thin-lens conjugate.
