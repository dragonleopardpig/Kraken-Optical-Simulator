"""bugs/0046 -- a cemented doublet must read as TWO cemented elements in 3D,
not three stacked slabs, when the prescription models the bond as its own
microns-thick glass layer.

Zemax's ``Doublet_4_surf_no_TDE.zmx`` ("A SIMPLE DOUBLET USING A CROWN AND A
FLINT") models the crown/flint bond as a real 7.5 um ``___BLANK`` cement glass
between the BK7 crown and the F2 flint -- THREE distinct glasses. KrakenOS's
``Prerequisites3D`` builds one ``BBB`` solid per glass-bearing surface, so that
7.5 um bond becomes a full-aperture standalone slab stacked between its
neighbours: in the 3D perspective view it reads as a duplicated lens element,
while the flat 2D meridional slice collapses it to a sub-pixel hairline (the
"3D not matching 2D" flag). Both views render the SAME traced scene data, so
this is not a North-Star #2 violation -- it is a 3D legibility artifact.

The fix lives in ``_iter_3d_side_body_meshes``: a glass layer thinner than
``_CEMENT_LAYER_MAX_AXIAL_THICKNESS_MM`` (a cement/optical-contact bond, never a
free-standing element) keeps its actor -- so ``_row_actor_map`` centroid queries
still resolve and the cement optical surface stays in ``AAA`` for ray tracing --
but is drawn invisibly (opacity 0). A cemented doublet then reads as two
elements, matching 2D.

This is display-free (it exercises the real ``_iter_3d_side_body_meshes`` against
a ``__new__``-built editor; no Tk root) and SKIPs cleanly if PyVista/VTK is
unavailable. It also renders the doublet's visible bodies to a PNG so the visual
result can be eyeballed (VTK-property assertions alone once missed a ghost-block
regression). Folded into the comprehensive harness as Phase 51.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_cemented_doublet_body_count
"""
from __future__ import annotations

from pathlib import Path

from KrakenOS.UI import layout_editor as layout_editor_module
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
from KrakenOS.UI.services.three_d_scene_tools import (
    _CEMENT_LAYER_MAX_AXIAL_THICKNESS_MM,
)
from KrakenOS.UI.surface_table_model import SurfaceRow, surface_rows_to_specs

_VISIBLE_OPACITY = 0.01  # below this a body is effectively not drawn


def _visible_bodies(rows: list[SurfaceRow]) -> list[tuple[int, float, str, float]]:
    """Build the system display-free and return (row_index, opacity, name,
    thickness) for every side-body mesh the 3D scene would draw."""
    specs = surface_rows_to_specs(rows)
    system = layout_editor_module._build_system_from_specs(specs, build=1)
    editor = _snapshot_editor(rows, {})
    items = editor._iter_3d_side_body_meshes(system, include_reference_surfaces=False)
    out = []
    for item in items:
        idx = int(item.row_index)
        out.append((idx, float(item.opacity), rows[idx].name, float(rows[idx].thickness)))
    return out


def _lens_rows(*lens: SurfaceRow) -> list[SurfaceRow]:
    return [
        SurfaceRow(surface="Object", name="Object", thickness=100.0, diameter=20.0, glass="AIR"),
        SurfaceRow(surface="Standard", name="Stop", thickness=2.0, diameter=20.0, glass="AIR", rc=0.0),
        *lens,
        SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=30.0, glass="AIR"),
    ]


# Crown + 7.5 um cement BLANK + flint -- the flagged prescription's shape.
DOUBLET_WITH_CEMENT = _lens_rows(
    SurfaceRow(surface="Standard", name="Crown front", thickness=8.0, diameter=30.0, glass="N-BK7", rc=52.46),
    SurfaceRow(surface="Standard", name="Cement", thickness=0.0075, diameter=30.0, glass="N-SF2", rc=-55.46),
    SurfaceRow(surface="Standard", name="Flint front", thickness=5.0, diameter=30.0, glass="F2", rc=-55.46),
    SurfaceRow(surface="Standard", name="Flint back", thickness=114.0, diameter=30.0, glass="AIR", rc=-300.0),
)

# A clean singlet -- one glass gap, one body, nothing suppressed.
SINGLET = _lens_rows(
    SurfaceRow(surface="Standard", name="L1 front", thickness=8.0, diameter=30.0, glass="N-BK7", rc=60.0),
    SurfaceRow(surface="Standard", name="L1 back", thickness=110.0, diameter=30.0, glass="AIR", rc=-60.0),
)

# A genuine cemented doublet WITHOUT a modelled bond layer: two thick glasses
# share the cement interface directly -> two bodies, both visible (the fix must
# not touch real elements).
DOUBLET_NO_BOND_LAYER = _lens_rows(
    SurfaceRow(surface="Standard", name="Crown", thickness=8.0, diameter=30.0, glass="N-BK7", rc=52.46),
    SurfaceRow(surface="Standard", name="Flint", thickness=5.0, diameter=30.0, glass="F2", rc=-55.46),
    SurfaceRow(surface="Standard", name="Flint back", thickness=114.0, diameter=30.0, glass="AIR", rc=-300.0),
)

# Triplet, three thick glasses -> three visible bodies (no false suppression).
TRIPLET = _lens_rows(
    SurfaceRow(surface="Standard", name="T1", thickness=6.0, diameter=30.0, glass="N-BK7", rc=60.0),
    SurfaceRow(surface="Standard", name="T2", thickness=6.0, diameter=30.0, glass="N-SF2", rc=-200.0),
    SurfaceRow(surface="Standard", name="T3", thickness=5.0, diameter=30.0, glass="F2", rc=200.0),
    SurfaceRow(surface="Standard", name="T back", thickness=110.0, diameter=30.0, glass="AIR", rc=-60.0),
)


def _render_doublet_png(path: Path) -> bool:
    """Render the doublet's VISIBLE bodies off-screen so the 2-element result
    can be eyeballed. Returns True if a non-blank PNG was written."""
    pv = layout_editor_module.pv
    specs = surface_rows_to_specs(DOUBLET_WITH_CEMENT)
    system = layout_editor_module._build_system_from_specs(specs, build=1)
    editor = _snapshot_editor(DOUBLET_WITH_CEMENT, {})
    items = editor._iter_3d_side_body_meshes(system, include_reference_surfaces=False)
    plotter = pv.Plotter(off_screen=True, window_size=(900, 500))
    plotter.set_background("white")
    drew = False
    for item in items:
        if float(item.opacity) < _VISIBLE_OPACITY:
            continue  # the suppressed cement bond is not drawn -- exactly the fix
        plotter.add_mesh(item.mesh, color=item.color, opacity=float(item.opacity))
        drew = True
    if not drew:
        return False
    plotter.view_vector((0.0, 1.0, 0.0), viewup=(0.0, 0.0, 1.0))
    plotter.screenshot(str(path))
    plotter.close()
    try:
        import numpy as np
        from PIL import Image

        arr = np.asarray(Image.open(path).convert("RGB"), dtype=float)
        non_white = float(np.mean(np.any(arr < 250.0, axis=2)))
        return non_white > 0.005
    except Exception:
        return path.exists() and path.stat().st_size > 0


def run_checks() -> tuple[bool, list[str]]:
    """Return ``(passed, notes)``; notes are prefixed FAIL/SKIP/PASS so the
    comprehensive harness (Phase 51) can surface them."""
    layout_editor_module._load_3d_backends()
    if layout_editor_module.pv is None:
        return True, ["SKIP: PyVista/VTK unavailable -- cannot build 3D bodies"]

    notes: list[str] = []
    failures: list[str] = []

    # (A) The flagged doublet: exactly the cement (thinnest) body is invisible;
    #     the crown and flint stay visible -> reads as two cemented elements.
    doublet = _visible_bodies(DOUBLET_WITH_CEMENT)
    visible = [b for b in doublet if b[1] >= _VISIBLE_OPACITY]
    hidden = [b for b in doublet if b[1] < _VISIBLE_OPACITY]
    notes.append(f"doublet bodies (idx, opacity, name, thickness): {doublet}")
    if len(doublet) != 3:
        failures.append(f"doublet: expected 3 BBB bodies (crown+cement+flint), got {len(doublet)}")
    if len(visible) != 2:
        failures.append(
            f"doublet: expected 2 VISIBLE bodies (crown+flint), got {len(visible)}: {visible} "
            "-- the cement bond is being drawn as a standalone slab (bugs/0046 regression)"
        )
    if len(hidden) != 1 or (hidden and hidden[0][3] >= _CEMENT_LAYER_MAX_AXIAL_THICKNESS_MM):
        failures.append(
            f"doublet: expected exactly the sub-{_CEMENT_LAYER_MAX_AXIAL_THICKNESS_MM}mm cement "
            f"layer hidden, got hidden={hidden}"
        )

    # (B) A clean singlet: one body, fully visible (nothing suppressed).
    singlet = _visible_bodies(SINGLET)
    if len([b for b in singlet if b[1] >= _VISIBLE_OPACITY]) != 1:
        failures.append(f"singlet: expected 1 visible body, got {singlet}")

    # (C) A real cemented doublet (no modelled bond): two visible bodies.
    real_doublet = _visible_bodies(DOUBLET_NO_BOND_LAYER)
    if len([b for b in real_doublet if b[1] >= _VISIBLE_OPACITY]) != 2:
        failures.append(
            f"real cemented doublet: expected 2 visible bodies, got {real_doublet} "
            "-- the fix wrongly hid a real element"
        )

    # (D) A thick triplet: three visible bodies (no false suppression).
    triplet = _visible_bodies(TRIPLET)
    if len([b for b in triplet if b[1] >= _VISIBLE_OPACITY]) != 3:
        failures.append(f"triplet: expected 3 visible bodies, got {triplet}")

    # (E) Visual proof: the doublet renders to a non-blank PNG of two elements.
    png = Path(__file__).resolve().parents[2] / "attachment" / "cemented_doublet_3d_bodies.png"
    png.parent.mkdir(parents=True, exist_ok=True)
    try:
        if not _render_doublet_png(png):
            failures.append(f"doublet render: PNG blank or unwritten at {png}")
        else:
            notes.append(f"rendered visible-body proof: {png}")
    except Exception as exc:  # a render crash is a real failure, not a skip
        failures.append(f"doublet render raised: {exc}")

    notes.extend(f"FAIL: {failure}" for failure in failures)
    if not failures:
        notes.append("PASS: cemented doublet reads as two elements in 3D; controls keep all real bodies")
    return (not failures), notes


def main() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    if not passed:
        fails = sum(1 for n in notes if n.startswith("FAIL"))
        print(f"[FAIL] {fails} cemented-doublet body check(s) failed (bugs/0046)")
        return 1
    print("[PASS] cemented-doublet body checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
