"""bugs/1002: trigger EVERY command of the Qt shell and write down what each one does.

The session is the guard's own (`KrakenOS.UI.validate_qt_every_command.qt_session`): the Qt shell
started with nothing asked for, as the app starts it, a scene loaded, every command of
`qt.actions.ACTIONS` triggered the way a click does, every question answered "cancel". This
writes all of it down -- the guard holds each command's first response only:

  raised      an exception (in the command, or printed by Qt from its slot)
  asked       what it asked through the UI host
  tk          a Tk dialog function it called, or a Tk root / window / widget / variable it made
  modal       a modal Qt dialog it opened by itself (closed by the session)
  windows     top-level windows that appeared (closed by the session)
  opened      a document handed to the browser / the system viewer (not opened)
  changed     what was different afterwards

Nothing leaves the process: the browser, the system viewer, the flag bundles, the auto-saved
picture, the formula sheet and the scene file are all redirected to a temp folder.

Usage (needs a display; one process, about two minutes):
    python bugs/1002_trigger_every_qt_command.py <out.json> [scene.py]
    python bugs/1002_trigger_every_qt_command.py --table        # the guard's FIRST table, as source
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> int:
    from KrakenOS.UI.validate_qt_every_command import SCENE, qt_session

    as_table = sys.argv[1:2] == ["--table"]
    scene = sys.argv[2] if len(sys.argv) > 2 else str(SCENE)
    try:
        result = qt_session(scene)
    except BaseException:            # the session takes over sys.excepthook: say it here
        import traceback

        traceback.print_exc()
        os._exit(1)
    if as_table:
        print("FIRST = {")
        for name, response in result["first"].items():
            print(f"    {name!r}: {response!r},")
        print("}", flush=True)
    else:
        Path(sys.argv[1]).write_text(json.dumps(result, indent=1), encoding="utf-8")
        for name, entry in result["commands"].items():
            print(f"{name:40s} {entry['seconds']:6.1f} s  {result['first'][name]}")
        print("WROTE", sys.argv[1], flush=True)
    os._exit(0)                      # no interpreter teardown: a VTK/Qt teardown crash must not lose the output


if __name__ == "__main__":
    main()
