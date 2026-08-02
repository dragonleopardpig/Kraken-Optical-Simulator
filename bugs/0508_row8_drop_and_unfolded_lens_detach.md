# 0508 — three 13:2x flags: live-only row-8 drop; unfolded lens detach; BS-drag semantics

All on build `36ddd3cd` (current). Evidence gathered 2026-08-02 13:30-13:45; fixes NOT started.

## A — `flag_20260802_131958` "dragged the LED left, the rays go pass the camera sensor"

The E2 signature again: Image row exactly one mirror->image thickness (44.11) below the sensor
(row 8 cz -26.38 vs sensor blend +17.73). The recording pins the trigger ORDER: two PERPENDICULAR
LED drags first (row 8 correctly rode the fold: -5.1 -> 2.7 -> 17.7), then a STATION x-drag
dropped it to -26.4; a second x-drag left it stable. **Headless replay of the exact z,z,x
sequence with a system rebuild per step does NOT reproduce** (row 8 holds 17.72) — the drop needs
a live-only ingredient (inspector refresh order / async worker replay / a probe failing only in
the live system state). Also observed in the flag state: the row-0 ACTOR at x=-30.24 while the
axis/object anchor is at -64.7 — a 34.5 mismatch (suspiciously the 11:0x session's mirror-slide
amount; check whether `_surface_reference_world_point(0)`'s transforms[0] is non-identity there,
which would make the bugs/0505 lateral add double-count). Next: replay the RECORDING's real Tk
events (the 0503 method) against the live inspector, and dump `frame_source` from the follower
builder at the failing rebuild — if it reports the fallback, log WHY the probe trace died.

## B — `flag_20260802_132302` "glued BS cube to LED, moved BS, the LED not moving"

BY DESIGN per bugs/0437, from the user's OWN earlier flag (flag_20260726_110337: the symmetric
carry "effectively cancelled the BS plate move"): the BS is the child seated in the housing —
dragging it repositions it RELATIVE to the LED; dragging the LED moves the assembly. If the
expectation has genuinely changed, that is a product decision to revisit 0437 (e.g. modifier-gated
assembly drag from the BS side), not a regression.

## C — `flag_20260802_132419` "glued lens to surrogate, drag lens STEP, surrogate not moving —
is the fix general or specific to certain file only?"

Fresh UNFOLDED nominal-axis scene (imports + Add-BS-cube this morning): lens body slid to
z[436.3, 492.6] while the surrogate rows stayed (rows ~397-454) — detached. The honest answer to
the user's question: the 0499/0503 row-carry only fires on a FOLDED leg (`_lens_leg_slide_plan`
gate `plan[2]`); an unfolded scene relies on the OLDER thickness redirect, which is gated on
`overlay_on_axis`, `abs(delta[2])>1e-9`, AND a row-NAME search ("front"+"datum|edge") — and may
not be reached at all if this drag committed through the CARRY path (carry_finish_transition)
rather than the translate gizmo (never verified in 0503). So: general on folded machine-vision
scenes, NOT yet general on this import path. Next: reproduce on this scene shape (import lens ->
glue -> drag via BOTH carry and gizmo), then unify: make the leg slide use the SAME row-carry
mechanism for the unfolded root leg (rows_along_leg on axis:root between the datums) instead of
the name-matched thickness redirect, and route the carry commit through translate_step_overlay.
