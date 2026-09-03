Chapter 4: Fourier Optics
=========================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 4.  Fourier frequency is in cycles per unit length.

Figure 4.0-2 worked example: decomposing a picture
---------------------------------------------------

Textbook Figure 4.0-2 says that an arbitrary two-dimensional function is a
sum of spatial harmonics.  The schematic is exact, but it leaves an important
practical question unanswered: **how many harmonics does one picture have?**

The answer depends first on whether the picture is continuous or sampled.
A continuous function :math:`f(x,y)` generally requires the continuum of a
two-dimensional Fourier integral, so there is no finite component count.  A
sampled :math:`N_x\times N_y` picture instead has a finite two-dimensional
discrete Fourier transform (DFT):

.. math::
   :label: fop-figure-4-0-2-dft

   F[p,q]
   &=\sum_{n=0}^{N_y-1}\sum_{m=0}^{N_x-1}
     f[n,m]\exp\!\left[-j2\pi\left(
       \frac{qm}{N_x}+\frac{pn}{N_y}\right)\right],\\
   f[n,m]
   &=\frac{1}{N_xN_y}
     \sum_{p=0}^{N_y-1}\sum_{q=0}^{N_x-1}
     F[p,q]\exp\!\left[+j2\pi\left(
       \frac{qm}{N_x}+\frac{pn}{N_y}\right)\right].

Thus one complex spatial-harmonic component is

.. math::
   :label: fop-figure-4-0-2-one-component

   h_{p,q}[n,m]
   =\frac{F[p,q]}{N_xN_y}
    \exp\!\left[+j2\pi\left(
      \frac{qm}{N_x}+\frac{pn}{N_y}\right)\right].

NumPy uses the signs displayed above.  The textbook writes the spatial
harmonic with the opposite sign; relabeling :math:`(p,q)` as
:math:`(-p,-q)` makes the two conventions identical and does not change any
amplitude, energy, or component count.

The arbitrary test picture below is a reproducible grayscale landscape with
:math:`N_x=256` columns and :math:`N_y=128` rows.  It was generated for this
example rather than copied from the textbook or an external photograph.

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/fourier_picture_decomposition/figure_4_0_2_fourier_decomposition.png
   :alt: A grayscale landscape, its two-dimensional Fourier spectrum, cumulative spectral energy, and four progressively more detailed reconstructions
   :align: center
   :width: 100%

   **Worked decomposition of textbook Figure 4.0-2.**  The upper row shows
   the sampled picture, centered log-magnitude spectrum, cumulative energy,
   and the DC component alone.  The lower row reconstructs the picture after
   retaining the strongest conjugate-paired real harmonics.  Low-frequency
   terms establish average brightness and broad gradients; many weaker
   high-frequency terms restore edges and fine texture.

Exact count
^^^^^^^^^^^

The DFT array contains exactly

.. math::
   :label: fop-figure-4-0-2-exact-count

   N_{\mathrm{complex}}=N_xN_y=256(128)=\boxed{32{,}768}

complex coefficients.  For this generated picture, all 32,768 coefficients
are nonzero above a numerical tolerance of :math:`10^{-12}` times the largest
coefficient.  Exact zeros are possible for specially symmetric pictures, but
the DFT still has 32,768 available harmonic slots and exact reconstruction
uses the complete array.

Because the picture is real valued,
:math:`F[-p,-q]=F^*[p,q]`.  Most complex exponentials therefore occur in
conjugate pairs that combine into one real cosine with an amplitude and a
phase.  Since both dimensions are even, four bins are self-conjugate: the DC
bin and the three combinations of horizontal and vertical Nyquist frequency.
The independent real-harmonic group count is consequently

.. math::
   :label: fop-figure-4-0-2-real-count

   N_{\mathrm{real\ groups}}
   =\frac{32{,}768-4}{2}+4
   =\boxed{16{,}386}.

The two boxed numbers answer different conventions:

* **32,768 complex spatial harmonics** is the direct answer in the complex
  exponential language used by textbook Figure 4.0-2.
* **16,386 real-harmonic groups** is the same information after conjugate
  partners are combined into real cosines.

For an RGB picture of the same size treated as three separate channels, the
direct count would be :math:`3(32{,}768)=98{,}304` complex channel
coefficients.  The pixel pitch is not specified here, so frequencies are in
cycles/pixel.  For physical pitches :math:`\Delta x` and :math:`\Delta y`, a
signed DFT bin :math:`(\widetilde q,\widetilde p)` represents
:math:`\nu_x=\widetilde q/(N_x\Delta x)` and
:math:`\nu_y=\widetilde p/(N_y\Delta y)`.

How many are needed for a recognizable picture?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

There is no unique number until an error or retained-energy criterion is
chosen.  Parseval's theorem makes the coefficient energy
:math:`|F[p,q]|^2`.  Sorting conjugate pairs by their combined energy gives
the following minimum counts for this particular picture:

.. list-table:: Minimum harmonic counts at selected energy thresholds
   :header-rows: 1
   :widths: 14 20 20 23 23

   * - Energy target
     - Total-intensity groups
     - Complex coefficients
     - Contrast-only groups
     - Contrast coefficients
   * - 90%
     - 2
     - 3
     - 96
     - 192
   * - 95%
     - 3
     - 5
     - 324
     - 648
   * - 99%
     - 142
     - 283
     - 3,225
     - 6,448
   * - 99.9%
     - 3,965
     - 7,927
     - 10,785
     - 21,568

The total-intensity columns include DC.  The contrast columns first subtract
the mean brightness and measure only non-DC energy; add the one DC group when
forming a normally illuminated reconstruction.  This is why “90% energy” can
be misleading: DC and a broad vertical gradient contain much of the raw
numerical energy even though they do not yet make the scene recognizable.
The 99% and 99.9% reconstructions show the more useful practical progression.

What do individual components look like?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/fourier_picture_decomposition/figure_4_0_2_strongest_harmonics.png
   :alt: Eight sinusoidal patterns corresponding to the strongest non-DC spatial harmonics in the example picture
   :align: center
   :width: 100%

   **Eight strongest non-DC real harmonics.**  Each panel is one conjugate
   pair reconstructed by itself.  It is independently normalized so that its
   stripe orientation and period remain visible; the percentages in the
   titles, not the displayed color scale, give their true relative energy.
   Vertical variation in the scene produces horizontal stripes, horizontal
   variation produces vertical stripes, and simultaneous :math:`x` and
   :math:`y` variation produces diagonal stripes.

The complete picture is not stored inside any one component.  Every harmonic
extends across the whole image; localized mountains, trees, the house, and
the boat emerge only after many different amplitudes and phases are added.
The figures and counts are reproducible with
``docs/generate_fourier_picture_decomposition.py``.

Section 4.4: why the aperture advice reverses
----------------------------------------------

Two sentences in Sec. 4.4 appear to give opposite advice:

* Sec. 4.4A says that image quality may be improved with a **small aperture**.
* Example 4.4-1 in Sec. 4.4C says that a smaller F-number, and therefore a
  **larger aperture**, gives better image quality.

They do not describe the same limit.  Section A studies geometrical blur when
the system is **not in focus**.  Section C studies diffraction blur after the
system has been set **exactly in focus**.

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/aperture_tradeoff/section_4_4_aperture_tradeoff.svg
   :alt: Comparison of aperture diameter effects on ray-optics defocus blur and focused diffraction blur
   :align: center
   :width: 100%

   **Why the aperture conclusions reverse.**  On the left, the sensor is
   displaced from the true image plane, so a wider ray cone makes a wider
   geometrical patch.  On the right, the system is focused and the finite
   aperture produces diffraction; a wider aperture makes the diffraction
   spot narrower.  The colors identify the aperture cases, not two different
   wavelengths.

What Sec. 4.4A holds fixed: nonzero focusing error
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The section first says that a focused system is ideal within ray theory: each
object point maps to one image point.  It then changes the condition with the
sentence “Suppose now that the system is not in focus” and defines, in
textbook Eq. (4.4-1),

.. math::
   :label: fop-section-4-4-focusing-error

   \epsilon=\frac{1}{d_1}+\frac{1}{d_2}-\frac{1}{f}.

Here :math:`d_2` is the actual lens-to-image-plane distance.  The correctly
focused plane would instead be at :math:`d_{20}`, where
:math:`1/d_1+1/d_{20}=1/f`.  A ray passing through the aperture at radius
:math:`\rho` reaches the actual image plane at blur radius :math:`\rho_s`.
The similar-triangle calculation printed immediately below Fig. 4.4-2 gives

.. math::
   :label: fop-section-4-4-ray-scaling

   \frac{\rho_s}{\rho}
   =\frac{d_{20}-d_2}{d_{20}}
   =\epsilon d_2.

For a circular aperture, the edge ray has :math:`\rho=D/2`.  Textbook
Eq. (4.4-3) is therefore

.. math::
   :label: fop-section-4-4-geometrical-blur

   \rho_{s,\mathrm{ray}}=\frac{1}{2}\epsilon d_2D,
   \qquad
   |\rho_{s,\mathrm{ray}}|
   =\frac{1}{2}|\epsilon|d_2D.

The second form makes explicit that a physical radius is nonnegative; the
sign of :math:`\epsilon` identifies which side of focus contains the image
plane.  With :math:`\epsilon\ne0` and :math:`d_2` held fixed,

.. math::
   :label: fop-section-4-4-small-aperture-scaling

   |\rho_{s,\mathrm{ray}}|\propto D.

Halving :math:`D` halves this geometrical defocus patch.  This is the precise
reason Sec. 4.4A associates a small aperture with reduced sensitivity to
focusing error and increased depth of focus.  If :math:`\epsilon=0`, however,
Eq. :eq:`fop-section-4-4-geometrical-blur` gives zero ray-optics blur for
**every** aperture diameter.  The ray model then has nothing more to say
about the spot size.

What Example 4.4-1 holds fixed: exact focus
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Section 4.4C first defines the generalized pupil in textbook Eq. (4.4-10):

.. math::
   :label: fop-section-4-4-generalized-pupil

   p_1(x,y)=p(x,y)
   \exp\!\left[-j\pi\epsilon\frac{x^2+y^2}{\lambda}\right].

Immediately before Example 4.4-1, the book explicitly sets
:math:`\epsilon=0`; hence :math:`p_1=p`.  The example title also specifies a
“Focused Imaging System.”  The geometrical defocus term has therefore been
removed before the circular-aperture result is calculated.

For a circular pupil of diameter :math:`D`, textbook Eq. (4.4-13) gives the
focused amplitude impulse response

.. math::
   :label: fop-section-4-4-circular-impulse-response

   h(x,y)=h(0,0)
   \frac{2J_1(\pi D\rho/\lambda d_2)}
        {\pi D\rho/\lambda d_2},
   \qquad \rho=\sqrt{x^2+y^2}.

Its first zero occurs at the radius in textbook Eq. (4.4-14),

.. math::
   :label: fop-section-4-4-diffraction-blur

   \rho_{s,\mathrm{wave}}=1.22\frac{\lambda d_2}{D}.

For focus at infinity, :math:`d_1=\infty` and :math:`d_2=f`, so textbook
Eq. (4.4-15) becomes

.. math::
   :label: fop-section-4-4-f-number-blur

   \rho_{s,\mathrm{wave}}
   =1.22\lambda\frac{f}{D}
   =1.22\lambda F\#,
   \qquad F\#=\frac{f}{D}.

With :math:`\lambda` and :math:`d_2` fixed,

.. math::
   :label: fop-section-4-4-large-aperture-scaling

   \rho_{s,\mathrm{wave}}\propto\frac{1}{D}.

Halving :math:`D` now doubles the diffraction spot.  This is why the focused
wave-optics example favors a larger aperture.  The book immediately qualifies
this conclusion by requiring that the larger lens not introduce geometrical
aberrations.

Exact comparison
^^^^^^^^^^^^^^^^

.. list-table:: What changes between the two textbook conclusions
   :header-rows: 1
   :widths: 22 34 22 22

   * - Question
     - Sec. 4.4A
     - Sec. 4.4C, Example 4.4-1
     - Aperture advice
   * - Focus condition
     - Defocused, :math:`\epsilon\ne0`
     - Focused, :math:`\epsilon=0`
     - Different conditions
   * - Optical description
     - Ray optics
     - Wave optics
     - Different models
   * - Source of finite spot
     - Aperture shadow at the wrong image plane
     - Diffraction of a circular pupil at the correct image plane
     - Different mechanisms
   * - Radius scaling
     - :math:`|\rho_s|\propto D`
     - :math:`\rho_s\propto1/D`
     - Small versus large
   * - What improves
     - Tolerance to focusing error; depth of focus
     - Focused resolving power when geometrical aberrations remain negligible
     - Different performance limits

.. important::

   **The exact distinction is not merely “ray optics versus wave optics.”**
   It is also :math:`\epsilon\ne0` versus :math:`\epsilon=0`, meaning an
   incorrectly located image plane versus the correctly focused plane.  The
   aperture diameter :math:`D` is the same kind of quantity in both formulas,
   but the finite spot has a different cause.

When both finite aperture and defocus are present, Sec. 4.4C points back to
the generalized pupil :eq:`fop-section-4-4-generalized-pupil`: the pupil
boundary supplies diffraction while its quadratic phase contains the
focusing error.  Therefore, the two limiting sentences alone do not imply a
universal best aperture and their two spot radii should not simply be added.
The generalized pupil must be propagated for the specified
:math:`D`, :math:`\epsilon`, :math:`\lambda`, and :math:`d_2`.

In-text exercises
-----------------

Exercise 4.1-1 — Binary Fresnel plate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-4-1-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_04_01_01.svg
   :alt: Illustrated calculation map for Exercise 4.1-1, Binary Fresnel plate
   :align: center
   :width: 95%

   **Figure 40 — Exercise 4.1-1: Binary Fresnel plate.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`Fourier-transform and convolution identities <fop-formula-fourier>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Expand the binary radial phase in a Fourier series of its quadratic-phase
coordinate.  Its constant term is an unfocused order; harmonics
:math:`e^{-jqk x^2/(2f)}` are cylindrical-lens phases.  Thus the orders focus
at :math:`\boxed{\infty,\ \pm f,\ \pm f/2,\ldots}`; Fourier coefficients set
their amplitudes.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-4-1-1-result

   \boxed{\infty,\ \pm f,\ \pm f/2,\ldots}


**Step 5 — Check.**  Equation :eq:`fop-exercise-4-1-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.

Exercise 4.1-2 — Gaussian propagation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-4-1-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_04_01_02.svg
   :alt: Illustrated calculation map for Exercise 4.1-2, Gaussian propagation
   :align: center
   :width: 95%

   **Figure 41 — Exercise 4.1-2: Gaussian propagation.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`Fourier-transform and convolution identities <fop-formula-fourier>`, :ref:`integration identities <fop-formula-integration>`, and :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Fourier transforming :math:`e^{-\rho^2/W_0^2}`, multiplying by the paraxial
free-space transfer function, and transforming back gives
:math:`U=A_0(q_0/q)e^{-jkz}e^{-jk\rho^2/(2q)}` with
:math:`q=z+j\pi W_0^2/\lambda`.  Convolution with the Fresnel kernel gives the
same Gaussian integral and therefore the Chapter 3 beam.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-4-1-2-result

   q=z+j\pi W_0^2/\lambda


**Step 5 — Check.**  Equation :eq:`fop-exercise-4-1-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.

Exercise 4.2-1 — Fresnel versus Fraunhofer range
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-4-2-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_04_02_01.svg
   :alt: Illustrated calculation map for Exercise 4.2-1, Fresnel versus Fraunhofer range
   :align: center
   :width: 95%

   **Figure 42 — Exercise 4.2-1: Fresnel versus Fraunhofer range.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For :math:`a=0.02` m, :math:`b=0.01` m, and
:math:`\lambda=0.5\ \mathrm{\mu m}`, the Fresnel equality estimate is
:math:`d=[(a+b)^4/(4\lambda)]^{1/3}=0.740` m, so use
:math:`\boxed{d\gg0.740\ \mathrm m}`.  Fraunhofer requires both
:math:`a^2/(\lambda d)\ll1` and :math:`b^2/(\lambda d)\ll1`; the stricter is
:math:`\boxed{d\gg800\ \mathrm m}`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-4-2-1-result

   \boxed{d\gg800\ \mathrm m}


**Step 5 — Check.**  Equation :eq:`fop-exercise-4-2-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Exercise 4.2-2 — Inverse transform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-4-2-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_04_02_02.svg
   :alt: Illustrated calculation map for Exercise 4.2-2, Inverse transform
   :align: center
   :width: 95%

   **Figure 43 — Exercise 4.2-2: Inverse transform.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`Fourier-transform and convolution identities <fop-formula-fourier>` and :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The focal-plane relation samples :math:`F(\nu_x,\nu_y)` at
:math:`(x,y)/(\lambda f)`.  Reversing focal-plane coordinates changes the
kernel from :math:`e^{-j2\pi\boldsymbol\nu\cdot\mathbf r}` to
:math:`e^{+j2\pi\boldsymbol\nu\cdot\mathbf r}`, which is exactly the inverse
Fourier transform.

**Step 4 — Interpret the result.**  The final relation or conclusion in Step 3 is the requested result.  Read its sign, scale, or physical classification using the conventions fixed in Step 1.

**Step 5 — Check.**  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.

Exercise 4.3-1 — Rectangular aperture
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-4-3-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_04_03_01.svg
   :alt: Illustrated calculation map for Exercise 4.3-1, Rectangular aperture
   :align: center
   :width: 95%

   **Figure 44 — Exercise 4.3-1: Rectangular aperture.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`Fourier-transform and convolution identities <fop-formula-fourier>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The transform of :math:`\operatorname{rect}(x/D_x)
\operatorname{rect}(y/D_y)` is
:math:`D_xD_y\operatorname{sinc}(D_x\nu_x)
\operatorname{sinc}(D_y\nu_y)`.  Squaring at
:math:`\nu_{x,y}=(x,y)/(\lambda d)` gives Eq. (4.3-6), with first zeros
:math:`x=\pm\lambda d/D_x`, :math:`y=\pm\lambda d/D_y`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-4-3-1-result

   y=\pm\lambda d/D_y


**Step 5 — Check.**  Equation :eq:`fop-exercise-4-3-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.

Exercise 4.3-2 — Circular aperture
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-4-3-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_04_03_02.svg
   :alt: Illustrated calculation map for Exercise 4.3-2, Circular aperture
   :align: center
   :width: 95%

   **Figure 45 — Exercise 4.3-2: Circular aperture.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`Fourier-transform and convolution identities <fop-formula-fourier>`, :ref:`integration identities <fop-formula-integration>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The polar Fourier integral gives
:math:`2J_1(\pi D\rho/\lambda d)/(\pi D\rho/\lambda d)`.  Its first numerator
zero is 3.8317, hence
:math:`\boxed{\rho_s=1.22\lambda d/D}` and
:math:`\boxed{\theta_s=1.22\lambda/D}`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-4-3-2-result

   \boxed{\theta_s=1.22\lambda/D}


**Step 5 — Check.**  Equation :eq:`fop-exercise-4-3-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.

Exercise 4.3-3 — Focused spot
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-4-3-3-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_04_03_03.svg
   :alt: Illustrated calculation map for Exercise 4.3-3, Focused spot
   :align: center
   :width: 95%

   **Figure 46 — Exercise 4.3-3: Focused spot.** The
   diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route. Every
   symbol in the variable strip is labeled on the model itself.

**Step 2 — Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Replace propagation distance by focal length in the preceding result:
:math:`\rho_s=1.22\lambda f/D`.  A Gaussian filling a clear diameter near
:math:`D\simeq2W` has :math:`W'_0=\lambda f/(\pi W)\simeq0.637\lambda f/D`;
the differing radius definitions explain the numerical factor.

End-of-chapter problems
-----------------------

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-4-3-3-result

   W'_0=\lambda f/(\pi W)\simeq0.637\lambda f/D


**Step 5 — Check.**  Equation :eq:`fop-exercise-4-3-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 4.1-3 — Harmonic propagation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Decompose each input into terms :math:`c_m e^{j2\pi(\nu_{xm}x+\nu_{ym}y)}`
and multiply by
:math:`H_m=e^{-j2\pi d\sqrt{\lambda^{-2}-\nu_{xm}^2-\nu_{ym}^2}}`.
This leaves (a) one axial plane wave; (b) one oblique wave with
:math:`(\nu_x,\nu_y)=(-1/2\lambda,-1/2\lambda)`; (c) two waves at
:math:`\nu_x=\pm1/(4\lambda)`; (d) an axial term plus two at
:math:`\nu_y=\pm1/(2\lambda)`; and (e) grating orders
:math:`\nu_x=m/(20\lambda)` weighted by the 50%-duty rectangular-cell
coefficients.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-4-1-3-result

   \nu_x=m/(20\lambda)


**Check.**  Equation :eq:`fop-problem-4-1-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Problem 4.1-4 — Direction cone
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`\sin\theta_{max}=\lambda\nu_{max}=(0.000633)(200)=0.1266`, so
:math:`\boxed{\theta_{max}=7.27^\circ}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-4-1-4-result

   \boxed{\theta_{max}=7.27^\circ}


**Check.**  Equation :eq:`fop-problem-4-1-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 4.1-5 — Logarithmic map
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, :ref:`integration identities <fop-formula-integration>`, and :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

A phase :math:`t=e^{-j2\pi\phi}` deflects by
:math:`\theta=-\lambda\phi'`.  With a lens,
:math:`\phi'=-(\ln x)/(\lambda f)`, hence
:math:`\boxed{\phi=-(x\ln x-x)/(\lambda f)+C}`.  If light instead propagates
distance :math:`f` without the lens, require
:math:`x+f\theta=\ln x`; replace the derivative by
:math:`\phi'=-(\ln x-x)/(\lambda f)` and integrate.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-4-1-5-result

   \boxed{\phi=-(x\ln x-x)/(\lambda f)+C}


**Check.**  Equation :eq:`fop-problem-4-1-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.

Problem 4.2-3 — Lens Fourier-transform proof
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`Fourier-transform and convolution identities <fop-formula-fourier>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Expand :math:`(x-x')^2=x^2+x'^2-2xx'` in the Fresnel convolution.  The two
quadratic factors surround the Fourier kernel.  In the propagation--lens--
propagation cascade the lens cancels both inner quadratic phases, leaving
:math:`g(x)=e^{-j2kf}F[x/(\lambda f)]/(j\lambda f)` up to convention phase.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-4-2-3-result

   g(x)=e^{-j2kf}F[x/(\lambda f)]/(j\lambda f)


**Check.**  Equation :eq:`fop-problem-4-2-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.

Problem 4.2-4 — Line-function transforms
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`Fourier-transform and convolution identities <fop-formula-fourier>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

(a) :math:`\delta(x-y)` is a bright diagonal in both planes, rotated to its
orthogonal Fourier line.  (b) Two lines at :math:`x=\pm a` transform to
:math:`2\cos(2\pi a\nu_x)`, giving cosine-squared fringes.  (c) Relative phase
:math:`j` changes this to :math:`e^{j2\pi a\nu_x}+j e^{-j2\pi a\nu_x}` and
shifts the fringes by one quarter period.  Use
:math:`x_f=\lambda f\nu_x`; here :math:`\lambda f=1\ \mathrm{mm^2}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-4-2-4-result

   \lambda f=1\ \mathrm{mm^2}


**Check.**  Equation :eq:`fop-problem-4-2-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 4.2-5 — Fourier-plane scale
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`Fourier-transform and convolution identities <fop-formula-fourier>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`\Delta x=\lambda f(200-20)` lines/mm.  Therefore
:math:`\boxed{f=0.09/[488\times10^{-9}(180\times10^3)]
=1.025\ \mathrm m}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-4-2-5-result

   \boxed{f=0.09/[488\times10^{-9}(180\times10^3)]
   =1.025\ \mathrm m}


**Check.**  Equation :eq:`fop-problem-4-2-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 4.3-4 — Multi-slit grating
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The field is
:math:`\sum_{m=-L}^{L}e^{-j2\pi ma\theta/\lambda}` and the intensity is

.. math::
   :label: fop-problem-4-3-4-eq-1

   \boxed{I\propto\left[
   \frac{\sin(M\pi a\theta/\lambda)}
   {\sin(\pi a\theta/\lambda)}\right]^2}.

Principal orders occur at :math:`\theta_q\simeq q\lambda/a=q/10`; adjacent
zeros are :math:`1/M` of that separation away.

**Check.**  Equation :eq:`fop-problem-4-3-4-eq-1` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

Problem 4.3-5 — Oblique Fraunhofer illumination
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The aperture field gains :math:`e^{-j2\pi\nu_{0x}x}` with
:math:`\nu_{0x}\simeq\theta_x/\lambda`.  The shift theorem gives
:math:`\boxed{I(x,y)\propto|P(x/\lambda d-\nu_{0x},y/\lambda d)|^2}`: the
entire pattern shifts by :math:`d\theta_x`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-4-3-5-result

   \boxed{I(x,y)\propto|P(x/\lambda d-\nu_{0x},y/\lambda d)|^2}


**Check.**  Equation :eq:`fop-problem-4-3-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Problem 4.3-6 — Two-pinhole Fresnel pattern
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Adding the two Fresnel kernels cancels their common phase and leaves
:math:`2\cos(2\pi ax/\lambda d)`.  Squaring gives
:math:`\boxed{I=(2/\lambda d)^2\cos^2(2\pi ax/\lambda d)}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-4-3-6-result

   \boxed{I=(2/\lambda d)^2\cos^2(2\pi ax/\lambda d)}


**Check.**  Equation :eq:`fop-problem-4-3-6-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

Problem 4.3-7 — Fresnel/Fraunhofer relation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`Fourier-transform and convolution identities <fop-formula-fourier>`, :ref:`integration identities <fop-formula-integration>`, and :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Expanding the Fresnel kernel shows that its integral is the Fourier transform
of :math:`p(x',y')e^{-j\pi(x'^2+y'^2)/(\lambda d)}` evaluated at
:math:`(x,y)/(\lambda d)`, times an output quadratic phase.  Its magnitude is
therefore the requested Fraunhofer pattern.

**Check.**  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.

Problem 4.4-1 — Blurred sinusoidal grating
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Convolving :math:`[1+\cos(4\pi x/a)]/2` with a width-:math:`D` square gives
:math:`g(x,0)=D[1+\operatorname{sinc}(2D/a)\cos(4\pi x/a)]/2` (apart from the
constant y factor).  Thus
:math:`\boxed{C=|\operatorname{sinc}(2D/a)|}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-4-4-1-result

   \boxed{C=|\operatorname{sinc}(2D/a)|}


**Check.**  Equation :eq:`fop-problem-4-4-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

Problem 4.4-2 — Phase-edge image
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Because :math:`h=\operatorname{rect}(x)\delta(y)`, the output is the running
unit-width average
:math:`g(x,y)=\int_{x-1/2}^{x+1/2}f(u,y)du`.  Far from the phase edge its
magnitude is one; while the window straddles :math:`x=0`, the two constant
phasors add in proportions :math:`1/2\pm x`.  Squaring this piecewise linear
phasor gives the nonuniform transition intensity.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-4-4-2-result

   x=0


**Check.**  Equation :eq:`fop-problem-4-4-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.

Problem 4.4-3 — Spatial filtering
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`Fourier-transform and convolution identities <fop-formula-fourier>`, :ref:`vector-calculus identities <fop-formula-vector-calculus>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

With :math:`\lambda f=1\ \mathrm{mm^2}`,
:math:`g=\mathcal F^{-1}\{F(\nu)p(\nu)\}`.  Hence (a)
:math:`g(x,0)=\operatorname{sinc}(x-5)`; (b)
:math:`g(x,0)=\operatorname{tri}(x)`.  A Laplacian filter uses
:math:`\boxed{p(x_f,y_f)=-4\pi^2(x_f^2+y_f^2)/(\lambda f)^2}` within the
available pupil.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-4-4-3-result

   \boxed{p(x_f,y_f)=-4\pi^2(x_f^2+y_f^2)/(\lambda f)^2}


**Check.**  Equation :eq:`fop-problem-4-4-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 4.4-4 — Optical cross-correlation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`Fourier-transform and convolution identities <fop-formula-fourier>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Place :math:`f_1` at the input and
:math:`F_2^*(\nu_x,\nu_y)` in the Fourier plane.  The inverse-transform plane
then contains :math:`f_1\star f_2`.  All masks can be real only when the needed
spectra have zero/constant phase (for example, real even functions); a general
real image still has a complex Fourier transform.

**Check.**  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.

Problem 4.4-5 — Severe defocus
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`stationary-value condition <fop-formula-stationary>`, :ref:`integration identities <fop-formula-integration>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

In the diffraction integral the rapidly varying phase has stationary point
:math:`(x',y')=(x/(\epsilon d_2),y/(\epsilon d_2))`.  Stationary-phase
evaluation makes all slowly varying factors constant there and gives
:math:`\boxed{h(x,y)\propto p(x/(\epsilon d_2),y/(\epsilon d_2))}` up to the
book's normalization and phase, the same geometrical pupil image.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-4-4-5-result

   \boxed{h(x,y)\propto p(x/(\epsilon d_2),y/(\epsilon d_2))}


**Check.**  Equation :eq:`fop-problem-4-4-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.

Problem 4.4-6 — Resolving two points
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`common differential-equation solutions <fop-formula-odes>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For a square pupil,
:math:`h\propto\operatorname{sinc}(Dx/\lambda d_2)
\operatorname{sinc}(Dy/\lambda d_2)`.  Two points give
:math:`g=h(x,y)+h(x-b,y)`.  With :math:`\lambda d_2/D=0.1` mm, all three
listed separations (0.5, 1, 2 mm) show two clear peaks.  Solving
:math:`g''(b/2)=0` gives the equal-phase two-peak threshold
:math:`\boxed{b\simeq0.1325\ \mathrm{mm}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-4-4-6-result

   \boxed{b\simeq0.1325\ \mathrm{mm}}


**Check.**  Equation :eq:`fop-problem-4-4-6-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiating the proposed solution and substituting it into the original differential equation verifies the functional form.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 4.4-7 — Annular pupil
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

At unit magnification :math:`d_1=d_2=2f=2` m.  The coherent transfer function
is an annulus with spatial-frequency radii
:math:`a/(\lambda d_2)=2.5` and :math:`b/(\lambda d_2)=3.0` lines/mm.  Moving
the image plane to 0.25 m maps the physical pupil by ray scale
:math:`1+d_2(1/d_1-1/f)=0.875`; the impulse response is therefore an annulus
of radii :math:`\boxed{4.375,5.250\ \mathrm{mm}}` (apart from phase and scale).

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-4-4-7-result

   \boxed{4.375,5.250\ \mathrm{mm}}


**Check.**  Equation :eq:`fop-problem-4-4-7-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

Problem 4.5-1 — Spherical-reference holography
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Record :math:`|O+R|^2=|O|^2+|R|^2+OR^*+O^*R`, using
:math:`R\propto e^{-jk\rho^2/(2d)}`.  On replay with :math:`R`, the
:math:`OR^*` term reconstructs :math:`O`; the conjugate term creates the
twin image.  A tilted plane object makes an off-axis Fresnel-zone pattern; a
displaced spherical object makes the difference of two quadratic phases and
therefore shifted zone plates whose curvature encodes :math:`d_1^{-1}-d^{-1}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-4-5-1-result

   |O+R|^2=|O|^2+|R|^2+OR^*+O^*R


**Check.**  Equation :eq:`fop-problem-4-5-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

Problem 4.5-2 — Joint-transform correlation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`Fourier-transform and convolution identities <fop-formula-fourier>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For separated inputs the recorded spectrum contains
:math:`F_1F_2^*e^{-j4\pi a\nu_x}` and its conjugate besides the two
autocorrelation terms.  A second Fourier transform produces separated peaks
:math:`f_1\star f_2` and :math:`f_2\star f_1` at :math:`x=\pm2a`; reading
either off-axis term yields the desired cross-correlation without overlap.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-4-5-2-result

   x=\pm2a


**Check.**  Equation :eq:`fop-problem-4-5-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.
