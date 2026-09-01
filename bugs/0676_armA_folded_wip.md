# 0676 — om05a ARM-A FULLY-FOLDED scene (WIP checkpoint) + device cube

User flag_201424 item 4 / "Proceed next": the real prism assembly + 3D cube device +
the Prism_Assembly.png ray story.

## Landed

1. **Device cube** on `attachment/om05a_folded.py`: the inspection part (0661)
   enabled — 70 × 20.6 × 57.8 box with its active face ON the object plane, six
   blow-out axes. The "3D cube device" ask.
2. **`attachment/om05a_folded_armA.py` — the REAL five-fold chain traces**
   (`bugs/0676_build_armA.py`): the three prism folds are now REAL free-placed
   clean wedges (through-glass: normal entry, flagged-hyp reflection, normal
   exit — constant-path like the real TIR prisms) and both mirrors re-seated
   first-surface in the arm-A world. World = CAD mapped by
   scene=(−x,−y,z)_CAD anchored at device face A; every fold plane derived from
   CAD; tilts picked by the pure-math scan (now including tilt_y for the
   x-plane mirror folds). **The chief folds all five legs:
   +z → +y → −z → +y → −x → −y** — the slide's green path, in-scene, traced.
   68/243 rays reach; image refocused ONTO the convergence (y −11.00).

## Open (next session picks up here)

- **Launch-probe apertures again**: replacing the Ø80 plates with wedge solids
  dropped the launch to 243 paths (was 729) and the per-field rms to 156 µm
  (scattered aim, the bugs/0673 wide-first-aperture sensitivity). Likely fix:
  hidden Ø80 AIR aperture rows at the ladder head (they exist but sit BETWEEN the
  wedge rows now — try one BEFORE the first wedge), or root-cause the aim probe.
- Centre wedge is 12 mm (half of 4338A's 24) vs the ladder's 18 mm glass slot —
  refocus absorbed the difference; consider matching the ladder to 12.
- Housing decoration: with real folds the assembly housing chunk FITS — extract
  (9 components above mirror1, minus prisms) and seat by the same map.
- Fields for one face (face A centred at origin): field 1.9 × 3 instead of the
  tunnel's 4.3; per-face patch semantics.
- Guard + phase; renders; docs.
