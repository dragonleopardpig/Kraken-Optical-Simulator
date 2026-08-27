# 0660 — The un-killable green circles were the Quick-Estimation FOV discs

**Flags (2026-08-27):** the five-flag repro sequence 15:47–48 — "fresh load" →
"changed FOV" → "toggle Refs off. Still shwoing." → "toggle Det off" → "toggle ray
off" — plus "swapped to telecentric lens, 2 big circles" (15:52), and the earlier
153106 "all overlays off, why still have a big green circle?".

## Correction of the 0659 diagnosis

0659 round 1 concluded "Refs was still on" — WRONG. Three different toggles draw the
SAME green (0.2, 0.9, 0.35) at the same object plane: the Refs reference disc
(opacity 0.1), the Det coverage pick-fill (0.08) + FOV box (1.0), and the QE pick
disc (0.10) + FOV outline (1.0). My repros tested the Refs disc; the user's circle
was the QE family — same size (both scale to the field semi-diagonal), same colour.
The flag sequence's actor snapshots (sizes/opacities per step) told them apart.
**Identify overlapping actors by OPACITY before blaming a toggle.** (The 0659
fixes — the label rename and the visible menu checkmarks — remain real.)

## Three defects

1. **No discoverable switch:** opening the FOV dialog silently ENABLES QE mode
   (five code paths set `quick_estimation_var`); the only off switch was the Left
   Panel's "Quick Estimation" checkbox. → "FOV planes (QE)" added to the Overlays
   menu (same var, one obvious place).
2. **Toggle did nothing visible:** `_toggle_quick_estimation` never refreshed the
   scene — QE off left the discs until an unrelated rebuild. → refreshes now.
3. **Actor generations accumulated:** the overlay service did not own its actors;
   sets added by solve/readout paths outside the tracked scene rebuild lingered
   (the swap's "2 big circles" = current + stale generation). → the service tracks
   every actor and `clear()`s the previous set at the TOP of every `add_overlays`,
   disabled path included.

## Verified

The user's exact sequence on their scene: QE on + solve → Refs off (QE independent,
by design) → Det off (coverage pair dies) → "FOV planes (QE)" off → **object plane
empty**. Accumulation check: repeated refreshes hold the count constant. Guard
`validate_open3d_0660_qe_overlay_lifecycle` (penta phase 494).
