# 0725 — "rays haywired" / "sensor displaced seriously": a display STEP was moving the optics

Flags `flag_20260906_235409_571` ("rays hay wired") and `flag_20260907_000220_381`
("more screenshots", sensor displaced), build 49362db2, `attachment/om05a_folded_80mm.py`.

## Symptom

Pressing **Trace Now in the 3D window** produced a scene where the sensor and both FOV band
labels were drawn hundreds of millimetres away from the camera, rays sprayed off into empty
space, and almost nothing reached the detector. The recorded state:

| | flag | expected |
|---|---|---|
| ray paths | 3225 | ~4332 |
| reaching the image | **24** | 445 |
| missed the image | **1672** | — |
| detector target | **(0, 0, 589.14)**, trace surface 24 | (272.63, −1.76, −25.0), surface 23 |
| trace time | **524 s** | ~55 s |

## Root cause

`_refresh_trace_now_scene` builds its preview with `include_live_step_overlays=True`, and
`_live_step_overlay_trace_rows` **inserts** the imported optical STEP body into the traced row
list. On om05a that overlay is the whole vendor assembly — 61 698 mesh cells, and geometry that
merely *decorates* optics already promoted as rows 1–22.

Inserting it did two things:

1. **Shifted every later row index.** The Image row moved 23 → 24.
2. **Made it a station of the follower walk.** With an extra optical-solid row in the chain the
   walk no longer produced a folded pose for the Image row, so the detector target fell back to
   the unfolded axis at z +589 — 600 mm from the real sensor. Rays were then traced toward a
   phantom image plane, which is exactly the "haywire" fan and the 24/3225 hit rate.

It was also the reason Trace Now took minutes: every ray segment was intersected against the
61 698-cell decoration (bugs/0724 removed a second, unrelated multi-minute stall in the same
button — the two together made it look frozen).

## Fix (general, physics-first)

The invariant belongs to the scene, not to the overlay: **adding a display body must never move
an optical element.**

`three_d_scene_tools._live_step_overlay_injection_moves_optics(original_rows, candidate_rows,
insert_at, inserted)` walks `optical_solid_output_port_pose_overrides` for the row list with and
without the injection, maps the shifted indices, and compares every pre-existing row's pose. It
returns a reason string when any row moves, loses, or gains a traced pose — and a walk that
raises is refused rather than risked.

Every insertion path in `_live_step_overlay_trace_rows` (cached plan, fresh plan, single row and
multi-row) consults it and returns the untouched rows on refusal.
`_note_live_step_overlay_injection_refused` reports it to the debug log and the status line, so
the overlay is never silently dropped:

```
Transient optical STEP not traced: it would move the seated optics --
row 23 'Image / Sensor' lost its traced pose. The imported STEP stays CAD
display hardware; promote it to trace it.
```

A transient overlay that genuinely leaves the optics alone (the workflow this feature was built
for: place an unpromoted STEP, snap it to the axis, see rays through it) still traces — the
guard only fires on a harmful injection.

## Verified end to end (the inspector's own Trace Now, om05a)

| | before | after |
|---|---|---|
| Trace Now | 524 s | **94 s** |
| detector target | (0, 0, 589.14), surface 24 | **(272.63, −1.76, −25.0), surface 23** |
| records reaching the image | 24 of 3225 | **445 of 4332** |
| measured strips | — | A +3.49…+3.68 (129 rays), B −3.67…−3.47 (316 rays), symmetric |
| meshes in the traced system | 26 (one 61 698-cell body) | 25 |

Rendered from the flag's own camera (`verify_0725_flag_camera.png`): the sensor sits at the
camera prism, both arms fold onto it, no stray fan.

## Guard

`validate_open3d_0725_live_step_overlay_pose_guard` = penta phase 524 (display-free, synthetic
rows + stubbed walk): A a benign injection is allowed; B a row that moves is refused with the
row and distance named; C the shifted-index mapping, and the om05a signature (the Image row
losing its pose); D an unusable walk is refused; E every insertion path consults the guard and
the refusal is reported.

Also updated: `validate_open3d_action_timing`'s "hidden-ray STEP drop" pin matched the literal
`refresh_from_editor(force_retrace=physics_requested)`, but the call has since become
`force_retrace=physics_requested or bool(refocus_note)` (a committed lens drag refocuses and
must retrace). The pin now matches the `physics_requested` gate rather than the whole
expression, so it still guards the intent. That failure predates this change.

## Follow-ups

* Trace Now is still ~94 s on om05a. That is real physics: ~half is the arm-B light, which only
  started tracing for imaging rays with bugs/0723. Worth a sampling/decimation pass.
* Trace Now runs on the Tk thread, so the window stops repainting for its duration; progress or
  cancellation is the ergonomic fix (also noted in bugs/0724).
* `validate_optical_solid_runtime_frame` fails on row 6 of `attachment/penta.py`, unrelated and
  pre-existing (confirmed by stashing these changes).
