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

Symbol conventions
------------------

Symbols that recur throughout the page:

.. list-table::
   :header-rows: 1
   :widths: 18 82

   * - Symbol
     - Meaning
   * - :math:`(u, v)`
     - Normalised pupil coordinates, :math:`u^{2} + v^{2} \le 1`. Stored as
       ``Pup.Cordx``, ``Pup.Cordy`` in ``KrakenOS.PupilCalc``.
   * - :math:`(\rho, \theta)`
     - Polar form of the pupil coordinates: :math:`\rho = \sqrt{u^{2}+v^{2}}`,
       :math:`\theta = \arg(u + iv)`.
   * - :math:`(x, y)`
     - Cartesian coordinates on the image / detector plane, in millimetres.
   * - :math:`(x_{f}, y_{f})`
     - Field-point coordinates (object-space angle in degrees or object
       height in mm, set by ``Pup.FieldX``/``Pup.FieldY`` and
       ``Pup.FieldType``).
   * - :math:`h`
     - Generic field magnitude — image height (mm) for finite objects,
       field angle (rad or deg) for objects at infinity.
   * - :math:`\lambda`
     - Wavelength, in millimetres (matches the rest of the KrakenOS system
       units).
   * - :math:`k`
     - Vacuum wavenumber, :math:`k = 2\pi/\lambda`.
   * - :math:`n_{1}, n_{2}`
     - Refractive indices on the incident and transmitted sides of an
       interface.
   * - :math:`F/\#`
     - Working F-number, :math:`F/\# = f' / D_{\mathrm{EP}}`.
   * - :math:`f, f'`
     - Front / rear effective focal lengths
       (``PupilCalc.PPP``, ``PupilCalc.EFFL``).
   * - :math:`D_{\mathrm{stop}}, D_{\mathrm{EP}}, D_{\mathrm{XP}}`
     - Diameters of the aperture stop, entrance pupil and exit pupil.
   * - :math:`W(u, v)`
     - Optical-path-difference (OPD) wavefront in the exit pupil, in waves
       (multiples of :math:`\lambda`) or in millimetres depending on the
       plot.
   * - :math:`P(u, v)`
     - Pupil-amplitude function. Unit on the open pupil, zero outside;
       complex-valued if apodization or polarization loss is included.
   * - :math:`z`
     - Axial distance from the exit pupil to the image plane.
   * - :math:`\boldsymbol{\nu} = (\nu_{x}, \nu_{y})`
     - Spatial frequency vector on the image plane (cycles / mm).
   * - :math:`\nu_{c}`
     - Diffraction cut-off frequency, :math:`\nu_{c} = 1/(\lambda\,F/\#)`.
   * - :math:`E(x, y)`
     - Complex scalar field amplitude on a surface; irradiance is
       :math:`|E|^{2}`.
   * - :math:`w_{i}`
     - Radiometric weight (power, or :math:`|E|^{2}\,\Delta A`) carried by
       traced ray :math:`i`.
   * - :math:`\mathrm{OPL}_{i}`
     - Optical path length accumulated by ray :math:`i` along its path,
       :math:`\mathrm{OPL}_{i} = \sum_{\ell} n_{\ell}\,s_{\ell}`.
   * - :math:`\langle \cdot \rangle`
     - Average of the quantity over the pupil area (or the relevant
       integration domain).

.. contents::
   :local:
   :depth: 1


Geometric image quality
-----------------------

.. _analysis-spot:

Spot — Spot Diagram
~~~~~~~~~~~~~~~~~~~

Plots ray intercepts at the analysis surface (or the system image plane)
for the currently selected fields and wavelengths. For :math:`N` traced rays
with hit coordinates :math:`(x_i, y_i)` the centroid and geometric RMS spot
radius are

.. math::

   \bar{x} = \frac{1}{N}\sum_i x_i, \quad
   \bar{y} = \frac{1}{N}\sum_i y_i, \quad
   \sigma_{\mathrm{RMS}}
   = \sqrt{\frac{1}{N}\sum_i \bigl[(x_i-\bar{x})^2 + (y_i-\bar{y})^2\bigr]}.

where

* :math:`N` is the number of rays that reached the analysis surface
  (after vignetting),
* :math:`(x_i, y_i)` are the image-plane coordinates of ray :math:`i` (mm),
* :math:`(\bar{x}, \bar{y})` is the unweighted spot centroid (mm),
* :math:`\sigma_{\mathrm{RMS}}` is the geometric RMS spot radius (mm).

The geometric reference is the **Airy radius**

.. math::

   r_{\mathrm{Airy}} = 1.22\,\lambda\,F/\#,

where :math:`\lambda` is the wavelength and :math:`F/\#` the working
F-number. When :math:`\sigma_{\mathrm{RMS}} \lesssim r_{\mathrm{Airy}}` the
spot is dominated by diffraction rather than geometric aberration.

.. figure:: ../_static/manual/analysis_tools/01_spot.svg
   :alt: Spot diagram on the image plane
   :align: center
   :width: 360px


.. _analysis-rms:

RMS — RMS Spot Radius
~~~~~~~~~~~~~~~~~~~~~

Computes :math:`\sigma_{\mathrm{RMS}}(h)` for a swept field point :math:`h`
and plots one curve per wavelength,

.. math::

   \sigma_{\mathrm{RMS}}(h; \lambda)
   = \sqrt{\frac{1}{N(h, \lambda)}\sum_i
       \bigl[(x_i - \bar{x})^{2} + (y_i - \bar{y})^{2}\bigr]},

where

* :math:`h` is the field magnitude (image height in mm for finite objects,
  field angle in degrees for objects at infinity — see ``Pup.FieldType``),
* :math:`\lambda` is the wavelength of the traced bundle,
* :math:`N(h, \lambda)` is the number of rays that reach the image at that
  field/wavelength,
* :math:`(x_{i}, y_{i})` and :math:`(\bar{x}, \bar{y})` are defined as in
  :ref:`analysis-spot`.

Useful as a quick proxy for image quality across the field without forming
a full PSF.

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

where

* :math:`(x, y)` are the Cartesian image-plane coordinates (mm),
* :math:`(u, v)` are normalised exit-pupil coordinates,
* :math:`P(u, v)` is the pupil-amplitude function (1 inside the pupil,
  0 outside, optionally complex if apodization / polarization losses are
  included),
* :math:`W(u, v)` is the OPD wavefront in the exit pupil (mm),
* :math:`k = 2\pi/\lambda` is the vacuum wavenumber,
* :math:`\lambda` is the wavelength (mm),
* :math:`z` is the axial distance from exit pupil to image plane (mm).

The diffraction-limited case (:math:`W \equiv 0`) is the Airy pattern with
central radius

.. math::

   r_{\mathrm{Airy}} = 1.22\,\lambda\,F/\#,

with :math:`F/\#` the working F-number of the converging bundle.

.. figure:: ../_static/manual/analysis_tools/03_psf.svg
   :alt: Schematic Airy-like PSF
   :align: center
   :width: 360px


.. _analysis-mtf:

MTF — Modulation Transfer Function
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Magnitude of the Optical Transfer Function (OTF), which is the
autocorrelation of the generalised pupil:

.. math::

   \mathrm{OTF}(\boldsymbol{\nu})
   = \frac{\iint P(\mathbf{u})\,e^{i k W(\mathbf{u})}\,
                 P^{\!*}(\mathbf{u} - \lambda z\boldsymbol{\nu})\,
                 e^{-i k W(\mathbf{u} - \lambda z\boldsymbol{\nu})}\,
                 \mathrm{d}\mathbf{u}}
          {\iint |P(\mathbf{u})|^{2}\,\mathrm{d}\mathbf{u}},
   \qquad
   \mathrm{MTF}(\boldsymbol{\nu}) = |\mathrm{OTF}(\boldsymbol{\nu})|,

where

* :math:`\mathbf{u} = (u, v)` are exit-pupil coordinates (mm),
* :math:`\boldsymbol{\nu} = (\nu_{x}, \nu_{y})` is the spatial-frequency
  vector on the image plane (cycles / mm),
* :math:`P(\mathbf{u})` is the pupil-amplitude function and
  :math:`P^{*}` its complex conjugate,
* :math:`W(\mathbf{u})` is the wavefront error (mm),
* :math:`k = 2\pi/\lambda`, :math:`\lambda` is the wavelength (mm),
* :math:`z` is the exit-pupil-to-image distance (mm),
* :math:`|\mathrm{OTF}(\boldsymbol{\nu})|` is the contrast transmission at
  frequency :math:`\boldsymbol{\nu}`.

For a clear circular pupil the diffraction-limited MTF is

.. math::

   \mathrm{MTF}_{\mathrm{DL}}(\nu)
     = \frac{2}{\pi}\!\left[\phi - \cos\phi\,\sin\phi\right],
   \qquad \phi = \arccos\!\left(\nu / \nu_{c}\right),

where

* :math:`\nu = |\boldsymbol{\nu}|` is the radial spatial frequency
  (cycles / mm),
* :math:`\nu_{c} = 1/(\lambda\,F/\#)` is the **diffraction cut-off
  frequency** (cycles / mm),
* :math:`\phi` is an auxiliary angle obtained from the cut-off-normalised
  frequency, in radians.

KrakenOS plots both tangential and sagittal MTF along with the
diffraction-limited reference.

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

   m_{\mathrm{enter}} = \frac{\theta_{0}}{\theta_{\mathrm{stop}}},
   \qquad
   m_{\mathrm{exit}}  = \frac{\theta_{0}}{\theta_{\mathrm{image}}},

where

* :math:`\theta_{0}` is the half-angle subtended at the object by a small
  fan of rays launched from the optical axis (radians),
* :math:`\theta_{\mathrm{stop}}` is the half-angle the same fan subtends
  at the **aperture-stop surface** after being traced through the
  upstream optics,
* :math:`\theta_{\mathrm{image}}` is the half-angle the fan subtends at
  the final image surface after the full system trace,
* :math:`m_{\mathrm{enter}}` and :math:`m_{\mathrm{exit}}` are therefore
  the **angular magnifications** from object space to the stop and from
  object space to image space.

See ``PupilCalc.__init__`` in ``KrakenOS/PupilTool.py`` for the explicit
fan-of-rays construction. With a measured stop diameter
:math:`D_{\mathrm{stop}}`,

.. math::

   D_{\mathrm{EP}} = D_{\mathrm{stop}} / m_{\mathrm{enter}},
   \qquad
   D_{\mathrm{XP}} = D_{\mathrm{stop}} \cdot m_{\mathrm{exit}},

where

* :math:`D_{\mathrm{stop}}` is the clear-aperture diameter of the physical
  stop surface (mm),
* :math:`D_{\mathrm{EP}}` is the **entrance-pupil diameter** (mm) — the
  image of the stop as seen from object space,
* :math:`D_{\mathrm{XP}}` is the **exit-pupil diameter** (mm) — the image
  of the stop as seen from image space.

.. figure:: ../_static/manual/analysis_tools/05_pupil.svg
   :alt: Pupil diagnostic showing EP, Stop, and XP markers
   :align: center
   :width: 360px


.. _analysis-seidel:

Seidel — Seidel Aberrations
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Per-surface sums of the third-order monochromatic aberration coefficients
:math:`S_{\mathrm{I}}..S_{\mathrm{V}}` and the first-order chromatic terms
:math:`C_{\mathrm{I}}, C_{\mathrm{II}}`. The total wavefront aberration of
the system as a polynomial in pupil and field is

.. math::

   W(u, v; h)
   \;\sim\; S_{\mathrm{I}}\,\rho^{4}
   + S_{\mathrm{II}}\,h\,\rho^{3}\cos\theta
   + S_{\mathrm{III}}\,h^{2}\,\rho^{2}\cos^{2}\theta
   + S_{\mathrm{IV}}\,h^{2}\,\rho^{2}
   + S_{\mathrm{V}}\,h^{3}\,\rho\cos\theta,

where

* :math:`W(u, v; h)` is the OPD wavefront in the exit pupil for field
  :math:`h` (waves),
* :math:`(u, v)` are normalised pupil coordinates and
  :math:`(\rho, \theta)` their polar form
  (:math:`\rho^{2} = u^{2} + v^{2}`, :math:`\theta = \arg(u + i v)`),
* :math:`h` is the field magnitude (image height or field angle),
* :math:`S_{\mathrm{I}}` is the **spherical-aberration** coefficient
  (:math:`\rho^{4}` term),
* :math:`S_{\mathrm{II}}` is the **coma** coefficient (:math:`h \rho^{3}`
  term),
* :math:`S_{\mathrm{III}}` is the **astigmatism** coefficient
  (:math:`h^{2} \rho^{2}\cos^{2}\theta` term),
* :math:`S_{\mathrm{IV}}` is the **Petzval field-curvature** coefficient
  (:math:`h^{2} \rho^{2}` term),
* :math:`S_{\mathrm{V}}` is the **distortion** coefficient (:math:`h^{3}
  \rho` term),
* :math:`C_{\mathrm{I}}, C_{\mathrm{II}}` are the **axial** and **lateral
  chromatic** aberration coefficients (not shown in the polynomial above
  because they describe wavelength-dependent focal-length and
  magnification shifts rather than monochromatic OPD).

Each :math:`S_{k}` is a sum over surfaces; KrakenOS plots the per-surface
bars so the dominant contributor can be identified.

.. figure:: ../_static/manual/analysis_tools/06_seidel.svg
   :alt: Bar chart of Seidel + chromatic aberration contributions
   :align: center
   :width: 360px


.. _analysis-wfront:

WFront — Wavefront Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Computes the OPD :math:`W(u, v)` of every traced ray relative to a
reference sphere centred on the chief-ray intercept and plots a slice (or
the full 2D map — see :ref:`WfeMap <analysis-wfemap>`). The key scalar
summaries are

.. math::

   \mathrm{PV}  = \max(W) - \min(W),
   \qquad
   \mathrm{RMS} = \sqrt{\langle\,(W - \langle W\rangle)^{2}\,\rangle},

where

* :math:`W(u, v)` is the OPD wavefront in the exit pupil (waves),
* :math:`\max(W), \min(W)` are the maximum and minimum of :math:`W`
  over the pupil,
* :math:`\mathrm{PV}` is the **peak-to-valley** wavefront error (waves),
* :math:`\langle W \rangle = \frac{1}{\pi}\!\iint_{u^{2}+v^{2}\le 1}
  W(u, v)\,\mathrm{d}u\,\mathrm{d}v` is the area-average of :math:`W` over
  the pupil,
* :math:`\mathrm{RMS}` is the root-mean-square wavefront error (waves).

The **Maréchal approximation** links RMS to the Strehl ratio in the
small-aberration limit (:math:`\mathrm{RMS}\lesssim \lambda/14`):

.. math::

   S \;\approx\; \exp\!\bigl[-(2\pi\,\mathrm{RMS}/\lambda)^{2}\bigr],

where

* :math:`S` is the **Strehl ratio**, the on-axis PSF intensity normalised
  to the diffraction-limited value (dimensionless, :math:`0 < S \le 1`),
* :math:`\mathrm{RMS}` and :math:`\lambda` carry the same units (both in
  mm, or both in waves with :math:`\lambda = 1`).

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
   \qquad
   Z_{n}^{m}(\rho, \theta)
   = R_{n}^{|m|}(\rho)\!\cdot\!
     \begin{cases}\cos(m\,\theta), & m \ge 0\\
                  \sin(|m|\,\theta), & m < 0,\end{cases}

where

* :math:`(\rho, \theta)` are polar pupil coordinates, :math:`0 \le \rho
  \le 1`, :math:`0 \le \theta < 2\pi`,
* :math:`j` is the single-index ordering of the Zernike polynomials
  (Noll, OSA, or Fringe — KrakenOS reports which convention is used),
* :math:`n` is the **radial order** (non-negative integer),
* :math:`m` is the **azimuthal frequency**, an integer with
  :math:`|m| \le n` and :math:`n - |m|` even,
* :math:`Z_{n}^{m}(\rho, \theta)` is the Zernike polynomial of order
  :math:`(n, m)`,
* :math:`a_{j}` is the **expansion coefficient** of mode :math:`j`
  (waves), and is the quantity plotted in the bar chart.

The radial part :math:`R_{n}^{|m|}(\rho)` is

.. math::

   R_{n}^{|m|}(\rho)
   = \sum_{s=0}^{(n-|m|)/2}
     \frac{(-1)^{s}\,(n-s)!}{s!\,\bigl((n+|m|)/2 - s\bigr)!\,
                              \bigl((n-|m|)/2 - s\bigr)!}\;
     \rho^{n - 2s},

where :math:`s` is the dummy summation index (kept separate from the
wavenumber :math:`k`). Coefficients :math:`a_{j}` are recovered by a
linear least-squares fit to the sampled wavefront and displayed both as a
bar chart and as a colour map of :math:`W(\rho, \theta)`.

.. figure:: ../_static/manual/analysis_tools/08_zernike.svg
   :alt: Zernike disk and coefficient bar chart
   :align: center
   :width: 360px


Field-dependent metrics
-----------------------

.. _analysis-fc-dist:

FC/Dist — Field Curvature / Distortion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Two coupled plots:

* **Field curvature** — the focus shift
  :math:`\Delta z_{\mathrm{focus}}(h) = z_{\mathrm{best}}(h) -
  z_{\mathrm{paraxial}}`, split into **tangential** (T, meridional fan
  best focus) and **sagittal** (S, sagittal fan best focus) branches;
  :math:`z_{\mathrm{best}}(h)` is the axial position of the
  minimum-spot-radius image surface at field :math:`h`,
  :math:`z_{\mathrm{paraxial}}` is the paraxial image-plane position.
* **Distortion** — the radial deviation of the real image height from the
  paraxial value:

.. math::

   \mathrm{distortion}(h)
   = \frac{h_{\mathrm{real}}(h) - h_{\mathrm{paraxial}}(h)}
          {h_{\mathrm{paraxial}}(h)} \times 100\,\%,

where

* :math:`h` is the (paraxial-defined) field magnitude — image height in
  mm for a finite object, or field angle in degrees for an object at
  infinity,
* :math:`h_{\mathrm{paraxial}}(h)` is the image height predicted by the
  paraxial (first-order) trace,
* :math:`h_{\mathrm{real}}(h)` is the chief-ray landing height obtained
  by the full real-ray trace,
* :math:`\mathrm{distortion}(h)` is the dimensionless percentage by which
  the real image deviates radially from the paraxial position.

.. figure:: ../_static/manual/analysis_tools/09_field_curvature.svg
   :alt: Field curvature S/T branches and distortion curve
   :align: center
   :width: 360px


.. _analysis-illum:

Illum — Relative Illumination
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Image-plane irradiance normalised to the on-axis value:

.. math::

   \mathrm{RI}(\theta) = \frac{E(\theta)}{E(0)},

where

* :math:`\theta` is the **chief-ray field angle** as measured from the
  optical axis (degrees or radians),
* :math:`E(\theta)` is the image-plane irradiance (W / mm²) at the
  chief-ray landing point for field angle :math:`\theta`,
* :math:`E(0)` is the on-axis irradiance,
* :math:`\mathrm{RI}(\theta)` is the **relative illumination**, a
  dimensionless ratio in :math:`[0, 1]`.

For an ideal lens with no vignetting, geometric considerations yield the
classical **cos⁴ law**:

.. math::

   \mathrm{RI}_{\mathrm{ideal}}(\theta) = \cos^{4}\theta.

The four cosine factors come from (i) projection of the entrance-pupil
area, (ii) the inverse-square spread of pupil-to-image distance, (iii)
projection of the image-pixel area, and (iv) the Lambertian cosine of
incidence at the detector. KrakenOS overlays the measured curve, which
also captures vignetting and pupil aberration, on top of that reference.

.. figure:: ../_static/manual/analysis_tools/10_illumination.svg
   :alt: cos^4 ideal curve and measured RI vs field
   :align: center
   :width: 360px


.. _analysis-latclr:

LatClr — Lateral Color
~~~~~~~~~~~~~~~~~~~~~~

The transverse separation of chief-ray landing points between wavelengths,

.. math::

   \Delta y_{\mathrm{lat}}(\lambda; h)
   = y_{\mathrm{chief}}(\lambda, h) - y_{\mathrm{chief}}(\lambda_{0}, h),

where

* :math:`h` is the field magnitude (image height or field angle),
* :math:`\lambda` is the wavelength of the traced ray (mm),
* :math:`\lambda_{0}` is the **reference wavelength** against which other
  wavelengths are compared (typically the primary wavelength in the
  current spectrum),
* :math:`y_{\mathrm{chief}}(\lambda, h)` is the image-plane :math:`y`
  coordinate of the chief ray for field :math:`h` at wavelength
  :math:`\lambda` (mm),
* :math:`\Delta y_{\mathrm{lat}}(\lambda; h)` is the **lateral colour**
  at field :math:`h` for wavelength :math:`\lambda` (mm); equivalently
  the chromatic difference of magnification.

The result is a coloured spread along the field direction.

.. figure:: ../_static/manual/analysis_tools/11_lateral_color.svg
   :alt: Lateral color curves for two wavelengths vs field
   :align: center
   :width: 360px


.. _analysis-pol:

Pol — Polarization
~~~~~~~~~~~~~~~~~~

Tracks the Jones state
:math:`\mathbf{E}_{\mathrm{out}} = J\,\mathbf{E}_{\mathrm{in}}` through
every interaction, applying the Fresnel coefficients at each surface,

.. math::

   r_{s} = \frac{n_{1}\cos\theta_{1} - n_{2}\cos\theta_{2}}
                {n_{1}\cos\theta_{1} + n_{2}\cos\theta_{2}},
   \qquad
   r_{p} = \frac{n_{2}\cos\theta_{1} - n_{1}\cos\theta_{2}}
                {n_{2}\cos\theta_{1} + n_{1}\cos\theta_{2}},

where

* :math:`\mathbf{E}_{\mathrm{in}}, \mathbf{E}_{\mathrm{out}}` are the
  complex Jones vectors :math:`(E_{s}, E_{p})^{T}` of the incident and
  exit electric fields, decomposed into components perpendicular
  (:math:`s`) and parallel (:math:`p`) to the local plane of incidence,
* :math:`J` is the :math:`2 \times 2` **Jones matrix** of the surface
  (or, by composition, of the whole system),
* :math:`n_{1}, n_{2}` are the refractive indices on the incident and
  transmitted sides of the interface,
* :math:`\theta_{1}` is the angle of incidence (between the ray and the
  surface normal, radians),
* :math:`\theta_{2}` is the angle of refraction, related to
  :math:`\theta_{1}` by Snell's law
  :math:`n_{1}\sin\theta_{1} = n_{2}\sin\theta_{2}`,
* :math:`r_{s}, r_{p}` are the **amplitude reflection coefficients** for
  the s- and p-polarizations; the corresponding power reflectances are
  :math:`R_{s} = |r_{s}|^{2}`, :math:`R_{p} = |r_{p}|^{2}`, and
  transmittances :math:`T_{s} = 1 - R_{s}`, :math:`T_{p} = 1 - R_{p}`.

The local s/p frame is rotated between surfaces to track polarization
through the system. KrakenOS reports transmittance, diattenuation, and
retardance; the Stokes vector

.. math::

   \mathbf{S} = (S_{0}, S_{1}, S_{2}, S_{3})

gives the **degree of polarization**

.. math::

   \mathrm{DoP} = \frac{\sqrt{S_{1}^{2} + S_{2}^{2} + S_{3}^{2}}}{S_{0}},

where

* :math:`S_{0}` is the **total irradiance** (any polarization state),
* :math:`S_{1}` is the difference between horizontal and vertical
  linearly polarized irradiance,
* :math:`S_{2}` is the difference between +45° and −45° linearly
  polarized irradiance,
* :math:`S_{3}` is the difference between right- and left-circularly
  polarized irradiance,
* :math:`\mathrm{DoP} \in [0, 1]` is the fraction of light that is
  polarized (1 = fully polarized, 0 = unpolarized).

.. figure:: ../_static/manual/analysis_tools/12_polarization.svg
   :alt: Polar transmittance curves T_s and T_p vs AOI
   :align: center
   :width: 360px


.. _analysis-atmos:

Atmos — Atmospheric Dispersion
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Bends each incoming ray by the wavelength-dependent atmospheric
refraction reported by the AstroAtmosphere library (Ref. 3). A useful
closed form is the **Cassini approximation**

.. math::

   R(z; \lambda) \;\approx\;
   A(\lambda, T, P, H, x_{c})\,\tan z
   - B(\lambda, T, P, H, x_{c})\,\tan^{3} z,

where

* :math:`R(z; \lambda)` is the **astronomical refraction**: the angular
  deviation between the true and apparent direction of a star
  (arcseconds; positive bends the apparent position towards the zenith),
* :math:`z` is the **zenith distance** of the line of sight (radians;
  :math:`z = 0` is straight up, :math:`z = 90°` is the horizon),
* :math:`\lambda` is the wavelength (µm),
* :math:`T` is the air temperature (K),
* :math:`P` is the atmospheric pressure (Pa),
* :math:`H` is the relative humidity in :math:`[0, 1]`,
* :math:`x_{c}` is the CO₂ concentration (ppm),
* :math:`A`, :math:`B` are the **first and third Cassini coefficients**
  — weak functions of :math:`\lambda`, :math:`T`, :math:`P`, :math:`H`,
  :math:`x_{c}` and geographic latitude.

KrakenOS plots one curve per wavelength and uses the same model when
``Pup.AtmosRef = 1`` in ``PupilCalc`` (with the matching
``Pup.l1, Pup.l2, Pup.T, Pup.P, Pup.H, Pup.xc, Pup.lat, Pup.h, Pup.z0``
attributes documented in :doc:`pupilcalc_tool`).

.. figure:: ../_static/manual/analysis_tools/13_atmosphere.svg
   :alt: Atmospheric refraction vs zenith distance for three wavelengths
   :align: center
   :width: 360px


Map analyses on the detector / pupil
------------------------------------

.. _analysis-psfmap:

PSFMap — Point Spread Function Map
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Renders the local PSF at a grid of field positions
:math:`(x_{f}, y_{f})` — useful for visualising how aberrations (notably
coma, astigmatism and field curvature) deform the spot across the field.
Each cell evaluates

.. math::

   \mathrm{PSF}(x, y;\, x_{f}, y_{f})
   = \Bigl|\,\mathcal{F}\!\left\{P(u, v)\,
       e^{\,i\,k\,W(u, v;\,x_{f}, y_{f})}\right\}(x, y)\,\Bigr|^{2},

where

* :math:`(x_{f}, y_{f})` are the **field-point coordinates** at which the
  local PSF is computed (object-space angles in degrees for objects at
  infinity, or object-plane heights in mm for finite objects),
* :math:`(x, y)` are the local image-plane coordinates inside one
  PSF-cell (mm),
* :math:`(u, v)` are normalised pupil coordinates,
* :math:`P(u, v)` is the pupil-amplitude function,
* :math:`W(u, v;\, x_{f}, y_{f})` is the field-dependent wavefront error
  for the chief ray of :math:`(x_{f}, y_{f})` (mm),
* :math:`k = 2\pi/\lambda` is the wavenumber,
* :math:`\mathcal{F}\{\cdot\}` denotes the 2D Fourier transform from
  pupil coordinates to image coordinates (an appropriate scale factor
  :math:`1/(\lambda z)` is absorbed into :math:`\mathcal{F}`).

.. figure:: ../_static/manual/analysis_tools/14_psf_map.svg
   :alt: Field-position grid of locally-deformed PSFs
   :align: center
   :width: 360px


.. _analysis-fldmap:

FldMap — Field Map
~~~~~~~~~~~~~~~~~~

Plots the real chief-ray image positions on a regular field grid and
overlays the paraxial / ideal grid. The pointwise displacement vector

.. math::

   \Delta\mathbf{r}(x_{f}, y_{f})
   = \mathbf{r}_{\mathrm{real}}(x_{f}, y_{f})
   - \mathbf{r}_{\mathrm{paraxial}}(x_{f}, y_{f}),

where

* :math:`(x_{f}, y_{f})` are field-grid sampling coordinates (object
  angle or object height),
* :math:`\mathbf{r}_{\mathrm{paraxial}}(x_{f}, y_{f}) = (x_{p}, y_{p})`
  is the **paraxial / ideal** image-plane landing point (mm), computed
  from the first-order matrix model,
* :math:`\mathbf{r}_{\mathrm{real}}(x_{f}, y_{f}) = (x_{r}, y_{r})` is
  the **real** chief-ray landing point (mm), obtained by tracing the
  ray through every surface,
* :math:`\Delta\mathbf{r}` is the displacement (mm) from ideal to real.

The radial component of :math:`\Delta\mathbf{r}` is distortion; the
azimuthal component captures lateral colour and field-dependent decentre.

.. figure:: ../_static/manual/analysis_tools/15_field_map.svg
   :alt: Real (red) vs paraxial (grey) image grid showing distortion
   :align: center
   :width: 360px


.. _analysis-illmap:

IllMap — Illumination Map
~~~~~~~~~~~~~~~~~~~~~~~~~

A 2D irradiance heat map on the detector,

.. math::

   E(x, y) \;=\; \frac{\mathrm{d}\Phi}{\mathrm{d}A}
           \;\approx\; \sum_{i\in\mathrm{pixel}(x, y)}
                       \frac{w_{i}\,\cos\alpha_{i}}{A_{\mathrm{pix}}},

where

* :math:`(x, y)` are the detector-plane coordinates of the pixel centre
  (mm),
* :math:`E(x, y)` is the **irradiance** on that pixel (W / mm²),
* :math:`\Phi` is the radiant power (W) and :math:`\mathrm{d}A` an area
  element of the pixel (mm²),
* :math:`\mathrm{pixel}(x, y)` is the set of traced rays whose
  intersection with the detector falls inside the pixel at
  :math:`(x, y)`,
* :math:`w_{i}` is the **per-ray radiometric weight** (W) carried by
  ray :math:`i` after all upstream transmittances, vignetting and
  apodization,
* :math:`\alpha_{i}` is the **angle of incidence** between ray
  :math:`i` and the pixel surface normal (radians); the
  :math:`\cos\alpha_{i}` factor projects the ray's power onto the pixel
  area,
* :math:`A_{\mathrm{pix}}` is the area of one pixel (mm²).

The map captures cos⁴ falloff, vignetting, caustics and lens hot-spots in
a single picture.

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

   \mathrm{PV} = \max_{u^{2}+v^{2}\le 1} W
              - \min_{u^{2}+v^{2}\le 1} W,
   \qquad
   \mathrm{RMS}^{2} = \frac{1}{\pi}\!\iint_{u^{2}+v^{2}\le 1}
       \bigl(W(u, v) - \langle W \rangle\bigr)^{2}\,\mathrm{d}u\,\mathrm{d}v,

where

* :math:`W(u, v)` is the OPD wavefront over the unit-disk exit pupil
  (waves),
* :math:`u^{2} + v^{2} \le 1` is the integration domain (open pupil),
* :math:`1/\pi` is the area of the unit disk in the denominator (so
  :math:`\langle\,\cdot\,\rangle` is a true area-average),
* :math:`\langle W \rangle =
  \frac{1}{\pi}\!\iint_{u^{2}+v^{2}\le 1} W\,\mathrm{d}u\,\mathrm{d}v`
  is the pupil-average wavefront,
* :math:`\mathrm{PV}` and :math:`\mathrm{RMS}` are as in
  :ref:`analysis-wfront`.

.. figure:: ../_static/manual/analysis_tools/17_wfe_map.svg
   :alt: 2D wavefront error map on the unit pupil
   :align: center
   :width: 360px


.. _analysis-detmap:

DetMap — Detector Power Map
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Bins the *incoherent* power of each landed ray into detector pixels:

.. math::

   P_{kl} \;=\; \sum_{i\,\in\,\mathrm{pixel}(k, l)} w_{i},

where

* :math:`(k, l)` are the integer **column / row indices** of a detector
  pixel,
* :math:`\mathrm{pixel}(k, l)` is the set of traced rays whose detector
  intersection falls into that pixel,
* :math:`w_{i}` is the radiometric weight (W) carried by ray :math:`i`
  after all upstream losses,
* :math:`P_{kl}` is the **total incoherent power** (W) deposited in
  pixel :math:`(k, l)`.

Used for radiometric / throughput analyses and to detect stray-light
hot spots. ``CohDet`` (next) replaces the sum with a coherent one.

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

   I_{kl} \;=\; \Bigl|\,\sum_{i\,\in\,\mathrm{pixel}(k, l)}
       \sqrt{w_{i}}\;
       \exp\!\bigl[\,i\,(k_{\lambda}\,\mathrm{OPL}_{i} + \varphi_{i})\bigr]
       \,\Bigr|^{2},

where

* :math:`(k, l)` are the detector-pixel indices (same as in DetMap),
* :math:`\mathrm{pixel}(k, l)` is the set of rays landing in that pixel,
* :math:`w_{i}` is ray :math:`i`'s radiometric weight; its square root
  acts as a complex-amplitude magnitude,
* :math:`k_{\lambda} = 2\pi/\lambda` is the wavenumber (the subscript
  :math:`\lambda` distinguishes it from the pixel index :math:`k`),
* :math:`\mathrm{OPL}_{i} = \sum_{\ell} n_{\ell}\,s_{\ell}` is the
  optical path length accumulated along ray :math:`i` over all segments,
  with :math:`n_{\ell}` the segment index and :math:`s_{\ell}` the
  segment geometric length (mm),
* :math:`\varphi_{i}` is any additional phase picked up by ray :math:`i`
  (e.g. Fresnel reflection phase, polarization rotation, grating order
  phase), in radians,
* :math:`I_{kl}` is the resulting **coherent intensity** in pixel
  :math:`(k, l)` (W).

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

For Gaussian-branch sources, plots the on-axis intensity :math:`|E(x)|^{2}`
and phase :math:`\arg E(x)` of the propagated field along the current
branch, together with a fitted TEM₀₀ Hermite–Gauss template. The
mode-overlap efficiency is

.. math::

   \eta \;=\; \frac{\bigl|\!\int E^{*}(x)\,u_{\mathrm{TEM}_{00}}(x)\,
                              \mathrm{d}A\bigr|^{2}}
                   {\bigl(\!\int |E(x)|^{2}\,\mathrm{d}A\bigr) \cdot
                    \bigl(\!\int |u_{\mathrm{TEM}_{00}}(x)|^{2}\,
                              \mathrm{d}A\bigr)},

where

* :math:`x` is the transverse coordinate on the analysis surface along
  the branch (mm),
* :math:`E(x)` is the complex scalar field of the propagated bundle on
  that surface; :math:`E^{*}` is its complex conjugate,
* :math:`u_{\mathrm{TEM}_{00}}(x)` is the **fitted TEM₀₀ template** — a
  fundamental Hermite–Gauss mode with the same wavelength, waist and
  pointing as the measured field,
* :math:`\mathrm{d}A` is an area element on the analysis surface,
* :math:`\eta \in [0, 1]` is the **mode-overlap efficiency** (also
  called the coupling efficiency): the fraction of the measured field's
  power that lies in the fundamental Gaussian mode.

.. figure:: ../_static/manual/analysis_tools/20_branch_field.svg
   :alt: Branch field intensity, phase, and TEM00 overlap template
   :align: center
   :width: 360px


.. _analysis-diffr:

Diffr — Diffraction Detector
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Computes the angular spectrum of the coherent field landing on the
detector,

.. math::

   \tilde{E}(k_{x}, k_{y})
   = \iint E(x, y)\,e^{-i(k_{x}\,x + k_{y}\,y)}\,\mathrm{d}x\,\mathrm{d}y,

where

* :math:`(x, y)` are detector-plane coordinates (mm),
* :math:`E(x, y)` is the complex scalar field on the detector (W^½ / mm),
* :math:`(k_{x}, k_{y})` are the **transverse wave-vector components**
  (rad / mm),
* :math:`\tilde{E}(k_{x}, k_{y})` is the 2D spatial Fourier transform of
  :math:`E`, i.e. the **angular spectrum**.

The plot shows :math:`|\tilde{E}(k_{x}, k_{y})|^{2}` versus angular
direction

.. math::

   (\theta_{x}, \theta_{y}) = (k_{x}, k_{y}) / k_{\lambda},

with :math:`k_{\lambda} = 2\pi/\lambda` the vacuum wavenumber and
:math:`(\theta_{x}, \theta_{y})` the corresponding propagation angles
(radians). This is the natural output for gratings, holograms and
far-field diffraction studies.

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

   I(u, v) \;=\; I_{1} + I_{2}
   + 2\sqrt{I_{1}\,I_{2}}\;
     \cos\!\left[\,\frac{2\pi}{\lambda}\,W(u, v) + \varphi_{0}\,\right],

where

* :math:`(u, v)` are normalised pupil coordinates,
* :math:`I(u, v)` is the fringe **irradiance** at the pupil sample point
  (W / mm²),
* :math:`I_{1}` is the **test-beam** irradiance (from the optical system
  under analysis),
* :math:`I_{2}` is the **reference-beam** irradiance (from the ideal
  reference arm),
* :math:`2\sqrt{I_{1}\,I_{2}}` is the **fringe-visibility envelope** for
  fully coherent interference (visibility :math:`V = 2\sqrt{I_{1}I_{2}} /
  (I_{1}+I_{2})`),
* :math:`\lambda` is the wavelength (mm),
* :math:`W(u, v)` is the OPD wavefront of the test beam relative to the
  reference (mm),
* :math:`\varphi_{0}` is a global **carrier-phase offset** (radians),
  set by the alignment of the reference arm.

Adding tilt / defocus to :math:`W` introduces straight or annular
reference fringes the way a real Twyman–Green or Fizeau interferometer
does.

.. figure:: ../_static/manual/analysis_tools/22_interferogram.svg
   :alt: Mock interferogram fringes over the pupil
   :align: center
   :width: 360px


.. _analysis-tolcmp:

TolCmp — Tolerance Compare
~~~~~~~~~~~~~~~~~~~~~~~~~~

Overlays the *nominal-design* spot diagram against the **worst**
Monte-Carlo sample from the tolerance run (see
``KrakenOS/UI/validate_tolerance_monte_carlo.py``). Each design parameter
is perturbed independently and the system is re-traced. The merit
function is

.. math::

   M(\boldsymbol{\delta})
   = \sigma_{\mathrm{RMS}}\bigl(\boldsymbol{\delta}\bigr)
   \quad\text{or}\quad
   M(\boldsymbol{\delta})
   = \mathrm{Strehl}\bigl(\boldsymbol{\delta}\bigr),

where

* :math:`\boldsymbol{\delta} = (\delta p_{1}, \delta p_{2}, \ldots,
  \delta p_{K})` is the vector of perturbations applied in one
  Monte-Carlo trial,
* :math:`p_{k}` is the :math:`k`-th design parameter (e.g. surface
  radius, thickness, decentre, tilt, refractive index),
* :math:`\delta p_{k}` is a random draw from the tolerance distribution
  attached to :math:`p_{k}` (typically uniform or Gaussian),
* :math:`K` is the total number of toleranced parameters,
* :math:`\sigma_{\mathrm{RMS}}(\boldsymbol{\delta})` is the RMS spot
  radius of the perturbed system at the test field (mm; lower is
  better),
* :math:`\mathrm{Strehl}(\boldsymbol{\delta})` is the on-axis Strehl
  ratio of the perturbed system (dimensionless; higher is better),
* :math:`M(\boldsymbol{\delta})` is the chosen merit function for the
  trial.

Many trials are run; the worst (highest :math:`\sigma_{\mathrm{RMS}}` /
lowest :math:`\mathrm{Strehl}`) sample is shown overlaid on the nominal
cluster.

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
