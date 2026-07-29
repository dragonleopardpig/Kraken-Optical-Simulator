Photonics Essentials: Chapter 3 Interactive Physics Lab
=======================================================

This lab turns the equations in Chapter 3, ``Photodiodes``, into curves that
can be changed directly in the browser.  It complements the
:doc:`ch03_diffusion_equation` derivation.

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
       excess_carrier_profile,
       photodiode_current_density,
       photovoltage,
       responsivity,
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
