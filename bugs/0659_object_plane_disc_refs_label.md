# 0659 — "All overlays off, why still have a big green circle?"

**Flags (2026-08-27 15:30/15:31):** `flag_153045` "original: everything correct?"
(the #85-869 35 mm scene — yes: rays land, m = 0.169 = sensor/FOV ✓) +
`flag_153106` "all overlays off, why still have a big green circle?"

## Finding: the mechanism is CORRECT; the label was the bug

The big green circle is the **Object-plane reference disc** (row 0), sized to
circumscribe the FOV (semi-diagonal 32.6 mm for the 50×41.8 field — hence "big").
Its visibility is gated by `show_reference_surfaces_var` — the Overlays-menu
checkbox labelled just **"Refs"**.

Repro on the user's own scene proved the gating works on BOTH refresh paths
(display-toggle fast path AND full refresh): Refs off → the disc hides, actor gone.
The flagged state snapshot shows the row-0 actor still `visible=1` — i.e. the
"Refs" box was still ticked; nobody connects the word "Refs" to the object plane,
so an "all overlays off" sweep skipped it.

Fix: the checkbox now reads **"Obj/Img planes (Refs)"**. No mechanism change; the
repro script stands as the verification that none was needed. (Lesson: before
fixing a display bug, reproduce it — this one was a labelling gap, and a "fix" to
the visibility machinery would have been code churn on a proven-correct path.)

## Round 2 (Refs.png): the checkmarks were INVISIBLE

The user showed the Overlays menu: every item looked unchecked, yet the circle
persisted. Re-verified the machinery a third way — forcing BOTH refresh branches
(the fast display-toggle reuse AND the full refresh) with Refs off: the Object disc
hides in both. And the flagged state snapshot shows the Refs-gated actor was the
ONLY overlay actor left alive → Refs was still ON in the live app.

The real bug: on this Linux Tk theme the menu checkbutton indicator fill
(`selectcolor`) defaults to a grey indistinguishable from the menu background, so
CHECKED and UNCHECKED items render identically — the user had no way to see that
"Refs" was still on. `create_popup_menu` now sets `selectcolor="#1a7f37"`
(project-wide: all popup menus' check/radio indicators become legible).
