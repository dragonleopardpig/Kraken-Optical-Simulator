# 0501 — the build stamp could report a commit the running app had never loaded

Found chasing `flag_20260801_213047` — *"lens dragged right."*

## Why it mattered immediately

That flag reported build `9bde7db3` — the bugs/0499 fix — and showed the **pre-fix** behaviour
exactly:

```
lens body   x 97.41 -> 125.72   (+28.31, the drag)
row 1       x 71.66             unchanged
row 6       x 126.66            unchanged
```

Driven headlessly on `9bde7db3`, both drag paths move both — the direct
`translate_step_overlay(..., refresh=True, record_history=True)` and the real drag release through
`_finish_step_translate_drag`:

```
DIRECT        before body=97.41 row1=71.66  ->  after body=125.72 row1=99.97
DRAG-RELEASE  before body=97.41 row1=71.66  ->  after body=125.72 row1=99.97
```

The body lands on 125.72 in the recording *and* in both probes, so the drag itself was 28.31 mm and
the code under test is right. Only the rows disagree — which is the old behaviour, from an app that
had never loaded the new code.

## Root cause

`_open3d_running_build_stamp` shells out to `git rev-parse --short HEAD` and caches the answer in a
module global, **lazily**. It therefore reports the working tree's HEAD *at the moment it is first
asked*, not the code that was imported. An app started before a commit and flagged after it reports
the new hash while executing the old code.

That is the "[stale-app recording]" trap with the one signal that should have caught it disabled: a
recording's build stamp exists precisely to distinguish a stale app from a real regression, and it
was reporting whatever the repository had moved on to.

## Fix

Compute the stamp at **import** — when the code was actually loaded. Measured cost: 0.97 s for the
subprocess on first import of `open3d_inspector`, once per process, and 59/59 pytest unchanged.

A stamp taken at import can still be wrong in one direction — an app running from an editor buffer
saved after import — but it can no longer silently claim a commit that landed after startup, which
is the case that actually bites.

## Bearing on 0499

`flag_20260801_213047` is **not** a bugs/0499 regression. It needs re-recording from an app started
on `9bde7db3` or later.
