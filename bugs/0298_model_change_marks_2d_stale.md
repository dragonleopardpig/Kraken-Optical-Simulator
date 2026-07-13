# 0298 — "I clicked Done 2D, 2D not refreshing"

User report (2026-07-13), on the AZ85 RA-mirror scene: after removing the defocus in the 3D
inspector, clicking **Done 2D** left the main 2D layout showing the OLD prescription.

## Root cause

"Done 2D" is `Kraken3DInspector.finish_stl_placement`, and it re-plots the 2D **only** when
`_stl_placement_dirty` is set:

```python
def finish_stl_placement(self) -> None:
    if self._stl_placement_dirty:
        self.editor.refresh_plot(suppress_analysis=True, ...)
        self._stl_placement_dirty = False
    self._on_close()
```

The action the user took — right-click → **"Snap detector to image plane (remove defocus)"**
(`_snap_detector_to_image_plane`) — rewrites the Image row and retraces the 3D, but never marked
the 2D stale. So the flag stayed False, Done-2D skipped its re-plot, and the 2D kept the old layout.

An AST audit of `Kraken3DInspector` found **eleven** methods with exactly that shape — they call
`refresh_from_editor(force_retrace=True)` (i.e. the prescription changed) but never mark the 2D:

| method | what it changes |
|---|---|
| `_snap_detector_to_image_plane` | Image row → best focus (**the reported one**) |
| `_finish_detector_carry_drag` | detector dragged along the axis |
| `import_machine_vision_lens_from_folder` | a whole lens surrogate |
| `add_illumination_led_source` | a scene source |
| `glue_selected_step_to_surrogate` | glue / pose |
| `_open_measure_value_editor` | an edited measured distance |
| `_register_branch_detector_camera` | sensor coupling |
| `_register_image_plane_camera` | sensor coupling |
| `_attach_surrogate_wavefront_map` / `_clear_surrogate_wavefront_map` | wavefront map |
| `_apply_step_overlay_resize_solve` | resized STEP geometry |

This is the **third** time this bug has been reported: bugs/0248 patched the QE solve paths, and
bugs/0296 patched the STEP import/delete — each time a single instance, never the invariant.

## Fix

Pin the invariant instead of the instance. `_apply_model_change()` does both halves together:

```python
def _apply_model_change(self, *, sampling_mode: str | None = None) -> None:
    self._mark_2d_layout_stale()
    self.refresh_from_editor(sampling_mode=sampling_mode, force_retrace=True)
```

All eleven methods now route through it, and the guard **fails** if any `Kraken3DInspector` method
forces a retrace without the pairing — so a twelfth action cannot regress it silently.

## Result (real Tk app, `bugs/diag_done2d_refresh.py`)

Load the scene → open 3D → "Snap detector to image plane (remove defocus)" → Done 2D:

| | before | after |
|---|---|---|
| rows after the snap | `[…, 150.368, **-8.518**, 0]` | same (the snap always worked) |
| 2D marked stale | **False** | **True** |
| Done-2D re-plotted | **No** | **Yes** |
| 2D layout `xlim` | `(-47.004, 94.131)` — stale | `(-6.752, 91.149)` — current |

## Guard

`KrakenOS/UI/validate_open3d_model_change_marks_2d_stale.py` (display-free, AST), penta **phase 262**:

* **A** INVARIANT — no inspector method forces a retrace without marking the 2D stale.
* **B** HELPER PAIRS BOTH — `_apply_model_change` marks *and* retraces.
* **C** THE REPORTED ACTION — the best-focus snap routes through it.
* **D** DONE-2D STILL GATES ON THE FLAG — `finish_stl_placement` re-plots only when dirty
  (bugs/0248's contract is preserved, so the flag stays the single "2D is out of date" signal).

Note: `validate_open3d_interaction_workflows` fails on this branch **before** this change too
(pre-existing, unrelated: "4. Snap STEP face to optical axis").
