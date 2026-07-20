# 0366 — "Hide" on Scene Sources created another illumination: the creator sat in the Hide slot

**Flag:** 20260720_082633_349 (build e00e2c1b). **Status:** FIXED 2026-07-20 (phase-311 guard).

The per-source hide machinery was sound (glyphs AND the 0355 volume actors honour it). The real
defect was a MENU TRAP: right-clicking the "Scene Sources" group header showed a menu whose FIRST
ACTIVE ENTRY was "Add Illumination Source (LED)" — exactly the slot where "Hide" sits in every
other group menu (0361). Mid group-hide-spree the user clicked it: a new module-seeded source was
created and retraced instantly ("another illumination created") and nothing hid. The screenshot's
two arrowed amber panels = two source glyphs = two specs, confirming creation, not a reveal.

Fix: the Scene Sources group menu now leads with Hide/Show (cascading over the `source:*`
children) and Add moves below a separator; the empty group keeps Add-only. **Invariant (guard the
class, not the instance): the first active entry of ANY group right-click menu is Hide/Show, never
a creator** — asserted by ordering probe in the phase-311 guard. The stray extra source can be
right-click → Edit/Hide or deleted from the layout's scene_sources.
