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

``Source X/Y/Z`` and ``Source L/M/N``
   The Gaussian source can be launched from a physical origin and chief-ray
   direction. ``Source L/M/N`` are normalized direction cosines. The traced
   representative rays follow that direction, so the source can be separated
   from the ``Object`` reference row for beam-splitter geometry. The amber
   q-envelope overlay is intentionally limited to centered ``+Z`` paraxial
   layouts; for tilted or folded Gaussian systems, use the traced rays and the
   Gaussian Beam Report until the future non-sequential astigmatic q model is
   implemented.

``GB input mode``
   ``Waist + offset`` is the direct q-parameter workflow. ``Diameter +
   divergence`` is the laser-datasheet workflow: enter the beam diameter at the
   source/reference plane and the full far-field divergence, then KrakenOS
   back-calculates the equivalent waist radius and waist location.

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

Datasheet diameter/divergence flow
----------------------------------

Laser manufacturers often specify a beam diameter at the laser output and a
full-angle divergence. Use this flow for beam expanders and collimators:

1. Choose ``Source model -> Gaussian beam``.
2. Set ``GB input mode -> Diameter + divergence``.
3. Enter ``GB diameter [mm]`` as the 1/e^2 beam diameter at the source plane.
4. Enter ``GB full div [mrad]`` as the full far-field divergence angle.
5. Choose ``GB waist side``. ``Waist before source`` is the normal diverging
   laser-output case. ``Waist after source`` represents a converging beam.
6. Set ``GB M2`` if the laser is not diffraction-limited.
7. Click ``Update``. The UI computes the equivalent ``w0`` and waist offset,
   traces representative rays, and draws the amber 1/e^2 q-envelope.

The calculation uses:

.. math::

   \theta = \frac{\Theta_{full}}{2}

.. math::

   w_0 = \frac{M^2 \lambda}{\pi n \theta}

.. math::

   z_R = \frac{\pi n w_0^2}{M^2 \lambda}

.. math::

   z = z_R \sqrt{\left(\frac{w}{w_0}\right)^2 - 1}

where ``w`` is half the specified beam diameter at the source plane. If
``w < w0``, the diameter/divergence pair is physically inconsistent and the UI
reports an invalid Gaussian source input.

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

Astigmatic and elliptical beams
-------------------------------

KrakenOS also exposes a two-axis helper for laser sources whose tangential and
sagittal beam diameters, divergences, or ``M2`` values are different. This is
useful for diode lasers and beam-shaping lenses where the source is elliptical.

The current UI and ``ParaxMatrices()`` path use one centered ABCD sequence, so
the two axes differ because the input beam data differ. This is not yet a full
oblique-incidence astigmatic matrix model. When future non-sequential or tilted
surface matrices expose separate tangential/sagittal ABCD chains, the same
per-axis propagation routine can consume them.

For splitter and folded-laser future work, see :doc:`beam_splitters`.
Deterministic beam-splitter ray branches now carry power and phase metadata.
The remaining Gaussian-beam step is to attach per-branch ``q`` state plus
optical path length through tilted/folded non-sequential systems.

.. code-block:: python

   astigmatic_beam = Kos.astigmatic_gaussian_beam_from_diameter_divergence(
       wavelength_um=0.6328,
       tangential_beam_diameter_mm=1.2,
       tangential_full_divergence_mrad=0.9,
       sagittal_beam_diameter_mm=0.8,
       sagittal_full_divergence_mrad=1.4,
       tangential_m2=1.1,
       sagittal_m2=1.3,
       waist_after_input=False,
   )
   astigmatic_trace = Kos.propagate_astigmatic_gaussian_beam(
       paraxial_trace,
       astigmatic_beam,
   )
   print(astigmatic_trace.final_tangential.beam_radius_mm)
   print(astigmatic_trace.final_sagittal.beam_radius_mm)

Cavity eigenmode flow
---------------------

The Gaussian Beam Report includes a ``Use Cavity Eigenmode`` button. It solves
the self-consistent mode:

.. math::

   q = \frac{Aq + B}{Cq + D}

for the current ABCD matrix, then fills the report input waist and waist offset
with that eigenmode. Use this only when the current ABCD matrix represents one
complete cavity round trip at the chosen reference plane. A normal single-pass
imaging lens is not a cavity round trip, so the button may correctly report an
unstable or invalid eigenmode.

The reported stability parameter is:

.. math::

   g = \frac{A + D}{2 \sqrt{AD - BC}}

and the mode is stable when ``|g| < 1`` and the solved ``q`` has a positive
imaginary part.

The same solve is available from Python:

.. code-block:: python

   import numpy as np
   import KrakenOS as Kos

   L = 300.0
   R = 1000.0
   propagation = np.array([[1.0, L], [0.0, 1.0]])
   mirror = np.array([[1.0, 0.0], [-2.0 / R, 1.0]])
   round_trip = mirror @ propagation @ mirror @ propagation

   mode = Kos.solve_gaussian_cavity_eigenmode(
       round_trip,
       wavelength_um=0.6328,
       m2=1.0,
   )
   if mode.stable:
       beam = mode.beam
       print(beam.waist_radius_mm, beam.waist_offset_mm)

UI workflow
-----------

1. Load ``Common Optical Layout -> Gaussian Beam ABCD Example``.
2. In the Source panel, choose ``Gaussian beam``.
3. Set ``GB waist [mm]``, ``GB waist offset [mm]``, and ``GB M2``.
4. Click ``Update`` to trace representative Gaussian source rays and draw the
   amber 1/e^2 q-envelope in the 2-D layout.
5. Open ``Actions -> Gaussian Beam Report`` for the per-surface q table.
6. For resonator layouts whose ABCD matrix is one complete round trip, click
   ``Use Cavity Eigenmode`` to seed the report from the stable cavity mode.
7. Use ``Export CSV`` when you want to compare the per-step q trace externally.

Low ray-count Gaussian previews use equal-spaced meridional samples inside the
current beam radius so the 2-D layout gaps are uniform. The outer preview rays
stay conservatively inside the source edge to avoid accidental clipping on
tilted finite plates. Increase ``Ray count`` above nine when you want the
representative rays to fill the 2-D source disk.

Folded laser scanner example
----------------------------

``Common Optical Layout -> Galvo F-Theta Laser Scanner`` demonstrates a typical
laser-scanner path:

1. a Gaussian 1064 nm source using diameter/divergence input
   (1 mm beam diameter and 50 mrad full divergence in the preset, so the
   source visibly diverges before the first beam-expander lens);
2. a negative/positive two-lens beam expander;
3. a 45 degree galvo mirror;
4. a simple positive F-theta proxy lens;
5. a flat scan/focus plane.

The preset uses ``Folded Preview`` so the 2-D layout reads like the physical
bench: beam expander, fold mirror, downward F-theta leg, and scan plane. It is
not yet a full non-sequential Gaussian q propagation through tilted optics; use
it as a ray-layout and source-workflow example. Change the galvo mirror
``TiltX`` by small amounts to see scan steering, then use detector/spot
analysis at the scan plane to inspect the representative ray footprint.

The galvo mirror row also supports a 2-D scan overlay. Right-click the mirror
row and choose ``Galvo scan overlay...``. Enter comma-separated TiltX values,
such as ``40,45,50`` or ``-50,-45,-40``, or a range like ``40:50:5``. The
nominal ``TiltX`` cell remains the editable center pose; the overlay values
draw additional mirror positions and representative focused bundles without
duplicating rows in the prescription table.

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

   # Alternative manufacturer-style input:
   beam = Kos.gaussian_beam_from_diameter_divergence(
       wavelength_um=0.6328,
       beam_diameter_mm=1.0,
       full_divergence_mrad=1.0,
       m2=1.0,
       waist_after_input=False,
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
``KrakenOS/Examples/Examp_Gaussian_Beam_Propagation.py``. A second runnable
example for astigmatic beams and cavity eigenmodes is available at
``KrakenOS/Examples/Examp_Gaussian_Laser_Modes.py``.

Scope and limitations
---------------------

This is a paraxial q-parameter tool, not a full diffraction field propagator. It
does not yet model clipping, higher-order modes, or coherent recombination after
beam splitters. Tangential/sagittal helpers model independent two-axis source
data on the current centered ABCD path; fully oblique astigmatic optics still
require future separate axis matrices.

The 2-D layout also traces an exact-count representative 2-D disk bundle so the
source appears in the normal ray display. The amber envelope is the physical
Gaussian beam size; the traced rays are still a visual/geometric guide rather
than a diffraction-field calculation.

Source-mode field relevance
---------------------------

When ``Gaussian beam`` or another physical source is selected, object/field and
pupil controls do not define the source. The UI therefore hides unused controls
such as ``Object mode``, ``Field type``, ``Pupil pattern``, and ``Pupil
factor``. The saved values are preserved internally and restored when returning
to ``Pupil / field``.

This distinction is intentional for future beam-splitter and illumination
workflows: an illumination source is a separate entity from the optical object.
For example, a source can illuminate an object through a 45 degree beam
splitter from a 90 degree direction. In that case source position, direction,
beam diameter, divergence, and power define the launched rays; object mode and
pupil-factor ray-height scaling are not the ray-generation controls.
