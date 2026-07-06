# 0243 — Trace the REAL folded scene: first-surface RA mirrors, no display bend

## The report
`flag_20260706_161136_145` ("after setting FOV 55x55, still the same error.") and the user's
diagnosis, verbatim: *"Why the glass take part in the ray tracing again?"* / *"It is first
surface reflection or Outer reflection."* / *"nothing to do with the Glass!!!"* / *"the physics
engine and the UI out-of-sync or detached, the UI clearly shows the ray reflect in the air while
the underlying code trace through glass."* / *"the ray not even touches the lens surrogate, and
yet it can focus."*

All of it was one architecture defect: **the folded promoted-RA-mirror scene was never traced.**

## Root causes (three, stacked)

1. **The displayed rays were bent copies of a stand-in trace.** The preview traced a fictional
   UNFOLDED "straight-equivalent" system (mirrors flattened to plates on a straight axis;
   bugs/0197/0208) and then display-REFLECTED those rays about the mirror planes after the
   bundle was built, with reconcile/reseat snaps (bugs/0217/0239) papering the residuals. So
   the drawn rays reflected "in air" off a mirror the physics never saw, never intersected the
   Thin-Lens surrogates' folded poses, and "focused" wherever the snap put the detector.
   Every drawn ray carried `display_geometry_source=folded_straight_equivalent_reflected`.

2. **Why the stand-in existed: the ideal Thin Lens retroreflected in the real non-seq trace**
   (bugs/0187). KrakenOS's non-sequential loop carries directions in a SIGN-relative
   (pseudo-forward) convention — after a reflection `SIGN=-1` and the loop marches
   `ResVec*SIGN`. Snell physics answers in that convention; the ideal Thin Lens
   (`paraxial_exact_physics` + the `InterNormalCalc` focal-target construction) answers with
   an ABSOLUTE direction. Behind one fold the loop marched the lens's correct exit direction
   backwards — the retroreflection that made the real trace unusable and forced the stand-in.

3. **The folded Image/detector seat sat one mirror-thickness short of the prescription.**
   `neutralize_offbeam_inert_solids` (bugs/0065/0074, built for solids PARKED clear of the
   beam) classifies by lateral distance from the straight +Z axis — so a free-placed 2nd fold
   mirror sitting ON THE FOLDED ARM was "off-beam" and its row thickness was zeroed in the
   build specs. The output-port follower walk then advanced the exit frame by
   `thickness - pre_hit_run = -pre_hit_run` and seated the folded Image surface (and the
   detector target chain) a full plate short of the prescription station, while the QE/paraxial
   solve focused AT the prescription station. That standing gap is what the old reconcile
   hid — and what the user kept hitting as "still the same error" defocus.

## The fix

- **KrakenSys.py (both non-seq loops, main + branching):** after the physics call on a
  `Thin_Lens` surface, re-express the absolute exit direction in the loop's convention
  (`ResVec *= SIGN`). `SIGN=+1` scenes — every unfolded layout — are byte-identical.
- **KrakenSys.py `__VignetteTerminalCollect`:** a mid-chain aperture-stop vignette (bugs/0179)
  now collects a SHAPE-CONSISTENT terminal record. The old whole-empty `__EmptyCollect` record
  was only ever safe as a ray's sole record or under the branching tracer; mixed with real
  records it crashed `raykeeper.push` on numpy>=1.24 ("inhomogeneous shape"). RayKeeper's
  invalid-ray push also got a ragged-safe fallback (those lists are write-only diagnostics).
- **three_d_scene_tools.py / plot_refresh.py:** `_trace_preview_rays_folded_aware` now traces
  the REAL system for a folded scene — the same solids and surfaces the 3D view draws. The
  mesh mirror reflects FIRST SURFACE off the coated face's analytic plane (KrakenSys
  `force_reflection` + `external_reflection`: the beam never enters the prism glass), the
  lens/aperture/image rows are intersected at their folded output-port poses, and the rays
  come out of the trace already folded. The straight-equivalent TRACE, the display bend, the
  bugs/0192 reflection correction and the bugs/0217/0239 reconcile/reseat calls are retired
  from the pipeline (the paraxial straight-equivalent ROWS remain for first-order/QE math,
  where they are exact). 2D and 3D share the same trace.
- **offbeam_optical_solid.py `folded_beam_reached_mirror_fold_indices`:** walk the beam
  analytically (fold at each promoted mirror-fold face the leg crosses within
  `sqrt(area)+2mm` — the bugs/0224 rule); a REACHED fold mirror keeps its full spec
  (thickness included), so the follower walk seats the folded Image/detector at the TRUE
  prescription station. Genuinely parked bodies still neutralise exactly as before.
- **layout_polyline_display.py `_camera_track_image_plane_z`:** the camera STEP tracks the
  PRESCRIPTION plane again. The bugs/0220 focus-tracking special case existed to chase the
  detector that the 0217 reconcile had moved onto the waist; with the reconcile retired the
  detector sits at the prescription seat, so focus-tracking would re-detach the camera by
  the as-built defocus. Camera and detector now coincide always; a solve/snap moves both
  onto the focus together.

## Measured after the fix (AZ85 two-fold, display-free)
- Every drawn ray kinks ON both hypotenuse planes (max plane residual 9.8e-06 mm) and obeys
  the reflection law about the face normal (max residual 7.7e-08); no polyline vertex inside
  either prism wedge; no display-bend tags.
- Image seat == detector target == prescription station; rays terminate ON the seat.
- After `snap_detector_to_image_plane`, the on-axis cone focuses **stigmatically on the drawn
  sensor: transverse RMS 0.0000 mm** (313 rays through the real mesh mirrors + ideal lenses).
- The single-fold pipeline (bugs/0187 guard) runs on `NsTraceLoop` and converges at RMS
  0.29 mm on the folded Image seat.

## Verification
`validate_open3d_folded_real_trace_sync` (penta **phase 220**, baseline `pass`): real rays +
vignette-record push, first-surface kinks + reflection law, glass inert, detector termination
on the seat, lens-in-beam, and an unfolded ideal-lens byte-exactness regression. Stale guards
pinned to the old mechanism were updated to the new contract: 0187 (NsTraceLoop backend +
dynamic seat), 0188 (dynamic seat), 0191 (no dive can occur), 0192 (kinks native, no tags),
0194/0195 (self-consistent focus numbers: snap = paraxial = real-ray = −8.5179 mm; |m| = 1.0),
0201/0227 (2D real trace, no bend/reconcile), 0203 (focus ON the drawn detector), 0205 (raw
contrast dropped), 0208 (rewritten on the real two-fold fixture), 0217/0239 (native
coincidence, no snap), 0220 (camera tracks the prescription; post-snap camera=detector=focus),
0224 (prescription-seat constant), 0233 (same), 0242 (rays terminate on the seat), second-
mirror orientation fold (no tag). The branching-tracer / beam-splitter / branch-detector /
aperture-vignette suites all stay green (the KrakenSys edits are inert for SIGN=+1).

## Deferred (bugs/0244)
The QE folded FOV solve still mis-carries a free-placed trailing mirror whose pinned pose
encodes corner-spanning gaps (PYRITE 85: the solve leaves mirror2 mid-arm BEFORE the lens
block). The real trace now shows that inconsistency honestly instead of painting over it;
fixing the solve/carry arithmetic is the follow-up.
