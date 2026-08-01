# 0503 — the leg slide moved the model and nothing redrew; glue restored an ABSOLUTE pose

`flag_20260801_220951` — *"quit Kitty, relaunched the app, glued lens, seems glue function not
doing anything. Still detached after drag right."* and `flag_20260801_221613` — *"right click lens
body glued to surrogate seems not functioning, lens body and surrogate detached after dragging the
lens to the right."* Both on build `6b7c9447`, which already contains the bugs/0499 fix — and the
0499 guard passes. The pair is what the 0499 fix looks like from the outside when the DRAWING and
the GLUE are the parts that are broken.

## What the recording proves

`recording_20260801_221711` captured the whole gesture with per-event model state:

```
t= 6.6s  click on the lens          pose 97.4064   actor 97.406    (glued, model == drawing)
t=11.9s  grab the translate arrow   pose 97.4064   actor 97.406
t=13.3s  release after +187 px      pose 97.4064   actor 131.608   (cheap actor translate)
t=14.0s  next click                 pose 131.6076  actor 131.608   (commit ran: delta +34.2012)
t=18.9s  flag                       pose 131.6076  actor 131.608   rows drawn at 71.66 -- STALE
```

187 px at the recorded `camera_parallel_scale` (120.08 over 1264 px) is 5.263 px/mm → 35.5 mm ≈
the committed 34.2. Replaying the events byte-for-byte through the real Tk bindings (same camera,
same widget size, same coordinates) reproduces the identical commit — `offset x 97.4064 → 131.6076`
— **with the surrogate rows correctly carried** (+34.2 on rows 1/2/4/5/6). The 0499 redirect was
working the whole time. What failed was everything around it.

## Defect 1 — the drawing never caught up (the flagged "detached")

`translate_step_overlay`'s leg-slide branch moved the ROWS but did not set
`_fold_carry_pending_rebuild`. The commit's own refresh is scoped to the dragged STEP label
(`_refresh_open_3d_views(step_label="lens")`), which repaints the body and nothing else. The
bugs/0493 release flush — written for exactly "the model carried while every actor stood still" —
is keyed on that marker, so it no-opped. And with Show Rays OFF (the user's state,
`show_rays: false` in the flag snapshot) there is no background-trace completion to ever trigger a
full repaint either: the stale picture was *permanent*, which is why both flags six minutes apart
show the rows drawn at x 71.66 while the model had them at 105.86.

The same gap hid the earlier session's slide too, which is what made the GLUE look broken: by
22:15:55 the model+drawing agreed at the glued pose again, but the user had watched a "glue" that
(correctly, per its then-semantics) moved nothing they could see.

**Fix**: the leg-slide branch now sets `_fold_carry_pending_rebuild = True`, invalidates the
preview trace and syncs the table — the same duties the neighbouring thickness-redirect branches
already perform. The 0493 release flush then promotes the first post-drag refresh to a full
rebuild. Verified live by replaying the recorded events: the drawn row actors are at the slid
station at the moment of release (105.861, no idle wait), and the ray bundle refracts at the
body's new position.

## Defect 2 — glue restored an ABSOLUTE pose (the "glue does nothing / manufactures a detach")

The bugs/0497 reference is where the body was PLACED — *relative to where its surrogate SAT then*.
Once a leg slide (or a fold carry) has legitimately moved the surrogate rows, restoring the
reference verbatim seats the body on the ORIGINAL stations, 28.7 mm from the surrogate the user is
looking at. Tonight that produced: slide (+28.69, rows carried) → glue → body yanked back to
x 97.406 while the surrogate sat at 100.35/155.35 — a glue that *creates* the detach it exists to
undo.

**Fix**: the reference is re-expressed against the surrogate datum midpoint as it sits at glue
time: `target = reference + (mid_now − mid_then)`. `mid_then` — the midpoint the reference was
recorded against — is persisted beside the reference (`step_glue_reference_datum_mid_xyz` in the
layout settings) and seeded for older layouts from the freshly loaded rows (reference == saved
placement and rows == saved rows there, so the pair is consistent by construction;
`load_layout_by_name` assigns `self.rows` before `_apply_layout_settings`, so the datums are
readable at seed time). When the surrogate has not moved, `mid_now == mid_then` exactly and 0497's
exact-restore guarantee is unchanged.

Consequences that fall out correctly:

* after an ATTACHED slide, glue reports "already glued" instead of yanking the body 34 mm back;
* a lateral detach still glues back exactly (residual 0.000000 mm) — onto the slid surrogate;
* a body stranded at the absolute reference by tonight's old glue is repaired by one glue click;
* a layout SAVED after a slide reloads with the pair still consistent (the E-section round trip).

The 0497 guard's B-section expectations were updated for the new semantics: "exact" now means the
same relative placement on the (possibly slid) surrogate, not the original world coordinates.

## Defect 3 — undo detached them (latent, found while fixing)

The first cut of 0499 mutated the rows BEFORE `_begin_history_capture()`, so the undo snapshot
already contained the moved rows: Ctrl-Z restored the offset but not the optics — an undo that
detaches. The row mutation now happens inside the capture, next to the thickness redirects.

## The "right click seems not functioning" part

Neither recording contains a single button-3 event (`right_press` records them), and
`right_click_diagnostics` is empty — the right-clicks happened before each recording started, and
the complaint reads as "the glue action's OUTCOME was nothing", which is defect 2 (plus defect 1
hiding the one time it did act). No evidence of a context-menu failure; nothing to chase there.

## Guards

* `validate_open3d_0503_leg_slide_redraw_and_relative_glue.py`, penta phase 405 (display-free):
  slide carries rows AND sets the rebuild marker; glue is relative (already-glued after an attached
  slide, exact reattach after a lateral detach, gap-to-datum preserved); the stranded-at-absolute
  state repairs; undo restores rows+offset together; the reference/anchor pair survives a REAL
  save/reload through `_write_layout_file`.
* `validate_open3d_0497_glue_restores_the_recorded_placement.py` (phase 402) updated to the
  relative semantics, plus C3 for the persisted anchor.
* Phases 402–405 smoke-run green; live replay of the recorded flag events verified the drawn rows
  follow at release, with before/after screenshots.

## Still open (inherited notes)

* The LED still takes 0497's destructive zeroing path ("glue" clears its offsets outright).
* bugs/0500 (lens STEP orientation at import) remains not started.
