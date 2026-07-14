# 0305 — Save the whole 3D scene (visible + invisible items) and a Save As in 3D

Two follow-ups after the 0304 lens-edge highlight, both from the same session:

> *Now I put some manual measurement in the 3D, when I click Save Layout, are these manual thickness save as well?*

They were **not**. And then the requirement:

> *When clicked save, please save all visible and invisible items in the layout. Must exactly reproduce when re-opened.*
> *also add a Save As in 3D.*

## What already persisted vs. what did not
The layout `.py` is a standard KrakenOS prescription plus a `settings` dict (`_collect_layout_settings` /
`_apply_layout_settings`). That dict already carries the **heavy** scene state: STEP-overlay paths + rotations +
axis/placement offsets (camera/lens/optical/led), promoted solids (`row.advanced["StepOverlayPromotion"]` /
`Solid_3d_stl`, regenerated on open), scene sources / LED emitters (`scene_sources`), the BS↔LED glue flag,
per-STEP clear apertures, per-branch camera assignments, thickness-dimension re-anchor overrides, and per-row
thickness-dimension visibility.

What it did **not** carry is the **inspector-only** 3D-session state — everything that lives on
`Kraken3DInspector`, not on the editor:

* manual measurements — `_measure_segments` (each `p0/r0/dz0/n0`, `p1/r1/dz1`, `id`, and the user-nudged lane
  `offset`) and `_hidden_measure_segments`;
* per-item hidden state from the Scene Components browser — `_hidden_scene_rows`, `_hidden_step_labels`,
  `_hidden_source_ids`;
* the scene overlay toggles — rays, references, detectors, the field-aberration overlays (best-focus,
  distortion, astigmatism, spot map, pixel grid) and the illumination overlays;
* the camera pose.

So a save dropped exactly the things the user had just built in 3D.

## The fix — a 3D-session sidecar next to the layout
On Save / Save As the inspector writes a **`<layout>.open3d.json`** sidecar next to the layout `.py`
(`foo.py` → `foo.open3d.json`), so it travels with the layout (under the Filen-synced `attachment/`) and is
gitignored (`*.open3d.json`). It carries only the inspector-only state above — the heavy state stays in the
`.py` settings, never duplicated.

On **open**, when the 3D view builds the scene for that layout, the sidecar is loaded **once per layout file**
(guarded, so a routine Update never clobbers live edits):

* overlay toggles + hidden sets + measurements are set on the inspector **before** the rebuild — the scene
  refresh already re-draws measure overlays (`open3d_scene_refresh.py:1116`) and re-applies visibility
  (`:1130`) from inspector state on every rebuild, so they reproduce for free;
* the camera pose is **buffered** and applied **after** the rebuild, funnelled through `refresh_scene` so it
  covers both the synchronous and the async (worker-process) trace paths.

Restore is keyed on `editor.current_layout_file`; a save marks that path restored (the saved scene *is* the
live scene) so re-opening the same file mid-session does not reload over edits. A missing sidecar is a
harmless no-op (older layouts just open with an empty session).

**Save As in 3D:** the 3D toolbar gained a **"Save As"** button beside "Save Layout" (mirrors the main
window's File → Save As); a new inspector `save_layout_as()` forces the editor's Save-As dialog then writes the
sidecar next to the freshly chosen file.

## Files
- `KrakenOS/UI/open3d_inspector.py` — session helpers (`_open3d_session_sidecar_path`,
  `_open3d_session_state_dict`, `_capture_open3d_session_camera`, `_write_open3d_session_sidecar`,
  `_maybe_restore_open3d_session_state`, `_apply_open3d_session_state`, `_coerce_int_set`,
  `_apply_pending_session_camera`); `save_layout` writes the sidecar; new `save_layout_as`; restore wired into
  `refresh_from_editor`, camera apply into `refresh_scene`; `_session_restored_for_path` /
  `_pending_session_camera` init.
- `KrakenOS/UI/panels/open3d_top_controls.py` — "Save As" button.
- `.gitignore` — `*.open3d.json`.

## Verified (display-free — headless VTK segfaults under Xvfb llvmpipe)
- `KrakenOS/UI/validate_open3d_session_persistence.py` (`run_checks()`) — binds the real inspector methods to a
  fake `self` (fake Tk vars / camera / renderer) and proves a genuine JSON round-trip through a **temp sidecar
  file**: measurements (incl. lane `offset` + `n0=None`), all four hidden sets, three non-default overlay
  toggles, and the camera pose all restore; the camera is buffered then applied (and the buffer cleared); the
  restore **guard** does not re-fire for the same layout (no clobbering live edits); a sidecar-less layout is a
  no-op. Plus source asserts on the save / Save-As / restore / camera wiring and the toolbar button.
  **PASSED**.
- Penta **phase 268** (`phase_268_session_persistence`) delegates to that guard; baseline `"268": "pass"`.

## Notes / remaining
- In-app eyeball owed (needs a GLX display): in 3D, add a couple of measurements, hide a lens + a row, toggle
  an overlay, orbit the camera, **Save**; reopen the layout + Open 3D and confirm the scene reproduces exactly.
  Same for **Save As** to a new file.
