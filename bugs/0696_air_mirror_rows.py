"""0696: first-surface mirror rows carry glass AIR.

The 0695 stamp set glass=BK7 on every swapped row -- but the window/centre
mirrors and the two big RA mirrors fold FIRST-SURFACE (the beam never enters
their glass). The sequential medium bookkeeping consumed those BK7 fields for
ADDITIVE-source rays (chain rays suppress virtual glass on folded scenes):
measured, arm B climbed + rode ~189 mm of the lens leg in phantom BK7
(events: surface 6 'medium_change' AIR->BK7 at (0,28.3,-33.3), back to AIR
only at the Front Datum) -- the whole 19.2 mm faceB defocus.
"""
from pathlib import Path

SCENE = Path("attachment/om05a_folded.py")
AIR_ROWS = {
    "First RA mirror A", "First RA mirror B",
    "Centre RA mirror A", "Centre RA mirror B",
    "RA mirror 1 (50 mm)", "RA mirror 2 (40 mm)",
}


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = SCENE.resolve()
    editor.load_layout_by_name("p")
    n = 0
    for row in editor.rows:
        if str(getattr(row, "name", "")) in AIR_ROWS and str(row.glass) != "AIR":
            row.glass = "AIR"
            n += 1
    print(f"set {n} first-surface mirror rows to AIR")
    editor._sync_table()
    editor._write_layout_file(SCENE.resolve())
    editor.destroy()
    print("saved", SCENE)


if __name__ == "__main__":
    main()
