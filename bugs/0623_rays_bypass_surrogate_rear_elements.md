# 0623 — "Some rays missed lens surrogate" and flew on un-refracted (FIXED)

Flags `flag_20260815_221338/221413/221442` (object side / missed rays / image side),
build `efd98165` — surfaced by the bugs/0621 fix: with pencils finally launching from
the TRUE field edge, corner-field rays showed up bypassing the lens surrogate.

## Measured mechanism

Of the 38 `missed_image` rays on the solved Apo75 (55×55, c=0.906):

- **0 of 38** cross outside the front datum, lens 1, or the aperture stop — every
  escaper enters the block legally (the stop is already a wall: the bugs/0179
  `IsApertureStop` scan blocks outside its hole at any radius, 106 rays vignette).
- **21 of 38** then diverge OUTSIDE lens 2 and the rear datum (Ø13.11) before
  reaching their planes. The non-seq chooser skips a finite surface the ray misses
  (the known aperture-skip behaviour), so they fly on UN-REFRACTED — the flagged
  yellow bypass fan. A physical barrel would absorb them at its interior.
- **17 of 38** stay inside every aperture and honestly miss the 23×23 glass — real
  corner vignetting/aberration; correct, untouched.

## Fix — the surrogate datums are barrel walls, bounded

- Build: rows named `*Front*Datum*` / `*Rear*Datum*` (both surrogate recipes' naming)
  get `HardApertureWall = True` with `HardApertureWallOuter = 2 × diameter`.
- Engine: the bugs/0179 stop scan honours `HardApertureWall` alongside
  `IsApertureStop` — but as an ANNULUS: outside the clear aperture AND within the
  barrel outer diameter blocks; beyond the barrel is free space. The designated stop
  keeps its infinite wall. The annulus matters on non-seq scenes: illumination flood
  and splitter arms legitimately cross these planes far off-axis, and an infinite
  invisible wall would silently absorb them (the invisible-wall trap).

Verified: the 21 bypass rays terminate at the barrel; the 17 honest misses remain;
solve phases 447/448 and the diffuse/illumination phases 92/178/179/180 unchanged.

Guard: phase 468 (`validate_open3d_0623_surrogate_datum_walls`).

## Part 2 — 0624 (flag_20260815_233428 "image side still missing 2 sampled rays, only shows 7")

The 0623 walls over-reached: absorbing everything outside Ø13.11 killed TWO of the
nine field pencils entirely (arrivals 120 → 95, stop-vignettes 106 → 161). The
surrogate is a vendor BLACKBOX: its row diameters are paraxial bookkeeping, not glass
sizes — the vendor guarantees the Ø32.6 image circle, so corner pencils MUST pass.
Neither skipping (fake bypass, part 1) nor walling at the drawn radius (fake corner
vignetting, this flag) is the truth.

**Blackbox semantics (the fix):** rows between the Front and Rear vertex datums
(marked `_surrogate_block_member` in a build pre-scan) trace with their aperture
EXTENDED to 2× the drawn diameter — the mesh the non-seq chooser intersects grows;
the DISPLAY keeps the drawn row size; the STOP keeps sole aperture authority
(anything "stop"-named / Aperture-typed is excluded from the extension). The datum
walls remain only as a far backstop annulus (2×..4× the drawn diameter): inside 2×
refracts, 2×–4× absorbs at the barrel, beyond 4× is free space.

Verified: all 9 field spots restored, arrivals recover, the bypass class stays
extinct, and phases 92/178/179/180/447/448/467/468 pass.
