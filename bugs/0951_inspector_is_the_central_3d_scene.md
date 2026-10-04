# 0951 -- one 3D scene in the centre: the real inspector, with its Nav Cube

Reported 2026-10-04 (Qt shell): "the Nav Cube is missing in 3D scene", and the panels on the four
edges "are overlapping each other now".

## What was on screen

Reproduced at the user's screen size (2560 x 1440), captured at the X level:

- **At start-up** the centre of the window was the phase-2 *preview* of the scene
  (`qt/viewport.py`): bodies and rays, no Nav Cube, no gizmos, no readouts.
- **The real inspector** (which has the Nav Cube) was a dock in the TOP area, built only when
  "3D Inspector" was pressed.
- **Once it opened**, the top area took the height, and everything else shared the band left under
  it. Measured: the preview 1743 x 112 px, Scene Components 319 x 112, the System tabs 486 x 86.

So both reports had one cause: two 3D views, and the wrong one in the centre.

## Change

- **The inspector is the central 3D scene.** The central widget is a two-page stack: the
  inspector's page and the preview's. `build_scene()` (what `app.run()` calls) builds the
  inspector and shows its page. The preview is no longer built at start-up; it remains the
  fallback when the inspector cannot be built.
- **No `InspectorDock`.** The panels flank the scene: Scene Components left, the System / Source /
  Trace / Optimization / 3D Live tabs right, the table above, Debug / Progress / Results below.
  Starting sizes: left 300, right 400, bottom 150, table 170 px.
- **The ribbon's view commands drive that scene.**
  - Show Rays and the inspector's own "Show rays" box are one switch, either way.
  - Fit Scene frames the scene without turning the view (what a Nav Cube snap does).
  - Redraw refreshes the inspector.
- **The ribbon trades height with the scene, not the table.** With the inspector gone from the top
  area, the ribbon and the table were its only docks, and Qt keeps an area's total height. Folding
  the ribbon handed its height to the table; undocking and re-docking it cost the scene 40 px each
  time (measured). The ribbon now puts its neighbours' heights back after it changes its own.

## Sizes

| Window | 3D view before (inspector open) | 3D view now |
|---|---|---|
| 2560 x 1440 | 2560 x 769, panels crushed | 1790 x 804, panels at full size |
| 2560 x 1440, every panel folded (0952) | -- | 2502 x 1247 |
| 1500 x 950 (a 1000-px screen) | 415 px high | 425 px high |

## Found by the gate: the scene could be squeezed narrower than its own readouts

The first gate over the Qt phases failed one of 92: phase 706, "every viewport text stays inside the
window and off the Nav Cube after a resize". With panels on both sides, a 1080-px window left the
3D view 462 px wide. The scene's readouts do not shrink: the system box is about 500 px, the banner
wraps no narrower than 48 characters, and the Nav Cube takes its corner. Both texts ran off the
edge.

The scene is now the last thing to shrink: the 3D view has a minimum width of 700 px
(`SCENE_MIN_WIDTH`), so the panels beside it give way first. Claim **S** of the guard narrows the
window to its minimum with every panel open and checks the view is still 700 px wide.

## A consequence worth knowing

A layout now loads into an inspector that is already open, so the **fast-load rule (bugs/0646)
applies in Qt as it does in Tk**: the scene comes up with bodies only, and rays are traced when
asked for (Show Rays, or the inspector's box). Before, pressing "3D Inspector" after a load built a
fresh inspector, which traced at once.

## Guards

- **`validate_qt_scene_layout` (phase 724)**, claims C, N, L, V (the rest are 0952's):
  - **C:** the inspector's page is the central one on show; no preview is built beside it; no dock
    holds it.
  - **N:** the Nav Cube's viewport is the scene's top-right corner and pixel-square, and 29% of the
    pixels there change when the cube's renderers are switched off (0% elsewhere).
  - **L:** with every panel open, each sits beside the scene, none is under 100 px, no two
    intersect, and the 3D view is at least 400 px high.
  - **V:** Show Rays is one switch both ways; Fit Scene restores the fitted zoom after a 3x
    zoom-out; Redraw refreshes the inspector once.
  - **S:** at the window's narrowest, with six panels open, the 3D view is still 700 px wide.
- **Re-pointed:** the 0855 guard (the preview sits in its own page of the central stack), the 0906
  guard (the inspector is the central scene and no dock holds it), the ribbon guard's T (the table
  is above the 3D scene).

**Mutation-checked:** with the inspector's page not made current and the rays hook removed, C, L
and V fail.
