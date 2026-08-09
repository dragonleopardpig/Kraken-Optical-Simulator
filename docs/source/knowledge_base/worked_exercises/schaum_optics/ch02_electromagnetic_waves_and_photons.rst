Chapter 2: Electromagnetic Waves and Photons
============================================

Source: Eugene Hecht, *Schaum's Outline of Theory and Problems of
Optics* (1975), Chapter 2.  The entries below cover only the
chapter's **Supplementary Problems**; prompts are paraphrased and are not
reproduced.

Each topic derives its shared formula once.  Every numbered problem then
applies that derivation to the particular proof, calculation, or construction
in the book.  Read the source diagram alongside entries that depend on a figure.

Maxwell equations and electromagnetic waves
-------------------------------------------

**Formula and definitions.**

.. math::
   :label: schaum-2-1

   \mathbf B=\frac{1}{v}\hat{\mathbf k}\times\mathbf E,\qquad \mathbf E=-v\hat{\mathbf k}\times\mathbf B,\qquad v=\frac{c}{n}

For a transverse plane wave, :math:`\mathbf E`,
:math:`\mathbf B`, and :math:`\hat{\mathbf k}` form a right-handed orthogonal
triad.  Their amplitudes satisfy :math:`E_0=vB_0`; the phase and propagation
argument are common to both fields.

Problem 2.26 — reconstruct E from a specified plane-wave B field
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Reconstruct e from a specified plane-wave b field.

**Formula reference.** Use :eq:`schaum-2-1` and the definitions immediately above it.

**Worked application.**

1. Read the propagation sign from the constant-phase condition, use the cross product for orientation, and scale the companion amplitude by v.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`\lambda=500\,\mathrm{nm}`, :math:`v=c`, along :math:`+z`; :math:`E_0=200\,\mathrm{V/m}` with the transverse orientation fixed by :math:`\mathbf E\times\mathbf B`.

**Check.** Verify E·B=0, E×B points along propagation, and E0/B0=v.

Problem 2.27 — reconstruct B from a graphed electric field
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Reconstruct b from a graphed electric field.

**Formula reference.** Use :eq:`schaum-2-1` and the definitions immediately above it.

**Worked application.**

1. Read the propagation sign from the constant-phase condition, use the cross product for orientation, and scale the companion amplitude by v.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The companion field is transverse to both :math:`+x` and the graphed :math:`\mathbf E`; it has the same phase and amplitude :math:`B_0=E_0/c`.

**Check.** Verify E·B=0, E×B points along propagation, and E0/B0=v.

Problem 2.28 — reconstruct E from a graphed magnetic field
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Reconstruct e from a graphed magnetic field.

**Formula reference.** Use :eq:`schaum-2-1` and the definitions immediately above it.

**Worked application.**

1. Read the propagation sign from the constant-phase condition, use the cross product for orientation, and scale the companion amplitude by v.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The right-hand triad gives :math:`\mathbf E` along :math:`+y`; the graph's amplitude corresponds to :math:`E_0\approx7.6\times10^3\,\mathrm{V/m}`.

**Check.** Verify E·B=0, E×B points along propagation, and E0/B0=v.

Problem 2.29 — determine a field from wavelength, direction, and irradiance
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Determine a field from wavelength, direction, and irradiance.

**Formula reference.** Use :eq:`schaum-2-1` and the definitions immediately above it.

**Worked application.**

1. Read the propagation sign from the constant-phase condition, use the cross product for orientation, and scale the companion amplitude by v.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`E_0=\sqrt{2I/(c\epsilon_0)}\approx30.0\,\mathrm{V/m}`.  For propagation along :math:`+y` with :math:`\mathbf B` in the xy plane, choose :math:`\mathbf E\parallel+z` and :math:`\mathbf B\parallel+x`.

**Check.** Verify E·B=0, E×B points along propagation, and E0/B0=v.

Index of refraction
-------------------

**Formula and definitions.**

.. math::
   :label: schaum-2-2

   v=\frac{c}{n},\qquad \lambda=\frac{\lambda_0}{n},\qquad k=\frac{2\pi n}{\lambda_0},\qquad \Delta t=\frac{L(n_2-n_1)}{c}

Frequency is unchanged at a stationary interface, so reducing
the phase velocity by :math:`n` reduces wavelength by the same factor.  For a
nonmagnetic transparent material, :math:`n\simeq\sqrt{\epsilon_r}`.

Problem 2.30 — compute propagation number in a dielectric
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Compute propagation number in a dielectric.

**Formula reference.** Use :eq:`schaum-2-2` and the definitions immediately above it.

**Worked application.**

1. Select the relation matching the requested propagation number, wavelength ratio, transit delay, or dielectric constant and solve symbolically before inserting units.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`k=1.57\times10^7\,\mathrm{rad/m}`.

**Check.** The vacuum limit n=1 must give v=c and λ=λ0; the larger index must have the shorter wavelength and longer transit time.

Problem 2.31 — infer path length from a transit-time difference
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer path length from a transit-time difference.

**Formula reference.** Use :eq:`schaum-2-2` and the definitions immediately above it.

**Worked application.**

1. Select the relation matching the requested propagation number, wavelength ratio, transit delay, or dielectric constant and solve symbolically before inserting units.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`L=c\Delta t/(1.46-1)=6.52\times10^2\,\mathrm m`.

**Check.** The vacuum limit n=1 must give v=c and λ=λ0; the larger index must have the shorter wavelength and longer transit time.

Problem 2.32 — compare wavelengths in diamond and zircon
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Compare wavelengths in diamond and zircon.

**Formula reference.** Use :eq:`schaum-2-2` and the definitions immediately above it.

**Worked application.**

1. Select the relation matching the requested propagation number, wavelength ratio, transit delay, or dielectric constant and solve symbolically before inserting units.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`\lambda_D/\lambda_Z=n_Z/n_D=0.796`.

**Check.** The vacuum limit n=1 must give v=c and λ=λ0; the larger index must have the shorter wavelength and longer transit time.

Problem 2.33 — infer refractive index from dielectric constant
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer refractive index from dielectric constant.

**Formula reference.** Use :eq:`schaum-2-2` and the definitions immediately above it.

**Worked application.**

1. Select the relation matching the requested propagation number, wavelength ratio, transit delay, or dielectric constant and solve symbolically before inserting units.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`n\simeq\sqrt{2.381}=1.543`.

**Check.** The vacuum limit n=1 must give v=c and λ=λ0; the larger index must have the shorter wavelength and longer transit time.

Irradiance
----------

**Formula and definitions.**

.. math::
   :label: schaum-2-3

   I=\frac{P}{A},\qquad U=IAt,\qquad \langle S\rangle=I=\frac12 c\epsilon_0E_0^2,\qquad P_{\rm iso}=4\pi r^2I

The instantaneous Poynting vector is
:math:`\mathbf S=\mathbf E\times\mathbf H`.  Since
:math:`\langle\sin^2\Phi\rangle=1/2` and :math:`H_0=E_0/Z_0`, its cycle
average becomes :math:`I=E_0^2/(2Z_0)=c\epsilon_0E_0^2/2`.

Problem 2.34 — convert flux density and exposure time to energy
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Convert flux density and exposure time to energy.

**Formula reference.** Use :eq:`schaum-2-3` and the definitions immediately above it.

**Worked application.**

1. Convert area to square metres, use the cycle-averaged expression for harmonic fields, and integrate over time or sphere area only after finding I.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`U=10^4\,\mathrm J`.

**Check.** Power has units W, exposure energy J, and electric-field amplitude V/m; inverse-square spreading must conserve 4πr²I.

Problem 2.35 — obtain focused-laser irradiance and field amplitude
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Obtain focused-laser irradiance and field amplitude.

**Formula reference.** Use :eq:`schaum-2-3` and the definitions immediately above it.

**Worked application.**

1. Convert area to square metres, use the cycle-averaged expression for harmonic fields, and integrate over time or sphere area only after finding I.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`I=3.0\times10^{12}\,\mathrm{W/m^2}` and :math:`E_0\approx4.75\times10^7\,\mathrm{V/m}`.

**Check.** Power has units W, exposure energy J, and electric-field amplitude V/m; inverse-square spreading must conserve 4πr²I.

Problem 2.36 — derive the vacuum irradiance coefficient
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive the vacuum irradiance coefficient.

**Formula reference.** Use :eq:`schaum-2-3` and the definitions immediately above it.

**Worked application.**

1. Convert area to square metres, use the cycle-averaged expression for harmonic fields, and integrate over time or sphere area only after finding I.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Inserting :math:`c` and :math:`\epsilon_0` gives :math:`I=(1.33\times10^{-3}\,\mathrm{W/V^2})E_0^2` in vacuum.

**Check.** Power has units W, exposure energy J, and electric-field amplitude V/m; inverse-square spreading must conserve 4πr²I.

Problem 2.37 — recover total power from a measured point-source field
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Recover total power from a measured point-source field.

**Formula reference.** Use :eq:`schaum-2-3` and the definitions immediately above it.

**Worked application.**

1. Convert area to square metres, use the cycle-averaged expression for harmonic fields, and integrate over time or sphere area only after finding I.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`P=4\pi r^2(c\epsilon_0E_0^2/2)\approx1.67\times10^2\,\mathrm W`.

**Check.** Power has units W, exposure energy J, and electric-field amplitude V/m; inverse-square spreading must conserve 4πr²I.

Problem 2.38 — derive irradiance from a sinusoidal electric field
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive irradiance from a sinusoidal electric field.

**Formula reference.** Use :eq:`schaum-2-3` and the definitions immediately above it.

**Worked application.**

1. Convert area to square metres, use the cycle-averaged expression for harmonic fields, and integrate over time or sphere area only after finding I.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Time averaging :math:`c\epsilon_0E_0^2\sin^2\Phi` gives :math:`I=c\epsilon_0E_0^2/2`.

**Check.** Power has units W, exposure energy J, and electric-field amplitude V/m; inverse-square spreading must conserve 4πr²I.

Photon energy and momentum
--------------------------

**Formula and definitions.**

.. math::
   :label: schaum-2-4

   E_\gamma=h\nu=\frac{hc}{\lambda},\qquad p_\gamma=\frac{E_\gamma}{c}=\frac{h}{\lambda},\qquad p_{\rm rad}=\frac{I}{c}\ \text{(absorbed)},\ \frac{2I}{c}\ \text{(reflected)}

A photon reverses momentum on perfect reflection, transferring
:math:`2p_\gamma`; absorption transfers :math:`p_\gamma`.  Multiplying the
per-photon transfer by photon rate :math:`P/E_\gamma` gives force
:math:`P/c` or :math:`2P/c`.

Problem 2.39 — derive the photon-energy wavelength shortcut
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive the photon-energy wavelength shortcut.

**Formula reference.** Use :eq:`schaum-2-4` and the definitions immediately above it.

**Worked application.**

1. Use hc after converting wavelength to metres (or 1239 eV·nm consistently), and choose the absorption/reflection momentum factor explicitly.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Unit conversion gives :math:`E_\gamma(\mathrm{eV})=1239.84/\lambda(\mathrm{nm})`, conventionally rounded to 1239.

**Check.** Photon energy and momentum are positive; perfect reflection must double the pressure obtained for perfect absorption.

Problem 2.40 — calculate solar radiation pressure for reflection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Calculate solar radiation pressure for reflection.

**Formula reference.** Use :eq:`schaum-2-4` and the definitions immediately above it.

**Worked application.**

1. Use hc after converting wavelength to metres (or 1239 eV·nm consistently), and choose the absorption/reflection momentum factor explicitly.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`p_{\rm rad}\approx9.8\times10^{-6}\,\mathrm{N/m^2}`.

**Check.** Photon energy and momentum are positive; perfect reflection must double the pressure obtained for perfect absorption.

Problem 2.41 — find the photoelectric threshold wavelength
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find the photoelectric threshold wavelength.

**Formula reference.** Use :eq:`schaum-2-4` and the definitions immediately above it.

**Worked application.**

1. Use hc after converting wavelength to metres (or 1239 eV·nm consistently), and choose the absorption/reflection momentum factor explicitly.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`\lambda_{\max}=hc/(1.8\,\mathrm{eV})\approx688\,\mathrm{nm}`.

**Check.** Photon energy and momentum are positive; perfect reflection must double the pressure obtained for perfect absorption.

Problem 2.42 — find flashlight recoil thrust
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find flashlight recoil thrust.

**Formula reference.** Use :eq:`schaum-2-4` and the definitions immediately above it.

**Worked application.**

1. Use hc after converting wavelength to metres (or 1239 eV·nm consistently), and choose the absorption/reflection momentum factor explicitly.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`F=P/c\approx3.34\times10^{-12}\,\mathrm N` for a collimated 1 mW output; use :math:`2P/c` only if the emitted beam is replaced by a perfectly reflected incident beam.

**Check.** Photon energy and momentum are positive; perfect reflection must double the pressure obtained for perfect absorption.

Problem 2.43 — find laser force on a reflecting microsphere
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find laser force on a reflecting microsphere.

**Formula reference.** Use :eq:`schaum-2-4` and the definitions immediately above it.

**Worked application.**

1. Use hc after converting wavelength to metres (or 1239 eV·nm consistently), and choose the absorption/reflection momentum factor explicitly.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The reflecting area intercepts the full 600-W beam, so :math:`F=2P/c\approx4.0\times10^{-6}\,\mathrm N`.

**Check.** Photon energy and momentum are positive; perfect reflection must double the pressure obtained for perfect absorption.

Electromagnetic-photon spectrum
-------------------------------

**Formula and definitions.**

.. math::
   :label: schaum-2-5

   \nu=\frac{c}{\lambda},\qquad T=\frac{1}{\nu}=\frac{\lambda}{c},\qquad E_\gamma=\frac{hc}{\lambda},\qquad N=\frac{E_{\rm total}}{E_\gamma}

Classify the radiation from its wavelength or frequency, then
use the vacuum dispersion relation.  Photon count is total energy divided by
the single-photon energy; convert :math:`1\,\mathrm{erg}=10^{-7}\,\mathrm J`
before division.

Problem 2.44 — classify and quantify the 21-cm hydrogen line
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Classify and quantify the 21-cm hydrogen line.

**Formula reference.** Use :eq:`schaum-2-5` and the definitions immediately above it.

**Worked application.**

1. Carry the wavelength conversion first, calculate ν or T, then use the same wavelength in hc/λ and divide total energy when a photon count is requested.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Microwave radiation: :math:`\nu\approx1.43\times10^9\,\mathrm{Hz}` and :math:`E_\gamma\approx9.46\times10^{-25}\,\mathrm J`.

**Check.** Longer wavelengths have lower frequency and photon energy; N must be dimensionless and inversely proportional to photon energy.

Problem 2.45 — characterize extremely long radio waves
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Characterize extremely long radio waves.

**Formula reference.** Use :eq:`schaum-2-5` and the definitions immediately above it.

**Worked application.**

1. Carry the wavelength conversion first, calculate ν or T, then use the same wavelength in hc/λ and divide total energy when a photon count is requested.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Radio-frequency radiation with :math:`T\approx100\,\mathrm s` and :math:`E_\gamma\approx4.14\times10^{-17}\,\mathrm{eV}`.

**Check.** Longer wavelengths have lower frequency and photon energy; N must be dimensionless and inversely proportional to photon energy.

Problem 2.46 — count photons carrying one erg at three wavelengths
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Count photons carrying one erg at three wavelengths.

**Formula reference.** Use :eq:`schaum-2-5` and the definitions immediately above it.

**Worked application.**

1. Carry the wavelength conversion first, calculate ν or T, then use the same wavelength in hc/λ and divide total energy when a photon count is requested.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** For one erg the photon counts are approximately :math:`5.0\times10^5`, :math:`2.5\times10^{11}`, and :math:`5.0\times10^{15}` at :math:`10^{-12}\,\mathrm m`, 500 nm, and 1 cm.

**Check.** Longer wavelengths have lower frequency and photon energy; N must be dimensionless and inversely proportional to photon energy.

Problem 2.47 — compare microwave and helium-neon photon energies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Compare microwave and helium-neon photon energies.

**Formula reference.** Use :eq:`schaum-2-5` and the definitions immediately above it.

**Worked application.**

1. Carry the wavelength conversion first, calculate ν or T, then use the same wavelength in hc/λ and divide total energy when a photon count is requested.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The photon energies are :math:`1.99\times10^{-24}\,\mathrm J` at 10 cm and :math:`3.14\times10^{-19}\,\mathrm J` at 632.9 nm; the microwave photon carries about :math:`6.3\times10^{-6}` as much energy.

**Check.** Longer wavelengths have lower frequency and photon energy; N must be dimensionless and inversely proportional to photon energy.
