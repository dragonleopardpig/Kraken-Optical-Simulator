# 0683 — part centred in the prism gap + authored partial-FOV bands (flag_20260901_133605_262)

## User
"The 3D object is not centered in the gap. Please also note that the Center Prism
effectively divide the FOV into half. As a result, one side of the 50x1mm should
attach the usual green transparent partial FOV. Is my reasoning correct?"

## 1. Part centred
New inspection-part spec field `axis_offset_mm` (offset of the ACTIVE face along the
axis, may be negative; `face_frames` + `part_frame` shift their anchor by it, so the
box, outlines, blow-out axes and part STEP all follow; editable in the part dialog).
The om05a scene sets -3.9: gap z -57.9..+0.1 -> part z -53.9..-3.9, centred with
4.0 mm margins. NOTE: face A now sits 3.9 mm behind the arm-A conjugate (z=0) --
the 57.8 mm conjugate spacing vs the 50 mm part is the modelling discrepancy the
0684 component remodel (real first-surface mirrors + cube BS) is expected to close.

## 2. The split-FOV reasoning -- CONFIRMED, with sharper numbers
Measured (bugs/0683_band_scan.py, a 1 mm y-scan through the real chain launch):
arm A delivers object y -5..+1 (>=20% reach; sharp cut at both ends).
- The one-sidedness is real: fold-parity through the three folds maps the centre
  prism's column window (z -30.6..-18.4) to object y (-11, +1.2) -- the band hangs
  off ONE side of the face, exactly as the user reasoned.
- The band is NARROWER than a half-FOV: the outer wedge's 10.5 mm entry window
  (y +-5.25) clips before the centre-prism split -> net y (-5, +1).
- Arm B: identical band by the z=-28.9 mirror symmetry (fold parity gives the same
  world-y window).

## 3. Partial-FOV display (general mechanism)
New layout setting `object_fov_bands`: a scene AUTHORS its measured delivered-field
bands (name, world center, plane axis, half_width, v_lo..v_hi). When present, the
detector-coverage overlay draws each band as the green FOV edge + faint pickable
fill AT ITS FACE and suppresses the misleading full-FOV rectangle/fill at the
object plane. om05a authors two bands (z=0 and z=-57.8, y -5..+1, half-width 26.8).
Persistence mirrors `display_fold_spec` (save + load in layout_settings.py).

## Guards
0672 validator: A7 re-pinned to the CENTRED part box; A8 pins the two authored
bands. 14/14 PASS. Inspection-cell phases 495-500 unaffected (offset defaults 0).
