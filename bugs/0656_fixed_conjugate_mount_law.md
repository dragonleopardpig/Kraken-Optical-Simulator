# 0656 — A fixed-magnification lens MOUNTS to the camera; FOV is stated, never solved

**flag_20260827_140507:** "this 0.75X telecentric lens supposed to get FOV 11.7x8.8. I
think the FOV pop up dialog should have option to let user to somehow no need to input
FOV for this kind of fixed magnificaiton lens. Anyway, I entered the FOV after swapped
lens pop up, the lens crash inside the camera, it should directly mount to the camera."
Screenshot: the solve delivered 0.753× optically — with the barrel ~30 mm THROUGH the
camera front.

## The mount law

A C-mount telecentric is fully determined; nothing is a choice:
- object at the vendor WD (110 mm to the rim);
- BOTH principals coincident at f(1+1/m) − WD behind the rim (54.3 mm) — the 0653 EFL
  derivation IS the coincident-principal identity;
- sensor at the mount flange, FFD (17.526) behind the housing rear — where the camera
  screws on. FOV = sensor/m, full stop.

## What was wrong

1. The 0647 refit pinned only ppa and PRESERVED the builder's ppp — the rear principal
   sat elsewhere, so best focus ≠ the flange plane, and the FOV solve legally focused
   the sensor inside the barrel's mount overhang (the "crash").
2. First fix attempt: pin ppp = ppa − span through `solve_two_thin_groups`. **Scar:**
   two thin groups have HH′ = −f·d²/(f₁f₂) — exactly zero is DEGENERATE, and the
   solver silently returned a best-effort that regressed the WD mismatch to 15.3 mm.
   Lesson: outcome-check every solver result (the refit now recomputes ppa from the
   solution and refuses if it missed the law by >0.05).
3. The fix: the fixed-conjugate refit CONSTRUCTS the honest shape directly — full
   power in group 2 AT the principal station, group 1 a near-flat window (f₁ = 1e5 →
   |HH′| ~4e-5 mm) — and writes the library image gap onto the flange plane.

## The flow now

- Import: object 110.0, HH′ = 0.0000, image at rim+L+FFD = 177.536 exactly.
- Swap: object leg set to the vendor WD (unfrozen scenes); the existing auto-refocus
  lands the sensor at the flange (same plane as best focus now) and the camera glue
  seats the body there — measured lens-rear→camera-front gap +1.53 mm (the STEP's
  4 mm C-mount thread screws INSIDE the camera; the shoulder butts at the sheet's
  160.01). MOUNTED, not solved.
- The post-swap prompt STATES "Fixed 0.75x — FOV = sensor/m, nothing to enter"
  instead of opening the dialog (the user's ask).
- `fov_solve` on a fixed-magnification lens: a foreign field REFUSES honestly and
  moves nothing (0572 doctrine); the lens's own field confirms focus idempotently.

Note: the spec's "FOV 11.7×8.8" is at the max 2/3" sensor; with a different camera the
honest number is that camera's sensor/m — which is exactly what the machine states.

## Verified

Guard `validate_open3d_0656_fixed_conjugate_mount_law` (penta phase 492): import
invariants (A1–A5), the flagged swap flow incl. the mount gap + refusal honesty
(B1–B5), wiring (C1–C4). Guards 0647/0653 regression-green.

## Open (noted, not shipped)

The surrogate's stop sits between the groups, not at the rear focal plane — chief
rays are not drawn telecentric (parallel in object space). Display fidelity only;
conjugates/FOV are exact.
