# 0974 -- the un-promoted optical STEP body in the modern look: a colour the promoted prisms stand out against

Asked 2026-10-06. After bugs/0966 the un-promoted part of an "optical" STEP import -- the fixture the
prisms are promoted out of -- was the one saturated teal body left in the modern scene. Asked whether
it should take the pale glass colour, the user: "You can make it modern look for the unpromoted STEP,
but the color should be well contrast to all the promoted prism within it."

## Measured before choosing

On `om05a_folded` (twelve promoted prisms, most of them inside the fixture), in the user's own view:
how much DRAWING the promoted prisms changes the pixels where they lie within the body, as a CIE76
colour difference (2 is the least the eye notices). Fourteen candidate colours, same opacity and
material:

| Body colour | The prisms within show by |
|---|---|
| the pale glass colour itself | 2.6 -- they vanish |
| the classic teal | 7.1 |
| a neutral warm grey | 7.8 |
| sand, rose grey | 8.5, 8.2 |
| the hardware's slate | 10.9 |
| graphite | 11.6 |
| bronze .. umber | 10.2 .. 12.2 |
| terracotta, copper | 13.2, 14.1 |

Warm and mid-dark is what pale blue stands out against. Copper scored highest but swallows an orange
ray bundle (seen in the render), as the amber LED once did (bugs/0052); slate and graphite would
make the fixture look like the camera and lens hardware.

Two things that did NOT help, also measured: a fainter body (at 0.2 and 0.1 opacity the prisms show
LESS, 3.4 and 3.0 -- the body's colour is what they are seen against), and drawing the body before
the prisms (no change at all).

## Change

- **The body is a smoked bronze, (0.52, 0.42, 0.33), with a satin material**, in the modern look.
  Its colour is 55 from the modern glass and 51 from the modern mirror (the teal was 30 from the
  glass), and 35 from the hardware's slate, so it is not mistaken for a camera or a lens barrel.
- Opacity is kept inside 0.30 .. 0.46 (what the scene refresh already asks for); a body hidden on
  purpose stays hidden. Lens, camera and LED hardware are untouched.
- The look module decides (`open3d_scene_look.step_body_look`), asked at the one actor factory, so
  the full scene refresh and the single-body refresh cannot disagree. Display only: the import draws
  the same two actors with the same points in both looks.
- The classic look, and so the Tk app by default, keeps the teal.

In the picture the guard takes, drawing the promoted prisms now changes the pixels within the body
by **11.8**, against 5.6 with the body painted the classic teal and 0.8 with it painted the pale
glass colour.

Pictures: `0974_before_teal.png` / `0974_after_smoked_bronze.png` (the user's view, rays on) and
`0974_before_teal_close.png` / `0974_after_smoked_bronze_close.png` (the fixture, rays off).

## Found on the way: a deselected lens came back paler (a defect of 0966)

The selection saved an actor's colour with VTK's `GetColor()` and painted it back with `SetColor()`.
Once a material gives the highlight its own colour -- the modern look's glass and mirrors have a
white one -- `GetColor()` returns the ambient/diffuse/specular BLEND, and `SetColor()` paints all
three with it. Measured in the Qt shell: a lens drawn (0.66, 0.83, 0.98) with a white highlight,
selected and then deselected, was (0.84, 0.92, 0.99) with no highlight, until the next redraw.

The new body has such a material too, so it would have done the same. The selection now saves and
restores the three colours one by one, for table elements and for STEP bodies alike.

## Guard: `validate_open3d_unpromoted_step_look` (phase 742)

- **P1, P2:** the look as numbers -- the colour, the material, the opacity range, what is left alone;
  the distances to the glass, the mirror and the slate.
- **Q:** in the Qt shell the body has the modern colour by default; the real Overlays entry switches
  to the teal and back; the lens and camera bodies are the same in both looks.
- **B:** the single-body refresh draws the body exactly as the full refresh did.
- **E:** the import draws the same actors and points in both looks.
- **S, R:** a selected body, and a selected promoted prism, get their own three colours back.
- **I:** by the picture, the 11.8 / 5.6 / 0.8 above.
- **T:** the Tk app keeps the teal until the look is switched on, then takes the bronze too.

`om05a_folded` needs the vendor STEP files, which are not in git: without them Q to T skip.

## Checks

**Mutations: 14 of 14 caught, each by the claims meant to catch it** -- the body in the pale glass
colour, left teal, or a neutral warm grey; no material; opacity not kept in range; a hidden body
shown; hardware or any other colour restyled too; the actor factory not asking the look module; the
classic look restyling the body; either selection saving the blended colour again; a deselected
actor not getting its highlight colour back; the single-body refresh asking for another colour.

**Neighbouring guards, all pass:** the modern look (735), soft STEP bodies (728), the STEP
selection pink snapshot (56), the analytic lens selection, the STEP edge palette, the interaction
contract (655).

**Baseline:** phase 742 recorded (pass; 741 phases). The full Tk gate ran at ff4c2088, before this
change; it has not been run again since.

