TITLE = "Diffuse Object pySCATMECH Microroughness"

SETTINGS = {
    "object_mode": "Finite",
    "display_orientation": "Vertical",
    "wavelength": "0.532",
    "ray_count": "1",
    "ray_height_factor": "0.8",
    "source_model": "Collimated disk source",
    "source_radius": "0.0",
    "source_power": "1.0",
    "source_x": "0.0",
    "source_y": "0.0",
    "source_z": "0.0",
    "source_l": "0.0",
    "source_m": "0.4",
    "source_n": "0.916515138991168",
    "field_type": "Object Height",
    "field_value": "0.0",
    "field_count": "1",
    "aperture_type": "EPD",
    "aperture_value": "20.0",
    "trace_mode": "Non-Sequential Preview",
    "nonseq_target_surface": "Auto",
    "nonseq_ns_limit": "80",
    "analysis_branch_filter": "All paths",
    "ray_display_mode": "All rays",
    "show_path_labels": False,
    "show_clipped_rays": True,
}

PYSCATMECH_SCATTER = {
    "model": "pySCATMECH BRDF",
    "backend": "pySCATMECH",
    "backend_model": "Microroughness_BRDF_Model",
    "backend_parameters": {
        "substrate": "(1.56,0.0)",
        "type": 0,
        "psd": {
            "__model__": "Gaussian_PSD_Function",
            "sigma": 0.05,
            "length": 1.0,
        },
    },
    "reflectance": 0.6,
    "sample_count": 13,
    "max_scatter_angle_deg": 80.0,
    "min_branch_power": 1e-5,
    "max_branch_depth": 1,
    "polarization": "Preserve projected Jones",
}

SURFACES = [
    {
        "surface": "Object",
        "name": "Reference object/source plane",
        "rc": 0.0,
        "thickness": 40.0,
        "diameter": 20.0,
        "glass": "AIR",
    },
    {
        "surface": "Diffuse Object",
        "name": "pySCATMECH rough object",
        "rc": 0.0,
        "thickness": 40.0,
        "diameter": 42.0,
        "glass": "MIRROR",
        "axis_move": 2.0,
        "advanced": {
            "DiffuseScatter": PYSCATMECH_SCATTER,
            "Display2D": {"label": "pySCATMECH object"},
            "Note": (
                "Optional pySCATMECH BRDF target. When the SCATPY extension is installed, "
                "Microroughness_BRDF_Model weights the deterministic scatter branches. "
                "Otherwise the trace falls back to the built-in Lambertian direction set."
            ),
        },
    },
    {
        "surface": "Image",
        "name": "Reference image plane",
        "rc": 0.0,
        "thickness": 0.0,
        "diameter": 60.0,
        "glass": "AIR",
    },
]
