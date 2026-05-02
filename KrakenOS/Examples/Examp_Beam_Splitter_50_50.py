"""50/50 finite-plate beam splitter with deterministic child branches.

The front coated face has ``BeamSplitter`` metadata, ``Glass='BK7'``, and a
3 mm thickness to a following rear ``AIR`` face. Non-sequential tracing now
spawns both the transmitted branch through the plate and the reflected branch
from the coating interface.
"""

import numpy as np

import KrakenOS as Kos


BEAM_SPLITTER = {
    "split_mode": "Deterministic branches",
    "reflectance": 0.5,
    "absorption": 0.0,
    "transmit_phase_deg": 0.0,
    "reflect_phase_deg": 180.0,
    "min_branch_power": 1e-3,
    "max_branch_depth": 8,
}


def coating_from_splitter(settings):
    reflectance = min(max(float(settings["reflectance"]), 0.0), 1.0)
    absorption = min(max(float(settings["absorption"]), 0.0), 1.0 - reflectance)
    wavelengths = [0.45, 0.55, 0.65]
    angles = [0.0, 45.0, 70.0]
    r_table = [[reflectance for _wavelength in wavelengths] for _angle in angles]
    a_table = [[absorption for _wavelength in wavelengths] for _angle in angles]
    return [r_table, a_table, wavelengths, angles]


def build_system():
    setup = Kos.Setup()

    obj = Kos.surf()
    obj.Name = "Input reference"
    obj.Thickness = 45.0
    obj.Diameter = 30.0
    obj.Glass = "AIR"
    obj.AxisMove = 0.0

    splitter = Kos.surf()
    splitter.Name = "50/50 coated front face"
    splitter.Rc = 0.0
    splitter.Thickness = 3.0
    splitter.Diameter = 25.0
    splitter.TiltX = 45.0
    splitter.Glass = "BK7"
    splitter.AxisMove = 0.0
    splitter.BeamSplitter = dict(BEAM_SPLITTER)
    splitter.Coating = coating_from_splitter(splitter.BeamSplitter)

    rear = Kos.surf()
    rear.Name = "BK7 plate rear face"
    rear.Rc = 0.0
    rear.Thickness = 60.0
    rear.Diameter = 25.0
    rear.TiltX = 45.0
    rear.Glass = "AIR"
    rear.AxisMove = 0.0

    image = Kos.surf()
    image.Name = "Large diagnostic target"
    image.Thickness = 0.0
    image.Diameter = 100.0
    image.Glass = "AIR"
    image.AxisMove = 0.0

    system = Kos.system([obj, splitter, rear, image], setup)
    system.energy_probability = 0
    system.NsLimit = 120
    return system


def collimated_disk_bundle(radius=8.0, ray_count=7):
    """Exact-count collimated source bundle used by the UI source model.

    Points are placed inside the requested radius, not exactly on the edge, so
    marginal rays do not get clipped differently by sibling splitter branches.
    """
    count = max(1, int(ray_count))
    if count == 1 or radius <= 0:
        count = 1
        points = np.asarray([[0.0, 0.0]], dtype=float)
    else:
        golden_angle = np.pi * (3.0 - np.sqrt(5.0))
        points = [[0.0, 0.0]]
        for index in range(1, count):
            r = float(radius) * np.sqrt(index / float(count))
            theta = index * golden_angle
            points.append([r * np.cos(theta), r * np.sin(theta)])
        points = np.asarray(points, dtype=float)
    x = points[:, 0]
    y = points[:, 1]
    z = np.zeros(count)
    l = np.zeros(count)
    m = np.zeros(count)
    n = np.ones(count)
    metadata = [
        {
            "source_model": "Collimated disk source",
            "source_xyz": [float(x[i]), float(y[i]), float(z[i])],
            "source_lmn": [float(l[i]), float(m[i]), float(n[i])],
            "source_power": 1.0,
            "source_weight": 1.0 / float(count),
            "source_wavelength": 0.55,
        }
        for i in range(count)
    ]
    return x, y, z, l, m, n, metadata


def trace_demo():
    system = build_system()
    rays = Kos.raykeeper(system)
    wavelength = 0.55
    x, y, z, l, m, n, source_metadata = collimated_disk_bundle()
    Kos.NsTraceLoop(x, y, z, l, m, n, wavelength, rays, source_metadata=source_metadata)
    return rays


if __name__ == "__main__":
    traced_rays = trace_demo()
    for ray_index, surfaces in enumerate(traced_rays.SURFACE):
        surface_path = [int(value) for value in np.asarray(surfaces, dtype=int)]
        branch = int(np.asarray(traced_rays.BRANCH_ID[ray_index]).ravel()[0])
        parent = int(np.asarray(traced_rays.PARENT_BRANCH_ID[ray_index]).ravel()[0])
        label = str(np.asarray(traced_rays.BRANCH_LABEL[ray_index]).ravel()[0])
        power = float(np.asarray(traced_rays.BRANCH_POWER[ray_index]).ravel()[0])
        source = int(np.asarray(traced_rays.SOURCE_RAY[ray_index]).ravel()[0])
        source_weight = float(np.asarray(traced_rays.SOURCE_WEIGHT[ray_index]).ravel()[0])
        print(
            f"ray {ray_index:02d}: source={source} branch={branch} parent={parent} {label} "
            f"surfaces={surface_path} power={power:.6g} "
            f"source_weight={source_weight:.6g} TT={float(np.asarray(traced_rays.TT[ray_index]).ravel()[-1]):.6g}"
        )
