Chapter 1: Wave Motion
======================

Source: Eugene Hecht, *Schaum's Outline of Theory and Problems of
Optics* (1975), Chapter 1.  The entries below cover only the
chapter's **Supplementary Problems**; prompts are paraphrased and are not
reproduced.

Each topic derives its shared formula once.  Every numbered problem then
applies that derivation to the particular proof, calculation, or construction
in the book.  Read the source diagram alongside entries that depend on a figure.

The wave equation
-----------------

**Formula and definitions.**

.. math::
   :label: schaum-1-1

   \frac{\partial^2 y}{\partial x^2}=\frac{1}{v^2}\frac{\partial^2 y}{\partial t^2},\qquad y=f(x-vt)+g(x+vt)

Put :math:`u=x\mp vt`.  The chain rule gives
:math:`y_x=f'(u)`, :math:`y_{xx}=f''(u)`, :math:`y_t=\mp vf'(u)`, and
:math:`y_{tt}=v^2f''(u)`.  Substitution proves the differential equation.
A plus sign in :math:`x+vt` moves a fixed value of :math:`u` toward decreasing
:math:`x`; a minus sign moves it toward increasing :math:`x`.

Problem 1.31 — test a squared-sine travelling profile
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Test a squared-sine travelling profile.

**Formula reference.** Use :eq:`schaum-1-1` and the definitions immediately above it.

**Worked application.**

1. Rewrite every term as a function of one travelling coordinate, differentiate twice, and compare coefficients before assigning the speed and sign.
2. Substitute the candidate directly into the governing equation and compare both sides term by term.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** With :math:`u=t+2z`, :math:`y_{zz}=4y_{uu}` and :math:`y_{tt}=y_{uu}`; hence the wave equation holds for :math:`v=1/2`, toward :math:`-z`.

**Check.** Both sides of the wave equation must contain the same second derivative; following a point of fixed phase must reproduce the stated direction.

Problem 1.32 — distinguish progressive from non-progressive functions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Distinguish progressive from non-progressive functions.

**Formula reference.** Use :eq:`schaum-1-1` and the definitions immediately above it.

**Worked application.**

1. Rewrite every term as a function of one travelling coordinate, differentiate twice, and compare coefficients before assigning the speed and sign.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Only candidates reducible to :math:`F(q\mp vt)` with one constant :math:`v` are progressive; the squared travelling coordinate and the linear :math:`y+t+B` candidate pass this test, while expressions mixing independent squares do not.

**Check.** Both sides of the wave equation must contain the same second derivative; following a point of fixed phase must reproduce the stated direction.

Problem 1.33 — recover speed and direction from three profiles
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Recover speed and direction from three profiles.

**Formula reference.** Use :eq:`schaum-1-1` and the definitions immediately above it.

**Worked application.**

1. Rewrite every term as a function of one travelling coordinate, differentiate twice, and compare coefficients before assigning the speed and sign.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`v_1=1` toward :math:`+y`, :math:`v_2=C/B` toward :math:`-x`, and :math:`v_3=C` toward :math:`+z`.

**Check.** Both sides of the wave equation must contain the same second derivative; following a point of fixed phase must reproduce the stated direction.

Problem 1.34 — prove that an arbitrary profile moving toward negative x is progressive
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Prove that an arbitrary profile moving toward negative x is progressive.

**Formula reference.** Use :eq:`schaum-1-1` and the definitions immediately above it.

**Worked application.**

1. Rewrite every term as a function of one travelling coordinate, differentiate twice, and compare coefficients before assigning the speed and sign.
2. Carry the algebra from the formula reference to the identity named in the paraphrased task; do not assume that identity as an intermediate step.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** For :math:`u=x+vt`, fixed :math:`u` gives :math:`x=u-vt`; the entire profile therefore translates toward :math:`-x` without changing shape.

**Check.** Both sides of the wave equation must contain the same second derivative; following a point of fixed phase must reproduce the stated direction.

Problem 1.35 — test a superposition of oppositely travelling profiles
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Test a superposition of oppositely travelling profiles.

**Formula reference.** Use :eq:`schaum-1-1` and the definitions immediately above it.

**Worked application.**

1. Rewrite every term as a function of one travelling coordinate, differentiate twice, and compare coefficients before assigning the speed and sign.
2. Substitute the candidate directly into the governing equation and compare both sides term by term.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Both travelling terms have speed magnitude :math:`B`.

**Check.** Both sides of the wave equation must contain the same second derivative; following a point of fixed phase must reproduce the stated direction.

Problem 1.36 — verify an arbitrary twice-differentiable travelling profile
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Verify an arbitrary twice-differentiable travelling profile.

**Formula reference.** Use :eq:`schaum-1-1` and the definitions immediately above it.

**Worked application.**

1. Rewrite every term as a function of one travelling coordinate, differentiate twice, and compare coefficients before assigning the speed and sign.
2. Evaluate both sides independently from the definitions and confirm equality without circular substitution.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Two chain-rule differentiations give :math:`y_{xx}=F''` times the squared spatial coefficient and :math:`y_{tt}=F''` times the squared temporal coefficient, so their ratio is :math:`1/v^2` for any twice-differentiable :math:`F`.

**Check.** Both sides of the wave equation must contain the same second derivative; following a point of fixed phase must reproduce the stated direction.

Problem 1.37 — relate the temporal and spatial rates of change
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Relate the temporal and spatial rates of change.

**Formula reference.** Use :eq:`schaum-1-1` and the definitions immediately above it.

**Worked application.**

1. Rewrite every term as a function of one travelling coordinate, differentiate twice, and compare coefficients before assigning the speed and sign.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** A one-way wave satisfies :math:`\partial_t y=-v\,\partial_x y` for :math:`F(x-vt)` and :math:`\partial_t y=+v\,\partial_x y` for :math:`G(x+vt)`.

**Check.** Both sides of the wave equation must contain the same second derivative; following a point of fixed phase must reproduce the stated direction.

Sinusoidal waves
----------------

**Formula and definitions.**

.. math::
   :label: schaum-1-2

   y=A\sin(kx\mp\omega t+\phi),\quad \lambda=\frac{2\pi}{k},\quad T=\frac{2\pi}{\omega},\quad v=\frac{\omega}{k}=f\lambda

A repetition in time requires :math:`\omega T=2\pi m`; the
fundamental period uses :math:`m=1`.  Likewise a spatial repetition requires
:math:`k\lambda=2\pi`.  Holding the phase constant yields
:math:`dx/dt=\pm\omega/k`, which fixes the propagation direction.

Problem 1.38 — derive temporal periodicity of a harmonic wave
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Derive temporal periodicity of a harmonic wave.

**Formula reference.** Use :eq:`schaum-1-2` and the definitions immediately above it.

**Worked application.**

1. Identify the coefficient of position as k and the magnitude of the time coefficient as omega; then evaluate or translate the phase exactly before taking a trigonometric value.
2. Keep the variables symbolic until the requested relationship is isolated, then reduce it to the limiting cases described in the check.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The fundamental temporal repetition is :math:`T=2\pi/\omega`; equivalently :math:`\omega T=2\pi`.

**Check.** The argument of a sine or cosine is dimensionless, and advancing by one period or wavelength must leave the disturbance unchanged.

Problem 1.39 — convert radio frequency to wavelength and back
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Convert radio frequency to wavelength and back.

**Formula reference.** Use :eq:`schaum-1-2` and the definitions immediately above it.

**Worked application.**

1. Identify the coefficient of position as k and the magnitude of the time coefficient as omega; then evaluate or translate the phase exactly before taking a trigonometric value.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`\lambda=3.0\times10^6\,\mathrm m` at 100 Hz; a 1 m wave requires :math:`3.0\times10^8\,\mathrm{Hz}` (300 MHz).

**Check.** The argument of a sine or cosine is dimensionless, and advancing by one period or wavelength must leave the disturbance unchanged.

Problem 1.40 — prove the sine-to-cosine phase identity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Prove the sine-to-cosine phase identity.

**Formula reference.** Use :eq:`schaum-1-2` and the definitions immediately above it.

**Worked application.**

1. Identify the coefficient of position as k and the magnitude of the time coefficient as omega; then evaluate or translate the phase exactly before taking a trigonometric value.
2. Carry the algebra from the formula reference to the identity named in the paraphrased task; do not assume that identity as an intermediate step.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Euler addition gives :math:`\sin(\Phi+\pi/2)=\sin\Phi\cos(\pi/2)+\cos\Phi\sin(\pi/2)=\cos\Phi`.

**Check.** The argument of a sine or cosine is dimensionless, and advancing by one period or wavelength must leave the disturbance unchanged.

Problem 1.41 — read speed, wavelength, and frequency from a wave
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Read speed, wavelength, and frequency from a wave.

**Formula reference.** Use :eq:`schaum-1-2` and the definitions immediately above it.

**Worked application.**

1. Identify the coefficient of position as k and the magnitude of the time coefficient as omega; then evaluate or translate the phase exactly before taking a trigonometric value.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`\lambda=200\,\mathrm{nm}`, :math:`f=1.5\times10^{15}\,\mathrm{Hz}`, and :math:`v=3.0\times10^8\,\mathrm{m\,s^{-1}}`.

**Check.** The argument of a sine or cosine is dimensionless, and advancing by one period or wavelength must leave the disturbance unchanged.

Problem 1.42 — evaluate a harmonic disturbance at a specified event
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Evaluate a harmonic disturbance at a specified event.

**Formula reference.** Use :eq:`schaum-1-2` and the definitions immediately above it.

**Worked application.**

1. Identify the coefficient of position as k and the magnitude of the time coefficient as omega; then evaluate or translate the phase exactly before taking a trigonometric value.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The specified event gives a disturbance magnitude of 10 units.

**Check.** The argument of a sine or cosine is dimensionless, and advancing by one period or wavelength must leave the disturbance unchanged.

Problem 1.43 — plot a time trace with amplitude and phase
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Plot a time trace with amplitude and phase.

**Formula reference.** Use :eq:`schaum-1-2` and the definitions immediately above it.

**Worked application.**

1. Identify the coefficient of position as k and the magnitude of the time coefficient as omega; then evaluate or translate the phase exactly before taking a trigonometric value.
2. Evaluate zeros, extrema, period, and phase origin before sketching the continuous curve.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** At :math:`x=0`, retain the stated amplitude and plot the sinusoid against :math:`t`; its intercept is fixed by :math:`\phi` and its period by :math:`2\pi/\omega`.

**Check.** The argument of a sine or cosine is dimensionless, and advancing by one period or wavelength must leave the disturbance unchanged.

Problem 1.44 — translate a photographed profile after four seconds
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Translate a photographed profile after four seconds.

**Formula reference.** Use :eq:`schaum-1-2` and the definitions immediately above it.

**Worked application.**

1. Identify the coefficient of position as k and the magnitude of the time coefficient as omega; then evaluate or translate the phase exactly before taking a trigonometric value.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The translated snapshot is :math:`y(x,4)=5\sin[\pi(x+8)/25]` for motion at :math:`2\,\mathrm{m/s}` toward :math:`-x`.

**Check.** The argument of a sine or cosine is dimensionless, and advancing by one period or wavelength must leave the disturbance unchanged.

Problem 1.45 — compare phase-locked readings at two detectors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Compare phase-locked readings at two detectors.

**Formula reference.** Use :eq:`schaum-1-2` and the definitions immediately above it.

**Worked application.**

1. Identify the coefficient of position as k and the magnitude of the time coefficient as omega; then evaluate or translate the phase exactly before taking a trigonometric value.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The first detector condition selects :math:`t'=7/8` modulo the period; the second detector is then also at the crest, so its reading is :math:`10^2` in the source units.

**Check.** The argument of a sine or cosine is dimensionless, and advancing by one period or wavelength must leave the disturbance unchanged.

Problem 1.46 — exploit integer position and period shifts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Exploit integer position and period shifts.

**Formula reference.** Use :eq:`schaum-1-2` and the definitions immediately above it.

**Worked application.**

1. Identify the coefficient of position as k and the magnitude of the time coefficient as omega; then evaluate or translate the phase exactly before taking a trigonometric value.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Integer spatial shifts and a one-period time shift add integral multiples of :math:`2\pi` to the phase, so the corresponding detector readings repeat unchanged.

**Check.** The argument of a sine or cosine is dimensionless, and advancing by one period or wavelength must leave the disturbance unchanged.

Problem 1.47 — test, sketch, and assign the speed of a candidate wave
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Test, sketch, and assign the speed of a candidate wave.

**Formula reference.** Use :eq:`schaum-1-2` and the definitions immediately above it.

**Worked application.**

1. Identify the coefficient of position as k and the magnitude of the time coefficient as omega; then evaluate or translate the phase exactly before taking a trigonometric value.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** It is a negative-x travelling profile with :math:`v=3.0\times10^8\,\mathrm{m\,s^{-1}}`.

**Check.** The argument of a sine or cosine is dimensionless, and advancing by one period or wavelength must leave the disturbance unchanged.

Phase and phase velocity
------------------------

**Formula and definitions.**

.. math::
   :label: schaum-1-3

   \Phi=kx-\omega t+\phi_0,\qquad \left.\frac{\partial\Phi}{\partial x}\right|_t=k,\qquad \left.\frac{\partial\Phi}{\partial t}\right|_x=-\omega,\qquad v_\phi=-\frac{\Phi_t}{\Phi_x}

At a specified event use :math:`E/E_0=\sin\Phi` (or the
cosine convention printed in the problem) to select the phase modulo
:math:`2\pi`.  Between two events,
:math:`\Delta\Phi=k\Delta x-\omega\Delta t`; solve this linear relation for
the requested separation, elapsed time, or phase speed.

Problem 1.48 — infer initial phase from a negative field maximum
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer initial phase from a negative field maximum.

**Formula reference.** Use :eq:`schaum-1-3` and the definitions immediately above it.

**Worked application.**

1. Write the complete phase first, retain the 2πm family when positions are not unique, and only then substitute the event data.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** For the sine convention, :math:`\sin\phi_0=-1`, hence :math:`\phi_0=3\pi/2\pmod{2\pi}`.

**Check.** Substitution into the original phase must recover the requested phase difference; equivalent answers can differ by an integer multiple of 2π.

Problem 1.49 — infer phase when the spatial origin is a maximum
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Infer phase when the spatial origin is a maximum.

**Formula reference.** Use :eq:`schaum-1-3` and the definitions immediately above it.

**Worked application.**

1. Write the complete phase first, retain the 2πm family when positions are not unique, and only then substitute the event data.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** For the sine convention, :math:`\phi_0=\pi/2\pmod{2\pi}`.

**Check.** Substitution into the original phase must recover the requested phase difference; equivalent answers can differ by an integer multiple of 2π.

Problem 1.50 — describe phase evolution at a fixed observer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Describe phase evolution at a fixed observer.

**Formula reference.** Use :eq:`schaum-1-3` and the definitions immediately above it.

**Worked application.**

1. Write the complete phase first, retain the 2πm family when positions are not unique, and only then substitute the event data.
2. Use signs, directions, and limiting behavior from the governing equations to classify the physical result.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** At fixed position, :math:`d\Phi/dt=-\omega`: the observed phase decreases uniformly in time for a wave travelling toward :math:`+x`.

**Check.** Substitution into the original phase must recover the requested phase difference; equivalent answers can differ by an integer multiple of 2π.

Problem 1.51 — describe phase variation across a snapshot
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Describe phase variation across a snapshot.

**Formula reference.** Use :eq:`schaum-1-3` and the definitions immediately above it.

**Worked application.**

1. Write the complete phase first, retain the 2πm family when positions are not unique, and only then substitute the event data.
2. Use signs, directions, and limiting behavior from the governing equations to classify the physical result.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** At fixed time, :math:`d\Phi/dx=k`: the snapshot phase increases uniformly with position.

**Check.** Substitution into the original phase must recover the requested phase difference; equivalent answers can differ by an integer multiple of 2π.

Problem 1.52 — find separations producing a sixty-degree phase offset
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Find separations producing a sixty-degree phase offset.

**Formula reference.** Use :eq:`schaum-1-3` and the definitions immediately above it.

**Worked application.**

1. Write the complete phase first, retain the 2πm family when positions are not unique, and only then substitute the event data.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** :math:`\lambda=1\,\mu\mathrm m`, hence :math:`\Delta x=(m+1/6)\lambda`: 166.7 nm, 1166.7 nm, 2166.7 nm, … .

**Check.** Substitution into the original phase must recover the requested phase difference; equivalent answers can differ by an integer multiple of 2π.

Problem 1.53 — count phase cycles and wave-train length
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Count phase cycles and wave-train length.

**Formula reference.** Use :eq:`schaum-1-3` and the definitions immediately above it.

**Worked application.**

1. Write the complete phase first, retain the 2πm family when positions are not unique, and only then substitute the event data.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** (a) :math:`5.0\times10^5` cycles, or :math:`10^6\pi` rad; (b) the train length is :math:`0.300\,\mathrm m`.

**Check.** Substitution into the original phase must recover the requested phase difference; equivalent answers can differ by an integer multiple of 2π.

Problem 1.54 — construct a wave from measured phase gradients
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Construct a wave from measured phase gradients.

**Formula reference.** Use :eq:`schaum-1-3` and the definitions immediately above it.

**Worked application.**

1. Write the complete phase first, retain the 2πm family when positions are not unique, and only then substitute the event data.
2. Evaluate all breakpoints or ray/phasor endpoints first, then join only the intervals allowed by the governing relation.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The measured gradients give :math:`y(x,t)=10\sin(4\pi\times10^8x-12\pi\times10^{14}t+\pi/3)` and :math:`v=3.0\times10^8\,\mathrm{m/s}`.

**Check.** Substitution into the original phase must recover the requested phase difference; equivalent answers can differ by an integer multiple of 2π.

Complex-number representation
-----------------------------

**Formula and definitions.**

.. math::
   :label: schaum-1-4

   z=a+ib,\quad z^*=a-ib,\quad \Re z=\frac{z+z^*}{2},\quad \Im z=\frac{z-z^*}{2i},\quad |z|=(zz^*)^{1/2}

Conjugation changes :math:`i` to :math:`-i` everywhere,
including exponential phases.  Euler's identity converts
:math:`Ae^{i\Phi}` to :math:`A(\cos\Phi+i\sin\Phi)`.  A physical squared
field is :math:`[\Re(Ae^{i\Phi})]^2=A^2\cos^2\Phi`, not merely the real part
of :math:`zz^*`.

Problem 1.55 — form complex conjugates
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Form complex conjugates.

**Formula reference.** Use :eq:`schaum-1-4` and the definitions immediately above it.

**Worked application.**

1. Apply conjugation algebraically, simplify products before taking a square root, and distinguish a real instantaneous field from its complex representative.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Replace every :math:`i` by :math:`-i`; in exponential form, :math:`(Ae^{i\Phi})^*=A^*e^{-i\Phi}`.

**Check.** The magnitude is real and non-negative; conjugating twice returns the original quantity, and real/imaginary parts reconstruct z.

Problem 1.56 — extract real parts of phasors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Extract real parts of phasors.

**Formula reference.** Use :eq:`schaum-1-4` and the definitions immediately above it.

**Worked application.**

1. Apply conjugation algebraically, simplify products before taking a square root, and distinguish a real instantaneous field from its complex representative.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** After Euler expansion, the two requested real parts reduce to :math:`-2` and :math:`2\cos(\omega t-kx)`.

**Check.** The magnitude is real and non-negative; conjugating twice returns the original quantity, and real/imaginary parts reconstruct z.

Problem 1.57 — extract imaginary parts of phasors
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Extract imaginary parts of phasors.

**Formula reference.** Use :eq:`schaum-1-4` and the definitions immediately above it.

**Worked application.**

1. Apply conjugation algebraically, simplify products before taking a square root, and distinguish a real instantaneous field from its complex representative.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The requested imaginary parts reduce to the sine quadratures of the first two phasors and zero for the explicitly real symmetric exponential pair.

**Check.** The magnitude is real and non-negative; conjugating twice returns the original quantity, and real/imaginary parts reconstruct z.

Problem 1.58 — calculate phasor magnitudes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Calculate phasor magnitudes.

**Formula reference.** Use :eq:`schaum-1-4` and the definitions immediately above it.

**Worked application.**

1. Apply conjugation algebraically, simplify products before taking a square root, and distinguish a real instantaneous field from its complex representative.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The magnitudes are :math:`1` and :math:`2[5+4\cos(2\omega t)]^{1/2}`.

**Check.** The magnitude is real and non-negative; conjugating twice returns the original quantity, and real/imaginary parts reconstruct z.

Problem 1.59 — square a real harmonic field without confusing it with intensity
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Square a real harmonic field without confusing it with intensity.

**Formula reference.** Use :eq:`schaum-1-4` and the definitions immediately above it.

**Worked application.**

1. Apply conjugation algebraically, simplify products before taking a square root, and distinguish a real instantaneous field from its complex representative.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The physical square is :math:`A^2\cos^2(kx-\omega t)=[(z+z^*)/2]^2`; it is not :math:`\Re(zz^*)`.

**Check.** The magnitude is real and non-negative; conjugating twice returns the original quantity, and real/imaginary parts reconstruct z.

Three-dimensional waves
-----------------------

**Formula and definitions.**

.. math::
   :label: schaum-1-5

   y(\mathbf r,t)=A\sin(\mathbf k\cdot\mathbf r-\omega t+\phi_0),\quad |\mathbf k|=\frac{2\pi}{\lambda},\quad \nabla\Phi=\mathbf k,\quad \omega=v|\mathbf k|

Write :math:`\mathbf k=k\hat{\mathbf s}`, where the supplied
direction is normalized to unit length.  The chain rule gives
:math:`\nabla^2 f(\Phi)=k^2f''(\Phi)` and
:math:`\partial_t^2f(\Phi)=\omega^2f''(\Phi)`, proving the 3-D wave equation
when :math:`\omega=vk`.

Problem 1.60 — verify an arbitrary three-dimensional plane-wave profile
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Verify an arbitrary three-dimensional plane-wave profile.

**Formula reference.** Use :eq:`schaum-1-5` and the definitions immediately above it.

**Worked application.**

1. Normalize the stated direction, form its dot product with (x,y,z), and insert k=2π/λ and ω=vk.
2. Evaluate both sides independently from the definitions and confirm equality without circular substitution.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** For direction cosines satisfying :math:`\alpha^2+\beta^2+\gamma^2=1`, the Laplacian is :math:`k^2f''` and the time derivative is :math:`\omega^2f''`; :math:`\omega=vk` completes the proof.

**Check.** The direction vector must have unit norm and every term in the phase must be dimensionless.

Problem 1.61 — write a wave along the diagonal in the xy plane
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Write a wave along the diagonal in the xy plane.

**Formula reference.** Use :eq:`schaum-1-5` and the definitions immediately above it.

**Worked application.**

1. Normalize the stated direction, form its dot product with (x,y,z), and insert k=2π/λ and ω=vk.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** One valid form is :math:`y=A\sin[(2\pi/(\lambda\sqrt2))(x+y)-\omega t+\phi_0]`, with :math:`\omega=2\pi v/\lambda`.

**Check.** The direction vector must have unit norm and every term in the phase must be dimensionless.

Problem 1.62 — identify the constant-time phase gradient
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Identify the constant-time phase gradient.

**Formula reference.** Use :eq:`schaum-1-5` and the definitions immediately above it.

**Worked application.**

1. Normalize the stated direction, form its dot product with (x,y,z), and insert k=2π/λ and ω=vk.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** At fixed time, :math:`\nabla\Phi=\mathbf k`; its magnitude is :math:`2\pi/\lambda`.

**Check.** The direction vector must have unit norm and every term in the phase must be dimensionless.

Problem 1.63 — normalize a propagation-direction vector
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Normalize a propagation-direction vector.

**Formula reference.** Use :eq:`schaum-1-5` and the definitions immediately above it.

**Worked application.**

1. Normalize the stated direction, form its dot product with (x,y,z), and insert k=2π/λ and ω=vk.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** The coefficients normalize to the propagation unit vector :math:`(\hat{\mathbf x}-2\hat{\mathbf y}+3\hat{\mathbf z})/\sqrt{14}`.

**Check.** The direction vector must have unit norm and every term in the phase must be dimensionless.

Problem 1.64 — write a Cartesian plane wave through a specified direction point
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Paraphrased task.** Write a cartesian plane wave through a specified direction point.

**Formula reference.** Use :eq:`schaum-1-5` and the definitions immediately above it.

**Worked application.**

1. Normalize the stated direction, form its dot product with (x,y,z), and insert k=2π/λ and ω=vk.
2. Solve the displayed relation symbolically for the requested quantity, substitute the source data with units, and round only the final value.
3. Substitute the values or boundary conditions attached to this
   problem number in the book and retain the source sign convention.

**Result.** Since :math:`(2,2,3)` has norm :math:`\sqrt{17}`, use :math:`\mathbf k=(2\pi/\lambda)(2,2,3)/\sqrt{17}` in :math:`A\sin(\mathbf k\cdot\mathbf r-\omega t+\phi_0)`.

**Check.** The direction vector must have unit norm and every term in the phase must be dimensionless.
