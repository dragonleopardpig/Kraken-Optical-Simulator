Analysis Tools (Layout Editor Toolbar)
======================================

The **Analysis** row of the |ui| toolbar exposes 23 toggleable analyses that
plot data on top of the editable layout. Their button labels and tooltip text
are defined in ``KrakenOS/UI/layout_editor.py`` near
``mode_button_groups`` / ``mode_tooltips``. This page collects the *theory*
behind each tool — the equation(s) it evaluates and what the resulting figure
represents — together with a schematic SVG of the typical output.

The toolbar groups them into five clusters, reflected by the section
ordering below:

* **Geometric image quality** — Spot, RMS, PSF, MTF
* **Pupil and wavefront** — Pupil, Seidel, WFront, Zernike
* **Field-dependent metrics** — FC/Dist, Illum, LatClr, Pol, Atmos
* **Map analyses on the detector / pupil** — PSFMap, FldMap, IllMap, WfeMap,
  DetMap, CohDet, BField, Diffr
* **Comparative analyses** — Interf, TolCmp

Throughout the equations below, :math:`(u, v)` are *normalised pupil
coordinates* (``Pup.Cordx, Pup.Cordy``), :math:`(x, y)` are image-plane
coordinates, :math:`\lambda` is the wavelength, :math:`F/\#` is the working
F-number, :math:`W(u, v)` is the optical-path-difference (OPD) wavefront, and
:math:`P(u, v)` is the (possibly apodized) pupil-amplitude function.

.. contents::
   :local:
   :depth: 1


Geometric image quality
-----------------------

.. _analysis-spot:

Spot — Spot Diagram
~~~~~~~~~~~~~~~~~~~

Plots ray intercepts at the analysis surface (or the system image plane)
for the currently selected fields and wavelengths. For ``N`` traced rays
with hit coordinates :math:`(x_i, y_i)` the centroid and geometric RMS spot
radius are

.. math::

   \bar{x} = \frac{1}{N}\sum_i x_i, \quad
   \bar{y} = \frac{1}{N}\sum_i y_i, \quad
   \sigma_{\mathrm{RMS}}
   = \sqrt{\frac{1}{N}\sum_i \bigl[(x_i-\bar{x})^2 + (y_i-\bar{y})^2\bigr]}.

The geometric reference is the *Airy radius*
:math:`r_{\mathrm{Airy}} = 1.22\,\lambda\,F/\#`; when
:math:`\sigma_{\mathrm{RMS}} \lesssim r_{\mathrm{Airy}}` the system is
diffraction-limited.

.. figure:: ../_static/manual/analysis_tools/01_spot.svg
   :alt: Spot diagram on the image plane
   :align: center
   :width: 360px


.. _analysis-rms:

RMS — RMS Spot Radius
~~~~~~~~~~~~~~~~~~~~~

Computes :math:`\sigma_{\mathrm{RMS}}(h)` (the formula above) for a swept
field point ``h`` and plots one curve per wavelength. Useful as a quick
proxy for image quality across the field without forming a full PSF.

.. figure:: ../_static/manual/analysis_tools/02_rms.svg
   :alt: RMS spot radius vs field, several wavelengths
   :align: center
   :width: 360px


.. _analysis-psf:

PSF — Point Spread Function
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The image-plane irradiance produced by a point source. With the
Fraunhofer / Fourier-optics formulation,

.. math::

   \mathrm{PSF}(x, y) \;\propto\;
   \Bigl|\,\iint P(u, v)\,
       e^{\,i\,k\,W(u, v)}\,
       e^{\,-i\,2\pi\,(u x + v y) / (\lambda z)}\,
       \mathrm{d}u\,\mathrm{d}v\,\Bigr|^{2},

where :math:`k = 2\pi/\lambda`. The diffraction-limited case
(:math:`W \equiv 0`) is the Airy pattern with central radius
:math:`r_{\mathrm{Airy}} = 1.22\,\lambda\,F/\#`.

.. figure:: ../_static/manual/analysis_tools/03_psf.svg
   :alt: Schematic Airy-like PSF
   :align: center
   :width: 360px


.. _analysis-mtf:

MTF — Modulation Transfer Function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Magnitude of the Optical Transfer Function (OTF), which is the autocorrelation
of the generalized pupil:

.. math::

   \mathrm{OTF}(\boldsymbol{\nu})
   = \frac{\iint P(\mathbf{u})\,e^{i k W(\mathbf{u})}\,
                 P^{\!*}(\mathbf{u} - \lambda z\boldsymbol{\nu})\,
                 e^{-i k W(\mathbf{u} - \lambda z\boldsymbol{\nu})}\,
                 \mathrm{d}\mathbf{u}}
          {\iint |P(\mathbf{u})|^{2}\,\mathrm{d}\mathbf{u}},

   \quad \mathrm{MTF}(\boldsymbol{\nu}) = |\mathrm{OTF}(\boldsymbol{\nu})|.

For a clear circular pupil the diffraction-limited MTF is

.. math::

   \mathrm{MTF}_{\mathrm{DL}}(\nu)
     = \tfrac{2}{\pi}\!\left[\phi - \cos\phi\,\sin\phi\right],
   \quad \phi = \arccos\!\left(\nu / \nu_c\right),

with cut-off frequency :math:`\nu_c = 1/(\lambda\,F/\#)`. KrakenOS plots both
tangential and sagittal MTF along with the diffraction-limited reference.

.. figure:: ../_static/manual/analysis_tools/04_mtf.svg
   :alt: Diffraction-limited MTF with tangential/sagittal curves
   :align: center
   :width: 360px


Pupil and wavefront
-------------------

.. _analysis-pupil:

Pupil — Pupil Diagnostic
~~~~~~~~~~~~~~~~~~~~~~~~

Reports the *entrance* (EP) and *exit* (XP) pupil positions and diameters
along the optical axis, plus the chief- and marginal-ray paths. KrakenOS
computes the small-angle pupil magnifications

.. math::

   m_{\mathrm{enter}} = \frac{\theta_0}{\theta_{\mathrm{stop}}}, \quad
   m_{\mathrm{exit}}  = \frac{\theta_0}{\theta_{\mathrm{image}}}

(see ``PupilCalc.__init__`` in ``KrakenOS/PupilTool.py`` for the explicit
fan-of-rays construction). With a measured stop diameter :math:`D_{\mathrm{stop}}`,

.. math::

   D_{\mathrm{EP}} = D_{\mathrm{stop}} / m_{\mathrm{enter}}, \quad
   D_{\mathrm{XP}} = D_{\mathrm{stop}} \cdot m_{\mathrm{exit}}.

.. figure:: ../_static/manual/analysis_tools/05_pupil.svg
   :alt: Pupil diagnostic showing EP, Stop, and XP markers
   :align: center
   :width: 360px


.. _analysis-seidel:

Seidel — Seidel Aberrations
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Per-surface sums of the third-order monochromatic aberration coefficients
:math:`S_{\mathrm{I}}..S_{\mathrm{V}}` and the chromatic terms
:math:`C_{\mathrm{I}}, C_{\mathrm{II}}`. The total wavefront aberration of the
system as a polynomial in pupil and field is

.. math::

   W(u, v; h)
   \;\sim\; S_{\mathrm{I}}\,\rho^{4}
   + S_{\mathrm{II}}\,h\,\rho^{3}\cos\theta
   + S_{\mathrm{III}}\,h^{2}\,\rho^{2}\cos^{2}\theta
   + S_{\mathrm{IV}}\,h^{2}\,\rho^{2}
   + S_{\mathrm{V}}\,h^{3}\,\rho\cos\theta,

with :math:`\rho^{2} = u^{2} + v^{2}` and :math:`\theta = \arg(u + i v)`. Each
:math:`S_{k}` is a sum over surfaces; KrakenOS plots the per-surface bars so
the dominant contributor can be identified.

.. figure:: ../_static/manual/analysis_tools/06_seidel.svg
   :alt: Bar chart of Seidel + chromatic aberration contributions
   :align: center
   :width: 360px


.. _analysis-wfront:

WFront — Wavefront Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Computes the OPD :math:`W(u, v)` of every traced ray relative to a reference
sphere centred on the chief-ray intercept and plots a slice (or the full 2D
map — see :ref:`WfeMap <analysis-wfemap>`). The key scalar summaries are

.. math::

   \mathrm{PV}  = \max(W) - \min(W), \qquad
   \mathrm{RMS} = \sqrt{\langle (W - \langle W\rangle)^{2}\rangle},

with the Maréchal approximation linking RMS to the Strehl ratio
(small-aberration limit):

.. math::

   S \;\approx\; \exp\!\bigl[-(2\pi\,\mathrm{RMS}/\lambda)^{2}\bigr].

.. figure:: ../_static/manual/analysis_tools/07_wavefront.svg
   :alt: Wavefront slice with PV / RMS / Strehl indicated
   :align: center
   :width: 360px


.. _analysis-zernike:

Zernike — Zernike Polynomial Fit
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Expands the wavefront on the orthonormal Zernike basis over the unit disk,

.. math::

   W(\rho, \theta) = \sum_{j} a_{j}\,Z_{j}(\rho, \theta),
   \quad Z_{n}^{m}(\rho, \theta)
   = R_{n}^{m}(\rho)\!\cdot\!
     \begin{cases}\cos(m\theta), & m \ge 0\\ \sin(|m|\theta), & m < 0\end{cases}

with radial polynomials

.. math::

   R_{n}^{|m|}(\rho)
   = \sum_{k=0}^{(n-|m|)/2}
     \frac{(-1)^{k}(n-k)!}{k!\,\bigl((n+|m|)/2 - k\bigr)!\,
                            \bigl((n-|m|)/2 - k\bigr)!}\,
     \rho^{n - 2k}.

Coefficients :math:`a_{j}` are recovered by a linear least-squares fit to the
sampled wavefront and displayed both as a bar chart and as a colour map.

.. figure:: ../_static/manual/analysis_tools/08_zernike.svg
   :alt: Zernike disk and coefficient bar chart
   :align: center
   :width: 360px


Field-dependent metrics
-----------------------

.. _analysis-fc-dist:

FC/Dist — Field Curvature / Distortion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Two coupled plots: **field curvature** is the focus shift
:math:`\Delta z_{\mathrm{focus}}(h)` of the best image surface from the
paraxial image plane, split into tangential (T) and sagittal (S) branches.
**Distortion** is the radial deviation of the real image height from the
paraxial value:

.. math::

   \mathrm{distortion}(h) \;=\; \frac{h_{\mathrm{real}} - h_{\mathrm{paraxial}}}
                                       {h_{\mathrm{paraxial}}} \times 100\,\%.

.. figure:: ../_static/manual/analysis_tools/09_field_curvature.svg
   :alt: Field curvature S/T branches and distortion curve
   :align: center
   :width: 360px


.. _analysis-illum:

Illum — Relative Illumination
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Image-plane irradiance normalised to the on-axis value:

.. math::

   \mathrm{RI}(\theta) = \frac{E(\theta)}{E(0)}.

For an ideal lens with no vignetting, geometric considerations yield the
classical **cos⁴ law**,

.. math::

   \mathrm{RI}(\theta) = \cos^{4}\theta,

and KrakenOS overlays the measured curve (which also captures vignetting and
pupil aberration) on top of that reference.

.. figure:: ../_static/manual/analysis_tools/10_illumination.svg
   :alt: cos^4 ideal curve and measured RI vs field
   :align: center
   :width: 360px


.. _analysis-latclr:

LatClr — Lateral Color
~~~~~~~~~~~~~~~~~~~~~~

The transverse separation of chief-ray landing points between wavelengths,

.. math::

   \Delta y_{\mathrm{lat}}(\lambda; h) = y_{\mathrm{chief}}(\lambda, h)
                                       - y_{\mathrm{chief}}(\lambda_{0}, h),

with :math:`\lambda_{0}` the reference wavelength. The result is a coloured
spread along the field direction (chromatic difference of magnification).

.. figure:: ../_static/manual/analysis_tools/11_lateral_color.svg
   :alt: Lateral color curves for two wavelengths vs field
   :align: center
   :width: 360px


.. _analysis-pol:

Pol — Polarization
~~~~~~~~~~~~~~~~~~

Tracks the Jones state :math:`\mathbf{E}_{\mathrm{out}} = J\,\mathbf{E}_{\mathrm{in}}`
through every interaction, applying the Fresnel coefficients at each surface,

.. math::

   r_{s} = \frac{n_{1}\cos\theta_{1} - n_{2}\cos\theta_{2}}
                {n_{1}\cos\theta_{1} + n_{2}\cos\theta_{2}}, \quad
   r_{p} = \frac{n_{2}\cos\theta_{1} - n_{1}\cos\theta_{2}}
                {n_{2}\cos\theta_{1} + n_{1}\cos\theta_{2}},

and rotating the local s/p frame between surfaces. KrakenOS reports
transmittance, diattenuation, and retardance; the Stokes vector
:math:`\mathbf{S} = (S_{0}, S_{1}, S_{2}, S_{3})` gives the *degree of
polarization* :math:`\mathrm{DoP} = \sqrt{S_{1}^{2}+S_{2}^{2}+S_{3}^{2}}/S_{0}`.

.. figure:: ../_static/manual/analysis_tools/12_polarization.svg
   :alt: Polar transmittance curves T_s and T_p vs AOI
   :align: center
   :width: 360px


.. _analysis-atmos:

Atmos — Atmospheric Dispersion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Bends each incoming ray by the wavelength-dependent atmospheric refraction
:math:`R(\lambda; T, P, H, z_{0}, \ldots)` reported by the AstroAtmosphere
library (Ref. 3). A useful closed form is the Cassini approximation

.. math::

   R(z) \;\approx\; A(\lambda)\,\tan z - B(\lambda)\,\tan^{3} z,

with :math:`z` the zenith distance and :math:`A`, :math:`B` weak functions of
temperature, pressure, humidity, CO₂ and latitude. KrakenOS plots one curve
per wavelength and uses the same model when ``Pup.AtmosRef = 1`` in
``PupilCalc``.

.. figure:: ../_static/manual/analysis_tools/13_atmosphere.svg
   :alt: Atmospheric refraction vs zenith distance for three wavelengths
   :align: center
   :width: 360px


Map analyses on the detector / pupil
------------------------------------

.. _analysis-psfmap:

PSFMap — Point Spread Function Map
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Renders the local PSF at a grid of field positions :math:`(x_{f}, y_{f})` —
useful for visualising how aberrations (notably coma, astigmatism and field
curvature) deform the spot across the field. Each cell evaluates

.. math::

   \mathrm{PSF}(x, y; x_{f}, y_{f})
   = \bigl|\,\mathcal{F}\!\left\{P(u, v)\,e^{\,i k W(u, v;\,x_{f}, y_{f})}\right\}\bigr|^{2}.

.. figure:: ../_static/manual/analysis_tools/14_psf_map.svg
   :alt: Field-position grid of locally-deformed PSFs
   :align: center
   :width: 360px


.. _analysis-fldmap:

FldMap — Field Map
~~~~~~~~~~~~~~~~~~

Plots the real chief-ray image positions on a regular field grid and overlays
the paraxial / ideal grid. The pointwise displacement vector

.. math::

   \Delta\mathbf{r}(x_{f}, y_{f}) =
        \mathbf{r}_{\mathrm{real}}(x_{f}, y_{f})
      - \mathbf{r}_{\mathrm{paraxial}}(x_{f}, y_{f})

visualises distortion (radial component) and lateral colour /
field-dependent decentre (azimuthal component) together.

.. figure:: ../_static/manual/analysis_tools/15_field_map.svg
   :alt: Real (red) vs paraxial (grey) image grid showing distortion
   :align: center
   :width: 360px


.. _analysis-illmap:

IllMap — Illumination Map
~~~~~~~~~~~~~~~~~~~~~~~~~

A 2D irradiance heat map on the detector,

.. math::

   E(x, y) = \frac{\mathrm{d}\Phi}{\mathrm{d}A}
           = \sum_{i\in\mathrm{pixel}} \frac{w_{i}\cos\alpha_{i}}{A_{\mathrm{pix}}},

where :math:`w_{i}` is the per-ray energy weight and :math:`\alpha_{i}` is
the incidence angle on the pixel. The map captures cos⁴ falloff, vignetting,
caustics and lens hot-spots in a single picture.

.. figure:: ../_static/manual/analysis_tools/16_illum_map.svg
   :alt: Detector irradiance heat map with colorbar
   :align: center
   :width: 360px


.. _analysis-wfemap:

WfeMap — Wavefront Error Map
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The 2D analogue of :ref:`WFront <analysis-wfront>`: a colour map of
:math:`W(u, v)` over the exit pupil. The same PV / RMS / Strehl summaries
apply,

.. math::

   \mathrm{PV} = \max_{u^2+v^2 \le 1} W - \min_{u^2+v^2 \le 1} W, \qquad
   \mathrm{RMS}^{2} = \frac{1}{\pi}\iint_{u^2+v^2\le 1}
                          (W - \langle W\rangle)^{2}\,\mathrm{d}u\,\mathrm{d}v.

.. figure:: ../_static/manual/analysis_tools/17_wfe_map.svg
   :alt: 2D wavefront error map on the unit pupil
   :align: center
   :width: 360px


.. _analysis-detmap:

DetMap — Detector Power Map
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Bins the *incoherent* power of each landed ray into detector pixels:

.. math::

   P_{kl} = \sum_{i \in \mathrm{pixel}(k, l)} w_{i}.

Used for radiometric / throughput analyses and to detect stray-light hot
spots. ``CohDet`` (next) replaces the sum with a coherent one.

.. figure:: ../_static/manual/analysis_tools/18_detector_map.svg
   :alt: Detector power map - binned ray weights per pixel
   :align: center
   :width: 360px


.. _analysis-cohdet:

CohDet — Coherent Detector Field Sum
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Replaces the incoherent sum in DetMap with a *coherent* sum of complex
amplitudes carried along each ray (including OPL, transmittance and
polarization phase),

.. math::

   I_{kl} = \Bigl|\!\sum_{i\in\mathrm{pixel}(k,l)} \sqrt{w_{i}}\;
                          \exp\!\bigl[\,i\,(k\,\mathrm{OPL}_{i} + \varphi_{i})\bigr]\Bigr|^{2}.

This reveals interferometric fringes from two-beam recombination
(Mach–Zehnder, Michelson, etc.), speckle, and any other coherent effects
the trace can resolve.

.. figure:: ../_static/manual/analysis_tools/19_coherent_detector.svg
   :alt: Coherent fringe pattern from a two-beam superposition
   :align: center
   :width: 360px


.. _analysis-bfield:

BField — Branch Field
~~~~~~~~~~~~~~~~~~~~~

For Gaussian-branch sources, plots the on-axis intensity :math:`|E(x)|^2` and
phase :math:`\arg E(x)` of the propagated field along the current branch,
together with a fitted TEM₀₀ Hermite–Gauss template. The mode-overlap
efficiency is

.. math::

   \eta = \frac{\bigl|\!\int E^{*}(x)\,u_{\mathrm{TEM}_{00}}(x)\,\mathrm{d}A\bigr|^{2}}
                {\!\int |E|^{2}\,\mathrm{d}A \cdot
                 \!\int |u_{\mathrm{TEM}_{00}}|^{2}\,\mathrm{d}A}.

.. figure:: ../_static/manual/analysis_tools/20_branch_field.svg
   :alt: Branch field intensity, phase, and TEM00 overlap template
   :align: center
   :width: 360px


.. _analysis-diffr:

Diffr — Diffraction Detector
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Computes the angular spectrum of the coherent field landing on the detector,

.. math::

   \tilde{E}(k_{x}, k_{y}) = \iint E(x, y)\,
       e^{-i(k_{x} x + k_{y} y)}\,\mathrm{d}x\,\mathrm{d}y,

and plots :math:`|\tilde{E}|^{2}` versus angular direction
:math:`(\theta_x, \theta_y) = (k_x, k_y)/k`. This is the natural output for
gratings, holograms and far-field diffraction studies.

.. figure:: ../_static/manual/analysis_tools/21_diffraction.svg
   :alt: Diffraction angular spectrum (sinc^2 example)
   :align: center
   :width: 360px


Comparative analyses
--------------------

.. _analysis-interf:

Interf — Interferogram
~~~~~~~~~~~~~~~~~~~~~~

Simulates a two-beam interference fringe pattern between the system
wavefront and an ideal reference,

.. math::

   I(u, v) = I_{1} + I_{2} + 2\sqrt{I_{1} I_{2}}\;
             \cos\!\left[\,\frac{2\pi}{\lambda}\,W(u, v) + \varphi_{0}\,\right].

Adding tilt / defocus to :math:`W` introduces straight or annular reference
fringes the way a real Twyman–Green or Fizeau interferometer does.

.. figure:: ../_static/manual/analysis_tools/22_interferogram.svg
   :alt: Mock interferogram fringes over the pupil
   :align: center
   :width: 360px


.. _analysis-tolcmp:

TolCmp — Tolerance Compare
~~~~~~~~~~~~~~~~~~~~~~~~~~

Overlays the *nominal-design* spot diagram against the **worst** Monte-Carlo
sample from the tolerance run (see ``KrakenOS/UI/validate_tolerance_monte_carlo.py``).
Each parameter :math:`p_{k}` is perturbed by :math:`\delta p_{k}` drawn from
its tolerance distribution; the merit function

.. math::

   M(\boldsymbol{\delta}) = \sigma_{\mathrm{RMS}}\!\bigl(\boldsymbol{\delta}\bigr)
   \quad\text{or}\quad
   M(\boldsymbol{\delta}) = \mathrm{Strehl}\!\bigl(\boldsymbol{\delta}\bigr)

is recorded, and the worst (highest σ / lowest Strehl) sample is shown
overlaid on the nominal cluster.

.. figure:: ../_static/manual/analysis_tools/23_tolerance_compare.svg
   :alt: Nominal vs worst Monte-Carlo spot overlay
   :align: center
   :width: 360px


Cross-reference table
---------------------

.. list-table:: Toolbar button ↔ analysis mode ↔ this page
   :header-rows: 1
   :widths: 18 24 58

   * - Button
     - ``mode`` key
     - Anchor
   * - Spot
     - ``spot``
     - :ref:`analysis-spot`
   * - RMS
     - ``rms``
     - :ref:`analysis-rms`
   * - PSF
     - ``psf``
     - :ref:`analysis-psf`
   * - MTF
     - ``mtf``
     - :ref:`analysis-mtf`
   * - Pupil
     - ``pupil``
     - :ref:`analysis-pupil`
   * - Seidel
     - ``seidel``
     - :ref:`analysis-seidel`
   * - WFront
     - ``wavefront``
     - :ref:`analysis-wfront`
   * - Zernike
     - ``zernike``
     - :ref:`analysis-zernike`
   * - FC/Dist
     - ``field_curvature``
     - :ref:`analysis-fc-dist`
   * - Illum
     - ``relative_illumination``
     - :ref:`analysis-illum`
   * - LatClr
     - ``lateral_color``
     - :ref:`analysis-latclr`
   * - Pol
     - ``polarization``
     - :ref:`analysis-pol`
   * - Atmos
     - ``atmosphere``
     - :ref:`analysis-atmos`
   * - PSFMap
     - ``psf_map``
     - :ref:`analysis-psfmap`
   * - FldMap
     - ``field_map``
     - :ref:`analysis-fldmap`
   * - IllMap
     - ``illum_map``
     - :ref:`analysis-illmap`
   * - WfeMap
     - ``wavefront_map``
     - :ref:`analysis-wfemap`
   * - DetMap
     - ``detector_map``
     - :ref:`analysis-detmap`
   * - CohDet
     - ``coherent_detector``
     - :ref:`analysis-cohdet`
   * - BField
     - ``branch_field``
     - :ref:`analysis-bfield`
   * - Diffr
     - ``diffraction_detector``
     - :ref:`analysis-diffr`
   * - Interf
     - ``interferogram``
     - :ref:`analysis-interf`
   * - TolCmp
     - ``tolerance_compare``
     - :ref:`analysis-tolcmp`
