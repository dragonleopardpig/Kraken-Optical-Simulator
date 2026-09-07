# 0743 -- a guard that reads source must name its encoding

The penta gate blocked on ten phases. Eight were the pre-existing set; the other two were
**Phase 536** (bugs/0738's own new guard) and **Phase 518** (bugs/0719) -- and both PASSED when run
standalone. A guard that passes alone and fails in the suite is a state-leak, not a regression.

## Root cause

Phase 536's failure carried the reason:

    ! phantom_spacer_surfaces guard raised: UnicodeDecodeError('ascii', b'import numpy as np...')

`Path(...).read_text()` with no `encoding` uses the locale's preferred encoding. Python defaults to
UTF-8 even with `LANG`/`LC_ALL` unset -- but **VTK/Tk reset the C locale** as the suite builds
scenes, and after that `locale.getpreferredencoding()` returns `ANSI_X3.4-1968`. Both files these
guards read contain non-ascii (`validate_open3d_penta_telescope_comprehensive.py` at byte 66059,
`KrakenSys.py` at byte 4631), so the read raised.

Standalone, the locale is still UTF-8 and the same guard passes. That is why the two phases looked
like regressions and why the gate's picture of the suite has been unreliable.

Phase 518 hid it. Its G5 check wraps the read in a bare `except Exception: penta_src = ""`, so the
decode error became an empty string and the check reported "not registered as penta phase 518" --
a **false, and misleading, failure reason**. Phase 536 let the exception reach the phase wrapper,
which is the only reason the cause was visible at all.

## Fix

Every source read in a validator names its encoding -- 11 call sites across 8 guards
(0481, 0492, 0650, 0652, 0667, 0719, 0722, 0738). Reading SOURCE is never locale-dependent.

Verified by reproducing the suite's condition directly:

```
$ PYTHONUTF8=0 LC_ALL=C python -c "import locale; print(locale.getpreferredencoding(False))"
ANSI_X3.4-1968
$ PYTHONUTF8=0 LC_ALL=C python -m KrakenOS.UI.validate_open3d_0738_phantom_spacer_surfaces
0738 phantom-spacer validation PASSED
$ PYTHONUTF8=0 LC_ALL=C python -m KrakenOS.UI.validate_open3d_0719_lens_move_thickness_pair
0719 lens-move thickness-pair validation PASSED
```

## The wider lesson

A guard that swallows its own failure reason (`except Exception:` -> empty source -> a check that
then fails for a fabricated reason) costs more than the bug it hides. bugs/0518's G5 reported a
registration problem that did not exist. When a guard cannot read what it needs, it should say so.

## Guard

`KrakenOS/UI/validate_open3d_0743_guards_name_their_encoding.py` (penta phase 539) fails if any
validator reads source without an encoding, and runs a guard under an ascii locale to prove the
class of bug is actually closed.
