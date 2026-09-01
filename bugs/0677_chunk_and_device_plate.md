# 0677 — flag_20260901_091046: import the red-boxed prism assembly + the 50x50x1 device

Both landed on `attachment/om05a_folded.py` (`bugs/0677_chunk_and_device.py`):

1. **The prism-assembly chunk** (A.png red box = the 9 components above the first
   RA mirror: housing, top plate, 2 lower blocks, 2 plate LEDs, centre prism, 2
   outer prisms — extracted from the assembly STEP as ONE compound,
   `om05a_components/prism_assembly_chunk.step`). Imported via the UNPROMOTED
   `optical_step_path` overlay (display-only, no trace cost). Placement contract:
   the overlay seats the mesh's native z-min at scene z=0 — the chunk is
   pre-oriented R_x(-90) (native z = the chain direction, native y = the device
   length) with the slot plane at native z=0, and a placement offset z=-5.3
   returns the slot to the object plane after the min-normalization.
2. **The device is a 50 x 50 x 1 plate** (not a deep cube): the inspection part
   re-specced W50 x H50 x D1, active face on the object plane — the thin DUT
   lying in the slot between the outer prisms, as in Prism_Assembly.png.

Note (tunnel fiction, stated openly): in THIS scene leg 1 is the unfolded tunnel,
so rays pass through the chunk's housing visually; the chunk's slot spans +-30 mm
while the traced patches sit at +-5.5 (the centre-prism beam separation). The
fully-REAL geometry lives in `om05a_folded_armA.py` (0676) where all five folds
are traced and the chunk would align exactly — its polish continues there.
