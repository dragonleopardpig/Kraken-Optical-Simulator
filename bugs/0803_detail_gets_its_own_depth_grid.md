# 0803 -- a detailed part gets its own depth grid; cut specks are dropped where they are noise

Follow-on to `bugs/0802` (hidden-line removal in the DXF exports). Its written residuals: small
mount-hole rims on the camera six-view still broke into dots, and small parts in the viewport
export got coarse detail because one depth grid covered the whole scene.

## First: one residual note in 0802 was wrong

0802 blamed the dotted rims on "a depth discontinuity the 1400-px buffer resolves poorly".
Measured, that is false. In the six-view the pixels are already 21-35 um and the depth test
almost never cuts a small strip -- 0 small strips cut into four or more runs in five of six views,
at most 6 in the last. The viewport, however, really was coarse:

| export | grid span | pixel | camera spans |
|---|---|---|---|
| six-view (one part) | 29-49 mm | 21-35 um | 1396 px |
| viewport (whole scene) | 263 mm | **188 um** | **284 px** |

## Also false: resampled output causing the dots

0802 returned densely resampled points even for fully visible strips, and it seemed likely that
this stopped the silhouette and feature copies of an edge from deduplicating. Emitting original
vertices instead moved the six-view from 3900 to 3934 polylines -- no effect. The change is kept
(an uncut strip should come back unchanged) but it was not the cause.

## What the specks actually were -- an A/B of every 0802 test change

Real camera six-view, one configuration per process:

| configuration | total | under 0.5 mm | over 5 mm |
|---|---|---|---|
| sample along + 3x3 filter + gap closing (0802) | 3934 | 3254 | 227 |
| without the 3x3 filter | 5497 | 4827 | 190 |
| without gap closing | 3984 | 3303 | 227 |
| vertex-only test (with filter and gaps) | 2772 | 2137 | 206 |
| vertex-only, no filter, no gaps | 2016 | 1510 | 199 |

Gap closing does nothing measurable; the 3x3 filter removes ~1500 fragments; **sampling along
segments** is what adds ~1100 sub-0.5 mm cut pieces -- and also what recovers 21 real lines over
5 mm. The cut is correct; its short end pieces at rims are the dots.

## Fix 1: per-part depth tiles

A detailed body (at least 1000 triangles) that is meaningfully smaller than the scene (under 80%
of its span) gets its own full-resolution tile, rasterising **every solid that overlaps it** so the
lens still hides the camera. A strip is tested on the finest tile that contains it; strips spanning
several bodies fall back to the global grid.

Tiles built on the user's viewport: lens 152.4 mm at 108.9 um, camera 55.5 mm at 39.7 um.

**Truth test** -- every strip over 1 mm the export actually tests, visible length measured on each
grid against a 4000 px reference (65.8 um):

| grid | total visible-length error | strips off by more than 0.25 mm |
|---|---|---|
| global 1400 px (0802) | 667 mm | 406 |
| **per-part tiles** | **282 mm** | **144** |

The viewport's lines over 5 mm went 135 -> 130 with tiles; given the truth test, those five were
leaks from the coarse grid, not losses. (The camera tile is finer than the reference, so part of the
remaining "error" is the reference's own.)

## Fix 2: drop cut specks -- only in a single-part view

A visible piece shorter than three pixels, created by the depth test cutting a strip, is below that
test's resolution. Tried in 0802 and reverted because on the 188 um viewport grid it cut real lines.
With tiles it was tried again, against criteria set before looking (tiny fragments fall; lines over
5 mm stay at 227 six-view and 130 viewport):

| rule | six-view over 5 mm | viewport over 5 mm |
|---|---|---|
| drop on every grid | 227 -> **232** | 130 -> **127** |
| drop only on full-resolution grids | 232 | **127** (unchanged -- the loss is on tiles) |
| **drop only in a single-part view** | **232** | **130** |

In a single-part sheet a cut is the part hiding itself at a rim, and the pieces are noise. In a
multi-body view a short visible piece can be a line emerging from behind another body, and dropping
it opens a gap. That distinction is what was measured on this scene; it is stated as observed, not
as a law.

## Measured, same scene

| export | 0802 | 0803 |
|---|---|---|
| camera six-view: polylines | 3900 | **3192** |
| camera six-view: fragments under 0.5 mm | 3254 | **2532** |
| camera six-view: lines over 5 mm | 227 | **232** |
| camera six-view: closed shapes | 40 | **48** |
| viewport: body polylines | 871 | **664** |
| viewport: lines over 5 mm | 135 (with leaks) | 130 (truth-tested) |

Rendered and looked at: the side-view mount-hole rims are now closed rings with few open ends,
where 0802 left them solid with dots.

## Residuals

* A few dots remain on the smallest holes (the back view's upper row) and around the connector pins.
* The single-part / multi-body rule for specks rests on one scene.
* Export time: viewport ~57 s (was ~48 s; the tiles add rasterisation), six-view ~107 s.
* Viewport closed-flag shapes 15 -> 13.

## Guard

`python -m KrakenOS.UI.validate_open3d_0803_detail_gets_its_own_depth_grid` -- display-free,
synthetic boxes. It pins that a small part in a large scene is tested on its own finer tile while a
strip spanning bodies falls back to the global grid; that occlusion by ANOTHER body survives inside a
tile; that an uncut strip returns its original vertices exactly; and that sub-3-px cut pieces are
dropped in a single-part view but kept in a multi-body one. Penta phase 586.
