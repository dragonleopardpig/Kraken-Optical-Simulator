"""Guard: the lens STEP overlay stays ATTACHED to its surrogate on the AZ85 folded scene (bugs/0412).

bugs/0374 re-registers the lens STEP overlay by pinning its optical GLASS-BLOCK centre on the
surrogate's datum-span centre (display-only), so the mechanical body no longer needs a manual
glass-alignment nudge. But layouts SAVED before 0374 carry that old nudge
(``lens_step_placement_offset_xyz`` z = mechanical_front - front_glass_vertex, the pre-0374 body-face-pin
correction). The aligner adds the placement offset ON TOP of the 0374 pin, so the stale nudge now
DOUBLE-counts and detaches the STEP by ~its own magnitude (the user's AZ85 "lens STEP detached" report:
z = -3.849 = body_hi - glass_hi for ELS-85).

Fix = drop the stale offset (z -> 0); the 0374 pin then lands the STEP exactly on the surrogate because
the ELS-85 GLASS SPAN equals the surrogate DATUM SPAN (the surrogate was built from the STEP's glass
vertices). Display-free: a data check on the committed layout + a pure-geometry reimplementation of the
pin + a getsource check of the additive mechanism.

Checks
------
* LAYOUT-CLEAN -- the committed AZ85 layout's ``lens_step_placement_offset_xyz`` z is ~0 (no stale
  glass-alignment nudge left to double-count the 0374 pin).
* PIN-GEOMETRY -- with the real ELS-85 glass metrics and a surrogate whose datum span equals the glass
  span, the 0374 glass-centre pin lands the front glass vertex ON the front datum at offset 0 (gap ~0),
  and the old glass-alignment offset (body_hi - glass_hi) detaches it by that amount.
* MECHANISM    -- the aligner adds ``placement_offset`` AFTER ``target_front_z`` (so a stale offset
  detaches), and ``_lens_step_display_front_z`` pins the glass-block centre on the datum-span centre.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_lens_step_datum_attached

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import re
from pathlib import Path

# The real ELS-85 glass metrics (from the STEP; also on disk in attachment/cad_cache).
_ELS85 = {"body_hi": 28.32542379414665, "body_lo": -30.866049717850444,
          "glass_hi": 24.476299125547822, "glass_lo": -30.523700874452214}
_AZ85_LAYOUT = Path(__file__).resolve().parents[1] / "common_optical_layouts" / "machine_vision_AZ85_RA_Mirror.py"


def _pin_front_glass_vertex_world(m, front_datum, rear_datum, offset_z, front_face="max"):
    """Reference reimplementation of _lens_step_display_front_z + the aligner (max face), returning the
    world z of the FRONT glass vertex. Mirrors layout_polyline_display exactly:
      target = datum_centre - (body_hi - glass_centre)      # glass-centre pin
      world(u) = target + (body_hi - u)                     # aligner, front_face='max'
      + placement_offset_z                                  # stacked on top
    """
    glass_center_u = 0.5 * (m["glass_lo"] + m["glass_hi"])
    datum_center = 0.5 * (front_datum + rear_datum)
    delta = m["body_hi"] - glass_center_u            # front_face == 'max'
    target = datum_center - delta
    vertex_u = m["glass_hi"]                          # the front (max-side) glass vertex
    return target + (m["body_hi"] - vertex_u) + offset_z


def _check_layout_clean(failures, notes):
    if not _AZ85_LAYOUT.exists():
        failures.append(f"LAYOUT-CLEAN: {_AZ85_LAYOUT.name} not found")
        return
    text = _AZ85_LAYOUT.read_text(encoding="utf-8")
    match = re.search(r"lens_step_placement_offset_xyz'\s*:\s*\[([^\]]*)\]", text)
    if not match:
        failures.append("LAYOUT-CLEAN: no lens_step_placement_offset_xyz in the AZ85 layout")
        return
    try:
        z = float(match.group(1).split(",")[2])
    except (IndexError, ValueError):
        failures.append(f"LAYOUT-CLEAN: could not parse the offset ({match.group(1)!r})")
        return
    if abs(z) > 1e-6:
        failures.append(f"LAYOUT-CLEAN: AZ85 carries a stale lens offset z={z:g} (double-counts the 0374 glass-centre pin -> detach)")
    if not [f for f in failures if f.startswith("LAYOUT-CLEAN")]:
        notes.append("layout-clean = AZ85 lens_step_placement_offset z is 0 (no stale glass-alignment nudge)")


def _check_pin_geometry(failures, notes):
    glass_span = _ELS85["glass_hi"] - _ELS85["glass_lo"]
    body_span = _ELS85["body_hi"] - _ELS85["body_lo"]
    if not (body_span < 1.6 * glass_span):
        failures.append("PIN-GEOMETRY: ELS-85 should be a close barrel (glass-centre pin active)")
    # surrogate whose datum span == glass span (built from the STEP glass vertices)
    front_datum, rear_datum = 100.0, 100.0 + glass_span
    gap0 = _pin_front_glass_vertex_world(_ELS85, front_datum, rear_datum, 0.0) - front_datum
    if abs(gap0) > 1e-6:
        failures.append(f"PIN-GEOMETRY: offset 0 must land the front glass vertex ON the front datum (gap {gap0:+.4g})")
    stale = _ELS85["body_hi"] - _ELS85["glass_hi"]   # the pre-0374 body-face-pin correction
    gap_stale = _pin_front_glass_vertex_world(_ELS85, front_datum, rear_datum, -stale, ) - front_datum
    if abs(gap_stale + stale) > 1e-6:
        failures.append(f"PIN-GEOMETRY: a stale glass-alignment offset must detach by its magnitude (got {gap_stale:+.4g}, expected {-stale:+.4g})")
    if not [f for f in failures if f.startswith("PIN-GEOMETRY")]:
        notes.append(f"pin-geometry = offset 0 attaches (gap {gap0:+.2g}); stale offset detaches by {stale:.3f}mm")


def _check_mechanism(failures, notes):
    from KrakenOS.UI.services.layout_polyline_display import LayoutPolylineDisplayMixin

    aligner = inspect.getsource(LayoutPolylineDisplayMixin._cad_mesh_aligned_to_optical_axis)
    tpin = aligner.find("aligned[:, 2] += float(target_front_z)")
    toff = aligner.find("aligned[:, :3] += placement_offset")
    if tpin < 0 or toff < 0 or not (tpin < toff):
        failures.append("MECHANISM: the aligner must add placement_offset AFTER target_front_z (so a stale offset detaches)")
    pin = inspect.getsource(LayoutPolylineDisplayMixin._lens_step_display_front_z)
    if "datum_center" not in pin or "glass_center_u" not in pin:
        failures.append("MECHANISM: _lens_step_display_front_z must pin the glass-block centre on the datum-span centre (0374)")
    if not [f for f in failures if f.startswith("MECHANISM")]:
        notes.append("mechanism = aligner stacks placement_offset on the glass-centre pin (double-count is a stale offset)")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (_check_layout_clean, _check_pin_geometry, _check_mechanism):
        try:
            check(failures, notes)
        except Exception as exc:
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_lens_step_datum_attached (bugs/0412) ===")
    for note in notes:
        print(f"  {'ok ' if '=' in note else 'XX '} {note}")
    if not passed:
        n = len([x for x in notes if "=" not in x])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll lens-STEP-datum-attached checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
