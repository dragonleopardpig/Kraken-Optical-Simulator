"""bugs/0998: after a lens swap the editor says "Enter the field you want in the FOV dialog". Does the dialog open?

Builds the given shell with its 3D scene, asks the model for the after-swap prompt and waits two
seconds. Prints what the model answered and whether the FOV dialog was asked for.

    python bugs/0998_fov_prompt_after_swap.py qt|tk
"""
import os
import sys
import time
from pathlib import Path

LAYOUT = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")


def main(shell: str) -> None:
    opened: list = []
    if shell == "qt":
        from KrakenOS.UI.qt.app import build

        app, window = build(["probe"])
        window.show()
        editor = window.editor

        def settle(seconds: float) -> None:
            end = time.time() + seconds
            while time.time() < end:
                app.processEvents()
                time.sleep(0.02)

        settle(1.5)
        editor.layout_files[LAYOUT.stem] = LAYOUT
        editor.load_layout_by_name(LAYOUT.stem, refresh=False)
        settle(1.0)
        inspector = window.build_inspector_view().inspector
    else:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        editor = KrakenLayoutEditor()

        def settle(seconds: float) -> None:
            end = time.time() + seconds
            while time.time() < end:
                editor.update()
                time.sleep(0.02)

        settle(1.0)
        editor.layout_files[LAYOUT.stem] = LAYOUT
        editor.load_layout_by_name(LAYOUT.stem, refresh=False)
        settle(0.5)
        editor.open_3d_view()
        inspector = editor._three_d_inspector
    settle(2.5)
    inspector._open_quick_estimation_fov_popup = lambda plane: opened.append(plane)     # do not open it: note that it was asked for
    said = editor._prompt_fov_solve_after_swap(True)
    settle(2.0)
    print(f"RESULT {shell}: the model said {said.strip()!r}; the FOV dialog was asked for: {opened or 'never'}; "
          f"the inspector has a Tk window: {getattr(inspector, 'window', None) is not None}", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main(sys.argv[1])
