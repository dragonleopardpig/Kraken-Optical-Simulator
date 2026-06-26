# 0156 — FreeCAD-style interactive navigation cube for the Open 3D canvas

User request (refer `attachment/2D.png`): *"can we have this kind of navigation
ball? I need to rotate the canvas view, for example, the object plane is now located
at North-West direction facing South-East, I want to be able to rotate it so that the
direction is reversed (object at South-East facing North-West). So to make it general,
I think better to add a Navigation Ball just like FreeCAD."*

Chosen variant (user): **the axis-handle interactive cube** (over the labelled
RIGHT/REAR-faces variant).

## What shipped

A native VTK `vtkCameraOrientationWidget` is enabled in the Open 3D canvas. It is the
purpose-built orientation cube: clicking a face / edge / corner handle snaps the
camera to that orthographic or isometric view, and clicking the opposite handle
reverses the look direction — exactly the "reverse NW-facing-SE to SE-facing-NW"
the user described. It sits alongside the existing fixed Iso / ±YZ / ±XY preset
buttons and the passive lower-left axes marker; it is the first control that lets the
user rotate to an *arbitrary* standard orientation by clicking, not just the five
presets.

## Design

* **Native widget, no new dependency.** VTK 9.5.2 (already in use) ships
  `vtkCameraOrientationWidget` in `vtkmodules.vtkInteractionWidgets` — the same module
  as the existing passive `vtkOrientationMarkerWidget`. It is wired through the same
  lazy `_load_3d_backends` plumbing (`layout_editor.py` import + `open3d_inspector.py`
  re-export), so it loads only when 3D is opened and degrades to `None` (feature
  simply absent) if VTK is unavailable.

* **Created after `Initialize()`.** The widget is built in `Kraken3DInspector.__init__`
  *after* `self._vtk_widget.Initialize()`, so the interactor is live when `On()`
  registers the handle observers. This is the exact path verified under Xvfb (a
  pre-existing 3-layer window → enable → clean 4-layer render).

* **Upper-right anchor.** `GetRepresentation().AnchorToUpperRight()` parks the cube's
  own renderer in the upper-right corner (measured viewport ≈ (0.75, 0.82)–(0.98,
  0.99)). The passive axes marker keeps the lower-left (0–0.18), so the two corner
  aids share a render layer without ever overlapping. Enabling the widget
  auto-bumps the render window layer count 3 → 4; the gizmo overlay (layer 2) still
  composites on top, and the source still declares `SetNumberOfLayers(3)` (the bump
  is internal to the widget at runtime).

* **Animation OFF.** `SetAnimate(False)` makes the snap instantaneous and removes any
  dependence on the embedded-`vtkTkRenderWindowInteractor` animation timer — matching
  the instant preset buttons. (Animation can be turned on later if desired.)

* **Each snap reuses the orbit backstop.** Both `InteractionEvent` and
  `EndInteractionEvent` on the widget are bound to the existing
  `_on_camera_interaction`, so a cube snap behaves like a mouse orbit / preset jump:
  the clip range re-fits (bugs/0048) and the perpendicular thickness labels re-square
  for the new basis (bugs/0128, 0140); on the End event the view-relative dimensions
  re-place (bugs/0152). No new bookkeeping was written — the tested orbit path is
  reused verbatim.

## Guard

`KrakenOS/UI/validate_open3d_navigation_cube.py` (penta Phase 147) — display-free:

* **A** the lazy import resolves `vtkCameraOrientationWidget` to the real VTK class on
  both `layout_editor` and the `open3d_inspector` re-export (same class object);
* **B** `Kraken3DInspector.__init__` builds the widget with `SetParentRenderer` +
  `AnchorToUpperRight` + `SetAnimate(False)` + `On()`, stores it on
  `self._camera_orientation_widget`, and registers *both* Interaction/EndInteraction
  observers bound to `_on_camera_interaction`;
* **C** `_on_camera_interaction` re-fits the clip range *and* re-squares the thickness
  labels (removing either fails here);
* **D** the construction path (`SetParentRenderer` on a bare renderer +
  `AnchorToUpperRight` + `SetAnimate(False)`) runs without a display and leaves
  animation off.

Phase 147 additionally drives the **live** inspector (Xvfb): the real widget must be
present, enabled, anchored upper-right, animation off.

## Notes

* Verified end-to-end under Xvfb: the real inspector creates the enabled cube in the
  upper-right (viewport ≈ (0.746, 0.823)–(0.98, 0.986)), layers compose to 4, render
  is clean, and `_on_camera_interaction` fires from a simulated widget event without
  error.
* No regression in the only layer-sensitive guard
  (`validate_open3d_gizmo_overlay_on_top`, source-contract `SetNumberOfLayers(3)`
  untouched) nor the camera-preset guard.
* The full Xvfb penta marathon was deliberately **not** run (documented
  SIGSEGV/login-stall risk) — the change is purely additive UI chrome and was
  isolation-verified (Phase 147 passes standalone with the real inspector).
* **In-app eyeball owed:** the actual click-to-snap behaviour (rotate / reverse the
  view) renders through and is driven by the embedded VTK canvas, which the headless
  harness can't click. The widget's presence + placement + wiring are proven; the
  hover/click handle interaction needs an in-app confirm.
