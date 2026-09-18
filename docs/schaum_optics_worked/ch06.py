SOLUTIONS = {
    "6.52": (
        r"""
1. Put the two in-phase sources at :math:`(\pm1.5,0)` metres. Every point :math:`(0,y)` on their perpendicular bisector is at the same distance :math:`r=\sqrt{y^2+1.5^2}` from both sources.
2. Therefore :math:`\Delta r=0`, :math:`\delta=2\pi\Delta r/\lambda=0`, and the interference factor is constructive everywhere on this line. There is no finite destructive fringe on the stated bisector; ordinary inverse-square falloff is not an interference minimum.
3. The printed :math:`2.25\,\mathrm m` instead follows for a perpendicular line through one source: :math:`\sqrt{y^2+3^2}-y=\lambda/2=1.5`. Squaring gives :math:`9=3y+2.25`, hence :math:`y=2.25\,\mathrm m`. This is a different geometry, and unequal spherical-wave amplitudes also prevent exact cancellation there.
""",
        r"As worded, no interference minimum exists on the perpendicular bisector. The printed 2.25 m belongs to a different path-difference construction.",
        r"Always establish the two actual path lengths before substituting into a fringe condition.",
    ),
    "6.53": (
        r"""
1. For coherent vector fields, time averaging gives :math:`I=I_1+I_2+2\sqrt{I_1I_2}(\hat{\mathbf e}_1\cdot\hat{\mathbf e}_2)\cos\delta` for linear polarization unit vectors.
2. To make the interference term vanish everywhere, choose orthogonal polarization directions: :math:`\hat{\mathbf e}_1\cdot\hat{\mathbf e}_2=0`. Equal source phase alone does not guarantee equal phase at every point on the screen.
3. Then :math:`I=I_1+I_2` regardless of path difference. At an individual screen point, a phase difference :math:`\delta=(m+1/2)\pi` also makes the cross term zero, but that is a local condition rather than removal of the whole fringe pattern.
""",
        r"Orthogonal linear polarizations remove the interference term throughout the screen.",
        r"A following analyzer can project both beams onto a common polarization and restore interference.",
    ),
    "6.54": (
        r"""
1. The microwave wavelength is :math:`\lambda=c/\nu=0.30\,\mathrm m`. The source spacing is :math:`a=0.60\,\mathrm m=2\lambda`.
2. In the far field, :math:`\Delta r=a\sin\theta`, so :math:`I(\theta)=4I_0\cos^2(2\pi\sin\theta)`. Principal lobes satisfy :math:`a\sin\theta=m\lambda`, or :math:`\sin\theta=m/2`.
3. The allowed orders are :math:`m=-2,-1,0,1,2`. Over a complete angular section the maxima occur at :math:`0^\circ,30^\circ,90^\circ,150^\circ,180^\circ,210^\circ,270^\circ,330^\circ`. Minima satisfy :math:`\sin\theta=(2m+1)/4` when the right side lies in :math:`[-1,1]`.
""",
        r"Eight lobe directions in a full plane, with pattern :math:`I/(4I_0)=\cos^2(2\pi\sin\theta)`.",
        r"The pattern is symmetric under :math:`\theta\mapsto-\theta` because the emitters have equal phase.",
    ),
    "6.55": (
        r"""
1. The coherent cross term is proportional to :math:`\cos(ka\cos\vartheta)` if :math:`\vartheta` is measured from the source-separation axis. For isotropic scalar emitters its spherical average is

   .. math::

      \frac1{4\pi}\int\cos(ka\cos\vartheta)\,d\Omega
      =\frac12\int_{-1}^{1}\cos(ka\mu)\,d\mu
      =\frac{\sin(ka)}{ka}.

2. When :math:`a\gg\lambda`, this average tends to zero: bright and dark angular regions nearly balance, leaving the incoherent-sum average. It is an asymptotic result, not exactly zero for every finite separation.
3. When :math:`a\ll\lambda`, the average tends to one. Equal in-phase fields behave approximately as a single doubled-amplitude source. Holding those field amplitudes fixed requires extra work from the mutually coupled sources; the enhanced radiated power does not violate energy conservation.
""",
        r"The angularly averaged scalar cross term scales as :math:`\operatorname{sinc}(ka)` and vanishes in the large-separation limit.",
        r"One cannot simultaneously hold source amplitudes fixed and assume their required driving powers are unaffected by coherent coupling.",
    ),
    "6.56": (
        r"""
1. Define :math:`\Delta\epsilon=\epsilon_1-\epsilon_2` and choose the path-sign convention :math:`\delta=ka\sin\theta+\Delta\epsilon`.
2. Equal individual irradiances give :math:`I=2I_0(1+\cos\delta)`.
3. Use :math:`1+\cos\delta=2\cos^2(\delta/2)`:

   .. math::

      I(\theta)=4I_0\cos^2\left(
      \frac{\pi a\sin\theta}{\lambda}+\frac{\Delta\epsilon}{2}\right).

   Maxima obey :math:`ka\sin\theta+\Delta\epsilon=2\pi m`; a phase offset steers the lobe positions without moving the emitters.
""",
        r"The phase offset translates the array factor in :math:`\sin\theta`, rather than rigidly rotating all lobes by the same angle.",
        r"Setting :math:`\Delta\epsilon=0` recovers the symmetric in-phase pattern.",
    ),
    "6.57": (
        r"""
1. Problem 6.54 has :math:`a/\lambda=2`, so :math:`ka=4\pi`. Introduce :math:`\Delta\epsilon=30^\circ=\pi/6`.
2. Track the formerly forward, zeroth-order maximum by setting :math:`4\pi\sin\theta+\pi/6=0`.
3. Hence :math:`\sin\theta=-1/24` and :math:`\theta=-2.3880^\circ`. The displacement magnitude is about :math:`2^\circ23'`; reversing which emitter leads reverses the steering direction.
""",
        r"The forward lobe shifts by :math:`2.39^\circ` in magnitude.",
        r"The required geometric path phase exactly cancels the imposed :math:`30^\circ` source phase.",
    ),
    "6.58": (
        r"""
1. The referenced array has separation :math:`a=\lambda/2`, so :math:`ka=\pi`.
2. For a zeroth-order maximum at :math:`\theta_0=20^\circ`, enforce :math:`ka\sin\theta_0+\Delta\epsilon=0`.
3. Thus :math:`\Delta\epsilon=-\pi\sin20^\circ=-1.07449\,\mathrm{rad}=-61.5636^\circ`. Its magnitude is :math:`61.56^\circ`; the sign depends on the emitter labeling and desired side of broadside.
""",
        r"A relative phase magnitude of :math:`61.56^\circ` steers the central lobe by :math:`20^\circ`.",
        r"Changing phase shifts the pattern in direction cosine, so other lobes do not necessarily move by exactly :math:`20^\circ`.",
    ),
    "6.59": (
        r"""
1. Near the central axis, sources separated by :math:`a` at distance :math:`L` subtend a small angle :math:`\beta\approx a/L`.
2. Moving along the screen by :math:`dy` changes the path difference by :math:`d(\Delta r)\approx(a/L)dy=\beta\,dy`.
3. Consecutive like fringes require a path-difference increment of one wavelength: :math:`\beta\Delta y=\lambda_0`. Therefore :math:`\Delta y=\lambda_0/\beta` for an air/vacuum observation region.
""",
        r":math:`\Delta y=\lambda_0/\beta` in the paraxial limit, with :math:`\beta` in radians.",
        r"Greater apparent source separation makes the fringes closer together; in a medium use the wavelength in that medium.",
    ),
    "6.60": (
        r"""
1. Convert the wavelength: :math:`5875.618\,\text{\AA}=5.875618\times10^{-7}\,\mathrm m`. The screen distance is :math:`L=2.25\,\mathrm m` and fringe spacing :math:`\Delta y=5.0\times10^{-4}\,\mathrm m`.
2. Rearrange Young's spacing relation :math:`\Delta y=\lambda L/a` to :math:`a=\lambda L/\Delta y`.
3. Substitution gives :math:`a=(5.875618\times10^{-7})(2.25)/(5.0\times10^{-4})=2.64403\times10^{-3}\,\mathrm m`.
""",
        r"The slit separation is :math:`2.64\,\mathrm{mm}`.",
        r"The angle :math:`a/L\approx1.18\times10^{-3}` is small enough for the paraxial approximation.",
    ),
    "6.61": (
        r"""
1. For Fresnel's double mirror, let the source be distance :math:`R` from the mirrors' intersection and the small mirror angle be :math:`\alpha`.
2. The two virtual source positions lie on a circle of radius :math:`R`, separated by angle :math:`2\alpha`; their separation is :math:`a=2R\sin\alpha\approx2R\alpha`.
3. A central screen point a distance :math:`d` beyond the mirror intersection is approximately :math:`R+d` from the virtual-source plane. The angular separation is therefore :math:`\beta\approx a/(R+d)=2R\alpha/(R+d)`.
""",
        r":math:`\beta\approx2R\alpha/(R+d)` for small mirror tilt and paraxial observation.",
        r"Do not confuse the mirror angle :math:`\alpha` with the larger angular separation :math:`2\alpha` of the virtual-source radius vectors.",
    ),
    "6.62": (
        r"""
1. Convert the mirror angle to radians: :math:`\alpha=0.667\pi/180=0.0116411`. With :math:`R=0.1\,\mathrm m`, the virtual-source spacing is :math:`a\approx2R\alpha=0.00232827\,\mathrm m`.
2. The effective source-screen distance is :math:`L=R+d=1.1\,\mathrm m`. Thus :math:`\Delta y=\lambda L/a=(600\times10^{-9})(1.1)/0.00232827=0.283473\,\mathrm{mm}`.
3. The seventh bright fringe counted from the central maximum is :math:`y_7=7\Delta y=1.9843\,\mathrm{mm}`; the opposite side has :math:`y_{-7}=-y_7`.
""",
        r"The seventh bright fringe is about :math:`1.98\,\mathrm{mm}` from the axis.",
        r"Use the source-to-screen distance :math:`R+d`, not just the mirror-to-screen distance :math:`d`.",
    ),
    "6.63": (
        r"""
1. A thin biprism of small refracting angle :math:`\alpha` deviates each half beam by :math:`\delta\approx(n-1)\alpha`.
2. With source distance :math:`R=1\,\mathrm m`, the virtual-source separation is :math:`a=2R(n-1)\alpha`. The screen is :math:`R+d=6\,\mathrm m` from that virtual-source plane.
3. Solve :math:`\Delta y=\lambda(R+d)/[2R(n-1)\alpha]`:

   .. math::

      \alpha=\frac{(500\times10^{-9})(6)}{2(1)(0.5)(0.6\times10^{-3})}
      =0.005\,\mathrm{rad}=0.28648^\circ.

   This value follows from the stated 1 m, 5 m, and 0.6 mm data; a different printed angle does not reproduce that spacing.
""",
        r"Each small biprism angle is :math:`\alpha\approx0.286^\circ` for the supplied distances.",
        r"The resulting source separation is 5 mm, and :math:`500\,\mathrm{nm}\times6\,\mathrm m/5\,\mathrm{mm}=0.6\,\mathrm{mm}`.",
    ),
    "6.64": (
        r"""
1. For a prism of index :math:`n_g` immersed in liquid :math:`n_l`, the small-angle Snell relation gives :math:`\delta\approx(n_g/n_l-1)\alpha`.
2. The two virtual sources are separated by :math:`a=2R\delta=2R(n_g-n_l)\alpha/n_l`. If the whole interference region is immersed, its wavelength is :math:`\lambda_l=\lambda_0/n_l`.
3. Substitute both changes, not just the new deviation:

   .. math::

      \Delta y=\frac{\lambda_l(R+d)}a
      =\frac{\lambda_0(R+d)}{2R(n_g-n_l)\alpha}.

   If a formula is expressed using :math:`\lambda_l` instead, its numerator is :math:`n_l\lambda_l(R+d)`. An extra :math:`n_l` multiplying a vacuum wavelength would count the wavelength conversion incorrectly.
""",
        r"For a fully immersed setup, :math:`\Delta y=\lambda_0(R+d)/[2R(n_g-n_l)\alpha]`.",
        r"As the indices match, source splitting vanishes and fringe spacing diverges. A setup with liquid only around the prism requires its actual exit geometry.",
    ),
    "6.65": (
        r"""
1. Replacing air by a plate of thickness :math:`t` adds optical path :math:`(n-1)t` to the direct beam at near-normal incidence.
2. The Lloyd-mirror reflection already supplies a relative :math:`\pi` phase. The zero-geometric-OPD dark fringe therefore moves until the original path imbalance cancels the plate's added path; in the source geometry it moves upward.
3. Each fringe displacement represents an OPD change :math:`\lambda_0`, so the shift is :math:`N=(n-1)t/\lambda_0` fringes. With broadband illumination the equal-total-OPD fringe is approximately achromatic, helping identify it among the coloured neighbouring fringes.
""",
        r"The central dark fringe shifts upward by :math:`(n-1)t/\lambda_0` fringe spacings in the illustrated geometry.",
        r"The direction depends on which beam receives the plate; insertion into the reflected arm would reverse it. Dispersion limits perfect white-light compensation.",
    ),
    "6.66": (
        r"""
1. The mirror's virtual source lies the same distance below the surface as the real source lies above it. If the source height is :math:`h`, their separation is :math:`a=2h`.
2. The fringe spacing is :math:`\Delta y=\lambda L/(2h)`, unaffected by the half-order shift caused by reflection.
3. Solve for height: :math:`h=(500\times10^{-9})(2)/[2(0.667\times10^{-3})]=7.4963\times10^{-4}\,\mathrm m`.
""",
        r"The source is approximately :math:`0.750\,\mathrm{mm}` above the reflecting surface.",
        r"The reflection changes whether the central fringe is bright or dark, but not the separation of consecutive bright fringes.",
    ),
    "6.67": (
        r"""
1. Each displaced half of the convex lens forms a real image of the same point source. For object and image distances :math:`s_o,s_i`, the common conjugate relation is :math:`1/f=1/s_o+1/s_i`.
2. A lens half displaced transversely by :math:`h` images the on-axis object at :math:`y_i=h(1+s_i/s_o)`. Thus equal and opposite half displacements create two real image sources with a controlled separation.
3. After those foci the beams diverge and overlap. Because both came from the same source through symmetric paths, they interfere with :math:`I=I_1+I_2+2\sqrt{I_1I_2}\cos(2\pi\Delta r/\lambda)`. At a distant screen their fringe spacing is approximately :math:`\lambda L/a`.
""",
        r"Billet's split lens makes two coherent real image sources; fringes appear only where their outgoing beams overlap.",
        r"Unlike the Fresnel biprism's virtual sources, these intermediate image points are real foci traversed by the rays.",
    ),
    "6.68": (
        r"""
1. The film thickness is :math:`t=0.002\,\mathrm{mm}=2000\,\mathrm{nm}`. Snell's law gives :math:`\sin\theta_t=\sin30^\circ/1.5=1/3`, so :math:`\cos\theta_t=2\sqrt2/3`.
2. The round-trip optical path contributing to the reflected phase difference is :math:`2nt\cos\theta_t=5656.85\,\mathrm{nm}`; its propagation phase is :math:`4\pi nt\cos\theta_t/\lambda_0=22.6274\pi`.
3. Air-film reflection reverses phase while film-air reflection does not. Add one :math:`\pi`: :math:`\delta=23.6274\pi`, equivalent to :math:`1.6274\pi` modulo :math:`2\pi`.
""",
        r"The relative reflected phase is :math:`1.63\pi` modulo :math:`2\pi`.",
        r"Using :math:`2nt/\cos\theta_t` alone misses the lateral wavefront compensation and gives an incorrect thin-film phase.",
    ),
    "6.69": (
        r"""
1. Let :math:`\lambda_f=\lambda_0/n_f`. For a film with exactly one reflected phase reversal, :math:`\delta=4\pi t\cos\theta_t/\lambda_f+\pi`.
2. A reflected maximum requires :math:`\delta=2\pi q`; therefore :math:`t\cos\theta_t=(2q-1)\lambda_f/4`. Relabel :math:`m=q-1\ge0`.
3. A minimum requires :math:`\delta=(2q+1)\pi`, giving :math:`t\cos\theta_t=q\lambda_f/2`. Thus maxima are at odd quarter-wave thicknesses and minima at integer half-wave thicknesses.
""",
        r"Maxima: :math:`t\cos\theta_t=(2m+1)\lambda_f/4`; minima: :math:`t\cos\theta_t=2m\lambda_f/4`.",
        r"With zero or two relative reflection reversals, the bright and dark conditions interchange.",
    ),
    "6.70": (
        r"""
1. The printed thickness is :math:`2.5\,\mathrm{mm}`; OCR can misread it as 2.6 mm. At the centre :math:`\theta_t=0`, with :math:`n=1.5` and :math:`\lambda_0=750\,\mathrm{nm}`.
2. The round-trip order is :math:`m=2nt/\lambda_0=2(1.5)(2.5\times10^{-3})/(750\times10^{-9})=10000`.
3. This integer propagation order supplies :math:`2\pi m`; the additional single reflection reversal makes the reflected beams antiphase. The central fringe is therefore a reflected minimum.
""",
        r"The central reflected fringe is a minimum of round-trip order :math:`10000`.",
        r"At the same setting, transmission is maximal in an ideal lossless plate; bright/dark labels must specify the observed port.",
    ),
    "6.71": (
        r"""
1. A single quarter-wave layer must satisfy two independent conditions: opposite reflected phases and equal reflected amplitudes.
2. At normal incidence, amplitude matching between air :math:`n_0=1` and substrate :math:`n_s=2.409` gives :math:`n_f^2=n_0n_s`, hence :math:`n_f=\sqrt{2.409}=1.55210`.
3. The least positive odd-quarter-wave thickness is :math:`t=\lambda_0/(4n_f)=589/[4(1.55210)]=94.87\,\mathrm{nm}`. These choices make the net reflection vanish at the design wavelength for ideal real indices.
""",
        r"Design index :math:`n_f\approx1.552`; thickness :math:`t\approx94.9\,\mathrm{nm}`.",
        r"A quarter-wave thickness alone is not sufficient for zero reflectance unless the layer index also matches the geometric mean.",
    ),
    "6.72": (
        r"""
1. At near-normal incidence the destructive-reflection design uses an odd quarter-wave optical thickness: :math:`n_ft=(2m+1)\lambda_0/4`.
2. Choose :math:`m=0` for the thinnest coating and use :math:`n_f=1.38`, :math:`\lambda_0=589\,\mathrm{nm}`.
3. This gives :math:`t=589/(4\cdot1.38)=106.703\,\mathrm{nm}`. It minimizes reflection at the design wavelength, but exact cancellation additionally requires an appropriate substrate index.
""",
        r"The thinnest magnesium-fluoride layer is :math:`106.7\,\mathrm{nm}`.",
        r"Its optical thickness is :math:`147.25\,\mathrm{nm}=589/4`, whereas its geometric thickness is smaller by :math:`n_f`.",
    ),
    "6.73": (
        r"""
1. For a small wedge angle :math:`\alpha`, film thickness grows as :math:`t(x)\approx\alpha x`.
2. Consecutive same-type reflected fringes differ in thickness by :math:`\Delta t=\lambda_0/(2n_f)`, so :math:`\Delta x=\lambda_0/(2n_f\alpha)`.
3. Substitute :math:`n_f=1.3290`, :math:`\lambda_0=589\,\mathrm{nm}`, :math:`\Delta x=0.2\,\mathrm{mm}`: :math:`\alpha=0.00110798\,\mathrm{rad}=0.06348^\circ`.
""",
        r"The wedge angle is approximately :math:`0.0635^\circ`.",
        r"The radian angle is much smaller than one, so :math:`\tan\alpha\approx\alpha` is justified.",
    ),
    "6.74": (
        r"""
1. The apex is dark because the film has zero thickness and one relative reflection phase reversal. The first bright fringe is at :math:`t=\lambda_0/(4n_f)`.
2. Counting the fourth bright fringe from the apex gives the odd factor 7: :math:`t_4=7\lambda_0/(4n_f)=7(589)/(4\cdot1.3290)=775.58\,\mathrm{nm}`.
3. Bright positions are halfway between consecutive dark positions. With :math:`\Delta x=0.2\,\mathrm{mm}`, :math:`x_4=(4-1/2)\Delta x=0.700\,\mathrm{mm}`; equivalently :math:`x_4=t_4/\alpha`.
""",
        r"The fourth maximum occurs at thickness :math:`7.76\times10^{-7}\,\mathrm m`, :math:`0.700\,\mathrm{mm}` from the apex.",
        r"Counting the first bright fringe as order zero prevents an off-by-one half-wave error.",
    ),
    "6.75": (
        r"""
1. At fixed bright-ring order and lens curvature, Newton's ring equation has :math:`r_m^2\propto1/n`; the same scaling holds for squared diameter.
2. Divide the before/after equations to remove wavelength, curvature, and order: :math:`n_{\rm liquid}/n_{\rm air}=D_{\rm air}^2/D_{\rm liquid}^2`.
3. With :math:`D_{\rm air}=2.52\,\mathrm{cm}`, :math:`D_{\rm liquid}=2.21\,\mathrm{cm}`, and :math:`n_{\rm air}\approx1`, :math:`n=(2.52/2.21)^2=1.30023`.
""",
        r"The liquid index is approximately :math:`1.30`.",
        r"A liquid with index greater than air shrinks the rings, matching the observed diameter decrease.",
    ),
    "6.76": (
        r"""
1. Allow an unknown central film gap :math:`t_0`, since the centre is bright rather than the usual contact dark. The gap profile is :math:`t(r)=t_0+r^2/(2R)`.
2. Subtract the dark-ring conditions at orders 85 and 5. The unknown :math:`t_0` and any common order offset cancel, giving :math:`r_{85}^2-r_5^2=80\lambda R` for an air gap.
3. Therefore :math:`R=[(0.01871)^2-(0.01414)^2]/[80(550\times10^{-9})]=3.411\,\mathrm m`.
""",
        r"The convex lens radius is approximately :math:`3.41\,\mathrm m`.",
        r"Using radius-squared differences avoids assuming perfect contact or assigning an absolute order to the bright centre.",
    ),
    "6.77": (
        r"""
1. The opposing spherical sags are approximately :math:`r^2/(2R_1)` and :math:`r^2/(2R_2)`. With :math:`R_2>R_1`, the air gap is :math:`t(r)=\tfrac12r^2(1/R_1-1/R_2)`.
2. Reflected dark rings with one phase reversal satisfy :math:`2t=m\lambda_0`.
3. Substitute the sag difference and solve:

   .. math::

      r_m=\sqrt{\frac{m\lambda_0}{1/R_1-1/R_2}}
      =\sqrt{\frac{m\lambda_0R_1R_2}{R_2-R_1}}.

""",
        r":math:`r_m=\sqrt{m\lambda_0R_1R_2/(R_2-R_1)}` for a contacting air film.",
        r"Letting :math:`R_2\to\infty` recovers the standard plano-convex Newton-ring result :math:`r_m^2=m\lambda_0R_1`.",
    ),
    "6.78": (
        r"""
1. Follow a fixed Michelson ring order :math:`m` satisfying :math:`2d\cos\theta_m=m\lambda_0`, where :math:`d` is the arm-length difference.
2. Solve :math:`\cos\theta_m=m\lambda_0/(2d)`. As positive :math:`d` decreases, the right side increases, so :math:`\theta_m` decreases and the ring radius shrinks.
3. The ring reaches the axis at :math:`d=m\lambda_0/2`, where :math:`\theta_m=0`. For smaller :math:`d`, the same order has no real angle and disappears; successive orders collapse in turn as equal arms are approached.
""",
        r"Each fixed-order ring contracts to the centre and disappears as its allowed arm difference is crossed.",
        r"A given nonzero order reaches the centre before :math:`d=0`; it cannot be followed continuously all the way to equal arms.",
    ),
    "6.79": (
        r"""
1. The two vacuum wavelengths are :math:`\lambda_1=589.5923\,\mathrm{nm}` and :math:`\lambda_2=588.9953\,\mathrm{nm}`, separated by :math:`0.5970\,\mathrm{nm}`.
2. For mirror displacement :math:`x`, the OPD changes by :math:`2x`. The phase difference between the two fringe systems changes by :math:`4\pi x(1/\lambda_2-1/\lambda_1)`.
3. A visibility maximum becomes a minimum when this phase difference reaches :math:`\pi`. Hence :math:`x=\lambda_1\lambda_2/[4(\lambda_1-\lambda_2)]\approx0.14542\,\mathrm{mm}`.
""",
        r"Move the mirror approximately :math:`0.1454\,\mathrm{mm}` from maximum to minimum visibility.",
        r"Maximum-to-maximum travel is twice as large; the optical-path change is itself twice the mirror travel.",
    ),
    "6.80": (
        r"""
1. Moving one Michelson mirror through :math:`x` changes the round-trip optical path by :math:`2x`.
2. Each passing bright fringe represents one wavelength of OPD, so :math:`N=2x/\lambda_0` and :math:`x=N\lambda_0/2`.
3. With :math:`N=10000` and :math:`\lambda_0=605.7802105\,\mathrm{nm}`, :math:`x=3028901.0525\,\mathrm{nm}=3.028901\,\mathrm{mm}`.
""",
        r"The mirror must travel :math:`3.0289\,\mathrm{mm}`.",
        r"A result twice as large would forget that the beam traverses the moving arm twice.",
    ),
    "6.81": (
        r"""
1. A dark centre has some axial order :math:`m_0=2d/\lambda_0`. At increasing angle the order decreases, so the :math:`p`th surrounding dark ring has :math:`m=m_0-p`.
2. Subtract :math:`2d\cos\theta_p=(m_0-p)\lambda_0` from the axial equation :math:`2d=m_0\lambda_0` to obtain :math:`2d(1-\cos\theta_p)=p\lambda_0`.
3. For small angle, :math:`1-\cos\theta_p\approx\theta_p^2/2`; hence :math:`\theta_p\approx\sqrt{p\lambda_0/d}`.
""",
        r"Exact: :math:`\cos\theta_p=1-p\lambda_0/(2d)`; paraxial: :math:`\theta_p\approx\sqrt{p\lambda_0/d}`.",
        r"Ring number counted outward is not the same as absolute interference order; the latter decreases outward.",
    ),
    "6.82": (
        r"""
1. Use :math:`p=15`, :math:`d=1\,\mathrm{cm}=0.01\,\mathrm m`, and :math:`\lambda_0=400\,\mathrm{nm}`.
2. The small-angle expression gives :math:`\theta_{15}=\sqrt{15(400\times10^{-9})/0.01}=0.0244949\,\mathrm{rad}`.
3. Converting to degrees gives :math:`1.40345^\circ\approx1^\circ24'`. The exact expression :math:`\arccos[1-15\lambda_0/(2d)]` changes this only slightly.
""",
        r"The fifteenth dark ring subtends a half-angle of about :math:`1.40^\circ`.",
        r"This is the angular radius of the ring; its full angular diameter is twice this value.",
    ),
    "6.83": (
        r"""
1. In the Jamin arrangement the test cell is traversed once. Replacing vacuum by gas adds OPD :math:`(n-1)L`, where :math:`L=0.35\,\mathrm m`.
2. The 75 observed fringe passages imply :math:`(n-1)L=75\lambda_0`.
3. Thus :math:`n=1+75(650\times10^{-9})/0.35=1.000139286`.
""",
        r"The gas refractive index is :math:`n\approx1.000139`.",
        r"Do not import the Michelson factor of two into this single-pass cell measurement.",
    ),
    "6.84": (
        r"""
1. The first beam splitter divides the incident field into two spatially separated arms. Each arm reflects from its own mirror, and the second beam splitter overlaps their fields.
2. Their relative phase is :math:`\delta(x,y)=2\pi\,\mathrm{OPD}(x,y)/\lambda+\delta_{\rm BS}`. At either output the irradiance has the form :math:`I_1+I_2+2\sqrt{I_1I_2}\cos\delta`; the other output is complementary for a balanced lossless system.
3. A slight relative mirror tilt adds an approximately linear phase ramp, producing straight carrier fringes. A specimen in one arm changes :math:`\mathrm{OPD}=\int(n-n_{\rm ref})\,ds`; fringe shifts then map refractive-index variations, for example in gas flows or a wind tunnel.
""",
        r"The Mach–Zehnder is a two-arm, single-pass amplitude-splitting interferometer, closely related in measurement purpose to the Jamin arrangement.",
        r"Both path matching within the coherence length and spatial/polarization overlap at the second splitter are needed for visible fringes.",
    ),
    "6.85": (
        r"""
1. At :math:`\lambda=1153\,\mathrm{nm}`, the optical frequency is :math:`\nu=c/\lambda\approx2.60\times10^{14}\,\mathrm{Hz}`.
2. In the source's estimate, identify the quoted fractional frequency spread :math:`s=8\times10^{-14}` with :math:`\Delta\nu/\nu`. This gives :math:`\Delta\nu=s\nu\approx20.8\,\mathrm{Hz}`.
3. Using the order-of-magnitude convention :math:`\tau_c\sim1/\Delta\nu`, obtain :math:`\tau_c\approx0.0480\,\mathrm s` and :math:`L_c=c\tau_c\approx1.44\times10^7\,\mathrm m`.
""",
        r"The wave-train estimate is :math:`\tau_c\approx4.8\times10^{-2}\,\mathrm s`, :math:`L_c\approx14.4\,\mathrm{Mm}`.",
        r"A measured frequency-stability statistic is not automatically a spectral linewidth; rigorous coherence requires the frequency-noise spectrum and a specified linewidth/coherence convention.",
    ),
    "6.86": (
        r"""
1. For a wave train of duration :math:`\tau=10^{-8}\,\mathrm s`, estimate :math:`\Delta\nu\sim1/\tau=10^8\,\mathrm{Hz}`.
2. Differentiate :math:`\nu=c/\lambda` in magnitude: :math:`\Delta\lambda\approx\lambda^2\Delta\nu/c`. With :math:`\lambda=650\,\mathrm{nm}`, :math:`\Delta\lambda\approx1.41\times10^{-13}\,\mathrm m=1.41\times10^{-4}\,\mathrm{nm}`.
3. The coherence length in this convention is :math:`L_c=c\tau\approx3.0\,\mathrm m`.
""",
        r"Approximate linewidth :math:`10^8\,\mathrm{Hz}` or :math:`1.41\times10^{-4}\,\mathrm{nm}`; coherence length :math:`3\,\mathrm m`.",
        r"Numerical factors such as :math:`\pi` depend on the assumed line shape and the exact definition of coherence time; these are wave-train estimates.",
    ),
    "6.87": (
        r"""
1. A train of 50 wavelengths has :math:`L_c=50\lambda=50(650\,\mathrm{nm})=32.5\,\mathrm{\mu m}`.
2. From :math:`L_c\sim\lambda^2/\Delta\lambda`, the filter bandwidth is :math:`\Delta\lambda\sim\lambda/50=13\,\mathrm{nm}`.
3. In a Michelson interferometer, mirror displacement :math:`x` introduces :math:`2x` OPD. Starting at matched paths, appreciable overlap is lost on the scale :math:`x\sim L_c/2=16.25\,\mathrm{\mu m}=0.01625\,\mathrm{mm}`.
""",
        r"Bandwidth about :math:`13\,\mathrm{nm}`; one-sided mirror travel from equal paths about :math:`16.25\,\mathrm{\mu m}`.",
        r"This is a coherence scale, not a sharp universal visibility cutoff for every filter profile.",
    ),
    "6.88": (
        r"""
1. The number of optical cycles in a train is :math:`N=\nu\tau_c`, equivalently :math:`N=L_c/\lambda`.
2. Use the bandwidth estimate :math:`\tau_c\sim1/\Delta\nu`, giving :math:`N\sim\nu/\Delta\nu`.
3. If the fractional spectral width is :math:`s=\Delta\nu/\nu`, then :math:`N\sim1/s`. A fractional width of :math:`10^{-6}`, for example, corresponds to roughly a million optical cycles per train in this model.
""",
        r":math:`N\sim(\Delta\nu/\nu)^{-1}`.",
        r"This statement concerns a spectral-width interpretation of stability; drift and short-term noise measures need not equal that width.",
    ),
    "6.89": (
        r"""
1. The filter has central wavelength :math:`\lambda=550\,\mathrm{nm}` and narrow passband :math:`\Delta\lambda=1.5\,\mathrm{nm}`.
2. Compute :math:`L_c\sim\lambda^2/\Delta\lambda=550^2/1.5\,\mathrm{nm}=201666.7\,\mathrm{nm}=2.0167\times10^{-4}\,\mathrm m`.
3. The number of wavelengths is :math:`N=L_c/\lambda=550/1.5=366.67`.
""",
        r"Coherence length approximately :math:`0.202\,\mathrm{mm}`, containing about 367 wavelengths.",
        r":math:`\Delta\lambda/\lambda\approx0.0027\ll1`, so the narrowband frequency-to-wavelength conversion is valid.",
    ),
    "6.90": (
        r"""
1. Model the star as a uniformly bright circular disk of angular diameter :math:`\phi`. Its two-aperture visibility is :math:`V=|2J_1(\pi h\phi/\lambda)/(\pi h\phi/\lambda)|`.
2. The first zero of :math:`J_1` is 3.8317, so the first vanished-fringe baseline obeys :math:`h_0\phi/\lambda=3.8317/\pi=1.21967`.
3. Convert :math:`h_0=121\,\mathrm{in}=3.0734\,\mathrm m`, then :math:`\phi=1.21967(570\times10^{-9})/3.0734=2.262\times10^{-7}\,\mathrm{rad}`. This is :math:`1.296\times10^{-5}\,\mathrm{deg}` or :math:`0.0467` arcsec.
""",
        r"Uniform-disk angular diameter :math:`\phi\approx2.26\times10^{-7}\,\mathrm{rad}=0.0467` arcsec.",
        r"The factor 1.22 depends on a circular uniform-disk brightness model; limb darkening changes the inferred physical diameter.",
    ),
    "6.91": (
        r"""
1. Keep the wavelength 1153 nm, hence :math:`\nu\approx2.60\times10^{14}\,\mathrm{Hz}`. Interpret the new :math:`6\times10^{-16}` fractional spread with the same heuristic as Problem 6.85.
2. The estimated width is :math:`\Delta\nu\approx0.156\,\mathrm{Hz}`, giving :math:`\tau_c\sim1/\Delta\nu\approx6.41\,\mathrm s`.
3. The ratio of inferred coherence times is the inverse ratio of fractional spreads: :math:`\tau_{1973}/\tau_{1963}=(8\times10^{-14})/(6\times10^{-16})=133.3`. The quoted 100 s stability interval is the observation interval, not itself the coherence time.
""",
        r"The source's estimate increases from about :math:`0.048\,\mathrm s` to :math:`6.4\,\mathrm s`, a factor of 133.",
        r"This historical comparison assumes the quoted stability values represent comparable spectral widths; it is not a general conversion rule for laser stability specifications.",
    ),
}
