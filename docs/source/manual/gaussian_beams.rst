Gaussian Beam Propagation
=========================

KrakenOS now exposes a lightweight Gaussian beam propagation path on top of the
same paraxial matrices used by ``system.ParaxMatrices()`` and
``Actions -> Paraxial Matrix Report``. It is intended for first-order laser
layout work: waist size, beam radius, divergence, Rayleigh range, wavefront
radius, Gouy phase, and CSV export at every paraxial step.

The implementation uses the conventional complex beam parameter:

.. math::

   q_{out} = \frac{A q_{in} + B}{C q_{in} + D}

where ``A``, ``B``, ``C``, and ``D`` are the step matrix values in the
``(height, angle)`` convention. KrakenOS refraction matrices include refractive
index transitions, so a flat air-to-glass interface scales the Rayleigh range
correctly.

Input conventions
-----------------

All distances are in millimeters. Wavelength is in micrometers, matching the
rest of KrakenOS.

``waist_radius_mm``
   The 1/e^2 Gaussian field radius at the input waist.

``waist_offset_mm``
   The signed real part of the input ``q`` parameter. A value of ``0`` means
   the waist is located exactly at the first paraxial input plane. A positive
   value means the input plane is downstream of the waist. A negative value
   means the waist is downstream of the input plane.

``m2``
   Beam quality factor. ``m2=1`` is diffraction-limited. Larger values increase
   the effective wavelength used by the q-parameter report.

Report columns
--------------

``Re(q)`` and ``Im(q)``
   Complex beam parameter after the paraxial step. ``Im(q)`` is the local
   Rayleigh range in the current medium.

``w`` and ``2w``
   Gaussian beam radius and diameter at the current step.

``Rwf``
   Wavefront radius. ``inf`` means a flat wavefront at the waist.

``w0``
   Waist radius implied by the current ``q`` state in the current medium.

``Waist offset``
   Distance from the current step plane to the waist. Positive values mean the
   waist is still downstream of the current step.

``Div``
   Far-field half-angle divergence in milliradians.

``Gouy``
   Gouy phase in radians for the current ``q`` state.

UI workflow
-----------

1. Load ``Common Optical Layout -> Gaussian Beam ABCD Example``.
2. In the Source panel, choose ``Gaussian beam``.
3. Set ``GB waist [mm]``, ``GB waist offset [mm]``, and ``GB M2``.
4. Click ``Update`` to trace representative Gaussian source rays and draw the
   amber 1/e^2 q-envelope in the 2-D layout.
5. Open ``Actions -> Gaussian Beam Report`` for the per-surface q table.
6. Use ``Export CSV`` when you want to compare the per-step q trace externally.

Python example
--------------

The same feature is available directly from Python:

.. code-block:: python

   import KrakenOS as Kos

   setup = Kos.Setup()

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

   system = Kos.system([obj, lens, image], setup)
   paraxial_trace = system.ParaxMatrices(0.6328)

   beam = Kos.GaussianBeamInput(
       wavelength_um=0.6328,
       waist_radius_mm=0.5,
       waist_offset_mm=0.0,
       m2=1.0,
   )
   beam_trace = Kos.propagate_gaussian_beam(paraxial_trace, beam)

   for step in beam_trace.steps:
       print(
           step.step_index,
           step.label,
           f"w={step.beam_radius_mm:.6g} mm",
           f"R={step.wavefront_radius_mm:.6g} mm",
           f"waist_offset={step.waist_offset_mm:.6g} mm",
       )

A runnable version of this example is available at
``KrakenOS/Examples/Examp_Gaussian_Beam_Propagation.py``.

Scope and limitations
---------------------

This is a paraxial q-parameter tool, not a full diffraction field propagator. It
does not yet model clipping, higher-order modes, coherent recombination after
beam splitters, or astigmatic tangential/sagittal separation. Those belong to
the next laser-propagation tiers after the single-pass q trace is stable.

The 2-D layout also traces a small representative meridional ray bundle so the
source appears in the normal ray display. The amber envelope is the physical
Gaussian beam size; the traced rays are only a visual/geometric guide.
