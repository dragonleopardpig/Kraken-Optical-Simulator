# Bug tracking

User-flagged bugs in the KrakenOS Open 3D inspector get a numbered record
here, fixed, pinned with a small targeted test, and folded into the
comprehensive penta-telescope regression validator.

## Workflow (per bug)

1. **Document** — add `NNNN-short-slug.md` (next free number, see the
   register below). Capture: symptom (the user's own words), the in-app
   repro bundle it came from, root cause, the fix (files + line refs), the
   test that pins it, and which validator phase now guards it.
2. **Fix** — make the change. Keep it minimal and root-cause, not a
   band-aid over the symptom.
3. **Test immediately** — write a small, specific test that fails before
   the fix and passes after. Prefer a display-free unit test against the
   narrowest seam (e.g. a `@staticmethod` on a real VTK actor) so it runs
   without an X server.
4. **Integrate** — add a phase to
   `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` so the
   bug is re-checked end-to-end on the real penta-prism cascade (load,
   cascade one by one, select / unselect, observe optical axis). Then
   regenerate the pre-push gate baseline:
   `python tools/penta_validator_gate.py --update-baseline`.

## Where reproductions come from

Users flag bugs with the in-app event recorder
(`KrakenOS/UI/services/open3d_event_recorder.py`). Bundles land under
`attachment/recorded_bug_repros/flag_<timestamp>/` (gitignored): a
`description.txt` (the complaint), a `screenshot.png`, and a `state.json`
snapshot. Analyze the newest by mtime; correlate with the matching
`recording_<timestamp>.json` event log.

## Test layers

- **Unit / display-free** — `KrakenOS/UI/validate_open3d_<bug>.py`, run via
  `.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_<bug>`.
- **Regression / end-to-end** — a numbered phase in
  `validate_open3d_penta_telescope_comprehensive.py`, gated on push by
  `.githooks/pre-push` -> `tools/penta_validator_gate.py` (boots Xvfb,
  blocks only on a PASS->FAIL flip vs `tools/penta_validator_baseline.json`).

## Register

| ID | Title | Status | Fix tests |
|----|-------|--------|-----------|
| [0001](0001-analytic-lens-selection-all-red.md) | Selecting an analytic lens renders solid red, no slide handle | Fixed | `validate_open3d_analytic_lens_select_not_all_red` + Phase 10 |
