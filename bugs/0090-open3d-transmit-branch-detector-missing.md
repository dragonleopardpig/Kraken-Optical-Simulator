# 0090 — Open 3D: beam-splitter transmit arm had no detector (B1 only gave the reflect arm one), and derived planes were sub-mm slivers

## Symptom (user)

> [flag_20260617_232606_140] seems like the reflected beam gets a detector, the
> transmitted one is missing.

A doublet feeds a coated beam-splitter cube. After B1 (bugs/0088), the **reflected**
arm got a derived detector and its beam terminated — but the **transmitted** beam
ran straight through and off into the distance with no detector.

## Root cause

`branch_detectors.derive_branch_detectors`:
1. **Skipped the transmit leaf.** `_leaf_reaches_existing_detector` returns True
   for the straight-through leaf (it reaches the sequential `Image`), so that leaf
   was `continue`d — only the reflect leaf got a derived detector. The existing
   `Image` (the nominal transmit detector) was a **zero-size point** at the
   sequential z (state: `row 5 = [0,0,0,0,266,266]`), so Phase A's hard-stop
   couldn't clip the transmit beam there either (radial limit ≈ 0).
2. **Degenerate plane size.** Detector half-extents came from the focus-spot
   spread (≈0 at a focus) / a zero-size existing Image, so the derived reflect
   plane was a sub-mm sliver (state: `row 100000 = [-1,0, 69,69, 164,165]`).

## Fix (this commit)

In `derive_branch_detectors`:
- **Both arms when a split occurs.** When there is more than one terminal leaf
  (a real split), derive a detector for **every** leaf — including the
  straight-through transmit leaf that reaches the `Image` — each at its own
  converging focus. A plain sequential scene (single leaf reaching the `Image`)
  still derives nothing and keeps the existing `Image`. Intermediate branches
  (proper prefixes of another branch → they feed a downstream splitter) still get
  none, so cascading stays correct.
- **Visible plane size.** Size each detector to the **beam footprint** entering
  the branch (it catches the whole beam) rather than the focus spot, with a
  scene-scaled minimum (`max(0.04·scene_radius, 5 mm)`), so a tight focus no longer
  collapses the plane to a sliver. A real, sensibly-sized existing detector still
  wins.

Result: a beam splitter now shows a detector on **both** arms, each at its focus,
and both beams terminate there (Phase A hard-stop). Cascading splitters get a
sized detector on every terminal arm.

## Regression gate (display-free)

`validate_open3d_beam_splitter_branch_detectors.py` updated: single BS → **two**
detectors (transmit + reflect) at their foci with half-extents ≥ 5 mm; cascading →
a detector on each of the three terminal leaves (transmit + the two BS2 arms),
**none** on the intermediate `S4:BS/reflect` arm; absorbing / no-splitter → none.
Penta **Phase 82** (baseline unchanged at 84).

## Status: FIXED (pending in-app confirmation)

In-app: the beam splitter should now show a detector on the transmitted arm too
(at its focus), with the transmitted beam terminating there. Confirm visually
(headless VTK can't render).
