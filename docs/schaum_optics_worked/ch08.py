SOLUTIONS = {
    "8.22": (
        r"""
1. Set the fundamental spatial frequency :math:`k_0=2\pi/L`. Expand each phase-shifted term using :math:`\cos(mk_0x+\epsilon_m)=\cos\epsilon_m\cos(mk_0x)-\sin\epsilon_m\sin(mk_0x)`.
2. Identify the sine-cosine coefficients as :math:`a_m=C_m\cos\epsilon_m`, :math:`b_m=-C_m\sin\epsilon_m`, and the constant as :math:`C_0=a_0/2`.
3. Conversely, take :math:`C_m=\sqrt{a_m^2+b_m^2}` and :math:`\epsilon_m=\operatorname{atan2}(-b_m,a_m)`. The two-argument angle keeps the correct quadrant; when :math:`C_m=0`, that harmonic's phase is arbitrary.
""",
        r"The amplitude-phase and sine-cosine forms are equivalent term by term.",
        r"The minus sign in :math:`b_m=-C_m\sin\epsilon_m` comes from the plus sign inside :math:`\cos(mk_0x+\epsilon_m)`.",
    ),
    "8.23": (
        r"""
1. Suppose :math:`f(x+L/2)=-f(x)`. Split a complex Fourier coefficient into two half-period integrals:

   .. math::

      c_m=\frac1L\left[\int_0^{L/2}f(x)e^{-imk_0x}\,dx
      +\int_{L/2}^{L}f(x)e^{-imk_0x}\,dx\right].

2. In the second integral substitute :math:`x=u+L/2`. Its integrand becomes :math:`-f(u)e^{-imk_0u}e^{-im\pi}=-(-1)^mf(u)e^{-imk_0u}`.
3. Thus :math:`c_m=[1-(-1)^m]L^{-1}\int_0^{L/2}f(u)e^{-imk_0u}\,du`. Every even coefficient, including DC, vanishes; only odd harmonics can remain.
""",
        r"Half-wave antisymmetry removes the DC term and all even harmonics.",
        r"Odd harmonics can contain both sine and cosine terms unless an additional odd/even spatial parity is specified.",
    ),
    "8.24": (
        r"""
1. Suppose the function repeats after :math:`L/2`, even though its Fourier series is expressed on an interval of length :math:`L`.
2. Split the coefficient integral into two halves as in Problem 8.23. Now :math:`f(u+L/2)=f(u)`, so the multiplier is :math:`1+(-1)^m`.
3. This vanishes for every odd :math:`m`, leaving only even harmonics relative to :math:`k_0=2\pi/L`, plus possible DC. Relative to the true shorter period, these are simply ordinary integer harmonics.
""",
        r"Only even harmonics relative to period :math:`L` remain when the function also has period :math:`L/2`.",
        r"Harmonic parity depends on the chosen reference period; it is not an intrinsic label independent of that choice.",
    ),
    "8.25": (
        r"""
1. Read one period of the source graph as :math:`f(x)=-\pi` for :math:`-\pi<x<0` and :math:`f(x)=x` for :math:`0<x<\pi`, extended with period :math:`2\pi`. Its mean is :math:`[-\pi^2+\pi^2/2]/(2\pi)=-\pi/4`.
2. Split the coefficient integrals at zero. The cosine integral gives :math:`a_m=[(-1)^m-1]/(\pi m^2)`. For sine, the constant segment contributes :math:`[1-(-1)^m]/m`, while integration by parts of :math:`x\sin mx` contributes :math:`-(-1)^m/m`.
3. Therefore

   .. math::

      f(x)=-\frac\pi4-\frac2\pi\sum_{j=0}^{\infty}
      \frac{\cos[(2j+1)x]}{(2j+1)^2}
      +\sum_{m=1}^{\infty}\frac{1-2(-1)^m}{m}\sin(mx).

   The first sine terms are :math:`3\sin x-\tfrac12\sin2x+\sin3x-\tfrac14\sin4x`.
""",
        r"The series contains odd cosines and both odd and even sines; the waveform is neither even nor odd.",
        r"At :math:`x=0` the series converges to the jump midpoint :math:`-\pi/2`, not to either one-sided value.",
    ),
    "8.26": (
        r"""
1. The triangular graph is :math:`f(y)=|y|` on :math:`[-\pi,\pi]`, extended periodically. It is even, so :math:`b_m=0`.
2. The mean is :math:`a_0/2=(1/\pi)\int_0^\pi y\,dy=\pi/2`. Integration by parts gives :math:`a_m=(2/\pi)\int_0^\pi y\cos(my)\,dy=2[(-1)^m-1]/(\pi m^2)`.
3. Even coefficients vanish; odd coefficients are :math:`-4/(\pi m^2)`. Hence :math:`f(y)=\pi/2-(4/\pi)\sum_{j=0}^{\infty}\cos[(2j+1)y]/(2j+1)^2`.
""",
        r":math:`f(y)=\pi/2-(4/\pi)(\cos y+\cos3y/9+\cos5y/25+\cdots)`.",
        r"At :math:`y=0`, :math:`\sum_{j\ge0}(2j+1)^{-2}=\pi^2/8` makes the reconstructed value zero.",
    ),
    "8.27": (
        r"""
1. The generalized triangle has period :math:`L`, minimum zero at :math:`y=0`, and maximum :math:`H` at :math:`y=\pm L/2`. On the centred period it is :math:`f(y)=2H|y|/L`.
2. Scale the previous solution's coordinate by :math:`u=2\pi y/L` and amplitude by :math:`H/\pi`, so :math:`f(y)=(H/\pi)|u|` on that period.
3. The scaled series is

   .. math::

      f(y)=\frac H2-\frac{4H}{\pi^2}
      \sum_{j=0}^{\infty}
      \frac{\cos[2\pi(2j+1)y/L]}{(2j+1)^2}.

""",
        r"The mean is :math:`H/2`; odd cosine amplitudes scale as :math:`-4H/[\pi^2(2j+1)^2]`.",
        r"Setting :math:`H=\pi` and :math:`L=2\pi` recovers Problem 8.26 exactly.",
    ),
    "8.28": (
        r"""
1. The shifted graph has a peak :math:`\pi/2` at zero and troughs :math:`-\pi/2` at :math:`\pm\pi`. On the centred period it is :math:`g(y)=\pi/2-|y|`.
2. Subtract the entire series from Problem 8.26 from :math:`\pi/2`. The constant term cancels and every nonzero coefficient changes sign.
3. Thus :math:`g(y)=(4/\pi)\sum_{j=0}^{\infty}\cos[(2j+1)y]/(2j+1)^2`. Equivalently, a half-period shift of the zero-mean triangle reverses the signs of all its odd harmonics.
""",
        r":math:`g(y)=(4/\pi)(\cos y+\cos3y/9+\cos5y/25+\cdots)`.",
        r"The absence of a DC term matches the equal positive and negative areas of this centred triangular waveform.",
    ),
    "8.29": (
        r"""
1. A full-wave rectified sinusoid with a 1 s period is :math:`f(t)=E_0|\sin\pi t|`, whose unrectified parent has a 2 s period.
2. Over :math:`0<t<1`, :math:`f=E_0\sin\pi t`. The mean is :math:`\int_0^1f\,dt=2E_0/\pi`. Product-to-sum integration gives :math:`a_m=2E_0\int_0^1\sin\pi t\cos2\pi mt\,dt=-4E_0/[\pi(4m^2-1)]`; sine coefficients vanish by symmetry.
3. Therefore

   .. math::

      f(t)=\frac{2E_0}\pi-\frac{4E_0}\pi
      \sum_{m=1}^{\infty}\frac{\cos(2\pi mt)}{4m^2-1}.

""",
        r"The first cosine denominators are :math:`3,15,35,\ldots`, with a 1 Hz fundamental after rectification.",
        r"Using :math:`|\sin2\pi t|` would instead give a 0.5 s rectified period.",
    ),
    "8.30": (
        r"""
1. These notes use :math:`F(k)=\int f(x)e^{-ikx}\,dx`, whereas the source uses the opposite exponential sign in some endpoints. Let the pulse be :math:`E_0` on :math:`[-L,L]` and zero elsewhere.
2. Direct integration gives :math:`F(k)=E_0[e^{-ikx}/(-ik)]_{-L}^{L}=E_0(e^{ikL}-e^{-ikL})/(ik)`.
3. Euler's identity reduces this to :math:`F(k)=2E_0\sin(kL)/k=2E_0L\operatorname{sinc}(kL)`, where :math:`\operatorname{sinc}u=\sin u/u`. At zero frequency use the continuous limit.
""",
        r":math:`F(k)=2E_0L\operatorname{sinc}(kL)`.",
        r":math:`F(0)=2LE_0` equals the pulse area; the even real pulse must have an even real transform under either sign convention.",
    ),
    "8.31": (
        r"""
1. Write the windowed sine as :math:`f(x)=E_0P_L(x)[e^{ik_px}-e^{-ik_px}]/(2i)`, where :math:`P_L=1` for :math:`|x|\le L`.
2. The rectangular-window transform is :math:`W(k)=2L\operatorname{sinc}(kL)`. Modulation shifts it: :math:`\mathcal F\{P_Le^{\pm ik_px}\}=W(k\mp k_p)`.
3. Consequently

   .. math::

      F(k)=\frac{E_0L}{i}
      \left\{\operatorname{sinc}[(k-k_p)L]
      -\operatorname{sinc}[(k+k_p)L]\right\}.

   The source's :math:`+ikx` forward convention reverses this imaginary transform's sign.
""",
        r"The spectrum is the imaginary, antisymmetric difference of two shifted sinc lobes.",
        r"The input is real and odd, so :math:`F(-k)=-F(k)=F(k)^*` and :math:`F(0)=0`.",
    ),
    "8.32": (
        r"""
1. Apply :math:`\sin^2k_px=(1-\cos2k_px)/2` within the same :math:`[-L,L]` window.
2. The constant-window term transforms to :math:`E_0L\operatorname{sinc}(kL)`. The cosine term is the sum of two exponentials, each shifted by :math:`\pm2k_p` and weighted by :math:`-E_0/4` before multiplying the window transform.
3. Thus

   .. math::

      F(k)=E_0L\left\{\operatorname{sinc}(kL)
      -\frac12\operatorname{sinc}[(k-2k_p)L]
      -\frac12\operatorname{sinc}[(k+2k_p)L]\right\}.

""",
        r"A central sinc lobe minus two half-weight sinc lobes centred at :math:`\pm2k_p`.",
        r":math:`F(0)=E_0[L-\sin(2k_pL)/(2k_p)]`, equal to the integral of the windowed sine squared.",
    ),
    "8.33": (
        r"""
1. The plotted function is the two-sided even exponential :math:`f(x)=e^{-a|x|}`, with :math:`a>0`, not a one-sided exponential. Parity removes the sine contribution.
2. Directly, :math:`F(k)=2\int_0^\infty e^{-ax}\cos(kx)\,dx=2\operatorname{Re}[1/(a+ik)]=2a/(a^2+k^2)`.
3. Alternatively, split :math:`f=H(x)e^{-ax}+H(-x)e^{ax}`. The two transforms are :math:`1/(a+ik)` and :math:`1/(a-ik)`; adding them gives the same Lorentzian.
""",
        r":math:`F(k)=2a/(a^2+k^2)`.",
        r":math:`F(0)=2/a` matches the total area, and the result is even and real.",
    ),
    "8.34": (
        r"""
1. Let :math:`f(x)=\sqrt{a/\pi}\,e^{-ax^2}`, :math:`a>0`. In the transform exponent, complete the square: :math:`-ax^2-ikx=-a(x+ik/(2a))^2-k^2/(4a)`.
2. The Gaussian integral contributes :math:`\sqrt{\pi/a}`, cancelling the normalization. Equivalently, integration by parts gives :math:`F'(k)=-kF(k)/(2a)` with :math:`F(0)=1`. Both routes yield :math:`F(k)=e^{-k^2/(4a)}`.
3. A smoothly Gaussian pupil amplitude has a Gaussian Fourier field with no sidelobes in the ideal untruncated model. Gaussian apodization suppresses Airy rings at the cost of throughput and a broader central image; a finite hard truncation can leave residual rings.
""",
        r":math:`\mathcal F\{\sqrt{a/\pi}e^{-ax^2}\}=e^{-k^2/(4a)}`.",
        r"Making the spatial Gaussian narrower by increasing :math:`a` broadens its Fourier transform, as expected from reciprocal width scaling.",
    ),
    "8.35": (
        r"""
1. The step function restricts support to :math:`x\ge0`, so :math:`F(k)=\int_0^\infty xe^{-(a+ik)x}\,dx`, with :math:`a>0` ensuring convergence.
2. Start from :math:`\int_0^\infty e^{-(a+ik)x}\,dx=1/(a+ik)`. Differentiate with respect to :math:`a` and change sign to insert the factor :math:`x`.
3. This gives :math:`F(k)=-\partial_a[1/(a+ik)]=1/(a+ik)^2`. Under a :math:`+ikx` forward-transform convention, it becomes the source's :math:`1/(a-ik)^2`.
""",
        r":math:`F(k)=1/(a+ik)^2` with the negative-exponential convention used here.",
        r":math:`F(0)=1/a^2=\int_0^\infty xe^{-ax}\,dx`, and :math:`F(-k)=F(k)^*`.",
    ),
    "8.36": (
        r"""
1. Apply delta sifting: :math:`\mathcal F\{\delta(x)\}=\int\delta(x)e^{-ikx}\,dx=e^0=1`.
2. The inverse transform of a frequency delta is :math:`(2\pi)^{-1}\int2\pi\delta(k)e^{ikx}\,dk=1`.
3. Therefore :math:`\mathcal F\{1\}=2\pi\delta(k)`. The second relation is a distribution identity, not an ordinary convergent integral of a constant over the whole real line.
""",
        r":math:`\delta(x)\leftrightarrow1` and :math:`1\leftrightarrow2\pi\delta(k)`.",
        r"The factor :math:`2\pi` is fixed by the chosen inverse-transform normalization.",
    ),
    "8.37": (
        r"""
1. Insert the inverse transform of :math:`h`: :math:`h(x)=(2\pi)^{-1}\int H(q)e^{iqx}\,dq` into :math:`\mathcal F\{fh\}=\int f(x)h(x)e^{-ikx}\,dx`.
2. Interchange the integrals when they are absolutely integrable, or interpret the result distributionally where appropriate. The inner integral is :math:`\int f(x)e^{-i(k-q)x}\,dx=F(k-q)`.
3. Hence

   .. math::

      \mathcal F\{f h\}(k)=\frac1{2\pi}\int H(q)F(k-q)\,dq
      =\frac1{2\pi}(F*H)(k).

""",
        r"Multiplication in position corresponds to frequency convolution divided by :math:`2\pi`.",
        r"The dual theorem :math:`\mathcal F\{f*h\}=FH` has no extra factor in this convention.",
    ),
    "8.38": (
        r"""
1. The cosine spectrum is :math:`F(k)=\pi[\delta(k-k_0)+\delta(k+k_0)]`.
2. Self-convolution produces four ordered pairs: the equal-sign pairs land at :math:`\pm2k_0`, while the two opposite-sign pairs coincide at zero. Thus :math:`F*F=\pi^2[\delta(k-2k_0)+2\delta(k)+\delta(k+2k_0)]`.
3. Multiply by :math:`1/(2\pi)` from the product theorem:

   .. math::

      \mathcal F\{\cos^2k_0x\}
      =\pi\delta(k)+\frac\pi2[\delta(k-2k_0)+\delta(k+2k_0)].

""",
        r"Three spectral lines: DC weight :math:`\pi`, and weights :math:`\pi/2` at :math:`\pm2k_0`.",
        r"Directly transforming :math:`\cos^2k_0x=(1+\cos2k_0x)/2` gives the same weights.",
    ),
    "8.39": (
        r"""
1. Begin with :math:`(f*h)(x)=\int_{-\infty}^{\infty}f(\xi)h(x-\xi)\,d\xi`.
2. Substitute :math:`u=x-\xi`, so :math:`d\xi=-du`. The lower and upper integration limits exchange; the Jacobian minus sign restores their usual order.
3. The result is :math:`\int_{-\infty}^{\infty}h(u)f(x-u)\,du=(h*f)(x)`. Thus either function can be the one reflected and translated in the graphical construction.
""",
        r":math:`f*h=h*f` whenever the convolution is well defined.",
        r"Convolution is commutative, whereas correlation generally changes by reversal or conjugation when its arguments are exchanged.",
    ),
    "8.40": (
        r"""
1. The graph contains three unit impulses at :math:`-1,0,1`, so :math:`f(x)=\delta(x+1)+\delta(x)+\delta(x-1)`.
2. Form all nine ordered sums of positions. The sum :math:`-2` occurs once, :math:`-1` twice, zero three times, :math:`1` twice, and :math:`2` once.
3. Draw impulses at those five positions with weights :math:`1,2,3,2,1`; these are weights (areas), not finite impulse heights. Algebraically the result is :math:`\delta(x+2)+2\delta(x+1)+3\delta(x)+2\delta(x-1)+\delta(x-2)`.
""",
        r"The self-convolution is the five-line triangular weight sequence :math:`1,2,3,2,1`.",
        r"The output total weight is :math:`9=3^2`, the product of the two input total weights.",
    ),
    "8.41": (
        r"""
1. Use the delta identity directly: :math:`\int\delta(\xi-a)\delta(x-\xi-b)\,d\xi=\delta[x-(a+b)]`.
2. Expand the product of the three terms in :math:`f=\delta(x-1)+\delta(x)+\delta(x+1)` with another copy of :math:`f`. Keep all ordered pairs, including the two ways to form each nonzero inner sum and the three ways to form zero.
3. Collect coincident deltas:

   .. math::

      (f*f)(x)=\delta(x-2)+2\delta(x-1)+3\delta(x)
      +2\delta(x+1)+\delta(x+2).

""",
        r"The analytic expansion confirms the graphical construction in Problem 8.40.",
        r"Replacing ordered pairs with only distinct unordered pairs would undercount the cross terms.",
    ),
    "8.42": (
        r"""
1. The four unit spectral impulses lie at :math:`-3,-2,2,3`. Write :math:`F(k)=\sum_{a\in\{-3,-2,2,3\}}\delta(k-a)`.
2. Sum every ordered pair. The outer equal pairs give weights one at :math:`\pm6,\pm4`; mixed same-sign pairs give weight two at :math:`\pm5`; mixed opposite-sign pairs give weight two at :math:`\pm1`; the four exactly opposite pairs give weight four at zero.
3. Consequently

   .. math::

      F*F=4\delta(k)+2[\delta(k-1)+\delta(k+1)+\delta(k-5)+\delta(k+5)]
      +\delta(k-4)+\delta(k+4)+\delta(k-6)+\delta(k+6).

""",
        r"Nine output locations :math:`-6,-5,-4,-1,0,1,4,5,6` with weights :math:`1,2,1,2,4,2,1,2,1`.",
        r"The weights sum to :math:`16=4^2`; there are no lines at :math:`\pm2` or :math:`\pm3`.",
    ),
    "8.43": (
        r"""
1. Let :math:`p(x)=E_0` on :math:`[-d/2,d/2]` and zero outside. The impulse pair is signed: :math:`h(x)=\delta(x-d/2)-\delta(x+d/2)`.
2. Sifting gives :math:`g(x)=p(x-d/2)-p(x+d/2)`: it is :math:`-E_0` on :math:`(-d,0)`, :math:`+E_0` on :math:`(0,d)`, and zero elsewhere.
3. The transforms are :math:`P(k)=E_0d\operatorname{sinc}(kd/2)` and :math:`H(k)=-2i\sin(kd/2)`. Multiply them:

   .. math::

      G(k)=-2iE_0d\operatorname{sinc}(kd/2)\sin(kd/2).

""",
        r"The convolution is an odd bipolar rectangular pulse; its transform is the imaginary product of a sinc envelope and a sine.",
        r"The opposite-sign lobes have zero total area, so :math:`G(0)=0`.",
    ),
    "8.44": (
        r"""
1. Let each unit-height slit have width :math:`b`, with centre separation :math:`d`. Write :math:`f(x)=p_b(x-d/2)+p_b(x+d/2)`.
2. A rectangle convolved with itself is its overlap length: :math:`T_b(x)=(b-|x|)_+`, where :math:`(u)_+=\max(u,0)`.
3. Expand the four shifted pairings. The two same-side pairings are centred at :math:`\pm d`, while the two cross pairings coincide at zero:

   .. math::

      (f*f)(x)=T_b(x-d)+2T_b(x)+T_b(x+d).

""",
        r"Three triangular components of base width :math:`2b`, with central peak twice either outer peak when they do not overlap.",
        r"Their total area is :math:`4b^2=(2b)^2`, as required by the convolution area rule.",
    ),
    "8.45": (
        r"""
1. The actual source graph shows two finite rectangles: height :math:`A` on :math:`[1,2]` and height :math:`B` on :math:`[3,5]`. The tick marks depict :math:`A=2`, :math:`B=1`; keeping :math:`A,B` symbolic makes the normalization explicit.
2. In the convolution integral the allowed overlap is :math:`[1,2]\cap[x-5,x-3]`. Its length is :math:`\max[0,\min(2,x-3)-\max(1,x-5)]`.
3. Hence the output is zero outside :math:`[4,7]`, rises as :math:`AB(x-4)` on :math:`[4,5]`, stays at :math:`AB` on :math:`[5,6]`, and falls as :math:`AB(7-x)` on :math:`[6,7]`. The resulting trapezoid has height 2 for the illustrated normalization.
""",
        r"A trapezoid supported on :math:`[4,7]`, with a flat top on :math:`[5,6]` and peak :math:`AB`.",
        r"Its area is :math:`2AB=(A\cdot1)(B\cdot2)`, matching the product of rectangle areas.",
    ),
    "8.46": (
        r"""
1. The input impulses at :math:`x=0,1,2,3,4,5` have respective weights :math:`1,2,3,1,1,2`. The spread function is the unit triangle :math:`h(x)=(1-|x|)_+`.
2. Delta sifting turns the convolution into shifted weighted copies:

   .. math::

      g(x)=h(x)+2h(x-1)+3h(x-2)+h(x-3)+h(x-4)+2h(x-5).

3. Each triangle is zero at neighbouring integer centres, so :math:`g` passes through :math:`(-1,0),(0,1),(1,2),(2,3),(3,1),(4,1),(5,2),(6,0)`. Join consecutive points by straight segments and set the curve to zero outside :math:`[-1,6]`.
""",
        r"The result is the piecewise-linear interpolation of the six impulse weights, with zero endpoints at :math:`-1` and :math:`6`.",
        r"The triangle area is one, so the output area equals the input weight sum :math:`10`.",
    ),
    "8.47": (
        r"""
1. Let the six hole centres be the vertices :math:`\mathbf r_j` of a regular hexagon of circumradius :math:`a`, and let :math:`p(\mathbf r)` denote one circular hole. Then :math:`f=\sum_jp(\mathbf r-\mathbf r_j)` and :math:`f*f=\sum_{j,l}(p*p)(\mathbf r-\mathbf r_j-\mathbf r_l)`.
2. The 36 ordered centre sums form 19 distinct positions: one central position of multiplicity 6, six positions at radius :math:`a` of multiplicity 2, six at radius :math:`\sqrt3a` of multiplicity 2, and six at radius :math:`2a` of multiplicity 1. The middle-radius hexagon is rotated :math:`30^\circ` relative to the others.
3. Finite holes do not convolve to uniform disks. If each hole has radius :math:`r_0`, the individual spot profile is the disk-overlap area

   .. math::

      (p*p)(\rho)=2r_0^2\arccos\frac{\rho}{2r_0}
      -\frac{\rho}{2}\sqrt{4r_0^2-\rho^2},\quad 0\le\rho\le2r_0,

   and zero beyond :math:`2r_0`. Place copies of this profile at the 19 centres with the stated multiplicities, adding overlaps if necessary.
""",
        r"Nineteen hexagonally arranged convolution spots, with multiplicities :math:`6` at the centre, :math:`2` on each of two inner rings, and :math:`1` on the outer ring.",
        r"The multiplicities total :math:`6+6(2)+6(2)+6(1)=36`, accounting for every ordered pair of the six holes.",
    ),
}
