Chapter 18: Semiconductor Photon Detectors
==========================================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 18.

In-text exercises
-----------------

.. rubric:: Exercise 18.6-1 — Shot/Johnson crossover

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Set :math:`2e(\eta e\Phi)B=4kTB/R_L`.  For the stated ideal detector,
:math:`\boxed{\Phi=6.454\times10^{15}\ \mathrm{s^{-1}}}` and at 1550 nm
:math:`\boxed{P=0.827\ \mathrm{mW}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-18-6-1-result

   \boxed{P=0.827\ \mathrm{mW}}


**Check.**  Equation :eq:`fop-exercise-18-6-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Exercise 18.6-2 — APD sensitivity

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`expectation, variance, and probability identities <fop-formula-probability>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Signal current is :math:`G\eta e\Phi`; shot variance is multiplied by
:math:`G^2F`.  Solving the resulting quadratic in photon count gives the APD
analogue of Eq. (18.6-45); with circuit noise zero, gain cancels and
:math:`\boxed{m_0=F\,\mathrm{SNR}_0}` detected primary electrons.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-18-6-2-result

   \boxed{m_0=F\,\mathrm{SNR}_0}


**Check.**  Equation :eq:`fop-exercise-18-6-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  For a probability result, verify the zero-to-one bounds; when a full distribution is present, also verify normalization and nonnegative variance.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Exercise 18.6-3 — Efficiency and background

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`expectation, variance, and probability identities <fop-formula-probability>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Poisson zero-count detection gives
:math:`\mathrm{BER}=\tfrac12e^{-2\eta n_a}` and hence roughly ten detected
electrons/bit at the stated target.  With background, convolve independent
Poisson signal/background counts and choose the integer threshold minimizing
the two conditional tails; plotting those sums gives sensitivity versus
:math:`n_B`.

End-of-chapter problems
-----------------------

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-18-6-3-result

   \mathrm{BER}=\tfrac12e^{-2\eta n_a}


**Check.**  Equation :eq:`fop-exercise-18-6-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  For a probability result, verify the zero-to-one bounds; when a full distribution is present, also verify normalization and nonnegative variance.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 18.1-1 — Fresnel collection factor

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses the physical definitions stated in the item; no separate calculus or algebraic identity is required for this qualitative comparison.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For each tabulated complex/real index compute :math:`R_s,R_p` from Fresnel
equations; :math:`1-R` at normal incidence and
:math:`1-(R_s+R_p)/2` at 45 degrees are the required factors.  Using the table
at the detector wavelength is essential because semiconductor index is highly
dispersive near its band edge.

**Check.**  For a qualitative conclusion, test every absolute statement against the stated assumptions and at least one limiting case or counterexample.

.. rubric:: Problem 18.1-2 — Ideal responsivity limits

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`stationary-value condition <fop-formula-stationary>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Maximum useful wavelength is :math:`\lambda_g=hc/E_g`; with unit efficiency,
:math:`\boxed{\mathcal R_{max}=e/E_g}` A/W when :math:`E_g` is expressed in
volts/eV.  Insert the Si, GaAs, and InSb gaps from Table 16.2-1.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-1-2-result

   \boxed{\mathcal R_{max}=e/E_g}


**Check.**  Equation :eq:`fop-problem-18-1-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 18.1-3 — One generated pair

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Ramo current magnitudes are :math:`i_e=e v_e/w`, :math:`i_h=e v_h/w`.
From :math:`x=w/3`, durations are distance/velocity:
:math:`t_e=2w/(3v_e)`, :math:`t_h=w/(3v_h)=w/v_e` for :math:`v_e=3v_h`.
Areas are :math:`2e/3` and :math:`e/3`, totaling :math:`e`; these two
rectangles give the requested 10-micrometre timing sketch.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-1-3-result

   v_e=3v_h


**Check.**  Equation :eq:`fop-problem-18-1-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 18.1-4 — Uniform impulsive generation

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

At time :math:`t`, only carriers farther than :math:`vt` from their collecting
contact remain.  Integrating their constant Ramo currents over that shrinking
length gives the two printed triangular currents.  Time integration yields
:math:`Ne/2` from electrons and holes separately, total :math:`Ne`.

**Check.**  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.

.. rubric:: Problem 18.1-5 — Two-photon responsivity

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`J=\zeta\Phi^2`, :math:`\Phi=P/(Ah\nu)`, and output current :math:`AJ`
give
:math:`\boxed{\mathcal R=I/P=\zeta\lambda^2P/[A(hc)^2]}`.  Two-photon
coincidence explains both quadratic wavelength leverage and dependence on
irradiance :math:`P/A`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-1-5-result

   \boxed{\mathcal R=I/P=\zeta\lambda^2P/[A(hc)^2]}


**Check.**  Equation :eq:`fop-problem-18-1-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 18.2-1 — Biased photoconductor

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

If conductance :math:`g=aP`, divider voltage is
:math:`\boxed{V_R=V(RaP)/(1+RaP)}`.  It is linear for :math:`RaP\ll1` and
saturates at the supply voltage for large optical power.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-2-1-result

   \boxed{V_R=V(RaP)/(1+RaP)}


**Check.**  Equation :eq:`fop-problem-18-2-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 18.2-2 — Illuminated intrinsic silicon

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Generation is :math:`\eta P_v/(hc/\lambda)=2.52\times10^{15}`
:math:`\mathrm{cm^{-3}s^{-1}}`; :math:`\Delta n=G\tau=2.52\times10^{10}`
:math:`\mathrm{cm^{-3}}`.  Since both carrier types rise equally, conductivity
increases by :math:`\boxed{\Delta n/n_i=167.8\%}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-2-2-result

   \boxed{\Delta n/n_i=167.8\%}


**Check.**  Equation :eq:`fop-problem-18-2-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 18.3-1 — p-i-n efficiency

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`\eta=2/6=\boxed{1/3}` and
:math:`\mathcal R=\eta e\lambda/(hc)=\boxed{0.417\ \mathrm{A/W}}` at 1550 nm.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-3-1-result

   \mathcal R=\eta e\lambda/(hc)=\boxed{0.417\ \mathrm{A/W}}


**Check.**  Equation :eq:`fop-problem-18-3-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 18.4-1 — APD efficiency/current

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`\eta=\mathcal R hc/(Ge\lambda)=\boxed{0.480}`.  For
:math:`10^{10}` photons/s, :math:`I=G\eta e\Phi=
\boxed{15.38\ \mathrm{nA}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-4-1-result

   I=G\eta e\Phi=
   \boxed{15.38\ \mathrm{nA}}


**Check.**  Equation :eq:`fop-problem-18-4-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 18.4-2 — Equal ionization coefficients

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

With :math:`\alpha_e=\alpha_h`, coupled multiplication equations integrate
to a geometric feedback series; summing it gives
:math:`\boxed{G=1/(1-\alpha_e w)}` before breakdown.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-4-2-result

   \boxed{G=1/(1-\alpha_e w)}


**Check.**  Equation :eq:`fop-problem-18-4-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.

.. rubric:: Problem 18.5-1 — APD excess noise

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

McIntyre's result :math:`F=kG+(1-k)(2-1/G)` gives :math:`F\to2` for
:math:`k=0,G\gg1`; then :math:`G=e^{\alpha_ew}`.  Responsivity is
:math:`\eta Ge/E_g`; for :math:`k=0.01,G=70`, insert those values in the same
formula to compare with two.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-5-1-result

   k=0.01,G=70


**Check.**  Equation :eq:`fop-problem-18-5-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 18.5-2 — Multilayer APD

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Each stage multiplies the mean by :math:`1+P`; independence yields
:math:`\boxed{G=(1+P)^l}`.  With :math:`P=\alpha w/l` and :math:`l\to\infty`,
this tends to :math:`e^{\alpha w}`, the continuous single-carrier APD.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-5-2-result

   \boxed{G=(1+P)^l}


**Check.**  Equation :eq:`fop-problem-18-5-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 18.5-3 — One-stage PMT noise

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`expectation, variance, and probability identities <fop-formula-probability>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For Poisson secondary yield :math:`\bar G=\delta` and
:math:`\langle G^2\rangle=\delta^2+\delta`; hence
:math:`\boxed{F=1+1/\delta}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-5-3-result

   \boxed{F=1+1/\delta}


**Check.**  Equation :eq:`fop-problem-18-5-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  For a probability result, verify the zero-to-one bounds; when a full distribution is present, also verify normalization and nonnegative variance.

.. rubric:: Problem 18.5-4 — Photoconductor gain noise

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`expectation, variance, and probability identities <fop-formula-probability>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

With :math:`G=\tau/t_e` and exponential lifetime,
:math:`\langle\tau^2\rangle=2\bar\tau^2`; therefore
:math:`\boxed{F=\langle G^2\rangle/\bar G^2=2}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-5-4-result

   \boxed{F=\langle G^2\rangle/\bar G^2=2}


**Check.**  Equation :eq:`fop-problem-18-5-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  For a probability result, verify the zero-to-one bounds; when a full distribution is present, also verify normalization and nonnegative variance.

.. rubric:: Problem 18.5-5 — RC noise bandwidth

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`Fourier-transform and convolution identities <fop-formula-fourier>`, :ref:`integration identities <fop-formula-integration>`, and :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Fourier transforming :math:`h=e^{-t/\tau}/\tau` and integrating
:math:`|H|^2` gives :math:`B=1/(4\tau)=1/(4RC)`.  For 1 kohm and 5 pF,
:math:`\boxed{B=50\ \mathrm{MHz}}` and Johnson RMS current
:math:`\boxed{28.8\ \mathrm{nA}}` at 300 K.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-5-5-result

   \boxed{28.8\ \mathrm{nA}}


**Check.**  Equation :eq:`fop-problem-18-5-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 18.5-6 — Changing APD ionization ratio

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

With negligible circuit noise, SNR is inversely proportional to
:math:`F=kG+(1-k)(2-1/G)`.  Evaluate :math:`F(0.1,100)` and
:math:`F(0.2,100)`; their inverse ratio is the SNR factor.  For
:math:`G\gg2(1-k)/k`, :math:`F\simeq kG`, proving :math:`\mathrm{SNR}\propto1/G`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-5-6-result

   F=kG+(1-k)(2-1/G)


**Check.**  Equation :eq:`fop-problem-18-5-6-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 18.5-7 — APD receiver noise budget

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Compute signal primary current :math:`I_p=\eta eP/(h\nu)`, multiplied output
:math:`GI_p`, APD shot RMS
:math:`[2eBFG^2(I_p+I_d)]^{1/2}`, and Johnson RMS
:math:`(4kTB/R_L)^{1/2}`.  Add variances, not RMS values; SNR is
:math:`(GI_p)^2` divided by their sum.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-5-7-result

   I_p=\eta eP/(h\nu)


**Check.**  Equation :eq:`fop-problem-18-5-7-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 18.5-8 — Optimum APD gain

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, :ref:`integration identities <fop-formula-integration>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Write normalized noise denominator
:math:`F(G)+100/G^2` with :math:`k=0.2`; differentiate and solve its positive
root.  The ratio of the original p-i-n denominator 101 to the minimized APD
denominator is the SNR improvement.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-5-8-result

   k=0.2


**Check.**  Equation :eq:`fop-problem-18-5-8-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.

.. rubric:: Problem 18.5-9 — Shot-noise sensitivity

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

With no circuit noise, :math:`\mathrm{SNR}=\eta\Phi/(2B)` for the chapter's
one-sided bandwidth convention.  Thus
:math:`\boxed{P=(2B\,\mathrm{SNR}/\eta)(hc/\lambda)}`; insert
:math:`B=100` MHz, SNR :math:`10^3`, eta 0.8.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-5-9-result

   \boxed{P=(2B\,\mathrm{SNR}/\eta)(hc/\lambda)}


**Check.**  Equation :eq:`fop-problem-18-5-9-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 18.5-10 — Three-detector comparison

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`expectation, variance, and probability identities <fop-formula-probability>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

For each device compute mean output :math:`G\eta e\Phi`; detector variance
:math:`2e^2B\eta\Phi\langle G^2\rangle` and common Johnson variance
:math:`4kTB/R`.  Use :math:`\langle G^2\rangle=G^2F`; a device is detectable
when resulting power SNR exceeds one.  This common table prevents confusing
large gain with improved photon-limited SNR.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-5-10-result

   \langle G^2\rangle=G^2F


**Check.**  Equation :eq:`fop-problem-18-5-10-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  For a probability result, verify the zero-to-one bounds; when a full distribution is present, also verify normalization and nonnegative variance.

.. rubric:: Problem 18.5-11 — Wavelength scaling

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`power and decibel conversions <fop-formula-power-decibels>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

The same photons/bit require power proportional to photon energy
:math:`1/\lambda`.  Therefore sensitivity improves by
:math:`10\log_{10}(1300/870)=1.744` dB:
:math:`\boxed{-77.74\ \mathrm{dBm}}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-5-11-result

   \boxed{-77.74\ \mathrm{dBm}}


**Check.**  Equation :eq:`fop-problem-18-5-11-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Converting the final decibel value back to a linear power ratio checks the logarithm, sign, and accumulated loss budget.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 18.5-12 — Changed zero-count BER

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`expectation, variance, and probability identities <fop-formula-probability>` and :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Use :math:`P_e\propto e^{-\eta PT/(hc/\lambda)}`.  Relative exponent factors
are 1300/870, 2, 0.5, 1, and (with a nonzero decision threshold) the APD
excess-noise-tail calculation.  Ideal noiseless gain alone does not change
zero-primary-count probability; doubling power squares the original
:math:`10^{-10}` exponential factor.

**Check.**  For a probability result, verify the zero-to-one bounds; when a full distribution is present, also verify normalization and nonnegative variance.

.. rubric:: Problem 18.5-13 — Detecting AM on background

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`expectation, variance, and probability identities <fop-formula-probability>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Signal mean-square current is :math:`(\mathcal R P_s)^2/2`; background shot
variance is :math:`2e\mathcal RP_0B`.  Solving gives
:math:`\boxed{P_{s,min}=2\sqrt{eBP_0\mathrm{SNR}_0/\mathcal R}}`; sensitivity
degrades as :math:`\sqrt{P_0}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-5-13-result

   \boxed{P_{s,min}=2\sqrt{eBP_0\mathrm{SNR}_0/\mathcal R}}


**Check.**  Equation :eq:`fop-problem-18-5-13-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  For a probability result, verify the zero-to-one bounds; when a full distribution is present, also verify normalization and nonnegative variance.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 18.5-14 — Counting sensitivity

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`expectation, variance, and probability identities <fop-formula-probability>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Poisson power SNR equals detected mean, so SNR :math:`10^3` requires 1000
photoelectrons or :math:`\boxed{2000}` photons at eta 0.5.  At 870 nm over 1
microsecond, :math:`\boxed{P=4.57\times10^{-10}\ \mathrm W}`; zero-count
probability is :math:`e^{-1000}`.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-5-14-result

   \boxed{P=4.57\times10^{-10}\ \mathrm W}


**Check.**  Equation :eq:`fop-problem-18-5-14-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  For a probability result, verify the zero-to-one bounds; when a full distribution is present, also verify normalization and nonnegative variance.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 18.5-15 — One-dynode PMT

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`expectation, variance, and probability identities <fop-formula-probability>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Condition on input :math:`n=0,1`; the zero branch remains zero output and the
one-photon branch has the stated dynode secondary distribution.  Therefore
the output law is a 50:50 mixture of a delta at zero and that secondary law;
use total expectation/variance to obtain its mean, excess-noise factor, and
SNR without treating the input as Poisson.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-18-5-15-result

   n=0,1


**Check.**  Equation :eq:`fop-problem-18-5-15-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  For a probability result, verify the zero-to-one bounds; when a full distribution is present, also verify normalization and nonnegative variance.
