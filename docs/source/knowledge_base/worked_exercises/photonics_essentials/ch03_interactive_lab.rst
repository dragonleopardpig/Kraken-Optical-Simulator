Photonics Essentials: Chapter 3 Interactive Physics Lab
=======================================================

This lab turns the equations in Chapter 3, ``Photodiodes``, into curves that
can be changed directly in the browser.  It complements the
:doc:`ch03_diffusion_equation` derivation and
:doc:`ch03_detector_modes` explanation.

.. important::

   The controls below use ideal equation-based models.  The modes labelled
   **qualitative** reproduce a measured curve's physical trends, not the
   book's experimental data.  Use a manufacturer's data sheet for device
   design.

Interactive curve explorer
--------------------------

Choose a curve, then move any slider.  The graph and calculated quantities
update immediately; no Python server is required, so this works on the
GitHub-hosted documentation.

.. raw:: html

   <div class="photodiode-lab" data-photodiode-lab>
     <p class="photodiode-lab__loading">Loading the Chapter 3 curve explorer...</p>
   </div>

Curves and equations
--------------------

The explorer includes:

.. list-table::
   :header-rows: 1
   :widths: 22 23 55

   * - Explorer mode
     - Chapter reference
     - What changes
   * - Carrier profile
     - Equations 3.5--3.11
     - Diffusion coefficient, lifetime, junction concentration, generation
   * - Junction bands
     - Figure 3.1
     - Built-in voltage and depletion width
   * - Photodiode I--V family
     - Figures 3.2--3.4; Equations 3.14 and 3.16
     - Temperature, ideality factor, dark current, illumination
   * - LED semilog I--V
     - Figure 3.5; Equation 3.16
     - Temperature, ideality factor, saturation current
   * - Ideal spectral cutoff
     - Figure 3.6; Equations 3.19--3.21
     - Band-gap energy
   * - Rounded detector response
     - Figure 3.7
     - Short and long absorption edges; **qualitative model**
   * - Absorption with depth
     - Figure 3.8; Equation 3.22
     - Absorption coefficient
   * - Silicon power with surface reflection
     - Section 3.4.1; Equation 3.22 and normal-incidence Fresnel reflection
     - Source power from :math:`1\ \mathrm{mW}` to :math:`10\ \mathrm W`,
       detection floor, silicon absorption coefficient, refractive index, and
       plotted depth. Power is plotted logarithmically on a fixed frame: raising
       the source lifts the curve without changing the decay length
       :math:`1/\alpha`, which belongs to the material. What power does move is
       the depth at which the beam is still above the floor, by
       :math:`\ln(10)/\alpha` per decade
   * - Silicon slab inverse designer
     - Section 3.4.1; inverse of Equation 3.22
     - Slab width, desired fractional transmission, desired absolute output
       power, absorption coefficient, and silicon refractive index
   * - Responsivity
     - Figure 3.9; Equations 3.25--3.28
     - Quantum efficiency and band gap
   * - Antireflection response
     - Figure 3.10; Equations 3.29--3.32
     - Film index, substrate index, thickness, design wavelength, and a
       **qualitative** collection envelope at the band-gap edge
   * - Open-circuit photovoltage
     - Equation 3.18
     - Temperature, ideality factor, and optical generation

Python physics engine
---------------------

The browser controls and the notebook use the same equations implemented in
``KrakenOS/Physics/photodiode.py``.  Its primary entry points are:

.. code-block:: python

   from KrakenOS.Physics.photodiode import (
       PhotodiodeParameters,
       absorption_coefficient_for_transmission,
       excess_carrier_profile,
       absorption_power,
       photodiode_current_density,
       photovoltage,
       required_source_log10_power,
       responsivity,
       slab_log10_transmission,
   )

   parameters = PhotodiodeParameters(
       diffusion_cm2_s=25.0,
       lifetime_s=1e-6,
       temperature_k=300.0,
   )

   current = photodiode_current_density(
       [-0.5, 0.0, 0.5],
       parameters=parameters,
       generation_cm3_s=2.5e11,
   )

Live Jupyter kernel
-------------------

The button opens a real JupyterLite notebook backed by a Python kernel
compiled for the browser with Pyodide.  It runs locally on the reader's
computer; GitHub Pages only serves static files.  The first kernel start can
take several seconds because the browser downloads Python and NumPy.

.. notebooklite:: notebooks/ch03_photodiode_lab.ipynb
   :new_tab: True
   :new_tab_button_text: Open Chapter 3 in JupyterLite

The notebook is intentionally separate from the instant slider explorer:
the explorer is fast and works without a kernel, while the notebook exposes
the Python equations for modification and further experiments.

Silicon absorption with and without surface reflection
------------------------------------------------------

Equation 3.22 describes the intensity after light has entered the material:

.. math::

   I_{\mathrm{bulk}}(x)=I_0e^{-\alpha x}.
   \tag{3.22}

For a beam whose cross-sectional area is constant, :math:`P=IA`, so optical
power has the same exponential dependence:

.. math::

   P_{\mathrm{no\ surface}}(x)=P_0e^{-\alpha x}.

At normal incidence, an uncoated air-to-silicon boundary reflects the
fraction

.. math::

   R
   =
   \left(
      \frac{n_{\mathrm{air}}-n_{\mathrm{Si}}}
           {n_{\mathrm{air}}+n_{\mathrm{Si}}}
   \right)^2.

The power that actually enters silicon is :math:`(1-R)P_0`.  The comparison
curve is therefore

.. math::

   P_{\mathrm{with\ surface}}(x)
   =
   (1-R)P_0e^{-\alpha x}.

For the explorer's initial values,
:math:`n_{\mathrm{air}}=1`, :math:`n_{\mathrm{Si}}=3.5`, and
:math:`\alpha=100\ \mathrm{cm^{-1}}`:

.. math::

   R=0.3086,
   \qquad
   \frac{1}{\alpha}=100\ \mathrm{\mu m}.

Thus about :math:`69.1\%` of the incident power crosses the uncoated surface.
At one absorption length, :math:`e^{-1}=0.3679` of that entering power
remains, or about :math:`25.4\%` of the original source power.

.. note::

   Real silicon's refractive index and absorption coefficient depend strongly
   on wavelength, temperature, doping, surface layers, and angle of
   incidence.  Strongly absorbing silicon is described by a complex
   refractive index, whereas this introductory Fresnel calculation uses a
   real index.  The controls isolate the Chapter 3 equations; they are not a
   substitute for wavelength-dependent measured optical constants.

Inverse design: how much source power is required?
--------------------------------------------------

For a slab, light crosses an entrance and an exit surface.  In the simple
single-pass model, the fraction transmitted through two uncoated surfaces
and the absorbing bulk is

.. math::

   T_{\mathrm{slab}}
   =
   \frac{P_{\mathrm{out}}}{P_{\mathrm{source}}}
   =
   (1-R)^2 e^{-\alpha d},

where :math:`d` is the slab width.  Therefore, the source power required for
a specified **absolute** output power is

.. math::

   P_{\mathrm{source}}
   =
   \frac{P_{\mathrm{out,target}}}
        {(1-R)^2e^{-\alpha d}}.

This is different from asking for a percentage of the source to be
transmitted.  For a desired fractional transmission
:math:`T_{\mathrm{target}}`,

.. math::

   T_{\mathrm{target}}
   =
   (1-R)^2e^{-\alpha d}.

The source power cancels.  Increasing it raises both
:math:`P_{\mathrm{source}}` and :math:`P_{\mathrm{out}}` by the same factor,
so it cannot change the percentage.  Instead, solve for the largest
acceptable absorption coefficient:

.. math::

   \alpha_{\max}
   =
   -\frac{1}{d}
   \ln\left(
      \frac{T_{\mathrm{target}}}{(1-R)^2}
   \right).

Eight-millimetre silicon example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use the initial inverse-designer values:

.. math::

   d=8\ \mathrm{mm}=0.8\ \mathrm{cm},
   \qquad
   \alpha=100\ \mathrm{cm^{-1}},
   \qquad
   n_{\mathrm{Si}}=3.5.

The surface reflectance and total transmission are

.. math::

   R=0.3086,
   \qquad
   T_{\mathrm{slab}}
   =(1-0.3086)^2e^{-80}
   \approx 8.63\times10^{-36}.

Consequently, **no source power can make 10% of the incident power emerge**
while these linear material parameters remain fixed.  Achieving
:math:`T_{\mathrm{target}}=10\%` through :math:`8\ \mathrm{mm}` would
require

.. math::

   \boxed{\alpha\leq1.96\ \mathrm{cm^{-1}}}.

At :math:`\alpha=100\ \mathrm{cm^{-1}}`, the maximum width that gives 10%
transmission is only approximately

.. math::

   \boxed{d_{\max}=0.156\ \mathrm{mm}}.

If the intended requirement is instead an absolute output of
:math:`100\ \mathrm{mW}`, then the ideal equation predicts a required source
near :math:`1.16\times10^{34}\ \mathrm W`.  That impossible result is useful:
it says to change wavelength, material, thickness, or detection method rather
than searching for a stronger source.

The **Silicon slab inverse designer** plots required source power against
width.  Its logarithmic Y-axis uses readable SI power units rather than
scientific notation.

.. warning::

   This is a linear, single-pass Beer--Lambert calculation.  It neglects
   coherent etalon effects, repeated internal reflections, heating,
   free-carrier absorption, and nonlinear absorption.  At high power the
   relevant quantity is irradiance, so beam area and pulse duration would
   also be required.
