# 0645 — Magnifying FOV solve: focus behind the fold mirror, sensor never moved, solve claimed focus anyway

**Flags:** `flag_20260824_201012_781` ("original", in focus) + `flag_20260824_201312_282`
("solved for FOV 20x20, image side ray defocus"), scene `attachment/machine_vision_ELS85.py`,
build 714d447c.

**User demand (the arc's point):** "This happened many times in the past. After fixing a
specific .py file, the other .py file repeat the same problem. Please check all imaging lens,
please provide general solution rather than specific one."

## Measured

Reproduced headless, exactly as flagged: after `fov_solve 20x20` (a MAGNIFYING conjugate,
|m| = 1.152 — the never-tested regime; every prior flag was demagnifying) the census went
247/0 → 174 target / 72 missed_image, per-pencil RMS blur 0.0 → mean 3.57 mm, and the sensor
moved **0.0000 mm** — while the solve reported *"Focus: residual +82.65 -> +82.65 mm (snapped
to the traced focus). Delivered field VERIFIED…"*.

`bugs/probe_0645_els85_focus_scan.py` (the 0576 method — scan the sensor along its folded leg,
measure real traced axial spot RMS; the as-loaded scene is the control and its minimum sits
exactly at the sensor):

- post-solve, blur is **monotone toward the fold mirror** across the whole bookable leg;
  extrapolating the slope to zero blur puts the focus at world far **−23.5 mm** — behind the
  fold mirror. No sensor position on the exit leg can reach it.
- `_snap_detector_refusal` held *"best focus could not be reached from here … the scene was
  left untouched"* — recorded, and ignored by the solve message.

## Root causes (all in the SHARED snap/solve pipeline — no scene is special)

1. **The 0570 pre-flip guessed, didn't measure.** A target exit leg going negative was taken
   as *proof of a sign error* (true on the 0570 Pyrite85 case). Here it was genuine
   unreachability, so the flip drove the sensor +82.65 mm the WRONG way; the residual grew to
   +165.31 (≈ 78.05 + 82.65 — the measure was honest, the direction wasn't).
2. **The 0515-B2 adaptive flip was dead code.** The 0577 divergence guard reverted-and-broke
   on the first non-improving pass — before the flip it was built around could ever run.
   Net effect: one wrong pass, revert, exit. Sensor never moves.
3. **No geometric remedy existed** for a focus that lies before the fold point. The remedy is
   not another sign: slide the fold mirror back toward the lens along its incoming leg
   (`_apply_folded_image_split("near", …)` — near shrinks, far grows, total and therefore the
   focus unchanged, bugs/0447's repackaging) until a positive exit leg exists.
4. **Dishonest reporting, twice.** `_finish_solve_on_traced_focus` said "snapped to the traced
   focus" unconditionally, and the solve's `image_deferred` branch hard-coded "the sensor was
   placed at the traced focus" — both while the recorded refusal said the opposite.
5. **(Latent) the 0577 revert snapshot was rows-only.** The settle's clause (i) walks the
   camera BODY with the sensor by writing its STEP placement offset, so a reverted pass could
   strand the body at the failed pose. Now snapshots rows + STEP offsets (the 0626 mechanism).

## Fix (`scene_placement_commands.py` snap loop + `quick_estimation.py` finisher)

- One **measured retry**: on the first non-improving pass, restore best, flip direction,
  continue; only the second failure declares divergence (the 0577 guarantee stands).
- The 0570 pre-flip is the **first hypothesis only** (gated off after the retry); a
  still-negative target then **recruits the near leg** via `_recruit_image_fold_near_leg`
  (clamped to the split's collision floors; partial recruitment books the closest reachable
  point and records the remainder in `_snap_detector_unreachable_mm`).
- Honest claims: the finisher's "snapped to the traced focus" is gated on the re-measured
  residual (≤ 0.5 mm); otherwise it reports "closest reachable focus" / a WARNING with the
  out-of-reach remainder; the solve prefix now states intent, not outcome.

## Verified

- ELS85 20×20 (the flagged case): residual +82.65 → **+0.0004 mm**, refusal empty, scan shows
  an interior blur minimum at the sensor (RMS at sensor ~0.2 mm = the aberration floor; was
  3.57 mm defocus). The as-loaded control is untouched.
- `tools/sweep_0645_fov_solve_focus.py` — the user-demanded general witness: every
  `attachment/machine_vision_*.py` scene solved in BOTH regimes (|m| ≈ 0.42 and ≈ 1.15,
  one app per process); contract per case: **FOCUSED** (spot RMS ≤ 0.25 mm) or
  **HONEST-LIMIT** (the message says why not). Silent defocus = RED.
  **Result: 14/14 FOCUSED** (7 scenes × 2 regimes; ELS85/Pyrite85 mag land at RMS 0.001,
  residual −0.025 mm). Two harness scars fixed on the way: the Missing-CAD dialog is modal
  and invisible on Xvfb (worker stuck at 0.2% CPU — suppress it headless), and SEQUENTIAL
  scenes end landing rays with reason `"image"`, not `"target_termination"` (the 65M
  false NO-DATA).
- Guard: `validate_open3d_0645_focus_reach_recruitment` = penta **phase 483** (A live retry,
  B recruitment routing + numeric stub, C snapshot covers STEP offsets, D measured claims,
  E published remainder).
