# bugs/0344 — "right click snap still not working" (auto-detected CA had no snap item)

**Flag `flag_20260717_145154_083`** (imported LED, app running the bugs/0341/0342 fix):

> "right click snap still not working."

This flag is on the **same fresh session** that recorded `flag_20260717_145231_845`
(which proves bugs/0341 — and therefore the co-shipped bugs/0342 — is present). So this
is a **real gap in bugs/0342**, not a stale app.

## The defect

bugs/0342 offered the "Snap Clear Aperture → Optical Axis (center + normal)" only inside
the manual-record gate:

```python
if self.editor.step_clear_aperture(step_label) is not None:   # MANUAL record only
    if opening_feature is None:
        ca_center, ca_normal = self._clear_aperture_record_center_normal(step_label)
        ...  # snap
```

But the LED's clear aperture is **auto-detected** (bugs/0319 C2), not manually set. The
hover **highlight** already keys off `_clear_aperture_opening_face_index`, which prefers
the manual record **then falls back to the deterministic auto-detect**. So the opening
lights up on hover even with no manual record — the user reasonably believes "the CA is
there" — but the **snap** was gated on the manual record only, so no snap item appeared.
"right click snap still not working" even though nothing was "set".

Confirmed headless (`bugs/probe_0344_led_auto_ca_snap.py`, the AZ85 LED overlay):

```
manual step_clear_aperture('led') = None
auto-detect candidates: 5
  top face 266: center=[0.77, 0, 8.0], normal=[0,0,-1], area=719.6, finite=True
VERDICT: opening snappable WITHOUT a manual record = True
```

Face 266 is exactly the CA face from the flag diagnostics — a real, finite, snappable
opening with **no** manual record.

## Fix — key the snap off the same resolver as the highlight, un-gated

The snap now resolves from the **opening** (manual record OR auto-detect), the same
resolver the hover highlight uses, and is offered **outside** the manual-record gate in
both the body STEP menu and the pinned-opening menu
(`open3d_face_assignment.py`):

```python
def _clear_aperture_opening_center_normal(self, label):   # bugs/0344 (was _record_)
    face_index = self._clear_aperture_opening_face_index(label)   # manual OR auto-detect
    if face_index is None:
        return None, None
    centroid, normal, _area = self.editor._step_overlay_fine_face_centroid_normal(label, face_index)
    ...  # finite-check -> (center, normal) or (None, None)
```

Body menu:

```python
if opening_feature is None:                                 # not already on the opening
    ca_center, ca_normal = self._clear_aperture_opening_center_normal(step_label)
    if ca_center is not None and ca_normal is not None:
        menu.add_command(label="Snap Clear Aperture -> Optical Axis (center + normal)", ...)
if self.editor.step_clear_aperture(step_label) is not None:  # Center / Forget act on the
    menu.add_command(label="Center Clear Aperture -> Optical Axis", ...)   # manual record,
    menu.add_command(label="Forget Clear Aperture", ...)                    # so stay gated
```

The pinned-opening menu's `not normal_finite` fallback is likewise un-gated from the
manual record. Only **Center** / **Forget** (which read/clear the manual record) remain
gated on `step_clear_aperture(...) is not None`.

Invariant: **if the clear-aperture opening RESOLVES (manual record OR auto-detect) — i.e.
if it can highlight on hover — it is snappable to the optical axis.** The snap and the
highlight now share one resolver, so they can never disagree again.

## Guard & regression

`KrakenOS/UI/validate_open3d_clear_aperture_snap_auto_detect.py` (penta **Phase 300**),
display-free:
- `_clear_aperture_opening_face_index` falls back to the top auto-detect candidate when
  there is **no** manual record;
- source contract: in **both** menus the `_clear_aperture_opening_center_normal` snap is
  resolved **before** (outside) the `step_clear_aperture(...) is not None` gate.

`KrakenOS/UI/validate_open3d_clear_aperture_snap_from_record.py` (Phase 298) updated for
the rename + broadened resolver — the manual-record snap path still holds.

## Files touched
- `KrakenOS/UI/services/open3d_face_assignment.py` — `_clear_aperture_record_center_normal`
  → `_clear_aperture_opening_center_normal` (now resolves manual OR auto-detect); body
  menu + pinned-opening menu offer the snap outside the manual-record gate.
- `KrakenOS/UI/validate_open3d_clear_aperture_snap_auto_detect.py` — new guard.
- `KrakenOS/UI/validate_open3d_clear_aperture_snap_from_record.py` — updated for the rename.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — Phase 300 (+ Phase 298
  docstring).
- `tools/penta_validator_baseline.json` — Phase 300 = pass.
- `bugs/probe_0344_led_auto_ca_snap.py` — headless root-cause probe.
