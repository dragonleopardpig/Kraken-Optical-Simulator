Chapter 7: Diffraction
======================

Source: Eugene Hecht, *Schaum's Outline of Theory and Problems of
Optics* (1975), Chapter 7.  The entries below cover only the
chapter's **Supplementary Problems**; prompts are paraphrased and are not
reproduced.

Each topic derives its shared formula once.  Every numbered problem then
applies that derivation to the particular proof, calculation, or construction
in the book.  Read the source diagram alongside entries that depend on a figure.

Radiation from a coherent line source
-------------------------------------

**Formula and definitions.**

.. math::
   :label: schaum-7-1

   I(\theta)=I_1\left[\frac{\sin(N\alpha)}{\sin\alpha}\right]^2,\qquad \alpha=\frac12(ka\sin\theta+\delta_0)

Sum the geometric phasor series
:math:`\sum_{m=0}^{N-1}e^{i2m\alpha}` and square its magnitude.  Principal
maxima occur when :math:`\alpha=q\pi`; zeros occur at the intervening
:math:`N-1` numerator zeros.  A progressive source phase shifts the whole
pattern by changing :math:`\delta_0`.

Problem 7.52 — recover Young's pattern as a two-element array
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Recover young's pattern as a two-element array.

**Formula reference.** Use :eq:`schaum-7-1` and the definitions immediately above it.

**Worked application.**

1. Insert N, spacing, wavelength, and intrinsic phase into the array factor; solve its numerator and denominator limits separately at principal maxima.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** For :math:`N=2`, :math:`\sin(2\alpha)/\sin\alpha=2\cos\alpha`; squaring yields the Young two-source :math:`4I_1\cos^2\alpha` pattern.

**Check.** The N=2 limit must equal the two-source cosine-squared pattern and the peak intensity must scale as N² for equal coherent emitters.

Problem 7.53 — count minima and subsidiary maxima between array principals
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Count minima and subsidiary maxima between array principals.

**Formula reference.** Use :eq:`schaum-7-1` and the definitions immediately above it.

**Worked application.**

1. Insert N, spacing, wavelength, and intrinsic phase into the array factor; solve its numerator and denominator limits separately at principal maxima.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** There are :math:`N-1` minima and :math:`N-2` subsidiary maxima between adjacent principal maxima.

**Check.** The N=2 limit must equal the two-source cosine-squared pattern and the peak intensity must scale as N² for equal coherent emitters.

Problem 7.54 — resolve the beam spacing and width of a thirty-two-antenna array
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Resolve the beam spacing and width of a thirty-two-antenna array.

**Formula reference.** Use :eq:`schaum-7-1` and the definitions immediately above it.

**Worked application.**

1. Insert N, spacing, wavelength, and intrinsic phase into the array factor; solve its numerator and denominator limits separately at principal maxima.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The principal-maxima spacing is about :math:`1^\circ43'`; the central peak width is about 6 arcmin.

**Check.** The N=2 limit must equal the two-source cosine-squared pattern and the peak intensity must scale as N² for equal coherent emitters.

Problem 7.55 — orient the central maximum with progressive source phase
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Orient the central maximum with progressive source phase.

**Formula reference.** Use :eq:`schaum-7-1` and the definitions immediately above it.

**Worked application.**

1. Insert N, spacing, wavelength, and intrinsic phase into the array factor; solve its numerator and denominator limits separately at principal maxima.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The zeroth maximum satisfies :math:`ka\sin\theta_0+\delta_0=0`, so :math:`\theta_0=\sin^{-1}[-\delta_0\lambda/(2\pi a)]` with sign set by the phase convention.

**Check.** The N=2 limit must equal the two-source cosine-squared pattern and the peak intensity must scale as N² for equal coherent emitters.

Problem 7.56 — calculate array steering from a thirty-degree phase increment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Calculate array steering from a thirty-degree phase increment.

**Formula reference.** Use :eq:`schaum-7-1` and the definitions immediately above it.

**Worked application.**

1. Insert N, spacing, wavelength, and intrinsic phase into the array factor; solve its numerator and denominator limits separately at principal maxima.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Substituting the 30° progressive phase into the steering equation gives the same approximately :math:`2.39^\circ` displacement as the related two-source problem.

**Check.** The N=2 limit must equal the two-source cosine-squared pattern and the peak intensity must scale as N² for equal coherent emitters.

Problem 7.57 — derive specular reflection as an atomic-array maximum
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive specular reflection as an atomic-array maximum.

**Formula reference.** Use :eq:`schaum-7-1` and the definitions immediately above it.

**Worked application.**

1. Insert N, spacing, wavelength, and intrinsic phase into the array factor; solve its numerator and denominator limits separately at principal maxima.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The incident wave induces adjacent-atom phase :math:`ka\sin\theta_i`; reradiation is principal when the outgoing path phase cancels it, requiring :math:`\theta_o=\theta_i`.

**Check.** The N=2 limit must equal the two-source cosine-squared pattern and the peak intensity must scale as N² for equal coherent emitters.

Fraunhofer diffraction by one and two narrow slits
--------------------------------------------------

**Formula and definitions.**

.. math::
   :label: schaum-7-2

   I(\theta)=I(0)\operatorname{sinc}^2\beta,\quad \beta=\frac{\pi b}{\lambda}\sin\theta,\quad b\sin\theta_m=m\lambda,\quad \Delta y\simeq\frac{\lambda f}{a}

Integrating a uniform slit gives the sinc amplitude.  Its zeros
set the diffraction envelope, while two-slit interference supplies the faster
factor :math:`\cos^2(\pi a\sin\theta/\lambda)`.  Oblique incidence replaces
:math:`\sin\theta` by the difference from the incident-direction sine.

Problem 7.58 — prove lens-position independence of focal-plane minima
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Prove lens-position independence of focal-plane minima.

**Formula reference.** Use :eq:`schaum-7-2` and the definitions immediately above it.

**Worked application.**

1. Use the slit width b for envelope zeros and center spacing a for interference maxima; convert small angles to focal-plane coordinates only after establishing the angular condition.
2. Carry the algebra from the formula reference to the identity named in the paraphrased task; do not assume that identity as an intermediate step.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Geometry and :math:`a\sin\theta_m=m\lambda` give :math:`Z_m=m\lambda f/\sqrt{a^2-m^2\lambda^2}`, which contains no lens-position distance.

**Check.** The central single-slit lobe spans twice the first-minimum angle; reducing the slit width must broaden the envelope.

Problem 7.59 — shift the single-slit pattern for oblique incidence
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Shift the single-slit pattern for oblique incidence.

**Formula reference.** Use :eq:`schaum-7-2` and the definitions immediately above it.

**Worked application.**

1. Use the slit width b for envelope zeros and center spacing a for interference maxima; convert small angles to focal-plane coordinates only after establishing the angular condition.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The central lobe shifts to the 30° specular direction and broadens by :math:`1/\cos30^\circ\approx1.155`.

**Check.** The central single-slit lobe spans twice the first-minimum angle; reducing the slit width must broaden the envelope.

Problem 7.60 — overlap minima produced by two wavelengths
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Overlap minima produced by two wavelengths.

**Formula reference.** Use :eq:`schaum-7-2` and the definitions immediately above it.

**Worked application.**

1. Use the slit width b for envelope zeros and center spacing a for interference maxima; convert small angles to focal-plane coordinates only after establishing the angular condition.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Coincidence of first and third minima requires :math:`\lambda_1=3\lambda_3` (with subscripts assigned to those orders).

**Check.** The central single-slit lobe spans twice the first-minimum angle; reducing the slit width must broaden the envelope.

Problem 7.61 — find the half-maximum width of a distant single-slit pattern
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find the half-maximum width of a distant single-slit pattern.

**Formula reference.** Use :eq:`schaum-7-2` and the definitions immediately above it.

**Worked application.**

1. Use the slit width b for envelope zeros and center spacing a for interference maxima; convert small angles to focal-plane coordinates only after establishing the angular condition.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The full half-maximum central width is about 632.8 mm at the 1-km screen.

**Check.** The central single-slit lobe spans twice the first-minimum angle; reducing the slit width must broaden the envelope.

Problem 7.62 — find first-minimum separation in a lens focal plane
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find first-minimum separation in a lens focal plane.

**Formula reference.** Use :eq:`schaum-7-2` and the definitions immediately above it.

**Worked application.**

1. Use the slit width b for envelope zeros and center spacing a for interference maxima; convert small angles to focal-plane coordinates only after establishing the angular condition.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The first-minimum separation is about 2.64 mm.

**Check.** The central single-slit lobe spans twice the first-minimum angle; reducing the slit width must broaden the envelope.

Problem 7.63 — infer focal length from fourth-order minima
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer focal length from fourth-order minima.

**Formula reference.** Use :eq:`schaum-7-2` and the definitions immediately above it.

**Worked application.**

1. Use the slit width b for envelope zeros and center spacing a for interference maxima; convert small angles to focal-plane coordinates only after establishing the angular condition.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The inferred focal length is about 7.1 cm.

**Check.** The central single-slit lobe spans twice the first-minimum angle; reducing the slit width must broaden the envelope.

Problem 7.64 — count double-slit fringes inside the diffraction envelope
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Count double-slit fringes inside the diffraction envelope.

**Formula reference.** Use :eq:`schaum-7-2` and the definitions immediately above it.

**Worked application.**

1. Use the slit width b for envelope zeros and center spacing a for interference maxima; convert small angles to focal-plane coordinates only after establishing the angular condition.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Envelope zeros occur at :math:`b\sin\theta=\pm\lambda`; with :math:`a=Mb`, the interference orders strictly inside are :math:`m=-(M-1),\ldots,M-1`, with the boundary coincidences counted as in the source convention to give :math:`2M` bright bands.

**Check.** The central single-slit lobe spans twice the first-minimum angle; reducing the slit width must broaden the envelope.

Problem 7.65 — infer slit separation from fifteen central bright fringes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer slit separation from fifteen central bright fringes.

**Formula reference.** Use :eq:`schaum-7-2` and the definitions immediately above it.

**Worked application.**

1. Use the slit width b for envelope zeros and center spacing a for interference maxima; convert small angles to focal-plane coordinates only after establishing the angular condition.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Fifteen bright fringes place the seventh interference maximum at the first diffraction minimum, giving :math:`a=15b=3.75\,\mathrm{mm}`.

**Check.** The central single-slit lobe spans twice the first-minimum angle; reducing the slit width must broaden the envelope.

Problem 7.66 — infer fringe spacing and slit width from a nine-fringe pattern
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer fringe spacing and slit width from a nine-fringe pattern.

**Formula reference.** Use :eq:`schaum-7-2` and the definitions immediately above it.

**Worked application.**

1. Use the slit width b for envelope zeros and center spacing a for interference maxima; convert small angles to focal-plane coordinates only after establishing the angular condition.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The consecutive maxima are separated by :math:`\Delta Z=\lambda L/a=4.125\,\mathrm{mm}` and the envelope count gives :math:`b=0.089\,\mathrm{mm}`.

**Check.** The central single-slit lobe spans twice the first-minimum angle; reducing the slit width must broaden the envelope.

Multiple narrow slits and diffraction gratings
----------------------------------------------

**Formula and definitions.**

.. math::
   :label: schaum-7-3

   a\sin\theta_m=m\lambda,\qquad \mathcal R=\frac{\lambda}{\Delta\lambda}=mN,\qquad |m|\leq\frac{a}{\lambda}

The grating equation locates orders; the finite geometric sum
sets their width.  Applying the Rayleigh criterion to neighboring wavelengths
gives :math:`\mathcal R=mN`.  Order overlap requires
:math:`m_1\lambda_1=m_2\lambda_2`.

Problem 7.67 — recover one- and two-slit limits of the N-slit equation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Recover one- and two-slit limits of the n-slit equation.

**Formula reference.** Use :eq:`schaum-7-3` and the definitions immediately above it.

**Worked application.**

1. Use groove spacing (the reciprocal of line density), count illuminated grooves, select the requested order, and apply either the grating equation or mN resolving power.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** At :math:`N=1` the array factor tends to one; at :math:`N=2`, :math:`\sin2\alpha/\sin\alpha=2\cos\alpha`, recovering the single- and double-slit formulas.

**Check.** The sine in the grating equation cannot exceed unity; increasing illuminated width or order must improve resolving power.

Problem 7.68 — bound the number of grating principal orders
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Bound the number of grating principal orders.

**Formula reference.** Use :eq:`schaum-7-3` and the definitions immediately above it.

**Worked application.**

1. Use groove spacing (the reciprocal of line density), count illuminated grooves, select the requested order, and apply either the grating equation or mN resolving power.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The finite order condition is :math:`|m|\le a/\lambda`.

**Check.** The sine in the grating equation cannot exceed unity; increasing illuminated width or order must improve resolving power.

Problem 7.69 — find the midpoint subsidiary-maximum irradiance for odd N
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find the midpoint subsidiary-maximum irradiance for odd n.

**Formula reference.** Use :eq:`schaum-7-3` and the definitions immediately above it.

**Worked application.**

1. Use groove spacing (the reciprocal of line density), count illuminated grooves, select the requested order, and apply either the grating equation or mN resolving power.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** At the midpoint subsidiary maximum for odd :math:`N`, numerator and denominator sines each have unit magnitude, so :math:`I_{\rm sub}=I(0)/N^2`.

**Check.** The sine in the grating equation cannot exceed unity; increasing illuminated width or order must improve resolving power.

Problem 7.70 — choose focal length for a specified second-order spectrum length
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Choose focal length for a specified second-order spectrum length.

**Formula reference.** Use :eq:`schaum-7-3` and the definitions immediately above it.

**Worked application.**

1. Use groove spacing (the reciprocal of line density), count illuminated grooves, select the requested order, and apply either the grating equation or mN resolving power.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The required focal length is about 5.63 cm.

**Check.** The sine in the grating equation cannot exceed unity; increasing illuminated width or order must improve resolving power.

Problem 7.71 — prove the upper limit of grating resolving power
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Prove the upper limit of grating resolving power.

**Formula reference.** Use :eq:`schaum-7-3` and the definitions immediately above it.

**Worked application.**

1. Use groove spacing (the reciprocal of line density), count illuminated grooves, select the requested order, and apply either the grating equation or mN resolving power.
2. Carry the algebra from the formula reference to the identity named in the paraphrased task; do not assume that identity as an intermediate step.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Since the largest physical order is :math:`m\le a/\lambda`, :math:`\mathcal R=mN\le aN/\lambda`.

**Check.** The sine in the grating equation cannot exceed unity; increasing illuminated width or order must improve resolving power.

Problem 7.72 — calculate resolving power and wavelength resolution of a grating
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Calculate resolving power and wavelength resolution of a grating.

**Formula reference.** Use :eq:`schaum-7-3` and the definitions immediately above it.

**Worked application.**

1. Use groove spacing (the reciprocal of line density), count illuminated grooves, select the requested order, and apply either the grating equation or mN resolving power.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** At 550 nm, :math:`\mathcal R_3=120{,}000` and the second-order resolution is about :math:`6.88\times10^{-3}\,\mathrm{nm}`.

**Check.** The sine in the grating equation cannot exceed unity; increasing illuminated width or order must improve resolving power.

Problem 7.73 — size a grating to resolve adjacent laser longitudinal modes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Size a grating to resolve adjacent laser longitudinal modes.

**Formula reference.** Use :eq:`schaum-7-3` and the definitions immediately above it.

**Worked application.**

1. Use groove spacing (the reciprocal of line density), count illuminated grooves, select the requested order, and apply either the grating equation or mN resolving power.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** About 79 cm of the 200-line/mm grating must be illuminated.

**Check.** The sine in the grating equation cannot exceed unity; increasing illuminated width or order must improve resolving power.

Problem 7.74 — decide which visible diffraction orders can overlap
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Decide which visible diffraction orders can overlap.

**Formula reference.** Use :eq:`schaum-7-3` and the definitions immediately above it.

**Worked application.**

1. Use groove spacing (the reciprocal of line density), count illuminated grooves, select the requested order, and apply either the grating equation or mN resolving power.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The first and second visible orders only meet at the extreme visible limits and substantially miss; second and third orders do overlap because :math:`2\lambda_{\rm red}=3\lambda_{\rm blue}` is possible.

**Check.** The sine in the grating equation cannot exceed unity; increasing illuminated width or order must improve resolving power.

Problem 7.75 — match a third-order wavelength to a fourth-order line
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Match a third-order wavelength to a fourth-order line.

**Formula reference.** Use :eq:`schaum-7-3` and the definitions immediately above it.

**Worked application.**

1. Use groove spacing (the reciprocal of line density), count illuminated grooves, select the requested order, and apply either the grating equation or mN resolving power.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The coincident third-order wavelength is :math:`(4/3)(490\,\mathrm{nm})=653.3\,\mathrm{nm}`.

**Check.** The sine in the grating equation cannot exceed unity; increasing illuminated width or order must improve resolving power.

Rectangular and circular apertures: Fraunhofer diffraction
----------------------------------------------------------

**Formula and definitions.**

.. math::
   :label: schaum-7-4

   N_F=\frac{d^2}{\lambda L}\ll1,\qquad \theta_R=1.22\frac{\lambda}{D},\qquad r_{\rm Airy}=1.22\frac{\lambda f}{D}

Fraunhofer behavior requires the quadratic phase variation
across the aperture to be small, giving :math:`L\gg d^2/\lambda`.  A circular
aperture produces the Airy pattern; the first zero gives the Rayleigh angular
resolution and multiplication by :math:`f` gives focal-plane radius.

Problem 7.76 — derive the distance criterion for far-field diffraction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive the distance criterion for far-field diffraction.

**Formula reference.** Use :eq:`schaum-7-4` and the definitions immediately above it.

**Worked application.**

1. Select aperture diameter D (not radius unless converted), use the vacuum or in-medium wavelength consistently, and turn angular resolution into separation by the small-angle relation s=Lθ.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Bounding the aperture's quadratic phase by much less than one gives :math:`L\gg d^2/\lambda`; :math:`L>d^2/\lambda` is the usual rule of thumb.

**Check.** A larger aperture or shorter wavelength must improve resolution; the focal-plane spot scales linearly with focal length.

Problem 7.77 — estimate direct-view distance behind a circular hole
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Estimate direct-view distance behind a circular hole.

**Formula reference.** Use :eq:`schaum-7-4` and the definitions immediately above it.

**Worked application.**

1. Select aperture diameter D (not radius unless converted), use the vacuum or in-medium wavelength consistently, and turn angular resolution into separation by the small-angle relation s=Lθ.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The direct-view far-field criterion gives a distance of order 10 m or more.

**Check.** A larger aperture or shorter wavelength must improve resolution; the focal-plane spot scales linearly with focal length.

Problem 7.78 — find a diagonal sidelobe of a square aperture
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find a diagonal sidelobe of a square aperture.

**Formula reference.** Use :eq:`schaum-7-4` and the definitions immediately above it.

**Worked application.**

1. Select aperture diameter D (not radius unless converted), use the vacuum or in-medium wavelength consistently, and turn angular resolution into separation by the small-angle relation s=Lθ.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The third diagonal bright spot has :math:`I/I(0)\approx6.8\times10^{-5}`.

**Check.** A larger aperture or shorter wavelength must improve resolution; the focal-plane spot scales linearly with focal length.

Problem 7.79 — scale central irradiance with wavelength and aperture area
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Scale central irradiance with wavelength and aperture area.

**Formula reference.** Use :eq:`schaum-7-4` and the definitions immediately above it.

**Worked application.**

1. Select aperture diameter D (not radius unless converted), use the vacuum or in-medium wavelength consistently, and turn angular resolution into separation by the small-angle relation s=Lθ.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The on-axis field scales as aperture area divided by wavelength, so :math:`I(0)\propto A^2/\lambda^2`.

**Check.** A larger aperture or shorter wavelength must improve resolution; the focal-plane spot scales linearly with focal length.

Problem 7.80 — calculate telescope focal-plane Airy radius
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Calculate telescope focal-plane airy radius.

**Formula reference.** Use :eq:`schaum-7-4` and the definitions immediately above it.

**Worked application.**

1. Select aperture diameter D (not radius unless converted), use the vacuum or in-medium wavelength consistently, and turn angular resolution into separation by the small-angle relation s=Lθ.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The focal-plane Airy radius is about :math:`8.39\times10^{-3}\,\mathrm{mm}`.

**Check.** A larger aperture or shorter wavelength must improve resolution; the focal-plane spot scales linearly with focal length.

Problem 7.81 — estimate diffraction-limited laser spreading
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Estimate diffraction-limited laser spreading.

**Formula reference.** Use :eq:`schaum-7-4` and the definitions immediately above it.

**Worked application.**

1. Select aperture diameter D (not radius unless converted), use the vacuum or in-medium wavelength consistently, and turn angular resolution into separation by the small-angle relation s=Lθ.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The beam diameter after 1 km is of order 0.77 m under the aperture convention used in the problem.

**Check.** A larger aperture or shorter wavelength must improve resolution; the focal-plane spot scales linearly with focal length.

Problem 7.82 — choose lens diameter for a one-micron image spot
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Choose lens diameter for a one-micron image spot.

**Formula reference.** Use :eq:`schaum-7-4` and the definitions immediately above it.

**Worked application.**

1. Select aperture diameter D (not radius unless converted), use the vacuum or in-medium wavelength consistently, and turn angular resolution into separation by the small-angle relation s=Lθ.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Using a 0.5-µm Airy radius gives :math:`D=1.22\lambda f/r\approx0.247\,\mathrm m`.

**Check.** A larger aperture or shorter wavelength must improve resolution; the focal-plane spot scales linearly with focal length.

Problem 7.83 — calculate radio-telescope angular resolution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Calculate radio-telescope angular resolution.

**Formula reference.** Use :eq:`schaum-7-4` and the definitions immediately above it.

**Worked application.**

1. Select aperture diameter D (not radius unless converted), use the vacuum or in-medium wavelength consistently, and turn angular resolution into separation by the small-angle relation s=Lθ.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The 1420-MHz radio telescope resolution is about :math:`6.0\times10^{-3}\,\mathrm{rad}` or 0.34°.

**Check.** A larger aperture or shorter wavelength must improve resolution; the focal-plane spot scales linearly with focal length.

Problem 7.84 — calculate eye resolution and resolved object spacing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Calculate eye resolution and resolved object spacing.

**Formula reference.** Use :eq:`schaum-7-4` and the definitions immediately above it.

**Worked application.**

1. Select aperture diameter D (not radius unless converted), use the vacuum or in-medium wavelength consistently, and turn angular resolution into separation by the small-angle relation s=Lθ.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`\Delta\phi_{\min}\approx2.68\times10^{-4}\,\mathrm{rad}`, requiring about 0.268 m separation at 1 km.

**Check.** A larger aperture or shorter wavelength must improve resolution; the focal-plane spot scales linearly with focal length.

Problem 7.85 — find headlight resolution distance for a dark-adapted pupil
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find headlight resolution distance for a dark-adapted pupil.

**Formula reference.** Use :eq:`schaum-7-4` and the definitions immediately above it.

**Worked application.**

1. Select aperture diameter D (not radius unless converted), use the vacuum or in-medium wavelength consistently, and turn angular resolution into separation by the small-angle relation s=Lθ.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The headlamps become just resolvable at roughly 6.5 km.

**Check.** A larger aperture or shorter wavelength must improve resolution; the focal-plane spot scales linearly with focal length.

Fresnel diffraction: circular systems
-------------------------------------

**Formula and definitions.**

.. math::
   :label: schaum-7-5

   r_m^2\simeq m\lambda\frac{r_0r_1}{r_0+r_1},\qquad \frac1f=\frac1{r_0}+\frac1{r_1},\qquad f_m=\frac{r_m^2}{m\lambda}

Successive Fresnel-zone boundaries differ in optical path by
:math:`\lambda/2`, so adjacent zone amplitudes nearly cancel.  Convert every
open annulus to the difference of two cumulative vibration-curve vectors and
sum complex amplitudes before squaring.  A zone plate passes alternate zones,
making their surviving contributions add near a focus.

Problem 7.86 — count Fresnel zones uncovered by a circular aperture
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Count fresnel zones uncovered by a circular aperture.

**Formula reference.** Use :eq:`schaum-7-5` and the definitions immediately above it.

**Worked application.**

1. Compute the dimensionless zone order from aperture radius and conjugate distances, add only the open-zone phasors, and square the resultant amplitude relative to the unobstructed reference.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The aperture uncovers about 100 Fresnel zones.

**Check.** Adjacent complete zones must nearly cancel; irradiance, not field amplitude, is the squared vibration-curve chord length.

Problem 7.87 — find aperture radii giving on-axis maxima and minima
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find aperture radii giving on-axis maxima and minima.

**Formula reference.** Use :eq:`schaum-7-5` and the definitions immediately above it.

**Worked application.**

1. Compute the dimensionless zone order from aperture radius and conjugate distances, add only the open-zone phasors, and square the resultant amplitude relative to the unobstructed reference.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Successive half-zone conditions give maxima at about 1.06, 1.84, and 2.87 mm and minima at 1.50, 2.12, and 2.60 mm for the stated geometry.

**Check.** Adjacent complete zones must nearly cancel; irradiance, not field amplitude, is the squared vibration-curve chord length.

Problem 7.88 — find axial irradiance behind a helium-neon aperture
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find axial irradiance behind a helium-neon aperture.

**Formula reference.** Use :eq:`schaum-7-5` and the definitions immediately above it.

**Worked application.**

1. Compute the dimensionless zone order from aperture radius and conjugate distances, add only the open-zone phasors, and square the resultant amplitude relative to the unobstructed reference.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** For the stated aperture and axial point, the vibration-curve chord gives :math:`I=2I_0`.

**Check.** Adjacent complete zones must nearly cancel; irradiance, not field amplitude, is the squared vibration-curve chord length.

Problem 7.89 — sum annular-zone contributions for a shaped aperture
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Sum annular-zone contributions for a shaped aperture.

**Formula reference.** Use :eq:`schaum-7-5` and the definitions immediately above it.

**Worked application.**

1. Compute the dimensionless zone order from aperture radius and conjugate distances, add only the open-zone phasors, and square the resultant amplitude relative to the unobstructed reference.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Adding the open annular-zone phasors and squaring gives :math:`I\approx90\,\mathrm{W/m^2}`.

**Check.** Adjacent complete zones must nearly cancel; irradiance, not field amplitude, is the squared vibration-curve chord length.

Problem 7.90 — use the vibration curve for one-and-a-half open zones
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Use the vibration curve for one-and-a-half open zones.

**Formula reference.** Use :eq:`schaum-7-5` and the definitions immediately above it.

**Worked application.**

1. Compute the dimensionless zone order from aperture radius and conjugate distances, add only the open-zone phasors, and square the resultant amplitude relative to the unobstructed reference.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** One and one-half open zones give :math:`I\approx2I_0`.

**Check.** Adjacent complete zones must nearly cancel; irradiance, not field amplitude, is the squared vibration-curve chord length.

Problem 7.91 — find axial irradiance through a second shaped aperture
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find axial irradiance through a second shaped aperture.

**Formula reference.** Use :eq:`schaum-7-5` and the definitions immediately above it.

**Worked application.**

1. Compute the dimensionless zone order from aperture radius and conjugate distances, add only the open-zone phasors, and square the resultant amplitude relative to the unobstructed reference.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The aperture's open-zone chord has twice the unobstructed field amplitude, giving :math:`I=100\,\mathrm{W/m^2}` from the 25-W/m² incident reference.

**Check.** Adjacent complete zones must nearly cancel; irradiance, not field amplitude, is the squared vibration-curve chord length.

Problem 7.92 — evaluate an annular obstruction with the vibration curve
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Evaluate an annular obstruction with the vibration curve.

**Formula reference.** Use :eq:`schaum-7-5` and the definitions immediately above it.

**Worked application.**

1. Compute the dimensionless zone order from aperture radius and conjugate distances, add only the open-zone phasors, and square the resultant amplitude relative to the unobstructed reference.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The central-disk and second-zone obstruction phasors cancel the unobstructed vector to the plotted accuracy, so the axial irradiance is approximately zero.

**Check.** Adjacent complete zones must nearly cancel; irradiance, not field amplitude, is the squared vibration-curve chord length.

Problem 7.93 — derive zone-plate focal length and first-zone radius
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive zone-plate focal length and first-zone radius.

**Formula reference.** Use :eq:`schaum-7-5` and the definitions immediately above it.

**Worked application.**

1. Compute the dimensionless zone order from aperture radius and conjugate distances, add only the open-zone phasors, and square the resultant amplitude relative to the unobstructed reference.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The zone-plate relation is :math:`r_m^2=m\lambda f`; for equal 5-m conjugates, :math:`f=2.5\,\mathrm m` and :math:`r_1\approx1.12\,\mathrm{mm}`.

**Check.** Adjacent complete zones must nearly cancel; irradiance, not field amplitude, is the squared vibration-curve chord length.

Problem 7.94 — calculate zone-plate focus irradiance with only the first zone open
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Calculate zone-plate focus irradiance with only the first zone open.

**Formula reference.** Use :eq:`schaum-7-5` and the definitions immediately above it.

**Worked application.**

1. Compute the dimensionless zone order from aperture radius and conjugate distances, add only the open-zone phasors, and square the resultant amplitude relative to the unobstructed reference.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** With only the first zone open, its field is approximately twice the unobstructed field, hence :math:`I\approx4I_0`.

**Check.** Adjacent complete zones must nearly cancel; irradiance, not field amplitude, is the squared vibration-curve chord length.

Problem 7.95 — find zone-plate focal and image distances
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find zone-plate focal and image distances.

**Formula reference.** Use :eq:`schaum-7-5` and the definitions immediately above it.

**Worked application.**

1. Compute the dimensionless zone order from aperture radius and conjugate distances, add only the open-zone phasors, and square the resultant amplitude relative to the unobstructed reference.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The first-order focal length is about 3.89 m; equal object and image distances are about 7.78 m.

**Check.** Adjacent complete zones must nearly cancel; irradiance, not field amplitude, is the squared vibration-curve chord length.

Fresnel diffraction: straight edges
-----------------------------------

**Formula and definitions.**

.. math::
   :label: schaum-7-6

   u=y\sqrt{\frac{2(r_0+r_1)}{\lambda r_0r_1}},\qquad \frac{E}{E_0}=\frac{[C(u_2)-C(u_1)]+i[S(u_2)-S(u_1)]}{1+i},\qquad \frac{I}{I_0}=\left|\frac{E}{E_0}\right|^2

Map each physical edge to its dimensionless Fresnel coordinate
:math:`u`.  The Cornu-spiral chord between the two edge points is the complex
field; its squared length, with the unobstructed normalization, is irradiance.
For complementary apertures, Babinet's principle adds fields—not
irradiances—to the unobstructed field.

Problem 7.96 — prove that a very wide slit approaches unobstructed irradiance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Prove that a very wide slit approaches unobstructed irradiance.

**Formula reference.** Use :eq:`schaum-7-6` and the definitions immediately above it.

**Worked application.**

1. Calculate each edge coordinate with sign, read or evaluate both Fresnel integrals, subtract endpoints in the same order, and square the normalized complex magnitude.
2. Carry the algebra from the formula reference to the identity named in the paraphrased task; do not assume that identity as an intermediate step.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** As the two slit edges tend to opposite infinite Cornu endpoints, their chord becomes the full unobstructed vector and :math:`I(0)\to I_0`.

**Check.** Sending both edges to infinity must give I/I0=1; a single edge exactly on axis gives one quarter of the unobstructed irradiance.

Problem 7.97 — derive Cornu-spiral slope and locate horizontal and vertical tangencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive cornu-spiral slope and locate horizontal and vertical tangencies.

**Formula reference.** Use :eq:`schaum-7-6` and the definitions immediately above it.

**Worked application.**

1. Calculate each edge coordinate with sign, read or evaluate both Fresnel integrals, subtract endpoints in the same order, and square the normalized complex magnitude.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Since :math:`dS/dC=\tan(\pi u^2/2)`, horizontal tangencies are :math:`u=\sqrt{2},\sqrt4,\sqrt6,\ldots` and vertical tangencies :math:`u=\sqrt1,\sqrt3,\sqrt5,\ldots`, with symmetric negative points.

**Check.** Sending both edges to infinity must give I/I0=1; a single edge exactly on axis gives one quarter of the unobstructed irradiance.

Problem 7.98 — evaluate a line-source central slit irradiance and Cornu arc
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Evaluate a line-source central slit irradiance and cornu arc.

**Formula reference.** Use :eq:`schaum-7-6` and the definitions immediately above it.

**Worked application.**

1. Calculate each edge coordinate with sign, read or evaluate both Fresnel integrals, subtract endpoints in the same order, and square the normalized complex magnitude.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The central irradiance is about :math:`0.09I_0` and the Cornu-parameter span is about 0.417.

**Check.** Sending both edges to infinity must give I/I0=1; a single edge exactly on axis gives one quarter of the unobstructed irradiance.

Problem 7.99 — evaluate an off-axis slit irradiance under plane-wave illumination
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Evaluate an off-axis slit irradiance under plane-wave illumination.

**Formula reference.** Use :eq:`schaum-7-6` and the definitions immediately above it.

**Worked application.**

1. Calculate each edge coordinate with sign, read or evaluate both Fresnel integrals, subtract endpoints in the same order, and square the normalized complex magnitude.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The specified off-axis point gives :math:`I\approx0.0896I_0`.

**Check.** Sending both edges to infinity must give I/I0=1; a single edge exactly on axis gives one quarter of the unobstructed irradiance.

Problem 7.100 — maximize on-axis irradiance of a variable-width slit
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Maximize on-axis irradiance of a variable-width slit.

**Formula reference.** Use :eq:`schaum-7-6` and the definitions immediately above it.

**Worked application.**

1. Calculate each edge coordinate with sign, read or evaluate both Fresnel integrals, subtract endpoints in the same order, and square the normalized complex magnitude.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The maximum variable-slit central irradiance is about :math:`1.8I_0`.

**Check.** Sending both edges to infinity must give I/I0=1; a single edge exactly on axis gives one quarter of the unobstructed irradiance.

Problem 7.101 — explain the narrow-slit approach to Fraunhofer behavior
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Explain the narrow-slit approach to fraunhofer behavior.

**Formula reference.** Use :eq:`schaum-7-6` and the definitions immediately above it.

**Worked application.**

1. Calculate each edge coordinate with sign, read or evaluate both Fresnel integrals, subtract endpoints in the same order, and square the normalized complex magnitude.
2. Identify the controlling phase or conservation relation, then use it to account for every stated observation.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** A very narrow slit spans only a small Cornu parameter interval, so its two edge phasors are locally almost straight and parallel; the resulting scaled sinc-like modulation approaches the Fraunhofer pattern.

**Check.** Sending both edges to infinity must give I/I0=1; a single edge exactly on axis gives one quarter of the unobstructed irradiance.

Problem 7.102 — choose a slit width that maximizes axial irradiance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Choose a slit width that maximizes axial irradiance.

**Formula reference.** Use :eq:`schaum-7-6` and the definitions immediately above it.

**Worked application.**

1. Calculate each edge coordinate with sign, read or evaluate both Fresnel integrals, subtract endpoints in the same order, and square the normalized complex magnitude.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The first useful axial maximum corresponds to :math:`\Delta u\approx2.53`, giving slit width about 1.13 mm.

**Check.** Sending both edges to infinity must give I/I0=1; a single edge exactly on axis gives one quarter of the unobstructed irradiance.

Problem 7.103 — prove the quarter-irradiance value opposite a half-plane edge
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Prove the quarter-irradiance value opposite a half-plane edge.

**Formula reference.** Use :eq:`schaum-7-6` and the definitions immediately above it.

**Worked application.**

1. Calculate each edge coordinate with sign, read or evaluate both Fresnel integrals, subtract endpoints in the same order, and square the normalized complex magnitude.
2. Carry the algebra from the formula reference to the identity named in the paraphrased task; do not assume that identity as an intermediate step.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** At the geometric edge the Cornu chord is one half of the unobstructed field vector, so :math:`I=|E_0/2|^2=I_0/4`.

**Check.** Sending both edges to infinity must give I/I0=1; a single edge exactly on axis gives one quarter of the unobstructed irradiance.

Problem 7.104 — locate the first maximum and minimum behind a straight edge
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Locate the first maximum and minimum behind a straight edge.

**Formula reference.** Use :eq:`schaum-7-6` and the definitions immediately above it.

**Worked application.**

1. Calculate each edge coordinate with sign, read or evaluate both Fresnel integrals, subtract endpoints in the same order, and square the normalized complex magnitude.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The first minimum and maximum lie about 2.66 mm and 1.78 mm from the geometrical edge, respectively.

**Check.** Sending both edges to infinity must give I/I0=1; a single edge exactly on axis gives one quarter of the unobstructed irradiance.

Problem 7.105 — find and sketch the central irradiance behind a narrow opaque strip
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find and sketch the central irradiance behind a narrow opaque strip.

**Formula reference.** Use :eq:`schaum-7-6` and the definitions immediately above it.

**Worked application.**

1. Calculate each edge coordinate with sign, read or evaluate both Fresnel integrals, subtract endpoints in the same order, and square the normalized complex magnitude.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The complementary-slit field and Babinet subtraction give central irradiance :math:`I(0)\approx0.08I_0`; the curve is symmetric about the strip center.

**Check.** Sending both edges to infinity must give I/I0=1; a single edge exactly on axis gives one quarter of the unobstructed irradiance.
