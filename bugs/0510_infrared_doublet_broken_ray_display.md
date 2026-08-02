# 0510 — infrared doublet preset looked like disconnected rays

Flag: `attachment/recorded_bug_repros/flag_20260802_135332_444`

The flagged `IDE B.3.2 — Ge / AMTIR-1 doublet F/1.5` Full 3D view showed a
dense ray cloud with clipped fragments around a tiny lens.  The trace was
sequential and mostly valid (5684/5776 paths reached Image), but two preset
defaults were not faithful/useful:

- Table B.4 in *Infrared Design Examples* evaluates all four 1 mm F/1.5
  doublets through a maximum 10-degree field.  The imported presets used 15
  degrees, outside the source's reported range.
- The object-at-infinity plane used an arbitrary 100 mm display gap and 25 mm
  diameter.  Those proxies dwarf these roughly 1.6 mm-long, 1 mm-diameter
  systems and make the launch rays visually dominate the prescription.

All four B.3.2 doublets now use the printed 10-degree maximum field and a
clearly UI-only 5 mm by 3 mm object-plane display proxy.  Clipped pupil-rim
fragments are hidden by default for these presets (the existing Show clipped
rays control can still reveal them).  The common-layout validator requires
those defaults and traces the real saved-layout multi-field bundle, with
124/124 rays reaching the Image for each doublet.

The exact Full 3D `world_cone` pipeline also selected `BatchTraceLoop` for all
four presets.  It produced 5756, 5724, 5684, and 5624 image-reaching paths out
of 5776 respectively; only the small pupil-rim populations stopped at a clear
aperture, and those diagnostic fragments are now hidden by the preset default.
