# 0101 — decoration STEP overlay (LED/camera) promoted as an optical solid

**Flagged:** `flag_20260622_085225_999` ("Unable to glue to LED after promotion"),
`flag_20260622_085300_094` ("Unpromoted, BS move back"),
`flag_20260622_092141_643` ("ray is not splitting anymore.") — 2026-06-22.
Live report: *"after I demoted the BS and dragged it to overlap the LED (NOT glued), right-click
direct assign BS splitting face takes super long time, and it is still doing."*

## Root cause (ONE bug, two symptoms)
The beam-splitter cube ("optical" overlay) was unpromoted and dragged so it **spatially overlaps the
LED** ("led" overlay). On the right-click "assign BS splitting face", the VTK cell picker returned the
**front-most actor under the cursor = the LED**, so `step_label` resolved to `"led"`. The right-click
menu happily offered *"Promote and set Partial Reflecting / Transmitting"* for **any** overlay label, so
the LED got promoted into an optical mesh-solid and a Beam-Splitter face was assigned to it.

Proof from the live debug log (`~/.cache/krakenos/logs/kraken_debug_latest.log`):
```
promoted_step_face_assignment_metadata_saved  face_id "F044"
function "Partial Reflecting / Transmitting"   label: "led"
metadata: {assigned_faces: 160, function_counts: {Beam Splitter: 1, Transmit/Port: 159}}
```

### Symptom 1 — "takes super long"
The LED STEP is a **160-face** complex CAD. Promoting it into the traced system makes the
non-sequential ray trace pathological. The timing log for the session:
- `trace_preview_bundle` 189 calls, **mean 5.1 s, max 87 s**.
- `preview_trace_rays` max **742 s**; `refresh_from_editor` max **769 s (12.8 min)**.
- Build was NOT the cost (build=1 mean 487 ms — the STL read cache works; mesh_collect 0 ms).
So the slowness is **ray-tracing the 160-face LED-as-optical-solid**, not building or the LED merely
being drawn (the un-glued LED is never auto-traced — only the "optical" overlay is, by design).

### Symptom 2 — "ray is not splitting anymore"
The Beam-Splitter face landed on the **LED** (F044), not on the BS cube. So the cube has no splitting
face → rays pass straight through to the camera; no reflect arm. (Confirmed against
`flag_..._085225` where the promoted cube DID split: reflect arm up + transmit arm right, two detectors.)

## Fix — decorations are not optical elements (commit pending)
A camera body and an LED source are **decorations**, never refracting/reflecting optical elements. This
already held for the *live-trace* path ("Only the generic optical STEP overlay becomes live-traceable",
`validate_open3d_live_transient_step.py`); the gap was the **manual promote / face-assign** path.

- `KrakenOS/UI/services/step_overlay_labels.py`: new `STEP_OVERLAY_DECORATION_LABELS = ("led", "camera")`
  + `is_step_overlay_decoration(label)`.
- `open3d_face_assignment.py`: the STEP-overlay right-click menu no longer offers *"Promote and set …"*
  or *"Promote to Optical Element"* for a decoration; it shows a disabled "… is a decoration" note and a
  **"Hide … STEP"** command instead (matches the user's ask: hide the LED like the Camera STEP, while
  hidden the heavy CAD is skipped in the rebuild). `_promote_step_and_assign_face_function` and
  `_promote_step_from_context` reject decoration labels defensively.
- `open3d_inspector.py::_promote_step_overlay_to_optical_solid_row`: the shared UI promote chokepoint
  (top-controls menu too) blocks decoration labels. The lower state-service method
  (`promote_imported_overlay_to_row`) is left intact so the import-accept validator is unaffected.

So a decoration can never be promoted/assigned as optics, regardless of overlap; if the user clicks the
LED in the overlap region they get "decoration / Hide" instead of silently fusing it into the beam path.

## Repro / test
`.devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_decoration_not_promotable`
— classifies led/camera as decorations (optical/lens not), and asserts the promote/face-assign paths
reject decorations while leaving the "optical" overlay promotable.

## Follow-up (not in this fix)
- The picker still returns the front-most actor on overlap; preferring the *optical* overlay/solid over a
  decoration when they overlap would let the user assign the BS without first hiding the LED. Deferred
  (geometry-containment pick is riskier); the Hide command is the interim path.
