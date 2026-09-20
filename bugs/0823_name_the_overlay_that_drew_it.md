# 0823 -- the app names the overlay family, the user does not guess

Not a flag. This is optiland's renderer-registry idea aimed at a bug class KrakenOS
has already paid for twice.

## The bug

Three Open 3D overlay families draw at the object plane, scaled to the same field
semi-diagonal, and **two of them use the byte-identical green** `(0.2, 0.9, 0.35)`:

* Quick Estimation FOV -- pick disc at opacity 0.10, circle outline at 1.0
* Detector coverage FOV -- pick fill at opacity 0.08, FOV rectangle at 1.0
* Reference surfaces -- a plane disc whose opacity is **scene-derived**

When a user says *"toggle Refs off. Still showing."*, the only way to answer has
been to read a note listing opacities and reason backwards. bugs/0659 round 1 did
exactly that and **blamed the reference-surface family for a disc it does not
draw**. The two green families are 0.02 apart in opacity; the third has no literal
at all.

That third case is the trap, and it is worth stating plainly: the reference-surface
disc takes its opacity from the scene bundle's mesh opacity, which the refresh
clamps per row. There is no constant to match, so **any procedure that excludes it
by opacity reproduces the 0659 mistake automatically**.

## Fix

Optiland's `NSQViewer3D` keeps a `_renderer_registry` mapping component type ->
renderer, so a drawn thing always has a declared owner. Overlays here are not
per-component-type, so the registry maps **visual signature -> family** and answers
the question actually asked: *what drew this, and how do I turn it off?*

`KrakenOS/UI/services/overlay_registry.py` declares each family's colour, opacity
literals, shapes, toggle var, UI paths, owning module, and actor lifecycle, with:

* `identify_overlay(color, opacity, shape)` -- candidates for a signature. A family
  with no literal is **never excluded** by that literal, by design.
* `families_sharing_color(color)` / `overlay_clash_report()` -- names every colour
  more than one family draws, and what separates them.
* `describe_family(name)` -- the user-facing answer, including how to switch it off.
* `verify_registry_against_source()` -- re-reads the declared literals from their
  real modules.

That last one is the point. A registry of hand-copied constants is just the next
stale note; this one fails a guard when a colour or opacity drifts.

## What shape can and cannot do

Shape does not narrow a green disc to one family -- the reference-surface family
draws a plane disc too. What it does is **rule out Detector coverage**, which draws
a rectangle. Stating that precisely matters: the first version of the guard asserted
"a green disc is Quick Estimation alone" and was wrong in the same direction 0659
was wrong.

## Deliberately not done

The overlays are not re-plumbed through the registry. Making it the mandatory draw
path would touch seven services and the scene refresh, and the bugs/0660 lifecycle
law is already enforced where it was proved. This ships the identification the user
needs; adopting it as the draw path is a separate change with its own risk.

## Guard

`KrakenOS/UI/validate_open3d_0823_overlay_registry.py`, penta phase 602. Display-free
and pure: the clash report, opacity discrimination with a tolerance that cannot span
the 0.02 gap, the colourless family surviving every opacity query, shape ruling out
the rectangle-drawer, every family reachable in the UI, the drift check, the 0660
lifecycle fact, and lookup degradation.
