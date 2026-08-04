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

## 0541 (flags 130936 "auto seat still slanted" + 131019 "seat a surface: not functioning")

Both seats produced visibly tilted panels: mesh-derived normals carry bracket/cluster
noise (~7-10 deg), and the face-cluster normals of the coarse pick inherit draft angles.
A coaxial illuminator fires along the OPTICAL AXIS -- both seat routes now snap the
resolved aim to the object-leg axis when within 20 deg of it (exact: the AZ85 leg is
(0.0022, 0, -1)); a deliberate far-off-axis wall seat keeps its honest face normal.

## The TIR question ("why would the BS coating introduce TIR -- shouldn't it be Air?")

Precisely right to challenge: the COATING never TIRs -- the deterministic splitter
splits at any angle. The `reflect_tir@3` events happen at the plate's UNCOATED
glass-to-air faces, overwhelmingly the four narrow EDGE strips: internal rays reaching
them beyond the 41.1 deg critical angle (rim entries + split-reflect bounces along the
thin plate) totally reflect -- correct physics for POLISHED edges, newly traceable since
0533. Real catalog plates have GROUND (matte) edges that absorb/scatter instead;
flagging F001-F004 as Absorber/Mechanical models that and kills the chains -- offered to
the user before touching their scene's physics.

## 0542 (flags 133005/133134/133253/133342/133543 + "replace my eyeball" snapshots)

- **Master toggle**: "Illum rays" now gates illumination-role sources in the preview
  TRACE itself. OFF (default) = the fast imaging preview (6 s; a seated LED costs
  nothing); ON = the illumination fan (~19 s). Toggling invalidates + retraces.
- **Coaxial fate overlay gated**: it drew an MV-150 fan (with a self-contradicting
  "green 0" label) on a free seated source; now it requires a source that couples to
  the imaging launch.
- **Radial bound on the miss projection**: the seated LED's strays crossed the folded
  sensor plane within the 0530 travel bound but 2-8 sensor-halves off-centre -- the
  REAL origin of the "transmitted ray not according to physics" phantom fan. Rejected
  beyond 3x sensor-half (arm-known scenes; the 0018 harness keeps cos-guard-only).
  Verified by before/after snapshots from the flag's own viewpoint: with the fan gone
  the ON view shows the reflected arm left, the transmitted cone up, edge-TIR strays
  outward -- all straight, honest tails.
- **"not seating at floor" (133005)**: the area-weighted bin lands on the strongest
  interior plate (z~100) -- likely the diffuser shelf, physically the right emitter
  plane; for the exact bottom pick the floor's outer face from below and use
  "Seat ... on This Face" (axis-snapped since 0541).
- **"right click works only after toggling clipped" (133253)**: OPEN -- suspected
  right-click dead zone while the async/selection trace swaps actors; needs a live
  repro with the now-fast default preview.

## 0543 (flags 142341 / 142524 / 142623)

- **"still not snap to the floor for auto, not centered"** -- the auto floor now takes
  the BOTTOM-most bin carrying >= 15 % of the peak area (cables stay too thin to
  qualify; the mid shelf no longer wins) and centres the emitter on the housing's
  lateral centre: origin (-17.4, 0.0, 144.5) = the outer bottom plane, centred,
  emission axis-snapped straight up. Guard updated (phase 431).
- **"All rays now turn green"** -- NOT reproduced headless (source + toggle OFF keeps
  the field palette: 124 green / 62 cyan / 62 orange over 9 field bundles). Needs a
  recording on the next build if it persists.
- **"snap to face only works after toggle clipped overlay" (142524) + "illumination
  overlay rays seem clipped themselves" (142623)** -- OPEN. New clue: a RENDER-ONLY
  visibility refresh re-arms the right-click, so the dead state lives in the
  renderer/pick maps between the seat's rebuild and the next actor rebuild.
