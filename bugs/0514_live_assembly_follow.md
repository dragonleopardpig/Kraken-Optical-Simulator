# 0514 — glued assemblies follow the drag LIVE (BS->LED, lens->surrogate, sources)

Flags `flag_20260802_210122_674` ("Glued the BS cube, drag it, the BS move
first, then the LED next, they should go together live as an assembly") + the
user's verbal AZ85 report ("the LENS body move first, the lens surrogate come
next"). One defect class: per-frame commits move the MODEL (or the model
catches up at release), but only the dragged actor is translated live --
partners, surrogate rows and glued sources jump at mouse-up.

## Mechanism

* `translate_step_overlay` records **breadcrumbs** (`_last_translate_row_shifts`
  + `_last_translate_source_shifts`, reset per call) in every row-moving branch:
  the atomic station write (members + BS row), the folded lens leg slide, the
  unfolded axial redirect (front datum .. end), the detector redirect, and the
  glued-source carry.
* `Kraken3DInspector._apply_translate_row_shift_breadcrumbs` translates the
  DRAWN actors for those rows/sources (render deferred), applied per frame by:
  - the STEP whole-body carry (`_apply_step_carry_motion_delta`) -- so the lens
    surrogate (folded AND unfolded) and the LED-drag station rows track live;
    the glued-BS row is excluded there (the 0137 mirror already moves it);
  - the ROW carry of the GLUED BS (`_apply_row_carry_drag_motion`): each frame
    now routes the model write through `translate_step_overlay("led", ...)` --
    the same 0508 B assembly gesture the release commit used -- then mirrors the
    LED body (0137 helper, bidirectional) + breadcrumb rows/sources. Without
    this the per-frame vector write (record_history=False = the 0437 internal
    layer) moved the BS alone and the LED teleported at release.

Alt: the placement-ARROW drag keeps its captured `alt_suspend_glue` seat-move;
the body-carry of a glued BS is always the assembly gesture (seat adjustments
use Alt+arrow).

Guards: `validate_open3d_glue_live_actor_carry` section C pins the wiring
(row-carry -> LED translate + breadcrumbs; step-carry -> breadcrumbs; applier
reads both lists); 0512's A2b pins source breadcrumbs; phase 409's B3 pins the
0513 rebuild marker. Live rendering itself is headless-unverifiable -- in-app
eyeball owed on all three gestures.

## Follow-up — the placement-ARROW drag was the remaining "one after another"

User (post-0514): "they move together after glue, but one after another, they
don't move together as an assembly live." The ARROW gizmo drag was the one
gesture still unwired: it previews with pure actor transforms and commits the
model ONCE at release, so the BS tracked the arrow while the LED + sources
teleported at mouse-up -- sequential at human timescale. The arrow motion now
previews the glued LED body (0137 mirror) + glued source glyphs with the same
per-frame vector, gated on the glued BS row and `alt_suspend_glue` (Alt keeps
the 0437 seat move); the release commit's rebuild reconciles exact placement.
Station/object rows still land at release on this path (far from the gesture;
promote if flagged). Guard: live_actor_carry section C gained the arrow-drag
contract.
