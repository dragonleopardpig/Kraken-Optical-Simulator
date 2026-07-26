# 0443–0445 — Eyeball round 3 (2 flags): FOV plate tilt, BS rotation ghost, first-surface split

Flags on build `478ede02`/`ea3d4aa0`, continuing bugs/0433→0442. The round-3 loop itself worked —
chain snapped at the click on the split leg, camera translate-only onto the frozen-fold guide,
object plane drawing — with three findings:

## 0443 — "everything almost work except now the FOV plate is tilted" (`flag_20260726_153531`)

The detector-coverage `object_axis` was derived as *row 1's world point − the object's* — correct
while row 1 sat on the source axis (every walk-folded scene), but on a 0433-frozen/snapped chain
row 1 is a baked off-axis row: the axis measured `[0.461, 0, 0.888]` (~27°) and the green FOV
rectangle drew tilted. **Fix:** the axis is +Z rotated by the OBJECT row's own tilts (the object is
never frozen/snapped; 0432/0436 exclude it), legacy row-1 derivation kept as fallback only.
Guard `validate_open3d_0443_object_fov_axis` (penta 359).

## 0444 — "residual ghost plane" after rotating the BS (`flag_20260726_153723`)

**Not reproduced headlessly**: every reachable rotation path re-poses every plate actor family
cleanly (full renderer census — zero stale/untracked/duplicated actors). The healthy contract is
the guard (penta 360). To pin the live culprit: close the app (recordings flush on close) or flag
again **with the ghost on screen and the BS selected**. Found en route, both fixed:
- **0442 gap**: the delete's spacer claim called `_is_inpath_trailing_spacer` through `getattr` —
  but that method is NOT in the editor's MRO (the 0319 wrapper trap), so the branch silently never
  ran and the spacer was orphaned; also the BS row insertion breaks +1 adjacency. Inline predicate
  + scan past station-neutral rows; the full 90.135 mm span now returns.
- The step-rotation gizmo path is dead for a promoted BS (`_step_path_for_label('optical')` is
  None post-promotion) — mildly misleading dead gesture, noted.

## 0445 — the reflecting surface sat on the SECOND surface (user decision + kernel fix)

The coating pick tied on `abs(dot)` between the plate's two diagonals, landing arbitrarily — the
user had to rotate the plate. **User decision (AskUserQuestion): object-facing default.** Applying
it exposed a kernel defect that had always lurked under first-surface splits:
`__NsTraceSplitChildSkipSurface` gave the ENTRY-face split's transmit child a row-level skip, so
after refracting INTO the glass it could never hit its own exit face — it died inside the solid
(`no_next_intersection`), the branch map collapsed to 2 rows, and `_branch_traced_row_frames`
sampled the doomed in-glass segment as an unphysical −38 mm/−7.4 y frame walk. **Fix:** an
entry-face split returns no skip (the same reasoning that exempts the cube's internal cemented
diagonal; the reflect child leaves the solid so the zero-distance re-hit cannot occur); far-face
splits byte-identical. Post-fix BOTH coating choices produce the same canonical structure
(transmit carries the full chain, power ≈0.467, `target_termination`; reflect ≈0.5 along the
seat's fold) — **phases 347 and 26 pass unchanged, no re-cut needed**. The 0444 guard now asserts
object-facing as contract. Guard `validate_open3d_0445_first_surface_split` (penta 361).

Note: the auto-seat on this LED folds +Z→−Y (the side window faces Y) — the user's +X layout comes
from their manual plate rotation.

## Open

- The live ghost (needs the flushed recording or an on-screen flag).
- The promoted BS row is an ordinary rubber-band/snap candidate — consider excluding it like the
  Object row before a box over the LED region drags the BS into a chain snap.
- Round-4 eyeball: BS add lands the coating object-facing (no manual rotation needed), FOV plate
  faces the source axis, spacer no longer strays in the table after a delete.
