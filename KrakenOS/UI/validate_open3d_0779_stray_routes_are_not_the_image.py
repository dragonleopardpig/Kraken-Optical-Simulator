"""Guard for bugs/0779 -- stray light that reached the sensor by another optical route is not the image.

The user: *"have you looked into the sudden appear of stray rays issue?"* -- after flag
`20260910_172158_555` ("device 21x21x1mm, start to have hay wired rays ... why the symmetry not
hold?") and flag `20260911_084908_485` ("many stray lights showing up").

Measured on om05a_folded_80mm. From device 23 to device 21 the SAME 9 launch rays per arm -- all
stopped at the aperture stop at 23 -- clear the centre RA mirror's edge at 21, cross the prism gap
into the other arm's beam-splitter cube, bounce off that arm's first RA mirror and come back down
their own arm to the sensor, landing 1.4 mm outside the strip. They share their field's launch
point, so the focus measurement put them in that field's group, and ONE of them dragged a 105-ray
field's least-squares waist from 2.06 um to 656 um:

    device 21, edge field      with stray rays 656 um, 5.99 mm off   without 2.06 um, 0.019 mm
    device 21, centre field    with stray rays 419 um, 3.04 mm off   without 0.51 um, 0.095 mm
    device 15 FOV 24, centre   with stray rays 413 um, 2.63 mm off   without 0.40 um, 0.083 mm
    device 23 (no stray rays)  0.42 um either way

So the "419 um blur" at device 21, and the FOV limit it implied for small devices, were stray
light inside the field groups, not optics. The route a ray took is the physical identity of an
image: a route carrying a real share of a source's light is an image, a sliver is stray.

Checks (display-free; the REAL LayoutTableWorkbenchMixin._measure_focused_image_plane is driven by
a stub on synthetic rays -- no application, no trace):
  A  the pure helpers: landing_route, split_stray_routes, discrete_launch_sources;
  B  a sharp mirror-image split field plus stray rays from the SAME launch points on another route:
     the stray rays change nothing -- waist, plane, offset, footprint -- and are reported; without
     route data the SAME rays drag the waist, which is what gives B its teeth;
  C  an additive random emitter traced alongside does not flip the arms' grouping (decided per
     source -- the pooled rule would have);
  D  the older 'target_termination' spelling measures the same;
  E  a stray ray landing past the sensor edge is not the FIELD overflowing;
  F  the drawn strip is measured from the image, not widened by a stray record;
  G  the banner names stray light only when it lands outside the image, with its own share;
  H  the focus snap's own traced measure (ParaxialToolsMixin._traced_bundle_best_focus_shift) is
     unchanged by stray rays, and moves without route data -- on the saved om05a device-21 trace it
     read 3.0251 mm with them and 0.0945 mm without, the solve's "residual +3.025" warning.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0779_stray_routes_are_not_the_image
"""

from __future__ import annotations

import math
import types

import numpy as np

# ---- synthetic split field, shared with the bugs/0778 guard -----------------------------------
RAYS_PER_FIELD = 361        # a 19 x 19 pupil grid
FIELD_COUNT = 7             # 3 fields + 4 corner probes; scene_builder clamps field_index at 6
ZC_A = -16.25               # arm A band centre; arm B is its mirror image about z = -25
DELTA = 0.6                 # every field focuses 0.6 mm behind the sensor plane x = 100
DET_C = np.array([100.0, 0.0, -25.0])
DET_N = np.array([1.0, 0.0, 0.0])
ROUTE = (1.0, 3.0, 25.0)
GHOST_ROUTE = (1.0, 3.0, 18.0, 17.0, 1.0, 3.0, 25.0)
BANDS = [
    {"name": "Face A field", "center": [0.0, 0.0, ZC_A], "axis": [0.0, 0.0, 1.0]},
    {"name": "Face B field", "center": [0.0, 0.0, -50.0 - ZC_A], "axis": [0.0, 0.0, 1.0]},
]
_FIELDS = [(0.0, ZC_A - 3.0), (0.0, ZC_A), (0.0, ZC_A + 3.0)]
_PROBES = [(-2.0, ZC_A - 3.0), (2.0, ZC_A - 3.0), (-2.0, ZC_A + 3.0), (2.0, ZC_A + 3.0)]
_PUPIL_Z = -19.0


def _image_point(ly, lz):
    return np.array([100.0 + DELTA, -0.5 * ly, -21.0 - 0.5 * (lz - ZC_A)])


def _polyline(launch, pupil, aim):
    s = (100.0 - pupil[0]) / (aim[0] - pupil[0])
    return np.array([launch, pupil, pupil + (aim - pupil) * s])


def _mirror(point):
    q = np.array(point, dtype=float)
    q[2] = -50.0 - q[2]
    return q


def arm_a_rays(*, tail: int = 0, tail_error: float = 1.7):
    """``(launch, pupil, aim)`` for arm A: three 361-ray fields and four 5-ray corner probes -- the
    RAGGED launch om05a traces. ``tail`` pupil-edge rays per field miss the image point by
    ``tail_error`` mm: aberration blur on the SAME route."""
    grid = np.linspace(-4.5, 4.5, 19)
    rays = []
    for ly, lz in _FIELDS:
        img = _image_point(ly, lz)
        k = 0
        for v in grid:
            for u in grid:
                eps = np.zeros(3)
                if tail and k >= RAYS_PER_FIELD - tail:
                    th = 2.0 * math.pi * (k - (RAYS_PER_FIELD - tail)) / tail
                    eps = np.array([0.0, tail_error * math.cos(th), tail_error * math.sin(th)])
                rays.append((np.array([0.0, ly, lz]), np.array([50.0, u, _PUPIL_Z + v]), img + eps))
                k += 1
    for ly, lz in _PROBES:
        img = _image_point(ly, lz)
        for u, v in [(0, 0), (4.5, 0), (-4.5, 0), (0, 4.5), (0, -4.5)]:
            rays.append((np.array([0.0, ly, lz]), np.array([50.0, u, _PUPIL_Z + v]), img))
    return rays


def arm_a_ghosts(*, land_y: float = 2.5):
    """Stray rays from arm A's OWN field launch points: 1 from each edge field and 2 from the centre
    field -- om05a's device-21 census -- aimed to land beside the strip at ``land_y``."""
    out = []
    for (ly, lz), count in zip(_FIELDS, (1, 2, 1)):
        img = _image_point(ly, lz)
        for j in range(count):
            aim = np.array([100.0 + DELTA, land_y + 0.1 * j, img[2]])
            out.append((np.array([0.0, ly, lz]), np.array([50.0, 3.0 * (j + 1), _PUPIL_Z]), aim))
    return out


def split_field_paths(*, tail: int = 0, ghosts: bool = False, ghost_land_y: float = 2.5,
                      routes: bool = True, term: str = "image", source: str = "source:split"):
    """Ray paths for the mirror-image two-arm split field, as the scene bundle carries them.
    ``field_index`` is scene_builder's uniform fallback (``index // rays_per_field``, clamped),
    which slides out of step over the ragged launch -- the bugs/0778 mis-cut."""
    a = arm_a_rays(tail=tail)
    rays = a + [tuple(_mirror(p) for p in r) for r in a]
    route = [ROUTE] * len(rays)
    if ghosts:
        g = arm_a_ghosts(land_y=ghost_land_y)
        rays += g + [tuple(_mirror(p) for p in r) for r in g]
        route += [GHOST_ROUTE] * (2 * len(g))
    return [
        types.SimpleNamespace(
            points_world=_polyline(*ray),
            termination_reason=term,
            source_id=source,
            field_index=min(index // RAYS_PER_FIELD, FIELD_COUNT - 1),
            surface_ids=np.asarray(rt if routes else ROUTE, dtype=float),
        )
        for index, (ray, rt) in enumerate(zip(rays, route))
    ]


def make_probe(bands=BANDS):
    """A stand-in editor carrying only what _measure_focused_image_plane reads."""
    import KrakenOS.UI.services.layout_table_workbench as ltw

    # layout_editor injects np into this module at runtime (_sync_layout_globals); without it the
    # method's first np call is swallowed and it silently returns None
    ltw.__dict__.setdefault("np", np)

    class Probe(ltw.LayoutTableWorkbenchMixin):
        def __init__(self):
            self.layout_object_fov_bands = [dict(b) for b in bands] if bands else bands
            self.inspection_part_spec = {}
            self.debug = []

        def append_debug(self, message):
            self.debug.append(str(message))

        def _current_camera_sensor_active_mm(self):
            return (23.04, 23.04)

    return Probe()


def detector_bundle(paths):
    target = types.SimpleNamespace(
        is_detector=True, metadata={"focus_source": "reached_image"},
        center_world=DET_C.copy(), normal_world=DET_N.copy(),
    )
    return types.SimpleNamespace(targets=[target], ray_paths=list(paths))


def measure(paths, bands=BANDS):
    probe = make_probe(bands)
    return probe, probe._measure_focused_image_plane(detector_bundle(paths))


def per_arm(info) -> dict:
    if not isinstance(info, dict):
        return {}
    return {str(entry.get("name", "")): entry for entry in (info.get("images") or [info])}


def strip_records(paths):
    """The trace's ray-analysis records for measure_split_field_image_strips: first hit at the
    pupil (it decides the band), then the route, then the landing on surface 25."""
    records = []
    for path in paths:
        pts = path.points_world
        route = [int(s) for s in path.surface_ids]
        pupil = {"x": float(pts[1][0]), "y": float(pts[1][1]), "z": float(pts[1][2])}
        hits = [dict(pupil, surface=route[0])] + [dict(pupil, surface=s) for s in route[1:-1]]
        hits.append({"surface": route[-1], "x": float(pts[-1][0]), "y": float(pts[-1][1]), "z": float(pts[-1][2])})
        records.append({"reaches_image": True, "hits": hits})
    return records


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.detector_coverage_overlay import (
        discrete_launch_sources,
        format_focus_summary_lines,
        landing_route,
        measure_split_field_image_strips,
        split_stray_routes,
    )

    # ---- A: the pure helpers --------------------------------------------------------------------
    ok(landing_route(types.SimpleNamespace(surface_ids=np.array([1.0, 3.0, 25.0]))) == (1, 3, 25),
       "A1: a path's route is its ordered surface_ids")
    ok(landing_route({"surface_ids": [4, 5]}) == (4, 5), "A2: a record dict's surface_ids too")
    ok(landing_route(types.SimpleNamespace(surface_ids=np.empty(0), hits=[
        types.SimpleNamespace(surface_id=7), types.SimpleNamespace(surface_id=25)])) == (7, 25),
       "A3: without surface_ids the route comes from the hits")
    ok(landing_route({"hits": [{"surface": 2}, {"surface_id": 25}]}) == (2, 25),
       "A4: record hits spell the id either way")
    ok(landing_route(types.SimpleNamespace()) == (), "A5: no route data -> an empty route, never a crash")

    items = ([("a", "R")] * 322 + [("a", "G")] * 4 + [("b", "R")] * 60 + [("b", "S")] * 40
             + [("c", f"r{k}") for k in range(10)] + [("d", "R"), ("d", "R"), ("d", "G")])
    kept, stray = split_stray_routes(items, group_of=lambda it: it[0], route_of=lambda it: it[1])
    ok([it for it in stray if it[0] == "a"] == [("a", "G")] * 4,
       "A6: 4 rays on another route among 326 (1.2%, the device-21 census) are stray")
    ok(not any(it[0] == "b" for it in stray),
       "A7: a second route carrying 40% of its source is a second image and is kept")
    ok(not any(it[0] == "c" for it in stray),
       "A8: with no dominant route (ten routes at 10% each) nothing is called stray")
    ok(not any(it[0] == "d" for it in stray),
       "A9: a three-ray group cannot tell stray light from image -- everything kept")
    ok([it for it in kept if it[0] == "a"] == [("a", "R")] * 322, "A10: kept rays keep their order")

    def launches(n_rays, n_points, source="s"):
        points = [np.array([float(k), 0.0, 0.0]) for k in range(max(n_points, 1))]
        return [(source, points[i % max(n_points, 1)]) for i in range(n_rays)] if n_points else []

    for n_rays, n_points, want, why in (
        (1103, 7, True, "om05a: 1103 launch rays over 7 points"),
        (322, 7, True, "the same bundle after the aperture stop"),
        (400, 400, False, "a true random emitter: one launch per ray"),
        (400, 120, False, "mostly distinct launches, 3.3 per point"),
        (400, 100, True, "exactly 4 per point"),
        (0, 0, False, "nothing landed"),
    ):
        got = discrete_launch_sources(launches(n_rays, n_points), source_of=lambda it: it[0],
                                      launch_of=lambda it: it[1]).get("s", False)
        ok(got == want, f"A11[{why}]: {n_rays} rays / {n_points} launches -> discrete={got}")
    mixed = launches(2206, 14, "split") + launches(800, 800, "led")
    decided = discrete_launch_sources(mixed, source_of=lambda it: it[0], launch_of=lambda it: it[1])
    ok(decided == {"split": True, "led": False} and not (len(mixed) >= 4 * (14 + 800)),
       f"A12: decided PER SOURCE ({decided}) -- pooled, 3006 rays over 814 launches would have "
       f"called the imaging arms continuous too")

    # ---- B: stray rays change nothing, and are reported ------------------------------------------
    clean_paths = split_field_paths()
    ghost_paths = split_field_paths(ghosts=True)
    _, clean = measure(clean_paths)
    _, ghosted = measure(ghost_paths)
    _, blind = measure(split_field_paths(ghosts=True, routes=False))
    ca, ga, ba = per_arm(clean), per_arm(ghosted), per_arm(blind)
    ok(len(ca) == 2 and len(ga) == 2, f"B0: both arms are measured, with and without stray rays ({list(ga)})")
    for name in ("Face A field", "Face B field"):
        c, g, b = ca.get(name), ga.get(name), ba.get(name)
        if not (c and g and b):
            ok(False, f"B1[{name}]: an arm is missing from the measurement")
            continue
        ok(float(c["rms_waist_mm"]) < 1.0e-6,
           f"B1[{name}]: the synthetic arm is sharp ({1000 * float(c['rms_waist_mm']):.6f} um at its waist)")
        same = all(abs(float(g[k]) - float(c[k])) < 1.0e-9 for k in ("rms_waist_mm", "rms_plane_mm", "offset_mm"))
        ok(same, f"B2[{name}]: with stray rays in the bundle the waist, spot and offset are unchanged "
                 f"({1000 * float(g['rms_waist_mm']):.6f} um, {float(g['offset_mm']):+.6f} mm)")
        ok(all(abs(float(g[k]) - float(c[k])) < 1.0e-9 for k in ("half_along_u_mm", "half_along_v_mm")),
           f"B3[{name}]: and the drawn footprint is the image's, not widened by the stray landings")
        ok(float(b["rms_waist_mm"]) > 0.05,
           f"B4[{name}]: WITHOUT route data the same rays drag the waist to "
           f"{1000 * float(b['rms_waist_mm']):.1f} um -- the device-21 mechanism, so B2 has teeth")
    summary = ghosted.get("stray_light") if isinstance(ghosted, dict) else None
    ok(isinstance(summary, dict) and summary.get("rays") == 8 and summary.get("outside") == 8,
       f"B5: all 8 stray rays are counted and land outside the image ({summary})")
    ok(isinstance(summary, dict) and 1.0 < float(summary.get("worst_outside_mm", 0.0)) < 2.0,
       "B6: and the report says how far outside (about 1.5 mm here)")
    ok(isinstance(clean, dict) and "stray_light" not in clean, "B7: a bundle without stray light reports none")

    # ---- C: an additive random emitter does not flip the arms ------------------------------------
    rng = np.random.default_rng(779)
    led = []
    for _ in range(800):
        launch = np.array([rng.uniform(-3.0, 3.0), rng.uniform(-3.0, 3.0), rng.uniform(-40.0, -10.0)])
        pupil = np.array([50.0, rng.uniform(-4.5, 4.5), rng.uniform(-30.0, -20.0)])
        aim = np.array([100.0 + DELTA, rng.uniform(-3.0, 3.0), rng.uniform(-30.0, -20.0)])
        led.append(types.SimpleNamespace(
            points_world=_polyline(launch, pupil, aim), termination_reason="image", source_id="source:led",
            field_index=None, surface_ids=np.asarray((9.0, 25.0)),
        ))
    _, with_led = measure(clean_paths + led)
    la = per_arm(with_led)
    ok(len(la) == 2 and all(
        abs(float(la[n]["rms_waist_mm"]) - float(ca[n]["rms_waist_mm"])) < 1.0e-9
        and abs(float(la[n]["offset_mm"]) - float(ca[n]["offset_mm"])) < 1.0e-9
        for n in ("Face A field", "Face B field") if n in la and n in ca),
       "C1: 800 random-emitter landings traced alongside leave both arms' waist and offset unchanged -- "
       "the arms stay on launch-point grouping")

    # ---- D: the older termination spelling ----------------------------------------------------------
    _, legacy = measure(split_field_paths(ghosts=True, term="target_termination"))
    da = per_arm(legacy)
    ok(len(da) == 2 and all(
        abs(float(da[n]["rms_waist_mm"]) - float(ga[n]["rms_waist_mm"])) < 1.0e-9 for n in da if n in ga)
       and isinstance(legacy, dict) and (legacy.get("stray_light") or {}).get("rays") == 8,
       "D1: 'target_termination' landings are measured and split exactly like 'image' ones")

    # ---- E: a stray ray past the sensor edge is not the field overflowing ----------------------------
    far_paths = split_field_paths(ghosts=True, ghost_land_y=12.5)
    probe, far = measure(far_paths)
    over = (far or {}).get("sensor_overflow") or {}
    ok(over.get("outside") == 0 and over.get("landed") == 2206,
       f"E1: stray rays landing 12.5 mm out on an 11.52 mm half-sensor are not counted as overflow ({over})")
    raw = {}
    probe._annotate_sensor_overflow(raw, detector_bundle(far_paths), DET_C, DET_N)
    ok((raw.get("sensor_overflow") or {}).get("outside") == 8,
       "E2: measuring every landing ray instead WOULD count them -- so E1 has teeth")

    # ---- F: the drawn strip -----------------------------------------------------------------------
    widths = {}
    for label, paths in (("clean", clean_paths), ("stray", ghost_paths), ("blind", split_field_paths(ghosts=True, routes=False))):
        bands = [dict(b) for b in BANDS]
        measure_split_field_image_strips(bands, strip_records(paths), image_surface=25,
                                         image_point=DET_C, image_axis=DET_N)
        widths[label] = [float((b.get("image_strip") or {}).get("half_width", float("nan"))) for b in bands]
    ok(all(abs(s - c) < 1.0e-9 for s, c in zip(widths["stray"], widths["clean"])),
       f"F1: stray records do not widen the drawn strips (half-width {widths['stray']} vs {widths['clean']})")
    ok(all(b > c + 1.0 for b, c in zip(widths["blind"], widths["clean"])),
       f"F2: without route data they would ({widths['blind']}) -- F1 has teeth")

    # ---- G: the banner ------------------------------------------------------------------------------
    text = "\n".join(format_focus_summary_lines(ghosted, None, pixel_size_um=(4.5, 4.5)))
    ok("STRAY LIGHT: 8 ray(s)" in text and "outside the image" in text,
       "G1: the banner says how many stray rays land outside the image, and how far")
    ok("STRAY LIGHT" not in "\n".join(format_focus_summary_lines(clean, None, pixel_size_um=(4.5, 4.5))),
       "G2: and says nothing when there is none")
    inside_only = {"offset_mm": 0.0, "stray_light": {"rays": 8, "outside": 0, "share": 0.012, "worst_outside_mm": 0.0}}
    ok(not any("STRAY" in line for line in format_focus_summary_lines(inside_only, None)),
       "G3: off-route rays that land ON the image (a bookkeeping-only difference) are not called stray light")
    mixed_info = {"offset_mm": 0.0, "stray_light": {"rays": 16, "outside": 8, "share": 16 / 652, "worst_outside_mm": 1.74}}
    mixed_text = "\n".join(format_focus_summary_lines(mixed_info, None))
    ok("(1.2% of the landing rays)" in mixed_text,
       f"G4: the share printed is of the rays reported -- 8 of 652, not all 16 off-route ({mixed_text!r})")

    # ---- H: the focus snap's own traced measure ----------------------------------------------------
    # The solve's snap reads ParaxialToolsMixin._traced_bundle_best_focus_shift FIRST. On the saved
    # om05a device-21 trace it returned 3.0251 mm with the stray rays and 0.0945 mm without them --
    # the solve's "WARNING: the focus snap could not improve the defocus (residual +3.025 ...)".
    import KrakenOS.UI.services.paraxial_tools as paraxial

    paraxial.__dict__.setdefault("np", np)

    def snap_shift(paths):
        class SnapStub(paraxial.ParaxialToolsMixin):
            # the object sits at arm A's centre field launch, so the axial-field pick is that field
            rows = [types.SimpleNamespace(desp_x=0.0, desp_y=0.0, desp_z=ZC_A)]

            def _build_preview_system_rays_bundle(self, **_kwargs):
                return None, None, detector_bundle(paths)

            def _row_z_positions(self):
                return [0.0]

        return SnapStub()._traced_bundle_best_focus_shift()

    # Thin each field to every third ray -- om05a's centre field reaches the sensor with 108 image
    # rays and 2 stray ones after the aperture stop, not 361 -- so the stray share matches the
    # measured case. Every kept ray still converges on its field's image point.
    n_clean = len(clean_paths)
    blind_all = split_field_paths(ghosts=True, routes=False)

    def thin(paths):
        return [p for i, p in enumerate(paths[:n_clean]) if i % 3 == 0] + list(paths[n_clean:])

    clean_shift = snap_shift(thin(clean_paths))
    ghost_shift = snap_shift(thin(ghost_paths))
    blind_shift = snap_shift(thin(blind_all))
    ok(clean_shift is not None and abs(float(clean_shift) + DELTA) < 1.0e-3,
       f"H1: the snap measure finds the synthetic waist {DELTA} mm behind the sensor (got {clean_shift!r})")
    ok(clean_shift is not None and ghost_shift is not None and abs(float(ghost_shift) - float(clean_shift)) < 1.0e-9,
       f"H2: stray rays in the axial field leave the snap measure unchanged ({ghost_shift!r})")
    ok(clean_shift is not None and blind_shift is not None and abs(float(blind_shift) - float(clean_shift)) > 0.1,
       f"H3: without route data the same rays move it to {blind_shift!r} -- the device-21 +3.025 mm, so H2 has teeth")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0779 stray-routes-are-not-the-image validation PASSED")
        return 0
    print("0779 stray-routes-are-not-the-image validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
