"""Regression: undo across a STEP overlay import does a full scene refresh.

User flag (flag_20260531_094104_762): "pressing Ctrl-z to Undo: wierd
changed of color and placement of elements." The scene was left with
a stale STEP overlay actor while ``_selected_step_label`` was None,
because ``_STEP_DISPLAY_HISTORY_SETTING_KEYS`` included
``*_step_path``. A path transition (None -> file or file -> None) was
classified as "display-only" and the inspector took the translate-
only fast path, which can shift existing actors but cannot add or
remove them.

The fix drops the ``*_step_path`` keys from that frozenset so any undo
that crosses an import/clear of a STEP overlay falls through to the
full refresh. This test verifies the classifier:

* placement-offset-only delta -> stays display-only
* path-only delta -> NOT display-only
* mixed delta -> NOT display-only
"""

from __future__ import annotations

import sys

from KrakenOS.UI.services.layout_table_workbench import (
    _STEP_DISPLAY_HISTORY_SETTING_KEYS,
)


def _run() -> int:
    failures: list[str] = []

    # 1. Path keys must NOT be in the display-only set.
    for label in ("camera", "lens", "optical", "led"):
        key = f"{label}_step_path"
        if key in _STEP_DISPLAY_HISTORY_SETTING_KEYS:
            failures.append(
                f"{key!r} is in the display-only set; an undo across STEP "
                "import/clear would take the translate-only fast path and "
                "leave a stale actor."
            )

    # 2. Placement-offset keys must remain in the set so the fast path
    #    still handles pure-translation undos.
    for label in ("camera", "lens", "optical", "led"):
        key = f"{label}_step_placement_offset_xyz"
        if key not in _STEP_DISPLAY_HISTORY_SETTING_KEYS:
            failures.append(
                f"{key!r} is missing from the display-only set; pure-"
                "translation undos will pay a full plot refresh."
            )

    # 3. Mixed delta containing a path change must not be a subset of
    #    the display-only keys.
    mixed = {"optical_step_path", "optical_step_placement_offset_xyz"}
    if mixed <= _STEP_DISPLAY_HISTORY_SETTING_KEYS:
        failures.append(
            "mixed delta {path, placement_offset} is a subset of the "
            "display-only keys; the path change would not force a full "
            "refresh."
        )

    if failures:
        print("FAIL: undo display-only classifier regression:", file=sys.stderr)
        for line in failures:
            print(f"  - {line}", file=sys.stderr)
        return 1

    print(
        "PASS: undo display-only classifier excludes *_step_path so import/"
        "clear undos force a full scene refresh."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_run())
