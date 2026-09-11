# 0781 -- one Solve FOV may not trace the same scene twice

> "after clicking apply + solve FOV, it takes ages to trace."

## Measured

One Apply + Solve FOV on `attachment/om05a_folded_80mm.py`, 21x21x1 device, default FOV, 3D window
open, build 40d35e2f, every `_build_preview_system_rays_bundle` call counted with its caller chain:

| step | wall time | full traces |
|---|---|---|
| Apply (`set_inspection_part_spec`) | 40.4 s | 1 -- the 3D refresh, 38.2 s |
| Solve FOV (`solve_fov_to_inspection_face`) | 237.8 s | **4, 163.6 s** |

The four solve traces are all focus measurements:

| # | time | caller | added by |
|---|---|---|---|
| 1 | 43.3 s | `_finish_solve_on_traced_focus`: the residual before the snap | bugs/0490 |
| 2 | 36.6 s | `snap_detector_to_image_plane`: the defocus before its write | bugs/0764 |
| 3 | 43.3 s | `snap_detector_to_image_plane`: the defocus after its write | bugs/0764 |
| 4 | 40.4 s | `_finish_solve_on_traced_focus`: the residual after the snap | bugs/0490 |

The solve's message was "Focus: residual +0.09445 mm -- already at the traced focus, so the snap left
the sensor where the solve put it": the snap wrote a move, measured it worse, and restored the
snapshot.

## Which traces re-trace an unchanged scene

An independent read-only review (six agents; each lens re-checked by a second agent against the code
at 40d35e2f):

- **#1 -> #2: the same scene.** Between them the snap only reads (the first-order split, the
  paraxial image plane, row snapshots). One caveat the verifier found: the snap's history capture
  re-syncs face-bound scene sources, which can change a trace input when such sources exist and
  their faces moved. om05a has none.
- **#2 -> #3: a changed scene by construction** -- the write. #3 is the only measurement of it.
- **#3 -> #4 on the revert path: the scene #1 traced.** The restore puts back thickness, desp and
  STEP offsets on every row, and the glued-unit pose restore then writes nothing.
- **#3 -> #4 on the keep path: depends** on whether the snap's tail writes something the trace reads
  (the glued LED+BS pose, an Auto image diameter).

So on om05a's path #2 and #4 -- 77 s -- measured values already in hand.

## Why explicit reuse and not a trace cache

The same review looked at caching `_build_preview_system_rays_bundle` itself and found it unsafe to
do simply: an `update_state=False` build still writes editor state (`_last_scene_bundle`, the focus
readout, band image strips), its products are mutable and edited after the build, the existing
`_preview_trace_signature` omits real inputs (learned fold corrections, sampling mode, the STEP-native
row swap), and most geometry writes never set the dirty flag. A stale trace is this product's worst
failure mode, so the fix is the narrow one.

## The fix

A measured value is handed forward only while a content fingerprint of the trace's inputs is
unchanged; any difference, or any doubt, means measuring exactly as before.

- `ParaxialToolsMixin._traced_focus_state_fingerprint()` hashes every row field, the saved layout
  settings minus the bands' image strips (a trace WRITES those), the STEP placement offsets, the
  scene source specs, the learned fold corrections, the sampling mode, the wavelength, the
  illumination-rays switch and the preview ray cap. It returns `None` -- never reuse -- with energy
  probability on (unseeded random numbers in the tracer), with a fold relearn pending (a launch can
  re-trace and rewrite the correction), with a forced or overridden preview sampling the next build
  consumes, and on any error. It is over-inclusive on purpose: an extra input only costs a reuse.
- `_finish_solve_on_traced_focus` fingerprints before and after #1 and offers #1's signed residual to
  the snap only when the build itself changed no trace input. Afterwards it uses the snap's
  recorded residual instead of #4 while the fingerprint still matches, and traces otherwise.
- `snap_detector_to_image_plane`, non-frozen branch:
  - takes the offered "before" when its fingerprint still matches, and measures otherwise;
  - snapshots the traced focus readouts (`_focused_image_plane_info`, `_last_scene_bundle`, the
    bands' image strips, ...) before its write;
  - on a revert restores them along with the rows -- the after-trace left them describing the
    rejected write, and nothing re-traces the restored scene any more -- and records the pre-write
    residual (the offered one, or its own measurement) under its fingerprint;
  - on a kept write records #3's signed residual, which the shared tail hands on only if nothing the
    trace reads changed in the meantime (the glued LED+BS pose restore, the table sync).
- `_traced_snap_defocus_magnitude` records the signed shift whenever it came from the traced bundle.
- The frozen branch is untouched. It records nothing, so the finisher still traces #4 there.

## Found alongside, not changed here

The review also located the rest of the Solve's time, none of it inside the four counted traces:

- the solve's closing `refresh_plot` (layout_table_workbench.py) runs a FIFTH full trace of the
  final scene, directly rather than through the bundle builder;
- `_in_focus_fields_at_current_track(samples=240)` re-derives the same magnification-independent
  first order hundreds of times before any move, and its result is discarded on this path;
- `_lens_datasheet_wd_registration` re-parses the lens folder's PDFs on every solve, uncached.

## Verified

Re-profiled live on the same scene, device and 3D window:

| | before (40d35e2f) | after |
|---|---|---|
| Solve FOV | 237.8 s | **154.9 s** (-82.9 s, 35%) |
| full traces inside it | 4, 163.6 s | **2, 84.9 s** |
| snap_detector_to_image_plane | 84.1 s | 47.1 s |
| the solve's reported outcome | "residual +0.09445 mm -- already at the traced focus" | identical |
| Apply | 40.4 s | 39.6 s (not targeted) |

The two traces left are #1 (the residual before the snap) and #3 (the snap's measurement of its own
trial write).

Related snap and solve guards, run one at a time:
- **Pass:** 0764, 0515, 0566, 0594, 0645, 0574, 0580, 0719, 0718, 0478, 0476, 0511, 0520, 0528, 0529,
  lens-swap auto-refocus, camera-tracks-folded-focus, RA-mirror folded cone, QE object lock,
  field-resolved surrogate, 2D folded rays.
- **Skip:** 0470, 0571 and 0570, whose beam-splitter scene is not in the checkout.
- **Fail, and pre-existing:** `folded_image_snaps_to_ray_convergence` (two-mirror: no sensor-reaching
  on-axis rays), `2d_layout_matches_3d_focus` (SHARP/NATIVE) and `model_change_marks_2d_stale` (two
  inspector methods). All three fail identically on 730ea7db without this change, run in a worktree
  with the real attachment assets.

## Guard

`KrakenOS/UI/validate_open3d_0781_solve_does_not_retrace_an_unchanged_scene.py`, penta phase
**564**. It drives the REAL finisher and the REAL snap on a stub host whose traced measure counts its
calls and writes the focus stashes a real build writes. Run against 40d35e2f it FAILS where it
should -- no fingerprint, 4 traces on the revert path, 4 on the keep path -- and passes everything
that must not change (the reported residuals, the bugs/0764 revert, a stand-alone snap measuring
twice).
