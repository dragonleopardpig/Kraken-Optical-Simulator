# 0180 — FEATURE: MV-150 coaxial area-LED, FOLDED (visualize the real beam path)

## User request (follow-on to 0179, Q4/Q5)

After 0179 shipped the **unfolded** coaxial layout (a straight LED → stop → FOV line that
feeds the quantitative *Relative illumination* dark-edge measurement), the user asked to see
the **actual folded beam** the production rig uses:

> "Enable this Area LED in MV-150 test. I want to visualize this as a Source with rays
> emanating from it, reflect to Object Plane and reflect back. The current Absorbing surface
> that the reflected beam hit is where the flat LED should be — just place it outside this BS
> with a small gap."

So this is the **visual companion** to 0179: render the rays going
**LED → BS reflect → object → diffuse scatter back → BS transmit → imaging lens → camera**,
with the LED sitting just outside the **+X absorber face** of the beam-splitter cube (the face
the reflected beam strikes in the MV-150 test scene, `S001/F002`, normal `[+1,0,0]`).

## Layout

`common_optical_layouts/machine_vision_150mm_coaxial_led_folded.py` is modeled on the proven
branched template `zemax_led_beam_splitter_imaging.py` (non-seq beam-splitter + diffuse
double-pass), retargeted to MV-150:

- **Source** — `Random rectangle source`, 55×78 mm, at the **+X side port** (`origin
  [40,0,45]`, `direction [-1,0,0]`), emitting −X into the cube.
- **Beam Splitter** — 45° BK7 diagonal, **`tilt_y = -45`** so its normal is `[-0.707, 0,
  +0.707]`, folding the −X beam to **−Z** (down to the object). `tilt_y = +45` is the trap:
  normal `[+0.707,0,+0.707]` reflects −X → **+Z** (the wrong way; the object then gets a
  single stray point instead of a 55×78 footprint).
- **Diffuse Object** — `MIRROR` + `DiffuseScatter` (guided target sampling back at the BS) on
  the reflected arm = the 39×39 mm FOV.
- **Imaging lens + Image** — on the transmitted return branch.

`ray_display_mode = "Beam-splitter paths"`, `trace_mode = "Non-Sequential Preview"`.

## The axis-mapping subtlety (the easy mistake)

After the −X → −Z fold, the LED's local extents map to the object as:

| LED source axis (dir `[-1,0,0]`) | world | object axis |
|---|---|---|
| `radius_x` (local-X = `u` = `[0,-1,0]`) | −Y | **Y, perp (78 mm, uniform)** |
| `radius_y` (local-Y = `v` = `[0,0,1]`) | +Z → (fold) | **X, fold (55 mm, the dark edges)** |

So the rectangle uses **`radius_x = 39` (perp/Y)** and **`radius_y = 27.5` (fold/Z)** — the
*opposite* of the naïve "x is fold" guess, because the fold rotates the LED's Z extent onto
the object's X. A swap would put the wide 78 mm on the fold axis. Verified empirically: with a
near-collimated probe the object footprint is **56 mm (X, fold) × 79 mm (Y, perp)** ✓.

## Verification

- The full branched diffuse double-pass traces end to end headlessly (image plane lit).
- Near-collimated probe at the object: fold(X) ≈ 55, perp(Y) ≈ 78, fold < perp (no swap).
- As-shipped 30° LED cone still reaches the image (the cone spreads the object footprint to
  ~83×80, which is cone divergence, not a geometry error).

## Guard / phase

`KrakenOS/UI/validate_open3d_coaxial_led_folded.py` (display-free): structural contract
(−X side-port rectangle LED outside +X, BS `tilt_y=-45`, Diffuse Object on the reflected arm,
beam-splitter-paths display) + fold geometry (near-collimated object footprint 55×78, fold <
perp) + end-to-end (as-shipped cone reaches the image). Wired as **penta phase 176**; baseline
updated (added standalone — the full marathon segfaults under Xvfb llvmpipe).

## Follow-up

This layout **visualizes** the path; it does not yet make the BS clear aperture the limiting
stop, so the 2 dark edges are not quantitatively carved here (the apertures are opened to pass
the 78 mm beam cleanly). The **unfolded** `machine_vision_150mm_coaxial_led.py` remains the
quantitative relative-illumination reference (fold edge/centre ≈ 0.66). Tightening the folded
BS to ~30 mm fold clear aperture to reproduce the dip in the folded view is the next step.
