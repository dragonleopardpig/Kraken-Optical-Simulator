"""Display-free guard for the user-selectable ISO up-axis feature (bugs/0231).

The Iso view hard-coded view-up = (0,1,0) (Y up). Users can now pick which WORLD axis points
up in the Iso view via the "Iso up" toolbar menu (X / Y / Z); the other two axes carry the
diagonal horizontal spread so all three stay visible. `set_camera_preset("iso")` reads the
chosen axis; `_iso_camera_offset_and_view_up` computes the pose.

  (A) HISTORIC Y-UP UNCHANGED: the default "y" reproduces the old Iso EXACTLY -- offset
      (-0.95, 0.55, 0.8)*distance, view-up (0, 1, 0).
  (B) EACH AXIS IS A TRUE ISO: for x/y/z the chosen axis IS the view-up, the camera sits
      ABOVE along it, all three axes have a non-zero offset (all visible), and the sight line
      is oblique (not axis-aligned -> genuinely isometric, not a cardinal plane view).
  (C) HANDLER: `_on_iso_up_axis_changed` reads the tk var, stores `_iso_up_axis`, and
      re-applies the Iso preset (immediate feedback); an unknown value falls back to "y".
  (D) WIRED: set_camera_preset's Iso branch calls the helper; the toolbar wires a radiobutton
      per axis to `iso_up_axis_var` + `_on_iso_up_axis_changed`.

Run: .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_iso_up_axis
Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import types
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.panels.open3d_top_controls import Open3DTopControlsPanel

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Check:
    check: str
    ok: bool
    detail: str


def validate_iso_up_axis() -> list[Check]:
    checks: list[Check] = []
    d = 100.0

    # ---- (A) historic Y-up unchanged ------------------------------------------------------- #
    off_y, up_y = Kraken3DInspector._iso_camera_offset_and_view_up("y", d)
    checks.append(Check(
        "HISTORIC: default Y-up reproduces the old Iso offset (-0.95,0.55,0.8)*d + view-up (0,1,0)",
        bool(np.allclose(off_y, [-95.0, 55.0, 80.0])) and up_y == (0.0, 1.0, 0.0),
        f"offset={np.round(off_y, 2).tolist()} view_up={up_y}",
    ))

    # ---- (B) each axis is a true iso ------------------------------------------------------- #
    ok_b = True
    detail_b = []
    for axis, idx in (("x", 0), ("y", 1), ("z", 2)):
        off, up = Kraken3DInspector._iso_camera_offset_and_view_up(axis, d)
        n = off / float(np.linalg.norm(off))
        is_up = up[idx] == 1.0 and abs(sum(up) - 1.0) < 1e-9
        above = off[idx] > 0.0
        all_visible = all(abs(v) > 1e-6 for v in off)
        oblique = float(np.max(np.abs(n))) < 0.99
        ok_b = ok_b and is_up and above and all_visible and oblique
        detail_b.append(f"{axis}:up={is_up},above={above},vis={all_visible},obl={oblique}")
    checks.append(Check(
        "EACH AXIS: chosen axis is view-up, camera above it, all 3 axes visible, sight line oblique",
        ok_b,
        " ".join(detail_b),
    ))

    # ---- (C) handler updates state + re-applies iso + falls back ---------------------------- #
    class _Stub:
        _ISO_UP_AXIS_INDEX = Kraken3DInspector._ISO_UP_AXIS_INDEX

        def __init__(self, value):
            self._v = value
            self.iso_up_axis_var = types.SimpleNamespace(
                get=lambda: self._v, set=lambda v: setattr(self, "_v", v)
            )
            self._iso_up_axis = "y"
            self.applied = None

        def set_camera_preset(self, preset):
            self.applied = preset

    stub_z = _Stub("z")
    Kraken3DInspector._on_iso_up_axis_changed(stub_z)
    stub_bad = _Stub("diagonal")
    Kraken3DInspector._on_iso_up_axis_changed(stub_bad)
    checks.append(Check(
        "HANDLER: picking an axis stores it + re-applies Iso; an unknown value falls back to y",
        stub_z._iso_up_axis == "z" and stub_z.applied == "iso"
        and stub_bad._iso_up_axis == "y" and stub_bad.applied == "iso",
        f"z->({stub_z._iso_up_axis},{stub_z.applied}) bad->({stub_bad._iso_up_axis},{stub_bad.applied})",
    ))

    # ---- (D) wiring ------------------------------------------------------------------------- #
    preset_src = inspect.getsource(Kraken3DInspector.set_camera_preset)
    toolbar_src = inspect.getsource(Open3DTopControlsPanel.build_view_toolbar)
    init_src = inspect.getsource(Kraken3DInspector.__init__)
    wired = (
        "_iso_camera_offset_and_view_up(self._iso_up_axis" in preset_src
        and "iso_up_axis_var" in toolbar_src
        and "_on_iso_up_axis_changed" in toolbar_src
        and "add_radiobutton" in toolbar_src
        and "value=axis_value" in toolbar_src
        and '"y"' in toolbar_src and '"z"' in toolbar_src and '"x"' in toolbar_src
        and 'self.iso_up_axis_var = tk.StringVar(value="y")' in init_src
    )
    checks.append(Check(
        "WIRED: the Iso branch reads the helper; the toolbar wires a radiobutton per axis to the var + handler",
        wired,
        f"preset_uses_helper={'_iso_camera_offset_and_view_up(self._iso_up_axis' in preset_src} "
        f"toolbar_var={'iso_up_axis_var' in toolbar_src} handler={'_on_iso_up_axis_changed' in toolbar_src} "
        f"radios={'add_radiobutton' in toolbar_src}",
    ))
    return checks


def run_checks() -> "tuple[bool, list[str]]":
    checks = validate_iso_up_axis()
    failures = [f"{c.check} | {c.detail}" for c in checks if not c.ok]
    return (not failures), failures


def main() -> int:
    checks = validate_iso_up_axis()
    failed = [c for c in checks if not c.ok]
    for c in checks:
        print(f"{'PASS' if c.ok else 'FAIL'}: {c.check} | {c.detail}")
    if failed:
        raise SystemExit(1)
    print("ISO up-axis validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
