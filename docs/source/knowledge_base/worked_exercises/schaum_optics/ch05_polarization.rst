Chapter 5: Polarization
=======================

Source: Eugene Hecht, *Schaum's Outline of Theory and Problems of
Optics* (1975), Chapter 5.  The entries below cover only the
chapter's **Supplementary Problems**; prompts are paraphrased and are not
reproduced.

Each topic derives its shared formula once.  Every numbered problem then
applies that derivation to the particular proof, calculation, or construction
in the book.  Read the source diagram alongside entries that depend on a figure.

Plane polarization
------------------

**Formula and definitions.**

.. math::
   :label: schaum-5-1

   \mathbf E=\Re\!\left\{\begin{bmatrix}E_{0x}\\E_{0y}e^{i\delta}\end{bmatrix}e^{i(kz-\omega t)}\right\},\qquad \tan\psi=\frac{E_{0y}}{E_{0x}}\quad(\delta=0\text{ or }\pi)

Remove the common carrier and compare the two complex
components.  Equal or opposite phases make their ratio real and hence give a
fixed line.  Its quadrant comes from the component signs; orthogonality is
tested by the Jones inner product.

Problem 5.48 — write a forty-five-degree linear wave travelling along y
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Write a forty-five-degree linear wave travelling along y.

**Formula reference.** Use :eq:`schaum-5-1` and the definitions immediately above it.

**Worked application.**

1. Express both components with a common phase, reduce their complex ratio, and obtain the physical azimuth with atan2 so the quadrant is retained.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** A suitable field is :math:`\mathbf E=(E_0/\sqrt2)(\hat{\mathbf x}+\hat{\mathbf z})\cos[\omega(y/v-t)+\phi_0]`.

**Check.** A normalized linear Jones vector has unit norm and zero ellipticity; orthogonal linear states have a zero inner product.

Problem 5.49 — pass z-polarized light through a y-fast-axis quarter-wave plate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Pass z-polarized light through a y-fast-axis quarter-wave plate.

**Formula reference.** Use :eq:`schaum-5-1` and the definitions immediately above it.

**Worked application.**

1. Express both components with a common phase, reduce their complex ratio, and obtain the physical azimuth with atan2 so the quadrant is retained.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Only the z component is incident, so the plate adds only a common phase: the output remains z-directed linear light, :math:`\mathbf E=E_0\hat{\mathbf z}\cos(kx-\omega t+\phi_0)`.

**Check.** A normalized linear Jones vector has unit norm and zero ellipticity; orthogonal linear states have a zero inner product.

Problem 5.50 — write an xy-plane linear wave with zero initial field
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Write an xy-plane linear wave with zero initial field.

**Formula reference.** Use :eq:`schaum-5-1` and the definitions immediately above it.

**Worked application.**

1. Express both components with a common phase, reduce their complex ratio, and obtain the physical azimuth with atan2 so the quadrant is retained.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** One suitable zero-initial-field form is :math:`\mathbf E=E_0\hat{\mathbf x}\sin(ky-\omega t)`.

**Check.** A normalized linear Jones vector has unit norm and zero ellipticity; orthogonal linear states have a zero inner product.

Problem 5.51 — classify a signed two-component linear wave
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Classify a signed two-component linear wave.

**Formula reference.** Use :eq:`schaum-5-1` and the definitions immediately above it.

**Worked application.**

1. Express both components with a common phase, reduce their complex ratio, and obtain the physical azimuth with atan2 so the quadrant is retained.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The components are in phase, so the result is linear with amplitude :math:`2E_0`, propagates toward :math:`-y`, and is tilted 60° from the yz plane in the source convention.

**Check.** A normalized linear Jones vector has unit norm and zero ellipticity; orthogonal linear states have a zero inner product.

Problem 5.52 — write a linear wave tilted 17.5 degrees above the xy plane
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Write a linear wave tilted 17.5 degrees above the xy plane.

**Formula reference.** Use :eq:`schaum-5-1` and the definitions immediately above it.

**Worked application.**

1. Express both components with a common phase, reduce their complex ratio, and obtain the physical azimuth with atan2 so the quadrant is retained.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`\mathbf E=E_0(0.9537\hat{\mathbf y}+0.3007\hat{\mathbf z})\cos(kx-\omega t+\phi_0)`.

**Check.** A normalized linear Jones vector has unit norm and zero ellipticity; orthogonal linear states have a zero inner product.

Circular polarization
---------------------

**Formula and definitions.**

.. math::
   :label: schaum-5-2

   \mathbf e_R=\frac1{\sqrt2}\begin{bmatrix}1\\-i\end{bmatrix},\qquad \mathbf e_L=\frac1{\sqrt2}\begin{bmatrix}1\\i\end{bmatrix},\qquad \delta=\pm\frac\pi2

Circular polarization requires equal component magnitudes and
quadrature phase.  Evaluate the real field at a fixed :math:`z` for increasing
:math:`t` to determine handedness under the book's viewing convention.  A
quarter-wave plate supplies the required :math:`\pm\pi/2` phase delay.

Problem 5.53 — superpose two in-phase linear waves of unequal amplitude
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Superpose two in-phase linear waves of unequal amplitude.

**Formula reference.** Use :eq:`schaum-5-2` and the definitions immediately above it.

**Worked application.**

1. Normalize the component amplitudes, reduce the relative phase modulo 2π, and track the field rotation explicitly before naming the handedness.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The in-phase collinear states add to one linear state of amplitude :math:`3E_0`.

**Check.** The field-tip magnitude must remain constant through a cycle; reversing propagation or viewing direction reverses the apparent handedness.

Problem 5.54 — devise a test that distinguishes right- from left-circular light
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Devise a test that distinguishes right- from left-circular light.

**Formula reference.** Use :eq:`schaum-5-2` and the definitions immediately above it.

**Worked application.**

1. Normalize the component amplitudes, reduce the relative phase modulo 2π, and track the field rotation explicitly before naming the handedness.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Send the beam backward through a known circular polarizer: one handedness emerges linear whereas the opposite handedness is extinguished; interchange the reference polarizer to resolve the sign.

**Check.** The field-tip magnitude must remain constant through a cycle; reversing propagation or viewing direction reverses the apparent handedness.

Problem 5.55 — write a right-circular wave with a specified initial azimuth
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Write a right-circular wave with a specified initial azimuth.

**Formula reference.** Use :eq:`schaum-5-2` and the definitions immediately above it.

**Worked application.**

1. Normalize the component amplitudes, reduce the relative phase modulo 2π, and track the field rotation explicitly before naming the handedness.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** A right-circular form meeting the initial -45° condition is :math:`E_0[\hat x\cos(kz-\omega t-\pi/4)+\hat y\sin(kz-\omega t-\pi/4)]` under the book's convention.

**Check.** The field-tip magnitude must remain constant through a cycle; reversing propagation or viewing direction reverses the apparent handedness.

Problem 5.56 — write a right-circular wave from a specified initial vector
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Write a right-circular wave from a specified initial vector.

**Formula reference.** Use :eq:`schaum-5-2` and the definitions immediately above it.

**Worked application.**

1. Normalize the component amplitudes, reduce the relative phase modulo 2π, and track the field rotation explicitly before naming the handedness.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Choose the common initial phase so the two equal quadrature components reproduce the supplied normalized vector; the resulting Jones ratio has unit magnitude and -90° relative phase for the stated right-circular convention.

**Check.** The field-tip magnitude must remain constant through a cycle; reversing propagation or viewing direction reverses the apparent handedness.

Problem 5.57 — write a left-circular wave with a specified initial azimuth
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Write a left-circular wave with a specified initial azimuth.

**Formula reference.** Use :eq:`schaum-5-2` and the definitions immediately above it.

**Worked application.**

1. Normalize the component amplitudes, reduce the relative phase modulo 2π, and track the field rotation explicitly before naming the handedness.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** A left-circular form is obtained by reversing the quadrature sign and choosing the common phase to reproduce the stated initial azimuth.

**Check.** The field-tip magnitude must remain constant through a cycle; reversing propagation or viewing direction reverses the apparent handedness.

Elliptical polarization
-----------------------

**Formula and definitions.**

.. math::
   :label: schaum-5-3

   \left(\frac{E_x}{E_{0x}}\right)^2+\left(\frac{E_y}{E_{0y}}\right)^2-2\frac{E_xE_y}{E_{0x}E_{0y}}\cos\delta=\sin^2\delta

Write one component as :math:`E_{0x}\cos\tau` and the other as
:math:`E_{0y}\cos(\tau+\delta)`.  Expanding the latter and eliminating
:math:`\sin\tau` gives the quadratic ellipse.  Diagonalizing its symmetric
quadratic form gives principal axes and azimuth.

Problem 5.58 — write a right-handed ellipse tilted to the y axis
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Write a right-handed ellipse tilted to the y axis.

**Formula reference.** Use :eq:`schaum-5-3` and the definitions immediately above it.

**Worked application.**

1. Eliminate the common phase, inspect equal-amplitude/quadrature special cases, and use the sign of temporal rotation for handedness.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** One right-handed example is :math:`E_0\hat y\cos(kx-\omega t)+E_0\hat z\cos(kx-\omega t-\pi/4)` with axes interpreted as in the source.

**Check.** The determinant of the ellipse quadratic must be non-negative; δ=0 or π collapses it to a line and equal quadrature components make a circle.

Problem 5.59 — write a left-handed ellipse with major axis at 135 degrees
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Write a left-handed ellipse with major axis at 135 degrees.

**Formula reference.** Use :eq:`schaum-5-3` and the definitions immediately above it.

**Worked application.**

1. Eliminate the common phase, inspect equal-amplitude/quadrature special cases, and use the sign of temporal rotation for handedness.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Use orthogonal components along the 135°/45° principal directions with unequal amplitudes and +90° relative phase; reversing that sign reverses handedness.

**Check.** The determinant of the ellipse quadratic must be non-negative; δ=0 or π collapses it to a line and equal quadrature components make a circle.

Problem 5.60 — classify an ellipse from two phase-shifted components
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Classify an ellipse from two phase-shifted components.

**Formula reference.** Use :eq:`schaum-5-3` and the definitions immediately above it.

**Worked application.**

1. Eliminate the common phase, inspect equal-amplitude/quadrature special cases, and use the sign of temporal rotation for handedness.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Reducing the relative phase modulo :math:`2\pi` gives a right-handed ellipse whose major axis is at 135° to x.

**Check.** The determinant of the ellipse quadratic must be non-negative; δ=0 or π collapses it to a line and equal quadrature components make a circle.

Problem 5.61 — write a right-handed two-to-one ellipse along x
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Write a right-handed two-to-one ellipse along x.

**Formula reference.** Use :eq:`schaum-5-3` and the definitions immediately above it.

**Worked application.**

1. Eliminate the common phase, inspect equal-amplitude/quadrature special cases, and use the sign of temporal rotation for handedness.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** One valid two-to-one state is :math:`\mathbf E=2E_0\hat x\cos(\omega t-kz)-E_0\hat y\sin(\omega t-kz)`.

**Check.** The determinant of the ellipse quadratic must be non-negative; δ=0 or π collapses it to a line and equal quadrature components make a circle.

Problem 5.62 — decompose an ellipse into linear and circular components
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Decompose an ellipse into linear and circular components.

**Formula reference.** Use :eq:`schaum-5-3` and the definitions immediately above it.

**Worked application.**

1. Eliminate the common phase, inspect equal-amplitude/quadrature special cases, and use the sign of temporal rotation for handedness.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** For :math:`E_{0x}\ge E_{0y}`, write the field as a circle of radius :math:`E_{0y}` plus the collinear remainder :math:`(E_{0x}-E_{0y})\hat x\sin\Phi`; the opposite ordering is analogous.

**Check.** The determinant of the ellipse quadratic must be non-negative; δ=0 or π collapses it to a line and equal quadrature components make a circle.

Natural and partially polarized light
-------------------------------------

**Formula and definitions.**

.. math::
   :label: schaum-5-4

   \mathcal P=\frac{I_{\max}-I_{\min}}{I_{\max}+I_{\min}}=\frac{I_p}{I_p+I_u},\qquad I(\theta)=\frac{I_u}{2}+I_p\cos^2\theta

An ideal analyzer transmits half of the unpolarized component
and the Malus-law projection of the polarized component.  Evaluating at
parallel and crossed orientations gives :math:`I_{\max}` and
:math:`I_{\min}`; their sum and difference isolate :math:`I_u` and
:math:`I_p`.

Problem 5.63 — decide whether a perfectly monochromatic wave must be polarized
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Decide whether a perfectly monochromatic wave must be polarized.

**Formula reference.** Use :eq:`schaum-5-4` and the definitions immediately above it.

**Worked application.**

1. Write the analyzer curve, evaluate its maximum and minimum, and solve the resulting two linear equations for the requested degree or component irradiances.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Yes: an exactly monochromatic field has unlimited temporal coherence, so its component amplitude ratio and phase are fixed and it has a definite polarization state.

**Check.** The degree of polarization must lie between zero and one; a fully natural beam has equal analyzer extrema and a pure linear beam has a zero minimum.

Problem 5.64 — distinguish partially linear from partially elliptical light
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Distinguish partially linear from partially elliptical light.

**Formula reference.** Use :eq:`schaum-5-4` and the definitions immediately above it.

**Worked application.**

1. Write the analyzer curve, evaluate its maximum and minimum, and solve the resulting two linear equations for the requested degree or component irradiances.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Find an analyzer extremum, align a quarter-wave plate to that axis, and repeat the analyzer scan.  Unshifted extrema indicate a partial linear state; rotated extrema identify a partial ellipse.

**Check.** The degree of polarization must lie between zero and one; a fully natural beam has equal analyzer extrema and a pure linear beam has a zero minimum.

Problem 5.65 — distinguish natural, circular, and mixed light experimentally
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Distinguish natural, circular, and mixed light experimentally.

**Formula reference.** Use :eq:`schaum-5-4` and the definitions immediately above it.

**Worked application.**

1. Write the analyzer curve, evaluate its maximum and minimum, and solve the resulting two linear equations for the requested degree or component irradiances.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Place a quarter-wave plate before a rotating analyzer: circular light becomes linear with a zero minimum, natural light stays angle independent, and a mixture has a nonzero modulation minimum.

**Check.** The degree of polarization must lie between zero and one; a fully natural beam has equal analyzer extrema and a pure linear beam has a zero minimum.

Problem 5.66 — recover polarization degree from two analyzer readings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Recover polarization degree from two analyzer readings.

**Formula reference.** Use :eq:`schaum-5-4` and the definitions immediately above it.

**Worked application.**

1. Write the analyzer curve, evaluate its maximum and minimum, and solve the resulting two linear equations for the requested degree or component irradiances.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`\mathcal P=(43-22)/(43+22)=0.323`, or 32.3%.

**Check.** The degree of polarization must lie between zero and one; a fully natural beam has equal analyzer extrema and a pure linear beam has a zero minimum.

Dichroism and Polaroid
----------------------

**Formula and definitions.**

.. math::
   :label: schaum-5-5

   I_1=\frac{I_{\rm unpol}}2,\qquad I_N=I_1\prod_{j=2}^{N}\cos^2(\theta_j-\theta_{j-1})

The first ideal polarizer transmits half of natural incident
light.  Every later plate receives a linearly polarized beam, so apply Malus's
law using the angle relative to the immediately preceding transmission axis,
not the first axis.

Problem 5.67 — write the field transmitted from natural light by one polarizer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Write the field transmitted from natural light by one polarizer.

**Formula reference.** Use :eq:`schaum-5-5` and the definitions immediately above it.

**Worked application.**

1. Order the polarizers physically, take every consecutive angular difference, and multiply the corresponding cos² factors without prematurely comparing only the endpoints.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The first polarizer transmits :math:`I_i/2`; its field has equal y and z components and amplitude :math:`E_0=\sqrt{2(I_i/2)/(c\epsilon_0)}`.

**Check.** Removing intermediate plates must recover direct Malus-law transmission; crossed adjacent axes force the product to zero.

Problem 5.68 — compare Malus transmission at thirty and sixty degrees
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Compare malus transmission at thirty and sixty degrees.

**Formula reference.** Use :eq:`schaum-5-5` and the definitions immediately above it.

**Worked application.**

1. Order the polarizers physically, take every consecutive angular difference, and multiply the corresponding cos² factors without prematurely comparing only the endpoints.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`I(30^\circ)/I(60^\circ)=\cos^2 30^\circ/\cos^2 60^\circ=3`.

**Check.** Removing intermediate plates must recover direct Malus-law transmission; crossed adjacent axes force the product to zero.

Problem 5.69 — propagate irradiance through three specified polarizers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Propagate irradiance through three specified polarizers.

**Formula reference.** Use :eq:`schaum-5-5` and the definitions immediately above it.

**Worked application.**

1. Order the polarizers physically, take every consecutive angular difference, and multiply the corresponding cos² factors without prematurely comparing only the endpoints.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The three-filter transmission is :math:`0.1920 I_i`.

**Check.** Removing intermediate plates must recover direct Malus-law transmission; crossed adjacent axes force the product to zero.

Problem 5.70 — propagate irradiance through ten forty-five-degree stages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Propagate irradiance through ten forty-five-degree stages.

**Formula reference.** Use :eq:`schaum-5-5` and the definitions immediately above it.

**Worked application.**

1. Order the polarizers physically, take every consecutive angular difference, and multiply the corresponding cos² factors without prematurely comparing only the endpoints.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Ten filters transmit :math:`I_i(1/2)^{10}=9.77\times10^{-4}I_i`; :math:`N` filters give :math:`I_i(1/2)^N` for the specified natural input and 45° steps.

**Check.** Removing intermediate plates must recover direct Malus-law transmission; crossed adjacent axes force the product to zero.

Problem 5.71 — compare four-polarizer transmission with crossed endpoints
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Compare four-polarizer transmission with crossed endpoints.

**Formula reference.** Use :eq:`schaum-5-5` and the definitions immediately above it.

**Worked application.**

1. Order the polarizers physically, take every consecutive angular difference, and multiply the corresponding cos² factors without prematurely comparing only the endpoints.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The four-filter stack transmits :math:`0.2109 I_i`; removing the middle plates gives zero through crossed endpoints.

**Check.** Removing intermediate plates must recover direct Malus-law transmission; crossed adjacent axes force the product to zero.

Problem 5.72 — explain extinction for a reordered three-polarizer stack
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Explain extinction for a reordered three-polarizer stack.

**Formula reference.** Use :eq:`schaum-5-5` and the definitions immediately above it.

**Worked application.**

1. Order the polarizers physically, take every consecutive angular difference, and multiply the corresponding cos² factors without prematurely comparing only the endpoints.
2. Identify the controlling phase or conservation relation, then use it to account for every stated observation.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** No light emerges because the final analyzer is crossed with the immediately preceding polarization.

**Check.** Removing intermediate plates must recover direct Malus-law transmission; crossed adjacent axes force the product to zero.

Polarization by reflection
--------------------------

**Formula and definitions.**

.. math::
   :label: schaum-5-6

   \tan\theta_B=\frac{n_t}{n_i},\qquad \theta_B+\theta_t=90^\circ,\qquad R_p(\theta_B)=0

At Brewster incidence the reflected and transmitted rays are
orthogonal.  Substituting that condition into Snell's law gives the tangent
rule.  For natural light, apply the separate Fresnel reflectances to equal
incident s and p irradiances, then form the polarization degree.

Problem 5.73 — infer glass index from a measured Brewster angle
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer glass index from a measured brewster angle.

**Formula reference.** Use :eq:`schaum-5-6` and the definitions immediately above it.

**Worked application.**

1. Identify whether incidence is internal or external, take the correct index ratio, and use the Fresnel power coefficients when a degree of polarization is requested.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`n=\tan(58^\circ01')\approx1.6014`.

**Check.** The internal and external Brewster angles are complementary for the same interface; the reflected p component must vanish at the result.

Problem 5.74 — calculate external Brewster and transmitted angles
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Calculate external brewster and transmitted angles.

**Formula reference.** Use :eq:`schaum-5-6` and the definitions immediately above it.

**Worked application.**

1. Identify whether incidence is internal or external, take the correct index ratio, and use the Fresnel power coefficients when a degree of polarization is requested.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`\theta_B\approx56^\circ36'` and :math:`\theta_t\approx33^\circ24'`.

**Check.** The internal and external Brewster angles are complementary for the same interface; the reflected p component must vanish at the result.

Problem 5.75 — derive Malus variation from two reflecting plates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive malus variation from two reflecting plates.

**Formula reference.** Use :eq:`schaum-5-6` and the definitions immediately above it.

**Worked application.**

1. Identify whether incidence is internal or external, take the correct index ratio, and use the Fresnel power coefficients when a degree of polarization is requested.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The second reflection projects the first reflected linear state onto its rotated incidence plane, so :math:`I(\theta)=I(0)\cos^2\theta`.

**Check.** The internal and external Brewster angles are complementary for the same interface; the reflected p component must vanish at the result.

Problem 5.76 — calculate reflected and transmitted degrees of polarization
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Calculate reflected and transmitted degrees of polarization.

**Formula reference.** Use :eq:`schaum-5-6` and the definitions immediately above it.

**Worked application.**

1. Identify whether incidence is internal or external, take the correct index ratio, and use the Fresnel power coefficients when a degree of polarization is requested.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The reflected beam is fully polarized; the transmitted degree is about 8.1%.

**Check.** The internal and external Brewster angles are complementary for the same interface; the reflected p component must vanish at the result.

Problem 5.77 — compare internal and external Brewster angles
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Compare internal and external brewster angles.

**Formula reference.** Use :eq:`schaum-5-6` and the definitions immediately above it.

**Worked application.**

1. Identify whether incidence is internal or external, take the correct index ratio, and use the Fresnel power coefficients when a degree of polarization is requested.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** External and internal Brewster angles are approximately :math:`51.45^\circ` and :math:`38.55^\circ`, respectively.

**Check.** The internal and external Brewster angles are complementary for the same interface; the reflected p component must vanish at the result.

Birefringence
-------------

**Formula and definitions.**

.. math::
   :label: schaum-5-7

   \Delta\phi=\frac{2\pi d}{\lambda_0}(n_s-n_f),\qquad J(\alpha,\Delta\phi)=R(-\alpha)\begin{bmatrix}e^{-i\Delta\phi/2}&0\\0&e^{i\Delta\phi/2}\end{bmatrix}R(\alpha)

Resolve the incident Jones vector onto the fast and slow axes,
apply their relative phase delay, and rotate back.  Quarter-, half-, and
full-wave behavior corresponds to :math:`\Delta\phi=\pi/2`, :math:`\pi`, and
:math:`2\pi` modulo :math:`2\pi`.  Minimum-deviation prism data gives each
principal index through the prism formula.

Problem 5.78 — pass right-circular light through a vertical-fast-axis quarter-wave plate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Pass right-circular light through a vertical-fast-axis quarter-wave plate.

**Formula reference.** Use :eq:`schaum-5-7` and the definitions immediately above it.

**Worked application.**

1. Build the rotated retarder matrix with the axis orientation shown in the source, multiply by the input state, and reduce the output phase and amplitude ratio before naming its polarization.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The output is linear at 135° to the positive x axis under the book's handedness convention.

**Check.** A lossless retarder preserves Jones-vector norm; doubling wavelength-dependent retardance order must agree with Δφ proportional to d/λ0.

Problem 5.79 — pass left-circular light through the same plate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Pass left-circular light through the same plate.

**Formula reference.** Use :eq:`schaum-5-7` and the definitions immediately above it.

**Worked application.**

1. Build the rotated retarder matrix with the axis orientation shown in the source, multiply by the input state, and reduce the output phase and amplitude ratio before naming its polarization.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The output is linear at 45° to the positive x axis.

**Check.** A lossless retarder preserves Jones-vector norm; doubling wavelength-dependent retardance order must agree with Δφ proportional to d/λ0.

Problem 5.80 — find extraordinary-ray and optic-axis angles in calcite
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find extraordinary-ray and optic-axis angles in calcite.

**Formula reference.** Use :eq:`schaum-5-7` and the definitions immediately above it.

**Worked application.**

1. Build the rotated retarder matrix with the axis orientation shown in the source, multiply by the input state, and reduce the output phase and amplitude ratio before naming its polarization.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The source geometry gives approximately :math:`\beta=45^\circ24'` and extraordinary-ray deflection :math:`\alpha=6^\circ14'`.

**Check.** A lossless retarder preserves Jones-vector norm; doubling wavelength-dependent retardance order must agree with Δφ proportional to d/λ0.

Problem 5.81 — design a retarder that reverses circular handedness
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Design a retarder that reverses circular handedness.

**Formula reference.** Use :eq:`schaum-5-7` and the definitions immediately above it.

**Worked application.**

1. Build the rotated retarder matrix with the axis orientation shown in the source, multiply by the input state, and reduce the output phase and amplitude ratio before naming its polarization.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** A minimum half-wave thickness is :math:`d\approx3.64\times10^{-3}\,\mathrm{cm}`.

**Check.** A lossless retarder preserves Jones-vector norm; doubling wavelength-dependent retardance order must agree with Δφ proportional to d/λ0.

Problem 5.82 — analyze a half-wave plate between crossed polarizers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Analyze a half-wave plate between crossed polarizers.

**Formula reference.** Use :eq:`schaum-5-7` and the definitions immediately above it.

**Worked application.**

1. Build the rotated retarder matrix with the axis orientation shown in the source, multiply by the input state, and reduce the output phase and amplitude ratio before naming its polarization.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The half-wave plate rotates the first polarizer's red linear state by 90°, making it parallel to the crossed analyzer; red light therefore emerges linearly polarized along the analyzer.

**Check.** A lossless retarder preserves Jones-vector norm; doubling wavelength-dependent retardance order must agree with Δφ proportional to d/λ0.

Problem 5.83 — repeat the crossed-polarizer analysis at half the wavelength
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Repeat the crossed-polarizer analysis at half the wavelength.

**Formula reference.** Use :eq:`schaum-5-7` and the definitions immediately above it.

**Worked application.**

1. Build the rotated retarder matrix with the axis orientation shown in the source, multiply by the input state, and reduce the output phase and amplitude ratio before naming its polarization.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** At half the wavelength the same plate supplies a full-wave delay, leaves the first polarizer's violet state unchanged, and the crossed analyzer extinguishes it.

**Check.** A lossless retarder preserves Jones-vector norm; doubling wavelength-dependent retardance order must agree with Δφ proportional to d/λ0.

Problem 5.84 — find wavelengths emerging circular after removing the analyzer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find wavelengths emerging circular after removing the analyzer.

**Formula reference.** Use :eq:`schaum-5-7` and the definitions immediately above it.

**Worked application.**

1. Build the rotated retarder matrix with the axis orientation shown in the source, multiply by the input state, and reduce the output phase and amplitude ratio before naming its polarization.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** With the analyzer removed, the yellow-green wavelength near 520 nm emerges circular.

**Check.** A lossless retarder preserves Jones-vector norm; doubling wavelength-dependent retardance order must agree with Δφ proportional to d/λ0.

Problem 5.85 — design a calcite plate for extinction between parallel polarizers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Design a calcite plate for extinction between parallel polarizers.

**Formula reference.** Use :eq:`schaum-5-7` and the definitions immediately above it.

**Worked application.**

1. Build the rotated retarder matrix with the axis orientation shown in the source, multiply by the input state, and reduce the output phase and amplitude ratio before naming its polarization.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Use a half-wave plate at 45°; :math:`d\approx1.713\times10^{-4}\,\mathrm{cm}`.

**Check.** A lossless retarder preserves Jones-vector norm; doubling wavelength-dependent retardance order must agree with Δφ proportional to d/λ0.

Problem 5.86 — infer ordinary and extraordinary indices from prism deviations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer ordinary and extraordinary indices from prism deviations.

**Formula reference.** Use :eq:`schaum-5-7` and the definitions immediately above it.

**Worked application.**

1. Build the rotated retarder matrix with the axis orientation shown in the source, multiply by the input state, and reduce the output phase and amplitude ratio before naming its polarization.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The two minimum-deviation measurements give principal indices about 1.532 and 1.597.

**Check.** A lossless retarder preserves Jones-vector norm; doubling wavelength-dependent retardance order must agree with Δφ proportional to d/λ0.
