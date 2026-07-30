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
   * - Silicon slab and 1100 nm LED
     - Section 3.4.1; inverse of Equation 3.22
     - Slab width, wavelength, LED spectral width, incident optical power,
       desired fractional transmission, and desired absolute output power.
       The wavelength-dependent silicon data are from Green (2008)
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
       silicon_optical_properties,
       silicon_slab_transmission,
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

Silicon slab and 1100 nm LED
----------------------------

The absorption coefficient in Equation 3.22 is not one fixed property of
silicon.  It is a strong function of wavelength, especially near silicon's
indirect band edge.  The slab explorer uses the tabulated intrinsic-silicon
values at :math:`300\ \mathrm K` from `Green (2008)
<https://doi.org/10.1016/j.solmat.2008.06.009>`_.  At
:math:`1100\ \mathrm{nm}`, that table gives

.. math::

   \alpha=3.5\ \mathrm{cm^{-1}},
   \qquad
   n=3.542.

.. important::

   An earlier version of this page used
   :math:`\alpha=100\ \mathrm{cm^{-1}}` in the 8 mm example.  That is close
   to Green's value near :math:`980\ \mathrm{nm}`, not
   :math:`1100\ \mathrm{nm}`.  Applying it to an 1100 nm experiment caused
   the physically absurd million-quetta-watt result.

For a slab, let the one-pass bulk transmission be
:math:`A=e^{-\alpha d}`.  The explorer includes the incoherent sequence of
forward beams produced by repeated reflections between two parallel,
uncoated surfaces:

.. math::

   T_{\mathrm{slab}}
   =
   \frac{P_{\mathrm{out}}}{P_{\mathrm{source}}}
   =
   \frac{(1-R)^2A}{1-R^2A^2},
   \qquad
   A=e^{-\alpha d}.

The single-pass approximation :math:`(1-R)^2e^{-\alpha d}` is recovered by
omitting the denominator.  For a specified **absolute** output power,

.. math::

   P_{\mathrm{source}}
   =
   \frac{P_{\mathrm{out,target}}}{T_{\mathrm{slab}}}.

This is different from asking for a percentage of the source to be
transmitted.  Source power cancels from the fraction:

.. math::

   \frac{P_{\mathrm{out}}}{P_{\mathrm{source}}}
   =T_{\mathrm{slab}}(\lambda,d).

Increasing source power raises both
:math:`P_{\mathrm{source}}` and :math:`P_{\mathrm{out}}` by the same factor,
so it cannot change the percentage in this linear model.  Wavelength,
thickness, surface treatment, temperature, and material properties do change
the percentage.

Eight-millimetre silicon example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For monochromatic :math:`1100\ \mathrm{nm}` light and
:math:`d=8\ \mathrm{mm}=0.8\ \mathrm{cm}`,

.. math::

   A=e^{-3.5(0.8)}=e^{-2.8}=0.0608,
   \qquad
   R=\left(\frac{1-3.542}{1+3.542}\right)^2=0.3132.

The predicted uncoated-slab transmission is therefore

.. math::

   T_{\mathrm{slab}}
   =
   \frac{(1-0.3132)^2e^{-2.8}}
        {1-0.3132^2e^{-5.6}}
   =0.02869
   \approx 2.87\%.

Thus :math:`3\ \mathrm W` of **optical power incident on the slab** gives

.. math::

   P_{\mathrm{out}}
   =(3\ \mathrm W)(0.02869)
   =86.1\ \mathrm{mW}.

Conversely, obtaining :math:`100\ \mathrm{mW}` after the slab requires

.. math::

   P_{\mathrm{source}}
   =\frac{0.100\ \mathrm W}{0.02869}
   =3.49\ \mathrm W.

This result is consistent with seeing transmitted light using a few-watt
source and a sensitive SWIR camera.  It does not say that 10% is transmitted:
a camera can clearly detect much less than 10%, depending on irradiance,
exposure, lens throughput, sensor response, and display gain.

Real LED spectrum
~~~~~~~~~~~~~~~~~

An LED is not monochromatic.  The explorer models its spectral power density
as a Gaussian with a selectable full width at half maximum (FWHM) and
integrates

.. math::

   T_{\mathrm{LED}}
   =
   \frac{\int S(\lambda)T_{\mathrm{slab}}(\lambda,d)\,d\lambda}
        {\int S(\lambda)\,d\lambda}.

For a nominal 1100 nm LED with a 50 nm FWHM, the model predicts approximately
:math:`5.04\%` transmission through 8 mm.  The transmitted spectrum is biased
toward the longer-wavelength tail because :math:`\alpha(\lambda)` falls
rapidly there.  With :math:`3\ \mathrm W` incident optical power, this example
gives about :math:`151\ \mathrm{mW}` after the slab.

The desired-transmission readout reports the approximate monochromatic
wavelength needed for the selected thickness.  For 10% through 8 mm, the
tabulated model gives about :math:`1121\ \mathrm{nm}` or longer.

.. warning::

   The source-power control is **incident optical radiant power**, not an
   LED's electrical input rating.  Use the LED datasheet's radiant-power
   spectrum, or measure it, for a quantitative comparison.

.. note::

   Green's table describes intrinsic silicon at 300 K.  Doping, defects,
   temperature, oxide or antireflection layers, surface roughness, incidence
   angle, finite camera aperture, and the actual LED and camera spectra can
   materially change a laboratory result.  The independent Schinke et al.
   dataset provides wavelength-dependent uncertainty and temperature
   coefficients for crystalline silicon (`ISFH data
   <https://isfh.de/en/datensaetze>`_).
