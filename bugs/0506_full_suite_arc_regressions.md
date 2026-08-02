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
