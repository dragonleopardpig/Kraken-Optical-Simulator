# 0375 — A fresh lens/camera import is a transient unsaved layout, not the user's .py

**Flag:** 20260720_210130_962 (build e7812198) — "direct import of Apo 75 lens load the previously
saved layout, can remove it?" + user follow-up: "if there is no .py file created by user, clicking
save layout should prompt user to create one first. Layout always tie to .py file, not fresh lens or
camera import." **Status:** SHIPPED 2026-07-20 (guard `validate_open3d_import_unsaved_layout`, penta
phase 316).

## Why it happened

The folder importer auto-generates `machine_vision_<slug>.py` in the common-layout library and loads
it as the working scene, which set `current_layout_file` to that **generated** file. Two consequences,
both wrong:

1. **Stale session restored.** The 3D rebuild runs `_maybe_restore_open3d_session_state()`, which
   restores the layout's `<layout>.open3d.json` sidecar (previous camera pose, camera coupling,
   overlay toggles). A re-import of a lens you'd worked on before therefore came back with the *old*
   session — the zoomed, camera-coupled, half-broken-looking view in the earlier flag
   (20260720_201610) was this stale sidecar, not a fresh import.
2. **Save silently overwrote the generated file.** `save_layout` only prompted (Save As) when
   `current_layout_file is None`; after an import it was the generated `.py`, so Save wrote there and
   re-tied the session to it — the layout was tied to a fresh import instead of the user's own file.

## The fix — a transient-import marker

`_layout_is_unsaved_import` (bool). The lens importer SETS it `True` right after loading the generated
surrogate; a normal menu load (`load_layout_by_name`), `open_layout`, and a successful `save_layout_as`
CLEAR it (the layout is now tied to a real file). While it is set:

- **Save prompts.** `save_layout` treats a transient import like an unsaved layout and routes to
  `save_layout_as`, so the user creates their own `.py` (the session sidecar then lands next to *that*
  file). The generated `machine_vision_*.py` stays a library surrogate, still insertable.
- **No stale-session restore.** `_maybe_restore_open3d_session_state` returns early for a transient
  import (marking attempted, so no retry), giving a clean scene. `File>Open` of a real user layout
  (which clears the marker) still restores its session normally.

Camera folder import needs no change: it adds a camera to the *current* layout without touching
`current_layout_file`, so the marker is preserved (a camera dropped on a still-transient import stays
transient; on a saved layout stays saved).

## Also fixed here (pre-existing, tripped the gate)

`validate_open3d_import_from_inspector_survives` (penta phase 258, baseline-pass) had been latently
FAILING since bugs/0298 (`f458f586`) moved the inspector import handler's in-place refresh from
`refresh_from_editor(force_retrace=True)` to the canonical `_apply_model_change()`. The guard now
accepts `_apply_model_change()` as the refresh call (the "any 3D model change MUST use
`_apply_model_change`" invariant), falling back to the old form.

## Files

- `KrakenOS/UI/services/layout_import_export.py` — `save_layout` routing, `save_layout_as` /
  `open_layout` clear the marker.
- `KrakenOS/UI/services/layout_table_workbench.py` — importer sets the marker; `load_layout_by_name`
  and the fresh-layout reset clear it.
- `KrakenOS/UI/open3d_inspector.py` — `_maybe_restore_open3d_session_state` skips a transient import.
- `KrakenOS/UI/validate_open3d_import_unsaved_layout.py` — display-free guard (penta phase 316).
- `KrakenOS/UI/validate_open3d_import_from_inspector_survives.py` — accept `_apply_model_change()`.
