SOLUTIONS = {
    "7.52": (
        r"""
1. For equally spaced coherent point emitters, write the phase increment as :math:`2\alpha=2\pi a\sin\theta/\lambda`. The array factor is :math:`I_N=I_1[\sin(N\alpha)/\sin\alpha]^2`.
2. Set :math:`N=2` and use :math:`\sin2\alpha=2\sin\alpha\cos\alpha`. The ratio reduces to :math:`2\cos\alpha`, including its continuous limit where numerator and denominator both vanish.
3. Hence :math:`I_2=4I_1\cos^2(\pi a\sin\theta/\lambda)`, exactly the equal-amplitude Young interference factor. Finite slit width multiplies this by the single-slit envelope.
""",
        r"Young's two-source pattern is the :math:`N=2` array factor.",
        r"At broadside the field doubles and the irradiance is four times the one-source value.",
    ),
    "7.53": (
        r"""
1. Principal maxima occur at :math:`\alpha=m\pi`, where all :math:`N` phasors align and the limiting amplitude is :math:`N`.
2. Between :math:`m\pi` and :math:`(m+1)\pi`, the numerator vanishes at :math:`\alpha=m\pi+q\pi/N`, with :math:`q=1,\ldots,N-1`; the denominator is nonzero there. These are :math:`N-1` true minima.
3. Each interval between consecutive internal zeros contains one subsidiary peak of the uniform-array factor, giving :math:`N-2` secondary maxima. The two outer intervals lead into the adjacent principal peaks rather than adding secondary ones.
""",
        r"There are :math:`N-1` minima and :math:`N-2` secondary maxima between adjacent principal maxima.",
        r"For :math:`N=2`, there is one minimum and no secondary maximum, matching Young interference.",
    ),
    "7.54": (
        r"""
1. The 32-element array has pitch :math:`a=7\,\mathrm m` and wavelength :math:`\lambda=0.21\,\mathrm m`. Principal maxima satisfy :math:`\sin\theta_m=m\lambda/a`.
2. Near broadside, adjacent principal maxima are separated by :math:`\Delta\theta\approx\lambda/a=0.0300\,\mathrm{rad}=1.719^\circ\approx1^\circ43'`.
3. The first nulls around the central maximum satisfy :math:`\sin\theta=\pm\lambda/(Na)`. The full null-to-null width is :math:`2\arcsin[0.21/(32\cdot7)]=0.001875\,\mathrm{rad}=6.45'`.
""",
        r"Principal-lobe separation near broadside :math:`1.72^\circ`; central null-to-null width :math:`6.45'`.",
        r"The individual 2 m dishes supply a broader element envelope; their diameter is not the array pitch used in the interference factor.",
    ),
    "7.55": (
        r"""
1. Define the phase advance imposed between adjacent emitters as :math:`\epsilon`, and write the received phase increment as :math:`\Delta=ka\sin\theta-\epsilon`.
2. The zeroth-order maximum occurs when adjacent received fields are in phase without an added full turn: :math:`\Delta=0`.
3. Therefore :math:`\theta_0=\arcsin(\epsilon/ka)=\arcsin[\epsilon\lambda/(2\pi a)]`. A propagating zeroth-order direction exists only when the arcsine argument lies between :math:`-1` and :math:`1`.
""",
        r":math:`\theta_0=\arcsin[\epsilon\lambda/(2\pi a)]` with the stated phase-advance convention.",
        r"Reversing the definition of which emitter leads changes the steering sign, not its magnitude.",
    ),
    "7.56": (
        r"""
1. The frequency :math:`10^9\,\mathrm{Hz}` gives :math:`\lambda=0.30\,\mathrm m`; the pitch is :math:`a=0.60\,\mathrm m`.
2. With adjacent phase advance :math:`\epsilon=30^\circ=\pi/6`, :math:`\sin\theta_0=(\pi/6)(0.30)/(2\pi\cdot0.60)=1/24`.
3. Thus :math:`\theta_0=2.388^\circ\approx2^\circ23'`. The 20-element count narrows the peak but does not change this steering angle, because the required cancellation is between adjacent phases.
""",
        r"The central lobe moves by about :math:`2.39^\circ`.",
        r"The same pitch and frequency give the same steering magnitude as the two-source example in Problem 6.57.",
    ),
    "7.57": (
        r"""
1. Points separated by :math:`a` along a smooth reflecting interface are driven by incident phase increment :math:`\epsilon=ka\sin\theta_i`.
2. Radiation toward a reflected angle :math:`\theta` contributes the opposite geometric increment, so the relative received phase is :math:`ka(\sin\theta-\sin\theta_i)`.
3. Constructive addition over the whole interface requires :math:`\sin\theta=\sin\theta_i`, giving :math:`\theta=\theta_i` in the reflected half-space. Atomic spacing is far below the wavelength, so no other propagating grating orders satisfy the condition.
""",
        r"The coherent reradiated principal maximum obeys the law of reflection.",
        r"Tangential wave-vector matching is the continuum version of this phased-array argument.",
    ),
    "7.58": (
        r"""
1. A slit minimum is a missing angular component at :math:`a\sin\theta_m=m\lambda`, independent of any subsequent collecting-lens position.
2. In the paraxial ray description, a ray arriving at a thin lens with height :math:`h` and slope :math:`u` exits with slope :math:`u-h/f`. At the rear focal plane its height is :math:`h+f(u-h/f)=fu`; the lens intercept height cancels.
3. Using the geometrical angle-to-screen convention :math:`z_m=f\tan\theta_m` gives

   .. math::

      z_m=\frac{m\lambda f}{\sqrt{a^2-m^2\lambda^2}}
      \approx\frac{m\lambda f}{a}.

   Translating a sufficiently large collecting lens does not change the angular spectrum; observe its corresponding rear focal plane.
""",
        r"The focal-plane minimum positions depend on :math:`a,\lambda,f`, not the slit-lens separation.",
        r"Clipping by a finite lens or keeping the detector away from the shifted focal plane invalidates the stated invariance.",
    ),
    "7.59": (
        r"""
1. For incidence at :math:`\theta_i`, the phase gradient across a slit is proportional to :math:`\sin\theta-\sin\theta_i`, so :math:`I\propto\operatorname{sinc}^2[\pi a(\sin\theta-\sin\theta_i)/\lambda]`.
2. The central maximum occurs at :math:`\theta=\theta_i=30^\circ`. Adjacent minima satisfy :math:`\sin\theta_m-\sin30^\circ=m\lambda/a`.
3. Linearize near the maximum: :math:`\cos30^\circ\,\Delta\theta\approx\lambda/a`. Compared with normal incidence, the local angular spacing increases by :math:`1/\cos30^\circ=1.1547`.
""",
        r"The pattern shifts to :math:`30^\circ` and its local angular fringe scale grows by about :math:`15.5\%`.",
        r"A screen-coordinate width additionally depends on how the screen is oriented relative to the displaced central beam.",
    ),
    "7.60": (
        r"""
1. A single-slit minimum obeys :math:`a\sin\theta=m\lambda`.
2. At the common angle, the first minimum for :math:`\lambda_1` gives :math:`a\sin\theta=\lambda_1`, while the third for :math:`\lambda_2` gives :math:`a\sin\theta=3\lambda_2`.
3. Equate the two right sides; the aperture width and observation geometry cancel.
""",
        r":math:`\lambda_1=3\lambda_2`.",
        r"The longer wavelength reaches a given angular minimum at a smaller order, consistent with its broader diffraction pattern.",
    ),
    "7.61": (
        r"""
1. The single-slit profile is :math:`I/I(0)=(\sin\beta/\beta)^2`, with :math:`\beta\approx\pi ay/(\lambda L)`.
2. Half maximum requires :math:`(\sin\beta/\beta)^2=1/2`; the first positive root is :math:`\beta_{1/2}=1.391557`, not :math:`\pi/2`.
3. The full width is

   .. math::

      W=\frac{2\beta_{1/2}}\pi\frac{\lambda L}{a}
      =0.885893\frac{(632.8\times10^{-9})(1000)}{10^{-3}}
      =0.56059\,\mathrm m.

   The printed 632.8 mm corresponds to the rough scale :math:`\lambda L/a`, not the exact half-irradiance width.
""",
        r"The central-peak FWHM is approximately :math:`560.6\,\mathrm{mm}`.",
        r"The null-to-null width is :math:`2\lambda L/a=1265.6\,\mathrm{mm}`; it must not be confused with FWHM.",
    ),
    "7.62": (
        r"""
1. The first minima satisfy :math:`\sin\theta_1=\pm\lambda/a` with :math:`\lambda=550\,\mathrm{nm}`, :math:`a=0.25\,\mathrm{mm}`.
2. Since :math:`\lambda/a=0.0022\ll1`, use focal-plane positions :math:`y_{\pm1}\approx\pm f\lambda/a`.
3. Their separation is :math:`W=2(0.60)(550\times10^{-9})/(0.25\times10^{-3})=0.00264\,\mathrm m`.
""",
        r"The central null-to-null width is :math:`2.64\,\mathrm{mm}`.",
        r"Each first minimum is only :math:`1.32\,\mathrm{mm}` from the centre; the question asks their full separation.",
    ),
    "7.63": (
        r"""
1. The fourth minima lie at :math:`y_{\pm4}\approx\pm4\lambda f/a`. Their measured separation is :math:`\Delta y=8\lambda f/a`.
2. Isolate the focal length: :math:`f=a\Delta y/(8\lambda)`.
3. With :math:`a=0.25\,\mathrm{mm}`, :math:`\Delta y=1.25\,\mathrm{mm}`, and :math:`\lambda=550\,\mathrm{nm}`, :math:`f=0.071023\,\mathrm m=7.10\,\mathrm{cm}`.
""",
        r"The collecting lens focal length is approximately :math:`7.1\,\mathrm{cm}`.",
        r"The relevant order factor is eight because the measurement spans the negative and positive fourth minima.",
    ),
    "7.64": (
        r"""
1. For centre spacing :math:`a` and individual slit width :math:`b`, the central diffraction envelope spans :math:`-\lambda/b<\sin\theta<\lambda/b`. Interference-order spacing in :math:`\sin\theta` is :math:`\lambda/a`.
2. Dividing envelope width by fringe spacing gives :math:`(2\lambda/b)/(\lambda/a)=2a/b=2M`. This proves the source's count of fringe *spacings* across the envelope.
3. For an exact count of nominal bright interference orders, require :math:`|m|<a/b=M`. If :math:`M` is an integer, the interior orders are :math:`m=-(M-1),\ldots,M-1`, giving :math:`2M-1`; the orders :math:`\pm M` are missing at the envelope zeros. The full product's very weak edge peaks and a visibility threshold can further complicate counting observed bright spots.
""",
        r":math:`2M` is the envelope-width/fringe-spacing ratio; it is not an exact universal count of visible maxima.",
        r"An integer order coincident with a single-slit zero cannot be counted as a bright fringe.",
    ),
    "7.65": (
        r"""
1. With :math:`b=0.25\,\mathrm{mm}`, the approximate width-count rule from Problem 7.64 gives :math:`15\approx2a/b`, hence :math:`a\approx1.875\,\mathrm{mm}`.
2. If instead 15 means the nominal nonmissing interference orders :math:`0,\pm1,\ldots,\pm7`, their strict condition is :math:`7<a/b\le8`, or :math:`1.75<a\le2.00\,\mathrm{mm}`. Merely counting those orders does not uniquely determine :math:`a`.
3. If the additional assumption is that the eighth order is exactly missing, :math:`a/b=8` and :math:`a=2.00\,\mathrm{mm}`. The printed 3.75 mm implies :math:`a/b=15` and is inconsistent with 15 nominal interior bright orders; the stated seventh-order coincidence is also incompatible with that value.
""",
        r"Width-count estimate: :math:`a\approx1.875\,\mathrm{mm}`. Exact inference requires an edge-order or fringe-position measurement.",
        r"Explicitly distinguish a count of visible peaks, a count of nominal interference orders, and a width divided by a spacing.",
    ),
    "7.66": (
        r"""
1. The printed screen distance is 3 m. With centre spacing :math:`a=0.4\,\mathrm{mm}`, :math:`\Delta y\approx\lambda L/a=(550\times10^{-9})(3)/(0.4\times10^{-3})=4.125\,\mathrm{mm}`.
2. Using the source's approximate count of nine fringes across the main envelope gives :math:`9\approx2a/b`; hence :math:`b\approx2(0.4)/9=0.08889\,\mathrm{mm}`.
3. This width is an estimate because the weak edge fringes are not assigned a precise detection threshold. Counting exactly nine nominal interference orders would instead constrain :math:`4<a/b\le5`, or :math:`0.080\le b<0.100\,\mathrm{mm}`, not uniquely determine the width.
""",
        r"Fringe spacing :math:`4.125\,\mathrm{mm}`; approximate slit width :math:`0.089\,\mathrm{mm}`.",
        r"The fine fringe spacing determines centre separation, while the much broader envelope determines individual slit width.",
    ),
    "7.67": (
        r"""
1. Write :math:`I_N=I_1\operatorname{sinc}^2\beta[\sin(N\alpha)/\sin\alpha]^2`, where :math:`\beta=\pi b\sin\theta/\lambda` and :math:`\alpha=\pi a\sin\theta/\lambda`.
2. For :math:`N=1`, the array factor is identically one, leaving the single-slit result :math:`I_1\operatorname{sinc}^2\beta`.
3. For :math:`N=2`, :math:`\sin2\alpha/\sin\alpha=2\cos\alpha`, giving :math:`I_2=4I_1\operatorname{sinc}^2\beta\cos^2\alpha`. This separates the individual-slit diffraction envelope from the two-slit interference modulation.
""",
        r"The general grating expression correctly reduces to the one- and two-slit formulas.",
        r"At the axis its value is :math:`N^2I_1`, because fields add coherently.",
    ),
    "7.68": (
        r"""
1. For normal incidence, grating principal orders obey :math:`a\sin\theta_m=m\lambda`.
2. A real propagation angle requires :math:`|\sin\theta_m|\le1`, hence :math:`|m|\le a/\lambda` and :math:`m_{\max}=\lfloor a/\lambda\rfloor`.
3. At most :math:`2\lfloor a/\lambda\rfloor+1` signed orders are geometrically allowed, including zero. Finite slit width can suppress some as missing orders, and an order exactly at grazing is not collected by an ordinary forward screen.
""",
        r"The maximum allowed order magnitude is :math:`\lfloor a/\lambda\rfloor` for normal incidence.",
        r"Increasing the number of illuminated slits sharpens the allowed orders; it does not create orders beyond the direction-cosine limit.",
    ),
    "7.69": (
        r"""
1. Midway in phase between two principal peaks, :math:`\alpha=(m+1/2)\pi`, so :math:`|\sin\alpha|=1`.
2. For odd :math:`N`, :math:`N\alpha` is also an odd multiple of :math:`\pi/2`, giving :math:`|\sin N\alpha|=1`. Thus the squared array factor is one.
3. Near the central envelope where :math:`\operatorname{sinc}^2\beta\approx1`, the midpoint irradiance is :math:`I_1`, while :math:`I(0)=N^2I_1`. The ratio is :math:`1/N^2`.
""",
        r"For odd :math:`N`, the midpoint subsidiary peak has :math:`I/I(0)\approx1/N^2`.",
        r"For even :math:`N`, the same midpoint has zero numerator and is a minimum, not a subsidiary maximum.",
    ),
    "7.70": (
        r"""
1. The pitch is :math:`a=25.4\,\mathrm{mm}/12000=2.11667\,\mathrm{\mu m}`. In second order, :math:`\theta(450\,\mathrm{nm})=\arcsin(0.9/2.11667)=25.163^\circ` and :math:`\theta(650\,\mathrm{nm})=37.892^\circ`.
2. The angular extent is :math:`\Delta\theta=0.222155\,\mathrm{rad}`. For a collecting lens aimed near the spectrum centre, the local focal-plane approximation :math:`\Delta y\approx f\Delta\theta` gives :math:`f=0.0125/0.222155=0.05627\,\mathrm m`.
3. This reproduces the source's :math:`5.63\,\mathrm{cm}` angular approximation. Geometry matters at these large absolute angles: a screen perpendicular to the original grating normal with mapping :math:`y=f\tan\theta` instead gives :math:`f=0.0125/(\tan37.892^\circ-\tan25.163^\circ)=4.05\,\mathrm{cm}`.
""",
        r"Approximately :math:`5.63\,\mathrm{cm}` for a locally centred collecting-lens angular mapping; specify the optical axis for a nonparaxial screen calculation.",
        r"The spectrum spans over :math:`12^\circ`, so :math:`f\Delta\theta` and :math:`f\Delta(\tan\theta)` should not be interchanged silently.",
    ),
    "7.71": (
        r"""
1. The ideal Rayleigh resolving power of :math:`N` illuminated grating lines in order :math:`m` is :math:`\mathcal R=\lambda/\Delta\lambda=|m|N`.
2. For normal incidence, the propagating-order condition from Problem 7.68 is :math:`|m|\le a/\lambda`.
3. Multiply this inequality by :math:`N`: :math:`\mathcal R\le aN/\lambda`. The bound is the illuminated grating width divided by wavelength, up to the usual :math:`Na` aperture-width convention.
""",
        r":math:`\mathcal R\le aN/\lambda` for the normal-incidence geometry considered.",
        r"The bound changes for oblique incidence; it is not a geometry-independent limit on all grating configurations.",
    ),
    "7.72": (
        r"""
1. The illuminated number of grooves is :math:`N=(16000\,\mathrm{in}^{-1})(2.5\,\mathrm{in})=40000`.
2. Formally, third-order resolving power is :math:`\mathcal R_3=3N=120000`. In second order :math:`\mathcal R_2=80000`, giving :math:`\Delta\lambda_{\min}=550/80000=0.006875\,\mathrm{nm}`.
3. Check accessibility: the pitch is :math:`1587.5\,\mathrm{nm}` and :math:`3(550)=1650\,\mathrm{nm}>a`. Thus third-order green light is not propagating at normal incidence; the quoted third-order resolving power requires suitable oblique incidence. Second order is accessible normally.
""",
        r"Formal :math:`\mathcal R_3=120000`; second-order :math:`\Delta\lambda_{\min}=6.875\times10^{-3}\,\mathrm{nm}`.",
        r"A large formal :math:`mN` is useful only if the chosen order actually exists in the illumination geometry.",
    ),
    "7.73": (
        r"""
1. A mode spacing :math:`\Delta\nu=150\,\mathrm{MHz}` at :math:`\lambda=632.8\,\mathrm{nm}` demands :math:`\mathcal R=\nu/\Delta\nu=c/(\lambda\Delta\nu)\approx3.16\times10^6`.
2. In second order :math:`N=\mathcal R/2\approx1.58\times10^6` illuminated grooves.
3. At :math:`200\,\mathrm{lines/mm}`, the width is :math:`W=N/(200\,\mathrm{mm}^{-1})\approx7900\,\mathrm{mm}=7.9\,\mathrm m`. This very large result follows from the given 150 MHz spacing; the printed 79 cm is a factor of ten smaller than these data require.
""",
        r"An ideal second-order grating would need approximately :math:`7.9\,\mathrm m` of illuminated width.",
        r"The equivalent wavelength separation is only about :math:`2.0\times10^{-4}\,\mathrm{nm}`, explaining the unusually demanding resolution.",
    ),
    "7.74": (
        r"""
1. Different orders overlap when :math:`m\lambda_m=n\lambda_n`, since they then share the same diffracted angle.
2. First and second orders require :math:`\lambda_1=2\lambda_2`. For a conventional 400–700 nm visible interval, even :math:`2(400)=800\,\mathrm{nm}` is beyond its red end, so those orders do not overlap. Extending the visible limits can permit a small edge overlap.
3. Second and third orders require :math:`\lambda_2=1.5\lambda_3`; for example :math:`2(600)=3(400)` nm. They can therefore overlap substantially within the visible band.
""",
        r"First/second overlap is absent or marginal depending on the visible-band definition; second/third overlap is common.",
        r"Order-sorting filters remove unwanted wavelengths that share the same grating output angle.",
    ),
    "7.75": (
        r"""
1. At the shared angle, the grating equation gives :math:`a\sin\theta=3\lambda_3=4\lambda_4`.
2. Substitute the known fourth-order wavelength :math:`\lambda_4=490\,\mathrm{nm}`.
3. Solve :math:`\lambda_3=(4/3)(490)=653.333\,\mathrm{nm}`.
""",
        r"Third-order :math:`653.3\,\mathrm{nm}` overlaps fourth-order :math:`490\,\mathrm{nm}`.",
        r"The lower order must use the longer wavelength to have the same product :math:`m\lambda`.",
    ),
    "7.76": (
        r"""
1. A spherical wave from an axial point a distance :math:`L` away has path :math:`r(x)=\sqrt{L^2+x^2}\approx L+x^2/(2L)` across the aperture.
2. If :math:`d` is the maximum transverse coordinate scale, the neglected quadratic phase is at most of order :math:`\Delta\phi\sim\pi d^2/(\lambda L)`.
3. Requiring this phase curvature to be small gives :math:`L\gg d^2/\lambda`, with order-one constants depending on whether :math:`d` denotes radius or full width and on the permitted phase error. The same expansion applies to propagation from aperture to screen.
""",
        r"The far-field scale is :math:`L\gg d^2/\lambda`; :math:`L>d^2/\lambda` is only a rough rule of thumb.",
        r"For finite source and screen distances, both quadratic contributions must be negligible, or lenses must provide the required wavefront transformation.",
    ),
    "7.77": (
        r"""
1. The hole radius is 1.25 mm, so its full diameter is :math:`d=2.5\times10^{-3}\,\mathrm m`.
2. Apply the source's full-aperture rule of thumb: :math:`d^2/\lambda=(2.5\times10^{-3})^2/(632.8\times10^{-9})=9.8767\,\mathrm m`.
3. A viewing distance greater than roughly 10 m begins the far-field regime on this criterion; use a substantially larger distance for a stricter small-phase-error approximation.
""",
        r"A lens-free Fraunhofer viewing distance is of order :math:`10\,\mathrm m` or more.",
        r"Using the radius in a formula stated for diameter changes the estimate by a factor of four.",
    ),
    "7.78": (
        r"""
1. A square aperture has :math:`I/I(0)=\operatorname{sinc}^2\alpha\operatorname{sinc}^2\beta`. Along a diagonal :math:`\alpha=\beta=u`, so the profile is :math:`(\sin u/u)^4`.
2. Nonzero side maxima satisfy :math:`d(\sin u/u)/du=0`, or :math:`u\cos u-\sin u=0`, equivalently :math:`\tan u=u`.
3. For the third side peak, the root between :math:`3\pi` and :math:`7\pi/2` is :math:`u=10.90412`. Therefore :math:`I/I(0)=(\sin u/u)^4=6.956\times10^{-5}`. The simpler midpoint estimate :math:`u\approx7\pi/2` gives :math:`6.84\times10^{-5}`.
""",
        r"The third diagonal side maximum is about :math:`6.96\times10^{-5}` of the central irradiance.",
        r"Along an axis there is only one sinc-squared factor; along a diagonal two factors suppress the side peaks much more strongly.",
    ),
    "7.79": (
        r"""
1. In scalar Fraunhofer propagation at fixed distance :math:`L`, the on-axis aperture integral has no transverse phase cancellation: :math:`U(0)=e^{ikL}U_iA/(i\lambda L)` for uniform illumination over area :math:`A`.
2. Take the squared magnitude: :math:`I(0)=I_iA^2/(\lambda^2L^2)`.
3. Thus at fixed incident irradiance and observation distance, the peak scales as :math:`A^2` and inversely as :math:`\lambda^2`. The total transmitted power still scales as :math:`A`, because a larger aperture also narrows the diffraction pattern.
""",
        r":math:`I(0)\propto A^2/\lambda^2` with illumination and distance held fixed.",
        r"Peak irradiance is not total transmitted power; confusing the two would suggest a false energy-conservation problem.",
    ),
    "7.80": (
        r"""
1. A uniformly illuminated circular pupil has first Airy zero at angular radius :math:`\theta_1\approx1.22\lambda/D`.
2. At the focal plane its physical radius is :math:`r_1\approx f\theta_1=1.22\lambda f/D`.
3. Substitute :math:`\lambda=550\,\mathrm{nm}`, :math:`f=1.50\,\mathrm m`, :math:`D=0.12\,\mathrm m`: :math:`r_1=8.3875\times10^{-6}\,\mathrm m=0.00839\,\mathrm{mm}`.
""",
        r"The Airy disk radius is approximately :math:`8.39\,\mathrm{\mu m}`.",
        r"The disk diameter is twice this value; the first dark ring defines the boundary used here.",
    ),
    "7.81": (
        r"""
1. In the source's uniform circular-aperture model, the diffraction half-angle to the first zero is :math:`\theta_1=1.22\lambda/D`.
2. With :math:`\lambda=632.8\,\mathrm{nm}` and initial diameter :math:`D=2\,\mathrm{mm}`, :math:`\theta_1=3.8601\times10^{-4}\,\mathrm{rad}`.
3. At :math:`L=1000\,\mathrm m`, the first-zero diameter is :math:`2L\theta_1=0.7720\,\mathrm m`, much larger than the initial 2 mm diameter.
""",
        r"The far-field central-disk diameter is about :math:`77\,\mathrm{cm}` under the uniform-aperture model.",
        r"A Gaussian laser beam uses a different beam-radius convention and divergence formula; its :math:`1/e^2` diameter is not an Airy first-zero diameter.",
    ),
    "7.82": (
        r"""
1. The requested 1 micrometre spot is a full first-zero diameter, so use :math:`d_{\rm spot}=2.44\lambda f/D`.
2. Solve for pupil diameter: :math:`D=2.44\lambda f/d_{\rm spot}`.
3. For :math:`\lambda=450\,\mathrm{nm}`, :math:`f=225\,\mathrm{mm}`, :math:`d_{\rm spot}=1\,\mathrm{\mu m}`, the paraxial expression gives :math:`D=0.24705\,\mathrm m=24.7\,\mathrm{cm}`. This is a fast, high-aperture system, so a real design needs a numerical-aperture/vector-diffraction treatment rather than assuming the paraxial result is exact.
""",
        r"The textbook paraxial aperture estimate is :math:`D\approx24.7\,\mathrm{cm}`.",
        r"The result corresponds to about :math:`f/0.91`, warning that small-angle pupil geometry is no longer very accurate.",
    ),
    "7.83": (
        r"""
1. For the stated historical telescope, convert :math:`D=140\,\mathrm{ft}=42.672\,\mathrm m`. The hydrogen-line wavelength is :math:`\lambda=c/\nu\approx3.0\times10^8/(1.420\times10^9)=0.21127\,\mathrm m`.
2. The uniform-aperture Rayleigh angle is :math:`\theta_R=1.22\lambda/D`.
3. Substitution gives :math:`\theta_R\approx0.00604\,\mathrm{rad}=0.346^\circ`, close to the rounded :math:`0.344^\circ` obtained with :math:`\lambda=0.21\,\mathrm m`.
""",
        r"Angular resolution is approximately :math:`6.0\times10^{-3}\,\mathrm{rad}`, or :math:`0.35^\circ`.",
        r"This uses the historical diameter supplied by the exercise, not a claim about present-day telescope rankings.",
    ),
    "7.84": (
        r"""
1. The diffraction-limited angular separation in object space is :math:`\Delta\phi=1.22\lambda_0/D` for the air-side pupil.
2. With :math:`\lambda_0=550\,\mathrm{nm}` and :math:`D=2.5\,\mathrm{mm}`, :math:`\Delta\phi=2.684\times10^{-4}\,\mathrm{rad}`.
3. At :math:`L=1000\,\mathrm m`, the minimum transverse source spacing is :math:`s\approx L\Delta\phi=0.2684\,\mathrm m=26.84\,\mathrm{cm}`. Internal ocular refraction changes the retinal angle, not this external source separation calculation.
""",
        r"Ideal angular resolution :math:`2.68\times10^{-4}\,\mathrm{rad}`; source separation at 1 km :math:`26.8\,\mathrm{cm}`.",
        r"Real visual acuity also depends on aberrations, contrast, retinal sampling, and illumination; this is only the diffraction limit.",
    ),
    "7.85": (
        r"""
1. Convert the headlight spacing: :math:`s=43\,\mathrm{in}=1.0922\,\mathrm m`.
2. A 4 mm pupil at 550 nm has Rayleigh angle :math:`\theta_R=1.22(550\times10^{-9})/0.004=1.6775\times10^{-4}\,\mathrm{rad}`.
3. Set the apparent separation :math:`s/L` equal to :math:`\theta_R`: :math:`L=s/\theta_R=6511\,\mathrm m\approx6.51\,\mathrm{km}`.
""",
        r"The ideal diffraction-limited just-resolvable distance is about :math:`6.5\,\mathrm{km}`.",
        r"This ignores atmospheric blur and glare; it is not a practical guaranteed nighttime viewing distance.",
    ),
    "7.86": (
        r"""
1. For normally incident plane waves observed on axis at distance :math:`z`, a radius :math:`r` adds path :math:`\Delta\approx r^2/(2z)`.
2. A half-period Fresnel zone corresponds to :math:`\Delta=m\lambda/2`, so :math:`r_m^2=m\lambda z` and the exposed zone count is :math:`N=r^2/(\lambda z)`.
3. The hole radius is :math:`r=0.005\,\mathrm m`, not 0.01 m. Hence :math:`N=0.005^2/[(500\times10^{-9})(0.5)]=100`.
""",
        r"The aperture uncovers approximately 100 Fresnel half-period zones.",
        r"The Fresnel-zone count uses radius squared; inserting the diameter would overestimate the count by four.",
    ),
    "7.87": (
        r"""
1. For a circular aperture, normalized axial field in the Fresnel approximation is :math:`U/U_0=1-e^{i\pi N}`, where :math:`N=r^2/(\lambda z)`.
2. Thus :math:`I/I_0=4\sin^2(\pi N/2)`: odd zone counts give maxima and even counts give minima.
3. With :math:`\lambda z=(500\times10^{-9})(2.25)=1.125\times10^{-6}\,\mathrm{m^2}`, the first three odd-zone radii are :math:`\sqrt{1,3,5}\sqrt{\lambda z}=1.061,1.837,2.372\,\mathrm{mm}`. The first three nonzero even-zone radii are :math:`1.500,2.121,2.598\,\mathrm{mm}`.
""",
        r"Maxima at :math:`1.06,1.84,2.37\,\mathrm{mm}`; minima at :math:`1.50,2.12,2.60\,\mathrm{mm}`, continuing by :math:`r_m=\sqrt{m\lambda z}`.",
        r"Adding more aperture area can reduce on-axis irradiance because adjacent zones arrive approximately out of phase.",
    ),
    "7.88": (
        r"""
1. Calculate the exposed zone count: :math:`N=(0.7955\times10^{-3})^2/[(632.8\times10^{-9})(2)]\approx0.50002`.
2. The normalized axial field is :math:`1-e^{i\pi N}`. For exactly half a zone this is :math:`1-i`, whose squared magnitude is 2.
3. Equivalently :math:`I/I_0=4\sin^2(\pi N/2)\approx4\sin^2(\pi/4)=2`.
""",
        r"The axial irradiance is approximately :math:`2I_0`.",
        r"Half a Fresnel zone does not mean half the unobstructed irradiance; amplitudes and their relative phase determine the result.",
    ),
    "7.89": (
        r"""
1. At :math:`\lambda=500\,\mathrm{nm}`, :math:`z=4\,\mathrm m`, the first two zone radii are :math:`r_1=\sqrt{\lambda z}=1.414\,\mathrm{mm}` and :math:`r_2=\sqrt{2\lambda z}=2.000\,\mathrm{mm}`.
2. The illustrated aperture transmits the full first zone plus a :math:`90^\circ` sector, one quarter, of the second zone. A full first zone contributes :math:`2U_0`, while the full second contributes :math:`-2U_0` in the equal-zone approximation.
3. Since phase on axis is independent of azimuth, the sector contributes its angular fraction of the field: :math:`U/U_0=2-(1/4)2=3/2`. Therefore :math:`I=(3/2)^2(40)=90\,\mathrm{W\,m^{-2}}`.
""",
        r"The axial irradiance is :math:`90\,\mathrm{W\,m^{-2}}` in the Fresnel-zone approximation.",
        r"Use a quarter of the second-zone amplitude, not a quarter of its irradiance; the sectors interfere coherently.",
    ),
    "7.90": (
        r"""
1. One and a half uncovered zones means :math:`N=1.5`, or an aperture-edge phase :math:`\pi N=3\pi/2`.
2. The circular-aperture field is :math:`U/U_0=1-e^{i3\pi/2}=1+i`.
3. Squaring gives :math:`I/I_0=|1+i|^2=2`. The same value follows from :math:`4\sin^2(3\pi/4)`.
""",
        r":math:`I=2I_0`.",
        r"The half-zone and one-and-a-half-zone apertures have different field phases but equal axial irradiances.",
    ),
    "7.91": (
        r"""
1. At :math:`\lambda z=2\times10^{-6}\,\mathrm{m^2}`, the source figure's upper semicircle of radius 1.414 mm ends at zone 1; its lower semicircle of radius 2.449 mm ends at zone 3.
2. Any full odd-zone circular aperture contributes :math:`2U_0` on axis in this approximation. Each semicircle contributes half of its respective full aperture field, so the two contributions are :math:`U_0` and :math:`U_0`.
3. Add before squaring: :math:`U=2U_0`, hence :math:`I=4I_0=4(25)=100\,\mathrm{W\,m^{-2}}`.
""",
        r"The on-axis irradiance is :math:`100\,\mathrm{W\,m^{-2}}`.",
        r"Although the semicircle areas differ, each includes an odd number of half-period zones and gives the same normalized axial field.",
    ),
    "7.92": (
        r"""
1. The opaque shape blocks the first full zone and two opposite :math:`90^\circ` sectors of the second zone, with radii :math:`r_1=1.414\,\mathrm{mm}`, :math:`r_2=2\,\mathrm{mm}` at the stated wavelength and distance.
2. The field that would pass through the complementary shaped aperture is :math:`U_{\rm blocked}=2U_0+\tfrac12(-2U_0)=U_0`.
3. Apply Babinet's principle to complex fields: :math:`U_{\rm obstruction}=U_0-U_{\rm blocked}=0`. Equivalently, the first-zone disk alone leaves :math:`-U_0`; blocking half the next zone adds :math:`+U_0` and cancels it.
""",
        r"The axial irradiance is approximately zero.",
        r"Babinet subtracts complex amplitudes, not intensities. Rounded zone radii and nonparaxial corrections prevent a perfectly exact physical zero.",
    ),
    "7.93": (
        r"""
1. For source and image distances :math:`p,q`, the extra path through radius :math:`r` is :math:`\Delta\approx r^2/(2p)+r^2/(2q)`.
2. At the :math:`m`th zone boundary, set :math:`\Delta=m\lambda/2`. Then :math:`r_m^2(1/p+1/q)=m\lambda`, or :math:`1/p+1/q=1/f` with :math:`f=r_m^2/(m\lambda)`.
3. With :math:`p=q=5\,\mathrm m`, :math:`f=2.5\,\mathrm m`. The first-zone radius is :math:`r_1=\sqrt{\lambda f}=\sqrt{(500\times10^{-9})(2.5)}=1.118\,\mathrm{mm}=0.1118\,\mathrm{cm}`.
""",
        r"The zone-plate focal length is :math:`r_m^2/(m\lambda)`; the first radius here is :math:`1.12\,\mathrm{mm}`.",
        r"The focal length varies inversely with wavelength, so a zone plate is strongly chromatic.",
    ),
    "7.94": (
        r"""
1. The unobstructed on-axis wave is the coherent sum of all half-period zones; their alternating contributions leave approximately half the first-zone field.
2. Equivalently, the Fresnel aperture formula at :math:`N=1` gives :math:`U/U_0=1-e^{i\pi}=2`.
3. With all other zones blocked, the irradiance is therefore :math:`I/I_0=|2|^2=4`.
""",
        r"The single first-zone opening produces approximately :math:`4I_0` at the focus.",
        r"This local concentration does not increase total transmitted power; other observation points receive less light.",
    ),
    "7.95": (
        r"""
1. Use :math:`m=8`, :math:`r_8=4.5\,\mathrm{mm}`, and :math:`\lambda=650\,\mathrm{nm}` in :math:`f=r_8^2/(m\lambda)`.
2. This gives :math:`f=(4.5\times10^{-3})^2/[8(650\times10^{-9})]=3.89423\,\mathrm m`.
3. For :math:`p=7.788\,\mathrm m`, :math:`q=(1/f-1/p)^{-1}\approx7.789\,\mathrm m`. Since :math:`p` is essentially :math:`2f`, the image distance is essentially :math:`2f` as well.
""",
        r":math:`f\approx3.894\,\mathrm m`; image distance approximately :math:`7.79\,\mathrm m`.",
        r"Use the zone-boundary index 8, not the count of transparent rings, when applying :math:`r_m^2=m\lambda f`.",
    ),
    "7.96": (
        r"""
1. Let :math:`F(v)=C(v)+iS(v)=\int_0^v e^{i\pi u^2/2}\,du`. For a centred slit with scaled half-width :math:`v`, its normalized irradiance is :math:`I/I_0=\tfrac12|F(v)-F(-v)|^2`.
2. Both Fresnel integrals are odd, so this becomes :math:`I/I_0=2[C(v)^2+S(v)^2]`.
3. A very wide slit has :math:`v\to\infty`, where :math:`C,S\to1/2`. Thus :math:`I/I_0\to2[(1/2)^2+(1/2)^2]=1`.
""",
        r"The axial irradiance approaches the unobstructed value :math:`I_0` as slit width increases without bound.",
        r"The approach is oscillatory because successive admitted strips add at changing phases; it is not monotonic.",
    ),
    "7.97": (
        r"""
1. Parameterize the Cornu spiral by :math:`(C(v),S(v))`. Differentiation gives :math:`C'(v)=\cos(\pi v^2/2)` and :math:`S'(v)=\sin(\pi v^2/2)`.
2. Therefore :math:`dS/dC=\tan(\pi v^2/2)`. The directed tangent angle is :math:`\beta=\pi v^2/2` modulo :math:`2\pi`; also :math:`\sqrt{C'^2+S'^2}=1`, so :math:`v` is signed arc length.
3. Horizontal tangents require :math:`v^2=2m`, while vertical tangents require :math:`v^2=2m+1`. Include both signs of :math:`v`; the origin itself is also a horizontal tangent.
""",
        r"Horizontal tangents: :math:`v=0,\pm\sqrt2,\pm\sqrt4,\ldots`; vertical tangents: :math:`v=\pm1,\pm\sqrt3,\ldots`.",
        r"The tangent slope repeats modulo :math:`\pi`, but the directed tangent retains the sign information of both derivatives.",
    ),
    "7.98": (
        r"""
1. For finite source and screen distances :math:`p=2\,\mathrm m`, :math:`q=3\,\mathrm m`, the reduced distance is :math:`L_{\rm eff}=pq/(p+q)=1.2\,\mathrm m`.
2. A centred slit of width :math:`b=0.25\,\mathrm{mm}` has scaled endpoints :math:`v_\pm=\pm(b/2)\sqrt{2/(\lambda L_{\rm eff})}=\pm0.208333`. The Cornu arc length is :math:`\Delta v=0.416667`.
3. At the positive endpoint, :math:`C=0.208237`, :math:`S=0.004733`. Thus :math:`I/I_0=2(C^2+S^2)=0.08677`, approximately the source's 0.09.
""",
        r"Axial irradiance :math:`0.0868I_0`; Cornu arc length :math:`0.417`.",
        r"The normalization :math:`I_0` is the unobstructed irradiance at the observation point, not necessarily the irradiance at the slit.",
    ),
    "7.99": (
        r"""
1. For plane-wave illumination the scale is :math:`v=(x-y)\sqrt{2/(\lambda z)}`. Here :math:`\sqrt{2/(640\times10^{-9}\cdot2)}=1250\,\mathrm{m}^{-1}`.
2. With slit edges :math:`x=\pm0.2\,\mathrm{mm}` and observation point :math:`y=-1\,\mathrm{mm}`, the endpoints are :math:`v_1=1.0`, :math:`v_2=1.5`.
3. The Fresnel integrals give :math:`\Delta C=0.445261-0.779893=-0.334632` and :math:`\Delta S=0.697505-0.438259=0.259246`. Therefore :math:`I/I_0=(\Delta C^2+\Delta S^2)/2=0.089594`.
""",
        r"The irradiance 1 mm below the axis is :math:`0.0896I_0`.",
        r"A symmetric slit gives the same irradiance 1 mm above the axis, although the signed Fresnel endpoints differ.",
    ),
    "7.100": (
        r"""
1. For a centred slit with scaled half-width :math:`v`, :math:`I/I_0=2[C(v)^2+S(v)^2]`.
2. Differentiate with respect to width parameter:

   .. math::

      \frac{d(I/I_0)}{dv}
      =4\left[C(v)\cos\frac{\pi v^2}{2}
      +S(v)\sin\frac{\pi v^2}{2}\right].

3. The first and largest positive maximum occurs at :math:`v\approx1.20938`, where this derivative changes from positive to negative. Evaluation gives :math:`I_{\max}/I_0\approx1.80142`; later oscillations tend toward one.
""",
        r"The greatest axial irradiance is approximately :math:`1.80I_0`.",
        r"On the Cornu diagram this is the longest chord joining the symmetric points :math:`F(-v)` and :math:`F(v)`.",
    ),
    "7.101": (
        r"""
1. Write the slit field as :math:`U(y)\propto\int_{-b/2}^{b/2}\exp[i\pi(x-y)^2/(\lambda z)]\,dx` for plane-wave incidence.
2. Expand the square: the phase contains a constant :math:`\pi y^2/(\lambda z)`, a linear term :math:`-2\pi xy/(\lambda z)`, and a quadratic term :math:`\pi x^2/(\lambda z)`. If :math:`b^2/(\lambda z)\ll1`, neglect the last term across the slit.
3. The remaining integral is :math:`b\operatorname{sinc}[\pi by/(\lambda z)]` times an irrelevant overall phase. On the Cornu spiral, the short integration arc has almost linear phase variation across the slit, and its chord develops the familiar far-field near-cancellations.
""",
        r"A narrow enough slit approaches the Fraunhofer sinc-squared pattern when its quadratic aperture phase is negligible.",
        r"A small aperture alone is not the criterion: its width must be small compared with the Fresnel scale :math:`\sqrt{\lambda z}`.",
    ),
    "7.102": (
        r"""
1. Interpret the source's wavelength typo as :math:`500\,\mathrm{nm}`, appropriate to the optical context. With :math:`p=1\,\mathrm m`, :math:`q=4\,\mathrm m`, :math:`L_{\rm eff}=pq/(p+q)=0.8\,\mathrm m`.
2. The greatest axial slit maximum from Problem 7.100 has scaled endpoints :math:`\pm1.20938`, hence :math:`\Delta v=2.41875`.
3. Convert arc length to physical width: :math:`b=\Delta v\sqrt{\lambda L_{\rm eff}/2}=2.41875\sqrt{(500\times10^{-9})(0.8)/2}=1.0817\,\mathrm{mm}`. A coarse graphical Cornu reading gives a value near the source's 1.13 mm, but numerical maximization gives 1.08 mm.
""",
        r"The numerically optimized slit width is approximately :math:`1.08\,\mathrm{mm}` for the first, largest axial maximum.",
        r"Other wider local maxima exist; stating the first/largest maximum makes the width selection unambiguous.",
    ),
    "7.103": (
        r"""
1. Opposite a straight edge, exactly one half of the unobstructed integration plane is open. In the one-dimensional Fresnel integral the aperture runs from :math:`v=0` to :math:`+\infty`.
2. Its complex Cornu displacement is :math:`F(\infty)-F(0)=(1+i)/2`, half the full-plane displacement :math:`F(\infty)-F(-\infty)=1+i`.
3. The field is therefore :math:`U=U_0/2`, and its irradiance is :math:`I=|U/U_0|^2I_0=I_0/4`.
""",
        r"At the geometrical shadow boundary, :math:`I=I_0/4`.",
        r"Half the coherent field gives one quarter of the irradiance, not one half.",
    ),
    "7.104": (
        r"""
1. Let :math:`y>0` point into the illuminated region and define :math:`v=y\sqrt{2/(\lambda z)}`. The edge profile is :math:`I/I_0=\tfrac12[(1/2+C(v))^2+(1/2+S(v))^2]`.
2. Set its derivative to zero: :math:`(1/2+C)\cos(\pi v^2/2)+(1/2+S)\sin(\pi v^2/2)=0`. The first maximum is at :math:`v=1.21720`; the next, first minimum, is at :math:`v=1.87252`.
3. With :math:`\lambda=400\,\mathrm{nm}`, :math:`z=10\,\mathrm m`, the conversion scale is :math:`\sqrt{\lambda z/2}=1.41421\,\mathrm{mm}`. Thus :math:`y_{\max}=1.721\,\mathrm{mm}` and :math:`y_{\min}=2.648\,\mathrm{mm}`. These refine the source's graphical estimates.
""",
        r"First maximum :math:`1.72\,\mathrm{mm}` into the lit side; first minimum :math:`2.65\,\mathrm{mm}` into the lit side.",
        r"There is no mirrored sequence of equal-brightness fringes deep in the shadow; the straight-edge pattern is asymmetric.",
    ),
    "7.105": (
        r"""
1. For strip width :math:`b=1.766\,\mathrm{mm}`, :math:`\lambda=693.4\,\mathrm{nm}`, :math:`z=1\,\mathrm m`, the centred complementary slit has :math:`v_\pm=\pm(b/2)\sqrt{2/(\lambda z)}=\pm1.49963`.
2. Babinet's principle gives the strip field as unobstructed field minus slit field. At the axis the normalized irradiance is

   .. math::

      \frac{I(0)}{I_0}
      =\frac{[1-2C(v)]^2+[1-2S(v)]^2}{2}.

3. With :math:`C(v)=0.445604`, :math:`S(v)=0.697647`, this is :math:`0.08405`. For a full sketch, move the endpoints together using :math:`v_{1,2}=(\mp b/2-y)\sqrt{2/(\lambda z)}` and plot :math:`\tfrac12|1+i-[F(v_2)-F(v_1)]|^2`. The curve is even, has a weak central shadow feature, and approaches unity far outside the strip.
""",
        r"The central irradiance is approximately :math:`0.084I_0`, consistent with the source's rounded :math:`0.08I_0`.",
        r"Subtract the slit field from the unobstructed complex field before squaring; subtracting slit irradiance gives a physically incorrect pattern.",
    ),
}
