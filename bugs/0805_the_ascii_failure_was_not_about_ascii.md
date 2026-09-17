# 0805 -- the "ascii locale" failure was not about ascii

`validate_open3d_0743_guards_name_their_encoding` (penta phase 539) failed with

    FAIL: C1: a source-reading guard passes under an ascii locale (exit 1)

and the user asked for "the ASCII thing" to be fixed. Its message pointed at encoding. Encoding was
not the cause.

## Measured

C1 runs a canary guard, `validate_open3d_0738_phantom_spacer_surfaces` (phase 536), under
`LC_ALL=C PYTHONUTF8=0` and required it to PASS. Run under the normal UTF-8 locale, the canary failed
**identically** -- same check, same rows:

    FAIL: A1: exactly the bare undrawn spacers after solids are phantom --
          [(2, 'air'), (4, 'air'), (6, 'to lens (unfolded RA mirror 1)'),
           (8, 'prism exit gap (air)'), (24, 'sensor standoff')]

C2 (no decode error under ascii) was already passing. The encoding fix of bugs/0743 was holding; a
failure elsewhere was being reported as a locale failure.

## The real failure: the scene changed, not the rule

0738 checks the phantom-spacer rule against `attachment/om05a_folded_80mm.py` and pins the expected
rows by NAME. The rule now also marks row 24, `sensor standoff`.

| | |
|---|---|
| guard and rule written | 09-07 22:27, same commit `6bf91be8` |
| `sensor standoff` in the 09-07 backup of the scene | absent |
| `sensor standoff` in the scene now (edited 09-10) | present |
| rule on the scene **with the row removed** | returns exactly the guard's original expected set |

The last row is the decisive one: the rule's behaviour on the rows the guard was written for is
unchanged; the only difference is a scaffolding row added to the scene afterwards. (A `git log -L`
lookup of the functions came back empty -- git cannot locate these class methods by name without a
Python diff driver -- so it was not relied on.)

The rule's verdict on that row is correct by its own contract: `sensor standoff` is undrawn AIR with
no aperture stop, barrel wall, detector or scatter -- a bare spacer. The guard's comment already
anticipated this: "the scene gains and loses scaffolding rows over time".

## Fix

* **0738** expects `sensor standoff` too, with the evidence recorded beside the list, and gains
  **A1b**: the Image row after a phantom standoff stays REAL -- skipping the standoff must never skip
  the sensor.
* **0743 C1** now runs the canary under the normal locale AND under ascii and requires the SAME
  result (exit code and every PASS/FAIL verdict). The question C asks is whether the LOCALE changes
  anything; requiring an outright pass let an unrelated failure masquerade as an encoding bug.
  **C2** now also rejects `UnicodeEncodeError` (printing non-ascii under an ascii locale), not only
  decode errors.

## Verified

* 0738: PASSED under the normal locale and under `LC_ALL=C PYTHONUTF8=0`.
* 0743: PASSED -- C1 compares exit 0 vs 0 and 39 vs 39 verdicts; C2 clean.
* **The new C1 still catches the bug class**: a throwaway script that reads a non-ascii file with a
  bare `read_text()` exits 0 under UTF-8 and 1 under ascii, and the new rule FAILS on it, with the
  decode error detected.
* Penta phases 536 and 539 PASS inside the suite harness, where VTK/Tk reset the C locale -- the
  condition bugs/0743 was about.
