import KrakenOS as Kos


def _fmt(value):
    try:
        return f"{float(value):12.6g}"
    except Exception:
        return f"{value!s:>12}"


def build_system():
    obj = Kos.surf()
    obj.Name = "Input plane"
    obj.Thickness = 80.0
    obj.Diameter = 20.0
    obj.Glass = "AIR"

    lens = Kos.surf()
    lens.Name = "Focusing lens f=100"
    lens.Thin_Lens = 100.0
    lens.Thickness = 130.0
    lens.Diameter = 30.0
    lens.Glass = "AIR"

    image = Kos.surf()
    image.Name = "Readout plane"
    image.Thickness = 0.0
    image.Diameter = 16.0
    image.Glass = "AIR"

    return Kos.system([obj, lens, image], Kos.Setup())


def main():
    system = build_system()
    paraxial_trace = system.ParaxMatrices(0.6328)
    beam = Kos.GaussianBeamInput(
        wavelength_um=0.6328,
        waist_radius_mm=0.5,
        waist_offset_mm=0.0,
        m2=1.0,
    )
    beam_trace = Kos.propagate_gaussian_beam(paraxial_trace, beam)

    print("Gaussian q-parameter propagation")
    print("step  surface  kind           Re(q)        Im(q)         w          Rwf   waist_offset")
    for step in beam_trace.steps:
        print(
            f"{step.step_index:4d}"
            f"{step.surface_index:9d}"
            f"  {step.kind[:11]:11s}"
            f"{_fmt(step.q_real_mm)}"
            f"{_fmt(step.q_imag_mm)}"
            f"{_fmt(step.beam_radius_mm)}"
            f"{_fmt(step.wavefront_radius_mm)}"
            f"{_fmt(step.waist_offset_mm)}"
        )


if __name__ == "__main__":
    main()
