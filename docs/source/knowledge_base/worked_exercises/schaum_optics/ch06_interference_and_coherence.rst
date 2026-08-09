Chapter 6: Interference and Coherence
=====================================

Source: Eugene Hecht, *Schaum's Outline of Theory and Problems of
Optics* (1975), Chapter 6.  The entries below cover only the
chapter's **Supplementary Problems**; prompts are paraphrased and are not
reproduced.

Each topic derives its shared formula once.  Every numbered problem then
applies that derivation to the particular proof, calculation, or construction
in the book.  Read the source diagram alongside entries that depend on a figure.

Interference of two waves
-------------------------

**Formula and definitions.**

.. math::
   :label: schaum-6-1

   I=I_1+I_2+2\sqrt{I_1I_2}\,|\hat{\mathbf e}_1\cdot\hat{\mathbf e}_2|\cos\delta,\qquad \delta=ka\sin\theta+\delta_0

Add fields before time averaging.  Equal parallel-polarized
sources give :math:`I=4I_0\cos^2(\delta/2)`; orthogonal polarization removes
the cross term.  Maxima and minima follow from :math:`\delta=2m\pi` and
:math:`(2m+1)\pi`, respectively.

Problem 6.52 — locate a minimum from two in-phase radio sources
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Locate a minimum from two in-phase radio sources.

**Formula reference.** Use :eq:`schaum-6-1` and the definitions immediately above it.

**Worked application.**

1. Express the path difference geometrically, add any source phase, impose the required maximum/minimum phase, and solve for position or angle.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The first accessible minimum is 2.25 m along the perpendicular bisector.

**Check.** A full angular average of the cosine cross term vanishes for well-separated sources, so integrated energy remains the sum of source energies.

Problem 6.53 — identify when orthogonally polarized sources add without fringes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Identify when orthogonally polarized sources add without fringes.

**Formula reference.** Use :eq:`schaum-6-1` and the definitions immediately above it.

**Worked application.**

1. Express the path difference geometrically, add any source phase, impose the required maximum/minimum phase, and solve for position or angle.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The cross term vanishes when :math:`\hat{\mathbf e}_1\cdot\hat{\mathbf e}_2=0`; the measured irradiance is then :math:`I_1+I_2` everywhere.

**Check.** A full angular average of the cosine cross term vanishes for well-separated sources, so integrated energy remains the sum of source energies.

Problem 6.54 — describe a two-source microwave radiation pattern
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Describe a two-source microwave radiation pattern.

**Formula reference.** Use :eq:`schaum-6-1` and the definitions immediately above it.

**Worked application.**

1. Express the path difference geometrically, add any source phase, impose the required maximum/minimum phase, and solve for position or angle.
2. Use signs, directions, and limiting behavior from the governing equations to classify the physical result.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Principal lobes occur at 0°, 30°, 90°, 150°, 180°, 210°, 270°, and 330° from the normal to the source line.

**Check.** A full angular average of the cosine cross term vanishes for well-separated sources, so integrated energy remains the sum of source energies.

Problem 6.55 — verify spatially averaged energy conservation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Verify spatially averaged energy conservation.

**Formula reference.** Use :eq:`schaum-6-1` and the definitions immediately above it.

**Worked application.**

1. Express the path difference geometrically, add any source phase, impose the required maximum/minimum phase, and solve for position or angle.
2. Evaluate both sides independently from the definitions and confirm equality without circular substitution.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** For :math:`a\gg\lambda`, the spatial average of :math:`\cos\delta` is zero and the integrated irradiance is :math:`I_1+I_2`; for :math:`a\ll\lambda` the pair behaves as one coherent source.

**Check.** A full angular average of the cosine cross term vanishes for well-separated sources, so integrated energy remains the sum of source energies.

Problem 6.56 — include an intrinsic phase in the two-source pattern
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Include an intrinsic phase in the two-source pattern.

**Formula reference.** Use :eq:`schaum-6-1` and the definitions immediately above it.

**Worked application.**

1. Express the path difference geometrically, add any source phase, impose the required maximum/minimum phase, and solve for position or angle.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** For equal sources, :math:`I(\theta)=4I_0\cos^2[(ka\sin\theta+\delta_0)/2]`.

**Check.** A full angular average of the cosine cross term vanishes for well-separated sources, so integrated energy remains the sum of source energies.

Problem 6.57 — find lobe rotation caused by a thirty-degree phase shift
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find lobe rotation caused by a thirty-degree phase shift.

**Formula reference.** Use :eq:`schaum-6-1` and the definitions immediately above it.

**Worked application.**

1. Express the path difference geometrically, add any source phase, impose the required maximum/minimum phase, and solve for position or angle.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The forward lobe rotates by about :math:`2.39^\circ`.

**Check.** A full angular average of the cosine cross term vanishes for well-separated sources, so integrated energy remains the sum of source energies.

Problem 6.58 — choose phase shift for a twenty-degree lobe rotation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Choose phase shift for a twenty-degree lobe rotation.

**Formula reference.** Use :eq:`schaum-6-1` and the definitions immediately above it.

**Worked application.**

1. Express the path difference geometrically, add any source phase, impose the required maximum/minimum phase, and solve for position or angle.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The required adjacent-source phase difference has magnitude about :math:`61.6^\circ`.

**Check.** A full angular average of the cosine cross term vanishes for well-separated sources, so integrated energy remains the sum of source energies.

Wavefront-splitting interferometers
-----------------------------------

**Formula and definitions.**

.. math::
   :label: schaum-6-2

   \Delta y=\frac{\lambda_0L}{a}=\frac{\lambda_0}{\beta},\qquad \delta=\frac{2\pi}{\lambda_0}\,\mathrm{OPD}

In the paraxial limit the path difference is
:math:`ay/L`, so successive orders differ by :math:`\lambda_0L/a`.  Mirrors,
biprisms, and split lenses first create two coherent virtual or real images;
compute their effective separation and then reuse Young's formula.

Problem 6.59 — express Young-fringe spacing using source angular separation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Express young-fringe spacing using source angular separation.

**Formula reference.** Use :eq:`schaum-6-2` and the definitions immediately above it.

**Worked application.**

1. Reduce the apparatus to two coherent sources, calculate their separation and relative phase (including reflection or plate shifts), then apply the fringe-order condition.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Since :math:`\beta\simeq a/L`, Young's result becomes :math:`\Delta y=\lambda_0/\beta`.

**Check.** Fringe spacing grows with wavelength and propagation distance and decreases with source separation; a zero-OPD white-light fringe is achromatic.

Problem 6.60 — infer slit spacing from helium fringes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer slit spacing from helium fringes.

**Formula reference.** Use :eq:`schaum-6-2` and the definitions immediately above it.

**Worked application.**

1. Reduce the apparatus to two coherent sources, calculate their separation and relative phase (including reflection or plate shifts), then apply the fringe-order condition.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`a=\lambda L/\Delta y\approx2.64\,\mathrm{mm}`.

**Check.** Fringe spacing grows with wavelength and propagation distance and decreases with source separation; a zero-OPD white-light fringe is achromatic.

Problem 6.61 — find virtual-source angular separation in a mirror geometry
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find virtual-source angular separation in a mirror geometry.

**Formula reference.** Use :eq:`schaum-6-2` and the definitions immediately above it.

**Worked application.**

1. Reduce the apparatus to two coherent sources, calculate their separation and relative phase (including reflection or plate shifts), then apply the fringe-order condition.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The source geometry gives an effective virtual-source separation :math:`2Ra/(R+a)` (or its corresponding small angle after division by the viewing distance).

**Check.** Fringe spacing grows with wavelength and propagation distance and decreases with source separation; a zero-OPD white-light fringe is achromatic.

Problem 6.62 — locate a Fresnel double-mirror fringe
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Locate a fresnel double-mirror fringe.

**Formula reference.** Use :eq:`schaum-6-2` and the definitions immediately above it.

**Worked application.**

1. Reduce the apparatus to two coherent sources, calculate their separation and relative phase (including reflection or plate shifts), then apply the fringe-order condition.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The seventh bright fringe is about 1.98 mm from the central axis.

**Check.** Fringe spacing grows with wavelength and propagation distance and decreases with source separation; a zero-OPD white-light fringe is achromatic.

Problem 6.63 — infer Fresnel-biprism angle from fringe spacing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer fresnel-biprism angle from fringe spacing.

**Formula reference.** Use :eq:`schaum-6-2` and the definitions immediately above it.

**Worked application.**

1. Reduce the apparatus to two coherent sources, calculate their separation and relative phase (including reflection or plate shifts), then apply the fringe-order condition.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The biprism apex angle is about :math:`0.843^\circ`.

**Check.** Fringe spacing grows with wavelength and propagation distance and decreases with source separation; a zero-OPD white-light fringe is achromatic.

Problem 6.64 — generalize biprism fringes to liquid immersion
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Generalize biprism fringes to liquid immersion.

**Formula reference.** Use :eq:`schaum-6-2` and the definitions immediately above it.

**Worked application.**

1. Reduce the apparatus to two coherent sources, calculate their separation and relative phase (including reflection or plate shifts), then apply the fringe-order condition.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Replace the prism relative index by :math:`n_p/n_l`; the fringe spacing becomes inversely proportional to :math:`n_p-n_l` and reduces to the air formula for :math:`n_l=1`.

**Check.** Fringe spacing grows with wavelength and propagation distance and decreases with source separation; a zero-OPD white-light fringe is achromatic.

Problem 6.65 — track Lloyd-mirror central fringe after inserting a plate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Track lloyd-mirror central fringe after inserting a plate.

**Formula reference.** Use :eq:`schaum-6-2` and the definitions immediately above it.

**Worked application.**

1. Reduce the apparatus to two coherent sources, calculate their separation and relative phase (including reflection or plate shifts), then apply the fringe-order condition.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** A plate of thickness :math:`d` adds :math:`(n-1)d`; the central dark band moves by :math:`(n-1)d/\lambda_0` fringe spacings.  White light locates the zero-OPD band.

**Check.** Fringe spacing grows with wavelength and propagation distance and decreases with source separation; a zero-OPD white-light fringe is achromatic.

Problem 6.66 — infer Lloyd source height from fringe spacing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer lloyd source height from fringe spacing.

**Formula reference.** Use :eq:`schaum-6-2` and the definitions immediately above it.

**Worked application.**

1. Reduce the apparatus to two coherent sources, calculate their separation and relative phase (including reflection or plate shifts), then apply the fringe-order condition.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The Lloyd source height is about 0.75 mm.

**Check.** Fringe spacing grows with wavelength and propagation distance and decreases with source separation; a zero-OPD white-light fringe is achromatic.

Problem 6.67 — explain interference from a Billet split lens
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Explain interference from a billet split lens.

**Formula reference.** Use :eq:`schaum-6-2` and the definitions immediately above it.

**Worked application.**

1. Reduce the apparatus to two coherent sources, calculate their separation and relative phase (including reflection or plate shifts), then apply the fringe-order condition.
2. Identify the controlling phase or conservation relation, then use it to account for every stated observation.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The two displaced real images of the original point source are mutually coherent in-phase emitters; their overlap region therefore contains Young-type fringes.

**Check.** Fringe spacing grows with wavelength and propagation distance and decreases with source separation; a zero-OPD white-light fringe is achromatic.

Amplitude splitting by thin films
---------------------------------

**Formula and definitions.**

.. math::
   :label: schaum-6-3

   \delta=\frac{4\pi nd\cos\theta_t}{\lambda_0}+\delta_r,\qquad 2nd\cos\theta_t=m\lambda_0,\qquad r_m^2\simeq \frac{m\lambda_0R}{n}

The round-trip optical thickness is
:math:`2nd\cos\theta_t`.  Add :math:`\pi` for exactly one reflection from a
higher-index boundary.  A quarter-wave coating sets
:math:`d=\lambda_0/(4n_c)` and ideally
:math:`n_c=\sqrt{n_0n_s}`.  Newton-ring radii follow from
:math:`d(r)\simeq r^2/(2R)`.

Problem 6.68 — compute reflected-ray phase difference through a film
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Compute reflected-ray phase difference through a film.

**Formula reference.** Use :eq:`schaum-6-3` and the definitions immediately above it.

**Worked application.**

1. Determine the reflection phase reversals first, write the correct bright/dark order condition, then solve for phase, thickness, radius, index, or position.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The propagation contribution is about :math:`22.63\pi`; after the single reflection reversal the equivalent phase is about :math:`1.63\pi` modulo :math:`2\pi`.

**Check.** Changing film thickness by λ0/(2n cos θt) advances one full fringe; ring-radius squared must vary linearly with order.

Problem 6.69 — derive equal-inclination extrema
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive equal-inclination extrema.

**Formula reference.** Use :eq:`schaum-6-3` and the definitions immediately above it.

**Worked application.**

1. Determine the reflection phase reversals first, write the correct bright/dark order condition, then solve for phase, thickness, radius, index, or position.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** With one reflection reversal, reflected maxima satisfy :math:`d\cos\theta_t=(2m+1)\lambda_0/(4n)` and minima :math:`d\cos\theta_t=m\lambda_0/(2n)`.

**Check.** Changing film thickness by λ0/(2n cos θt) advances one full fringe; ring-radius squared must vary linearly with order.

Problem 6.70 — identify the central order of a parallel plate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Identify the central order of a parallel plate.

**Formula reference.** Use :eq:`schaum-6-3` and the definitions immediately above it.

**Worked application.**

1. Determine the reflection phase reversals first, write the correct bright/dark order condition, then solve for phase, thickness, radius, index, or position.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Using the plate thickness printed in the source, :math:`2nd/\lambda_0=10{,}000`; the single reflection reversal makes the central fringe a minimum.

**Check.** Changing film thickness by λ0/(2n cos θt) advances one full fringe; ring-radius squared must vary linearly with order.

Problem 6.71 — design an ideal single-layer antireflection coating
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Design an ideal single-layer antireflection coating.

**Formula reference.** Use :eq:`schaum-6-3` and the definitions immediately above it.

**Worked application.**

1. Determine the reflection phase reversals first, write the correct bright/dark order condition, then solve for phase, thickness, radius, index, or position.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`n_c=\sqrt{2.409}=1.552` and the minimum thickness is about 94.9 nm.

**Check.** Changing film thickness by λ0/(2n cos θt) advances one full fringe; ring-radius squared must vary linearly with order.

Problem 6.72 — choose magnesium-fluoride coating thickness
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Choose magnesium-fluoride coating thickness.

**Formula reference.** Use :eq:`schaum-6-3` and the definitions immediately above it.

**Worked application.**

1. Determine the reflection phase reversals first, write the correct bright/dark order condition, then solve for phase, thickness, radius, index, or position.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The minimum magnesium-fluoride thickness is about 106.7 nm.

**Check.** Changing film thickness by λ0/(2n cos θt) advances one full fringe; ring-radius squared must vary linearly with order.

Problem 6.73 — infer wedge angle from fringe spacing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer wedge angle from fringe spacing.

**Formula reference.** Use :eq:`schaum-6-3` and the definitions immediately above it.

**Worked application.**

1. Determine the reflection phase reversals first, write the correct bright/dark order condition, then solve for phase, thickness, radius, index, or position.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The wedge angle is about :math:`0.0635^\circ`.

**Check.** Changing film thickness by λ0/(2n cos θt) advances one full fringe; ring-radius squared must vary linearly with order.

Problem 6.74 — locate the fourth wedge maximum and its film thickness
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Locate the fourth wedge maximum and its film thickness.

**Formula reference.** Use :eq:`schaum-6-3` and the definitions immediately above it.

**Worked application.**

1. Determine the reflection phase reversals first, write the correct bright/dark order condition, then solve for phase, thickness, radius, index, or position.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** At the fourth maximum, :math:`d\approx7.76\times10^{-7}\,\mathrm m` and :math:`x\approx0.700\,\mathrm{mm}`.

**Check.** Changing film thickness by λ0/(2n cos θt) advances one full fringe; ring-radius squared must vary linearly with order.

Problem 6.75 — infer liquid index from Newton-ring diameters
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer liquid index from newton-ring diameters.

**Formula reference.** Use :eq:`schaum-6-3` and the definitions immediately above it.

**Worked application.**

1. Determine the reflection phase reversals first, write the correct bright/dark order condition, then solve for phase, thickness, radius, index, or position.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The liquid index follows the squared-diameter ratio and is about 1.30 (using 2.52 cm and 2.21 cm); this also flags the scan's OCR-corrupted printed check.

**Check.** Changing film thickness by λ0/(2n cos θt) advances one full fringe; ring-radius squared must vary linearly with order.

Problem 6.76 — recover lens curvature from separated Newton-ring orders
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Recover lens curvature from separated newton-ring orders.

**Formula reference.** Use :eq:`schaum-6-3` and the definitions immediately above it.

**Worked application.**

1. Determine the reflection phase reversals first, write the correct bright/dark order condition, then solve for phase, thickness, radius, index, or position.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Eliminating the unknown absolute order with the two ring radii gives :math:`R\approx3.41\,\mathrm m`.

**Check.** Changing film thickness by λ0/(2n cos θt) advances one full fringe; ring-radius squared must vary linearly with order.

Problem 6.77 — generalize Newton rings to two curved surfaces
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Generalize newton rings to two curved surfaces.

**Formula reference.** Use :eq:`schaum-6-3` and the definitions immediately above it.

**Worked application.**

1. Determine the reflection phase reversals first, write the correct bright/dark order condition, then solve for phase, thickness, radius, index, or position.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Replacing the flat by radius :math:`R_2` gives effective curvature :math:`R_{\rm eff}=R_1R_2/(R_2-R_1)` and :math:`r_m=[m\lambda_0R_{\rm eff}]^{1/2}` for dark rings.

**Check.** Changing film thickness by λ0/(2n cos θt) advances one full fringe; ring-radius squared must vary linearly with order.

Amplitude-splitting interferometers
-----------------------------------

**Formula and definitions.**

.. math::
   :label: schaum-6-4

   \mathrm{OPD}=2d\cos\theta,\qquad N=\frac{2\Delta d}{\lambda_0},\qquad 2d(1-\cos\theta_p)=p\lambda_0\simeq d\theta_p^2

A mirror displacement changes a Michelson round trip by twice
the mechanical travel.  For a doublet, visibility goes from maximum to minimum
when the two wavelengths acquire a relative phase of :math:`\pi`.  A gas cell
adds optical path :math:`(n-1)L` per traversed cell length.

Problem 6.78 — prove Michelson equal-inclination rings collapse as arms equalize
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Prove michelson equal-inclination rings collapse as arms equalize.

**Formula reference.** Use :eq:`schaum-6-4` and the definitions immediately above it.

**Worked application.**

1. Count optical passes before equating OPD to Nλ, use 1-cos θ≈θ²/2 only after writing the exact relation, and distinguish mirror travel from optical-path change.
2. Carry the algebra from the formula reference to the identity named in the paraphrased task; do not assume that identity as an intermediate step.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** For fixed order, :math:`\cos\theta_m=m\lambda_0/(2d)` approaches one as the arm difference approaches that order's axial value; hence :math:`\theta_m\to0` and the ring collapses centrally.

**Check.** Moving a Michelson mirror by λ/2 must move one fringe past the detector; inferred gas indices should differ from unity only slightly.

Problem 6.79 — find sodium-doublet mirror travel from visibility maximum to minimum
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find sodium-doublet mirror travel from visibility maximum to minimum.

**Formula reference.** Use :eq:`schaum-6-4` and the definitions immediately above it.

**Worked application.**

1. Count optical passes before equating OPD to Nλ, use 1-cos θ≈θ²/2 only after writing the exact relation, and distinguish mirror travel from optical-path change.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The sodium-doublet maximum-to-minimum mirror travel is about 0.145 mm.

**Check.** Moving a Michelson mirror by λ/2 must move one fringe past the detector; inferred gas indices should differ from unity only slightly.

Problem 6.80 — find Michelson mirror travel for ten thousand fringes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find michelson mirror travel for ten thousand fringes.

**Formula reference.** Use :eq:`schaum-6-4` and the definitions immediately above it.

**Worked application.**

1. Count optical passes before equating OPD to Nλ, use 1-cos θ≈θ²/2 only after writing the exact relation, and distinguish mirror travel from optical-path change.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Ten thousand fringes require :math:`\Delta d=N\lambda/2\approx3.029\,\mathrm{mm}`; this distinguishes mirror travel from total OPD.

**Check.** Moving a Michelson mirror by λ/2 must move one fringe past the detector; inferred gas indices should differ from unity only slightly.

Problem 6.81 — derive the small-angle radius of a Michelson dark ring
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive the small-angle radius of a michelson dark ring.

**Formula reference.** Use :eq:`schaum-6-4` and the definitions immediately above it.

**Worked application.**

1. Count optical passes before equating OPD to Nλ, use 1-cos θ≈θ²/2 only after writing the exact relation, and distinguish mirror travel from optical-path change.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Using :math:`1-\cos\theta\simeq\theta^2/2` gives :math:`\theta_p\simeq\sqrt{p\lambda_0/d}`.

**Check.** Moving a Michelson mirror by λ/2 must move one fringe past the detector; inferred gas indices should differ from unity only slightly.

Problem 6.82 — calculate the fifteenth dark-ring angle
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Calculate the fifteenth dark-ring angle.

**Formula reference.** Use :eq:`schaum-6-4` and the definitions immediately above it.

**Worked application.**

1. Count optical passes before equating OPD to Nλ, use 1-cos θ≈θ²/2 only after writing the exact relation, and distinguish mirror travel from optical-path change.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** For the stated fifteenth ring, :math:`\theta\approx1^\circ24'`.

**Check.** Moving a Michelson mirror by λ/2 must move one fringe past the detector; inferred gas indices should differ from unity only slightly.

Problem 6.83 — infer gas index with a Jamin interferometer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer gas index with a jamin interferometer.

**Formula reference.** Use :eq:`schaum-6-4` and the definitions immediately above it.

**Worked application.**

1. Count optical passes before equating OPD to Nλ, use 1-cos θ≈θ²/2 only after writing the exact relation, and distinguish mirror travel from optical-path change.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`n\approx1.000139`.

**Check.** Moving a Michelson mirror by λ/2 must move one fringe past the detector; inferred gas indices should differ from unity only slightly.

Problem 6.84 — explain and apply a Mach-Zehnder interferometer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Explain and apply a mach-zehnder interferometer.

**Formula reference.** Use :eq:`schaum-6-4` and the definitions immediately above it.

**Worked application.**

1. Count optical passes before equating OPD to Nλ, use 1-cos θ≈θ²/2 only after writing the exact relation, and distinguish mirror travel from optical-path change.
2. Identify the controlling phase or conservation relation, then use it to account for every stated observation.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The two beam splitters form separate arms recombined at the output; a slight mirror tilt gives wedge fringes.  Like the Jamin arrangement, it maps large-volume refractive-index nonuniformity, for example in a wind tunnel.

**Check.** Moving a Michelson mirror by λ/2 must move one fringe past the detector; inferred gas indices should differ from unity only slightly.

Coherence
---------

**Formula and definitions.**

.. math::
   :label: schaum-6-5

   \tau_c\sim\frac1{\Delta\nu},\qquad \ell_c=c\tau_c\sim\frac{\lambda_0^2}{\Delta\lambda},\qquad \frac{\nu}{\Delta\nu}\sim\frac{\ell_c}{\lambda_0}

Convert fractional stability :math:`\Delta\nu/\nu` to an
absolute linewidth using :math:`\nu=c/\lambda_0`.  The reciprocal linewidth is
the coherence time and multiplication by :math:`c` gives coherence length.
For a stellar disk, the first visibility zero supplies its angular diameter.

Problem 6.85 — infer coherence time and length from laser frequency stability
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer coherence time and length from laser frequency stability.

**Formula reference.** Use :eq:`schaum-6-5` and the definitions immediately above it.

**Worked application.**

1. Keep frequency and wavelength linewidths distinct, use the small-bandwidth differential Δν/ν≈Δλ/λ, and compare interferometer OPD—not single-arm length—with coherence length.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`\tau_c\approx4.8\times10^{-2}\,\mathrm s` and :math:`\ell_c\approx1.44\times10^7\,\mathrm m`.

**Check.** All three ratios ν/Δν, λ/Δλ, and ℓc/λ should agree in order of magnitude.

Problem 6.86 — estimate linewidth and coherence length from transition time
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Estimate linewidth and coherence length from transition time.

**Formula reference.** Use :eq:`schaum-6-5` and the definitions immediately above it.

**Worked application.**

1. Keep frequency and wavelength linewidths distinct, use the small-bandwidth differential Δν/ν≈Δλ/λ, and compare interferometer OPD—not single-arm length—with coherence length.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Use :math:`\Delta\nu\sim1/\Delta t` and :math:`\ell_c=c\Delta t`; the numerical endpoint follows directly after inserting the transition time printed in the problem.

**Check.** All three ratios ν/Δν, λ/Δλ, and ℓc/λ should agree in order of magnitude.

Problem 6.87 — infer filter linewidth and Michelson range from wave-train length
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer filter linewidth and michelson range from wave-train length.

**Formula reference.** Use :eq:`schaum-6-5` and the definitions immediately above it.

**Worked application.**

1. Keep frequency and wavelength linewidths distinct, use the small-bandwidth differential Δν/ν≈Δλ/λ, and compare interferometer OPD—not single-arm length—with coherence length.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`\Delta\lambda\approx13\,\mathrm{nm}` and maximum one-arm Michelson travel about 0.0163 mm.

**Check.** All three ratios ν/Δν, λ/Δλ, and ℓc/λ should agree in order of magnitude.

Problem 6.88 — relate inverse fractional stability to wavelengths per wave train
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Relate inverse fractional stability to wavelengths per wave train.

**Formula reference.** Use :eq:`schaum-6-5` and the definitions immediately above it.

**Worked application.**

1. Keep frequency and wavelength linewidths distinct, use the small-bandwidth differential Δν/ν≈Δλ/λ, and compare interferometer OPD—not single-arm length—with coherence length.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Because :math:`N=\ell_c/\lambda_0=\nu/\Delta\nu`, the wavelength count is the inverse fractional frequency stability.

**Check.** All three ratios ν/Δν, λ/Δλ, and ℓc/λ should agree in order of magnitude.

Problem 6.89 — find coherence length and cycle count through a narrow filter
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find coherence length and cycle count through a narrow filter.

**Formula reference.** Use :eq:`schaum-6-5` and the definitions immediately above it.

**Worked application.**

1. Keep frequency and wavelength linewidths distinct, use the small-bandwidth differential Δν/ν≈Δλ/λ, and compare interferometer OPD—not single-arm length—with coherence length.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`\ell_c\approx2.02\times10^{-4}\,\mathrm m`, about 367 wavelengths.

**Check.** All three ratios ν/Δν, λ/Δλ, and ℓc/λ should agree in order of magnitude.

Problem 6.90 — infer stellar angular diameter with a Michelson interferometer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer stellar angular diameter with a michelson interferometer.

**Formula reference.** Use :eq:`schaum-6-5` and the definitions immediately above it.

**Worked application.**

1. Keep frequency and wavelength linewidths distinct, use the small-bandwidth differential Δν/ν≈Δλ/λ, and compare interferometer OPD—not single-arm length—with coherence length.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The stellar angular diameter is about :math:`2.26\times10^{-7}\,\mathrm{rad}`.

**Check.** All three ratios ν/Δν, λ/Δλ, and ℓc/λ should agree in order of magnitude.

Problem 6.91 — compare methane-stabilized laser coherence over a decade
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Compare methane-stabilized laser coherence over a decade.

**Formula reference.** Use :eq:`schaum-6-5` and the definitions immediately above it.

**Worked application.**

1. Keep frequency and wavelength linewidths distinct, use the small-bandwidth differential Δν/ν≈Δλ/λ, and compare interferometer OPD—not single-arm length—with coherence length.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The later stability corresponds to about 6.4 s coherence time versus :math:`4.8\times10^{-2}` s in the earlier result.

**Check.** All three ratios ν/Δν, λ/Δλ, and ℓc/λ should agree in order of magnitude.
