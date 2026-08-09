Chapter 8: Introduction to Fourier Optics
=========================================

Source: Eugene Hecht, *Schaum's Outline of Theory and Problems of
Optics* (1975), Chapter 8.  The entries below cover only the
chapter's **Supplementary Problems**; prompts are paraphrased and are not
reproduced.

Each topic derives its shared formula once.  Every numbered problem then
applies that derivation to the particular proof, calculation, or construction
in the book.  Read the source diagram alongside entries that depend on a figure.

Periodic waves and Fourier series
---------------------------------

**Formula and definitions.**

.. math::
   :label: schaum-8-1

   f(x)=\frac{a_0}{2}+\sum_{m=1}^{\infty}[a_m\cos(mkx)+b_m\sin(mkx)],\quad a_m=\frac{2}{L}\int_L f\cos(mkx)\,dx,\quad b_m=\frac{2}{L}\int_L f\sin(mkx)\,dx

Use parity before integrating: even functions have only cosine
terms and odd functions only sine terms.  Half-wave antisymmetry cancels even
harmonics.  Combine :math:`a_m` and :math:`b_m` as
:math:`C_m\cos(mkx+\phi_m)` using
:math:`a_m=C_m\cos\phi_m` and :math:`b_m=-C_m\sin\phi_m`.

Problem 8.22 — prove equivalence of amplitude-phase and sine-cosine Fourier forms
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Prove equivalence of amplitude-phase and sine-cosine fourier forms.

**Formula reference.** Use :eq:`schaum-8-1` and the definitions immediately above it.

**Worked application.**

1. Choose one complete period matching the source graph, split the integral at every discontinuity, exploit symmetry, and simplify the coefficient separately for even and odd m.
2. Carry the algebra from the formula reference to the identity named in the paraphrased task; do not assume that identity as an intermediate step.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Coefficient matching gives :math:`a_m=C_m\cos\phi_m` and :math:`b_m=-C_m\sin\phi_m`; therefore :math:`C_m=\sqrt{a_m^2+b_m^2}` and :math:`\phi_m=\operatorname{atan2}(-b_m,a_m)`.

**Check.** Reconstruct representative points away from jumps and verify the midpoint value at a jump; the coefficients must have the parity dictated by the waveform.

Problem 8.23 — show screw symmetry removes even harmonics
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Show screw symmetry removes even harmonics.

**Formula reference.** Use :eq:`schaum-8-1` and the definitions immediately above it.

**Worked application.**

1. Choose one complete period matching the source graph, split the integral at every discontinuity, exploit symmetry, and simplify the coefficient separately for even and odd m.
2. Start from the left-hand physical definition, transform it one step at a time, and stop only when the required right-hand form is obtained.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Pairing the two half-period integrals multiplies each coefficient by :math:`1-(-1)^m`; every even harmonic vanishes.

**Check.** Reconstruct representative points away from jumps and verify the midpoint value at a jump; the coefficients must have the parity dictated by the waveform.

Problem 8.24 — state when only even harmonics remain
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** State when only even harmonics remain.

**Formula reference.** Use :eq:`schaum-8-1` and the definitions immediately above it.

**Worked application.**

1. Choose one complete period matching the source graph, split the integral at every discontinuity, exploit symmetry, and simplify the coefficient separately for even and odd m.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Only even harmonics remain when the actual period is half the chosen :math:`2\pi` interval.

**Check.** Reconstruct representative points away from jumps and verify the midpoint value at a jump; the coefficients must have the parity dictated by the waveform.

Problem 8.25 — derive the series of a symmetric rectangular waveform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive the series of a symmetric rectangular waveform.

**Formula reference.** Use :eq:`schaum-8-1` and the definitions immediately above it.

**Worked application.**

1. Choose one complete period matching the source graph, split the integral at every discontinuity, exploit symmetry, and simplify the coefficient separately for even and odd m.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Integrating the constant segments of the source waveform leaves only the symmetry-allowed odd sine coefficients; evaluating the coefficient formula gives the displayed odd-harmonic series.

**Check.** Reconstruct representative points away from jumps and verify the midpoint value at a jump; the coefficients must have the parity dictated by the waveform.

Problem 8.26 — derive the series of a second periodic waveform
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive the series of a second periodic waveform.

**Formula reference.** Use :eq:`schaum-8-1` and the definitions immediately above it.

**Worked application.**

1. Choose one complete period matching the source graph, split the integral at every discontinuity, exploit symmetry, and simplify the coefficient separately for even and odd m.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The waveform is even, so all sine coefficients vanish; piecewise integration gives its constant term and the inverse-square odd-cosine sequence shown in the source answer.

**Check.** Reconstruct representative points away from jumps and verify the midpoint value at a jump; the coefficients must have the parity dictated by the waveform.

Problem 8.27 — generalize the waveform to arbitrary period
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Generalize the waveform to arbitrary period.

**Formula reference.** Use :eq:`schaum-8-1` and the definitions immediately above it.

**Worked application.**

1. Choose one complete period matching the source graph, split the integral at every discontinuity, exploit symmetry, and simplify the coefficient separately for even and odd m.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Replacing the normalized period by :math:`L` changes every harmonic argument to :math:`2\pi mx/L`; the coefficient amplitudes retain the same parity sequence after the corresponding scale factor.

**Check.** Reconstruct representative points away from jumps and verify the midpoint value at a jump; the coefficients must have the parity dictated by the waveform.

Problem 8.28 — obtain a shifted series by changing axes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Obtain a shifted series by changing axes.

**Formula reference.** Use :eq:`schaum-8-1` and the definitions immediately above it.

**Worked application.**

1. Choose one complete period matching the source graph, split the integral at every discontinuity, exploit symmetry, and simplify the coefficient separately for even and odd m.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Apply the translation theorem to the result of 8.26: shifting by :math:`x_0` multiplies each complex coefficient by :math:`e^{-imkx_0}`, equivalently rotating cosine terms into the source's shifted signs.

**Check.** Reconstruct representative points away from jumps and verify the midpoint value at a jump; the coefficients must have the parity dictated by the waveform.

Problem 8.29 — derive the series of a full-wave rectified sine
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive the series of a full-wave rectified sine.

**Formula reference.** Use :eq:`schaum-8-1` and the definitions immediately above it.

**Worked application.**

1. Choose one complete period matching the source graph, split the integral at every discontinuity, exploit symmetry, and simplify the coefficient separately for even and odd m.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** For unit period, :math:`f(t)=E_0|\sin\pi t|=2E_0/\pi-(4E_0/\pi)\sum_{m=1}^{\infty}\cos(2\pi mt)/(4m^2-1)`.

**Check.** Reconstruct representative points away from jumps and verify the midpoint value at a jump; the coefficients must have the parity dictated by the waveform.

Fourier transforms
------------------

**Formula and definitions.**

.. math::
   :label: schaum-8-2

   F(k)=\int_{-\infty}^{\infty}f(x)e^{-ikx}\,dx,\qquad f(x)=\frac1{2\pi}\int_{-\infty}^{\infty}F(k)e^{ikx}\,dk

Insert the piecewise support before integrating.  Modulation
shifts spectra:
:math:`\mathcal F\{f(x)e^{ik_0x}\}=F(k-k_0)`, while multiplication by
:math:`x` gives :math:`i\,dF/dk`.  Complete the square for a Gaussian and use
the delta sifting property for constants and impulses.

Problem 8.30 — transform a square pulse with complex exponentials
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Transform a square pulse with complex exponentials.

**Formula reference.** Use :eq:`schaum-8-2` and the definitions immediately above it.

**Worked application.**

1. Rewrite trigonometric modulation as exponentials, apply the shift theorem to the base transform, and preserve the book's 2π transform convention throughout.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** For a unit-height pulse on :math:`[-L,L]`, direct exponential integration gives :math:`F(k)=2\sin(kL)/k=2L\operatorname{sinc}(kL)`.

**Check.** A real even function must have a real even transform; narrowing a spatial pulse must broaden its spectrum.

Problem 8.31 — transform a windowed sine wave
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Transform a windowed sine wave.

**Formula reference.** Use :eq:`schaum-8-2` and the definitions immediately above it.

**Worked application.**

1. Rewrite trigonometric modulation as exponentials, apply the shift theorem to the base transform, and preserve the book's 2π transform convention throughout.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`F(k)=iE_0L[\operatorname{sinc}(k-k_0)L-\operatorname{sinc}(k+k_0)L]` under the book's transform convention.

**Check.** A real even function must have a real even transform; narrowing a spatial pulse must broaden its spectrum.

Problem 8.32 — transform a windowed sine-squared wave
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Transform a windowed sine-squared wave.

**Formula reference.** Use :eq:`schaum-8-2` and the definitions immediately above it.

**Worked application.**

1. Rewrite trigonometric modulation as exponentials, apply the shift theorem to the base transform, and preserve the book's 2π transform convention throughout.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`F(k)=E_0L[\operatorname{sinc}(kL)-\tfrac12\operatorname{sinc}(k+2k_0)L-\tfrac12\operatorname{sinc}(k-2k_0)L]`.

**Check.** A real even function must have a real even transform; narrowing a spatial pulse must broaden its spectrum.

Problem 8.33 — transform a one-sided exponential by two routes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Transform a one-sided exponential by two routes.

**Formula reference.** Use :eq:`schaum-8-2` and the definitions immediately above it.

**Worked application.**

1. Rewrite trigonometric modulation as exponentials, apply the shift theorem to the base transform, and preserve the book's 2π transform convention throughout.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The one-sided exponential transforms to :math:`2a/(a^2+k^2)`.

**Check.** A real even function must have a real even transform; narrowing a spatial pulse must broaden its spectrum.

Problem 8.34 — transform a Gaussian and interpret apodization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Transform a gaussian and interpret apodization.

**Formula reference.** Use :eq:`schaum-8-2` and the definitions immediately above it.

**Worked application.**

1. Rewrite trigonometric modulation as exponentials, apply the shift theorem to the base transform, and preserve the book's 2π transform convention throughout.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The normalized Gaussian transforms to :math:`\exp[-k^2/(4a)]`; Gaussian apodization suppresses hard-edge rings.

**Check.** A real even function must have a real even transform; narrowing a spatial pulse must broaden its spectrum.

Problem 8.35 — transform a causal exponentially weighted coordinate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Transform a causal exponentially weighted coordinate.

**Formula reference.** Use :eq:`schaum-8-2` and the definitions immediately above it.

**Worked application.**

1. Rewrite trigonometric modulation as exponentials, apply the shift theorem to the base transform, and preserve the book's 2π transform convention throughout.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`\mathcal F\{U(x)xe^{-ax}\}=1/(a+ik)^2` for the displayed :math:`e^{-ikx}` convention (the sign changes with the opposite convention).

**Check.** A real even function must have a real even transform; narrowing a spatial pulse must broaden its spectrum.

Problem 8.36 — transform delta and constant functions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Transform delta and constant functions.

**Formula reference.** Use :eq:`schaum-8-2` and the definitions immediately above it.

**Worked application.**

1. Rewrite trigonometric modulation as exponentials, apply the shift theorem to the base transform, and preserve the book's 2π transform convention throughout.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`\mathcal F\{\delta(x)\}=1` and :math:`\mathcal F\{1\}=2\pi\delta(k)`.

**Check.** A real even function must have a real even transform; narrowing a spatial pulse must broaden its spectrum.

Convolution
-----------

**Formula and definitions.**

.. math::
   :label: schaum-8-3

   (f*h)(x)=\int_{-\infty}^{\infty}f(\xi)h(x-\xi)\,d\xi,\qquad \mathcal F\{fh\}=\frac1{2\pi}(F*H),\qquad \delta(x-a)*\delta(x-b)=\delta[x-(a+b)]

For a graphical convolution, reverse one function, translate it
by :math:`x`, multiply overlaps, and integrate.  For impulses, form every
ordered pair of locations; their coordinates add and coincident sums add
weights.  The transform product/convolution theorem follows by inserting the
inverse transforms and evaluating the inner exponential integral as a delta.

Problem 8.37 — prove the frequency-domain convolution theorem
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Prove the frequency-domain convolution theorem.

**Formula reference.** Use :eq:`schaum-8-3` and the definitions immediately above it.

**Worked application.**

1. Use the integral definition for continuous shapes or pairwise coordinate sums for impulses; combine coincident contributions before plotting amplitudes.
2. Carry the algebra from the formula reference to the identity named in the paraphrased task; do not assume that identity as an intermediate step.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Insert the two inverse transforms into :math:`f(x)h(x)`; the x integral produces :math:`2\pi\delta[k-(q+p)]`, leaving :math:`\mathcal F\{fh\}=(F*H)/(2\pi)`.

**Check.** Convolution is commutative, its support width is the sum of input support widths, and total area equals the product of the two input areas.

Problem 8.38 — transform a cosine squared using spectral convolution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Transform a cosine squared using spectral convolution.

**Formula reference.** Use :eq:`schaum-8-3` and the definitions immediately above it.

**Worked application.**

1. Use the integral definition for continuous shapes or pairwise coordinate sums for impulses; combine coincident contributions before plotting amplitudes.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`\mathcal F\{\cos^2k_0x\}=\pi\delta(k)+(\pi/2)[\delta(k-2k_0)+\delta(k+2k_0)]` for the stated convention.

**Check.** Convolution is commutative, its support width is the sum of input support widths, and total area equals the product of the two input areas.

Problem 8.39 — prove commutativity of convolution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Prove commutativity of convolution.

**Formula reference.** Use :eq:`schaum-8-3` and the definitions immediately above it.

**Worked application.**

1. Use the integral definition for continuous shapes or pairwise coordinate sums for impulses; combine coincident contributions before plotting amplitudes.
2. Carry the algebra from the formula reference to the identity named in the paraphrased task; do not assume that identity as an intermediate step.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** In :math:`(f*h)(x)`, substitute :math:`u=x-\xi`; reversing the integration limits and differential restores them and yields :math:`(h*f)(x)`.

**Check.** Convolution is commutative, its support width is the sum of input support widths, and total area equals the product of the two input areas.

Problem 8.40 — construct a discrete self-convolution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Construct a discrete self-convolution.

**Formula reference.** Use :eq:`schaum-8-3` and the definitions immediately above it.

**Worked application.**

1. Use the integral definition for continuous shapes or pairwise coordinate sums for impulses; combine coincident contributions before plotting amplitudes.
2. Evaluate all breakpoints or ray/phasor endpoints first, then join only the intervals allowed by the governing relation.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Pairwise addition of the impulse locations in the source graph produces the plotted self-convolution; repeated sums add their amplitudes at the same coordinate.

**Check.** Convolution is commutative, its support width is the sum of input support widths, and total area equals the product of the two input areas.

Problem 8.41 — convolve a three-impulse distribution with itself
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Convolve a three-impulse distribution with itself.

**Formula reference.** Use :eq:`schaum-8-3` and the definitions immediately above it.

**Worked application.**

1. Use the integral definition for continuous shapes or pairwise coordinate sums for impulses; combine coincident contributions before plotting amplitudes.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`f*f=\delta(x-2)+2\delta(x-1)+3\delta(x)+2\delta(x+1)+\delta(x+2)`.

**Check.** Convolution is commutative, its support width is the sum of input support widths, and total area equals the product of the two input areas.

Problem 8.42 — self-convolve a four-line spectrum
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Self-convolve a four-line spectrum.

**Formula reference.** Use :eq:`schaum-8-3` and the definitions immediately above it.

**Worked application.**

1. Use the integral definition for continuous shapes or pairwise coordinate sums for impulses; combine coincident contributions before plotting amplitudes.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** For unit impulses at :math:`k=\pm2,\pm3`, the self-convolution has weights 1,2,1 at -6,-5,-4; 2,4,2 at -1,0,1; and 1,2,1 at 4,5,6.

**Check.** Convolution is commutative, its support width is the sum of input support widths, and total area equals the product of the two input areas.

Problem 8.43 — convolve a rectangular pulse with an impulse pair and transform it
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Convolve a rectangular pulse with an impulse pair and transform it.

**Formula reference.** Use :eq:`schaum-8-3` and the definitions immediately above it.

**Worked application.**

1. Use the integral definition for continuous shapes or pairwise coordinate sums for impulses; combine coincident contributions before plotting amplitudes.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Convolution with the signed impulse pair produces the difference of two shifted rectangular pulses; its transform is the rectangle's sinc spectrum multiplied by the corresponding sine phase factor.

**Check.** Convolution is commutative, its support width is the sum of input support widths, and total area equals the product of the two input areas.

Problem 8.44 — self-convolve a double-slit aperture function
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Self-convolve a double-slit aperture function.

**Formula reference.** Use :eq:`schaum-8-3` and the definitions immediately above it.

**Worked application.**

1. Use the integral definition for continuous shapes or pairwise coordinate sums for impulses; combine coincident contributions before plotting amplitudes.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The double-slit self-convolution is the sum of three triangular lobes: two outer unit-weight autocorrelations and a central lobe with twice their weight.

**Check.** Convolution is commutative, its support width is the sum of input support widths, and total area equals the product of the two input areas.

Problem 8.45 — convolve a point array with a continuous spread function
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Convolve a point array with a continuous spread function.

**Formula reference.** Use :eq:`schaum-8-3` and the definitions immediately above it.

**Worked application.**

1. Use the integral definition for continuous shapes or pairwise coordinate sums for impulses; combine coincident contributions before plotting amplitudes.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Each delta impulse in the discrete input centers one translated copy of the continuous function; summing those copies gives the source figure's output.

**Check.** Convolution is commutative, its support width is the sum of input support widths, and total area equals the product of the two input areas.

Problem 8.46 — construct a further graphical convolution
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Construct a further graphical convolution.

**Formula reference.** Use :eq:`schaum-8-3` and the definitions immediately above it.

**Worked application.**

1. Use the integral definition for continuous shapes or pairwise coordinate sums for impulses; combine coincident contributions before plotting amplitudes.
2. Evaluate all breakpoints or ray/phasor endpoints first, then join only the intervals allowed by the governing relation.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Reverse one plotted function, translate it through every breakpoint of the other, and integrate each overlap interval; the resulting piecewise curve has support equal to the sum of the two input supports.

**Check.** Convolution is commutative, its support width is the sum of input support widths, and total area equals the product of the two input areas.

Problem 8.47 — self-convolve a two-dimensional six-hole mask
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Self-convolve a two-dimensional six-hole mask.

**Formula reference.** Use :eq:`schaum-8-3` and the definitions immediately above it.

**Worked application.**

1. Use the integral definition for continuous shapes or pairwise coordinate sums for impulses; combine coincident contributions before plotting amplitudes.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Pairwise sums of the six aperture centers produce 19 sites on a hexagonal lattice; coincident sums determine their relative weights.

**Check.** Convolution is commutative, its support width is the sum of input support widths, and total area equals the product of the two input areas.
