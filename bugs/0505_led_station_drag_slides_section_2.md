# 0505 — dragging the glued LED+BS should slide the OBJECT with it: a pure section-2 edit

User requirement, 2026-08-02 (mid-session, verbatim intent): dragging the glued LED+BS left/right
on the folded AZ85 (or any folded scene) should move the OBJECT together with it, because that
gesture is "effectively constraint distance for section 2" (of the 4 thickness sections). There is
currently NO pure-graphical way to change section 2 alone: a lens drag (bugs/0499) trades section
2 against section 3, and there is no select-all-downstream-and-drag.

Sections on the AZ85: s1 = object→BS 54.459, s2 = BS→lens (front datum) 93.825 (on the current
saved file), s3 = rear datum→mirror 81.229, s4 = mirror→image 58.881. Per bugs/0437 the BS drag
stays a RELATIVE seat inside the housing; the LED (parent) drag is the "move the whole
illumination station" gesture, so this feature keys on the LED drag.

## Measured findings (probes, 2026-08-02 ~00:45)

**The fold-emission physics is right, and it kills the naive design.** Translating the BS row +20
along world x — via raw desp AND via `translate_scene_row_pose_vector` (both write raw desp; they
agree) — moves `axis_fold_emissions`' origin from [0, 0, 53.803] to [0, 0, **33.803**]: x
unchanged, z −20. That is CORRECT physics: the fold point is the intersection of the INCOMING beam
with the plate diagonal {z = x + c}; move the plate +20 in x and the incoming ray (still at x = 0)
meets it 20 earlier in z. A lone BS x-slide therefore does not edit section 2 — it slides the fold
point down the incoming axis and the emitted leg then runs at z = 33.8, missing the lens datums at
z = 53.8.

**The root leg is pinned nominal.** For the station slide to work as imagined (object+BS+LED all
+Δx ⇒ fold point moves to (Δx, 53.8) ⇒ s1 const, s2 −Δ, s3/s4 const), the INCOMING axis must come
down at x = Δ — i.e. the ROOT leg must follow the object row's decenter. It does not: the drawn
`axis:global` and the emissions' incoming axis stay at x = 0 regardless of the object row's desp
(an object decenter is a FIELD shift in this engine, not an axis move). Moving object+BS desp
alone produces a model whose row poses look right (`row_world_pose` respects desp; s1/s2 by pose
arithmetic look correct) while the actual fold/trace geometry disagrees — a trap: pose arithmetic
over `row_world_pose` is NOT sufficient validation for this feature; assert on
`axis_fold_emissions` origins too.

## Two sound formulations

**A — downstream march (fits today's machinery).** The identical relative edit: translate every
row DOWNSTREAM of the BS (lens datum block, aperture, BBs, mirror, image — the 0499/0491
leg-frame desp moves, which are proven there) by −Δ along the emitted leg, carrying their bodies.
s2 changes by −Δ, s1/s3/s4 hold. Drawback: the user drags the LED right and watches the
lens/mirror/camera march left while the dragged body stays put — the opposite of the requested
visual ("the object should move together").

**B — station move (needs engine support).** Make the emission's incoming axis (and the drawn
root leg) follow the object row's lateral position, so object+BS+LED desp moves realize the slide
directly. Touches the axis-tree root derivation, trace aiming, snaps and the frozen-fold override
records — an engine change to design deliberately, not to patch in at 1 am. Note the BS row on
this scene is a frozen-fold participant (`is_fold_override` in the flag diagnostics), so the
override path may already provide an anchor for "the emission origin is HERE" that formulation B
could set explicitly per drag — worth checking first, it may make B small.

## Also folded in when this ships

* The LED glue reference then needs the same relative treatment as the lens (bugs/0503): anchor
  the recorded LED reference to the station (e.g. the object row's world pose), persisted like
  `step_glue_reference_datum_mid_xyz`, so glue-after-station-slide stays a no-op. The generic
  anchor table from 0503 already supports per-label anchors.
* The 0503 lesson applies verbatim: the drag commit must set `_fold_carry_pending_rebuild`.
* Guard: sections via `axis_fold_emissions` origins AND row poses; LED/BS/object rigid; lens
  datums/mirror/image unmoved; perpendicular drag keeps today's behavior; trace still lands.

## Status — formulation B SHIPPED for the model/axes/glue; trace launch is the remaining gap

User chose B ("the station follows the drag"). Shipped 2026-08-02:

* **`axis_root_origin(rows)`** (nonseq_output_ports) — the ROOT axis is the line the OBJECT
  emits, anchored at the object row's lateral position. Consumed by `axis_fold_emissions`, both
  production `build_axis_tree` call sites, and the drawn `axis:global` guide. Zero change for
  every centred-object scene.
* **`_led_station_slide_plan` + the station write in `translate_step_overlay`** — a glued-LED
  drag's leg component moves object-side rows AND the BS row as ONE atomic write with the
  bugs/0485 fold-slide carry suppressed (`_suppress_fold_slide_carry`): the net fold point is
  unchanged by construction, and letting the carry fire on the BS's half dragged the whole split
  leg through the inconsistent intermediate state (measured: −20 mm in z). The ordinary LED→BS
  carry receives only the perpendicular remainder. Sets `_fold_carry_pending_rebuild` (0503).
* **LED glue anchored to the station** — `_led_station_anchor_world` (the object row's world
  pose) rides the generic 0503 anchor table and its persistence; glue after a station slide is a
  no-op, glue after a perpendicular housing displacement returns exactly onto the slid station.

Measured on the AZ85 (guard `validate_open3d_0505_led_station_drag_slides_section_2.py`, penta
phase 408): LED +20 along the leg → object, LED and the FOLD POINT all +20 at constant height;
lens datums / mirror / image unmoved; s1 53.803 → 53.803, s2 93.701 → 73.701 — the pure
section-2 edit. The drawn `axis:global` guide follows the station (screenshot-verified).

**Remaining gap — the TRACE still launches from the nominal axis.** Measured live: after the +25
station slide the imaging fan still leaves from x = 0, folds at the moved diagonal 25 mm below
the arm, and `target_termination` collapses 129 → 0 (`no_next_intersection` 320 → 520). The
launcher (`_default_nonseq_reference_bundles_from_settings` and the first-order/field aiming)
needs the same `axis_root_origin` anchor — this is precisely the known "non-seq first-order
pupil seam" (universal first-order reference), which this feature turns from a design note into
the next required fix. Until it lands, the station slide is geometrically correct and fully
drawn, but the traced rays vanish after a slide.
