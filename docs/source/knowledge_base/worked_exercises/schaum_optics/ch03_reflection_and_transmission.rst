Chapter 3: Reflection and Transmission
======================================

Source: Eugene Hecht, *Schaum's Outline of Theory and Problems of
Optics* (1975), Chapter 3.  The entries below cover only the
chapter's **Supplementary Problems**; prompts are paraphrased and are not
reproduced.

Each topic derives its shared formula once.  Every numbered problem then
applies that derivation to the particular proof, calculation, or construction
in the book.  Read the source diagram alongside entries that depend on a figure.

Laws of reflection and refraction
---------------------------------

**Formula and definitions.**

.. math::
   :label: schaum-3-1

   n_i\sin\theta_i=n_t\sin\theta_t,\qquad \theta_r=\theta_i,\qquad a=d\,\frac{\sin(\theta_i-\theta_t)}{\cos\theta_t}

Resolve every angle from the surface normal.  For a parallel
plate, apply Snell's law at each face and use the right triangle inside the
plate.  For a prism or mirror sequence, sum signed turns of the ray rather
than unsigned interior angles.

Problem 3.31 — express parallel-plate beam displacement with Snell's law
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Express parallel-plate beam displacement with snell's law.

**Formula reference.** Use :eq:`schaum-3-1` and the definitions immediately above it.

**Worked application.**

1. Label incident, reflected, and transmitted angles at each surface, apply Snell or reflection locally, then eliminate the intermediate angle geometrically.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Expanding :math:`\sin(\theta_i-\theta_t)` and using Snell's law gives :math:`a=d\sin\theta_i[1-n_i\cos\theta_i/(n_t\cos\theta_t)]`.

**Check.** A parallel plate must return the emergent direction to the incident direction; setting equal indices must eliminate refraction and lateral displacement.

Problem 3.32 — derive prism deviation from ray angles
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive prism deviation from ray angles.

**Formula reference.** Use :eq:`schaum-3-1` and the definitions immediately above it.

**Worked application.**

1. Label incident, reflected, and transmitted angles at each surface, apply Snell or reflection locally, then eliminate the intermediate angle geometrically.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Summing the two surface turns gives the prism deviation :math:`\delta=\theta_{i1}+\theta_{t2}-A` in the source notation.

**Check.** A parallel plate must return the emergent direction to the incident direction; setting equal indices must eliminate refraction and lateral displacement.

Problem 3.33 — derive the deviation made by two mirrors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive the deviation made by two mirrors.

**Formula reference.** Use :eq:`schaum-3-1` and the definitions immediately above it.

**Worked application.**

1. Label incident, reflected, and transmitted angles at each surface, apply Snell or reflection locally, then eliminate the intermediate angle geometrically.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Each reflection turns the ray through twice the angle between the ray and mirror normal; adding the two signed turns yields the source figure's two-mirror deviation relation.

**Check.** A parallel plate must return the emergent direction to the incident direction; setting equal indices must eliminate refraction and lateral displacement.

Problem 3.34 — find the mirror-angle condition for a retracing ray
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find the mirror-angle condition for a retracing ray.

**Formula reference.** Use :eq:`schaum-3-1` and the definitions immediately above it.

**Worked application.**

1. Label incident, reflected, and transmitted angles at each surface, apply Snell or reflection locally, then eliminate the intermediate angle geometrically.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The retracing condition is :math:`\theta_i=3\alpha` for the angles defined in the source figure.

**Check.** A parallel plate must return the emergent direction to the incident direction; setting equal indices must eliminate refraction and lateral displacement.

Problem 3.35 — justify a graphical Snell-law construction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Justify a graphical snell-law construction.

**Formula reference.** Use :eq:`schaum-3-1` and the definitions immediately above it.

**Worked application.**

1. Label incident, reflected, and transmitted angles at each surface, apply Snell or reflection locally, then eliminate the intermediate angle geometrically.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The perpendicular projection of the radius-:math:`n` construction is :math:`n\sin\theta`; equality of that projection across the interface is exactly :math:`n_i\sin\theta_i=n_t\sin\theta_t`.

**Check.** A parallel plate must return the emergent direction to the incident direction; setting equal indices must eliminate refraction and lateral displacement.

Fermat's principle
------------------

**Formula and definitions.**

.. math::
   :label: schaum-3-2

   \mathcal L=\sum_j n_j\ell_j,\qquad \delta\mathcal L=0,\qquad \frac{d\mathcal L}{dq}=0

Write the optical path length through an arbitrary point on the
interface and differentiate with respect to its free coordinate.  The two
derivatives are direction cosines; stationarity therefore gives equal
tangential optical-wave-vector components, i.e. Snell's law or the reflection
law.  For an ellipse, the sum of focal distances is constant.

Problem 3.36 — prove focus-to-focus reflection by an ellipsoid
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Prove focus-to-focus reflection by an ellipsoid.

**Formula reference.** Use :eq:`schaum-3-2` and the definitions immediately above it.

**Worked application.**

1. Choose the one independent displacement shown in the source diagram, differentiate every segment length by the chain rule, and set the first variation to zero.
2. Carry the algebra from the formula reference to the identity named in the paraphrased task; do not assume that identity as an intermediate step.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Every reflecting point on the ellipse satisfies :math:`SP_1+P_1P_2=2a`; the optical path is therefore stationary (indeed constant), so a ray from one focus reaches the other.

**Check.** The stationary result must be unchanged by relabelling the two media and must reduce to equal angles when their indices are equal.

Problem 3.37 — derive Snell's law using an angular coordinate
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive snell's law using an angular coordinate.

**Formula reference.** Use :eq:`schaum-3-2` and the definitions immediately above it.

**Worked application.**

1. Choose the one independent displacement shown in the source diagram, differentiate every segment length by the chain rule, and set the first variation to zero.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Differentiating the two segment lengths with respect to the angular coordinate again gives :math:`n_i\sin\theta_i=n_t\sin\theta_t`.

**Check.** The stationary result must be unchanged by relabelling the two media and must reduce to equal angles when their indices are equal.

Problem 3.38 — derive Snell's law from adjacent optical paths
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive snell's law from adjacent optical paths.

**Formula reference.** Use :eq:`schaum-3-2` and the definitions immediately above it.

**Worked application.**

1. Choose the one independent displacement shown in the source diagram, differentiate every segment length by the chain rule, and set the first variation to zero.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The first-order optical-path difference is proportional to :math:`n_i\sin\theta_i-n_t\sin\theta_t`; stationarity makes it zero and yields Snell's law.

**Check.** The stationary result must be unchanged by relabelling the two media and must reduce to equal angles when their indices are equal.

Problem 3.39 — prove coplanarity at a reflecting interface
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Prove coplanarity at a reflecting interface.

**Formula reference.** Use :eq:`schaum-3-2` and the definitions immediately above it.

**Worked application.**

1. Choose the one independent displacement shown in the source diagram, differentiate every segment length by the chain rule, and set the first variation to zero.
2. Carry the algebra from the formula reference to the identity named in the paraphrased task; do not assume that identity as an intermediate step.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** An out-of-plane displacement adds a nonzero first-order path change unless both rays and the surface normal share one plane; stationarity therefore enforces the plane of incidence.

**Check.** The stationary result must be unchanged by relabelling the two media and must reduce to equal angles when their indices are equal.

Fresnel equations
-----------------

**Formula and definitions.**

.. math::
   :label: schaum-3-3

   r_s=\frac{n_i\cos\theta_i-n_t\cos\theta_t}{n_i\cos\theta_i+n_t\cos\theta_t},\quad r_p=\frac{n_t\cos\theta_i-n_i\cos\theta_t}{n_t\cos\theta_i+n_i\cos\theta_t},\quad R=|r|^2,\quad T=\frac{n_t\cos\theta_t}{n_i\cos\theta_i}|t|^2

Apply the tangential-field boundary conditions separately for
s and p polarization and use Snell's law to remove either index or angle.
Squaring amplitudes alone is insufficient for transmitted power: include the
normal admittance factor shown in :math:`T`.

Problem 3.40 — calculate s-polarized Fresnel amplitudes at forty-five degrees
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Calculate s-polarized fresnel amplitudes at forty-five degrees.

**Formula reference.** Use :eq:`schaum-3-3` and the definitions immediately above it.

**Worked application.**

1. Find θt from Snell's law, evaluate the appropriate amplitude pair, and convert to power coefficients only after the amplitudes are known.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`r_s=-0.303` and :math:`t_s=0.697` (rounding depends on the refracted-angle precision).

**Check.** For lossless media R+T=1. At equal indices r=0 and t=1, while reversing the interface changes the reflection phase but conserves power.

Problem 3.41 — remove explicit refractive indices from transmission amplitudes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Remove explicit refractive indices from transmission amplitudes.

**Formula reference.** Use :eq:`schaum-3-3` and the definitions immediately above it.

**Worked application.**

1. Find θt from Snell's law, evaluate the appropriate amplitude pair, and convert to power coefficients only after the amplitudes are known.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Using Snell's law, :math:`t_s=2\sin\theta_t\cos\theta_i/\sin(\theta_i+\theta_t)` and :math:`t_p=t_s/\cos(\theta_i-\theta_t)`.

**Check.** For lossless media R+T=1. At equal indices r=0 and t=1, while reversing the interface changes the reflection phase but conserves power.

Problem 3.42 — verify amplitude-coefficient identities
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Verify amplitude-coefficient identities.

**Formula reference.** Use :eq:`schaum-3-3` and the definitions immediately above it.

**Worked application.**

1. Find θt from Snell's law, evaluate the appropriate amplitude pair, and convert to power coefficients only after the amplitudes are known.
2. Evaluate both sides independently from the definitions and confirm equality without circular substitution.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The boundary-field identities reduce to :math:`1+r_s=t_s` and the corresponding signed p-polarization relation after the refractive-index ratio is replaced with Snell's law.

**Check.** For lossless media R+T=1. At equal indices r=0 and t=1, while reversing the interface changes the reflection phase but conserves power.

Problem 3.43 — prove energy conservation of reflectance and transmittance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Prove energy conservation of reflectance and transmittance.

**Formula reference.** Use :eq:`schaum-3-3` and the definitions immediately above it.

**Worked application.**

1. Find θt from Snell's law, evaluate the appropriate amplitude pair, and convert to power coefficients only after the amplitudes are known.
2. Carry the algebra from the formula reference to the identity named in the paraphrased task; do not assume that identity as an intermediate step.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Substituting the Fresnel amplitudes into the normal-flux definitions cancels the common denominator and gives :math:`R_s+T_s=R_p+T_p=1`.

**Check.** For lossless media R+T=1. At equal indices r=0 and t=1, while reversing the interface changes the reflection phase but conserves power.

Problem 3.44 — reverse normal-incidence illumination from air to glass
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Reverse normal-incidence illumination from air to glass.

**Formula reference.** Use :eq:`schaum-3-3` and the definitions immediately above it.

**Worked application.**

1. Find θt from Snell's law, evaluate the appropriate amplitude pair, and convert to power coefficients only after the amplitudes are known.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** For glass-to-air normal incidence, :math:`r=+0.2` and :math:`t=1.2`; power remains conserved.

**Check.** For lossless media R+T=1. At equal indices r=0 and t=1, while reversing the interface changes the reflection phase but conserves power.

Problem 3.45 — solve normal-incidence reflectance/transmittance cases
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Solve normal-incidence reflectance/transmittance cases.

**Formula reference.** Use :eq:`schaum-3-3` and the definitions immediately above it.

**Worked application.**

1. Find θt from Snell's law, evaluate the appropriate amplitude pair, and convert to power coefficients only after the amplitudes are known.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Equal normal-incidence reflectance and transmittance occurs at relative index :math:`n_{ti}=3\pm2\sqrt2\approx5.83` or 0.172.

**Check.** For lossless media R+T=1. At equal indices r=0 and t=1, while reversing the interface changes the reflection phase but conserves power.

Critical angle and total internal reflection
--------------------------------------------

**Formula and definitions.**

.. math::
   :label: schaum-3-4

   \sin\theta_c=\frac{n_t}{n_i}\ (n_i>n_t),\qquad \tan\theta_B=\frac{n_t}{n_i},\qquad \mathrm{NA}=n_0\sin\theta_{\max}=\sqrt{n_{\rm core}^2-n_{\rm clad}^2}

At critical incidence set the transmitted angle to
:math:`90^\circ`.  At Brewster incidence use
:math:`\theta_B+\theta_t=90^\circ` in Snell's law.  For a fiber, combine the
entrance-face Snell relation with the core-cladding critical condition and
eliminate the internal ray angle.

Problem 3.46 — combine two forty-five-degree critical interfaces
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Combine two forty-five-degree critical interfaces.

**Formula reference.** Use :eq:`schaum-3-4` and the definitions immediately above it.

**Worked application.**

1. Use the geometry to identify the high-index side first; then apply the critical, Brewster, or numerical-aperture relation with all angles measured from their local normals.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The combined relative index is :math:`n_C/n_A=2`.

**Check.** A critical angle exists only from higher to lower index; the fiber acceptance must vanish when core and cladding indices are equal.

Problem 3.47 — find the minimum prism index for total internal reflection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find the minimum prism index for total internal reflection.

**Formula reference.** Use :eq:`schaum-3-4` and the definitions immediately above it.

**Worked application.**

1. Use the geometry to identify the high-index side first; then apply the critical, Brewster, or numerical-aperture relation with all angles measured from their local normals.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`n_{\min}=\sqrt2\approx1.414`.

**Check.** A critical angle exists only from higher to lower index; the fiber acceptance must vanish when core and cladding indices are equal.

Problem 3.48 — infer a block index from a critical internal ray
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer a block index from a critical internal ray.

**Formula reference.** Use :eq:`schaum-3-4` and the definitions immediately above it.

**Worked application.**

1. Use the geometry to identify the high-index side first; then apply the critical, Brewster, or numerical-aperture relation with all angles measured from their local normals.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`n\approx1.63`.

**Check.** A critical angle exists only from higher to lower index; the fiber acceptance must vanish when core and cladding indices are equal.

Problem 3.49 — compute Brewster incidence for a measured liquid
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Compute brewster incidence for a measured liquid.

**Formula reference.** Use :eq:`schaum-3-4` and the definitions immediately above it.

**Worked application.**

1. Use the geometry to identify the high-index side first; then apply the critical, Brewster, or numerical-aperture relation with all angles measured from their local normals.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`\theta_B=\arctan(1/\sin45^\circ)=54.74^\circ` for air incident on the liquid.

**Check.** A critical angle exists only from higher to lower index; the fiber acceptance must vanish when core and cladding indices are equal.

Problem 3.50 — derive the acceptance angle of a clad optical fiber
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive the acceptance angle of a clad optical fiber.

**Formula reference.** Use :eq:`schaum-3-4` and the definitions immediately above it.

**Worked application.**

1. Use the geometry to identify the high-index side first; then apply the critical, Brewster, or numerical-aperture relation with all angles measured from their local normals.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Eliminating the core ray angle gives :math:`n_0\sin\theta_{\max}=\sqrt{n_{\rm core}^2-n_{\rm clad}^2}`.

**Check.** A critical angle exists only from higher to lower index; the fiber acceptance must vanish when core and cladding indices are equal.
