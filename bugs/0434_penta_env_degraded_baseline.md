# 0434 — The penta marathon on a post-mesa-update machine (crash fix + degraded baseline)

Not a flagged bug: an infrastructure postmortem written while shipping bugs/0433. Between
2026-07-24 (last all-pass baseline, 346 phases) and 2026-07-25 the host's graphics/runtime stack was
updated (NixOS rebuild). Two independent breakages appeared, one fatal to the gate and one to a whole
class of guards, and the marathon now reports **34 known failures that are NOT caused by any code
change in this branch**.

## 1. The marathon SIGSEGV'd — a bug-0294 use-after-free the update made fatal

Every full run died ~4 min in with `TkRenderWidget is being destroyed before its vtkRenderWindow` +
SIGSEGV. Because the harness prints its `[PASS]/[FAIL]` report only at the END and Python buffers
stdout, the gate got **nothing** to parse → `no phase results parsed` → exit 1 → **every push blocked**.

- `phase_39_detector_coverage_live` and `phase_61_detector_fov_plane_pickable` call
  `app.load_layout_by_name(<machine-vision layout>)` while the shared inspector is open. That runs the
  viewer-replacement teardown, which destroys the `vtkTkRenderWindowInteractor` the harness keeps
  using across phases — exactly the bug-0294 anatomy. llvmpipe used to survive the use-after-free;
  after the update it is a deterministic segfault.
- **Fix:** hold `app._keep_scene_viewers_across_layout_replacement = True` across both loads (the
  0294 flag), popped in `finally`. Both phases then pass all their own checks.
- **Diagnosis aid kept in the driver:** a flushed `print("[running] " + phase.__name__)` per phase, so
  a native crash names the phase it died in instead of vanishing.

Reproduced identically at pre-0433 `f072cb91` in a clean worktree → not a 0433 regression.

## 2. A native library sets `LC_ALL=C`, so guards read source as ASCII

Ten phases (102, 103, 131, 132, 134, 163, 166, 230, 262, 285) failed with
`UnicodeDecodeError('ascii', ...)` while reading app source to assert on it. Mechanism proved with
`locale.setlocale(LC_ALL, "C")` + `Path(...).read_text()`: the bare call decodes with the locale
codec, and these sources have always contained non-ASCII. Something in the marathon resets the C
locale (the OCC STEP reader is the prime suspect — OCCT forces `C` for number parsing).

**Fix:** `read_text(encoding="utf-8")` at all 14 guard sites — removes the locale dependency outright.
Verified by re-running all ten guards with the C locale forced: every one passes, zero ascii errors.
The app package itself has **no** encoding-less reads, so nothing user-facing was exposed.

## 3. What is left: 34 environment-degraded phases (baseline re-cut, user-approved)

After both fixes: **316 pass / 34 fail**, and two successive HEAD runs produce byte-identical failure
sets (the marathon is deterministic here). Remaining classes:

| class | example phases | symptom |
|---|---|---|
| render/pick under llvmpipe | 1, 2, 10, 54, 226, 299 | `no handle actors (got 0)`, `only 4 pink pixels (need >500)` |
| nav cube | 147, 148, 149, 230-family | `_import_vtk() missing CubeSource`, click returns False |
| stub-editor drift | 68, 130, 263, 269, 294, 296 | guards' `_FakeEditor`/`SimpleNamespace` lack methods real code now calls |
| illumination / trace on REAL scenes | 250-255, 305, 307, 181, 199, 203 | branch/detector/sampling expectations |

**Attribution (why these are not ours):** 36 of the original 44 fail identically at pre-0433 code
(`f072cb91`, clean worktree). For the ones that looked HEAD-only, the first comparison run was
fixture-blind — `git worktree` had already created `attachment/`, so the intended symlink nested
itself inside and the real scenes were invisible, making those phases SKIP into vacuous passes.
Re-run **with fixture parity**, every directly testable suspect reproduces the identical failure at
pre-0433: 305 `analysis_overlays_reached_image_branch`, 255 `illumination_keeps_real_detector`, and
phases 1 / 2 / 10 driven in order off a fresh app (same notes, down to `only 4 pink pixels`). The
remaining three (251, 253, 254) are inline, stateful members of the same illumination family as the
proven 255. **Net: no 0433 regression anywhere in the 34.** Two successive HEAD runs also produced
byte-identical failure sets, so this is reproducible ground, not noise.

**Decision (user, 2026-07-25):** re-cut `tools/penta_validator_baseline.json` recording these 34 as
known-fail. This is the gate's designed behaviour — baseline-failing phases don't block a push, while
the other 316 still catch genuine PASS→FAIL flips. **Re-cut the baseline back toward all-pass once the
machine renders cleanly**; until then a "pass" on those 34 is not being asserted by anyone.

## Files

- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — keep-viewers around both
  machine-vision loads, `[running]` phase markers, phases 348-350 (bugs/0433).
- `KrakenOS/UI/validate_open3d_*.py` — 14 `read_text(encoding="utf-8")` sites.
- `tools/penta_validator_baseline.json` — re-cut, 350 phases, 34 known-fail.
