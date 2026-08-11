# 0609 — A swap asks for the FOV you want instead of keeping a stale number (FEATURE)

User, 2026-08-11 (after the bugs/0608 audit): *"I think direct swapping a lens most of
the time will not get back the condition (object distance, image distance, FOV, etc) of
the previous lens. How about pop up the FOV solve dialog and let user input and solve for
thickness?"*

Right, and the audit measured exactly that. After swapping PYRITE 4.5/85 into the folded
Apo75 scene, the swap's "FOV preserved" contract kept the old 15.30 x 15.30 object field
— but with the new glass that field lands 18.78 x 17.74 on a 23 x 23 sensor, filling only
**82% x 77%** of it. 19.79 mm was needed to fill the same sensor. Preserving the NUMBER
across a swap preserves neither the framing nor the working distances, so the scene ends
up in a state the user never chose.

## Behaviour

After an INTERACTIVE lens swap (the bugs/0586 convention: an explicitly-passed folder is
a programmatic caller), the object-plane FOV popup opens, prefilled with the field that
fills the sensor at the newly measured magnification, so the user can accept it or type
their own and click **Solve for Thickness**. Cancel keeps the swap's own auto-refocus —
nothing is forced. The swap message says so.

The popup is modal (`grab_set` + `wait_window`), so it is SCHEDULED via `after()` rather
than called inline: a headless or guarded swap must never block, and a programmatic swap
never prompts at all.

## The prefill had to be fixed first

`object_fov_dimensions()` — the popup's prefill — read the RAW folded first order, so it
would have offered 15.27 (the field that does NOT fill the sensor), defeating the point.
It is a DISPLAY/prefill reader, so per the bugs/0602 rule it now applies the measured
correction and offers 19.79.

## Known sibling, NOT changed here

"Solve for Image/Sensor Size" (`fov_solve(..., mode="sensor")`) sizes the sensor as
`|m_raw| * object field`. On this scene that is 23% too large — it should size by the
DELIVERED magnification. Left alone deliberately: it changes a SOLVE's booking rather
than a readout, so it wants its own flag and verification.

Guard: phase 461 (`validate_open3d_0609_swap_prompts_for_fov`).

## Verified, and one BLOCKING gap found (not caused by this change)

Measured through the REAL dialog callback (`_apply_quick_estimation_fov_solve` on the
inspector's persistent service, not a throwaway one):

- a PROGRAMMATIC swap never opens the popup — no hang, no modal in guards;
- the prefill offers **19.83** (delivered-aware) where the raw first order would have
  offered 15.27;
- the solve runs, records the target (semi 14.02) and re-learns the correction.

**But the traced field does not follow the typed value.** After accepting 19.83 and
clicking Solve for Thickness, the rays still launch the old 15.30 field and land
18.78 x 17.74 — the sensor stays at 82% x 77% fill, unchanged from before the solve.

Root cause (pre-existing, NOT introduced here): the scene's field is coupled as
`sensor_semi / |m|` using the **RAW** folded first order — 16.26 / 1.5062 = 10.79
semi-diagonal, i.e. the 15.30 square the trace samples — while the FOV label and this
popup's prefill now use the DELIVERED |m| (bugs/0602/0608). So the label says 19.79, the
prefill says 19.83, and the launcher still says 15.30.

Until that coupling reads the delivered magnification too, this dialog lets the user
*state* the field they want and moves the conjugates for it, but the scene keeps imaging
the old field. Fixing the coupling is the natural next step and needs its own
verification pass (it changes what the trace samples, not just a readout).

## Resolved by bugs/0610 (96c600cb, phase 462)

The blocking gap above — the launcher reading the RAW |m| — is fixed at the shared
converter `_field_metrics_for_value`. Guard green; the in-app swap measurement was still
running when the session ended, so the AFTER-swap fill number is unconfirmed. RESUME
HERE: re-run `scratchpad/verify_0610.py` (or an equivalent swap probe) and confirm the
traced launch field grows 15.30 -> ~19.8 mm and the sensor fill goes 82%x77% -> ~100%.
