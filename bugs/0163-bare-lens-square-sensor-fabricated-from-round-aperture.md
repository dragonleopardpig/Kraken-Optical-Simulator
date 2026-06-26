# 0163 — bare lens fabricates a square "Sensor" from its round image aperture

User report (two flags, *Tessar lens using vignetting factors* zemax example from
the menu, rays off): *"What is the meaning of the Sensor 93.2 x 93.2? Why there is
such recommendation? And because of this sensor, there is a recommendation of
131.8 image circle."* With no camera registered, the detector overlay draws an
orange **square** "Sensor 93.2×93.2" and then complains the image circle is too
small, recommending a larger **Ø131.8** ring — nonsense for a bare lens that only
has a round image aperture.

## Root cause

The Tessar has no vendor camera, so the Image detector target's
``active_width_mm`` / ``active_height_mm`` are **0**. Two draw paths then fall back
to the round Image-surface clear-aperture **diameter** (93.17 mm) and treat it as a
rectangular sensor:

* **The orange square** — ``scene_geometry.scene_target_active_footprint_polylines``
  calls ``scene_target_active_dimensions``, which fills *both* width and height from
  the diameter when the active dims are 0. A round Ø93.17 aperture is drawn as a
  93.17×93.17 **square**.
* **The "(short)" / "Needs Ø131.8" labels** — ``detector_coverage_overlay`` then
  asks "does the image circle reach the sensor *corners*?" The fabricated square's
  half-diagonal is ``93.17/2 × √2 ≈ 65.9`` (Ø131.8), which a round aperture's image
  circle (radius = max real image height 42.39, Ø84.78) can **never** reach — so it
  is always reported "short" and demands a Ø131.8 image circle.

The whole recommendation is an artifact of squaring a circle. There is no sensor.

## Fix (Option B — make the recommendation useful)

The user chose to keep a recommendation but with the rule **"the sensor must be
within the image circle."** So for a bare lens the overlay now recommends the
**largest square that fits *inside* the image circle** — corners *on* the circle,
side = ``radius × √2`` — instead of fabricating a square from the aperture and
demanding a bigger circle.

* `scene_geometry.py` — new ``scene_target_has_explicit_sensor(target)``: True only
  when the detector carries real ``active_width_mm`` / ``active_height_mm`` (a
  registered camera or explicit active area). ``scene_target_active_footprint_polylines``
  now returns ``[]`` when there is no real sensor — the misleading orange square is
  **suppressed**. Branch detectors and camera detectors set real active dims, so
  their footprints are untouched.
* `services/detector_coverage_overlay.py` —
  - ``DetectorCoverageMetrics`` gains ``sensor_is_real``; ``detector_coverage_metrics``
    takes a keyword-only ``sensor_is_real=True``.
  - new ``recommended_inscribed_sensor_side(image_circle_radius) = radius × √2``.
  - ``add_overlays`` routes via ``_target_has_real_sensor``: a real sensor keeps the
    existing coverage-vs-corners behaviour; a bare lens builds metrics from the
    inscribed side with ``sensor_is_real=False``.
  - The specs/labels treat a non-real sensor as always covering: the image circle
    stays cyan (no "(short)"), the label reads **"Max sensor 59.9×59.9"** (the
    inscribed square), a ``recommended_sensor_rect`` is drawn instead of the
    ``required_image_circle`` ring, and the "Needs Ø…" label + debug-log warning are
    suppressed.

On the Tessar (Ø84.78 image circle): the overlay now shows **"Max sensor
59.9×59.9"** inside a cyan **"Image circle Ø84.8"** — no square, no "(short)", no
Ø131.8. (59.949 = 42.391 × √2; "60" is the rounded value.)

The recommended sensor is **visual only** — it does not change the detector's actual
active dims or the ray-miss physics; it is a sizing suggestion drawn by the coverage
overlay while the raw round-aperture square is suppressed.

## Guard

* ``KrakenOS/UI/validate_open3d_inscribed_sensor_recommendation.py`` (new, penta
  Phase 154) — display-free: checks (a) a no-camera target reports no explicit
  sensor and suppresses the footprint polylines; (b) the inscribed side = R√2 and
  its metrics ``covers`` with ``sensor_is_real=False``; (c) the no-camera specs
  carry ``recommended_sensor_rect`` and **not** ``required_image_circle``, labels
  read "Max sensor …" with no "(short)" / "Needs"; (d) a real sensor still draws 3
  footprint polylines and keeps the coverage-vs-corners framing (an over-large
  sensor still goes "short" with a required ring).

## Notes

* **In-app eyeball owed:** the felt result — the orange square gone, replaced by a
  cyan "Max sensor 59.9×59.9 / Image circle Ø84.8" recommendation on the Tessar with
  rays off — must be eyeballed in the running app. Headless VTK (Xvfb llvmpipe)
  can't drive the embedded inspector render.
* End-to-end verified display-free on the loaded Tessar scene: image row diameter
  93.17, max real image height 42.391 → footprint suppressed (0 polylines), overlay
  routes to "Max sensor 59.9×59.9" (covers, sensor_is_real False); a synthetic
  36×24 real sensor still draws 3 footprint polylines unchanged.
