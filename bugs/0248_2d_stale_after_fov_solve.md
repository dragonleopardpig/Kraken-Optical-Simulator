# 0248 — Main 2D layout stays stale after a Quick-Estimation solve / FOV / constraint apply

User report (refer `attachment/2D.png`): *"After you have done, there is one bug I missed
out just now after the 55x55mm FOV, refer attachment/2D.png, the 2D did not update after
Done 2D or Close."*

The user, inside the Open 3D inspector, set a **55×55 mm Target FOV**, pinned the
**object-to-RA-mirror = 50 mm** and **image-side-last-surface-to-RA-mirror = 50 mm**
constraints, and solved for thickness. The 3D inspector updated, but on returning to the
main window via **Done 2D** or **Close** the main 2D matplotlib layout (title
"YZ full 3D") still showed the *pre-solve* geometry.

## Root cause

Done-2D (`finish_stl_placement`) and Close (`_on_close`) only redraw the main 2D when the
`_stl_placement_dirty` flag is set:

```python
def finish_stl_placement(self):
    if self._stl_placement_dirty:            # ← gate
        self.editor.refresh_plot(...)
        self._stl_placement_dirty = False
    self._on_close()
```

That flag is a **perf gate** first built for the STL/CAD placement flow (so a look-only
inspector session doesn't pay a slow 2D redraw on close). It is set in ~13 STL/CAD
placement paths — but **not** in any of the five Quick-Estimation / solve actions:

* `_quick_estimation_snap_to_fov` (Snap to FOV)
* `_open3d_run_thickness_solve` (Solve for Thickness)
* `_apply_quick_estimation_fov_solve` (FOV-solve dialog — the 55×55 + segment pins)
* `_apply_design_constraints`
* `_apply_placement_constraints` (object/image-to-RA-mirror pins)

Each of these rewrites the prescription — `editor.rows[...].thickness` (QuickEstimation
`snap_to_fov`/`fov_solve`/`apply_design`/`apply_placement`, and the thickness solver) — and
retraces the **3D inspector** via `refresh_from_editor(force_retrace=True)`. But none marked
the main 2D dirty, so the `_stl_placement_dirty` gate stayed False and Done-2D/Close skipped
the `editor.refresh_plot(...)`. The 2D went stale. Classic "display must follow the physics":
the model changed but one of its two views was never told.

## Fix

Add a single self-documenting helper and call it from the five producers' success paths:

```python
def _mark_2d_layout_stale(self) -> None:
    """... reuses the STL-placement gate as the single 'main 2D is out of date' signal
    both finish_stl_placement / _on_close check."""
    self._stl_placement_dirty = True
```

Placement is **surgical**: the flag is only set when the service actually reports success
(`if ok:`), so a failed/rejected solve does not force a spurious redraw. Centralising in
`refresh_from_editor(force_retrace=True)` was rejected — that funnel also fires for
view-only refreshes (ray show/hide restore at open3d_inspector.py ~7101/7202, drag
movements ~3357/3426), which would over-trigger the 2D redraw on a look-only Close.

The `_stl_placement_dirty` name is STL-centric but is reused rather than renamed: the flag
is referenced by name in a service (`services/open3d_face_assignment.py`) and asserted as a
source string in `validate_3d_interaction_contract.py`, so a rename has real blast radius
for zero behavioural gain. The helper name (`_mark_2d_layout_stale`) carries the intent at
the call sites.

## Guard

`validate_open3d_2d_refresh_after_solve` (display-free, penta **Phase 224**) binds the real
`Kraken3DInspector` methods to a light fake `self` (fake editor + fake QuickEstimation /
solve services):

* **A** — each of the five producers marks the 2D stale on a successful apply.
* **B** — a FAILED apply (`ok=False`) does NOT mark it (gate stays on a real change).
* **C** — `_mark_2d_layout_stale` sets the shared gate.
* **D** — Done-2D with the flag set calls `editor.refresh_plot` and clears the flag.
* **E** — Done-2D with the flag clear does NOT redraw (the perf gate still holds).
* **F** — Close schedules a post-close 2D redraw iff the flag is set (and the scheduled
  callback really calls `refresh_plot`).
* **G** — source contract: all five producers still call `_mark_2d_layout_stale()`.

## Notes

* Neighbouring inspector actions that also mutate model state without marking the 2D
  dirty — `_register_branch_detector_camera`, `_snap_detector_to_image_plane`,
  `_register_image_plane_camera` (open3d_inspector.py ~15823/15839/15905) — are the same
  bug class but were **not** reported; left out to keep the fix scoped to the reported
  workflow. Worth folding into the same helper if they surface.
* In-app eyeball owed only in the sense of confirming the 2D visibly redraws after the
  user's exact 55×55 workflow; the wiring is proven headless.
