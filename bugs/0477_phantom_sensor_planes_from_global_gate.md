# 0477 — two phantom sensor planes, because one arm's label gated every other arm's draw

Flag `flag_20260729_185450_727` on build `69426d5b`, scene
`attachment/machine_vision_AZ85_RA_Mirror_BS.py`:

> remove defocus introduce 2 unwanted sensor planes (orange)

Third time this family has been reported — `flag_20260729_120601` was
*"there are still 2 additional sensor planes (orange color). There are no camera why there is
a sensor?"*, which bugs/0464 answered.

## What the two plates are

NOT new rows and NOT stale actors. They are the beam splitter's two OTHER terminal leaves,
synthetic rows **100001** and **100002** (`S3:S3/transmit -> S3:S3/reflect` and
`S3:S3/transmit -> S3:S3/transmit`). They exist in every refresh as ray hard-stops, and
`dets = 3` in every state, good and bad. Orange is the detector active-footprint overlay
(`three_d_scene_tools.py:3199`, `(0.98, 0.45, 0.05)`), skipped only when
`metadata["draw_suppressed"]`.

Their own rays never changed. Measured across as-loaded, post-FOV and post-snap, and at FOV
20/30/40: **reach = 0 of 279 rays, `reaches_image` False, every time.**

## What actually changed

A scene-GLOBAL boolean derived from a DIFFERENT arm.

    scene_builder.py   _scene_has_real_sensor_arm = any(focus_source == "reached_image"
                                                        or assigned_camera_label)
    scene_builder.py   suppress an arm  <=>  _scene_has_real_sensor_arm
                                             and focus_source != "reached_image"
                                             and no assigned camera

`focus_source` conflates two different facts: *"this arm's rays land on the designed Image"*
and *"we could not trust this arm's convergence, so we force-pinned its plane to the Image"*.

The imaging leaf `S3:S3/reflect` has a vignette-contaminated exit bundle — only ~50-63% of its
279 rays reach the detector, and the least-squares closest-approach point of the FULL bundle
sits at (229.568, 0.120, 90.957) with mean direction (0.512, 0.000, -0.859): inside the prism,
~31 deg off the real landing beam. That point is garbage, and it is **byte-identical before and
after the snap**. What normally saves the scene is the bugs/0099/0100 `reliable_forward` window
at `branch_detectors.py:459-464`, which rejects it and pins the leaf to the Image.

"Remove defocus" moved the designed Image **+62.08 mm** (row 7 thickness 18.86 -> 80.9399)
*toward* that stale point:

    to_image   98.706 -> 45.373
    behind    -72.695 -> -19.362      window (-22.686, -1.0)

`behind` slipped inside the window, `reliable_forward` became True, the leaf stopped being
pinned, `focus_source` stayed `"converging_rays"` — and the scene-global flag went False,
un-suppressing every camera-less arm at once.

So the gate answered "is some OTHER arm labelled as having reached the Image?" when the
question it needed to answer was "do THIS arm's rays reach the Image?".

## Fix

`reaches_image` is already computed in the derive loop (`branch_detectors.py:361`, from
`_leaf_reaches_existing_detector`). Carry it as `BranchDetector.reaches_designed_image`, expose
it in the scene-target metadata, and have both gate sites read it instead of `focus_source`.
Measured stable across the snap, so the phantom arms stay suppressed either way.

The two gate decisions were also **extracted as pure functions** —
`scene_builder.scene_has_real_sensor_arm(branch_detectors)` and
`scene_builder.branch_detector_draw_suppressed(...)`. They had to be reasoned about from a
rendered screenshot twice; now they are testable without building a scene.

Deliberately untouched: the `lone_dead_end_arm` (bugs/0451) and `illumination_flood`
(bugs/0285) clauses still key off `focus_source`. Those ask a different question and are
guarded by phases 372 and 251.

### A real bug the extraction caused, and how it surfaced

The first extraction referenced `_branch_path_draw_suppressed` at module scope, but
`build_scene_bundle` imports it **locally**. The resulting `NameError` was swallowed whole by
the block's `except Exception: branch_detectors = []`, which silently dropped EVERY branch
detector — phases 0464, 0451 and 0448 went from PASS to FAIL with no traceback anywhere. Fixed
with a local import. Worth remembering that this bare except turns any error in that block into
"the scene simply has no branch detectors".

## Verified

`KrakenOS/UI/validate_open3d_0477_phantom_sensor_planes.py`, display-free, driving the extracted
gates directly. Penta phase **385**.

    PASS A1  BranchDetector carries reaches_designed_image
    PASS B0/B1/B2 [pinned and unpinned]  imaging arm draws; both phantom arms stay suppressed
    PASS C0  the scene-global flag is STABLE across the label flip
    PASS C1  a phantom arm's draw is UNCHANGED when the imaging arm's focus_source flips
    PASS D1  a two-CAMERA split still draws BOTH arms (bugs/0090)
    PASS E1  a scene with no real sensor arm still draws its detector (bugs/0464 control)
    PASS F1-F5  scatter / lone dead-end / flood / scatter-token terms unchanged

Reverting BOTH gate sites to `focus_source` fails B0, B2, C0 and C1 — with **B2 drawing the
phantom arms**, the reported symptom exactly.

Regression-checked against every branch-detector guard: 0464, 0451, 0448,
detector_redundancy_drop, branch_detector_supersedes_image, superseded_image_plane_hidden all
PASS. `branch_detector_leak_clutter` (phase 180), `branch_detector_scatter_clutter` (phase 178)
and `illumination_flood_phantom_branch_detector` fail both WITH and WITHOUT this change —
pre-existing, tracked separately.
