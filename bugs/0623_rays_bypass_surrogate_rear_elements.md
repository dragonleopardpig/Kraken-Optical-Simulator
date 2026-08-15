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
