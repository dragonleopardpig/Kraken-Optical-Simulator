# 0538/0539 — the seated source froze the app; the auto floor seated on the cable

## 0538 (live "it freezes now")

py-spy on the live PID: the app was ADVANCING inside a synchronous non-seq trace
(selection-triggered refresh after the seat) -- 2000 illumination rays through the
splitter = ~4000 branch paths, ~2 minutes on the UI thread. Two layers:

- **Shipped**: `__OpticalSolidScenePoints` memoized per surface (keyed to the live EEE
  list). The media/internal-face checks called it per ray-hit -- 55 027 gathers per
  trace, each converting pyvista points to numpy (py-spy hot frame).
- **Open perf debt**: the selection refresh still runs the big trace synchronously
  (`force_retrace` path skips the async worker). Deferring seated-source traces to the
  async path is the real UX fix; queued.

## 0539 (flag_20260804_121808 "not snapping properly")

The seat itself WORKED (plate flat, aiming up through the housing) but landed at the
LED body's bounding-box far plane -- which is the CABLE ARCH's depth, ~40 mm below the
real floor ("floating below the box"). The floor finder is now AREA-WEIGHTED: histogram
the mesh cells' axial stations weighted by triangle area and take the strongest 1 mm bin
on the far half -- a floor plate carries big area, cables are thin. On the OPT-ILS0202
housing the seat moved from z=142.7 (cable) to z=100.2 (the floor plate). Bounding-box
fallback kept for degenerate meshes; guard updated (phase 431 asserts off-bbox floor).

## "Illumination Emission" toggle (user report, same session)

Not a bug in the toggle: "Illumination" / "Illum rays" are the MV-150 COAXIAL overlays
(on-detector relative-illumination heatmap + fate-coloured coaxial rays); with a free
seated source there is no coupled-coaxial dataset, so they draw nothing. Toggling the
SOURCE itself on/off = the browser row's hide/unhide or Edit Source... -> enabled.
Renaming/greying those entries when no coaxial dataset exists is queued as UX polish.

## 0540 (flag_20260804_124129, three asks)

1. **"super long tracing of 2000 rays ... any toggle?"** -- the interactive preview now
   launches a CAPPED subset per source (`preview_ray_cap`, default 200; override per
   source spec) and a new LED defaults to ray_count 500 instead of 2000: the seated-
   source preview trace dropped 127 s -> ~26 s (the remainder is the real TIR-chain
   physics; async deferral stays queued). The on/off toggle exists today: the browser
   row's hide/unhide, or Edit Source... -> enabled.
2. **"still not seat correctly ... select a surface and snap to it"** -- the auto seat
   emitted TOWARD THE OBJECT CENTRE (tilted whenever the object is off-axis). It now
   emits along the FLOOR PLATE'S OWN NORMAL: plate-like cells only (|n.axis| >= 0.7 --
   the two skins' opposite normals cancel in a raw mean, leaving wall residue),
   sign-aligned toward the object, area-averaged. And the pick-a-surface flow the user
   asked for already exists: right-click any reachable face (the outer floor from below
   works) -> "Seat {source} on This Face".
3. **"all reflected at the BS, nothing transmitted"** -- transmission IS there: the
   census shows both split_transmit families continuing to the object and the reflected
   arm (which folds -x, mirroring the imaging fold -- the leftward fan in the flag).
   The chains `refraction@3 | split | reflect_tir@3 | split ...` are REAL total internal
   reflection inside the thin plate reaching its edge strips -- light-guide physics the
   0533 fix made traceable. The old view's impression came from the tilted aim plus
   display decimation of ~4600 paths.
