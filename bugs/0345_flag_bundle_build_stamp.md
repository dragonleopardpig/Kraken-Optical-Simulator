# bugs/0345 — stamp the running git build into every flag bundle

## The recording (3 flags, 2026-07-17 15:37–15:39)

| Flag | Description |
|---|---|
| `flag_20260717_153747_940` | "after right click select snap optical axis, mouse hover on optical axis no highlight." |
| `flag_20260717_153837_166` | "right click snap CA to optical axis still not working." |
| `flag_20260717_153918_295` | "the 's' shortcut key still missing after clicking elsewhere to destroy the right click menu." |

Two of the three (`153837`, `153918`) **restate verbatim** the two bugs fixed AND
guarded ~14 min earlier in commit `7d285dd6` (0343 's' hotkey focus restore, 0344
auto-detected-CA snap). The third (`153747`) is the **pre-0337** symptom — the snap
arms the axis-pick machine but the axis "never highlights", which the 0337
single-axis auto-complete was written to eliminate (see
`_snap_clear_aperture_to_optical_axis_from_context` docstring). Screenshot of
`153747` confirms it: the CA opening is pinned (cyan rim) and a green pick anchor
sits on the optical axis — the machine is armed, not auto-completed.

## The real problem this bug fixes

The flag bundle's `state.json` carried **no fingerprint of the code the app was
launched from**. So a **stale app** (still running pre-fix code because it was
never restarted) is indistinguishable from a **genuine post-fix regression** —
from the bundle alone. Two cycles in a row stalled on the same question: *"is this
recording even on the new build?"* A fix plus a passing display-free guard cannot
answer it; only a build stamp in the bundle can.

Root-cause reasoning (which of stale vs. regression) is deferred to the next
recording, which will carry the stamp. But the leading hypothesis is a stale app:
all three symptoms match pre-`7d285dd6` / pre-0337 behaviour, and the in-tree code
is correct (guards 298/299/300 pass; `bugs/probe_0344` proves the LED's CA resolves
to a finite centre+normal, so the snap item is added).

## Fix — `_open3d_running_build_stamp()` into `state.json["build"]`

`open3d_inspector.py`:

```python
_RUNNING_BUILD_STAMP = None

def _open3d_running_build_stamp() -> dict:
    # best-effort git fingerprint of THIS checkout; cached once per process;
    # never raises (non-git install -> {"git": None})
    #   {"git": "<short-sha>", "branch": "<name>", "dirty": <bool>}
    ...
```

`flag_bug` writes it into the bundle:

```python
payload = {
    "version": 1,
    "captured_at_iso": ...,
    "build": _open3d_running_build_stamp(),   # bugs/0345
    ...
}
```

Cached once per process (the checkout does not change while the app runs), git via
a 2 s-timeout subprocess, fully `try/except`-guarded. Only fires on a flag (rare).

Invariant: **every flag bundle records the git HEAD the app was launched from**, so
a re-recorded bug can be told apart from a stale pre-fix app without guesswork.

## What this does NOT do

It cannot retro-stamp the 15:37–15:39 bundles (already written). The three flags
above therefore remain **unresolved-by-inspection**: re-record on `7d285dd6`+ (this
commit) — the new bundles will carry `"build"`. If `153747`/`153837`/`153918` still
reproduce with a fresh stamp, they are real and each has a concrete lead:
- 's' hotkey: the 0343 `focus_set()` is synchronous inside the dismiss handler; if
  Tk stomps it, defer via `after_idle`.
- snap not completing / axis no highlight: `_single_optical_axis_pick_info` returns
  `None` when `_optical_axis_pick_records` is empty at snap time → the two-step pick
  is kept and the buried axis can't be hovered. Instrument the records population.

## Guard & regression

`KrakenOS/UI/validate_open3d_flag_bundle_build_stamp.py` (penta **Phase 301**),
display-free:
- `_open3d_running_build_stamp()` is a never-raising dict with a `"git"` key that
  resolves a short SHA inside a checkout;
- source contract: `flag_bug`'s `state.json` payload includes
  `"build": _open3d_running_build_stamp()`.

## Files touched
- `KrakenOS/UI/open3d_inspector.py` — `_open3d_running_build_stamp()` helper +
  `"build"` in the `flag_bug` payload.
- `KrakenOS/UI/validate_open3d_flag_bundle_build_stamp.py` — new guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — Phase 301.
- `tools/penta_validator_baseline.json` — Phase 301 = pass.
