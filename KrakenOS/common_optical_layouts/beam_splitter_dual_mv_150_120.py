"""Beam splitter with a DIFFERENT whole machine-vision lens on each arm.

A shared object feeds a 50 mm cube beam splitter; the TRANSMIT arm is the whole
Machine Vision 150 mm (1X) lens, the REFLECT arm is the whole Machine Vision 120 mm
lens (folded +Y). Because the two lenses have different EFL / object conjugates
(150 mm 1X: object->front 275 mm, field 16.5 mm; 120 mm 1X: object->front 215 mm,
field 11.52 mm) the two arms image the SAME object with overlapping but DIFFERENT
fields of view -- a test bed for per-branch quick estimation on overlapping FOVs and
for the per-branch source/pupil (DESIGN_nonseq_first_order_reference.md §5b).

Each arm's rows are tagged ``advanced.Element.branch_selector`` ('transmit'/'reflect')
so the per-leaf extraction (paraxial_tools._branch_leaf_rows) can pull each arm's path.
The reflect arm is folded onto the +Y path the same way as
``beam_splitter_two_arm_doublets`` (tilt_x=-90, desp_y = +Y arm distance,
desp_z = z_bs - z_sequential), here COMPUTED from the prescription so the spacings stay
exact. You can promote the real 50 mm cube (attachment/prisms/Beam_Splitter,
step_32704.step) over the splitter in-app instead of the analytic Beam Splitter surface.
"""

TITLE = "Beam Splitter: MV 150 mm 1X (transmit) + MV 120 mm (reflect)"

# --- geometry ---------------------------------------------------------------
OBJECT_TO_BS = 90.0            # object -> beam-splitter centre
Z_BS = OBJECT_TO_BS           # the splitter sits on this z plane (reflect arm folds here)
TX_OBJECT_TO_FRONT = 275.0    # MV 150 mm 1X object -> lens front datum
RX_OBJECT_TO_FRONT = 215.01   # MV 120 mm 1X object -> lens front vertex
BS_TO_TX_FRONT = TX_OBJECT_TO_FRONT - OBJECT_TO_BS   # transmit: BS -> 150 front (+Z)
BS_TO_RX_FRONT = RX_OBJECT_TO_FRONT - OBJECT_TO_BS   # reflect: BS -> 120 front (+Y)

BEAM_SPLITTER_SETTINGS = {
    "split_mode": "Deterministic paths",
    "reflectance": 0.5,
    "absorption": 0.0,
    "transmit_phase_deg": 0.0,
    "reflect_phase_deg": 180.0,
    "min_branch_power": 1e-3,
    "max_branch_depth": 8,
}


def _element(name, selector):
    return {"element_name": name, "branch_selector": selector}


# (surface, name, rc, thickness, diameter, glass) -- the lens INTERIOR (no Object/Image).
# MV 150 mm 1X blackbox (transmit arm), from machine_vision_150mm_datasheet_1x.
TRANSMIT_LENS = [
    ("Standard", "150 Front Datum", 0.0, 1.45390219, 35.0, "AIR"),
    ("Thin Lens", "150 Blackbox Group 1", 258.76640629, 24.405, 26.8, "AIR"),
    ("Aperture", "150 Aperture Stop", 0.0, 21.64217312, 19.35624, "AIR"),
    ("Thin Lens", "150 Blackbox Group 2", 293.32901330, 1.308924688, 26.8, "AIR"),
    ("Standard", "150 Rear Datum", 0.0, 272.0, 35.0, "AIR"),
    ("Standard", "150 Transmit Detector", 0.0, 0.0, 33.0, "AIR"),
]
# MV 120 mm 1X blackbox (reflect arm), from machine_vision_120mm_pyrite_datasheet_1x.
REFLECT_LENS = [
    ("Standard", "120 Front Vertex", 0.0, 17.760867505017475, 46.0, "AIR"),
    ("Thin Lens", "120 Blackbox Group 1", 153.30504283282798, 8.449132494982525, 38.0, "AIR"),
    ("Aperture", "120 Aperture Stop", 0.0, 23.5, 21.55, "AIR"),
    ("Thin Lens", "120 Blackbox Group 2", 448.8953720876923, 1.2, 38.0, "AIR"),
    ("Standard", "120 Rear Vertex", 0.0, 215.01, 46.0, "AIR"),
    ("Standard", "120 Reflect Detector", 0.0, 0.0, 45.0, "AIR"),
]


def _straight_arm(lens, selector):
    rows = []
    for surface, name, rc, thickness, diameter, glass in lens:
        rows.append({
            "surface": surface, "name": name, "rc": rc, "k": 0.0,
            "thickness": thickness, "diameter": diameter, "glass": glass,
            "advanced": {"Element": _element(name, selector)},
        })
    return rows


def _folded_arm(lens, selector, *, z_bs, arm_start, z_sequential_start):
    """Fold a straight lens onto the +Y arm at z_bs (beam_splitter_two_arm_doublets
    pattern, computed): tilt_x=-90, desp_y = +Y arm distance, desp_z = z_bs - z_seq."""
    rows = []
    arm_y = float(arm_start)
    z_seq = float(z_sequential_start)
    for surface, name, rc, thickness, diameter, glass in lens:
        rows.append({
            "surface": surface, "name": name, "rc": rc, "k": 0.0,
            "thickness": thickness, "diameter": diameter, "glass": glass,
            "tilt_x": -90.0, "tilt_y": 0.0, "tilt_z": 0.0,
            "desp_x": 0.0, "desp_y": round(arm_y, 6), "desp_z": round(z_bs - z_seq, 6),
            "axis_move": 0.0,
            "advanced": {"Element": _element(name, selector)},
        })
        arm_y += float(thickness)
        z_seq += float(thickness)
    return rows


def _build_surfaces():
    obj = {
        "surface": "Object", "name": "Shared Object", "rc": 0.0,
        "thickness": OBJECT_TO_BS, "diameter": 40.0, "glass": "AIR",
    }
    # The splitter is modelled as a thin 50/50 splitting plane (diameter shows the 50 mm
    # cube); its "thickness" is the air gap to the transmit lens. Glass is AIR so the
    # first-order reference is a clean centred system -- promote the real 50 mm BK7 cube
    # (attachment/prisms/Beam_Splitter/step_32704.step) over it in-app for the glass path.
    splitter = {
        "element": "Splitter", "surface": "Beam Splitter", "name": "50 mm cube splitter",
        "rc": 0.0, "k": 0.0, "thickness": BS_TO_TX_FRONT, "diameter": 50.0,
        "tilt_x": 45.0, "tilt_y": 0.0, "tilt_z": 0.0,
        "desp_x": 0.0, "desp_y": 0.0, "desp_z": 0.0, "axis_move": 0.0, "glass": "AIR",
        "advanced": {"BeamSplitter": BEAM_SPLITTER_SETTINGS, "Element": _element("50 mm cube splitter", "")},
    }
    transmit = _straight_arm(TRANSMIT_LENS, "transmit")
    z_seq_reflect_start = OBJECT_TO_BS + BS_TO_TX_FRONT + sum(r["thickness"] for r in transmit)
    reflect = _folded_arm(
        REFLECT_LENS, "reflect",
        z_bs=Z_BS, arm_start=BS_TO_RX_FRONT, z_sequential_start=z_seq_reflect_start,
    )
    global_image = {
        "surface": "Image", "name": "Global diagnostic image", "rc": 0.0,
        "thickness": 0.0, "diameter": 80.0, "glass": "AIR",
    }
    return [obj, splitter, *transmit, *reflect, global_image]


SURFACES = _build_surfaces()

SETTINGS = {
    "object_mode": "Finite",
    "display_orientation": "Vertical",
    "wavelength": "0.55",
    "ray_count": "5",
    "ray_height_factor": "0.85",
    "source_model": "Pupil / field",
    "pupil_pattern": "Meridional fan",
    "field_type": "Real Image Height",
    "field_value": "16.5",
    "field_count": "3",
    "aperture_type": "EPD",
    "aperture_value": "26.8",
    "trace_mode": "Non-Sequential Preview",
    "nonseq_target_surface": "Auto",
    "nonseq_ns_limit": "200",
    "nonseq_energy_probability": False,
    "analysis_modes": ["spot"],
}
