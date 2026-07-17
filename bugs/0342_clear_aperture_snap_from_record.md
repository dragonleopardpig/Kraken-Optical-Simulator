# bugs/0342 — can't right-click "Snap CA → Optical Axis" after setting the CA

**Flag `flag_20260717_142550_484`** (latest live test, imported LED):

> "still can't right click snap CA to optical axis even though I set the CA first,
> then right click again to snap."

## The defect

The center+normal **"Snap Clear Aperture → Optical Axis (center + normal)"** command
(bugs/0333/0337) was reachable only in two situations:

- the right-click landed **exactly on the see-through opening** (the
  `opening_feature` plain-hover pick supplied its centroid + normal), or
- a clear-aperture **opening was pinned** (bugs/0334), whose pinned rim carried the
  normal.

But the user's flow is: **Set Clear Aperture (pick window face)…** → then right-click
to snap. `_apply_step_clear_aperture_pick` finishes with `refresh_from_editor()`,
which **rebuilds the scene and drops the pin**. The follow-up right-click then lands
on a **housing face**, not the recessed see-through hole — the flag's diagnostics show
`prior_hover_key = "('step','led','F053')"` (F053 is a body face; the CA is F266). So
`opening_feature` was `None` and the opening was un-pinned:

```python
if opening_feature is not None:      # cursor not on the opening -> skipped
    menu.add_command(label="Snap Clear Aperture -> Optical Axis ...")
```

The body menu still offered **"Center Clear Aperture → Optical Axis"** and **"Forget
Clear Aperture"** (gated on the CA record existing) — proof a CA record *was* set —
but **not** the full center+normal snap. "Still can't right click snap CA to optical
axis even though I set the CA first."

## Fix — snap straight from the persisted CA record (`open3d_face_assignment.py`)

Once the CA is **defined**, its centre + unit normal are known from the stored face
index — `_step_overlay_fine_face_centroid_normal(label, face_index)` on the current
transformed mesh. A new helper exposes that:

```python
def _clear_aperture_record_center_normal(self, label):   # bugs/0342
    record = self.editor.step_clear_aperture(label)
    resolved = self.editor._step_overlay_fine_face_centroid_normal(label, record["face_index"])
    centroid, normal, _area = resolved
    return centroid, normal      # or (None, None) if unresolved / non-finite
```

The **body STEP menu** now offers the snap from the record whenever a CA is set and
the cursor is *not* already on the opening (so it never duplicates the hover path):

```python
if self.editor.step_clear_aperture(step_label) is not None:
    if opening_feature is None:
        ca_center, ca_normal = self._clear_aperture_record_center_normal(step_label)
        if ca_center is not None and ca_normal is not None:
            menu.add_command(label="Snap Clear Aperture -> Optical Axis (center + normal)",
                             command=... self._snap_clear_aperture_to_optical_axis_from_context(...))
```

The **pinned-opening menu** gains the same record-based snap as a fallback for the
rare case where the pinned rim has no usable normal (`not normal_finite`). Both route
to the existing `_snap_clear_aperture_to_optical_axis_from_context` pipeline (which,
for the single-axis scene in the flag, finishes in one click via bugs/0337).

Invariant: **a DEFINED clear aperture is always snappable to the optical axis** — no
live opening hover, no pin required.

## Guard & regression

`KrakenOS/UI/validate_open3d_clear_aperture_snap_from_record.py` (penta **Phase 298**),
display-free:
- `_clear_aperture_record_center_normal` returns the record's world `(center, normal)`
  when the CA face resolves, and `(None, None)` for no record / unresolvable face /
  non-finite geometry;
- source contract (body menu): the record snap sits in the `step_clear_aperture(...)
  is not None` branch, gated on `opening_feature is None`, routing to
  `_snap_clear_aperture_to_optical_axis_from_context`;
- source contract (pinned-opening menu): a `not normal_finite` fallback resolves the
  same helper.

## Files touched
- `KrakenOS/UI/services/open3d_face_assignment.py` — new
  `_clear_aperture_record_center_normal`; body menu + pinned-opening menu offer the
  record-based snap.
- `KrakenOS/UI/validate_open3d_clear_aperture_snap_from_record.py` — new guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — Phase 298.
- `tools/penta_validator_baseline.json` — Phase 298 = pass.
