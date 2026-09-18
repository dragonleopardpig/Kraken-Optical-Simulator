SOLUTIONS = {
    "5.48": (
        r"""
1. A wave travelling along :math:`+y` has phase :math:`\psi=ky-\omega t=\omega(y/v-t)` and no longitudinal electric component.
2. In the transverse :math:`xz` plane, a unit vector at :math:`45^\circ` is :math:`\hat{\mathbf e}=(\hat{\mathbf x}+\hat{\mathbf z})/\sqrt2`. The normalization is necessary to keep the total peak amplitude equal to :math:`E_0`.
3. Multiply the fixed direction by a harmonic scalar:

   .. math::

      \mathbf E(y,t)=\frac{E_0}{\sqrt2}
      (\hat{\mathbf x}+\hat{\mathbf z})\cos[\omega(y/v-t)].

""",
        r"A linear state with equal in-phase :math:`x,z` components and total amplitude :math:`E_0`.",
        r":math:`\mathbf E\cdot\hat{\mathbf y}=0` and the polarization direction does not change with time.",
    ),
    "5.49": (
        r"""
1. The incident field lies along :math:`z`, perpendicular to the plate's fast :math:`y` axis. It therefore excites only the slow eigenpolarization.
2. In the :math:`(y,z)` basis, the incident Jones vector is proportional to :math:`(0,1)`. A quarter-wave plate multiplies the two components by different phase factors, but a zero component remains zero.
3. After removing the common phase or redefining the time origin, the emerging field is :math:`\mathbf E(x,t)=E_0\hat{\mathbf z}\cos(kx-\omega t)`. No orthogonal component is created.
""",
        r"The light remains linearly polarized along :math:`z`, with unchanged amplitude for an ideal lossless plate.",
        r"A quarter-wave plate makes circular light only when both eigenaxes receive equal nonzero amplitudes.",
    ),
    "5.50": (
        r"""
1. Propagation is along :math:`y`; a vibration plane equal to :math:`xy` therefore requires the electric field to point along :math:`x`.
2. Use phase :math:`ky-\omega t` for propagation toward :math:`+y`. The specified zero field at the origin rules out a zero-phase cosine but permits a sine.
3. One convenient expression is :math:`\mathbf E(y,t)=E_0\hat{\mathbf x}\sin(ky-\omega t)`. Its value at :math:`y=t=0` is zero and its maximum magnitude is :math:`E_0`.
""",
        r":math:`\mathbf E=E_0\hat{\mathbf x}\sin(ky-\omega t)`.",
        r"Changing the overall sign gives another valid initial-phase choice with the same polarization and speed.",
    ),
    "5.51": (
        r"""
1. Factor the common oscillation: :math:`\mathbf E=-E_0(\sqrt3\hat{\mathbf x}+\hat{\mathbf z})\cos(ky+\omega t)`.
2. The coefficient vector is constant, so the polarization is linear. Its magnitude is :math:`E_0\sqrt{3+1}=2E_0` and its component ratio is :math:`|E_x/E_z|=\sqrt3`.
3. The polarization line therefore makes :math:`\arctan\sqrt3=60^\circ` with the :math:`z` direction in the transverse plane, hence with the :math:`yz` vibration plane. Constant phase gives :math:`dy/dt=-\omega/k`, so propagation is toward :math:`-y`.
""",
        r"A linear wave of amplitude :math:`2E_0`, propagating toward :math:`-y`, with vibration plane tilted :math:`60^\circ` from :math:`yz`.",
        r"The common minus sign is a phase shift of :math:`\pi`, not a different polarization axis.",
    ),
    "5.52": (
        r"""
1. For propagation along :math:`x`, the transverse reference direction in the :math:`xy` plane is :math:`y`.
2. Tilt toward :math:`z` by :math:`17.5^\circ`, giving unit vector :math:`\hat{\mathbf e}=\hat{\mathbf y}\cos17.5^\circ+\hat{\mathbf z}\sin17.5^\circ`.
3. Thus :math:`\mathbf E(x,t)=E_0(0.953717\hat{\mathbf y}+0.300706\hat{\mathbf z})\cos(kx-\omega t)`; the two components have the same phase.
""",
        r"Use the normalized direction :math:`0.9537\hat{\mathbf y}+0.3007\hat{\mathbf z}`.",
        r":math:`0.953717^2+0.300706^2\approx1`, so :math:`E_0` is the total, not component, amplitude.",
    ),
    "5.53": (
        r"""
1. Represent the common left-circular waveform by a unit rotating vector :math:`\mathbf u_L(\psi)=(\cos\psi,-\sin\psi)` in the transverse plane.
2. The two fields are :math:`2E_0\mathbf u_L` and :math:`E_0\mathbf u_L`. Equal phase and handedness mean their vectors are parallel at every instant.
3. Add fields before squaring: :math:`\mathbf E=3E_0\mathbf u_L`. The irradiance is nine times that of the :math:`E_0` wave alone, not five times, because the coherent cross term contributes.
""",
        r"Left-circular light of amplitude :math:`3E_0`.",
        r"For a nonzero relative phase, the circular handedness survives but the resultant amplitude becomes :math:`E_0\sqrt{5+4\cos\delta}`.",
    ),
    "5.54": (
        r"""
1. A rotating linear analyzer alone transmits half the irradiance of either circular handedness; it cannot distinguish them.
2. First insert a calibrated quarter-wave plate. In a fixed propagation and fast-axis convention, opposite circular states become orthogonal linear states.
3. Align a linear analyzer to the output direction known to correspond to right-circular input. Right-circular light is transmitted and left-circular light is extinguished; rotate the analyzer by :math:`90^\circ` to interchange the outcomes. Calibration avoids ambiguity between competing handedness naming conventions.
""",
        r"Use a quarter-wave plate followed by a linear analyzer, with known fast-axis orientation and viewing direction.",
        r"Reversing propagation or viewing direction can reverse a verbal right/left label; the measured orthogonal analyzer outputs remain unambiguous.",
    ),
    "5.55": (
        r"""
1. Use :math:`\psi=kz-\omega t`. In the source convention, right-circular light has transverse field :math:`E_0(\cos\phi,\sin\phi)` with :math:`\phi=\psi+\phi_0`.
2. At the origin the direction angle is :math:`\phi_0`; choose :math:`\phi_0=-\pi/4` to meet the requested :math:`-45^\circ` initial orientation.
3. The field is

   .. math::

      \mathbf E=E_0[\hat{\mathbf x}\cos(\psi-\pi/4)
      +\hat{\mathbf y}\sin(\psi-\pi/4)].

   At fixed :math:`z`, the angle decreases as time increases, explicitly fixing the rotation convention.
""",
        r"The above circular field starts at :math:`E_0(\hat{\mathbf x}-\hat{\mathbf y})/\sqrt2`.",
        r":math:`E_x^2+E_y^2=E_0^2` at every time, not merely on average.",
    ),
    "5.56": (
        r"""
1. The initial vector :math:`E_0(\hat{\mathbf x}+\sqrt3\hat{\mathbf y})/2` has unit direction :math:`(\cos\pi/3,\sin\pi/3)`.
2. For the same right-circular convention as Problem 5.55, set :math:`\phi=kz-\omega t+\pi/3` in both components.
3. Hence :math:`\mathbf E=E_0[\hat{\mathbf x}\cos\phi+\hat{\mathbf y}\sin\phi]`. Substituting the origin gives the requested vector, while :math:`|\mathbf E|=E_0` proves circularity. The mismatched phase signs in the printed endpoint would not give constant magnitude.
""",
        r"Use a common phase :math:`kz-\omega t+\pi/3` inside the cosine and sine.",
        r"Checking only the initial vector is insufficient: an incorrect elliptic waveform can pass through the same initial point.",
    ),
    "5.57": (
        r"""
1. Left-circular light in the source convention is :math:`E_0(\cos\phi,-\sin\phi)` with :math:`\phi=kz-\omega t+\phi_0`.
2. Its geometric field angle at the origin is :math:`-\phi_0`. To start at :math:`+30^\circ`, choose :math:`\phi_0=-\pi/6`.
3. The required field is :math:`\mathbf E=E_0[\hat{\mathbf x}\cos(kz-\omega t-\pi/6)-\hat{\mathbf y}\sin(kz-\omega t-\pi/6)]`. At fixed position its angle increases with time, opposite to Problem 5.55.
""",
        r"The initial field is :math:`E_0(\sqrt3\hat{\mathbf x}+\hat{\mathbf y})/2`.",
        r"The printed task specifies :math:`30^\circ`; some OCR copies misread this as :math:`80^\circ`.",
    ),
    "5.58": (
        r"""
1. Work in the right-handed transverse :math:`(y,z)` plane for propagation along :math:`+x`, with :math:`\psi=kx-\omega t`.
2. Choose equal component amplitudes and relative phase :math:`-\pi/4`: :math:`E_y=E_0\cos\psi`, :math:`E_z=E_0\cos(\psi-\pi/4)`.
3. In coordinates :math:`U=(E_y+E_z)/\sqrt2`, :math:`V=(E_y-E_z)/\sqrt2`, the squared semiaxes are :math:`E_0^2(1+1/\sqrt2)` and :math:`E_0^2(1-1/\sqrt2)`. The longer axis is :math:`y=z`, at :math:`45^\circ`; the negative phase offset gives the source's right-handed rotation.
""",
        r":math:`\mathbf E=E_0\hat{\mathbf y}\cos\psi+E_0\hat{\mathbf z}\cos(\psi-\pi/4)` is one valid tilted ellipse.",
        r"Equal Cartesian amplitudes do not imply a circle unless the relative phase is :math:`\pm\pi/2`.",
    ),
    "5.59": (
        r"""
1. Set :math:`\psi=kz-\omega t`, :math:`E_x=E_0\cos\psi`, and :math:`E_y=E_0\cos(\psi+3\pi/4)`.
2. The equal-amplitude ellipse has axes along :math:`x=y` and :math:`x=-y`. Since :math:`\cos(3\pi/4)<0`, the larger squared semiaxis is :math:`E_0^2[1-\cos(3\pi/4)]`, along :math:`x=-y`.
3. Thus the major-axis orientation is :math:`135^\circ` modulo :math:`180^\circ`. At fixed position the positive relative cosine phase produces the left-handed sense used in this chapter.
""",
        r":math:`\mathbf E=E_0[\hat{\mathbf x}\cos\psi+\hat{\mathbf y}\cos(\psi+3\pi/4)]`.",
        r"The major/minor axis ratio is :math:`\sqrt{(1+1/\sqrt2)/(1-1/\sqrt2)}=1+\sqrt2`.",
    ),
    "5.60": (
        r"""
1. The given phase is :math:`q=\omega(t-z/v)=-\psi`, not :math:`\psi=kz-\omega t`. Rewrite :math:`E_x=E_0\cos\psi` and :math:`E_y=E_0\cos(\psi+5\pi/4)=E_0\cos(\psi-3\pi/4)`.
2. The amplitudes are equal and the phase difference is neither zero nor a multiple of :math:`\pi/2`, so the state is elliptical. Because :math:`\cos(-3\pi/4)=-1/\sqrt2`, the major axis is along :math:`x=-y`.
3. The negative sine of the relative phase gives the same rotation sense as the right-handed state of Problem 5.58. The major axis is at :math:`135^\circ` and its axial ratio is :math:`1+\sqrt2`.
""",
        r"A right-handed ellipse, major axis at :math:`135^\circ`, propagating toward :math:`+z`.",
        r"Reversing the sign of the common time phase without changing the relative-phase interpretation reverses an inferred handedness incorrectly.",
    ),
    "5.61": (
        r"""
1. To put the principal axes along :math:`x,y`, choose components in quadrature rather than an arbitrary phase difference.
2. Give the :math:`x` component twice the amplitude of the :math:`y` component. With :math:`\psi=kz-\omega t`, take :math:`\mathbf E=2E_0\hat{\mathbf x}\cos\psi+E_0\hat{\mathbf y}\sin\psi`.
3. Eliminating the phase yields :math:`E_x^2/(2E_0)^2+E_y^2/E_0^2=1`. The major axis is :math:`x`, the axial ratio is 2, and the field rotates in the right-handed convention of Problem 5.55.
""",
        r":math:`\mathbf E=2E_0\hat{\mathbf x}\cos(kz-\omega t)+E_0\hat{\mathbf y}\sin(kz-\omega t)`.",
        r"The semiaxis ratio is 2, while the corresponding squared-amplitude ratio is 4.",
    ),
    "5.62": (
        r"""
1. Let :math:`\psi=kz-\omega t` and suppose first that :math:`E_{0x}\ge E_{0y}\ge0`. Add and subtract :math:`E_{0y}\hat{\mathbf x}\sin\psi`.
2. The given ellipse separates exactly into

   .. math::

      \mathbf E=(E_{0x}-E_{0y})\hat{\mathbf x}\sin\psi
      +E_{0y}(\hat{\mathbf x}\sin\psi+\hat{\mathbf y}\cos\psi).

3. The first term has a fixed direction and is linear. The second has equal quadrature components and constant magnitude, so it is circular. If :math:`E_{0y}>E_{0x}`, instead remove a circular field of amplitude :math:`E_{0x}` and leave the excess along :math:`y`.
""",
        r"The ellipse is a coherent sum of a circular component of the smaller semiaxis amplitude and a linear residual.",
        r"These fields are coherent; their irradiances cannot in general be added as though they were an incoherent statistical mixture.",
    ),
    "5.63": (
        r"""
1. For a single deterministic plane wave at exactly one frequency, write :math:`\mathbf E=\operatorname{Re}[(A_x\hat{\mathbf x}+A_y\hat{\mathbf y})e^{i(kz-\omega t)}]` with constant complex amplitudes.
2. The amplitude ratio and relative phase are fixed. Eliminating time gives a fixed ellipse, including the linear and circular limiting cases: the wave has a definite polarization.
3. In the source's wave-train model, a randomly changing polarization requires time-dependent amplitudes or phases, hence a finite spectral width. The claim applies to a single coherent mode; an ensemble or unresolved superposition of modes needs a statistical polarization description and should not be inferred from a narrow measured spectrum alone.
""",
        r"An exactly monochromatic, single deterministic plane wave is fully polarized.",
        r"A stationary narrowband beam can nevertheless be partially or wholly unpolarized when incoherent modes are averaged.",
    ),
    "5.64": (
        r"""
1. Rotate a linear analyzer to identify the principal-axis direction :math:`\alpha` of the polarized contribution. Write its Jones vector in these axes as :math:`(a,ib)`; add an incoherent natural background of irradiance :math:`I_u`.
2. Align a quarter-wave plate to these axes. If the contribution is linear, :math:`b=0`, so the plate changes no relative phase between nonzero components and the analyzer extrema stay on the same axes.
3. If it is genuinely elliptical, :math:`a,b\ne0`; the plate converts the quadrature components to an in-phase or antiphase pair :math:`(a,\pm b)`. The polarized output is now linear at :math:`\arctan(\pm b/a)`, and the analyzer's extrema shift. The natural component stays natural.
""",
        r"Compare analyzer scans before and after an axis-aligned quarter-wave plate; a shifted principal direction reveals an elliptical contribution.",
        r"A circular contribution has no initial preferred analyzer direction; the quarter-wave plate still turns it into a detectable linear contribution.",
    ),
    "5.65": (
        r"""
1. Let the incident beam contain circular irradiance :math:`I_c` and unpolarized irradiance :math:`I_u`. A quarter-wave plate converts the circular part into linear light but leaves the unpolarized part unchanged.
2. A following analyzer at angle :math:`\theta` to that linear direction transmits :math:`I(\theta)=I_c\cos^2\theta+I_u/2`.
3. Thus :math:`I_{\max}=I_c+I_u/2` and :math:`I_{\min}=I_u/2`. A zero minimum means purely circular input; equal maximum and minimum mean natural input; a positive minimum smaller than the maximum means a mixture.
""",
        r"After the quarter-wave plate, measure :math:`I_c=I_{\max}-I_{\min}` and :math:`I_u=2I_{\min}`.",
        r"Without the retarder all three possibilities give angle-independent transmission through a linear analyzer.",
    ),
    "5.66": (
        r"""
1. The two stated analyzer orientations, :math:`30^\circ` right and :math:`60^\circ` left of vertical, differ by :math:`90^\circ`. They therefore give the maximum and minimum: 43 and :math:`22\,\mathrm{W\,m^{-2}}`.
2. For a linear-plus-natural mixture, :math:`I_p=I_{\max}-I_{\min}=21` and :math:`I_u=2I_{\min}=44\,\mathrm{W\,m^{-2}}`.
3. The degree of polarization is

   .. math::

      V=\frac{I_p}{I_p+I_u}
      =\frac{43-22}{43+22}=\frac{21}{65}=0.32308.

""",
        r"The beam is :math:`32.3\%` polarized.",
        r"The incident total is :math:`65\,\mathrm{W\,m^{-2}}`, not the maximum analyzer reading of 43.",
    ),
    "5.67": (
        r"""
1. An ideal linear polarizer transmits half the unpolarized irradiance, so :math:`I_o=I_i/2`. Its transmission unit vector is :math:`(\hat{\mathbf y}+\hat{\mathbf z})/\sqrt2`.
2. For a harmonic representative in vacuum, :math:`I_o=\epsilon_0cE_0^2/2`; hence the total peak field is :math:`E_0=\sqrt{I_i/(\epsilon_0c)}`.
3. A suitable linearly polarized wave is

   .. math::

      \mathbf E(x,t)=\sqrt{\frac{I_i}{2\epsilon_0c}}
      (\hat{\mathbf y}+\hat{\mathbf z})
      \sin\left(\frac{2\pi x}{\lambda}-\omega t\right).

   Real filtered natural light has a fluctuating scalar amplitude/phase; this harmonic expression specifies the direction and intensity normalization, not a new temporal coherence imposed by the polarizer.
""",
        r"The output is linear at :math:`45^\circ` in the :math:`yz` plane and has irradiance :math:`I_i/2`.",
        r"Sum both squared component amplitudes before using :math:`I=\epsilon_0cE_0^2/2`.",
    ),
    "5.68": (
        r"""
1. Let :math:`I_1` be the irradiance immediately after the first polarizer. It is the same in both measurements.
2. Malus's law gives :math:`I(30^\circ)=I_1\cos^230^\circ=3I_1/4` and :math:`I(60^\circ)=I_1\cos^260^\circ=I_1/4`.
3. Divide the two expressions; the first polarizer's transmission and the original source irradiance cancel.
""",
        r":math:`I(30^\circ)/I(60^\circ)=3`.",
        r"Use the angle between the two transmission axes, not an angle relative to the incident propagation direction.",
    ),
    "5.69": (
        r"""
1. Assume the incident beam is unpolarized. The first polarizer at :math:`0^\circ` leaves :math:`I_i/2`.
2. The next axis differs by :math:`36^\circ`; the final axis differs from the second by :math:`76^\circ-36^\circ=40^\circ`, not :math:`76^\circ`.
3. Multiply the successive transmissions: :math:`I_o=(I_i/2)\cos^236^\circ\cos^240^\circ=0.19204I_i`.
""",
        r":math:`I_o\approx0.1920I_i` for natural input.",
        r"Each polarizer resets the output polarization direction, so each projection is relative to its immediate predecessor.",
    ),
    "5.70": (
        r"""
1. The first ideal polarizer reduces natural input to :math:`I_i/2` and creates a linear state.
2. Each of the remaining :math:`N-1` polarizers is at :math:`45^\circ` to the preceding one and contributes :math:`\cos^245^\circ=1/2`.
3. Therefore :math:`I_o=(I_i/2)(1/2)^{N-1}=I_i2^{-N}`. For ten polarizers, :math:`2^{-10}=1/1024=9.765625\times10^{-4}`.
""",
        r":math:`I_o=2^{-N}I_i`; for ten filters, :math:`I_o=9.77\times10^{-4}I_i`.",
        r"There are nine inter-axis projections for ten filters, plus the initial factor of one half.",
    ),
    "5.71": (
        r"""
1. The four axes may be written :math:`0^\circ,30^\circ,60^\circ,90^\circ`. Natural input loses half its irradiance at the first filter.
2. Three successive projections give :math:`I_o=(I_i/2)(\cos^230^\circ)^3=(I_i/2)(3/4)^3=27I_i/128`.
3. Removing the middle two leaves the :math:`0^\circ` and :math:`90^\circ` filters directly crossed, giving :math:`I_o=(I_i/2)\cos^290^\circ=0`.
""",
        r"All four transmit :math:`0.21094I_i`; the two end filters alone transmit zero.",
        r"Additional intermediate polarizers can increase transmission through crossed endpoints by changing the state between projections.",
    ),
    "5.72": (
        r"""
1. Assign orientations :math:`\alpha_1=0^\circ`, :math:`\alpha_2=+45^\circ`, and :math:`\alpha_3=-45^\circ`.
2. In the order 1, 2, 3, the last two axes differ by :math:`90^\circ`, so their Malus factor is zero regardless of the initial irradiance.
3. In the comparison order 2, 1, 3, each adjacent angle is :math:`45^\circ`; unpolarized incident light would transmit :math:`(I_i/2)(1/2)(1/2)=I_i/8`. Polarizer order therefore matters.
""",
        r"No light emerges in the stated 1–2–3 order.",
        r"Polarization projections do not commute; the same set of filters can transmit a different irradiance when reordered.",
    ),
    "5.73": (
        r"""
1. Complete reflected linear polarization at a lossless dielectric interface identifies the Brewster angle, where the p reflection coefficient vanishes.
2. Brewster's law is :math:`\tan\theta_B=n_g/n_{\rm air}`. Convert :math:`58^\circ01'=58+1/60=58.016667^\circ`.
3. With :math:`n_{\rm air}\approx1`, :math:`n_g=\tan58.016667^\circ\approx1.60137`. This is the index at the specified mercury wavelength, not a wavelength-independent material constant.
""",
        r":math:`n_g\approx1.6014` at :math:`546.072\,\mathrm{nm}`.",
        r"At Brewster incidence, the reflected field is s-polarized, parallel to the interface and perpendicular to the incidence plane.",
    ),
    "5.74": (
        r"""
1. For air to crown glass, :math:`\theta_B=\arctan(1.5170)=56.6074^\circ`.
2. At Brewster incidence, Snell's law and :math:`\tan\theta_B=n_t/n_i` imply :math:`\theta_t=90^\circ-\theta_B=33.3926^\circ`.
3. Converting fractional degrees to arcminutes gives approximately :math:`56^\circ36'` for incidence and :math:`33^\circ24'` inside the plate.
""",
        r":math:`\theta_B\approx56.61^\circ`, :math:`\theta_t\approx33.39^\circ`.",
        r"The transmitted and reflected ray directions are perpendicular at Brewster incidence.",
    ),
    "5.75": (
        r"""
1. The first Brewster reflection selects the component perpendicular to its incidence plane, leaving a linearly polarized beam.
2. Rotating the second incidence plane around this beam by :math:`\theta` rotates that plate's s direction by the same angle. Project the incident field onto it: :math:`E_{s2}=E_1\cos\theta`.
3. The p reflection is zero, so only :math:`E_{s2}` contributes. Squaring and including the fixed s reflectance gives :math:`I_2(\theta)=R_{s2}I_1\cos^2\theta=I_2(0)\cos^2\theta`.
""",
        r"The second reflected irradiance follows :math:`I_2(\theta)=I_2(0)\cos^2\theta`.",
        r"The Brewster incidence angle must stay fixed during the rotation; otherwise the Fresnel factor also changes.",
    ),
    "5.76": (
        r"""
1. Resolve natural incident light into equal incoherent s and p irradiances :math:`I_i/2`. At Brewster incidence, :math:`R_p=0` while :math:`R_s=0.15`.
2. The reflected components are :math:`0.075I_i` and zero, so :math:`V_r=1`. For a lossless interface the power transmittances are :math:`T_s=0.85` and :math:`T_p=1`.
3. The common geometric conversion from normal power flux to transmitted beam irradiance cancels in the ratio:

   .. math::

      V_t=\frac{T_p-T_s}{T_p+T_s}
      =\frac{1-0.85}{1+0.85}=0.081081.

""",
        r"Reflected light: :math:`100\%` polarized; transmitted light: :math:`8.11\%` polarized, with p predominating.",
        r"Complete polarization of the weak reflected beam does not imply complete polarization of the much stronger transmitted beam.",
    ),
    "5.77": (
        r"""
1. For incidence from water onto flint glass, use the relative index: :math:`\theta_{B,\rm ext}=\arctan(1.673/1.333)\approx51.45^\circ`.
2. For incidence from inside the glass, reverse the index ratio: :math:`\theta_{B,\rm int}=\arctan(1.333/1.673)\approx38.55^\circ`.
3. Since the two ratios are reciprocal and positive, their arctangents sum to :math:`90^\circ`. Rounded to arcminutes the pair is approximately :math:`51^\circ27'` and :math:`38^\circ33'`.
""",
        r"External Brewster angle :math:`51.45^\circ`; internal Brewster angle :math:`38.55^\circ`.",
        r"Using the glass index alone would calculate an air-glass angle and is inappropriate for a plate immersed in water.",
    ),
    "5.78": (
        r"""
1. Use real fields :math:`E_x=E_0\cos\psi`, :math:`E_y=E_0\sin\psi` for right-circular input, with :math:`\psi=kz-\omega t`.
2. The fast axis is :math:`y`, so relative to that component the slow :math:`x` component acquires an extra propagation phase :math:`\pi/2`. Removing the common phase gives :math:`E_x'=E_0\cos(\psi+\pi/2)=-E_0\sin\psi`, :math:`E_y'=E_0\sin\psi`.
3. Both components now share the same scalar oscillation and have opposite signs. The polarization line is :math:`y=-x`, or :math:`135^\circ` from :math:`x` modulo :math:`180^\circ`.
""",
        r"The output is linear at :math:`135^\circ` to the horizontal.",
        r"The angle refers to an unoriented polarization line: :math:`135^\circ` and :math:`-45^\circ` describe the same state.",
    ),
    "5.79": (
        r"""
1. Left-circular input has :math:`E_x=E_0\cos\psi`, :math:`E_y=-E_0\sin\psi` in the convention used here.
2. With a vertical fast axis, add :math:`\pi/2` to the slow x-component phase: :math:`E_x'=-E_0\sin\psi`, while :math:`E_y'=-E_0\sin\psi` after dropping a common phase.
3. The two components are now equal and in phase. Their sum points along :math:`\hat{\mathbf x}+\hat{\mathbf y}`, a fixed :math:`45^\circ` polarization line.
""",
        r"The output is linear at :math:`45^\circ` to the horizontal.",
        r"Opposite circular inputs become orthogonal linear outputs through the same ideal quarter-wave plate.",
    ),
    "5.80": (
        r"""
1. The cleavage orientation used in the source places the optic axis at :math:`\beta=45^\circ24'` to the face; thus its angle to the normally incident wave vector is :math:`\theta=90^\circ-\beta=44^\circ36'`. This orientation is crystallographic input, not something determined by the two optical indices alone.
2. In axes parallel and perpendicular to the optic axis, the extraordinary wavelet has semiaxes :math:`ct/n_o` and :math:`ct/n_e`. Its ray goes from the wavelet centre to the point whose tangent is the wavefront. The tangent-normal relation gives :math:`\tan\theta_r=(n_o^2/n_e^2)\tan\theta`.
3. Therefore the walk-off angle is

   .. math::

      \alpha=\theta_r-\theta
      =\arctan\left(\frac{1.658^2}{1.486^2}\tan44.6^\circ\right)-44.6^\circ
      \approx6.25^\circ.

   Rounded source indices yield about :math:`6^\circ15'`, close to the source's :math:`6^\circ14'`. The drawing exaggerates this small separation.
""",
        r"For the stated calcite cut, :math:`\beta=45^\circ24'` and extraordinary ray walk-off is about :math:`6.2^\circ`.",
        r"The wave normal remains normal to the entrance face; the extraordinary energy ray need not be parallel to that normal.",
    ),
    "5.81": (
        r"""
1. Reversing circular handedness requires changing the relative phase by :math:`\pi`, so use a half-wave rather than a quarter-wave retarder.
2. Its retardance is :math:`\delta=2\pi\Delta n\,d/\lambda_0`, with :math:`\Delta n=1.551-1.542=0.009`. The thinnest positive solution to :math:`\delta=\pi` is

   .. math::

      d=\frac{656\,\mathrm{nm}}{2(0.009)}
      =36444\,\mathrm{nm}=36.44\,\mathrm{\mu m}
      =3.644\times10^{-3}\,\mathrm{cm}.

3. A circular field has equal amplitudes on every pair of orthogonal transverse axes, so any transverse fast-axis azimuth works; it changes only the overall phase of the opposite circular output.
""",
        r"Use a :math:`36.4\,\mathrm{\mu m}` half-wave quartz plate; its transverse azimuth is arbitrary.",
        r"The optic axis must be oriented to produce the quoted birefringence; propagation along the optic axis would give no retardance.",
    ),
    "5.82": (
        r"""
1. The first polarizer converts natural red light to linear light of irradiance :math:`I_i/2`.
2. At :math:`45^\circ` to the retarder axes, the field has equal components. A half-wave plate reverses the sign of one component relative to the other, rotating the linear polarization by :math:`90^\circ` relative to its original direction.
3. The output is now parallel to the initially crossed analyzer, so an ideal analyzer transmits it fully. The emerging irradiance is :math:`I_i/2`, polarized along the analyzer axis.
""",
        r"Red light passes with ideal total transmission :math:`1/2` and emerges linearly polarized along the analyzer.",
        r"The half-wave plate rotates the polarization, not the physical beam direction.",
    ),
    "5.83": (
        r"""
1. Keep thickness and birefringence fixed. Retardance scales as :math:`1/\lambda`, so halving wavelength from 780 to 390 nm doubles :math:`\delta` from :math:`\pi` to :math:`2\pi`.
2. A :math:`2\pi` relative phase is equivalent to zero. The violet polarization after the plate is therefore the same as after the first polarizer.
3. The crossed analyzer blocks that unchanged state: :math:`I_o=0` in the ideal nondispersive model.
""",
        r"The plate is full-wave at :math:`390\,\mathrm{nm}`; no violet light passes the crossed analyzer.",
        r"Dispersion and imperfect retardance produce leakage in a real device; the calculation explicitly neglects them.",
    ),
    "5.84": (
        r"""
1. Without the final analyzer, equal-amplitude components leaving the :math:`45^\circ` retarder are circular whenever :math:`\delta=(2m+1)\pi/2`.
2. This plate has :math:`\delta(\lambda)=\pi(780\,\mathrm{nm})/\lambda`. Equating the two forms gives :math:`\lambda=1560/(2m+1)\,\mathrm{nm}`.
3. The first values are 1560, 520, 312, and 223 nm. Of these, only :math:`520\,\mathrm{nm}` is visible, giving yellow-green circular output in the source's nondispersive approximation.
""",
        r"The visible circular-output wavelength is :math:`520\,\mathrm{nm}`.",
        r"At 780 nm the output is linear; at 520 nm the plate is three-quarter-wave, which still supplies quadrature modulo :math:`2\pi`.",
    ),
    "5.85": (
        r"""
1. Parallel polarizers would normally transmit the state produced by the first one. Extinction requires rotating that linear state through :math:`90^\circ` before it reaches the second.
2. Use a half-wave plate with fast axis :math:`45^\circ` to the common transmission axis. With calcite indices :math:`n_o=1.658`, :math:`n_e=1.486`, the magnitude of birefringence is :math:`0.172`.
3. The minimum thickness is :math:`d=589.3/[2(0.172)]\,\mathrm{nm}=1713.1\,\mathrm{nm}=1.713\,\mathrm{\mu m}`. The rotated state is perpendicular to the final polarizer, so the ideal transmission is zero.
""",
        r"A half-wave calcite plate :math:`1.713\,\mathrm{\mu m}` thick, with an eigenaxis at :math:`45^\circ`, gives extinction.",
        r"The negative sign of calcite birefringence changes which axis is fast, but not the required half-wave thickness magnitude.",
    ),
    "5.86": (
        r"""
1. The prism apex in the source figure is :math:`A=60^\circ`, and its optic axis is perpendicular to the propagation section, so the two principal indices can be treated separately.
2. At minimum deviation each ray has :math:`r_1=r_2=A/2`, and :math:`i=e=(A+\delta_{\min})/2`. Snell's law in air therefore gives :math:`n=\sin[(A+\delta_{\min})/2]/\sin(A/2)`.
3. For the ordinary deviation :math:`46^\circ`, :math:`n_o=\sin53^\circ/\sin30^\circ=1.59727`. For the extraordinary deviation :math:`40^\circ`, :math:`n_e=\sin50^\circ/\sin30^\circ=1.53209`.
""",
        r":math:`n_o\approx1.597`, :math:`n_e\approx1.532`.",
        r":math:`n_e<n_o` confirms a negative uniaxial crystal; swapping the ordinary and extraordinary labels would contradict the specified material class.",
    ),
}
