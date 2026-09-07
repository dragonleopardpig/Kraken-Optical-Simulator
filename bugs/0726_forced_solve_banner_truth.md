# 0726 — "forced crash. But the lens is not crashing": the banner said REFUSED over a solve that worked

Flag `flag_20260907_083535_680` (build 656bd916): *"changed FOV to 20x20, solved refused, forced
crash. But the lens is not crashing, and Trace Now shows defocus rays at sensor."* Companion
flag `flag_20260907_083701_740` shows the same state down the sensor normal.

## What was actually happening

Forcing FOV 20 × 20 on om05a asks the lens for **138.6 mm** along its leg, and there is
**158.9 mm** of physical room to RA mirror 1's body. So the move **fits**, with 20.3 mm to
spare, and `solve_fov_to_inspection_face(..., force=True)` returns **ok=True** with the status
line *"FORCED: 20.32 mm clearance to RA mirror 1 (50 mm) body"*.

The in-scene banner, however, read:

```
SOLVE REFUSED -- the drawn scene does NOT deliver this request
FORCED solve applied -- inspect the 3D overlap
FORCED: applied; 20.32 mm clearance to RA mirror 1 (50 mm) body (158.9 mm of physical room)
```

A refusal heading over a successful solve, in alarm red, telling the user to inspect an overlap
that does not exist. There was no bug in the lens motion — the user was sent looking for a
collision that physics says cannot happen at this field.

Root cause: the forced branch stashes `_fov_solve_refusal_info` — the *refusal* channel —
whatever the outcome, with `info.setdefault("reason", "FORCED solve applied -- inspect the 3D
overlap")`, and `format_solve_refusal_lines` unconditionally headed the block with
"SOLVE REFUSED".

## Fix

`system_info_hud.solve_banner_outcome(info)` classifies what the banner is reporting —
`"refused"` (nothing applied), `"forced_crash"` (applied, `forced_penetration_mm` < 0),
`"forced_fits"` (applied, clearance or unmeasured), `""` (nothing). The heading follows it:

| outcome | heading |
|---|---|
| refused | `SOLVE REFUSED -- the drawn scene does NOT deliver this request` (unchanged) |
| forced_crash | `FORCED SOLVE APPLIED -- the lens PENETRATES hardware (inspect the 3D overlap)` |
| forced_fits | `FORCED SOLVE APPLIED -- the lens FITS: nothing collides` |

* `quick_estimation`: the "inspect the 3D overlap" reason is defaulted **only** when the body
  penetrates. When the move fits no reason is invented — but a REAL earlier refusal reason (why
  the plain solve said no) still renders, so the user learns the actual blocker.
* `open3d_inspector._update_solve_refusal_banner`: the banner is amber when the forced move fits
  and red for a refusal or a real penetration, so a successful force no longer reads as an alarm.

## Verified (om05a, real solves)

| request | move needed | room | outcome | banner heading |
|---|---|---|---|---|
| FOV 20 × 20 forced | 138.6 mm | 158.9 mm | fits, 20.3 mm clearance | `FORCED SOLVE APPLIED -- the lens FITS: nothing collides` |
| FOV 8 forced | 181.5 mm (capped 180.5) | 158.9 mm | **penetrates 21.5 mm** | `FORCED SOLVE APPLIED -- the lens PENETRATES hardware` |
| FOV 5 forced | 192.3 mm (capped 180.5) | 158.9 mm | **penetrates 21.5 mm** | same, cap note kept |
| re-solve at 20 after solving | — | — | refused | `SOLVE REFUSED` + "No real-image conjugate for that size" |

So a crash IS reachable on this scene — it needs a field small enough (≲8 mm) to demand more
than the 158.9 mm of room. At 20 × 20 there is genuinely nothing to crash.

## Not changed (physics, confirmed with the user)

* The two split-field strips land at **±14 mm on a ±11.5 mm sensor** after a 20 × 20 solve, so
  they sit outside the die. That is the real design limit: the ±8.8 mm beam offset at the lens
  maps to ∓offset·(1 − v/f), which grows with magnification. The user's call: *"if green field
  strips sitting outside is physically correct, then let it be."*
* The defocus at the sensor is the reported 40.6 mm focus residual — the vendor camera is fixed,
  so the exact conjugate needs the device stage ([[feedback_vendor_hardware_immutable]]).

## Guard

`validate_open3d_0726_forced_solve_banner_truth` = penta phase 525 (display-free): A the
classification; B a fits banner never says REFUSED/overlap/penetrates yet keeps the clearance and
obstacle; C the crash banner keeps the penetration and cap note and a plain refusal keeps its
heading, reason and Force hint; D a real reason survives and none is invented; E the wiring pins.
0717 / 0718 / 0719 still pass.

## Follow-up

The right-click item is labelled "Force FOV (show collision)", which over-promises when the move
fits. The banner now says what happened; renaming the menu entry (e.g. "Force FOV (bypass the
room limit)") would remove the last bit of the mismatch.
