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

## Status

Design captured, NOT implemented — blocked on choosing formulation A (works today, wrong visual)
vs B (right visual, engine change; check the frozen-fold override anchor first). The probes above
are the evidence base.
