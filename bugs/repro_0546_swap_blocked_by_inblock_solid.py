"""bugs/0546 repro -- "tried to swap lens, but got error" (flag_20260804_204450_689).

The AZ85 + RA-mirror + beam-splitter scene (attachment/machine_vision_AZ85_RA_Mirror_BS.py)
refuses "Swap Imaging Lens from Folder" with

    This scene has no imaging-lens surrogate (Front/Rear Vertex Datum) to swap.
    Use Add Imaging Lens to add one first.

although the scene obviously HAS one.  `_imaging_lens_block_indices` finds the tight block
(front=1 .. rear=6) and then vetoes it because row 3 is the promoted beam-splitter cube --
bugs/0381's "a foreign element inside the block means we must not swap it away" rule.

But a promoted optical solid is ABSOLUTELY placed (``axis_move = 0``, pose = station +
desp_z): its ROW INDEX says nothing about where it sits.  Here the cube is physically
UPSTREAM of the whole lens (display x -38..45 vs the lens at x 94..149) and only landed at
index 3 because ``_step_overlay_insert_index`` inserts after the current selection.  So the
veto fires on a scene the swap could serve perfectly well.

Run:  .devenv/state/venv/bin/python bugs/repro_0546_swap_blocked_by_inblock_solid.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LAYOUT = ROOT / "attachment" / "machine_vision_AZ85_RA_Mirror_BS.py"


class _Row:
    def __init__(self, name, thickness=0.0, desp_z=0.0):
        self.name = name
        self.thickness = float(thickness)
        self.desp_z = float(desp_z)
        self.desp_x = 0.0
        self.desp_y = 0.0
        self.surface = "Standard"


def _scene_rows_from_layout() -> list[_Row]:
    """The flagged scene's rows, read straight out of the user's saved layout."""
    source = LAYOUT.read_text(encoding="utf-8")
    fields: dict[str, dict[str, str]] = {}
    for match in re.finditer(r"^\s*(s\d+)\.(\w+)\s*=\s*(.+?)\s*$", source, re.M):
        fields.setdefault(match.group(1), {})[match.group(2)] = match.group(3)
    rows = []
    for var in sorted(fields, key=lambda name: int(name[1:])):
        entry = fields[var]
        rows.append(
            _Row(
                entry.get("Name", "''").strip("'\""),
                float(entry.get("Thickness", "0.0")),
                float(entry.get("DespZ", "0.0")),
            )
        )
    return rows


def _editor(rows):
    from KrakenOS.UI.services import layout_table_workbench as ltw
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    if getattr(ltw, "Path", None) is None:  # late-bound by _sync_layout_globals at init
        ltw.Path = Path
    editor = LayoutTableWorkbenchMixin.__new__(LayoutTableWorkbenchMixin)
    editor.rows = rows
    return editor


def main() -> int:
    rows = _scene_rows_from_layout()
    print(f"scene: {LAYOUT.name} -- {len(rows)} rows")
    stations = [0.0]
    for row in rows[:-1]:
        stations.append(stations[-1] + row.thickness)
    for index, row in enumerate(rows):
        print(
            f"  S{index}  station={stations[index]:9.3f}  desp_z={row.desp_z:11.3f}"
            f"  pose_z={stations[index] + row.desp_z:9.3f}   {row.name}"
        )

    editor = _editor(rows)
    front, rear = editor._imaging_lens_block_indices()
    print(f"\n_imaging_lens_block_indices() -> ({front}, {rear})")
    if front is None:
        print(
            "PRE-FIX behaviour: the swap is refused -- 'This scene has no imaging-lens\n"
            "surrogate (Front/Rear Vertex Datum) to swap.'  The block IS there (S1..S6); the\n"
            "promoted beam-splitter row inside it vetoes the whole swap."
        )
        return 1

    preservable, blocking = editor._imaging_lens_block_foreign_rows(rows, front, rear)
    print(
        f"foreign rows inside the block: preservable={preservable} blocking={blocking}\n"
        f"  -> the promoted BS row S{preservable[0] if preservable else '?'} is LIFTED OUT of the\n"
        "     block, re-seated after the new rear datum and given a desp_z that absorbs the\n"
        "     station delta, so it does not move (bugs/0546).\n"
        "FIXED: the swap runs and preserves the beam splitter."
    )
    return 0 if preservable and not blocking else 1


if __name__ == "__main__":
    raise SystemExit(main())
