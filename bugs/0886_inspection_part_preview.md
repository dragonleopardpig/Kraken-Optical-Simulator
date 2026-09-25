# 0886 -- `FormPreview`, and the dialog it was blocking

0885 found that `services/inspection_part.py` could not be ported because of its **picture**.
bugs/0828 had replaced an explanatory paragraph with a drawing of the part at true proportions --
the two inspected faces lit, the unreachable ones greyed -- plus a derivation chain where every
line names its parent, because *"a dense sentence does not attach to the fields above it"*.

The picture was never view code. `face_polygons()`, `inspected_faces()`, `unreachable_faces()`
and `field_chain()` already return polygons, face sets and lines. What was missing was somewhere
to put them.

## The eighth family property

```python
@dataclass(frozen=True)
class FormPreview:
    width: int = 210
    height: int = 150
    shapes: Callable[[Any, dict], tuple]    # form, values -> polygons and text, in pixels
    caption: Callable[[Any, dict], str]     # form, values -> the block beside it
```

A shape is a dict -- `{"kind": "polygon", "points": [...], "fill": "#rrggbb", "outline": ...}`
or `{"kind": "text", "x": .., "y": .., "text": .., "fill": .., "size": ..}` -- in pixel
coordinates inside `(width, height)`, so **the model decides the layout and neither view has
to**. Tk draws them onto a `tk.Canvas`; Qt paints them onto a `QPixmap` with `QPainter`.

Both redraw on **every keystroke**, which is the whole point: the consequence of a number is
visible *before* Apply rather than after a minutes-long retrace. The guard pins exactly that --
typing 90 redraws the part and recaptions the chain with no Apply in between.

## What did not change

bugs/0768 still holds: the two **derived** keys, `axis_reach_mm` and `axis_offset_mm`, come from
the live spec and never from a widget, because re-submitting a stale offset is what fought the
auto-centring. And the field labels stay the machine's -- Length / Width / Thickness (bugs/0766)
-- over the stored keys `width_mm` / `depth_mm` / `height_mm`, which no scene has to migrate.

`services/inspection_part.py` 496 -> 316 lines; the dialog is one call.

## Guard

`KrakenOS/UI/validate_open3d_0886_inspection_part_preview.py` (penta phase 674):

- **B** -- six fields in the model's stored keys, and the two verbs
- **P** -- six faces with exactly two lit and a four-line chain, and typing 90 **redraws and
  recaptions** before any Apply
- **V** -- "Length L (mm) expects a number.", "Thickness T (mm) must be non-negative.",
  "Required FOV must be a positive number, or blank."; a blank FOV passes
- **A** -- apply writes through `set_inspection_part_spec` with the derived keys untouched
- **T** -- the REAL Tk canvas carries the same 7 shapes the model returned
- **Q** -- the Qt dialog painted a 210x150 picture and re-captioned as the number was typed
