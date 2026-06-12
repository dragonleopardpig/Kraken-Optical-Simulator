# 0071 — Open 3D: the FOV popup accepts just one dimension and derives the other

## Request (user's words)

> 4) Double click the FOV input box: can user given the option to just enter value
> in one of the box, the other value should be auto calculated (or leave blank and
> calculate after pressing either of the buttons).

The double-click FOV popup has a **Width** box and a **Height** box. The user wants
to fill **just one** and have the other auto-complete from the sensor aspect, then
press either solve button.

## Before

`QuickEstimationService._sensor_wh(width, height)` (bugs/0057) derived a missing
**Height** from the 4:3 aspect, but **required a positive Width** — you could not
leave the Width box blank. The popup's commit handler parsed Width first and
returned early if it was not a positive number, so a Height-only entry was
rejected.

## Change (display-only — the optical solve is untouched)

`KrakenOS/UI/services/quick_estimation.py`:

* `_sensor_wh(width, height, aspect=None)` — **either** side may now be omitted
  (None / blank / unparseable) and the missing side is derived from `aspect` (the
  live sensor's width:height, default 4:3). A value that *is* supplied but is
  non-positive / non-finite is still rejected (so a typo refuses the whole solve
  rather than silently deriving). Returns None when neither side is usable.
* `fov_solve(plane, mode, width, height=None, aspect=None)` — threads `aspect`
  into `_sensor_wh` for both the object and image branches; the refusal messages
  became "Enter a positive FOV width or height." / "Enter a positive sensor width
  or height."

`KrakenOS/UI/open3d_inspector.py` (the popup):

* a grey hint — "Fill just one box — the other is derived from the sensor aspect."
* `_read_dim(var, label)` parses each box independently: blank → `(True, None)`
  (derive it), a present-but-non-positive / non-numeric value → `(False, None)`
  with a status note (refuse), a good value → `(True, val)`.
* `run(mode)` errors only when **both** boxes are blank, computes the live aspect
  from the prefilled sensor dimensions (`(w0, h0)` when both are known, else None →
  4:3), and calls `_apply_quick_estimation_fov_solve(plane, mode, width, height,
  aspect)` — which forwards `aspect` to `qe.fov_solve`.

The existing `horizontal_to_diagonal` / `diagonal_to_horizontal` mapping and the
width-only path are unchanged, so every prior behaviour (bugs/0055, 0057) still
holds; this only *relaxes* the requirement that Width be present.

## Test (fails before, passes after)

`KrakenOS/UI/validate_open3d_fov_plane_solve.py` — new `_test_solve_single_dimension`
(display-free), plus one-box wiring assertions added to
`_test_double_click_gesture_wiring`:

* Image 'sensor', **Height only** (H=12, default 4:3) → derived W=16, image circle
  Ø=20, detector dims (16, 12); the width-only path reaches the identical sensor.
* Object 'thickness', **Height only** (H=30 → W=40, diag 50) → the conjugate pair
  moves identically to the width-only solve.
* A **custom aspect** (the 65 MP Bopixel 29.9:22.4) fills the blank box at that
  ratio: H=22.4 → W=29.9, Ø=37.36, detector dims (29.9, 22.4).
* **Both boxes blank** → refused, model untouched.
* Wiring: the popup contains `_read_dim` (each box parsed independently) and
  threads `aspect` through to `_apply_quick_estimation_fov_solve` / `fov_solve`.

Against the old `_sensor_wh` the Height-only and custom-aspect cases fail (a blank
Width was rejected), and the old popup/apply had no `aspect` thread.

## Integrated

The display-free guard is wrapped by **Phase 60** of
`validate_open3d_penta_telescope_comprehensive.py`, which was extended with a live
mirror: a Height-only solve (16×12 / Ø20), a custom-aspect fill (29.9:22.4), a
both-blank refusal, and the `_read_dim` + `aspect` wiring checks. No new phase is
needed; the baseline phase count is unchanged.

## Verification note

The display-free guard pins the one-box math and the popup wiring. The live Tk
double-click + popup can't be driven headless (no X server); the user confirms the
one-box entry in-app.
