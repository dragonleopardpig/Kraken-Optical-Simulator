SOLUTIONS = {
    "1.31": (
        r"""
1. The printed argument is :math:`u=4\pi(t+z)`. Differentiate the squared sine before differentiating its argument: :math:`d(\sin^2u)/du=\sin2u`.
2. The first derivatives are :math:`\psi_t=4\pi A\sin2u` and :math:`\psi_z=4\pi A\sin2u`; differentiating again gives

   .. math::

      \psi_{tt}=32\pi^2A\cos2u,\qquad \psi_{zz}=32\pi^2A\cos2u.

3. Therefore :math:`\psi_{zz}=\psi_{tt}/v^2` with :math:`v=1` in the stated coordinate units. A fixed value of :math:`t+z` has :math:`dz/dt=-1`.
""",
        r"The profile satisfies the wave equation and translates toward negative :math:`z` at unit speed.",
        r"The factor of two from differentiating :math:`\sin2u` appears in both second derivatives; the speed follows their ratio, not the sine's period.",
    ),
    "1.32": (
        r"""
1. For :math:`\psi_1=A(x-t)^2`, put :math:`u=x-t`; it is a fixed profile translating at :math:`+1`.
2. The affine expression :math:`\psi_2=A(y+t+B)` is also :math:`F(y+t)`. Its second derivatives both vanish, so the differential equation cannot determine a unique speed; tracking a fixed level gives velocity :math:`-1`.
3. For the quadratic-phase sine, set :math:`u=B(x^2-Ct^2)`. The first-derivative ratio is

   .. math::

      -\frac{\psi_t}{\psi_x}=\frac{Ct}{x}.

   This is not a constant translation speed. For :math:`\psi_4=A/(Bx^2-t)`, the same ratio is :math:`1/(2Bx)`, again position dependent. Singular points are excluded.
""",
        r"For generic nonzero constants, the nondegenerate travelling wave is :math:`\psi_1`; :math:`\psi_2` is a degenerate affine travelling profile. The printed answer lists only :math:`\psi_1`.",
        r"A rigidly translated differentiable profile obeys :math:`\psi_t=-v\psi_x` with constant :math:`v`; satisfying a second-order equation trivially is a separate issue.",
    ),
    "1.33": (
        r"""
1. Write the first argument as :math:`y-t`; its constant-level trajectory is :math:`y=t+u_0`.
2. Factor the second argument as :math:`B[x+(C/B)t+D/B]`. Its velocity is :math:`dx/dt=-C/B`.
3. Complete the square in the exponential:

   .. math::

      Bz^2+BC^2t^2-2BCzt=B(z-Ct)^2.

   Thus its constant profile moves with :math:`dz/dt=C`. Speeds are absolute values; directions quoted below assume positive :math:`B,C`.
""",
        r"The velocities are :math:`+1\,\hat{\mathbf y}`, :math:`-(C/B)\hat{\mathbf x}`, and :math:`C\hat{\mathbf z}`.",
        r"The offset :math:`D` changes the origin of the profile but cannot change its velocity.",
    ),
    "1.34": (
        r"""
1. At :math:`t=0`, denote the graph by :math:`G(x)=g(x)`. At a later time the value at :math:`x` is :math:`G(x+vt)`.
2. Follow a recognizable point initially at :math:`x_0`. It remains the same point when :math:`x+vt=x_0`, so :math:`x=x_0-vt`.
3. Any two such points have separation :math:`x_b(t)-x_a(t)=x_{b0}-x_{a0}`. Their heights and separation remain unchanged, establishing translation without distortion.
""",
        r":math:`g(x+vt)` is a rigid profile travelling toward :math:`-x` for :math:`v>0`.",
        r"Replacing :math:`t` by :math:`t+\Delta t` shifts every feature left by :math:`v\Delta t`, as shown in the wave-profile diagram.",
    ),
    "1.35": (
        r"""
1. Complete the square :math:`Cx^2+B^2Ct^2-2BCxt=C(x-Bt)^2`.
2. Define :math:`G(u)=A(u+D)^2` and :math:`F(u)=Ae^{Cu^2}`. The disturbance is :math:`G(x+Bt)+F(x-Bt)`.
3. Differentiate each term using its own travelling coordinate:

   .. math::

      \psi_{xx}=G''+F'',\qquad \psi_{tt}=B^2G''+B^2F''=B^2\psi_{xx}.

   Linearity permits adding the two solutions, even though they move in opposite directions.
""",
        r"The sum solves the wave equation with speed magnitude :math:`|B|`; it is generally not one rigidly translating profile.",
        r"The two components must have the same speed magnitude for their sum to satisfy this one wave equation.",
    ),
    "1.36": (
        r"""
1. Set :math:`u=t-x/v`, with constant nonzero :math:`v` and a twice-differentiable function :math:`h`.
2. Apply the chain rule twice:

   .. math::

      \psi_t=h'(u),\quad \psi_{tt}=h''(u),\quad
      \psi_x=-h'(u)/v,\quad \psi_{xx}=h''(u)/v^2.

3. Subtract the two sides of the wave equation; the remainder is identically zero. Following :math:`u=u_0` gives :math:`x=v(t-u_0)`.
""",
        r":math:`h(t-x/v)` is a wave travelling at signed velocity :math:`v`.",
        r"The minus sign in the first spatial derivative disappears after the second derivative.",
    ),
    "1.37": (
        r"""
1. For a right-travelling profile :math:`\psi=F(x-vt)`, differentiate while holding the other independent variable fixed.
2. The resulting relations :math:`\psi_x=F'` and :math:`\psi_t=-vF'` eliminate the unknown profile derivative:

   .. math::

      \psi_t=-v\psi_x.

3. For :math:`G(x+vt)` the sign is positive. A sum of right- and left-travelling waves generally does not satisfy either first-order relation with one sign.
""",
        r"The multiplicative constant is :math:`-v` for rightward motion and :math:`+v` for leftward motion.",
        r"The units are displacement/time on both sides because :math:`v\psi_x` supplies the missing length/time factor.",
    ),
    "1.38": (
        r"""
1. At fixed position, advancing the time by :math:`T` changes the phase of :math:`A\sin(kx-\omega t+\phi)` by :math:`-\omega T`.
2. To repeat the entire waveform, rather than just one accidental value of the sine, this change must be :math:`2\pi` times an integer.
3. The smallest positive repeat uses :math:`\omega T=2\pi`, hence :math:`T=2\pi/\omega`. Combining :math:`\omega=2\pi f` and :math:`v=f\lambda` also gives :math:`T=\lambda/v`.
""",
        r":math:`T=2\pi/\omega=1/f=\lambda/v`.",
        r"A half-period changes the sign of a sine; it does not reproduce a general instantaneous displacement.",
    ),
    "1.39": (
        r"""
1. Electromagnetic waves in vacuum have :math:`v=c\simeq3.00\times10^8\,\mathrm{m/s}`.
2. At :math:`f=100\,\mathrm{Hz}`, use :math:`\lambda=c/f=(3.00\times10^8)/100=3.00\times10^6\,\mathrm m`.
3. For a one-metre wavelength, reverse the calculation: :math:`f=c/\lambda=3.00\times10^8\,\mathrm{Hz}=300\,\mathrm{MHz}`. The second value permits an antenna of a practical metre-scale length.
""",
        r":math:`\lambda=3.00\times10^6\,\mathrm m`; the one-metre carrier frequency is :math:`300\,\mathrm{MHz}`.",
        r"Multiplying either frequency by its wavelength must return :math:`c`.",
    ),
    "1.40": (
        r"""
1. Abbreviate the common phase by :math:`\Phi=kx-\omega t`.
2. Apply the sine addition identity, without assuming a special position or time:

   .. math::

      \sin(\Phi+\pi/2)=\sin\Phi\cos(\pi/2)+\cos\Phi\sin(\pi/2)
      =0+\cos\Phi.

3. The equality holds at every event. It changes the representation's initial phase, not the wavelength or propagation velocity.
""",
        r":math:`\sin(kx-\omega t+\pi/2)=\cos(kx-\omega t)`.",
        r"At :math:`\Phi=0` both expressions are one; at :math:`\Phi=\pi/2` both are zero.",
    ),
    "1.41": (
        r"""
1. Match the printed expression to :math:`10\cos[2\pi(x/\lambda-ft)]`. Its length denominator is :math:`2\times10^{-7}\,\mathrm m` and its frequency is :math:`1.5\times10^{15}\,\mathrm{Hz}`.
2. Convert the length: :math:`2\times10^{-7}\,\mathrm m=200\,\mathrm{nm}`. The angular quantities are :math:`k=\pi\times10^7\,\mathrm{rad/m}` and :math:`\omega=3\pi\times10^{15}\,\mathrm{rad/s}`.
3. Take their ratio: :math:`v=\omega/k=f\lambda=3.0\times10^8\,\mathrm{m/s}`. The minus sign before time means motion toward positive :math:`x`.
""",
        r":math:`\lambda=200\,\mathrm{nm}`, :math:`f=1.5\times10^{15}\,\mathrm{Hz}`, :math:`v=3.0\times10^8\,\mathrm{m/s}`.",
        r"The outer :math:`2\pi` is already present; do not insert another factor into the frequency.",
    ),
    "1.42": (
        r"""
1. Choose the positive-x sine convention :math:`y=10\sin(kx-\omega t)`; it satisfies the specified zero initial displacement. Here :math:`\omega=\pi/2\,\mathrm{rad/s}` and :math:`k=\omega/v=\pi/20\,\mathrm{rad/m}`.
2. At :math:`x=20\,\mathrm m`, :math:`t=3\,\mathrm s`, evaluate the phase before the sine:

   .. math::

      \Phi=(\pi/20)(20)-(\pi/2)(3)=-\pi/2,\qquad y=-10.

3. The requested magnitude is :math:`|y|=10`. The initial displacement alone does not fix the initial slope; reversing that slope reverses this signed answer.
""",
        r"The disturbance magnitude is 10 units; its signed value is :math:`-10` for the stated convention.",
        r"No calculated displacement magnitude may exceed the amplitude 10.",
    ),
    "1.43": (
        r"""
1. Set :math:`x=0` before inserting the constants :math:`y_0=3`, :math:`\omega=\pi/4`, and :math:`\epsilon=-\pi`. The spatial coefficient :math:`k=2\pi` then drops out.
2. The trace is :math:`y(0,t)=3\sin(\pi t/4-\pi)=-3\sin(\pi t/4)`, with period :math:`8\,\mathrm s`.
3. Plot the anchor points :math:`(t,y)=(0,0),(2,-3),(4,0),(6,3),(8,0)` and repeat every eight seconds. The initial slope is :math:`-3\pi/4`, so the trace initially descends.
""",
        r"A sine trace of amplitude 3 and period 8 s, starting at zero with negative slope.",
        r"The quarter-period extrema at 2 s and 6 s distinguish the specified phase from its opposite.",
    ),
    "1.44": (
        r"""
1. The photographed profile is :math:`F(x)=5\sin(\pi x/25)`. A wave moving toward negative :math:`x` at :math:`2\,\mathrm{m/s}` is :math:`y(x,t)=F(x+2t)`.
2. Four seconds corresponds to an eight-metre displacement, giving

   .. math::

      y(x,4)=5\sin\left[\frac{\pi}{25}(x+8)\right].

3. To sketch it, move every point of the initial graph eight metres left. Do not change its amplitude or its :math:`50\,\mathrm m` wavelength.
""",
        r":math:`y(x,4)=5\sin[\pi(x+8)/25]`.",
        r"The point initially at :math:`x=0` reappears at :math:`x=-8\,\mathrm m`.",
    ),
    "1.45": (
        r"""
1. For :math:`y=100\sin(2\pi x-4\pi t)`, the two detector phases differ by :math:`2\pi(10-2)=16\pi`.
2. This is eight full cycles, so their readings are identical at every common time. At the first detector's crest, :math:`4\pi-4\pi t'=\pi/2+2\pi m`.
3. Solving gives :math:`t'=7/8-m/2\,\mathrm s`. Every member of this family puts the second detector at a crest as well.
""",
        r"The second detector reads 100 units; :math:`t'=7/8\,\mathrm s` is one valid crest time.",
        r"The smallest nonnegative crest time is 3/8 s; 7/8 s is not unique because the period is 1/2 s.",
    ),
    "1.46": (
        r"""
1. At the same time :math:`T`, the phase change from integer position :math:`B` to integer position :math:`D` is :math:`2\pi(D-B)`.
2. Sine is unchanged by that integer number of cycles; therefore :math:`y(D,T)=y(B,T)=C`.
3. Advancing the time by one second adds :math:`-4\pi`, which is two periods of this wave. Thus :math:`y(D,T+1)=C` as well.
""",
        r"Both requested readings are :math:`C`.",
        r"The argument uses integer positions in the source's metre coordinate, and the time shift is two periods, not one.",
    ),
    "1.47": (
        r"""
1. Put :math:`u=x+ct`, where :math:`c=3\times10^8\,\mathrm{m/s}`. The argument in the numerator becomes :math:`bu`, with :math:`b=2\pi10^{15}/c`.
2. Rewrite the entire expression, including its denominator, as

   .. math::

      \psi=A\left(\frac{b}{2\times10^7}\right)^2\operatorname{sinc}^2(bu),
      \qquad \operatorname{sinc}q=\frac{\sin q}{q}.

3. This is a fixed squared-sinc profile translating left. Its apparent singularity at :math:`u=0` is removable: the peak is :math:`A(b/(2\times10^7))^2`. Zeros are at :math:`u=m\pi/b`, :math:`m\ne0`, and the side-lobe envelope decays as :math:`u^{-2}`.
""",
        r"After continuous extension at the origin, it solves the wave equation and travels toward :math:`-x` at :math:`c`.",
        r"Both numerator and denominator must be functions of the same travelling coordinate; testing the numerator alone is insufficient.",
    ),
    "1.48": (
        r"""
1. Use :math:`E=20\sin(kx-\omega t+\phi_0)\,\mathrm{V/m}`.
2. At the origin and initial time, :math:`-20=20\sin\phi_0`, hence :math:`\sin\phi_0=-1`.
3. The sine reaches :math:`-1` at :math:`3\pi/2` modulo :math:`2\pi`. Equivalently use :math:`-\pi/2`; the cosine representation would require a different numerical phase.
""",
        r":math:`\phi_0=3\pi/2+2\pi m`, :math:`m\in\mathbb Z`, for the sine convention.",
        r"Direct substitution gives :math:`E(0,0)=-20\,\mathrm{V/m}`.",
    ),
    "1.49": (
        r"""
1. A positive maximum at :math:`x=t=0` means :math:`E(0,0)/E_0=1`.
2. In the sine representation this requires :math:`\sin\phi_0=1`; therefore :math:`\phi_0=\pi/2+2\pi m`.
3. Distinguish a positive maximum from a maximum absolute value: the latter also permits a negative crest, with phase :math:`3\pi/2`.
""",
        r":math:`\phi_0=\pi/2\pmod{2\pi}` for a positive sine-wave maximum.",
        r"The spatial derivative is zero at the crest and its second derivative is negative.",
    ),
    "1.50": (
        r"""
1. Choose the phase :math:`\Phi=kx-\omega t+\phi_0` for motion toward positive :math:`x`.
2. At a fixed detector :math:`x=x_d`, the term :math:`kx_d+\phi_0` is constant. Thus :math:`\Phi(t+\Delta t)-\Phi(t)=-\omega\Delta t`.
3. The unwrapped phase is a descending straight line. A phase instrument reporting modulo :math:`2\pi` would show repeated wraps; these do not represent jumps in the physical field.
""",
        r":math:`(\partial\Phi/\partial t)_x=-\omega`.",
        r"In one period the unwrapped phase falls by :math:`2\pi`, while the field returns to its original value.",
    ),
    "1.51": (
        r"""
1. Freeze the time at :math:`t_0`; the phase is :math:`\Phi(x)=kx+(\phi_0-\omega t_0)`.
2. Two positions separated by :math:`\Delta x` have phase difference :math:`\Delta\Phi=k\Delta x`.
3. Consequently the spatial slope is :math:`k`, and a distance :math:`\lambda=2\pi/k` advances the phase by one full cycle. The diagram's phase slope and wavelength encode the same information.
""",
        r":math:`(\partial\Phi/\partial x)_t=k`.",
        r"Position must be expressed in the same length units used to specify :math:`k`.",
    ),
    "1.52": (
        r"""
1. Calculate :math:`\lambda=c/f=(3\times10^8)/(3\times10^{14})=10^{-6}\,\mathrm m`.
2. The requested phase offset is :math:`60^\circ=\pi/3`. Since :math:`k\Delta x=\pi/3+2\pi m`, divide by :math:`k=2\pi/\lambda`.
3. This gives :math:`\Delta x=(m+1/6)\lambda`. For :math:`m=0,1,2`, the positive separations are 166.7, 1166.7, and 2166.7 nm. Reversing the ordering of the two points reverses the signed offset.
""",
        r":math:`\Delta x=(m+1/6)\,\mu\mathrm m` for a signed :math:`+60^\circ` phase difference modulo a cycle.",
        r"The smallest positive separation is one sixth of a wavelength, not one sixth of a metre.",
    ),
    "1.53": (
        r"""
1. Convert :math:`500\,\mathrm{THz}=5.00\times10^{14}\,\mathrm{Hz}` and a billionth of a second to :math:`\Delta t=10^{-9}\,\mathrm s`.
2. The number of cycles is :math:`N=f\Delta t=5.00\times10^5`; the phase-change magnitude is :math:`2\pi N=10^6\pi\,\mathrm{rad}`.
3. The associated train length is :math:`\ell=c\Delta t=0.300\,\mathrm m`. Independently, :math:`\lambda=c/f=600\,\mathrm{nm}` and :math:`N\lambda=0.300\,\mathrm m`.
""",
        r"A phase change of :math:`10^6\pi` radians in magnitude and a 0.300 m train.",
        r"Frequency times time counts cycles; multiplying by :math:`2\pi` is needed to obtain radians.",
    ),
    "1.54": (
        r"""
1. The printed spatial gradient is :math:`k=4\pi\times10^6\,\mathrm{rad/m}`; the time-gradient magnitude is :math:`\omega=12\pi\times10^{14}\,\mathrm{rad/s}`.
2. Positive-x motion uses a negative time term. With amplitude 10 and initial phase :math:`\pi/3`, write

   .. math::

      y=10\sin(4\pi10^6x-12\pi10^{14}t+\pi/3).

3. Division gives :math:`v=\omega/k=3\times10^8\,\mathrm{m/s}`. The exponent on the spatial gradient is 6, not 8; the latter would contradict the stated speed.
""",
        r"The displayed wave has :math:`v=3.0\times10^8\,\mathrm{m/s}` toward positive :math:`x`.",
        r"Differentiating its phase reproduces both measured gradients and :math:`y(0,0)=5\sqrt3`.",
    ),
    "1.55": (
        r"""
1. Rationalize the first number: :math:`(1-4i)/(2i)=-2-i/2`, so its conjugate is :math:`-2+i/2`.
2. Combine the phases in the second: :math:`2e^{i\omega t}e^{-ikx}=2e^{i(\omega t-kx)}`. Conjugation reverses the entire phase.
3. For the third, use :math:`1/(5i)=-i/5` and :math:`(4i)^2=-16`, giving :math:`16+i/20`. Its conjugate is therefore :math:`16-i/20`.
""",
        r"The conjugates are :math:`-2+i/2`, :math:`2e^{-i(\omega t-kx)}`, and :math:`16-i/20`.",
        r"Each original-plus-conjugate is twice a real number, and their products are nonnegative real numbers.",
    ),
    "1.56": (
        r"""
1. Multiply :math:`(1-4i)/(2i)` by :math:`-i/(-i)` to obtain :math:`-2-i/2`.
2. Euler's identity gives :math:`2e^{i(\omega t-kx)}=2\cos(\omega t-kx)+2i\sin(\omega t-kx)`.
3. Read the coefficients independent of :math:`i`; these, not the absolute values of the expressions, are the requested real parts.
""",
        r":math:`\Re z_1=-2` and :math:`\Re z_2=2\cos(\omega t-kx)`.",
        r"The real part can be negative; it must not be replaced by the complex magnitude.",
    ),
    "1.57": (
        r"""
1. Multiplying exponentials adds phases, so the first expression is :math:`5e^{i(kx+\omega t+\epsilon)}`.
2. Dividing the second pair subtracts the denominator's phase, giving :math:`(A/B)e^{i(\omega t-kx+\epsilon)}` for real :math:`A,B`.
3. The symmetric pair is :math:`(e^{i\omega t}+e^{-i\omega t})/2=\cos\omega t`; the opposite imaginary contributions cancel.
""",
        r"The imaginary parts are :math:`5\sin(kx+\omega t+\epsilon)`, :math:`(A/B)\sin(\omega t-kx+\epsilon)`, and zero.",
        r"The imaginary part is the real coefficient multiplying :math:`i`, not that coefficient times :math:`i`.",
    ),
    "1.58": (
        r"""
1. A pure phase :math:`e^{i\Phi}` has :math:`zz^*=1`; its magnitude is one.
2. Factor :math:`e^{iky}` from the second expression, leaving :math:`2e^{i\omega t}+4e^{-i\omega t}`. The unit phase factor cannot change its magnitude.
3. Multiply by the conjugate and collect the cross terms:

   .. math::

      |z|^2=4+16+8e^{2i\omega t}+8e^{-2i\omega t}
      =20+16\cos2\omega t.

   Take the positive square root only after combining the terms.
""",
        r"The magnitudes are :math:`1` and :math:`2\sqrt{5+4\cos2\omega t}`.",
        r"The second magnitude ranges from :math:`|4-2|=2` to :math:`4+2=6`, as required by vector addition.",
    ),
    "1.59": (
        r"""
1. Introduce :math:`z=Ae^{i\Phi}` with :math:`\Phi=kx-\omega t`; the physical displacement is :math:`y=(z+z^*)/2`.
2. Square that real quantity:

   .. math::

      y^2=\frac{z^2+2zz^*+(z^*)^2}{4}
      =\frac{A^2}{2}(1+\cos2\Phi)=A^2\cos^2\Phi.

3. By contrast :math:`zz^*=A^2` is constant. It contains amplitude information but omits the instantaneous oscillation. Time averaging the physical square gives :math:`A^2/2`.
""",
        r":math:`y^2=A^2\cos^2(kx-\omega t)`, whereas :math:`\langle y^2\rangle=A^2/2`.",
        r"At a zero crossing the physical square vanishes although :math:`zz^*` remains :math:`A^2`.",
    ),
    "1.60": (
        r"""
1. Let :math:`u=k(\alpha x+\beta y+\gamma z)-\omega t`, with unit direction cosines satisfying :math:`\alpha^2+\beta^2+\gamma^2=1`.
2. The three second spatial derivatives are :math:`k^2\alpha^2f''`, :math:`k^2\beta^2f''`, and :math:`k^2\gamma^2f''`; summing gives :math:`\nabla^2f=k^2f''`.
3. The time derivative is :math:`f_{tt}=\omega^2f''`. Thus :math:`\nabla^2f=f_{tt}/v^2` precisely when :math:`\omega^2=v^2k^2`. Constant-phase surfaces are planes normal to :math:`(\alpha,\beta,\gamma)`.
""",
        r"Every twice-differentiable profile of this form is a plane wave when :math:`\omega=vk`.",
        r"If the direction vector is not normalized, its norm must be included in the magnitude of the wavevector.",
    ),
    "1.61": (
        r"""
1. The supplied direction :math:`\hat{\mathbf s}=(\hat{\mathbf x}+\hat{\mathbf y})/\sqrt2` is already normalized.
2. Form :math:`\mathbf k=(2\pi/\lambda)\hat{\mathbf s}`, so :math:`\mathbf k\cdot\mathbf r=2\pi(x+y)/(\lambda\sqrt2)`.
3. Insert :math:`\omega=2\pi v/\lambda` and choose an arbitrary phase origin, for example zero. Translation along :math:`\hat{\mathbf s}` by :math:`\lambda` adds exactly :math:`2\pi`.
""",
        r":math:`\psi=A\sin[2\pi(x+y)/(\lambda\sqrt2)-2\pi vt/\lambda]`.",
        r"The component wavelengths along the coordinate axes are :math:`\sqrt2\lambda`; the wavelength along propagation is :math:`\lambda`.",
    ),
    "1.62": (
        r"""
1. Write :math:`\Phi=k_xx+k_yy+k_zz-\omega t+\phi_0`.
2. At constant time, its partial derivatives are respectively :math:`k_x,k_y,k_z`.
3. Assemble the gradient:

   .. math::

      \nabla\Phi=k_x\hat{\mathbf x}+k_y\hat{\mathbf y}+k_z\hat{\mathbf z}=\mathbf k.

   A displacement tangent to a wavefront has :math:`\mathbf k\cdot d\mathbf r=0`, explaining why this vector is normal to the wavefront.
""",
        r":math:`(\nabla\Phi)_t=\mathbf k` with magnitude :math:`2\pi/\lambda`.",
        r"The gradient has units radians per metre and points toward increasing spatial phase.",
    ),
    "1.63": (
        r"""
1. Read the three spatial coefficients from the phase: :math:`\mathbf k=k(1,-2,3)/\sqrt{14}`.
2. Its norm is :math:`k\sqrt{1+4+9}/\sqrt{14}=k`. Divide the coefficient vector by this norm.
3. Since the time term is :math:`-\omega t`, the constant-phase surfaces advance along this vector, not its negative.
""",
        r":math:`\hat{\mathbf s}=(\hat{\mathbf x}-2\hat{\mathbf y}+3\hat{\mathbf z})/\sqrt{14}`.",
        r"The direction cosines have squared sum one; the negative y component must survive normalization.",
    ),
    "1.64": (
        r"""
1. The direction from the origin through :math:`(2,2,3)` has length :math:`\sqrt{2^2+2^2+3^2}=\sqrt{17}`.
2. Normalize it and multiply by :math:`k=2\pi/\lambda`: :math:`\mathbf k=(2\pi/\lambda)(2,2,3)/\sqrt{17}`.
3. Take the dot product with the observation coordinate and use the negative time sign for outward propagation. An arbitrary initial phase can be added without changing the direction.
""",
        r":math:`\psi=A\sin[2\pi(2x+2y+3z)/(\lambda\sqrt{17})-\omega t+\phi_0]`.",
        r"Putting :math:`\mathbf r=\ell(2,2,3)/\sqrt{17}` reduces the phase to :math:`k\ell-\omega t+\phi_0`.",
    ),
}
