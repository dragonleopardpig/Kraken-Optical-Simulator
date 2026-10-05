# 0966 -- a modern look for the table's elements and the rays

The user, in the Qt shell (2026-10-06): "the rays, the glass, the optical elements can have a nicer
look? Apart from the STEP element, the rest look like old TK. Perhaps reference to Optiland, very nice
display."

## What it looked like

bugs/0958 gave imported STEP hardware a soft look. Everything else in the scene was still drawn the
way the Tk app has drawn it since bugs/0020 -- rendered on the user's last flagged scene
(`machine_vision_Pyrite90_0.3X`) and on a table of doublets:

- **Rays:** every ray an opaque 1 px line in a fully saturated colour (0.88 opaque; pure green is
  saturation 1.0). The flagged scene draws hundreds per field, so each field is a solid painted fan
  and the fans turn to mud where they cross.
- **Glass:** bright cyan `(12, 238, 246)/256` under TWO outline passes, 2.8 px dark teal and 2.0 px
  teal. An element that is not an analytic lens (a splitter plate) is drawn 0.86 opaque with its
  triangle wires laid over it, which reads as a striped slab.
- **Mirrors:** a grey disc under the same triangle wires.
- **Behind it all:** a white sheet.

Pictures: `0966_classic_pyrite.png`, `0966_classic_doublets.png`.

## Change: Overlays > Modern look

A display switch in both shells, **on by default in the Qt shell, off in the Tk app** -- the same
arrangement as "Soft STEP bodies". The recipe is Optiland's 3D viewer (`optiland/visualization`,
MIT, (c) 2024 Kramer Harrison; credited in the module): a gradient backdrop, pale glass with a
strong narrow highlight, bright mirrors, thin mid-tone rays.

| | Classic | Modern |
|---|---|---|
| Backdrop | white | a vertical gradient, `(0.96, 0.97, 0.99)` at the bottom to `(0.73, 0.80, 0.89)` at the top |
| Glass body | cyan, 0.26-0.40 opaque (0.86 for a plate) | pale blue `(0.66, 0.83, 0.98)`, always 0.26-0.40, lit mostly by ambient light with a white highlight |
| Glass outline | two passes, 2.8 px + 2.0 px, teal | the same lines in ONE colour, slate `(0.34, 0.44, 0.56)`, 1.2 px |
| Triangle wires over a plate or mirror | drawn | not drawn (opacity 0) |
| Mirror | flat grey | silver, mirror material (specular 1.0, power 100) |
| Ring round a mirror or stop | near black | dark slate, at most 1.2 px |
| Ray colour | as the model gives it | the same HUE, saturation capped at 0.62, lightness drawn toward the middle |
| Ray opacity | 0.88 whatever the count | 0.88 up to 36 rays, then falling as 1/sqrt(n), not below a fifth |

- **The one thing that is not Optiland's:** it draws a handful of rays, this program draws hundreds
  per field. So a ray's opacity falls with the number drawn, and a bundle reads as a beam of light --
  denser where the rays are denser -- instead of a painted fan.
- **A diagnostic ray is a message, not light.** A ray that misses the detector (1.5 px) or is
  clipped (a grey 0.9 px stub) keeps its width and at least 0.7 of its opacity however many rays
  there are; the grey stays grey.
- **A surface with its own display colour keeps it.** The look replaces the DEFAULT glass, mirror
  and outline colours and nothing else, so a user's colour, a handle, a highlight and the selection
  tint are untouched.
- **An element hidden on purpose stays hidden** (a cement layer, a redundant drum, a suppressed
  aperture disc: opacity 0 in, opacity 0 out).

## Display only

`services/open3d_scene_look.py` holds both palettes and is asked in exactly two places, the two
functions every actor goes through: `_add_mesh_actor` (for an actor tied to a table row) and the
ray merge (`_flush_merged_ray_actors`, where the ray count is known). A look changes colour,
opacity, line width and shading. **It adds and removes no actor and moves no point**, so picking,
the row bookkeeping and "Alt picks the nearest DRAWN edge" (bugs/0323) are the same in both looks --
the guard counts them.

Switching redraws the cached scene; nothing is traced. The backdrop follows the look on every scene
refresh, however the switch was changed.

The classic palette now has one source: the scene refresh's `_OPTICAL_STEP_*` names and the
inspector's default surface colours are the look module's constants.

## Not changed

- **Imported STEP hardware** keeps its own switch (bugs/0958). Seen on `om05a_folded`: an
  un-promoted "optical" STEP import keeps its teal body, which now stands out beside the pale
  promoted prisms. Whether that body should take the glass colour too is a separate choice.
- The optical axis, the FOV box, the readouts, the labels and the solve banner.
- The 2D plot's ray colours (the 3D rays keep the same hues, so the two still correspond).

## Guard: `validate_open3d_modern_look` (phase 735)

- **P1, P2:** the look as numbers, no display -- each row of the table above, the ray law at
  1 / 36 / 144 / 900 / 100 000 rays, the diagnostic floor, a user's colour left alone, the one
  source of the classic palette.
- **Q:** in the Qt shell the switch and its menu entry are on by default: gradient backdrop, no
  element actor with a classic outline tone, 36 outline actors in the one quiet colour at 1.2 px,
  no ray above the saturation cap. The real Overlays entry switches to the classic look (white, 9
  silhouette passes at 2.8 px and 9 edge passes at 2.0 px, rays at saturation 1.0) and back.
- **E:** both looks draw the same 55 element actors with the same points per row, the same 18 rays,
  the same 297 ray cells.
- **I:** by the picture: 11 307 vivid pixels classic, 953 modern (what is left is the Nav Cube's
  arrows, the optical axis and the axes triad); the modern backdrop is darker and bluer at the top.
- **T:** in the Tk app the switch is off, the scene is the classic one on white, and the Overlays
  menu offers the entry.

**Seen by eye** (1920 x 1080 virtual display, the window at the user's 1916 x 1034): the flagged
scene from the flag's own camera, the doublets table, `om05a_folded`, two fold mirrors in a
three-quarter view, a selected lens (the pink selection tint reads clearly on the pale glass).
Pictures: `0966_modern_pyrite.png`, `0966_modern_doublets.png`.
