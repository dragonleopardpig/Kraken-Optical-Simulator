# 0447–0448 — Eyeball round 5 (recording_20260726_181001, 3 flags)

**Flag `flag_20260726_180523`: "rubberband selection + snap optical axis works perfectly."** — the
0433→0446 workflow is confirmed end-to-end. Two work items followed:

## 0447 — solve popup lost its 2+2 fold-leg pins (`flag_20260726_180738`, ref `attachment/FOV-solve.png`)

On the frozen/snapped BS scene the 0247-era conjugate splits vanished/mislanded: (a) the object
conjugate's fold vertex is the **BS coating** (deliberately not a mirror fold → split None); (b) the
image split's numbers looked right but its Solve mutated gap rows — sliding the breadcrumbed mirror
along **+Z instead of its leg** (station arithmetic on a baked row; `carry_free_placed_followers…`
no-ops with an empty override map). As built: object split falls back to the coating-plane crossing
(labels say *beam splitter*), image split carries world near/far + `frozen_world`, and both appliers
branch on it — image pin slides the frozen mirror along its incoming leg (sensor + camera re-seated
on its exit leg, breadcrumb intact); object pin slides **LED+BS** along the object axis and rigidly
translates the frozen chain. Classic live-fold scenes byte-identical. Penta 363.

## 0448 — "ray on": fragmented rays + phantom coverage rings (`flag_20260726_181751`)

**Fragmentation root (the 0433 slice-A deferred divergence, now fatal):** the engine composes tilts
in two orders — drawn/NS-mesh `Rz(−tz)@Ry@Rx` vs analytic-trace `Rx@Ry@Rz(−tz)`. For the baked
chain family (0,−90,−180) every frozen analytic row **traced facing backwards** (drawn local +Z →
(+1,0,0), traced (−1,0,0)) — rays refracted through reversed surfaces. Fix at the system-build
boundary: a breadcrumbed row with no solid mesh gets its mesh-convention rotation re-expressed into
trace-convention angles (`trace_convention_tilts_from_rotation_matrix`, exact to 2.5e-16). Post-fix
drawn==traced (+1.0) on every row.

**Phantom rings:** the imaging arm's synthesized branch detector sat at a garbage mid-chain focus
because only **4/279 rays** thread the frozen chain (the parked `nonseq_first_order_seam` — the
sequential PupilCalc aims the fan at the off-axis stop) and the vignette-dominated exit bundle
failed the 0093 pin. A reaching leaf with reach-fraction < 0.5 is now force-pinned to the designed
Image (normal from the surviving rays); the transmit arm's LED detector (0090 design — it shows
where the wasted arm goes) stays. High-reach arms (0097/0099/two-arm) untouched. Penta 364.

## Known-next

The launch-aiming seam is now the visible bottleneck: surfaces are honest but only a sliver of the
fan threads the frozen chain, so rays-on will look **sparse** until the universal first-order
reference (the `nonseq_first_order_seam` design note) is built. Expect that to be the next flag.

## Eyeball owed (round 6)

Rays-on: coherent object→BS→lens→mirror→camera path, exactly one ring at the camera + one at the
transmit arm; solve popup shows both bold-headed groups with BS wording; pinning each leg slides
the right bodies.
