# 0151 — the Object→LED distance dialog must edit the LIVE distance, not the raw knob

> **Provenance:** re-applied from M90aPro-local commit `6a16649` (originally numbered
> **0135**) after the cross-machine branch divergence — origin's 0135 is an unrelated
> clear-aperture bug, so this work was renumbered to 0151. The source fix cherry-picked
> onto current HEAD cleanly; only the penta phase + baseline were re-authored (phase **139**).

## Symptom

`flag_20260624_203712_059` — "changing the thickness of Object LED via dialog pop up is
**not working**." (Newest flag in `recording_20260624_203801.json`, after a fresh app
restart.)

The user had centred the LED on the optical axis, glued a promoted BK7 beam-splitter solid
to it, then **carry-dragged the LED −71.34 mm in Z**. The amber **"Object → LED = 128.7
mm"** dimension read the new live distance. Opening the dialog on that arrow and typing a
new distance did not put the LED where they typed — it landed ~71 mm short.

## Root cause

The LED has **two independent Z mechanisms** that add:

* `led_object_edge_distance_mm` — the "knob" the edge-distance dialog writes; drives the
  base placement via `_led_step_z_translation() = max(knob, 0) − led_step_object_edge_local_z`.
* `placement_offset_xyz.z` — what a free **carry-drag** of the LED body adds, applied on top
  in `_cad_mesh_aligned_to_optical_axis` (`target_front_z + placement_offset.z`).

A carry-drag adds `offset_z` **without** rewriting the knob, so the live object→LED distance
the amber arrow shows is

```
live_distance = led_object_edge_distance_mm + placement_offset_z      # open3d_thickness_dimensions.py (bugs/0125)
```

After the −71.34 drag the knob was still 200 while the arrow (and the LED's real edge) sat
at `200 + (−71.34) = 128.7`. But `set_led_edge_distance` **prefilled and wrote the raw
knob**:

* the dialog opened showing **200**, not the 128.7 the user could see; and
* typing `V` set `knob = V`, so the live edge became `V + offset_z = V − 71.34`, not `V`.

So typing 100 dropped the LED edge to 28.66 mm — "not working."

`bugs/repro_0151_object_led_dialog.py` reproduces it exactly (live shows 128.7 mm — the
recorded value — and typing 100 lands 28.66 mm; error = the drag offset).

## Fix

`set_led_edge_distance` (scene_placement_commands.py) now reconciles the drag offset:

* **prefill** the dialog with the live distance `knob + offset_z` (so it opens on the 128.7
  the user sees); and
* on commit write `knob = typed − offset_z`, so the live distance becomes exactly the typed
  value.

`placement_offset` is deliberately left untouched. The bugs/0133 glue-carry
(`_carry_led_glue_over_translation_change`) derives its shove from the
`_led_step_z_translation()` delta — which **excludes** `offset_z` — so writing
`knob = typed − offset_z` makes that delta equal the LED edge's *net* world move
(128.7 → 100 = −28.66), and the glued beam splitter follows by the same amount instead of
drifting. Undragged scenes (`offset_z = 0`) are unchanged: the fix is a no-op.

## Guard

`KrakenOS/UI/validate_open3d_object_led_distance_dialog.py` (display-free; binds the real
`set_led_edge_distance` + glue/carry methods onto a tk-free fake editor with the Tk prompt
stubbed). Checks: **A** post-drag edit lands the live distance at the typed value; **B** the
dialog prefills the live distance not the raw knob; **C** undragged edits are unchanged;
**D** a glued BS follows the LED's net edge move (−28.66), not the raw knob delta; **E**
source contract (offset reconciliation + glue carry both present). Penta phase **139**;
baseline regenerated. In-app eyeball owed (the embedded-VTK arrow click + Tk dialog can't be
driven headless).
