# 0078 — Open 3D: Face Editor slow to launch and slow "Save Roles" (re-read mesh + retrace per field change)

## Symptom (user's words)

> it takes long time for the face editor to launch, click save roles also takes
> long time. You might want to check as well any duplicate event/process.

## Root cause

Two hot paths in `panels/main_optical_solid_face_roles_dialog.py`:

1. **`render_face_preview` re-read the body mesh from disk every call.** It ran
   `transformed_mesh(pv.read(path).extract_surface(...))` **and**
   `extract_feature_edges(...)` on the full body on *every* invocation — and it is
   invoked on launch, on every face selection, and on every field auto-apply. The
   per-face candidate meshes were already cached (`candidate_mesh_cache`), but the
   base body + its edges were not, so each render paid the STL disk read + a
   feature-edge extraction.

2. **Every field change fired a full Open 3D retrace.** `auto_apply_selected_face_identity`
   is bound to the 2D-side / function / port / fit-reference comboboxes
   (`<<ComboboxSelected>>`) and the text entries (`<FocusOut>`, `<Return>`). Each
   fire called `persist_face_editor_metadata`, which ran
   `self._refresh_open_3d_views(force_retrace=True)` — a complete optical retrace +
   3-D scene rebuild. So one face edit (pick a function, then click away → FocusOut)
   triggered several full system retraces — the "duplicate event/process" the user
   sensed.

## Fix (display-only; trace + persistence semantics unchanged)

1. **Cache the base body mesh + feature edges** (`base_mesh_cache` +
   `base_body_raw_and_edges`): read from disk and edge-extracted **once** (both
   depend only on `path`, constant for the dialog's life). `render_face_preview`
   applies the cheap rigid pose transform per call, so a pose change still
   re-places the body, but the disk read + edge extraction no longer repeat.

2. **Debounce + coalesce the retrace.** `persist_face_editor_metadata` still saves
   the metadata to the row synchronously (no lost edits) but schedules the Open 3D
   retrace via `schedule_face_editor_retrace()` (a 250 ms debounce on the main
   editor loop), so rapid field changes collapse to a single retrace. The in-dialog
   3-D preview still updates instantly. **Save Roles** calls
   `cancel_pending_face_editor_retrace()` then does the one authoritative retrace,
   so there is never a double retrace on explicit save.

## Test

Source-regression guards added to
`validate_open3d_face_assignment_sampling_stability._validate_face_role_save_forces_stale_trace_rebuild`:
the dialog must carry `base_mesh_cache` + `base_body_raw_and_edges` and
`render_face_preview` must consume the cached base; auto-apply must debounce via
`schedule_face_editor_retrace`; Save Roles must `cancel_pending_face_editor_retrace`.
The pre-existing Save-Roles assertions (forces retrace, clears stale trace, saves
metadata immediately, FocusOut save) all still hold.

## Status: FIXED — pending in-app confirmation

Wall-clock launch/save speed is verified in-app (the dialog embeds a live VTK
renderer that SIGSEGVs the offscreen Xvfb llvmpipe path).
