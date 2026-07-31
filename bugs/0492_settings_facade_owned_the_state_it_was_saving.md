# 0492 — the settings facade owned the state it was saving

`flag_20260731_212326` (build `7f2c49bb`) — *"glued BS to LED, save layout, restart, still not
glued."*  A repeat of `flag_20260731_211244` on the previous build, so not a one-off.

## What the flag shows

The BS row reads `desp_z = -103.676` — exactly its as-loaded value — while the LED body sits where
the user left it.  The glue is genuinely off after the restart, and the relative pose of the two
bodies has changed by ~14 mm across the save/reload.  So the flag is about **persistence**, not
about the carry: nothing was going to follow the LED, because after the reload the app did not
believe the two were glued.

## Root cause

`LayoutSettingsService` is a facade over the editor.  Its `__setattr__` was:

```python
if name.startswith("_") or name == "editor":
    object.__setattr__(self, name, value)     # <-- keeps `_` names on the FACADE
    return
setattr(self.editor, name, value)
```

Three facts combine into the bug:

1. Python calls `__getattr__` **only when normal lookup fails**.  Once the facade owns
   `_optical_led_glued`, every later `getattr(self, "_optical_led_glued")` *inside the facade*
   finds its own copy and never reaches the editor.
2. `_apply_layout_settings` — which runs on **every layout load** — writes eight `_`-prefixed
   names.  So one load is enough to poison the facade.
3. The editor **caches** one facade instance (`_layout_settings_service_instance`) for its
   lifetime, so the poisoned copy never goes away.

Measured before the fix:

```
set_optical_led_glue(True) -> True | editor flag = True
facade sees                       = False
>>> value that SAVE writes to disk: optical_led_glued = False
```

The user glues, the editor records it, and the save reads back **the value from the last load**.

## It was not one key

Four persisted settings are written by `_apply_layout_settings` and read back by
`_collect_layout_settings`, so all four saved the previous load's value rather than the user's work:

| key | what it is | consequence |
| --- | --- | --- |
| `optical_led_glued` | the BS↔LED glue | the reported flag |
| `clear_aperture_edge_rects_by_label` | bugs/0379 physical clear-aperture **ray stops** | real vignetting silently dropped — physics, not cosmetics |
| `step_clear_aperture_by_label` | bugs/0134 per-overlay clear apertures | recorded CA window lost |
| `camera_precouple_stash` | bugs/0306 pre-camera field/aperture | ironic: 0306 added this **specifically** so a delete after save/reload could still un-couple the sensor |

Five more (`_cad_axis_pick_label`, `_cad_axis_pick_any`, `_cad_led_object_edge_pick`,
`_selected_step_label`, `_last_field_type`) were shadowed for any later read through the facade.

## Fix — remove the trap rather than patch around it

bugs/0449 met this exact trap from the *apply* side and worked around it: `_apply_layout_settings`
in `layout_table_workbench` re-asserts `self._optical_led_glued` on the editor afterwards.  That
fixed one name in one direction and left the read path intact, which is what this flag walked into.

A facade may now own `editor` and nothing else:

```python
if name == "editor":
    object.__setattr__(self, name, value)
    return
setattr(self.editor, name, value)
```

Applied to all six facades that carried the carve-out (`layout_settings`, `layout_file_writer`,
`tolerance_stackup`, `nonseq_scene_graph_records`, `legacy_3d_scene`, `ray_inspector_records`),
which makes all **14** delegating facades uniform.  `tolerance_stackup` was quietly diverging the
same way: it wrote `_last_tolerance_stackup_records` / `_summary` onto itself while
`layout_editor.py:2891` declares them and `render_layout_snapshot.py` + `saved_layout_plot.py`
*reset them on the editor* — a reset that could not reach the facade's copy.

## Guard — the invariant, not the instance

`validate_open3d_0492_settings_facade_holds_no_state.py`, penta phase 396.  Section A scans
**every** service class whose `__setattr__` forwards to `self.editor` and fails if any keeps
`_`-prefixed writes local or stores anything but `editor` on itself, so a facade added later cannot
reintroduce the trap.  Section B proves the mechanism display-free.  Section C drives the user's
gesture on the real scene: glue → save → reload → still glued, with the three other keys checked
alongside.  Run against the pre-fix code it fails 8 checks including
`C1: SAVE writes the glue the user made (False)`.

Two "failures" during investigation were bad fixtures, not code: a 0379 rect needs
`{center, normal, u_axis, v_axis, half_u, half_v}` and the 0306 stash restore is gated on a
non-empty `field_type`; a lazy fixture is dropped at *both* ends and round-trips as "empty in,
empty out", proving nothing.  The guard uses valid ones.

## Bearing on `flag_20260731_212425`

That flag ("dragged the glued BS and LED down, nothing follows") was recorded one minute later, in
the session started by the restart above — i.e. in an app that had **lost the glue**.  Its premise
is contaminated, and the recorded deltas agree: the LED moved +4.37 mm while the BS moved
+18.43 mm, which is not a rigid pair.  It needs re-recording on a build with this fix.
