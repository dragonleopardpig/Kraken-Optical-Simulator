# 0748 -- om05a_folded_80mm: track set so a 54 mm device focuses

User: "can you modify the total track of om05a_folded_80mm.py (modify only the total sliding gap
of the lens) so that the FOV start at 20mm to 54mm?"

## What was already true

20-54 mm already SOLVED on the original track -- the deliverable range was 17-56 mm. What could not
be done was focus across it, and that is arithmetic rather than a tuning problem: the required track
is `f(2 + m + 1/m)` with f = 82.407 mm, which over 20-54 mm runs from 329.6 mm (at |m| = 1, a
~22 mm device) to 401.1 mm. **71.5 mm of variation against a depth of focus of ~0.15 mm.** A fixed
track is one number and cannot follow it. The sizes that DO focus always come as a reciprocal pair,
d1 x d2 = 481.5 mm^2, so focus at 20 forces its partner to 24.1 mm and focus at 54 forces 8.9 mm --
no pair straddles the range.

## Change made

Sliding-gap sum **148.4000 -> 156.9400 mm** (+8.540), split proportionally:

    row  8  prism exit gap (air)        108.0696 -> 114.2887
    row 13  Rear Optical Vertex Datum    40.3304 ->  42.6513

That places the Gaussian focus on a **54.0 mm** device (residual -0.06 mm) -- the top of the
requested range -- and keeps the deliverable range at **17-56 mm** (58 refuses).

| device | \|m\| | residual before | residual after |
|---|---|---|---|
| 17 | 1.2908 | -57.58 | -66.12 |
| 20 | 1.0971 | -62.26 | -70.80 |
| 30 | 0.7314 | -54.85 | -63.39 |
| 40 | 0.5486 | -32.37 | -40.91 |
| 50 | 0.4389 |  -3.86 | -12.40 |
| **54** | 0.4063 |  +8.48 | **-0.06** |
| 56 | 0.3918 | +14.80 |  +6.26 |

The small-field end gets worse by the same 8.54 mm, which is unavoidable: moving the zero up the
curve moves everything else down it.

Backup `om05a_folded_80mm.py.pre-focus54.bak` (the 148.4000 state).

## Rejected: centring the focus over 20-54

Tried -27.22 mm (sum 121.18), which balanced the residual at +/-35.75 mm with focus at 42 mm --
and BROKE the top of the range: 50, 54, 56 all refused. The sliding-gap sum is simultaneously the
track AND the lens travel envelope, so shortening it removes reach. At 50 mm the lens needs
`row8 = 125.1 mm` against a whole sum of 121.18 -- unreachable at any split. Reverted.

## Caveat: Gaussian vs real-ray focus

The -0.06 mm above is the FIRST ORDER. A thin-device trace put the real-ray waist ~1.5 mm behind
that, i.e. the aberrated bundle's best focus sits nearer a **53.5 mm** device. Trimming the track
1.45 mm to chase it was tried and reverted: the traced waist fit is unreliable in this
configuration (it returns a 4 mm "waist", or nothing at all, for square multi-field devices), so
there is no trustworthy number to trim against. The track is therefore set by the paraxial model,
which is reproducible, and the ~0.5 mm of device-size offset is well inside what a bench focus
adjustment absorbs.

Station sum vs traced path after the change: 422.300 vs 422.576 mm, **0.276 mm** -- no bugs/0745
class of mismatch was introduced.

## Standing recommendation

For the whole 20-54 range in focus, the track cannot help; a focus axis with **~71.5 mm** of travel
on the camera or the device stage is required. 30-54 needs 63.3 mm, 40-54 needs 40.9 mm, 45-54
needs 27.1 mm.

## Process note

The first attempt applied +8.54 THREE times (148.40 -> 174.02) because the apply script had no
`if __name__ == "__main__"` guard and the multiprocessing spawn re-executed the module -- the
documented trap. Re-done with a guard AND an absolute target sum instead of a relative delta, so a
repeat run is idempotent.
