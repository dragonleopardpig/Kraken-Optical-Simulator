# 0840 -- point form becomes a table, and the HUD carries object-side DOF

> *"since the banner use a point form, why not display it as a table?"*
> *"can make table form to the system resolution table as well? Add DOF using 1-pixel to it too."*
> *"object-side DOF"*

Every line both actors produce is already `LABEL: value`. Rendering that as prose wasted the
structure that was already there.

## The font, measured rather than assumed

Space-padded columns only align in a MONOSPACE font, and neither actor set one -- VTK's
default is Arial. Rendering each sample off screen and asking VTK AFTER a real render:

    Courier @ 13   32 chars -> 256 px   110 -> 879   223 -> 1783   "MMMM" 0.615  "iiii" 0.612
    Arial   @ 13   32 chars -> 206 px   110 -> 713   223 -> 1422   "MMMM" 0.919  "iiii" 0.227

Courier is exactly **8.000 px per character**, 0.615 of the font size, for every sample
including all-M and all-i. So the switch is not a trade: it makes alignment possible AND turns
bugs/0838's approximate width into an exact one. In Arial a per-character width does not
exist, which is why 0838 had to pick a conservative 0.55 and live with the error.

## Result

    Resolution     4.102 um/px
    Magnification  1.1x (sensor/FOV)
    Pixels         5120 x 5120
    Pixel size     4.5 um
    Sensor roll    -90 deg (portrait)
    DOF (1 px)     0.07057 mm object side (N 4.5, |m| 1.097, c 4.5 um)

    SOLVE           delivering 21 x 21 mm (|m| 1.097); the lens moved -145.2 mm along its leg
    FOCUS           the image forms 0.1155 mm in front of the sensor -- spot 0.489 um there ...
      Face A field  0.1155 mm in front of the sensor
      Face B field  0.1155 mm in front of the sensor
    Landed          the blur on the sensor (3.06 um) is inside one pixel (4.5 um) -- nothing ...
    STRAY LIGHT     8 ray(s) reach the sensor by another optical route and land up to 1.56 ...

A line with NO label -- `SOLVE REFUSED -- the drawn scene does NOT deliver this request` -- spans
the full width. A heading is not a value and should not be forced into a column. A label is
only taken as one if it is short and carries no sentence punctuation, so a heading with an
interior colon cannot be cut in half.

## Object-side depth of field

    DOF = 2 N c (1 + |m|) / m^2        c = one pixel, N = the lens f-number

Object side was chosen explicitly: it answers how much DEVICE DEPTH stays inside a pixel of
blur, which is the inspection question. At N 4.5, |m| 1.097 and a 4.5 um pixel that is
**0.0706 mm** -- on a 1 mm device, about a fourteenth of its thickness in focus at once.

The row names its side, its criterion and all three inputs. The banner already reports an
image-side residual ("the image forms 0.1155 mm in front of the sensor"), and two depths on
one screen without labels is the bugs/0828 failure waiting to happen.

Only for an **FNO** aperture. An EPD or NA entry is not an f-number, and converting one
silently would feed a fabricated input into a number the user will act on. A missing
f-number, magnification or pixel yields no row at all.

## Guard

`KrakenOS/UI/validate_open3d_0840_point_form_becomes_a_table.py`, penta phase 619.

Its INDENT check was fake on the first run:

    if indented and indented[0].index(...) == (cols.pop() if cols else -1) or indented:

`cols` had already been emptied by the check above, and the trailing `or indented` made the
whole expression true whenever the list was non-empty -- the same always-true shape as the
bugs/0826 tally replaced earlier the same session. It now asserts that the sub-row keeps its
leading indent AND lands on the common column.
