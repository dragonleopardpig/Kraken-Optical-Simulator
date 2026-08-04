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
