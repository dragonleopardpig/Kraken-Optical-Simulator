# 0532 — the plate BS's BACK face also split 50/50 (ghost ~10× too bright)

## Evidence

`diag_0531b_plate_ghost_geometry.py` on the AZ85 scene: the transmit-dump family carried
power 0.25 = TWO 50 % transmits and the ghost family 0.25 = 50 % × 50 % — both large
faces of the 1.2 mm plate acted as 50/50 splitters. The saved scene's
`OpticalSolidFaces` had BOTH F005 ("Down") and F006 ("Up") flagged `Beam Splitter` — a
stale flag from the pre-0445 arbitrary pick surviving a later re-flag (the 0445 flagger
assigns ONE face; the plane-share propagation cannot bridge the 1.1 mm offset). Once 0533
let split children re-cross the glass, the mis-flagged plate traced as a full lossy
ETALON (1953 multi-bounce paths at 0.5^n powers) — correct tracing of wrong data.

## Physics

A real plate BS is coated on ONE face; the other is AR/bare. Correct budget: imaging
reflect ~50 %, transmit dump ~48 %, back-face ghost ~1–4 % (AR: ~0). User principle
(flag_20260804_083128 discussion): whatever "Show Clipped Rays" draws must be TRUE.

## Fix (two layers)

1. **Read-time normalization** — `_demote_parallel_duplicate_splitter_planes` in the
   shared `normalize_optical_solid_face_metadata` (used by the kernel trace AND the UI):
   when flagged splitter planes are PARALLEL but NON-COPLANAR, keep the 0445-preferred
   object-facing plane (then larger area) and demote the rest to Transmit/Port. Coincident
   pairs (the cube's cemented diagonal) and crossed planes (X-cube) are untouched. Heals
   every saved scene at load; the file heals on next save.
2. **Flag-time exclusivity** — `assign_optical_solid_face_function` demotes a stale
   `Beam Splitter` flag on the parallel-distinct plane when the user assigns the coating,
   so the LATEST choice wins (the normalizer alone would keep overriding a deliberate
   far-face choice with the object-facing preference).

AZ85 after: one splitter plane (F005), imaging 225 @ ~0.489, dump 279 @ ~0.475, no ghost
family, census sane. Overlay-ON now shows only true light.

## Guard

`validate_open3d_0532_single_splitter_plane.py` (penta phase 427): normalizer patterns
(plate / cube / X-cube), real-scene single-plane + dump power, assign latest-wins.
