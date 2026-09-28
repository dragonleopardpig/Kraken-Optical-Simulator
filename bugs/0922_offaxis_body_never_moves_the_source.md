# 0922 -- a body parked off the beam no longer moves the source, and a total miss is drawn

**User decision 2026-09-28: "Stay on axis, show misses."**

Found by the ungated sweep: `validate_open3d_face_assignment_sampling_stability`. After promoting
a 42779 prism placed 42 mm off the axis, the world-envelope launch jumped onto the prism.
Bisected to 596c8134 (05-25, "Center infinity field launches on stop"). With the promoted body
as the only element, it becomes the analysis/stop surface, and the launch centred on its
DECENTRED position.

## Fix 1: the launch reference (`_infinity_field_launch_reference_point`)

- Stop-centring is for a real APERTURE: it points each oblique field's chief ray through it.
- When the reference row is a file-backed optical SOLID (a promoted STEP/STL body), the
  reference is now the AXIS point at that row's z, not the body's decentre.
- An on-axis stop gives the same point either way, so the Double Gauss case
  (`validate_infinity_field_launch`) still passes.

## Fix 2: a total miss is shown (`_suppress_blocked_reference_ray_stubs`)

With the launch on the axis the rays miss the prism; with a solid present the Image follows its
output port, so the rays hit nothing. The bugs/0189 stub filter then hid ALL of them, since they
are `pupil_field_reference` rays `stopped_at_surface_0` with no power: the light vanished. The
0189 stubs are scaffolding BESIDE a beam that went through the fold, so the filter now drops
nothing when every path would be dropped. A miss is visibly a miss.

## Guard (re-pointed)

The old guard byte-compared the launch before and after. The pattern legitimately changes (the
solid makes the trace non-sequential, and the envelope fills the pupil disk instead of a fan).
The guard now measures the rule:
- same ray count, every ray drawn;
- the launch centre stays on the axis (0.057 mm off, for a 2 mm pupil);
- the launch stays inside the same pupil (2.005 vs 2.000 mm, 1% allowance for the disk sampler).
