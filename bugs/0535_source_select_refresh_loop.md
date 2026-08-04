# 0535 — selecting the new LED source armed an endless refresh loop ("drag seems freezed")

## Live report

User (2026-08-04, live session): added an LED illumination source from the browser panel,
tried to drag it, "it seems freezed. It is live now, can you check?" The logs showed the
app NOT hung but saturated: back-to-back full `refresh_from_editor` cycles at ~3.4 s each
(159+ cycles over 9 minutes, still running while idle), so every input queued behind a
rebuild and the gizmo drag felt dead.

## Diagnosis (py-spy on the live process)

```
_on_tree_select (panels/open3d_step_admin.py)
  -> select_scene_source_from_admin -> refresh_from_editor
     -> tree rebuild -> programmatic re-selection
        -> deferred <<TreeviewSelect>> (the 0049 mechanism, lands AFTER the
           _refreshing guard clears)
  -> select_scene_source_from_admin -> ...            # forever
```

`select_scene_source_from_admin` (the 0426 source-gizmo raiser) refreshed
UNCONDITIONALLY, and the browser's `source:` branch — unlike the generic branch right
below it — had no same-selection dedup. One click on the source row self-armed the loop.

## Fix

Idempotence at the one authority: re-selecting the CURRENT source with its gizmo already
raised (`_selected_source_id` matches, no row gizmo active, handles shown) is a no-op. A
genuine state change (another gizmo took over, handles hidden) still refreshes.

Verified: four consecutive re-selections → exactly ONE refresh; 10 s idle event pump →
zero refreshes; a re-select after a row gizmo took the handles still refreshes once.

## Unfreezing a live session

Click any non-source row (e.g. a category header) in the browser to break the cycle, or
restart the app.

## Guard

`validate_open3d_0535_source_select_idempotent.py` (penta phase 429).
