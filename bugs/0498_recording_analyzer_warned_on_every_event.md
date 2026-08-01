# 0498 — the recording analyzer warned on every event, burying the one real line

Found while reading `recording_20260801_204025` (the full recording whose single flag —
*"RA mirror drag left and right working fine"* — **confirms bugs/0496**).

## What it looked like

```
Analyzed recording_20260801_204025.json: 172 events
  1 info, 172 warning
  [warning] camera_view_up_drift  ev#0 ... camera_view_up=(6.12e-17, 0.0, -1.0) drifted from world up
  [warning] camera_view_up_drift  ev#1 ... (identical)
  ... 170 more, identical ...
```

172 warnings for 172 events. Reading the report meant filtering the tool's own output before the
one `[info] USER FLAG` line was visible.

## Root cause

`_check_view_up_drift` compared every event against a hardcoded `target = (0.0, 1.0, 0.0)` — world
+Y up. This app's scenes are viewed from TOP, `view_up = (0, 0, -1)`, which is what the nav cube
reads and what every AZ85 recording carries. So the check fired on every event of every recording
taken in the default view, and had presumably never been silent on this scene.

## Fix

The docstring already said what the check is for — *"drift = orbit flip bug"* — and drift means the
vector **changing** under an interaction that should have kept it locked, not being one particular
axis. Any axis-aligned view-up is a legitimate orientation. The check now compares each event
against the previous one and reports a transition once, instead of every event after it.

Measured: the same recording now analyses to `1 info, 0 warnings`. A synthetic flip from `(0,0,-1)`
to `(0,0,+1)` at event 20 yields exactly one finding, at event 20 — not thirty. Genuine per-event
drift still reports per changing event.

## Guard

`tests/test_recording_analyzer_view_up.py` (plain pytest — the analyzer is pure functions, no
display). Both halves are held, because either alone is satisfiable by cheating: silent on a steady
orientation *whatever axis it is* (both `-Z` and the `+Y` the old check happened to hardcode), and
still loud on a real flip and on gradual drift. Malformed entries are skipped rather than crashing.
Against the pre-fix code 4 of the 5 fail.

## Why it mattered

This is the tool for turning a recording into findings, and it is what I reach for first when a
recording arrives. At one warning per event it could not surface anything — a real finding would
have been indistinguishable from the noise. Cheap to fix, and it makes the next recording readable.
