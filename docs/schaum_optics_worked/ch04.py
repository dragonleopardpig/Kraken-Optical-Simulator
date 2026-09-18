SOLUTIONS = {
    "4.62": (
        r"""
1. Put the vertex at :math:`(0,0)`, a real source at :math:`(-s_o,0)`, and the desired real image at :math:`(s_i,0)`. Here :math:`s_o,s_i>0` are geometric distances, not signed Cartesian coordinates.
2. For a surface point :math:`Q=(x,y)`, Pythagoras gives :math:`SQ=\sqrt{(x+s_o)^2+y^2}` and :math:`QP=\sqrt{(s_i-x)^2+y^2}`. Multiply each length by its medium's index.
3. Equal optical path through every surface point, including the vertex, requires

   .. math::

      n_i\sqrt{(x+s_o)^2+y^2}+n_t\sqrt{(s_i-x)^2+y^2}
      =n_is_o+n_ts_i.

   This implicit curve is the Cartesian oval. Rotation about the source-image axis gives the refracting surface; differentiating its constant optical path gives Snell's law.
""",
        r"The weighted-distance equation above defines the stigmatic interface.",
        r"Setting :math:`x=y=0` recovers the vertex optical path. Virtual endpoints require signed optical lengths rather than blindly reusing positive distances.",
    ),
    "4.63": (
        r"""
1. A plane wave travelling along :math:`+x` reaches the surface point :math:`(x,y)` after an extra incident optical distance :math:`n_ix`. Equal path to the focus :math:`(s_i,0)` requires :math:`n_ix+n_t\sqrt{(s_i-x)^2+y^2}=n_ts_i`.
2. Isolate the square root, square, and collect terms:

   .. math::

      (n_t^2-n_i^2)x^2-2n_ts_i(n_t-n_i)x+n_t^2y^2=0.

3. For :math:`n_t>n_i`, divide by :math:`n_t^2-n_i^2` and complete the square. With :math:`a=n_ts_i/(n_t+n_i)` and :math:`b=s_i\sqrt{(n_t-n_i)/(n_t+n_i)}`, the equation is :math:`(x-a)^2/a^2+y^2/b^2=1`. Consequently :math:`e=\sqrt{1-b^2/a^2}=n_i/n_t`.
""",
        r"An ellipsoid of revolution, with :math:`a=n_ts_i/(n_t+n_i)`, :math:`b=s_i\sqrt{(n_t-n_i)/(n_t+n_i)}`, and :math:`e=n_i/n_t`.",
        r"Retain only the branch satisfying the unsquared optical-path equation; squaring alone can introduce an unphysical branch.",
    ),
    "4.64": (
        r"""
1. The apparent focus lies at :math:`s_i<0`. For a diverging transmitted wave, subtract its distance to the virtual focus: :math:`n_ix-n_t\sqrt{(x-s_i)^2+y^2}=n_ts_i`.
2. Squaring gives the same polynomial as in Problem 4.63. Now :math:`n_i>n_t`, so the coefficients of :math:`x^2` and :math:`y^2` have opposite signs.
3. Define :math:`a=|n_ts_i|/(n_i+n_t)`, :math:`b=|s_i|\sqrt{(n_i-n_t)/(n_i+n_t)}`, and :math:`x_c=n_ts_i/(n_i+n_t)`. Completing the square gives

   .. math::

      \frac{(x-x_c)^2}{a^2}-\frac{y^2}{b^2}=1,
      \qquad e=\sqrt{1+b^2/a^2}=\frac{n_i}{n_t}>1.

   Choose the sheet passing through the vertex and satisfying the unsquared equation.
""",
        r"A hyperboloid of revolution with eccentricity :math:`n_i/n_t` and a virtual focus at :math:`P`.",
        r"The change from ellipse to hyperbola follows from the sign of :math:`n_t^2-n_i^2`, not from a change in Snell's law.",
    ),
    "4.65": (
        r"""
1. Orient the axis along light leaving the diamond. The flaw is at the centre of curvature, so :math:`s_o=20\,\mathrm{cm}` and :math:`R=-20\,\mathrm{cm}`.
2. Apply the spherical-interface equation with :math:`n_i=2.42`, :math:`n_t=1.33`:

   .. math::

      \frac{2.42}{20}+\frac{1.33}{s_i}
      =\frac{1.33-2.42}{-20}=0.0545,
      \qquad s_i=-20\,\mathrm{cm}.

3. All rays from the centre strike the sphere normally and therefore keep their directions. Their backward extensions still meet at the original flaw, giving a virtual image there.
""",
        r":math:`s_i=-20\,\mathrm{cm}`; the image coincides with the flaw.",
        r"The geometric normal-incidence argument is exact, not merely paraxial, and is independent of the surrounding refractive index.",
    ),
    "4.66": (
        r"""
1. The right hyperboloid has :math:`e=n_{\rm glass}/n_{\rm air}=1.5`. Its specified virtual focus is therefore the image of a collimated beam travelling inside the rod.
2. The left hemisphere has :math:`R=5\,\mathrm{cm}`. Demand :math:`s_i\to\infty` at this first air-glass interface:

   .. math::

      \frac{1}{s_o}+\frac{1.5}{\infty}
      =\frac{1.5-1}{5},\qquad s_o=10\,\mathrm{cm}.

3. Put the source at this object focal point. Refraction at the hemisphere produces the paraxial parallel bundle; the hyperboloid then makes it appear to diverge from its first focus, 5 cm left of its vertex.
""",
        r"Place the source :math:`10\,\mathrm{cm}` to the left of the spherical vertex.",
        r"The spherical entrance is only paraxially collimating; a finite-aperture spherical entrance still has spherical aberration.",
    ),
    "4.67": (
        r"""
1. At the near surface, the ant is :math:`s_o=6-4=2\,\mathrm{cm}` from the vertex. The centre is on the transmitted side, hence :math:`R=+4\,\mathrm{cm}`.
2. Use alcohol as the incident medium and glass as the transmitted medium:

   .. math::

      \frac{1.36}{2}+\frac{1.50}{s_i}
      =\frac{1.50-1.36}{4}=0.035,
      \qquad s_i=\frac{1.50}{-0.645}=-2.326\,\mathrm{cm}.

3. The transverse magnification of a refracting surface is :math:`M_T=-n_is_i/(n_ts_o)=1.054`. The first-surface image is virtual, upright, and slightly enlarged.
""",
        r"The near interface forms a virtual image :math:`2.33\,\mathrm{cm}` outside its vertex, with :math:`M_T\approx1.05`.",
        r"This is the image formed by the first interface. Observing through the entire sphere would require a second refraction.",
    ),
    "4.68": (
        r"""
1. The real object and image give :math:`s_o=40\,\mathrm{cm}`, :math:`s_i=80\,\mathrm{cm}`, with :math:`n_i=1`, :math:`n_t=2`.
2. Rearrange the surface equation to isolate curvature:

   .. math::

      R=\frac{n_t-n_i}{n_i/s_o+n_t/s_i}
      =\frac{1}{1/40+2/80}=20\,\mathrm{cm}.

3. The positive sign places the centre of curvature in the second medium; this is a convex entrance surface as seen by the incident rays.
""",
        r":math:`R=+20\,\mathrm{cm}`.",
        r"Both terms on the left of the conjugate equation are positive, consistent with a positive refracting power.",
    ),
    "4.69": (
        r"""
1. Let the smaller radius magnitude be :math:`R`. A double-convex lens has opposite signed radii; take :math:`R_1=2R`, :math:`R_2=-R`.
2. The thin-lens maker equation in air is

   .. math::

      \frac1f=(1.5-1)\left(\frac1{2R}-\frac1{-R}\right)
      =\frac{3}{4R}.

3. Multiply by :math:`fR` to obtain :math:`R=3f/4`. Reversing the lens interchanges the magnitudes but leaves its thin-lens power unchanged.
""",
        r"The smaller radius magnitude is :math:`3f/4`; the larger is :math:`3f/2`.",
        r"Using two positive signed radii would describe a meniscus, not the specified biconvex lens.",
    ),
    "4.70": (
        r"""
1. If the lens is :math:`s` from the source, its distance to the screen is :math:`L-s`. Real imaging requires :math:`0<s<L`.
2. Substitute in the thin-lens equation: :math:`1/f=1/s+1/(L-s)=L/[s(L-s)]`. Thus :math:`s^2-Ls+fL=0`.
3. Solve the quadratic:

   .. math::

      s_\pm=\frac{L\pm\sqrt{L(L-4f)}}2.

   Two different positions exist for :math:`L>4f`; they merge at :math:`s=2f` for :math:`L=4f`. No real lens placement works for :math:`L<4f`.
""",
        r":math:`s_\pm=[L\pm\sqrt{L(L-4f)}]/2`.",
        r"The two roots sum to :math:`L`, so exchanging the object and image distances exchanges the two positions.",
    ),
    "4.71": (
        r"""
1. An equiconvex lens has :math:`R_1=R`, :math:`R_2=-R` in the left-to-right sign convention.
2. With :math:`n=1.65`, the lens maker equation becomes :math:`1/f=0.65(2/R)=1.30/R`.
3. For :math:`f=62\,\mathrm{cm}`, :math:`R=1.30(62)=80.6\,\mathrm{cm}`. Assign the signs only after calculating the common magnitude.
""",
        r":math:`R_1=+80.6\,\mathrm{cm}`, :math:`R_2=-80.6\,\mathrm{cm}`.",
        r"Substitution gives :math:`0.65(1/80.6+1/80.6)=1/62\,\mathrm{cm}^{-1}`.",
    ),
    "4.72": (
        r"""
1. A converging incident bundle has a virtual object on the transmitted side. Write :math:`s_o=-a` with :math:`a>0`; write the negative lens focal length as :math:`f=-F`, :math:`F>0`.
2. The lens equation gives

   .. math::

      -\frac1F=-\frac1a+\frac1{s_i},\qquad
      s_i=\frac{aF}{F-a}.

3. If :math:`a<F`, then :math:`s_i>0` and :math:`s_i/a=F/(F-a)>1`. Also :math:`M_T=-s_i/s_o=F/(F-a)>1`. The lens weakens the convergence, so the focus moves farther away but remains real.
""",
        r"For :math:`|s_o|<|f|`, the image is real, erect relative to the virtual object, and enlarged.",
        r"At :math:`a=F` the emerging light is parallel; for :math:`a>F` it diverges and the image is virtual.",
    ),
    "4.73": (
        r"""
1. The requested scale factor is :math:`2000/20=3000/30=100`. A real projected image is inverted, so :math:`M_T=-100`.
2. With the wall :math:`s_i=10\,\mathrm m` from the lens, :math:`M_T=-s_i/s_o` gives :math:`s_o=10/100=0.10\,\mathrm m`.
3. Calculate the focal length without rounding the reciprocal terms:

   .. math::

      f=\frac{s_os_i}{s_o+s_i}
      =\frac{0.10(10)}{10.10}=0.09901\,\mathrm m.

""",
        r"Place the slide :math:`10\,\mathrm{cm}` from a lens with :math:`f\approx99.0\,\mathrm{mm}`.",
        r"The slide is just beyond the front focal plane, as required for a large real projection.",
    ),
    "4.74": (
        r"""
1. The image is erect, so its signed magnification is :math:`M_T=8/5=+1.6`.
2. With a real object :math:`s_o=90\,\mathrm{cm}`, :math:`s_i=-M_Ts_o=-144\,\mathrm{cm}`. The negative image distance means a virtual image on the object's side.
3. Substitute both signed distances:

   .. math::

      \frac1f=\frac1{90}-\frac1{144}=\frac1{240},
      \qquad f=240\,\mathrm{cm}.

""",
        r":math:`f=240\,\mathrm{cm}` and :math:`s_i=-144\,\mathrm{cm}`.",
        r":math:`s_o<f`, exactly the regime in which a positive lens forms an enlarged upright virtual image.",
    ),
    "4.75": (
        r"""
1. Convert the object height to millimetres: :math:`h_o=1000\,\mathrm{mm}`. The inverted film image has :math:`M_T=-25/1000=-0.025`, so :math:`s_i=0.025s_o`.
2. Substitute into :math:`1/50=1/s_o+1/(0.025s_o)=41/s_o`, obtaining :math:`s_o=2050\,\mathrm{mm}`.
3. The film separation is :math:`s_i=0.025(2050)=51.25\,\mathrm{mm}`. These values follow directly from the stated heights and focal length; slightly different endpoints printed in the scan do not satisfy both equations.
""",
        r"Object-lens distance :math:`2.05\,\mathrm m`; lens-film distance :math:`51.25\,\mathrm{mm}`.",
        r":math:`1/2050+1/51.25=1/50` and :math:`51.25/2050=0.025`.",
    ),
    "4.76": (
        r"""
1. Define the signed axial object-image separation :math:`L=s_o+s_i`, and use :math:`M_T=-s_i/s_o`.
2. The lens equation and :math:`s_i=-M_Ts_o` give :math:`s_o=f(1-1/M_T)` and :math:`s_i=f(1-M_T)`.
3. Add the two distances and simplify:

   .. math::

      L=f\left(2-M_T-\frac1{M_T}\right)
      =-\frac{f(M_T-1)^2}{M_T}.

   For a real object and real image, :math:`M_T<0` and this is their positive physical separation. Other configurations require the absolute coordinate separation if an unsigned distance is wanted.
""",
        r":math:`L=-f(M_T-1)^2/M_T` under the stated signed convention.",
        r":math:`M_T=-1` gives :math:`L=4f`, the minimum real-conjugate separation.",
    ),
    "4.77": (
        r"""
1. For separated thin lenses, :math:`\Phi=1/f_1+1/f_2-d/(f_1f_2)`. With :math:`f_1=20`, :math:`f_2=-40`, :math:`d=10` cm, :math:`\Phi=0.0375\,\mathrm{cm}^{-1}` and :math:`f=26.6667\,\mathrm{cm}`.
2. The system matrix has :math:`A=1-d/f_1=0.5`, :math:`D=1-d/f_2=1.25`, :math:`C=-\Phi`. The rear focal distance from lens 2 is :math:`-A/C=Af`.
3. The front focal distance to the left of lens 1 is :math:`-D/C=Df`. Thus :math:`\mathrm{BFL}=13.3333\,\mathrm{cm}` and :math:`\mathrm{FFL}=33.3333\,\mathrm{cm}`.
""",
        r"Front focus :math:`33.33\,\mathrm{cm}` left of lens 1; rear focus :math:`13.33\,\mathrm{cm}` right of lens 2.",
        r"The total lens-1-to-rear-focus length is :math:`23.33\,\mathrm{cm}<f`, the characteristic telephoto shortening.",
    ),
    "4.78": (
        r"""
1. Lenses in contact add powers: :math:`1/f=1/10+1/20-1/40=1/8`, with lengths in centimetres.
2. For :math:`s_o=16\,\mathrm{cm}`, :math:`1/s_i=1/8-1/16=1/16`, giving :math:`s_i=16\,\mathrm{cm}`.
3. The magnification is :math:`M_T=-16/16=-1`. The image is real, inverted, and the same size as the object.
""",
        r":math:`f=8\,\mathrm{cm}`, :math:`s_i=16\,\mathrm{cm}`, :math:`M_T=-1`.",
        r"An object at :math:`2f` is imaged at :math:`2f`; the negative component reduces, but does not cancel, the positive total power.",
    ),
    "4.79": (
        r"""
1. Let the weaker lens power be :math:`P` and the stronger be :math:`2P`. Contact placement makes the combined power :math:`3P`.
2. The combined focal length is :math:`30\,\mathrm{cm}=0.30\,\mathrm m`, so :math:`3P=1/0.30` and :math:`P=1.1111\,\mathrm D`.
3. Invert each power: :math:`f_{\rm weak}=0.90\,\mathrm m` and :math:`f_{\rm strong}=0.45\,\mathrm m`.
""",
        r"The focal lengths are :math:`90\,\mathrm{cm}` and :math:`45\,\mathrm{cm}`.",
        r"Twice the power means half the focal length, not twice the focal length.",
    ),
    "4.80": (
        r"""
1. Lens 1 has :math:`f_1=9\,\mathrm{cm}` and :math:`s_{o1}=12\,\mathrm{cm}`. Hence :math:`s_{i1}=(1/9-1/12)^{-1}=36\,\mathrm{cm}`.
2. Lens 2 is only 21 cm beyond lens 1. Its incident light is still converging to a point 15 cm beyond it, so :math:`s_{o2}=21-36=-15\,\mathrm{cm}`.
3. For :math:`f_2=-18\,\mathrm{cm}`,

   .. math::

      \frac1{s_{i2}}=-\frac1{18}-\frac1{-15}=\frac1{90}.

   The component magnifications are :math:`M_1=-3` and :math:`M_2=+6`; the total is :math:`M_T=-18`.
""",
        r"The final image is real, :math:`90\,\mathrm{cm}` right of lens 2, inverted and enlarged by a factor of 18.",
        r"Assigning a positive object distance to the converging bundle at lens 2 would give the wrong image side.",
    ),
    "4.81": (
        r"""
1. For :math:`n=2`, :math:`R_1=R_2=R<0`, and thickness :math:`d`, the two surface powers cancel in the zero-thickness limit. The finite-thickness term remains:

   .. math::

      \Phi=(n-1)\left(\frac1{R_1}-\frac1{R_2}\right)
      +\frac{(n-1)^2d}{nR_1R_2}=\frac{d}{2R^2}.

2. Therefore :math:`f=1/\Phi=2R^2/d>0`. The centre separation equals the vertex separation because the signed radii are equal.
3. Principal-plane offsets, positive to the right of each corresponding vertex, are :math:`h_1=-f(n-1)d/(nR_2)=-R` and :math:`h_2=-f(n-1)d/(nR_1)=-R`. Both planes shift right by :math:`|R|` and remain separated by :math:`d`.
""",
        r"A positive lens with :math:`f=2R^2/d` and :math:`h_1=h_2=-R`.",
        r"As :math:`d\to0`, the power tends to zero even though the limiting principal-plane offsets remain finite.",
    ),
    "4.82": (
        r"""
1. Use :math:`R_1=+2`, :math:`R_2=-4`, :math:`d=2` cm and :math:`n=1.5`. The thick-lens power is :math:`\Phi=0.5(1/2+1/4)+0.25(2)/(1.5\cdot2\cdot(-4))=1/3\,\mathrm{cm}^{-1}`.
2. Thus :math:`f=3\,\mathrm{cm}`. The principal offsets are :math:`h_1=-3(0.5)(2)/(1.5(-4))=+0.5\,\mathrm{cm}` and :math:`h_2=-3(0.5)(2)/(1.5(2))=-1\,\mathrm{cm}`.
3. Measure the front focus from vertex 1 as :math:`h_1-f=-2.5\,\mathrm{cm}` and the rear focus from vertex 2 as :math:`h_2+f=+2\,\mathrm{cm}`. Effective focal length is measured from the principal planes, not from the glass vertices.
""",
        r":math:`H_1` is 0.5 cm right of :math:`V_1`; :math:`H_2` is 1 cm left of :math:`V_2`; front/rear vertex focal distances are 2.5 cm left and 2 cm right.",
        r"The two principal planes lie inside this lens; neglecting the thickness term would incorrectly give :math:`f=2.667\,\mathrm{cm}`.",
    ),
    "4.83": (
        r"""
1. Take the curved face first: :math:`R_1=12\,\mathrm{cm}`, :math:`R_2=\infty`, :math:`d=12\,\mathrm{cm}`, :math:`n=2`. Only the curved surface contributes power, so :math:`f=R_1/(n-1)=12\,\mathrm{cm}`.
2. The principal offsets are :math:`h_1=0` and :math:`h_2=-fd/(2R_1)=-6\,\mathrm{cm}`. The front focus is 12 cm left of the curved vertex; the rear focus is 6 cm beyond the plane face.
3. The object is :math:`s_o=36\,\mathrm{cm}` from :math:`H_1`. Therefore :math:`s_i=(1/12-1/36)^{-1}=18\,\mathrm{cm}` from :math:`H_2`, or 12 cm beyond the plane face. :math:`M_T=-18/36=-1/2`.
""",
        r"A real, inverted, half-size image 18 cm right of :math:`H_2`, equivalently 12 cm beyond the plane face.",
        r"The planar exit has zero surface power but shifts the rear principal plane; treating the hemisphere as a zero-thickness lens misplaces the image.",
    ),
    "4.84": (
        r"""
1. For the common centre to the left, let :math:`R_1=-a`, :math:`R_2=-(a+d)`, with :math:`a>0`. Both radius vectors point back to the same physical point.
2. With :math:`n=2`, collect the thick-lens terms:

   .. math::

      \Phi=-\frac1a+\frac1{a+d}+\frac{d}{2a(a+d)}
      =-\frac{d}{2a(a+d)},\qquad f=-\frac{2a(a+d)}d.

3. The offsets become :math:`h_1=-fd/(2R_2)=-a` and :math:`h_2=-fd/(2R_1)=-(a+d)`. In global coordinates both locate the common centre, so the two principal planes coincide there.
""",
        r"A negative lens with :math:`f=-2a(a+d)/d`; both principal planes pass through the common centre.",
        r"The negative power follows from concave entrance power exceeding convex exit power; the thickness correction only partly cancels it.",
    ),
    "4.85": (
        r"""
1. A ball lens has :math:`R_1=r`, :math:`R_2=-r`, :math:`d=2r`. Its power reduces to :math:`\Phi=2(n-1)/(nr)` and both principal planes pass through the centre.
2. For :math:`n=1.501`, :math:`r=2\,\mathrm{mm}`, :math:`f=nr/[2(n-1)]=2.9960\,\mathrm{mm}`. The object distance from the principal plane is :math:`s_o=58\,\mathrm{mm}`.
3. Compute :math:`s_i=fs_o/(s_o-f)=3.1592\,\mathrm{mm}`, :math:`M_T=-s_i/s_o=-0.05447`, and :math:`h_i=M_T(0.5)=-0.02723\,\mathrm{mm}`.
""",
        r"The image is real, inverted, and about :math:`0.027\,\mathrm{mm}` tall, :math:`3.16\,\mathrm{mm}` from the droplet centre.",
        r"The image is :math:`1.16\,\mathrm{mm}` beyond the rear surface. The quoted rounded :math:`f\approx3\,\mathrm{mm}` is consistent with this result.",
    ),
    "4.86": (
        r"""
1. Write the eye-lens focal length as :math:`q`. Then :math:`f_1=3q`, :math:`f_2=q`, :math:`d=2q`, so :math:`\Phi=1/(3q)+1/q-2/(3q)=2/(3q)` and :math:`f=3q/2`.
2. The matrix entry :math:`D=1-d/f_2=-1`. The signed front focal distance to the left of lens 1 is :math:`Df=-3q/2`: the front focal plane is actually :math:`3q/2` to its right.
3. Lens 2 is at :math:`2q`, so that plane is :math:`q/2` left of the eye lens. The incident bundle must converge toward that plane; the ocular then converts it to parallel light.
""",
        r"The first focal plane lies between the lenses, :math:`q/2` before the eye lens; the effective focal length is :math:`3q/2`.",
        r"The first principal plane is :math:`fd/f_2=3q` right of lens 1, and its front focus is one effective focal length to its left.",
    ),
    "4.87": (
        r"""
1. Work backward from the required :math:`s_{i2}=45\,\mathrm{cm}` and :math:`f_2=60\,\mathrm{cm}`: :math:`1/s_{o2}=1/60-1/45=-1/180`, so :math:`s_{o2}=-180\,\mathrm{cm}`.
2. This virtual object is 180 cm beyond lens 2, hence lens 1 must form its intermediate image :math:`s_{i1}=20+180=200\,\mathrm{cm}` to its right.
3. With :math:`f_1=40\,\mathrm{cm}`, :math:`1/s_{o1}=1/40-1/200=1/50`. Therefore the source belongs 50 cm before lens 1. The total magnification is :math:`(-200/50)(-45/(-180))=-1`.
""",
        r"Place the object :math:`50\,\mathrm{cm}` left of lens 1; its final real image is inverted and equal in size.",
        r"The equivalent :math:`f=30\,\mathrm{cm}` has principal-plane conjugates :math:`60\,\mathrm{cm}` and :math:`60\,\mathrm{cm}`, confirming unit inverted magnification.",
    ),
    "4.88": (
        r"""
1. Trace a parallel paraxial ray of height :math:`h` and slope zero. After lens 1, :math:`u_1=-h/4`; after propagation through 6 cm, :math:`y_2=h+6u_1=-h/2`.
2. The negative lens has :math:`f_2=-8\,\mathrm{cm}`. Its output slope is :math:`u_2=u_1-y_2/f_2=-h/4-h/16=-5h/16`. At lens 3, 1.4 cm later, :math:`y_3=-h/2-(1.4)(5h/16)=-15h/16`.
3. Afocality requires :math:`u_3=u_2-y_3/f_3=0`. Hence :math:`f_3=y_3/u_2=3\,\mathrm{cm}`. The arbitrary input height cancels, as it must for a first-order afocal system.
""",
        r":math:`f_3=+3.0\,\mathrm{cm}`.",
        r"The last positive lens receives a diverging bundle from its front focal plane and collimates it.",
    ),
    "4.89": (
        r"""
1. Let each lens have focal length :math:`q`, with separation :math:`d=2q/3`. The combined power is :math:`2/q-d/q^2=4/(3q)`, so :math:`f=3q/4`.
2. The front principal plane is :math:`h_1=fd/q=q/2` to the right of the field lens. Its front focus is therefore at :math:`h_1-f=-q/4` relative to that lens.
3. Place the object plane :math:`q/4` before the field lens, equivalently :math:`3q/4` before :math:`H_1`. Rays from this plane emerge collimated. The effective focal length alone is not the distance from the first glass element.
""",
        r"The object plane is :math:`q/4` in front of the first lens, or :math:`3q/4` in front of the first principal plane.",
        r"Sequentially, lens 1 gives :math:`s_{i1}=-q/3`; lens 2 then sees :math:`s_{o2}=2q/3+q/3=q` and produces parallel light.",
    ),
    "4.90": (
        r"""
1. Use the intended positive power :math:`P_1=10/3\,\mathrm D`, negative power :math:`P_2=-20\,\mathrm D`, and separation :math:`d=1/4\,\mathrm m`.
2. Separated powers combine as

   .. math::

      P=P_1+P_2-dP_1P_2
      =\frac{10}{3}-20-\frac14\frac{10}{3}(-20)=0.

3. Thus the focal length is infinite and a parallel input gives a parallel output. If the rounded value :math:`3.33\,\mathrm D` is taken literally, :math:`P=-0.02\,\mathrm D` and :math:`f=-50\,\mathrm m`, a nearly afocal system rather than exactly zero power.
""",
        r"The intended system is afocal; exact cancellation uses :math:`P_1=3\frac13\,\mathrm D`.",
        r"The separation equals :math:`f_1+f_2=0.30-0.05=0.25\,\mathrm m`, the telescope afocal condition.",
    ),
    "4.91": (
        r"""
1. The initial real conjugates give :math:`1/f=1/300+1/150=1/100`, so the concave mirror has :math:`f=100\,\mathrm{cm}`.
2. Demand a new real image at the old object position: :math:`s_i'=300\,\mathrm{cm}`. Then :math:`1/s_o'=1/100-1/300=1/150`.
3. Put the object :math:`150\,\mathrm{cm}` in front of the mirror. This is also an immediate consequence of optical reversibility: exchanging the original conjugate points preserves the ray paths.
""",
        r"Move the object to :math:`150\,\mathrm{cm}` from the vertex.",
        r"The original magnification is :math:`-1/2`; after exchanging conjugates it becomes :math:`-2`.",
    ),
    "4.92": (
        r"""
1. Problem 4.80's lenses alone would focus 90 cm beyond lens 2. The mirror intercepts this converging beam after 60 cm, giving a virtual mirror object :math:`s_o=-(90-60)=-30\,\mathrm{cm}`.
2. A convex mirror with radius magnitude 15 cm has :math:`f=-7.5\,\mathrm{cm}`. Thus :math:`1/s_i=1/f-1/s_o=-1/7.5+1/30=-1/10`.
3. The mirror image is :math:`s_i=-10\,\mathrm{cm}`, behind the mirror. Its magnification relative to the incident virtual object is :math:`M_m=-s_i/s_o=-1/3`. Including the lenses' :math:`M_{12}=-18` gives :math:`M_{\rm total}=+6` before any further return pass through the lenses.
""",
        r"A virtual mirror image 10 cm behind the mirror, inverted relative to its virtual object; relative to the original object its magnification is :math:`+6`.",
        r"Distinguish the mirror's local magnification from the whole preceding system, and do not include a second lens pass unless requested.",
    ),
    "4.93": (
        r"""
1. Write the convex mirror focal length as :math:`f=-F` with :math:`F>0`. A beam converging toward a point :math:`d` behind the mirror has :math:`s_o=-d`.
2. Substitute in the mirror equation:

   .. math::

      -\frac1F=-\frac1d+\frac1{s_i},\qquad
      s_i=\frac{dF}{F-d}.

3. For the stated :math:`d<F`, :math:`s_i>0`, so reflected rays really converge in front of the mirror. :math:`M_T=-s_i/s_o=F/(F-d)>1`, and :math:`s_i>d`.
""",
        r"The image is real, erect relative to the virtual object, enlarged, and farther from the mirror than :math:`d`.",
        r"The source's positive :math:`f` in the inequality denotes the focal-length magnitude; the signed convex-mirror focal length remains negative.",
    ),
    "4.94": (
        r"""
1. A concave mirror of radius magnitude 8 cm has :math:`f=+4\,\mathrm{cm}`.
2. For :math:`s_o=12\,\mathrm{cm}`, :math:`1/s_i=1/4-1/12=1/6`, giving :math:`s_i=6\,\mathrm{cm}` in front of the mirror.
3. :math:`M_T=-s_i/s_o=-1/2`. Multiplying the 1 cm object height gives :math:`h_i=-0.5\,\mathrm{cm}`: real, inverted, and half-size.
""",
        r":math:`s_i=6\,\mathrm{cm}`, :math:`M_T=-0.5`, and :math:`h_i=-0.5\,\mathrm{cm}`.",
        r"The image lies between :math:`f=4\,\mathrm{cm}` and :math:`2f=8\,\mathrm{cm}`, as expected for an object beyond the centre of curvature.",
    ),
    "4.95": (
        r"""
1. Keep the negative convex-mirror focal length: :math:`f=-400\,\mathrm{cm}`, while the real object has :math:`s_o=200\,\mathrm{cm}`.
2. :math:`1/s_i=-1/400-1/200=-3/400`, so :math:`s_i=-400/3=-133.33\,\mathrm{cm}`.
3. The magnification is :math:`M_T=-s_i/s_o=2/3`. For a 4 cm object, :math:`h_i=8/3=2.667\,\mathrm{cm}`. The image is virtual, upright, and reduced.
""",
        r"A :math:`2.67\,\mathrm{cm}` upright virtual image :math:`133.3\,\mathrm{cm}` behind the mirror.",
        r"Its distance behind the convex mirror is less than :math:`|f|`, consistent with the usual real-object image region.",
    ),
    "4.96": (
        r"""
1. The convex radius gives :math:`f=-90/2=-45\,\mathrm{cm}`. The object is real, with :math:`s_o=180\,\mathrm{cm}`.
2. The conjugate equation yields :math:`1/s_i=-1/45-1/180=-1/36`, so :math:`s_i=-36\,\mathrm{cm}`.
3. :math:`M_T=-(-36)/180=1/5`. Therefore a 3 cm object produces :math:`h_i=3/5=0.6\,\mathrm{cm}`. The image is upright, virtual, and minified.
""",
        r":math:`s_i=-36\,\mathrm{cm}`, :math:`M_T=+0.2`, and :math:`h_i=+0.6\,\mathrm{cm}`.",
        r"The height must be obtained from the supplied 3 cm object; a 2 cm endpoint would not satisfy the magnification relation.",
    ),
}
