# 0357 — Illumination Source covering a BS side must block the reflected imaging arm

**Flag:** 20260719_203032_676 — "When there is an Illumination Source cover the entire BS Cube
side, the imaging ray shouldn't reflected out from it, and there shouldn't be any second optical
axis created. Can make the illumination source solid color instead of translucent one?"

**Status:** glyph part SHIPPED 2026-07-19 (source panel now opacity 1.0 solid, was 0.28
translucent); the trace-level block is DESIGNED below, not yet implemented.

## Shipped now

The 0283 scene-source glyph panel draws solid amber — the LED reads as the opaque plate it is.
(The 0356 hard stop already truncates the DRAWN reflected rays at the emitter plane.)

## Remaining defect

The imaging trace still REFLECTS at the BS diagonal into the LED-covered side: the branch spawns
its "Optical Axis 2" chief-ray segment and branch detector machinery (draw-suppressed since 0285,
but the axis + in-cube reflected stubs remain). Physically the covered side is an opaque emitter —
the imaging arm hitting it is absorbed (exactly the 0273 face-block physics, which today engages
only for MARKED faces, not for scene sources).

## Design (reuse 0273 wholesale)

Detect coverage at build time: for each enabled, physical, NON-marker scene source, find the
promoted-solid face whose plane matches the source panel (|n·d|≈1, in-plane distance small,
panel rect covers the face bbox) and add that face to the row's `illumination_block_face_ids` —
the exact hook 0273 built (`OpticalSolidFaceIlluminationBlock` → `force_absorption` → the 0108
absorbed-leaf chain drops the branch detector AND its axis). Remember the 0273 cache gotcha:
`_row_specs_signature` must key on the derived ids or the fix silently no-ops. Guard: covered
face absorbs, uncovered BS still splits (0090), the LED's own flood unaffected, second axis gone.
