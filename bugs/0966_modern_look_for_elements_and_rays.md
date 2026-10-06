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
- **S:** through the real actor factory, a glass-edge line asked at 2.0 px is drawn modern when tied
  to a row and left exactly as asked with no row -- which is how imported STEP hardware is drawn.
- **D:** 144 rays asked at 0.88 through the real ray merge come out as one actor at 0.44.
- **I:** by the picture: 11 307 vivid pixels classic, 953 modern (what is left is the Nav Cube's
  arrows, the optical axis and the axes triad); the modern backdrop is darker and bluer at the top.
- **T:** in the Tk app the switch is off, the scene is the classic one on white, and the Overlays
  menu offers the entry.

**Seen by eye** (1920 x 1080 virtual display, the window at the user's 1916 x 1034): the flagged
scene from the flag's own camera, the doublets table, `om05a_folded`, two fold mirrors in a
three-quarter view, a selected lens (the pink selection tint reads clearly on the pale glass).
Pictures: `0966_modern_pyrite.png`, `0966_modern_doublets.png`.

**Mutation-checked: 25 of 25 caught, each by the claims it targets** (every mutation restored from a
copy; the tree clean afterwards):

| Mutation | Caught by |
|---|---|
| default glass keeps the classic cyan; its opacity is not kept in range; an element hidden on purpose becomes visible | P1 |
| the triangle wires stay drawn; a mirror gets no material; any colour is taken for default glass | P1 |
| the classic palette gets a second source | P1 |
| the outline keeps its classic widths | P1, Q, S |
| glass gets no material; the material is never applied to an actor | P1 and Q; Q |
| ray saturation is not capped | P2, Q, I |
| a diagnostic ray fades like the rest; a grey stub is recoloured; lightness is not drawn to the middle | P2 |
| ray opacity does not fall with the count | P2, D |
| the ray count does not reach the law (the merge passes 1) | D |
| the ray merge ignores the look | Q, D, I |
| the modern backdrop stays flat; the classic look keeps the gradient | Q, I |
| the actor factory ignores the look | Q, S, I |
| the look reaches actors with no row (STEP hardware) | S |
| switching the look does not redraw the scene | Q, I |
| the Qt shell does not turn the look on | Q, S, D, I |
| the Tk app starts in the modern look | T |
| the Overlays menu loses the entry | Q, T |

## Gates

By the cadence of 2026-10-05: its own guard, plus the guards that read this code, one at a time at
low priority on X299-SSD.

- **Phase 735** recorded in the baseline (1 pass, 0 fail) -- it passes inside the harness as well as
  alone.
- **Neighbours, all pass:** the interaction contract (phase 655, 259 checks -- its source pins on the
  scene refresh still hold), soft STEP bodies (728: the STEP switch still gives the two glass passes
  with the modern look on), the scene layout (724), the 3D toolbar catalogue (707), the shell flag
  (729), the 5e tools and readouts (706), the phase-2 preview's elements and rays (0857, 0858), the
  DXF export's menu wiring (0650) and the fold-mirror guard that reads the Overlays menu.
- **Skipped, not passed:** `validate_open3d_step_edges_glass_palette` -- its repro scene
  (`machine_vision_150mm_measured_test.py`) is not on this machine.

**Owed, on the user's go:** the Qt-hosted harness (`--shell qt`, 352 phases, about 15 minutes) is the
run that would notice a phase minding the look, because the look is on by default there. A source scan
found little to mind (7 colour or opacity reads in the harness, no pixel reads), but that is a scan,
not a run. The full Tk gate is owed since 8403abde; the look is off in the Tk app, so it covers the
classic path.

