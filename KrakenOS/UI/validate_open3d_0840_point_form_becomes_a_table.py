"""bugs/0840 guard -- point form is rendered as a table, and the HUD carries object-side DOF.

The user: *"since the banner use a point form, why not display it as a table?"* and
*"can make table form to the system resolution table as well? Add DOF using 1-pixel to it
too."* -- and, asked which convention, *"object-side DOF"*.

Every line both actors produce is already ``LABEL: value``. Rendering that as prose wasted the
structure that was already there.

Alignment by space padding needs a MONOSPACE font, so both actors move to Courier. That is not
a compromise, it is strictly better: rendering each sample off screen and asking VTK afterwards
gives

    Courier @ 13   32 chars -> 256 px   110 -> 879   223 -> 1783   "MMMM" 0.615   "iiii" 0.612
    Arial   @ 13   32 chars -> 206 px   110 -> 713   223 -> 1422   "MMMM" 0.919   "iiii" 0.227

so in Courier the per-character width is exactly 8.000 px and the width estimate bugs/0838 had
to approximate becomes exact. In Arial a per-character width does not exist.

Checks:
  FONT    -- both actors are Courier, and the ratio is the MEASURED 0.615.
  ALIGN   -- every labelled row's detail starts at the same column.
  HEADING -- a line with no label spans the full width, not forced into a column.
  INDENT  -- an indented sub-row keeps its indent and still aligns.
  WRAP    -- a detail too long for its column continues INDENTED to that column.
  DOF     -- the object-side one-pixel formula, its value, and its refusals.
"""
from __future__ import annotations

import inspect as _inspect

HUD = [
    "Resolution: 4.102 um/px",
    "Magnification: 1.1x (sensor/FOV)",
    "Pixels: 5120 x 5120",
    "Pixel size: 4.5 um",
    "Sensor roll: -90 deg (portrait)",
]
BANNER = [
    "SOLVE: delivering 21 x 21 mm (|m| 1.097); the lens moved -145.2 mm along its leg",
    "FOCUS: the image forms 0.1155 mm in front of the sensor -- spot 0.489 um there vs 3.06 um",
    "  Face A field: 0.1155 mm in front of the sensor",
    "Landed: the blur on the sensor (3.06 um) is inside one pixel (4.5 um) -- nothing to move",
]
REFUSAL = [
    "SOLVE REFUSED -- the drawn scene does NOT deliver this request",
    "delivered now: |m| 0.407  FOV 56.57 x 56.57 mm",
]


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.system_info_hud import (
        BANNER_CHAR_WIDTH_RATIO,
        format_depth_of_field_lines,
        format_kv_table,
        split_label,
    )
    from KrakenOS.UI import open3d_inspector as oi

    hud_src = _inspect.getsource(oi.Kraken3DInspector._update_system_info_hud)
    ban_src = _inspect.getsource(oi.Kraken3DInspector._update_solve_refusal_banner)
    if "SetFontFamilyToCourier" in hud_src and "SetFontFamilyToCourier" in ban_src:
        notes.append("FONT = both actors are Courier")
    else:
        notes.append("FONT one of the actors is still proportional")
        ok = False
    if abs(float(BANNER_CHAR_WIDTH_RATIO) - 0.615) <= 1e-9:
        notes.append("FONT = the ratio is the MEASURED Courier 0.615, not an estimate")
    else:
        notes.append(f"FONT the ratio is {BANNER_CHAR_WIDTH_RATIO}, not the measured 0.615")
        ok = False
    if "format_kv_table(" in ban_src:
        notes.append("FONT = the banner renders through the table formatter")
    else:
        notes.append("FONT the banner does not use the table formatter")
        ok = False

    def detail_columns(rendered, sources):
        cols = set()
        for line, src in zip(rendered, sources):
            _i, label, detail = split_label(src)
            if label and detail:
                cols.add(line.index(detail.split(" ")[0]))
        return cols

    table = format_kv_table(BANNER, width=236)
    cols = detail_columns(table, BANNER)
    common_col = next(iter(cols)) if len(cols) == 1 else None
    if common_col is not None:
        notes.append(f"ALIGN = every labelled detail starts at column {common_col}")
    else:
        notes.append(f"ALIGN details start at differing columns {sorted(cols)}")
        ok = False

    ref = format_kv_table(REFUSAL, width=236)
    if ref[0] == REFUSAL[0]:
        notes.append("HEADING = a line with no label spans the full width, untouched")
    else:
        notes.append(f"HEADING the heading was forced into a column: {ref[0]!r}")
        ok = False

    # A REAL check. The first draft read
    #     if indented and indented[0].index(...) == (cols.pop() if cols else -1) or indented:
    # where `cols` had already been emptied above and the trailing `or indented` made the whole
    # expression true whenever the list was non-empty -- the same always-true shape as the
    # bugs/0826 tally this session already had to replace. The claim worth making is that the
    # sub-row keeps its leading indent AND lands on the common column.
    indented = [line for line in table if line.lstrip().startswith("Face A")]
    if not indented:
        notes.append("INDENT the indented sub-row vanished from the table")
        ok = False
    elif not indented[0].startswith("  "):
        notes.append(f"INDENT the sub-row lost its indent: {indented[0][:34]!r}")
        ok = False
    elif common_col is not None and indented[0].index("0.1155") != common_col:
        notes.append(
            f"INDENT the sub-row's detail starts at {indented[0].index('0.1155')}, "
            f"not the common column {common_col}"
        )
        ok = False
    else:
        notes.append(
            f"INDENT = the sub-row keeps its indent AND lands on column {common_col}: "
            f"{indented[0][:34]!r}"
        )

    narrow = format_kv_table(BANNER, width=60)
    label_w = max(len(i + l) for i, l, _d in (split_label(x) for x in BANNER) if l)
    continuations = [line for line in narrow if line.startswith(" " * (label_w + 2))
                     and not line.strip().startswith("Face")]
    if continuations:
        notes.append(
            f"WRAP = a detail too long for its column continues indented to it "
            f"({len(continuations)} continuation rows at width 60)"
        )
    else:
        notes.append("WRAP no indented continuation appeared at width 60")
        ok = False

    dof = format_depth_of_field_lines(4.5, 1.097, 4.5)
    if dof and "object side" in dof[0] and "N 4.5" in dof[0] and "c 4.5 um" in dof[0]:
        notes.append(f"DOF = {dof[0]}")
    else:
        notes.append(f"DOF the row does not name its side and inputs: {dof}")
        ok = False
    expected = 2.0 * 4.5 * 0.0045 * (1.0 + 1.097) / (1.097 ** 2)
    if dof and f"{expected:.4g}" in dof[0]:
        notes.append(f"DOF = the value is 2 N c (1+|m|)/m^2 = {expected:.4g} mm")
    else:
        notes.append(f"DOF the value does not match the formula ({expected:.4g})")
        ok = False
    refused = [
        format_depth_of_field_lines(None, 1.097, 4.5),
        format_depth_of_field_lines(4.5, None, 4.5),
        format_depth_of_field_lines(4.5, 1.097, None),
        format_depth_of_field_lines(4.5, 0.0, 4.5),
    ]
    if all(r == [] for r in refused):
        notes.append("DOF = a missing f-number, magnification or pixel yields NO row, never a guess")
    else:
        notes.append(f"DOF a missing input still produced a row: {refused}")
        ok = False

    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if ("=" in note or note.startswith("SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
