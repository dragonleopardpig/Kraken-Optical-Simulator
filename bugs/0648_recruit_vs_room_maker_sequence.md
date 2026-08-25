# 0648 — the 0645 recruit vs the 0573 room-maker across consecutive solves (OPEN)

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
