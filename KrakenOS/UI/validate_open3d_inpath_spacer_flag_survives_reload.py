"""Display-free guard for bugs/0165: the in-path trailing-spacer flag must survive a
save/reload so the suppressed "big circle" (bugs/0093) does not come back.

The in-path promote (bugs/0079) inserts a trailing AIR gap-carrier row right after a
promoted optical solid and flags it ``advanced.InPathTrailingSpacer = True`` so the
display skips its big Ø-clear-aperture disc + surface ring (bugs/0093). But that flag
was never registered in the ``ADVANCED_SURFACE_ATTR_NAMES`` allowlist, so loading a
saved ``.py`` layout ran every surface's ``advanced`` dict through
``_advanced_surface_attrs_from_spec`` / ``_row_from_surface`` and SILENTLY DROPPED the
flag -- the spacer reverted to an ordinary surface and drew the big disc again (and a
pick region, so it was selectable as "S2").

The fix registers ``InPathTrailingSpacer`` in ``ADVANCED_SURFACE_FIELD_GROUPS``. This
guard pins:

  * the flag is in the allowlist (fail-before/pass-after: it was absent);
  * a spacer spec ``{'advanced': {'InPathTrailingSpacer': True}}`` round-trips through
    BOTH import paths (dict spec ``_row_from_layout_item`` and Kos.surf
    ``_row_from_surface``) with the flag intact;
  * ``_is_inpath_trailing_spacer_row`` stays True after each round-trip (so the 0093
    display skips keep firing);
  * a plain Standard surface does NOT spuriously gain the flag.

The rendered Ø disc only builds under the PyVista backend (absent headless), so the
disc itself still needs an in-app eyeball -- but the flag survival is unit-pinned here.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_inpath_spacer_flag_survives_reload

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import KrakenOS as Kos

from KrakenOS.UI.scene_builder import _is_inpath_trailing_spacer_row
from KrakenOS.UI.services.advanced_surface_attrs import (
    ADVANCED_SURFACE_ATTR_NAMES,
    _advanced_surface_attrs_from_spec,
    _canonical_advanced_surface_attr,
)
from KrakenOS.UI.services.layout_import_export import LayoutImportExportMixin

_SPACER_FLAG = "InPathTrailingSpacer"


def _spacer_spec() -> dict:
    return {
        "surface": "Standard",
        "name": "Promoted OPTICAL STEP optical solid -> next gap (AIR)",
        "thickness": 4.3291845356,
        "diameter": 78.0,
        "glass": "AIR",
        "advanced": {_SPACER_FLAG: True},
    }


def _spacer_surf():
    surf = Kos.surf()
    surf.Name = "Promoted OPTICAL STEP optical solid -> next gap (AIR)"
    surf.Thickness = 4.3291845356
    surf.Diameter = 78.0
    surf.Glass = "AIR"
    setattr(surf, _SPACER_FLAG, True)
    return surf


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    # 1) fail-before/pass-after: the flag must be a recognised advanced attr.
    if _SPACER_FLAG not in ADVANCED_SURFACE_ATTR_NAMES:
        failures.append(
            f"FAIL: {_SPACER_FLAG!r} is not in ADVANCED_SURFACE_ATTR_NAMES -- it would be "
            "stripped on save/reload (the big-circle recurrence)"
        )
    if _canonical_advanced_surface_attr(_SPACER_FLAG) != _SPACER_FLAG:
        failures.append(
            f"FAIL: _canonical_advanced_surface_attr({_SPACER_FLAG!r}) = "
            f"{_canonical_advanced_surface_attr(_SPACER_FLAG)!r} (not resolvable, would drop)"
        )

    # 2) the spec-extraction helper preserves the flag.
    attrs = _advanced_surface_attrs_from_spec(_spacer_spec())
    if attrs.get(_SPACER_FLAG) is not True:
        failures.append(
            f"FAIL: _advanced_surface_attrs_from_spec dropped the spacer flag (got {attrs!r})"
        )

    # 3) dict-spec import path (_row_from_layout_item) keeps the flag + spacer identity.
    row_dict = LayoutImportExportMixin._row_from_layout_item(_spacer_spec())
    if (row_dict.advanced or {}).get(_SPACER_FLAG) is not True:
        failures.append(
            f"FAIL: dict-spec import dropped the spacer flag (row.advanced={row_dict.advanced!r})"
        )
    if not _is_inpath_trailing_spacer_row(row_dict):
        failures.append(
            "FAIL: _is_inpath_trailing_spacer_row is False after dict-spec import -- the "
            "0093 disc/ring skips would not fire (big circle returns)"
        )

    # 4) Kos.surf round-trip path (_row_from_surface) keeps the flag too.
    row_surf = LayoutImportExportMixin._row_from_surface(_spacer_surf(), 2, 5)
    if (row_surf.advanced or {}).get(_SPACER_FLAG) is not True:
        failures.append(
            f"FAIL: Kos.surf import dropped the spacer flag (row.advanced={row_surf.advanced!r})"
        )
    if not _is_inpath_trailing_spacer_row(row_surf):
        failures.append("FAIL: _is_inpath_trailing_spacer_row is False after Kos.surf import")

    # 5) a plain Standard surface must NOT spuriously read as a spacer.
    plain = LayoutImportExportMixin._row_from_layout_item(
        {"surface": "Standard", "name": "Lens Front Datum", "thickness": 1.45, "diameter": 35.0, "glass": "AIR"}
    )
    if _is_inpath_trailing_spacer_row(plain):
        failures.append("FAIL: a plain Standard surface is mis-flagged as an in-path spacer")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0165 in-path trailing-spacer flag survives reload")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] in-path trailing-spacer flag survives save/reload -- big circle stays suppressed (bugs/0165)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
