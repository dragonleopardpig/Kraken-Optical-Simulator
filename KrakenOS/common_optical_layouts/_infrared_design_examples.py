"""Numerical prescriptions from William L. Wolfe, *Infrared Design Examples*.

The catalog covers every complete surface prescription in Appendix B (book
pages 145-157; attached-PDF pages 160-172), plus the three variants for which
the prose supplies an unambiguous numerical change.  Clear apertures are not
printed for most designs; the UI diameters used in those cases are explicitly
marked as display/trace proxies in ``SYSTEM_DATA`` and in each row's note.

The source is a scan.  The first radius of the fifty-degree cold lens is
``96.70241`` mm.  Its faint decimal point is missed by OCR, but that reading is
also confirmed by the printed 13.701141 mm final spacing and the paraxial focus
of the stated Ge/ZnSe prescription.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


SOURCE_BOOK = "William L. Wolfe, Infrared Design Examples, Appendix B"
SOURCE_PDF = "attachment/Infrared Design Examples.pdf"
DESIGN_WAVELENGTH_UM = 10.0


def r(
    name: str,
    radius: float | None,
    thickness: float,
    material: str = "AIR",
    *,
    diameter: float | None = None,
    stop: bool = False,
    k: float = 0.0,
    note: str = "",
) -> dict[str, Any]:
    """Return one source prescription row.

    ``material`` is the medium after a refractive surface, or ``MIRROR`` for a
    reflective surface.  ``stop=True`` represents either a standalone stop or
    a stop coincident with the printed optical surface.
    """

    return {
        "name": str(name),
        "radius": radius,
        "thickness": float(thickness),
        "material": str(material),
        "diameter": None if diameter is None else float(diameter),
        "stop": bool(stop),
        "k": float(k),
        "note": str(note),
    }


def d(
    design_id: int,
    section: str,
    title: str,
    pdf_page: int,
    book_page: int,
    rows: list[dict[str, Any]],
    *,
    field_deg: float,
    fno: float | None,
    stop_diameter: float,
    surface_diameter: float,
    image_diameter: float,
    image_radius: float = 0.0,
    wavelength_um: float = DESIGN_WAVELENGTH_UM,
    note: str = "",
    inferred_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": int(design_id),
        "section": str(section),
        "title": str(title),
        "pdf_page": int(pdf_page),
        "book_page": int(book_page),
        "rows": rows,
        "field_deg": float(field_deg),
        "fno": None if fno is None else float(fno),
        "stop_diameter": float(stop_diameter),
        "surface_diameter": float(surface_diameter),
        "image_diameter": float(image_diameter),
        "image_radius": float(image_radius),
        "wavelength_um": float(wavelength_um),
        "note": str(note),
        "inferred_values": dict(inferred_values or {}),
    }


PROXY_APERTURE_NOTE = (
    "The source does not print clear apertures for this prescription; KrakenOS "
    "uses documented proxy diameters so the layout can be displayed and traced."
)


DESIGNS: dict[int, dict[str, Any]] = {
    1: d(
        1,
        "B.2.1",
        "F/3 SEAL",
        160,
        145,
        [
            r("Mirror 1", 181.2, -147.8, "MIRROR", diameter=220.0),
            r("Mirror 2", 350.9, 147.8, "MIRROR", diameter=100.0, k=-0.404),
            r("Aperture stop", None, -147.8, stop=True, diameter=40.0),
            r("Mirror 3", 350.9, 119.0, "MIRROR", diameter=100.0, k=-0.404),
        ],
        field_deg=15.0,
        fno=3.0,
        stop_diameter=40.0,
        surface_diameter=100.0,
        image_diameter=70.0,
        note=PROXY_APERTURE_NOTE,
    ),
    2: d(
        2,
        "B.2.2",
        "F/3 Schwarzschild (flat image)",
        163,
        148,
        [
            r("Mirror 1", 30.62, -49.44, "MIRROR", diameter=28.0),
            r("Mirror 2", 80.0684, 80.26, "MIRROR", diameter=64.0),
            r("Aperture stop", None, 24.62, stop=True, diameter=10.0),
        ],
        field_deg=15.0,
        fno=3.0,
        stop_diameter=10.0,
        surface_diameter=64.0,
        image_diameter=30.0,
        note=PROXY_APERTURE_NOTE,
    ),
    3: d(
        3,
        "B.2.2",
        "F/3 Schwarzschild (R=-27 curved image)",
        163,
        148,
        [
            r("Mirror 1", 30.62, -49.44, "MIRROR", diameter=28.0),
            r("Mirror 2", 80.0684, 80.26, "MIRROR", diameter=64.0),
            r("Aperture stop", None, 24.62, stop=True, diameter=10.0),
        ],
        field_deg=15.0,
        fno=3.0,
        stop_diameter=10.0,
        surface_diameter=64.0,
        image_diameter=30.0,
        image_radius=-27.0,
        note=(
            "Variant explicitly stated in the prose: image-surface radius -27. "
            + PROXY_APERTURE_NOTE
        ),
    ),
    4: d(
        4,
        "B.2.3",
        "F/3 Reflective Schmidt (Lloyd)",
        163,
        148,
        [
            r(
                "Reflective corrector / stop",
                -66752.0,
                -67.37,
                "MIRROR",
                diameter=46.0,
                stop=True,
                k=0.508e-7,
            ),
            r("Plane mirror", None, 66.6, "MIRROR", diameter=46.0),
            r("Spherical mirror", -133.97, -66.85, "MIRROR", diameter=86.0),
        ],
        field_deg=15.0,
        fno=3.0,
        stop_diameter=46.0,
        surface_diameter=86.0,
        image_diameter=40.0,
        note=PROXY_APERTURE_NOTE,
    ),
    5: d(
        5,
        "B.2.3",
        "F/3 Reflective Schmidt (reoptimized corrector)",
        163,
        148,
        [
            r(
                "Reoptimized reflective corrector / stop",
                -9912.3925,
                -67.37,
                "MIRROR",
                diameter=46.0,
                stop=True,
                k=0.508e-7,
            ),
            r("Plane mirror", None, 66.6, "MIRROR", diameter=46.0),
            r("Spherical mirror", -133.97, -66.85, "MIRROR", diameter=86.0),
        ],
        field_deg=15.0,
        fno=3.0,
        stop_diameter=46.0,
        surface_diameter=86.0,
        image_diameter=40.0,
        note=(
            "Variant explicitly stated in the prose: the reflective corrector "
            "radius is changed from -66752 to -9912.3925. "
            + PROXY_APERTURE_NOTE
        ),
    ),
    6: d(
        6,
        "B.2.4",
        "F/3 Correctorless Schmidt (curved image)",
        164,
        149,
        [
            r("Aperture stop", None, 0.100, stop=True, diameter=10.0),
            r("Plane reference surface", None, 60.0, diameter=25.0),
            r("Spherical mirror", -60.0, -29.9302, "MIRROR", diameter=25.0),
        ],
        field_deg=15.0,
        fno=3.0,
        stop_diameter=10.0,
        surface_diameter=25.0,
        image_diameter=16.0,
        image_radius=-30.0022,
        note=PROXY_APERTURE_NOTE,
    ),
    7: d(
        7,
        "B.2.4",
        "F/3 Correctorless Schmidt (flat image)",
        164,
        149,
        [
            r("Aperture stop", None, 0.100, stop=True, diameter=10.0),
            r("Plane reference surface", None, 60.0, diameter=25.0),
            r("Spherical mirror", -60.0, -29.9302, "MIRROR", diameter=25.0),
        ],
        field_deg=15.0,
        fno=3.0,
        stop_diameter=10.0,
        surface_diameter=25.0,
        image_diameter=16.0,
        image_radius=0.0,
        note=(
            "Flat-image comparison explicitly discussed after the curved-image "
            "prescription. "
            + PROXY_APERTURE_NOTE
        ),
    ),
    8: d(
        8,
        "B.3.1",
        "ZnSe singlet F/3.21",
        165,
        150,
        [
            r("ZnSe front", 311.4638, 20.0, "ZNSE", diameter=114.3675),
            r("ZnSe back", 755.5295, 353.3419, diameter=114.3675),
        ],
        field_deg=15.0,
        fno=3.21,
        stop_diameter=114.3675,
        surface_diameter=114.3675,
        image_diameter=197.0,
        note=(
            "The source prints the two radii, 20 mm center thickness, and F/3.21, "
            "but not the image distance or clear diameter."
        ),
        inferred_values={
            "paraxial_efl_mm_at_10um": 367.1196,
            "paraxial_bfl_mm_at_10um": 353.3419,
            "entrance_pupil_diameter_mm_from_fno": 114.3675,
        },
    ),
    9: d(
        9,
        "B.3.2",
        "AMTIR-1 / ZnS doublet F/1.5",
        168,
        153,
        [
            r("AMTIR-1 front", 1.3874, 0.1724, "AMTIR1", diameter=1.0),
            r("AMTIR-1 back", 5.1990, 0.0327, diameter=1.0),
            r("ZnS front", -11.5083, 0.1, "ZNS_IR", diameter=1.0),
            r("ZnS back", 19.8665, 1.2960, diameter=1.0),
        ],
        field_deg=15.0,
        fno=1.5,
        stop_diameter=1.0,
        surface_diameter=1.0,
        image_diameter=1.0,
        note="The source explicitly states a 1 mm diameter and evaluates 8-12 um.",
    ),
    10: d(
        10,
        "B.3.2",
        "Ge / AMTIR-1 doublet F/1.5",
        168,
        153,
        [
            r("Ge front", 1.5184, 0.1340, "GERMANIUM", diameter=1.0),
            r("Ge back", 2.2313, 0.0532, diameter=1.0),
            r("AMTIR-1 front", -98.7706, 0.1, "AMTIR1", diameter=1.0),
            r("AMTIR-1 back", 31.8018, 1.2984, diameter=1.0),
        ],
        field_deg=15.0,
        fno=1.5,
        stop_diameter=1.0,
        surface_diameter=1.0,
        image_diameter=1.0,
        note="The source explicitly states a 1 mm diameter and evaluates 8-12 um.",
    ),
    11: d(
        11,
        "B.3.2",
        "Ge / ZnS doublet F/1.5",
        168,
        153,
        [
            r("Ge front", 1.6377, 0.1319, "GERMANIUM", diameter=1.0),
            r("Ge back", 2.4599, 0.1307, diameter=1.0),
            r("ZnS front", -1.4296, 0.1, "ZNS_IR", diameter=1.0),
            r("ZnS back", -1.4730, 1.2743, diameter=1.0),
        ],
        field_deg=15.0,
        fno=1.5,
        stop_diameter=1.0,
        surface_diameter=1.0,
        image_diameter=1.0,
        note="The source explicitly states a 1 mm diameter and evaluates 8-12 um.",
    ),
    12: d(
        12,
        "B.3.2",
        "Ge / ZnSe doublet F/1.5",
        168,
        153,
        [
            r("Ge front", 1.6572, 0.1319, "GERMANIUM", diameter=1.0),
            r("Ge back", 2.5151, 0.1380, diameter=1.0),
            r("ZnSe front", -1.3081, 0.1, "ZNSE", diameter=1.0),
            r("ZnSe back", -1.3562, 1.2793, diameter=1.0),
        ],
        field_deg=15.0,
        fno=1.5,
        stop_diameter=1.0,
        surface_diameter=1.0,
        image_diameter=1.0,
        note="The source explicitly states a 1 mm diameter and evaluates 8-12 um.",
    ),
    13: d(
        13,
        "B.3.3",
        "Ge / ZnSe meniscus triplet",
        170,
        155,
        [
            r("Ge front / stop", 18.3021, 0.9499, "GERMANIUM", stop=True),
            r("Ge back", 15.3831, 1.0000),
            r("ZnSe front", 19.9701, 1.0072, "ZNSE"),
            r("ZnSe back", 18.5201, 1.0000),
            r("Ge front", 17.6411, 1.1149, "GERMANIUM"),
            r("Ge back", 30.3345, 20.2265),
        ],
        field_deg=15.0,
        fno=None,
        stop_diameter=10.0,
        surface_diameter=20.0,
        image_diameter=12.0,
        note=(
            "The source prints no F-number or clear apertures for this triplet. "
            "A 10 mm entrance-pupil proxy is used."
        ),
        inferred_values={"paraxial_efl_mm_at_10um": 21.2094},
    ),
    14: d(
        14,
        "B.3.3",
        "Fischer-form Ge / ZnSe triplet",
        170,
        155,
        [
            r("Ge front / stop", -18.2818, 2.0, "GERMANIUM", stop=True),
            r("Ge back", -23.2325, 2.0),
            r("ZnSe front", 116.8642, 2.0, "ZNSE"),
            r("ZnSe back", 89.0374, 2.0),
            r("Ge front", -107.8522, 2.0, "GERMANIUM"),
            r("Ge back", -42.3473, 2.0),
        ],
        field_deg=15.0,
        fno=None,
        stop_diameter=10.0,
        surface_diameter=24.0,
        image_diameter=22.0,
        note=(
            "The source deliberately fixes every printed thickness/spacing to 2 "
            "and gives no F-number or clear apertures. A 10 mm entrance-pupil "
            "proxy is used; the printed final 2-unit image spacing is preserved."
        ),
        inferred_values={"paraxial_efl_mm_at_10um": 39.9991},
    ),
    15: d(
        15,
        "B.3.4",
        "F/1.5 fifty-degree cold helicopter lens",
        172,
        157,
        [
            r("Aperture stop", None, 30.395511, stop=True, diameter=26.6596),
            r("Ge front", 96.70241, 7.050114, "GERMANIUM", diameter=42.0),
            r("Ge back", 155.84290, 17.455786, diameter=42.0),
            r("ZnSe front", -57.92156, 4.0000000, "ZNSE", diameter=42.0),
            r("ZnSe back", -129.94860, 9.406118, diameter=42.0),
            r("ZnSe front", -68.64464, 9.000000, "ZNSE", diameter=42.0),
            r("ZnSe back", -54.34028, 10.230996, diameter=42.0),
            r("Ge front", 61.94634, 31.449508, "GERMANIUM", diameter=42.0),
            r("Ge back", 69.09355, 13.701141, diameter=42.0, k=0.743390),
        ],
        field_deg=25.0,
        fno=1.5,
        stop_diameter=26.6596,
        surface_diameter=42.0,
        image_diameter=38.0,
        note=(
            "The first lens radius is 96.70241 mm; the scan's faint decimal is "
            "confirmed by the prescription's paraxial focus. Surface clear "
            "diameters are UI proxies because the table omits them."
        ),
        inferred_values={
            "paraxial_efl_mm_at_10um": 39.9894,
            "entrance_pupil_diameter_mm_from_fno": 26.6596,
        },
    ),
}


OMITTED_SOURCE_DESIGNS = {
    "B.3.1 germanium singlet": "The printed radii and thickness are blank.",
    "B.3.3 silicon substitution": "Performance is stated, but no prescription is printed.",
    "B.3.3 separated Fischer triplet": "Improvement is stated, but no numerical separations are printed.",
    "B.3.3 contact Fischer triplet": "The contact alternative has no numerical prescription.",
}


def _row_note(design: dict[str, Any], row: dict[str, Any]) -> str:
    parts = [
        f"{SOURCE_BOOK}, Sec. {design['section']}, book p. {design['book_page']}, "
        f"attached PDF p. {design['pdf_page']}.",
        f"Printed row: {row['name']}.",
    ]
    if row.get("note"):
        parts.append(str(row["note"]))
    if row.get("diameter") is None:
        parts.append(
            f"Clear diameter {design['surface_diameter']:.12g} mm is a KrakenOS UI proxy."
        )
    return " ".join(parts)


def _surface_rows(design: dict[str, Any]) -> list[dict[str, Any]]:
    rows = list(design["rows"])
    max_diameter = max(
        [float(row["diameter"]) for row in rows if row.get("diameter") is not None]
        + [float(design["surface_diameter"]), float(design["stop_diameter"])]
    )
    result: list[dict[str, Any]] = [
        {
            "surface": "Object",
            "name": "Object at infinity",
            "rc": 0.0,
            "thickness": max(100.0, 2.0 * max_diameter),
            "diameter": max(25.0, max_diameter),
            "glass": "AIR",
            "advanced": {
                "Note": (
                    f"{SOURCE_BOOK}, Sec. {design['section']}; object at infinity. "
                    f"{design['note']}"
                )
            },
        }
    ]

    element_number = 0
    in_element = False
    for index, row in enumerate(rows, start=1):
        material = str(row["material"] or "AIR").strip()
        upper_material = material.upper()
        is_air = upper_material == "AIR"
        is_mirror = upper_material == "MIRROR"
        is_stop = bool(row.get("stop"))
        diameter = float(
            row["diameter"]
            if row.get("diameter") is not None
            else (design["stop_diameter"] if is_stop else design["surface_diameter"])
        )
        advanced = {"Note": _row_note(design, row)}

        # A Zemax stop can coincide with a powered or reflective surface.  The
        # editor represents the two roles as coincident rows so neither is lost.
        if is_stop and not is_air:
            result.append(
                {
                    "surface": "Aperture",
                    "element": "",
                    "name": f"S{index} Aperture stop (coincident)",
                    "rc": 0.0,
                    "thickness": 0.0,
                    "diameter": float(design["stop_diameter"]),
                    "glass": "AIR",
                    "advanced": deepcopy(advanced),
                }
            )
            is_stop = False

        if not is_air and not is_mirror and not in_element:
            element_number += 1
            in_element = True
        element = f"E{element_number}" if in_element and not is_mirror else ""
        if is_air and in_element:
            in_element = False
        elif is_mirror:
            in_element = False

        if is_stop:
            surface = "Aperture"
            name = f"S{index} Aperture stop"
            rc = 0.0
            glass = "AIR"
            element = ""
        elif is_mirror:
            surface = "Mirror"
            name = f"S{index} {row['name']}"
            rc = float(row["radius"] or 0.0)
            glass = "MIRROR"
            element = ""
        else:
            surface = "Standard"
            name = f"S{index} {row['name']}"
            rc = float(row["radius"] or 0.0)
            glass = material

        result.append(
            {
                "surface": surface,
                "element": element,
                "name": name,
                "rc": rc,
                "k": float(row.get("k", 0.0)),
                "thickness": float(row["thickness"]),
                "diameter": diameter,
                "glass": glass,
                "advanced": advanced,
            }
        )

    result.append(
        {
            "surface": "Image",
            "name": "Image" if not design["image_radius"] else "Curved image",
            "rc": float(design["image_radius"]),
            "thickness": 0.0,
            "diameter": float(design["image_diameter"]),
            "glass": "AIR",
            "advanced": {
                "Note": (
                    f"{SOURCE_BOOK}, Sec. {design['section']}; image radius "
                    f"{design['image_radius']:.12g} mm."
                )
            },
        }
    )
    return result


def load_design(design_id: int) -> tuple[str, list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    """Return ``TITLE, SURFACES, SETTINGS, SYSTEM_DATA`` for a wrapper module."""

    design = deepcopy(DESIGNS[int(design_id)])
    title = f"IDE {design['section']} — {design['title']}"
    aperture_type = "FNO" if design["fno"] is not None else "EPD"
    aperture_value = design["fno"] if design["fno"] is not None else design["stop_diameter"]
    settings = {
        "object_mode": "Infinity",
        # Appendix B prints ordered sequential prescriptions.  In particular,
        # its reflective systems use signed thicknesses to describe the folded
        # optical path; they are not non-sequential world-space assemblies.
        # Leaving this at Auto makes every Mirror row select NsTraceLoop, which
        # can encounter the mirrors out of prescription order and draw a ray
        # spray instead of the intended image-forming path.
        "trace_mode": "Sequential",
        "display_orientation": "YZ",
        "projection_display_mode": "Full 3D",
        "wavelength": f"{design['wavelength_um']:.12g}",
        "ray_count": "31",
        "ray_height_factor": "0.8",
        "analysis_surface": "Auto",
        "aperture_type": aperture_type,
        "aperture_value": f"{float(aperture_value):.12g}",
        "field_type": "Angle",
        "field_value": f"{design['field_deg']:.12g}",
        "field_count": "4",
        "spot_view_mode": "Grid",
        "image_diameter_mode": "Manual",
        "show_clipped_rays": True,
        "show_cardinals": False,
        "show_physical_distances": True,
        "analysis_mode": "none",
        "analysis_modes": [],
        "layout_preview_mode": "none",
        "auto_save_plot": False,
        "source_reference": SOURCE_BOOK,
        "source_section": design["section"],
        "source_pdf_pages": [design["pdf_page"], design["pdf_page"]],
        "layout_note": design["note"],
    }
    system_data = {
        "source": SOURCE_BOOK,
        "source_pdf": SOURCE_PDF,
        "section": design["section"],
        "book_page": design["book_page"],
        "pdf_pages": [design["pdf_page"], design["pdf_page"]],
        "wavelength_um": design["wavelength_um"],
        "f_number": design["fno"],
        "field_half_angle_deg": design["field_deg"],
        "source_rows": len(design["rows"]),
        "note": design["note"],
        "inferred_values": deepcopy(design["inferred_values"]),
    }
    return title, _surface_rows(design), settings, system_data
