# 0506 — four phases regressed somewhere in the 0434→0505 arc (first full suite since Jul 25)

The 2026-08-02 baseline re-cut (408 phases, 372 pass) is the first FULL marathon since the
2026-07-25 re-cut; the whole 0434→0505 arc shipped on filtered smoke runs. Four phases that
passed in the July baseline now fail deterministically on a clean tree (re-verified individually,
independent of tonight's changes — they fail with and without the 0500/0503/0504/0505 commits'
subject areas):

* **Phase 0 — load 5-penta-prism cascade**: trace gives 13 ray paths but **0 folded axis
  segments** (expected >= 2 for a 5-prism fold). The founding cascade phase; likely an axis-record
  or segment-counting change in the fold-axis arc.
* **Phase 178 / 180 — diffuse double-pass detector clutter (2D full-3D)**: branch-detector
  hard-stops are kept but **0 footprints / 0 branch planes are drawn** where the guard expects the
  clean-scene draws; the scatter/clean draw-gating flipped somewhere (0495's detector-fitting work
  is the nearest neighbour).
* **Phase 382 — camera sensor seats on the Image row (0471)**: seat lands 11.4 mm from the sensor
  vs the expected 11.5 mm — a 0.1 mm drift past the guard's tolerance; lateral seat and clearance
  still pass. Uses vendor lens fixtures (not the user's scene).

These four are IN the new baseline (the gate only blocks fresh PASS→FAIL flips), so this note is
what keeps them tracked as regressions to root-cause rather than silently absorbed environment.
Phase 10 (analytic lens selection not all-red), failing since July, now passes — fixed by the arc.

## Update 2026-08-02 (post-0507)

**Phase 382 RESOLVED as a side effect of the 0505/0507 station work** — the camera-seat guard
measures against traced geometry, and the nominal-anchored follower probe / static launch aim
were what had drifted it 0.1 mm. Full 408-phase run after `ebaaf226`: zero new failures, 373
pass. Remaining from this arc: phases 0 (cascade axis segments) and 178/180 (diffuse double-pass
detector draw-gating).

## RESOLVED 2026-08-03 — three display regressions, all in one masked window

**Phase 0** (cascade: 13 paths, 0 folded axis segments): bugs/0439's frozen-mirror
classification -- "a promoted fold mirror that is not an active override source" --
misfires on the penta cascade, where the geometric walk is legitimately empty
(system=None, no explicit ports): all five prisms classified "frozen" and sprayed
single-reflection diagonal guides (wrong geometry for a two-reflection penta), and
bugs/0464's supersede then treated those as scene guides and wiped the CORRECT traced
chief-ray segments. Fix: frozen classification additionally requires the 0433 baked-pose
breadcrumb (`ScenePlacement.stay_put_freeze` / `last_axis_to_axis_move`).

**Phases 178/180** -- this doc's original summary MISREAD the failing check: it was the
bounded-extent assertion (`max|x,y| 318 > 150`), not the footprint draws. Two 0459/0464
interactions: (a) 0459's `hit_detector` clip exemption extended to scatter/ghost branches
whose far-parked synthesized detectors exist precisely to bound them; (b) the 15-ray
leak path ESCAPES, and its diagnostic tail (`min(radius*1.25, 600)` ~312 mm) sails past
every plane's radial capture once 0464 sized planes to their beams. Fix in
`bounded_ray_points_for_scene_display`: a SUPPRESSED branch (per-path scatter/internal
bounce, or ANY non-primary branch once the scene has diffuse scatter -- the 0184 rule)
keeps the first-plane hard-stop clip AND caps its escape tail at a 75 mm stub (the 0182
bounding contract); a clean imaging arm keeps the full 0459 behaviour. `branch_path` +
`scene_has_diffuse_scatter` threaded through both display paths and the measuring guards.

**Bisect lesson**: both phases bisected to `b727b7ac` (the Physics-package birth) --
technically the first bad commit, but only because its module/package shadowing kept the
whole Jul-29 day red, masking 0459/0463/0464 landing inside it. Fix-then-rebreak
histories defeat monotone bisection; the Physics migration itself is clean at HEAD
(optics.py byte-identical to the legacy module, no export collisions).

Verified green: phases 0/178/179/180, scatter/leak/internal-bounce clutter guards,
0459 rays-to-sensor, detector hard-stop, optical-axis scatter, the 0433/0505/0508
frozen-guide family. Pre-existing failures confirmed NOT from this arc (clean-tree A/B
on X299): `validate_2d_3d_projection_sync` (known penta vendor-mesh, June) and
`validate_open3d_traced_rays_always_visible` (folded stopped/missed visibility).
With phase 382 healed earlier by 0507, **bugs/0506 is CLOSED**.
