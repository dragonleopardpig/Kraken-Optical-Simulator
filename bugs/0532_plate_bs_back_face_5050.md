# 0532 (OPEN) — the plate BS's BACK face splits 50/50 (ghost ~10× too bright)

## Evidence

`diag_0531b_plate_ghost_geometry.py` on the AZ85 scene: the transmit-dump family
(`S3/transmit -> S3/transmit`) carries power 0.25 = TWO 50 % transmits, and the ghost
family (`S3/transmit -> S3/reflect`) carries 0.25 = 50 % × 50 %. Both large faces of the
1.2 mm plate act as 50/50 splitters.

## Physics

A real plate BS has the beamsplitting coating on ONE face; the other is AR-coated or bare
glass. Correct budget: imaging reflect ~50 %, transmit dump ~48 %, back-face ghost ~1–4 %
(often invisible). User principle (flag_20260804_083128 discussion): strays shown with
Clip Overlay ON must be PHYSICALLY TRUE — so the ghost must carry its real power.

## Direction

The 0319 parametric plate promote auto-flags the splitter; find whether the flag is
per-FACE or effectively per-solid in the NS loop, and make the plate's non-coated face a
plain glass interface (pure transmit or Fresnel). Related: [0533](0533_split_child_skips_own_solid.md)
— the ghost also never exits the glass.
