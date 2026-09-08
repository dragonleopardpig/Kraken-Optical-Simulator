"""Guard for bugs/0752 -- a split field forms TWO images; measure one focus plane per image.

User, on my claim that "at 30 mm the image forms ~7.5 mm off the sensor centre":

    "everything is symmetry, A and B sides, I can't figure out how to make an Image Plane
     off-centered."

They were right. Traced, the two device faces land at v = +5.3474 and -5.3474 mm on the shared
sensor, summing to -0.00000 mm -- the optics is exactly symmetric. The off-centre plane came from
pooling BOTH arms into one "beam centre", which on a split field lands in the dark ridge BETWEEN
the two strips (nearest ray 4.5059 mm away); the "axial" ray picked there was an edge ray of
whichever arm won an exact tie, decided by dict iteration order.

Checks (display-free, no Tk/VTK):
  A  the partition splits two fed bands, and collapses to ONE group without bands, with a single
     band, or when only one band actually receives rays (every non-split scene is untouched).
  B  each image anchors on its OWN light -- the axial ray lands inside that image, not in the gap
     -- and mirrored input produces mirrored planes.
  C  the overlay fans out one rectangle + connector per image, sized and named per image, with the
     connector starting at that image's landing centre rather than the sensor centre.
  D  the banner names every image's offset.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0752_one_focus_plane_per_image
"""

from __future__ import annotations

import inspect

import numpy as np


def _bundle(waist, spread, normal):
    """A cone of rays converging at ``waist`` and landing on the y=0 sensor plane."""
    ends, dirs, polys = [], [], []
    for a, b in spread:
        d = np.asarray([a, 1.0, b], dtype=float)
        d = d / float(np.linalg.norm(d))
        s = (0.0 - float(waist[1])) / float(d[1])
        end = np.asarray(waist, dtype=float) + s * d
        ends.append(end)
        dirs.append(d)
        polys.append(np.asarray([end - 120.0 * d, end], dtype=float))
    return (ends, dirs), polys


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services import detector_coverage_overlay as dco
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    centre = np.array([0.0, 0.0, 0.0])
    normal = np.array([0.0, -1.0, 0.0])
    iu, iv = dco._basis(normal)

    class Stub:
        layout_object_fov_bands = None

    stub = Stub()
    partitions = LayoutTableWorkbenchMixin._focus_image_partitions
    measure_one = LayoutTableWorkbenchMixin._measure_one_focus_image

    # ---- build two mirror-image bundles, one per arm ---------------------------------------------
    spread = [(0.03, 0.02), (-0.03, 0.02), (0.03, -0.02), (-0.03, -0.02), (0.0, 0.0), (0.015, 0.0)]
    waist_a = centre + 10.0 * normal + 5.0 * iv     # image A, 5 mm up the strip axis
    waist_b = centre + 10.0 * normal - 5.0 * iv     # image B, its mirror
    buckets, polylines, launches = {}, {}, {}
    for name, waist, face_z in (("A", waist_a, 0.0), ("B", waist_b, -50.0)):
        for field in range(2):
            key = (f"source:{name}", field)
            nudge = [(a + 0.004 * field, b) for a, b in spread]
            buckets[key], polylines[key] = _bundle(waist, nudge, normal)
            launches[key] = [np.array([0.0, 0.0, face_z])] * len(nudge)

    bands = [
        {"name": "Face A field", "center": [0.0, 0.0, 0.0], "axis": [0.0, 0.0, 1.0]},
        {"name": "Face B field", "center": [0.0, 0.0, -50.0], "axis": [0.0, 0.0, 1.0]},
    ]

    # ---- A: the partition ------------------------------------------------------------------------
    stub.layout_object_fov_bands = bands
    split = partitions(stub, buckets, launches)
    ok(
        len(split) == 2 and {n for n, _ in split} == {"Face A field", "Face B field"},
        f"A1: two fed bands split into two images ({[n for n, _ in split]})",
    )
    ok(
        all(len(keys) == 2 for _n, keys in split)
        and all(all(k[0].endswith(n.split()[1]) for k in keys) for n, keys in split),
        "A2: every bundle is filed under the band it launched from",
    )
    stub.layout_object_fov_bands = None
    ok(
        [n for n, _ in partitions(stub, buckets, launches)] == [""]
        and len(partitions(stub, buckets, launches)[0][1]) == len(buckets),
        "A3: WITHOUT bands it is one pooled group over every bucket -- non-split scenes unchanged",
    )
    stub.layout_object_fov_bands = bands[:1]
    ok(
        len(partitions(stub, buckets, launches)) == 1,
        "A4: a single band is also one group (two bands are needed before a scene can split)",
    )
    stub.layout_object_fov_bands = bands
    only_a = {k: v for k, v in launches.items() if k[0] == "source:A"}
    ok(
        len(partitions(stub, {k: buckets[k] for k in only_a}, only_a)) == 1,
        "A5: two bands but only ONE fed -> one group; an arm that lands nothing cannot split it",
    )

    # ---- B: each image is anchored on its own light ------------------------------------------------
    measured = []
    for name, keys in split:
        entry = measure_one(stub, keys, buckets, polylines, centre, normal, name=name)
        ok(isinstance(entry, dict), f"B1[{name}]: the image measures")
        if isinstance(entry, dict):
            measured.append(entry)
    ok(len(measured) == 2, f"B2: both images measured ({len(measured)})")
    if len(measured) == 2:
        gaps = [float(e.get("axial_ray_gap_mm", 9e9)) for e in measured]
        ok(
            max(gaps) < 1.0,
            f"B3: the axial ray of each image lands INSIDE that image (max gap {max(gaps):.4f} mm) -- "
            f"pooling both arms put it 4.5059 mm away, in the gap between the strips",
        )
        pooled_centre = np.concatenate(
            [np.asarray(b[0], dtype=float).reshape(-1, 3) for b in buckets.values()]
        ).mean(axis=0)
        pooled_gap = min(
            float(np.min(np.linalg.norm(np.asarray(b[0], dtype=float).reshape(-1, 3) - pooled_centre, axis=1)))
            for b in buckets.values()
        )
        ok(
            pooled_gap > 4.0 * max(max(gaps), 1e-6),
            f"B4: and that is the whole point -- the POOLED centre's nearest ray is {pooled_gap:.4f} mm "
            f"away, far outside the light",
        )
        vs = sorted(
            float((np.asarray(e["focus_center_world"], dtype=float).reshape(3) - centre) @ iv)
            for e in measured
        )
        us = [
            float((np.asarray(e["focus_center_world"], dtype=float).reshape(3) - centre) @ iu)
            for e in measured
        ]
        ok(
            abs(vs[0] + vs[1]) < 1.0e-6,
            f"B5: mirrored input gives mirrored planes: v {vs[0]:+.5f} and {vs[1]:+.5f}, "
            f"sum {vs[0] + vs[1]:+.2e} -- the symmetry the user pointed at",
        )
        ok(
            abs(vs[1] - 5.0) < 0.05 and abs(vs[0] + 5.0) < 0.05,
            f"B6: each plane sits on its OWN strip (+-5 mm), not collapsed onto the sensor centre "
            f"({vs[0]:+.4f}, {vs[1]:+.4f})",
        )
        ok(
            abs(us[0] - us[1]) < 1.0e-6,
            f"B7: and the two agree across the strip axis too ({us[0]:+.5f} vs {us[1]:+.5f}) -- the "
            f"arms mirror in v, so u must MATCH",
        )
        offsets = [float(e["offset_mm"]) for e in measured]
        ok(
            abs(offsets[0] - offsets[1]) < 1.0e-6,
            f"B8: the two arms report the same conjugate ({offsets[0]:.4f} vs {offsets[1]:.4f} mm) -- "
            f"the check that makes the symmetry visible instead of arguable",
        )

    # ---- C: the overlay draws one plane per image -------------------------------------------------
    info = dict(measured[0]) if measured else {}
    info["images"] = measured
    specs = dco.focused_image_plane_specs(centre, normal, info, 11.52, 11.52)
    kinds = [s["kind"] for s in specs]
    ok(
        kinds.count("focused_image_plane") == 2 and kinds.count("focus_defocus_gap") == 2,
        f"C1: two rectangles and two connectors are drawn, one per image ({kinds})",
    )
    rect_v = sorted(
        float((np.asarray(s["points"], dtype=float)[:4].mean(axis=0) - centre) @ iv)
        for s in specs
        if s["kind"] == "focused_image_plane"
    )
    ok(
        abs(rect_v[0] + rect_v[1]) < 1.0e-6 and abs(rect_v[1]) > 1.0,
        f"C2: the two drawn rectangles are mirror images on their own strips ({rect_v})",
    )
    starts = sorted(
        float((np.asarray(s["points"], dtype=float)[0] - centre) @ iv)
        for s in specs
        if s["kind"] == "focus_defocus_gap"
    )
    ok(
        abs(starts[0] + starts[1]) < 1.0e-6 and abs(starts[1]) > 1.0,
        f"C3: each connector starts at ITS image's landing centre, not the sensor centre ({starts}) "
        f"-- the sensor centre is the dark ridge no ray reaches",
    )
    single = dco.focused_image_plane_specs(centre, normal, measured[0] if measured else {}, 11.52, 11.52)
    ok(
        [s["kind"] for s in single].count("focused_image_plane") == 1,
        "C4: an info WITHOUT an images list still draws exactly one plane (single-image scenes)",
    )
    labels = dco.focused_image_plane_label_specs(centre, normal, info, 11.52)
    ok(
        len(labels) == 2
        and any("Face A field" in str(l["text"]) for l in labels)
        and any("Face B field" in str(l["text"]) for l in labels),
        f"C5: each plane is labelled with the field band it belongs to "
        f"({[str(l['text'])[:22] for l in labels]})",
    )
    widths = {
        round(float(np.linalg.norm(np.asarray(s["points"], dtype=float)[0] - np.asarray(s["points"], dtype=float)[1])), 6)
        for s in specs
        if s["kind"] == "focused_image_plane"
    }
    ok(
        all(w < 2.0 * 11.52 for w in widths),
        f"C6: each rectangle is sized to the light it lands, not the whole sensor ({sorted(widths)})",
    )

    # ---- D: the banner names every image -----------------------------------------------------------
    lines = dco.format_focus_summary_lines(info, None)
    ok(
        any("Face A field" in line for line in lines) and any("Face B field" in line for line in lines),
        f"D1: the banner names both images' offsets ({len(lines)} lines)",
    )
    ok(
        dco.format_focus_summary_lines(measured[0] if measured else {}, None)
        and not any("Face B field" in line for line in dco.format_focus_summary_lines(measured[0], None)),
        "D2: a single-image scene's banner is unchanged",
    )

    # ---- E: the production path routes through it ----------------------------------------------------
    entry_src = inspect.getsource(LayoutTableWorkbenchMixin._measure_focused_image_plane)
    ok(
        "self._focus_image_partitions(" in entry_src and "self._measure_one_focus_image(" in entry_src,
        "E1: the real measurement partitions into images and measures each one",
    )
    ok(
        'info["images"] = measured' in entry_src and "len(measured) > 1" in entry_src,
        "E2: and publishes the list only when a scene actually forms more than one image",
    )
    one_src = inspect.getsource(LayoutTableWorkbenchMixin._measure_one_focus_image)
    ok(
        "base = np.asarray(anchor" in one_src,
        "E3: the straight-leg rule projects onto THIS image's landing centre, not the sensor "
        "centre (which would collapse a split field back together)",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0752 one-focus-plane-per-image validation PASSED")
        return 0
    print("0752 one-focus-plane-per-image validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
