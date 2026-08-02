Chapter 16: Semiconductor Optics
================================

Source: Saleh and Teich, *Fundamentals of Photonics*, second edition,
Chapter 16.

In-text exercises
-----------------

.. rubric:: Exercise 16.1-1 — Free-electron dispersion

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-16-1-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_16_01_01.svg
   :alt: Illustrated calculation map for Exercise 16.1-1, Free-electron dispersion
   :align: center
   :width: 95%

   The diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route.


**Step 2 — Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Substitute :math:`e^{-jkx}` in the free Schrödinger equation to get
:math:`\boxed{E=\hbar^2k^2/(2m_0)=p^2/(2m_0)}`.  Group velocity
:math:`\hbar^{-1}dE/dk=\hbar k/m_0=p/m_0` matches the particle velocity.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-16-1-1-result

   \boxed{E=\hbar^2k^2/(2m_0)=p^2/(2m_0)}


**Step 5 — Check.**  Equation :eq:`fop-exercise-16-1-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Exercise 16.1-2 — Boltzmann limit of Fermi occupation

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-16-1-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_16_01_02.svg
   :alt: Illustrated calculation map for Exercise 16.1-2, Boltzmann limit of Fermi occupation
   :align: center
   :width: 95%

   The diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route.


**Step 2 — Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

When :math:`E-E_F\gg kT`, :math:`f\simeq e^{-(E-E_F)/kT}`; similarly
:math:`1-f\simeq e^{-(E_F-E)/kT}` below :math:`E_F`.  Integrating these with
the band densities of states gives the chapter's :math:`n=N_ce^{-(E_c-E_F)/kT}`
and :math:`p=N_ve^{-(E_F-E_v)/kT}`.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-16-1-2-result

   p=N_ve^{-(E_F-E_v)/kT}


**Step 5 — Check.**  Equation :eq:`fop-exercise-16-1-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.

.. rubric:: Exercise 16.1-3 — Quasi-Fermi levels

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-16-1-3-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_16_01_03.svg
   :alt: Illustrated calculation map for Exercise 16.1-3, Quasi-Fermi levels
   :align: center
   :width: 95%

   The diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route.


**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

At zero temperature fill the 3-D density of states to :math:`k_F=(3\pi^2n)^{1/3}`:
:math:`E_{Fc}=E_c+\hbar^2(3\pi^2n)^{2/3}/(2m_e)` and
:math:`E_{Fv}=E_v-\hbar^2(3\pi^2p)^{2/3}/(2m_h)`.  In the Boltzmann regime
invert the preceding exponentials instead.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-16-1-3-result

   E_{Fv}=E_v-\hbar^2(3\pi^2p)^{2/3}/(2m_h)


**Step 5 — Check.**  Equation :eq:`fop-exercise-16-1-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Exercise 16.1-4 — Injected GaAs carriers

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-16-1-4-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_16_01_04.svg
   :alt: Illustrated calculation map for Exercise 16.1-4, Injected GaAs carriers
   :align: center
   :width: 95%

   The diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route.


**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

:math:`p_0=n_i^2/n_0`; low-injection lifetime is
:math:`\tau=[r(n_0+p_0)]^{-1}`.  Steady excess solves
:math:`R=r[(n_0+\Delta n)(p_0+\Delta n)-n_i^2]`; insert the stated values and
select the positive quadratic root, then compute the two quasi-Fermi levels
from Exercise 16.1-3.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-16-1-4-result

   R=r[(n_0+\Delta n)(p_0+\Delta n)-n_i^2]


**Step 5 — Check.**  Equation :eq:`fop-exercise-16-1-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Exercise 16.1-5 — Infinite quantum well

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-16-1-5-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_16_01_05.svg
   :alt: Illustrated calculation map for Exercise 16.1-5, Infinite quantum well
   :align: center
   :width: 95%

   The diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route.


**Step 2 — Mathematical formulas used.**  The working uses :ref:`trigonometric and small-angle identities <fop-formula-trigonometry>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Boundary conditions :math:`\psi(0)=\psi(d)=0` select
:math:`\psi_q=\sqrt{2/d}\sin(q\pi x/d)` and
:math:`\boxed{E_q=\hbar^2q^2\pi^2/(2md^2)}`.  A finite well has lower energies,
evanescent tails, and only finitely many bound roots of its tangent/cotangent
equations.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-16-1-5-result

   \boxed{E_q=\hbar^2q^2\pi^2/(2md^2)}


**Step 5 — Check.**  Equation :eq:`fop-exercise-16-1-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  The zero-angle or paraxial limit supplies an independent sign and magnitude check whenever that limit is part of the model.

.. rubric:: Exercise 16.2-1 — Semiconductor gain condition

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-16-2-1-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_16_02_01.svg
   :alt: Illustrated calculation map for Exercise 16.2-1, Semiconductor gain condition
   :align: center
   :width: 95%

   The diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route.


**Step 2 — Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Thermal equilibrium has one Fermi level and detailed balance makes absorption
larger.  In quasi-equilibrium, emission exceeds absorption when
:math:`\boxed{E_{Fc}-E_{Fv}>h\nu}` for the same-k states—the Bernard--Duraffourg
population-inversion condition.

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-16-2-1-result

   \boxed{E_{Fc}-E_{Fv}>h\nu}


**Step 5 — Check.**  Equation :eq:`fop-exercise-16-2-1-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Exercise 16.2-2 — Peak direct absorption

**Step 1 — Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

.. _fop-exercise-16-2-2-illustration:

.. figure:: /_static/knowledge_base/worked_exercises/fundamentals_of_photonics/exercise_illustrations/exercise_16_02_02.svg
   :alt: Illustrated calculation map for Exercise 16.2-2, Peak direct absorption
   :align: center
   :width: 95%

   The diagram identifies the input quantities, physical operation, requested
   result, variable meanings, and an independent verification route.


**Step 2 — Mathematical formulas used.**  The working uses :ref:`stationary-value condition <fop-formula-stationary>`, :ref:`product, quotient, and chain rules <fop-formula-product-chain>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Step 3 — Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Differentiate the equilibrium direct-gap form
:math:`\alpha\propto\sqrt{h\nu-E_g}/\nu`; its maximum occurs at
:math:`h\nu=2E_g`.  Therefore :math:`\boxed{\lambda_p=hc/(2E_g)}`; for GaAs
:math:`E_g=1.42` eV, :math:`\boxed{\lambda_p=436.6\ \mathrm{nm}}`.

End-of-chapter problems
-----------------------

**Step 4 — State the numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-exercise-16-2-2-result

   \boxed{\lambda_p=436.6\ \mathrm{nm}}


**Step 5 — Check.**  Equation :eq:`fop-exercise-16-2-2-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 16.1-6 — Hydrogenic donors

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Use :math:`E_D=13.606(m^*/m_0)/\epsilon_r^2` eV and
:math:`r_D=a_0\epsilon_r/(m^*/m_0)`.  Results (energy, radius) are Si
(88.1 meV, 0.664 nm), GaAs (5.63 meV, 9.82 nm), GaN (69.7 meV, 1.65 nm), and
polyacetylene (1.51 eV, 0.159 nm).  The last two radii approach lattice scale,
where bulk dielectric/effective-mass theory is least credible.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-16-1-6-result

   r_D=a_0\epsilon_r/(m^*/m_0)


**Check.**  Equation :eq:`fop-problem-16-1-6-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 16.1-7 — Intrinsic and doped Fermi levels

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Setting :math:`n=p` gives
:math:`\boxed{E_i=(E_c+E_v)/2+(3/4)kT\ln(m_h/m_e)}`.  With nondegenerate
doping, charge neutrality gives :math:`E_F=E_i+kT\ln(n/n_i)` for n type or
:math:`E_F=E_i-kT\ln(p/n_i)` for p type.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-16-1-7-result

   \boxed{E_i=(E_c+E_v)/2+(3/4)kT\ln(m_h/m_e)}


**Check.**  Equation :eq:`fop-problem-16-1-7-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 16.1-8 — Strong-injection decay

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

After the source turns off,
:math:`d\Delta n/dt=-r(\Delta n)^2`.  Separation gives
:math:`\boxed{\Delta n(t)=\Delta n_0/[1+r\Delta n_0(t-t_0)]}`—a reciprocal
power law, not an exponential.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-16-1-8-result

   \boxed{\Delta n(t)=\Delta n_0/[1+r\Delta n_0(t-t_0)]}


**Check.**  Equation :eq:`fop-problem-16-1-8-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 16.1-9 — Alloy bowing

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

At each plotted composition solve
:math:`\boxed{b=[xE_{AC}+(1-x)E_{BC}-E_g(x)]/[x(1-x)]}` and average consistent
points for every listed alloy.  Large :math:`b` means gap tuning is strongly
nonlinear even while lattice constant follows Vegard; it changes which
composition simultaneously provides a desired gap and substrate lattice match.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-16-1-9-result

   \boxed{b=[xE_{AC}+(1-x)E_{BC}-E_g(x)]/[x(1-x)]}


**Check.**  Equation :eq:`fop-problem-16-1-9-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 16.1-10 — GaAs/AlGaAs well

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Thirty-percent Al raises total gap by :math:`30(12.47)=374.1` meV; 60% gives
electron barrier :math:`\boxed{V_0=224.5\ \mathrm{meV}}`.  From
:math:`\sqrt{mV_0d^2/(2\hbar^2)}=4`,
:math:`\boxed{d=4\sqrt{2\hbar^2/(mV_0)}}`; solve the finite-well even/odd
equations to place the levels inside the drawn conduction/valence offsets.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-16-1-10-result

   \boxed{d=4\sqrt{2\hbar^2/(mV_0)}}


**Check.**  Equation :eq:`fop-problem-16-1-10-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.

.. rubric:: Problem 16.2-3 — Delta-lineshape approximation

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`Fourier-transform and convolution identities <fop-formula-fourier>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

At 300 K plot the lifetime Lorentzian width :math:`1/(\pi T_2)` beside the
:math:`kT/h` widths of occupation and joint DOS.  For :math:`T_2=1` ps the
lineshape is much narrower, validating replacement by a delta function for
both emission and absorption; numerical convolution quantifies the small error.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-16-2-3-result

   T_2=1


**Check.**  Equation :eq:`fop-problem-16-2-3-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Transform dimensions and the expected even/odd or conjugate symmetry provide an independent check on signs and scale factors.

.. rubric:: Problem 16.2-4 — Thermal spontaneous peak

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>` and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Maximize :math:`\sqrt{h\nu-E_g}e^{-h\nu/kT}` to obtain
:math:`\boxed{h\nu_p=E_g+kT/2}`.  Substitution gives the printed closed peak
rate.  Nondegenerate doping shifts Fermi factors but cancels under thermal
mass action until degeneracy; insert GaAs parameters in that formula for the
requested numerical rate.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-16-2-4-result

   \boxed{h\nu_p=E_g+kT/2}


**Check.**  Equation :eq:`fop-problem-16-2-4-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Check that dimensions agree term by term, then test the simplest symmetry or limiting case for the expected sign and scale.

.. rubric:: Problem 16.2-5 — Integrated radiative rate

**Definitions and setup.**  Symbols are local to this item and follow the chapter convention.  Each physical quantity and supplied numerical value is introduced at its first use below; angles are in radians unless a degree symbol is shown, and units are retained through numerical substitution.

**Mathematical formulas used.**  The working uses :ref:`integration identities <fop-formula-integration>`, :ref:`exponential, logarithmic, and phasor identities <fop-formula-exponentials>`, and :ref:`algebraic rearrangement and dimensional checks <fop-formula-algebra>`.

**Worked derivation.**  The calculation is kept in symbolic form until the governing relation has been rearranged for the requested quantity.

Set :math:`x=h\nu-E_g` and use the supplied gamma integral to obtain the
printed :math:`(kT)^{3/2}e^{-E_g/kT}` rate.  The peak-times-width estimate has
the same scaling.  Equating it to :math:`r_rn_i^2` gives
:math:`\boxed{r_r=\sqrt2\pi^{3/2}\hbar^3/
[(m_e+m_h)^{3/2}(kT)^{3/2}T_r]}`; GaAs evaluation is of order
:math:`10^{-10}\ \mathrm{cm^3/s}`, consistent with the table.

**Numbered result.**  The principal result obtained in the working is

.. math::
   :label: fop-problem-16-2-5-result

   \boxed{r_r=\sqrt2\pi^{3/2}\hbar^3/
   [(m_e+m_h)^{3/2}(kT)^{3/2}T_r]}


**Check.**  Equation :eq:`fop-problem-16-2-5-result` can be checked by substituting it back into the preceding governing relation and reversing the algebraic steps.  Differentiation of an antiderivative, or normalization of a definite integral, checks the integration step.  Repeat the substitution with unrounded intermediate values and retain the displayed units; the final unit must have the requested dimension.
