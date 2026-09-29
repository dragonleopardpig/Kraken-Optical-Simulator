# Design: three wave domains — route the question, do not write the propagator

Status: **proposal, 2026-09-29.** Nothing in this document is implemented. It supersedes nothing;
`docs/design_scene_ir.md` is a **prerequisite** for Stage 4 onward and is referenced, not repeated.

A note on numbering. `design_scene_ir.md` owns the words *Phase A–D*. This document uses
**Stage 1–7** so that "Phase D" always means the fold moving inside `lower()`, and never something
here.

## Why this, and not "add a wave module"

The obvious plan is to add diffraction to KrakenOS: pick a propagator, wire it behind a new
analysis mode, done. That plan is wrong for a measurable reason.

**KrakenOS already has four partial wave implementations, and each is honest about being partial.**

| what | where | scope it declares |
|---|---|---|
| diffraction PSF/MTF | `PSFCalc.py` | Zernike pupil → Fraunhofer FFT. No propagation. |
| coherent detector | `UI/coherent_detector_analysis.py` | ray-carried OPD + Jones P/S, binned and summed. Not a field. |
| angular spectrum | same file | `"Fraunhofer angular-spectrum FFT of coherent detector field"` — of the *detector* field, at the end. |
| grid field | `BranchField.py` | `"Only model='paraxial' is implemented in the first Phase 8 field slice."` |

A fifth would not change the shape of the problem. The interferogram makes this concrete:
`Examples/Examp_Michelson_Interferometer.py:237-244` computes real traced OPD and real branch
phase, then multiplies in a **user-supplied fringe tilt** as the carrier. Its own docstring says
"first-order". The physics that is missing is not a formula; it is a *domain* in which a field can
propagate, and a contract for getting into and out of it.

**And the propagators are already bought.** `~/Projects` holds five engines covering the whole
space (roster measured below). Writing a sixth would be the least valuable work available.

So the deliverable is not a propagator. It is **three domains and the handovers between them.**

## The one invariant

    A field never exists without a frame, a unit, and a sampling verdict.

There is no unverified field in the system. A field that cannot state its verdict is **refused**,
not returned — `feedback_no_silent_solve_failure` applied to diffraction, and for the same reason:
a plausible fringe pattern is more dangerous than an error, because it looks authoritative.

This invariant is checkable, which is the point. A guard can assert that every field crossing a
domain boundary carries all three, and that assertion is red until Stage 3 lands, on purpose.

## Shape

Three domains. None is a superset of another; the routing is the design.

```
  Domain G — rays                Domain B — beamlets              Domain F — grid fields
  ───────────────────            ───────────────────              ─────────────────────────
  KrakenOS, optiland             raypier                          poppy, lightpipes, torchoptics
  arbitrary 3D frames            arbitrary 3D frames              z-normal planes ONLY
  real surfaces, glass, TIR,     ray + complex q + Jones          exact scalar diffraction,
  coatings, CAD, non-seq         field by mode summation          hard edges, MCF, gain sheets
  NO diffraction                 weak at hard edges + caustics    NO real surfaces

      G ──seed hex beamlet grid──▶ B ──eval E-field on a plane──▶ F
      G ──Zernike pupil + amplitude map─────────────────────────▶ F
      F ──decompose_position / decompose_angle──▶ B ──▶ G
```

**Domain B is load-bearing.** It is the only one of the three with both 3D generality and phase.
Every tilted or folded question routes through it. That single fact is why `raypier` matters more
to this design than `torchoptics` does, which is the opposite of what the package descriptions
suggest.

Handover payloads are flat data, following the IR discipline — frozen dataclasses, no closures, no
live object references. If it cannot be written to disk and read back identically, it does not
cross a domain boundary.

```python
@dataclass(frozen=True)
class FieldHandover:
    field: np.ndarray          # complex, (Ny, Nx) or (..., Ny, Nx)
    frame: np.ndarray          # (4,4) world pose of the plane, POST-FOLD, always
    leg_id: str                # which straight leg of SceneIR this plane belongs to
    dx_m: tuple[float, float]  # SI metres. The engines disagree on units; the IR does not.
    wavelength_m: float
    verdict: "SamplingVerdict" # never None, never optional
    provenance: dict           # engine, version, method, seed origin

@dataclass(frozen=True)
class SamplingVerdict:
    ok: bool
    fresnel_number: float
    nyquist_margin: float       # < 1.0 means the quadratic phase is aliased
    critical_distance_m: float  # Voelz A.17, as torchoptics computes it
    guard_band_ratio: float     # padded extent / physical extent
    beamlet_overlap: float | None   # domain B only; None in F
    refusals: tuple[str, ...]   # empty iff ok
```

`SamplingVerdict.ok` is the gate. It is computed from the handover alone, so it can be asserted
without running an engine, which is what makes Stage 3 testable.

## The engine roster, measured 2026-09-29

Licenses first, because one of them constrains everything and it is better to know now.

| domain | engine | license | unique contribution |
|---|---|---|---|
| G | **KrakenOS** | **GPL-3** | scene of record: UI, CAD/STEP, catalogs, non-seq, tolerancing |
| G | optiland | MIT | `nonsequential/ir/` — the pattern `services/scene_ir.py` already copies |
| B | **raypier** | **GPL-3** | `core/gausslets.py`: `decompose_position`, `decompose_angle`; `core/fields.py`: `eval_Efield_from_gausslets`, `EFieldSummation`, `lagrange_invariant`, `make_hexagonal_grid`; Cython `core/cfields.pyx` |
| F | **poppy** | BSD-3 | `FresnelWavefront` with `_propagate_ptp` / `_wts` / `_stw` and a tracked pilot beam — Lawrence/Sziklas–Siegman, i.e. POP. JWST-validated. |
| F | **lightpipes** | BSD | `CircScreen`/`RectScreen` obstructions, `Steps` (BPM, complex refractive index), **`Gain`** (saturable sheet), `BeamMix`, `Strehl`, `ZonePlate` |
| F | **torchoptics** | MIT | ASM + DIM, autograd, full MCF, Jones elements |
| — | pySCATMECH | NIST | polarized BRDF, particle scatter, thin films |
| — | PyZDDE | — | the external reference. Worth more than any engine here. |

**The license finding, once, so it is never re-litigated.** KrakenOS is GPL-3
(`LICENSE.txt:1`). raypier is GPL-3 (`setup.py` header). They combine without friction —
which is fortunate, because raypier is Domain B and Domain B is load-bearing. poppy (BSD-3),
lightpipes (BSD) and torchoptics (MIT) are all inbound-compatible. **The combination ships as
GPL-3.** `reference_krakenos_gpl_vs_optiland_mit` already establishes that the non-sequential
engine is not relicensable; this does not change that, it only confirms the wave work inherits it.

### Measured baseline: the roster does not exist yet

`.devenv/state/venv/bin/python`, 2026-09-29:

    python 3.13.12
      numpy        OK    2.4.2
      scipy        OK    1.18.1
      torch        MISS  ModuleNotFoundError
      cupy         MISS  ModuleNotFoundError
      torchoptics  MISS  ModuleNotFoundError
      poppy        MISS  ModuleNotFoundError
      lightpipes   MISS  ModuleNotFoundError
      raypier      MISS  ModuleNotFoundError
      tmm          MISS  ModuleNotFoundError

**Zero of five engines are importable.** `torch` is absent because it arrives only from the opt-in
`scripts.kraken-install-gpu` (`devenv.nix:220-225`), whose three `pip install` lines each end in
`|| true` — so a failure is silent and indistinguishable from never having run it. `gpu_backend.py`
degrades to NumPy and nothing complains, which is correct behaviour and also why nobody noticed.

That is Stage 1's entire content, and it is a better first commit than any physics.

### Measured baseline: the canonical sampling case

25 mm aperture, HeNe 0.6328 µm, observation plane at 100 mm. Voelz Eq. A.17 as torchoptics
implements it (`propagation/propagator.py:151`), `z_c = 2·|x_max|·Δ/λ`:

    N=  512  dx= 48.83 um  z_c= 1929.1 mm  ASM@100mm=yes  samples/fringe=  5.2  field=  4.2 MB
    N= 1024  dx= 24.41 um  z_c=  964.5 mm  ASM@100mm=yes  samples/fringe= 10.3  field= 16.8 MB
    N= 2048  dx= 12.21 um  z_c=  482.3 mm  ASM@100mm=yes  samples/fringe= 20.6  field= 67.1 MB
    N= 4096  dx=  6.10 um  z_c=  241.1 mm  ASM@100mm=yes  samples/fringe= 41.2  field=268.4 MB

    Fresnel number N_F = D^2/(lam z) = 9877   (deep near field)
    edge fringe scale sqrt(lam z)    = 252 um

Two readings matter. First, **the canonical case is comfortable** — 2048² is 67 MB with 20 samples
per edge fringe, so the interesting physics is not gated on compute. Second, **`z_c` moves the
wrong way with resolution**: refining the grid *lowers* the critical distance, so a user who
"improves" sampling can silently cross from ASM into DIM. A guard that reports only grid size
would call N=4096 better than N=512. The verdict has to carry `critical_distance_m`.

### Measured baseline: partial coherence is quartic and that is the whole story

`torchoptics.SpatialCoherence` carries the full mutual coherence function, `DATA_MIN_NDIM = 4`,
shape `(..., H, W, H, W)`:

    MCF  32x 32  ->  complex128 =   0.017 GB
    MCF  64x 64  ->  complex128 =   0.268 GB
    MCF 128x128  ->  complex128 =   4.295 GB
    MCF 256x256  ->  complex128 =  68.719 GB

Partial coherence in Domain F is a **coarse-grid instrument**, permanently. 64² is the working
size, 128² is the ceiling on this desktop, and 256² is not a resolution choice, it is a different
machine. Per `feedback_leave_system_headroom`, anything at 128² runs alone. The general
partial-coherence answer therefore has to come from beamlet mutual coherence in Domain B, not from
refining F — which is a physics conclusion forced by an arithmetic fact, and worth writing down
before someone spends a week discovering it.

## Migration

Seven stages. Stages 1–3 need **nothing** from `design_scene_ir.md` and can start immediately;
Stage 4 onward cannot start until its Phase D lands. That ordering is deliberate: it puts the
engine truth and the guard in place while the IR work proceeds independently, instead of blocking
on it.

**Stage 1 — the roster exists.** Pin and install the five engines; record versions.
*Gate:* all five import in `.devenv/state/venv`; the silent `|| true` failures in
`kraken-install-gpu` are made loud; a validator asserts the roster and fails on a missing engine
rather than degrading. `feedback_nix_flake_untracked_files` applies — `git add` the devenv change
before rebuilding.

**Stage 2 — the known-answer battery, engines only, no KrakenOS.** Four problems with references
outside this codebase: circular-aperture Airy pattern, knife edge, Poisson's spot behind a disc,
Ronchi self-imaging. Run each on poppy, lightpipes and torchoptics.
*Gate:* each engine within a stated tolerance of the analytic or textbook answer, **and** a
cross-engine agreement matrix. Disagreement between two BSD-licensed, independently validated
engines is a finding about our harness, not about optics — which is exactly the diagnostic no
single-engine integration can produce.

**Stage 3 — the sampling guard, derived from Stage 2's failures.** Not designed a priori: build
the battery first, deliberately push each case until it breaks, then write the verdict that would
have caught it.
*Gate:* the guard refuses every configuration Stage 2 showed to be under-sampled, and passes every
one it showed to be sound. A guard tuned to its own author's intuition is a guard that asserts a
comment (`feedback_guards_assert_claims_not_calls`); one tuned to measured breakage is an
instrument.

**Stage 4 — the units and frames contract.** One module: KrakenOS mm/µm ↔ SI metres, 4×4 world
frame ↔ (z-normal plane, spacing, offset), and `Leg` extracted from `SceneIR.legs`.
**Requires `design_scene_ir.md` Phase D.** A wave engine cannot be handed a leg whose `to_world`
is a straight-equivalent; `reference_straight_equivalent_not_an_unfold` is the standing rule and
bugs/0593 is the precedent.
*Gate:* lower a folded scene, reconstruct every leg, assert the leg-chain optical path equals the
traced `TOP` to < 1 µm. On the real scenes — om05a benches, ELS85, Pyrite85, Apo75 — per
`feedback_general_not_special_case`.

**Stage 5 — G→F on one straight leg.** Seed from the ray pupil wavefront (`PhaseCalc.Phase2` →
`WavefrontFit.Zernike_Fitting`) plus an amplitude/vignetting map; propagate; land on the detector.
Back it with **two** engines and cross-check.
*Gate:* the propagated PSF matches the existing Fraunhofer PSF in the aberration-free limit; the
Ronchi/spider mask that today throws a geometric shadow produces fringes; poppy and torchoptics
agree to a stated tolerance. An image-snapshot test, per `feedback_image_snapshot_tests` — property
assertions alone will not catch a wrong fringe orientation.

**Stage 6 — beamlets, for the folded and tilted case.** raypier has STEP **export only** — there is
no `read_step` in `raypier/*.py`, measured — so exporting KrakenOS geometry into raypier is a dead
end; it would need its own scene definition and we would own two. The direction is inward: port
`raypier/core/gausslets.py` and the `core/cfields.pyx` evaluation to consume KrakenOS ray output,
seeded from the existing `GaussianBeam.propagate_branch_gaussian_q` / `BranchGaussianQTrace`, which
already carries complex q per branch through the non-sequential scene. Both are GPL-3, so the port
is clean.
*Gate:* a 45° fold + prism scene where the beamlet field at the detector matches Stage 5's field on
the equivalent unfolded straight leg. This is the gate that either validates Domain B or kills it,
and nothing in Stage 7 should be attempted first.

**Stage 7 — the named gaps, in value order.** Each independent; none blocks another.

| gap | route | why it waits |
|---|---|---|
| real multilayer coatings | add `tmm` — the one genuine package gap in the collection | feeds the coherent detector that already exists |
| resonator transverse modes | lightpipes `Gain` + `BeamMix` + aperture + `Forvard` = Fox–Li with gain saturation | gives mode *shapes*; `solve_gaussian_cavity_eigenmode` gives only w and stability |
| partial coherence | torchoptics MCF at 64² for illumination; beamlet MCF for the general case | the quartic baseline above forces this split |
| stray light / ghosts | pySCATMECH BRDF into KrakenOS non-seq | nobody has joined these two |
| rotated ASM (Matsushima) | only if Stage 6 proves beamlets inadequate at tilted refracting faces | may never be needed |

## Acceptance

Three instruments, gated together. None alone is sufficient, and the reason is the 0457 lesson
recorded in `design_scene_ir.md`: an audit that measures the wrong thing produces a confident,
precise, wrong number, and three investigations chase it.

* **The roster validator** (Stage 1) — refuses to degrade silently. A missing engine is a failure,
  not a NumPy fallback.
* **The known-answer battery + agreement matrix** (Stage 2) — external truth, then engine-vs-engine.
* **The sampling guard** (Stage 3) — asserted on every handover, red until it exists.

Plus, from Stage 4 on, the existing pair: `tools/pose_audit.py` and
`scene_placement_audit.pinned_placement_drifts`. A wave answer on a scene whose geometry is
drifting is not a wave finding.

Per `reference_krakenos_regression_validator`, new validators join a penta phase or they rot —
`reference_ungated_validators` measures 178 ungated validators with roughly one in three failing.
Every stage's gate lands in a phase in the same commit.

## Explicitly not in scope

* **Writing a propagator.** Four are already owned. A fifth is the least valuable work available.
* **Unifying the engines' scene models.** One scene of record, adapters outward. Seven scene
  models is the current state and it is fine, provided exactly one of them is authoritative.
* **Porting the KrakenOS UI to another backend.** Orthogonal, and separately expensive — the 3D
  inspector touches 197 distinct editor attributes across 888 references, measured 2026-09-29.
  `docs/design_qt_migration.md` owns that work.
* **RCWA / FDTD.** No package in the collection provides it and nothing in the current requirement
  set needs it. Revisit only when a real DOE or metasurface appears.
* **FEA → deformed optical surface.** STOP-utils does WFE decomposition, not the coupling.
* **Changing the sequential trace's mathematics.** It keeps consuming `prescription`, exactly as
  `design_scene_ir.md` states.

## Open questions

1. **Does the ray-seeded field carry enough truth to be worth propagating?** The Stage 5 seed is a
   Zernike fit of a ray-sampled wavefront, so it has already discarded whatever the rays did not
   sample, and a hard vignetting edge is precisely what a low-order fit smooths away. Stage 5's
   aberration-free-limit gate does not test this — an unaberrated pupil is exactly where the fit is
   perfect. **An additional case is needed: a deliberately vignetted pupil, where the fit is known
   to be poor, to characterise how wrong the seed is before anything depends on it.**

2. **What is the beamlet density rule?** `lagrange_invariant` and the hex grid exist; the rule for
   how many beamlets a given aperture and NA needs, and what `beamlet_overlap` must exceed, is not
   derivable from the source and has to be measured in Stage 6.

3. **Which engine is authoritative in Domain F when two disagree?** Stage 2 will produce
   disagreements. The decision cannot be "whichever matches the analytic case" because the
   interesting scenes have no analytic case. Candidate: poppy for anything with a pilot beam,
   lightpipes for hard edges and gain, torchoptics for gradients and coherence — declared per
   question rather than globally. Undecided.

4. **Does Domain B handle a tilted *refracting* face, or only a fold?** A mirror is a coordinate
   reset. A beamlet crossing a tilted glass interface acquires astigmatism that the generally
   astigmatic mode can represent, but whether the *decomposition* survives a prism cascade is the
   open physics question of this design, and Stage 6's gate is written to answer it.

5. **Where does a wave answer surface in the UI?** `analysis_modes.py` has 24 modes and the picker
   is already crowded. A wave answer that carries a refusal needs somewhere to *show* the refusal —
   `feedback_no_silent_solve_failure` requires it be visible in the scene, not buried in a log.
   Not designed.
