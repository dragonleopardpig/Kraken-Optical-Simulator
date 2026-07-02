# 0203 — BUG: the folded RA-mirror preview draws a sparse FAN, not a dense cone ("old bug resurface"); focus varies left-to-right

**Status: RESOLVED. A NON-branching promoted-mirror fold now routes its preview launch to the dense
revolved `world_cone` (like its sequential straight-equivalent), not the sparse ~31-ray area-filling
`world_envelope` that foreshortens to a flat fan (#2). The converged focus (bugs/0197 rigid flip) is
preserved — the wired on-axis cone lands on the drawn detector at ~0.8 µm transverse RMS, and the
guard pins the rigid flip against a revert to the old per-ray `tau` shear that smeared it to ~1.5 mm
(#5).**

## Origin

The user re-flagged the SAME working (bugs/0197-converging) folded AZURE ELS-85 layout
(`KrakenOS/common_optical_layouts/machine_vision_AZ85_RA_Mirror.py`, AZ85 = ELS-85 surrogate) twice in
one Open-3D session:

- **#2** (`attachment/recorded_bug_repros/flag_20260701_201316_884/`): *"the rays are fan, not cone.
  Old bug resurface."*
- **#5** (`attachment/recorded_bug_repros/flag_20260701_202347_149/`): *"the focusing rays varies from
  left to right. Some before defocus, some focus, some after defocus."*

Both are DISPLAY artifacts of the (working) folded trace, fixable without a vendor prescription. #2 is
the sampling-mode routing bug fixed here; #5 was the physics of the fold, resolved by the bugs/0197
rigid flip and now pinned by this bug's guard so it can't silently revert.

## #2 — Symptom, measured headlessly through the REAL production path

`_build_preview_system_rays_bundle` on the AZ85 scene (detector snapped to the image plane), on-axis
bundle (chief starts at the origin, reaches the +X arm past X=250):

| sampling mode | total paths | on-axis rays | mid-arm cross-section @ X≈148 |
|---|---:|---:|---|
| `world_envelope` (OLD, forced) | 279 | **31** | sparse points, foreshortens to a sheet |
| `world_cone` (NEW default)     | 3249 | **361** | **14.76 mm-wide 2-D disk** (2nd singular value 60.9) |

The incoming rays run +Z (X≈0, Z: 0→70), reflect at the mirror (Z≈70), then run +X (Z≈70, X: 0→296)
converging to focus at X≈296 — a genuine but SLENDER f/13 cone (±8 mm aperture over a ~220 mm arm).
At 31 golden-angle points that slender disk foreshortens from an iso view to a wireframe SHEET and
reads as a flat FAN. The same mirror-less sequential ELS-85 shows a dense cone because it revolves.
(Rendered contrast: `bugs/_0203_render_{envelope,cone}_{iso,downx}.png` — the down-X view is decisive:
a flat fan reads as a LINE, a real cone as a filled DISK.)

## #2 — Root cause: a promoted-mirror fold is misrouted to the branch-preserving envelope

The folded AZ85's promoted mesh mirror reads as an **"STL optical solid"** in `trace_intent`, so the
scene resolves to `use_nonseq = True` (NOT `use_folded`). It is **non-branching** (no beam splitter /
diffuse / probabilistic split). `_launch_pupil_prefers_meridional_fan()` returns False (the fold breaks
rotational symmetry), so BOTH `_preview_scene_sampling_mode()` and `_preview_3d_sampling_mode()` fell
through to their default `"world_envelope"`.

`world_envelope` exists to preserve the **per-branch sagittal width** of a BRANCHING scene (beam
splitter / diffuse double-pass): it scatters `Ray Count` (~31) golden-angle points across the pupil
AREA so each branch keeps its 2-D spread. A single fold has **no branch** — and, crucially, a
non-branching promoted-mirror fold is traced through its straight-equivalent SEQUENTIAL rows
(bugs/0197). So a revolved launch cone through the fold is provably just the **rotated sequential
cone**: each pupil ray is still traced individually through the fold, nothing is lost, and the
converged focus is preserved. The envelope was never needed here; it only cost density.

## #2 — Fix: route a non-branching promoted-mirror fold to `world_cone`

New predicate `_folded_scene_prefers_launch_cone()` in `services/trace_preview_sampling.py` (paired
with `_scene_has_promoted_mirror_fold()`, which detects an `OpticalSolidFaces` face whose `function ==
"Mirror"` — a bare tilt / decentre or a sequential `Mirror` surface does NOT count):

```python
def _folded_scene_prefers_launch_cone(self) -> bool:
    if self._is_full_pupil_mode():
        return False
    trace_state = self._resolved_trace_mode(system=self.__dict__.get("last_system"))
    if not (trace_state.get("use_folded") or trace_state.get("use_nonseq")):
        return False  # a plain sequential scene already revolves via the fan gate
    if (trace_state.get("has_beam_splitter") or trace_state.get("has_diffuse_scatter")
            or trace_state.get("has_probabilistic_nonseq")):
        return False  # branching: keep the per-branch area-filling envelope
    return self._scene_has_promoted_mirror_fold()
```

Both sampling-mode methods in `services/three_d_scene_tools.py` consult it before returning
`world_envelope`:

- `_preview_scene_sampling_mode()` (shared 2-D + Open-3D bundle) — after the `full_pupil` guard,
  before resolving the trace state.
- `_preview_3d_sampling_mode()` (Open-3D inspector) — after the `_launch_pupil_prefers_meridional_fan`
  fan check, before the `world_envelope` default. It keeps a 2-D disk pupil (not a 1-D fan) but
  revolves it densely.

`world_cone` revolves `count//2` rings × `_cone_azimuth_count` spokes (~361 on-axis rays) — the dense
structured cone any sequential scene launches.

### Scope / what is intentionally NOT rerouted

- **Branching scenes** (beam splitter / diffuse / probabilistic) keep `world_envelope` — the gate
  returns False on any of those flags, so the MV-150 folded-coaxial diffuse double-pass (bugs/0181–0184,
  penta phases 176–180) is untouched.
- **Full-pupil** mode still wins when explicitly requested.
- **Plain sequential** scenes are unaffected (they already revolve via `_launch_cone_prefers_flat_fan`,
  bugs/0161); the gate returns False when neither `use_folded` nor `use_nonseq` is set.

## #5 — the focus "varies left to right" was the per-ray `tau` shear; the rigid flip fixes it

`_apply_folded_mirror_rigid_reflection` (bugs/0197) applies ONE rigid reflection across the flip plane
(normal `d_out × s`) through the FOLDED fold point, replacing the OLD per-ray `tau` re-anchor. The
per-ray `tau` was a SHEAR on the 2-D cone: it landed the kink on the '/' face but dragged the focus
short and blew the on-axis waist to ~mm (rays reaching focus at different depths — exactly the user's
"some before / at / after focus"). Measured on the SAME rotation-folded bundle: **rigid flip endpoint
transverse RMS 0.83 µm vs per-ray `tau` 1535.5 µm.** Post-snap the wired on-axis cone lands at X =
295.577 (drawn detector 295.577, ΔX = 0.000) with ~0.83 µm RMS.

### Why the kink keeps a ~mm gap from the drawn hypotenuse (accepted tradeoff)

The KrakenOS mirror STATION sits ~12.5 mm before the mesh '/' centre (the cube's `desp_z`). No single
rigid map can both land the kink ON the mesh hypotenuse AND put the focus on the drawn detector — they
are 12.5 mm apart. Focus-on-detector wins, per the user's flag. (A candidate "Method Y" that re-derived
a per-ray landing to close the kink gap was rejected: it reintroduced the very shear #5 is about.)

## Verification (done)

- **`KrakenOS/UI/validate_open3d_ra_mirror_folded_cone_focus.py`** (new, standalone, display-free;
  exposes `run_checks() -> (ok, notes)`; run
  `.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_ra_mirror_folded_cone_focus`). Asserts
  on the live AZ85 editor: (1) **#2 routing** — `_folded_scene_prefers_launch_cone()` and
  `_scene_has_promoted_mirror_fold()` True, and BOTH `_preview_scene_sampling_mode()` and
  `_preview_3d_sampling_mode()` == `"world_cone"`; (2) **#2 density+shape** — the production `world_cone`
  on-axis bundle is DENSE (≥100 rays) where a forced `world_envelope` stays sparse (≤40) and is ≥3× it,
  AND the `world_cone` mid-arm cross-section is a 2-D DISK (2nd singular value > 0.5), not a collinear
  fan; (3) **#5 convergence** — the wired on-axis cone lands on the drawn detector (|ΔX| < 0.05 mm) and
  converges (endpoint transverse RMS < 0.05 mm); (4) **#5 rigid-vs-`tau` contrast** — on the same
  rotation-folded bundle the RIGID flip keeps that tight waist while the OLD per-ray `tau` SHEARS it
  (> 0.5 mm), so a revert to the shearing correction is caught.
- Registered as **penta phase 181** in
  `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py`; baseline
  `tools/penta_validator_baseline.json` hand-updated (`"181": "pass"`) per the phase-180 precedent (the
  full marathon segfaults under Xvfb llvmpipe, so the guard is verified STANDALONE and the at-risk
  cone/launch phases 117/152/153 were re-checked standalone — all pass; 176/178/180 fail standalone with
  a pre-existing Tk snapshot `__getattr__` recursion that also fails WITHOUT these edits, i.e. not a
  regression from this bug).

In-app eyeball still owed (headless cannot drive the VTK inspector).

## Follow-ups (deferred)

- The ~1.19× vs 1× FOV layout-conjugate question (bugs/0196) remains deferred.
- Quick Estimation across the fold (bugs/0197) still assumes a single straight axis.
