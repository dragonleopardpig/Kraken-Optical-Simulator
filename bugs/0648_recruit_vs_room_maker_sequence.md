# 0648 — the field-fill secant explodes on a flat slope; probes blind; machine torn apart (FIXED)

## Root cause (runtime repro, sequence AND direct-55 both degrade)

The 35→55 "sequence interaction" framing was wrong — the DIRECT 55×55 after the PYRITE
swap degrades identically. Decoded from the pass log (numbers exact):

- pass 1: request 24.11 → measured 18.91; pass 2: request 20.77 → measured 18.40
  (healthy, converging: the multiplicative step would book 18.39 next).
- The SECANT saw slope (18.40−18.91)/(20.77−24.11) = **0.153** — near-flat, because the
  arm/snap machinery reshapes the geometry between bookings, so `measured` is not a
  clean function of `request`. It extrapolated request → **6.889** (−67% where −11% was
  needed). The 0626 step cap `10·|error|·target` scales WITH the error: at a 13%
  residual it allowed a 21 mm step — the absurd secant (13.8 mm) passed.
- Request 6.889 demands |m| ≈ 2.4 → the booking legally slid the fold arm **+321 mm**
  (post-0645, refusals that used to stop the loop now succeed via retry/recruit/
  make-room), the ruler probes went blind (0/91 landed at fractions 0.7/0.35), and the
  fraction-shrink scale-up fabricated "delivered semi 92.77 mm" on a 16.3 mm sensor —
  which the refinement then chased (make-room to far=604 mm). Restore-best kept the
  last healthy pass: the observed 69.59 vs 77.78 readout.

## Fix (two independent bounds, both in quick_estimation.py)

1. **Trust region around the multiplicative step** (replaces the error-scaled cap): the
   step `request·target/measured` is direction-correct and ~error-sized at EVERY error
   scale; the secant may refine within twice its reach (legitimate slopes 0.5–2 pass;
   collapsed slopes cannot), else the multiplicative step is taken.
2. **Ruler plausibility bound**: a scaled-up "delivered semi" beyond 2× the sensor's
   own semi-diagonal is not a measurement — return unmeasurable (None), so the
   refinement lands on its best verified state instead of chasing fabrications.

Guard 0573's stale mechanism pins updated to claims-match-motion contracts (B2: "Made
room first" appears exactly iff the mirror really moved >1 mm; B5: the mirror may stay
put or slide either way ALONG the leg, never off it) — the 0645 machinery legitimately
reaches some fields without the room-maker.

---

# Original triage notes (superseded above)

Caught by guard 0573 on the final 0647 tree (Apo75 + PYRITE 45-85 swap scenario):

- **35×35 first**: the solve now succeeds WITHOUT the 0573 room-maker ("Made room first"
  absent, fold mirror net dx 0.000) — the 0645 snap recruit/retry converges the sensor
  within the existing budget. The field IS delivered (B3@35 passed), so this is a stale
  MECHANISM pin, not a defect: guard 0572's B-section already learned to disable the
  recruit explicitly (`editor._recruit_image_fold_near_leg = lambda amount: 0.0`) when it
  wants to simulate "no room available"; 0573's B2/B5 need the equivalent update — the
  essence of the contract is "the field is reached with legal geometry and the user is
  told what moved", not "this one function did it".
- **55×55 after the 35×35 (same session)**: the room-maker DOES run (B2/B5@55 passed),
  but the delivered FOV readout lands at diag 69.59 vs the 77.78 requested (−10.5%) —
  a REAL regression. The 55×55 solves fine on the as-loaded lens (B-1/B-2 passed), so the
  interaction is with the 35-solve's end state (recruit/restore cycles + learned
  correction) handicapping the subsequent larger-field solve.

NOTE: this regression entered with 0645 (commit 3627345b, already on the remote) — the
0647 work does not introduce it. Triage next: repro probe = fresh swap → solve 35 →
solve 55 with per-pass `field-fill pass N` + `snap detector iter` debug captured; find
what the 35 leaves behind (mirror position? learned correction? section pins?) that caps
the 55's refinement at 69.6.

Honesty gap to close alongside: when the snap recruits during a solve, the SOLVE message
must say the fold mirror moved (today only the snap's own status line carries it, and the
solve epilogue overwrites it).
