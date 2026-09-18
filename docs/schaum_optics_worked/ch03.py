SOLUTIONS = {
    "3.31": (
        r"""
1. Let :math:`d` be plate thickness measured along the normal. The internal ray length is :math:`d/\cos\theta_t`; the perpendicular distance between incident and emerging parallel rays is

   .. math::

      a=\frac{d\sin(\theta_i-\theta_t)}{\cos\theta_t}.

2. Expand the sine difference to obtain :math:`a=d[\sin\theta_i-\cos\theta_i\sin\theta_t/\cos\theta_t]`.
3. Snell's law gives :math:`\sin\theta_t=(n_i/n_t)\sin\theta_i`. Substitute and factor :math:`d\sin\theta_i`. A second refraction restores the initial direction because the external media and the two normals are the same.
""",
        r":math:`a=d\sin\theta_i[1-n_i\cos\theta_i/(n_t\cos\theta_t)]`.",
        r":math:`a=0` for normal incidence, zero thickness, or equal indices; :math:`a` is not the displacement measured parallel to the plate face.",
    ),
    "3.32": (
        r"""
1. Call the internal angles to the two face normals :math:`r_1,r_2`, and the prism apex :math:`A`. The triangle formed by the internal ray and the faces gives :math:`r_1+r_2=A`.
2. The turn at entrance is :math:`\theta_{i1}-r_1`; the turn at exit is :math:`\theta_{t2}-r_2`. Both contribute to the deviation in the standard prism geometry.
3. Add the turns and eliminate the internal angles:

   .. math::

      \delta=(\theta_{i1}-r_1)+(\theta_{t2}-r_2)
      =\theta_{i1}+\theta_{t2}-A.

   Snell's law is needed to calculate the angles numerically, but not to prove this geometric identity.
""",
        r":math:`\delta=\theta_{i1}+\theta_{t2}-A`.",
        r"At minimum deviation the path is symmetric, giving :math:`\delta_{\min}=2\theta_i-A`.",
    ),
    "3.33": (
        r"""
1. Extend the mirror lines until they meet. Let :math:`g_1,g_2` be the interior angles between the connecting ray and those mirror lines, and let their intersection angle be :math:`\gamma`.
2. The resulting triangle gives :math:`g_1+g_2=\pi-\gamma`. Reflection makes the incident and reflected grazing angles equal at each mirror.
3. The source marks reflex turns outside the triangle: :math:`\alpha=\pi+2g_1`, :math:`\beta=\pi+2g_2`. Therefore

   .. math::

      \delta=\alpha+\beta=2\pi+2(g_1+g_2)=4\pi-2\gamma.

   As a change of direction modulo a full turn, this is :math:`-2\gamma`; it is independent of the initial ray direction.
""",
        r":math:`\delta=4\pi-2\gamma` for the reflex-angle convention of Fig. 3-16.",
        r"For perpendicular mirrors, the emerging direction is opposite to the entering direction modulo :math:`2\pi`.",
    ),
    "3.34": (
        r"""
1. Measure ray directions counterclockwise from the lower horizontal mirror, and let the upper mirror's inclination be :math:`\alpha`. After the first lower reflection the left-going upward ray has direction :math:`\beta_1=\pi/2+\theta_i`.
2. Reflection in a line at angle :math:`\alpha` maps a direction :math:`\beta` to :math:`2\alpha-\beta`. Thus :math:`\beta_2=2\alpha-\pi/2-\theta_i`; reflection at the lower mirror then gives :math:`\beta_3=\pi/2+\theta_i-2\alpha`.
3. To retrace from the next upper hit, the ray must arrive normal to that mirror: :math:`\beta_3=\pi/2+\alpha`. Equating the two expressions gives :math:`\theta_i=3\alpha`.
""",
        r"The illustrated sequence retraces when :math:`\theta_i=3\alpha`.",
        r"Normal incidence at the final mirror reverses the direction exactly; reversibility then sends the ray back through every preceding hit.",
    ),
    "3.35": (
        r"""
1. Draw circles of radii proportional to :math:`n_i` and :math:`n_t`, centred on the interface crossing. Extend the incident direction to the first circle.
2. Its tangential coordinate is :math:`q=n_i\sin\theta_i`. Dropping a line normal to the interface keeps this coordinate unchanged when it meets the second circle.
3. The new radius therefore satisfies :math:`n_t\sin\theta_t=q`. Joining its endpoint to the centre constructs a refracted ray obeying Snell's law. Choose the transmitted half-plane and forward propagation branch.
""",
        r"The construction enforces :math:`n_i\sin\theta_i=n_t\sin\theta_t` geometrically.",
        r"If :math:`q>n_t`, the construction has no transmitted-circle intersection: this is precisely the total-internal-reflection condition.",
    ),
    "3.36": (
        r"""
1. For a point :math:`Q` on an ellipse with foci :math:`F_1,F_2`, its defining equation is :math:`|Q-F_1|+|Q-F_2|=2a`.
2. In a uniform medium the optical path is :math:`\mathcal L=n(|Q-F_1|+|Q-F_2|)=2na`. Every tangential displacement of :math:`Q` leaves it unchanged, so its first variation vanishes.
3. Differentiating the distances along a surface tangent :math:`\hat{\mathbf t}` gives :math:`(\hat{\mathbf s}_i-\hat{\mathbf s}_r)\cdot\hat{\mathbf t}=0`. The two rays thus have equal tangential components, the reflection law. Rotating the ellipse about the focal axis proves the ellipsoid case.
""",
        r"Every geometrically accessible ray from one focus reflects to the other with optical path :math:`2na`.",
        r"The path is constant along the surface; Fermat requires stationarity, not necessarily a strict minimum.",
    ),
    "3.37": (
        r"""
1. Let source and receiver heights be :math:`h,b`, with fixed lateral separation :math:`a=h\tan\theta_i+b\tan\theta_t`.
2. Differentiate this constraint: :math:`h\sec^2\theta_i\,d\theta_i+b\sec^2\theta_t\,d\theta_t=0`. Hence :math:`d\theta_t/d\theta_i=-h\cos^2\theta_t/(b\cos^2\theta_i)`.
3. The optical path is :math:`\mathcal L=n_ih\sec\theta_i+n_tb\sec\theta_t`. Substituting the constraint derivative yields

   .. math::

      \frac{d\mathcal L}{d\theta_i}
      =\frac{h}{\cos^2\theta_i}(n_i\sin\theta_i-n_t\sin\theta_t).

   Stationarity sets the parenthesis to zero.
""",
        r":math:`n_i\sin\theta_i=n_t\sin\theta_t`.",
        r":math:`\theta_i` and :math:`\theta_t` are constrained variables; differentiating while treating both as independent gives an incorrect result.",
    ),
    "3.38": (
        r"""
1. The two geometric segment lengths are :math:`\ell_i=h\sec\theta_i` and :math:`\ell_t=b\sec\theta_t`.
2. Their first-order optical-path change is

   .. math::

      d\mathcal L=\frac{n_ih\sin\theta_i}{\cos^2\theta_i}d\theta_i
      +\frac{n_tb\sin\theta_t}{\cos^2\theta_t}d\theta_t.

3. Moving the interface crossing by :math:`dx` gives :math:`dx=h\sec^2\theta_i\,d\theta_i=-b\sec^2\theta_t\,d\theta_t`. Therefore :math:`d\mathcal L=(n_i\sin\theta_i-n_t\sin\theta_t)dx`. For arbitrary infinitesimal :math:`dx`, stationarity requires the coefficient to vanish.
""",
        r"The adjacent-path difference reduces to Snell's law in first order.",
        r"The transmitted-angle change has the opposite sign to the incident-angle change because the endpoints remain fixed.",
    ),
    "3.39": (
        r"""
1. Put the reflecting plane at :math:`z=0`, and write the variable hit point as :math:`Q=(x,y,0)`. With fixed source :math:`S` and receiver :math:`P`, :math:`\mathcal L=n(|Q-S|+|P-Q|)`.
2. An arbitrary in-plane displacement :math:`d\mathbf q` gives :math:`d\mathcal L=n(\hat{\mathbf s}_i-\hat{\mathbf s}_r)\cdot d\mathbf q`. Both tangential components must vanish independently at stationarity.
3. Thus :math:`\hat{\mathbf s}_i-\hat{\mathbf s}_r` is normal to the mirror. Equivalently :math:`\hat{\mathbf s}_r=\hat{\mathbf s}_i-2(\hat{\mathbf s}_i\cdot\hat{\mathbf n})\hat{\mathbf n}`. The reflected vector lies in the span of the incident vector and normal, proving coplanarity.
""",
        r"Incident ray, reflected ray, and surface normal lie in one plane.",
        r"The reflected direction preserves norm and tangential component, while reversing the normal component.",
    ),
    "3.40": (
        r"""
1. With :math:`n_i=1`, :math:`n_t=1.5`, :math:`\theta_i=45^\circ`, Snell's law gives :math:`\sin\theta_t=\sin45^\circ/1.5=0.471405`, hence :math:`\theta_t=28.1255^\circ` and :math:`\cos\theta_t=0.881917`.
2. The electric field is perpendicular to the incidence plane, so use the s coefficients:

   .. math::

      r_s=\frac{0.707107-1.5(0.881917)}{0.707107+1.5(0.881917)}=-0.303337,
      \qquad t_s=\frac{2(0.707107)}{0.707107+1.5(0.881917)}=0.696663.

3. The negative reflection amplitude denotes a phase reversal. It does not represent negative reflected power.
""",
        r":math:`r_s\simeq-0.3033`, :math:`t_s\simeq0.6967`.",
        r":math:`1+r_s=t_s`, and :math:`R_s\simeq0.0920`, :math:`T_s\simeq0.9080` after the normal-flux factor is included.",
    ),
    "3.41": (
        r"""
1. Snell's law gives :math:`n_t/n_i=\sin\theta_i/\sin\theta_t`. Substitute it into :math:`t_s=2n_i\cos\theta_i/(n_i\cos\theta_i+n_t\cos\theta_t)`.
2. Multiply numerator and denominator by :math:`\sin\theta_t/n_i`; the denominator becomes :math:`\sin\theta_t\cos\theta_i+\sin\theta_i\cos\theta_t=\sin(\theta_i+\theta_t)`.
3. For p polarization the transformed denominator is :math:`\sin\theta_i\cos\theta_i+\sin\theta_t\cos\theta_t=\sin(\theta_i+\theta_t)\cos(\theta_i-\theta_t)`.
""",
        r":math:`t_s=2\sin\theta_t\cos\theta_i/\sin(\theta_i+\theta_t)` and :math:`t_p=t_s/\cos(\theta_i-\theta_t)`.",
        r"At normal incidence these angular forms have removable 0/0 expressions; take the limit or use the index forms.",
    ),
    "3.42": (
        r"""
1. Define :math:`a=n_i\cos\theta_i`, :math:`b=n_t\cos\theta_t`. The s-polarization formulas give :math:`t_s-r_s=[2a-(a-b)]/(a+b)=1`.
2. For p polarization let :math:`D=n_t\cos\theta_i+n_i\cos\theta_t`. Then

   .. math::

      \frac{n_t}{n_i}t_p-r_p
      =\frac{2n_t\cos\theta_i-(n_t\cos\theta_i-n_i\cos\theta_t)}{D}=1.

3. These are the book's :math:`t_s+(-r_s)=1` and :math:`n_{ti}t_p+(-r_p)=1`. The minus signs must follow the selected reflected p basis.
""",
        r":math:`t_s-r_s=1` and :math:`(n_t/n_i)t_p-r_p=1`.",
        r"At normal air-to-glass incidence, :math:`r_s=-0.2`, :math:`r_p=+0.2`, :math:`t_s=t_p=0.8`; both identities give one.",
    ),
    "3.43": (
        r"""
1. For real propagating waves in lossless media, put :math:`a=n_i\cos\theta_i`, :math:`b=n_t\cos\theta_t`. Then

   .. math::

      R_s+T_s=\frac{(a-b)^2}{(a+b)^2}
      +\frac{b}{a}\frac{4a^2}{(a+b)^2}
      =\frac{(a-b)^2+4ab}{(a+b)^2}=1.

2. For p polarization use :math:`D=n_t\cos\theta_i+n_i\cos\theta_t`. The numerator is :math:`(n_t\cos\theta_i-n_i\cos\theta_t)^2+4n_in_t\cos\theta_i\cos\theta_t=D^2`.
3. In total internal reflection the transmitted field is evanescent: its normal average transmitted flux is zero and :math:`|r|^2=1`; the real-angle transmission calculation must not be applied unchanged.
""",
        r":math:`R_s+T_s=R_p+T_p=1` for a lossless interface with the appropriate normal-flux definition.",
        r"Using :math:`T=|t|^2` alone fails whenever the two optical admittances differ.",
    ),
    "3.44": (
        r"""
1. Reverse the media: :math:`n_i=1.5`, :math:`n_t=1`, and both ray angles are zero.
2. The s electric-amplitude coefficient is :math:`r_s=(1.5-1)/(1.5+1)=0.2`; the transmission coefficient is :math:`t=2(1.5)/(1.5+1)=1.2`. In the stated p basis, :math:`r_p=-0.2`.
3. Compute powers with the index factor: :math:`R=0.2^2=0.04` and :math:`T=(1/1.5)(1.2)^2=0.96`. The transmitted field exceeds the incident field because the medium's wave impedance changes.
""",
        r":math:`r_s=+0.2`, :math:`r_p=-0.2` in the chosen basis, :math:`t_s=t_p=1.2`; :math:`R=0.04`, :math:`T=0.96`.",
        r":math:`E_i+E_r=E_t` for the s basis and :math:`R+T=1`; amplitude greater than one does not imply gain.",
    ),
    "3.45": (
        r"""
1. Set :math:`q=n_t/n_i>0`. At normal incidence, :math:`R=(1-q)^2/(1+q)^2` and :math:`T=4q/(1+q)^2`.
2. Representative points are :math:`q=1:(R,T)=(0,1)` and :math:`q=1.5` or :math:`2/3:(R,T)=(0.04,0.96)`; reciprocity explains the identical pairs.
3. For equal powers, set :math:`(1-q)^2=4q`. Expand and complete the square:

   .. math::

      q^2-6q+1=0,\qquad (q-3)^2=8,\qquad q=3\pm2\sqrt2.

   Both roots are positive and correspond to :math:`R=T=1/2`.
""",
        r":math:`n_t/n_i=5.8284` or :math:`0.171573` gives equal reflection and transmission.",
        r"The roots multiply to one, consistent with reversing the direction of normal-incidence illumination.",
    ),
    "3.46": (
        r"""
1. Critical refraction is from the higher-index side. At the B-to-A boundary, :math:`\sin45^\circ=n_A/n_B`, so :math:`n_B=\sqrt2\,n_A`.
2. At the C-to-B boundary, :math:`\sin45^\circ=n_B/n_C`, so :math:`n_C=\sqrt2\,n_B`.
3. Substitute the first equation into the second: :math:`n_C=2n_A`. The data determine a ratio; an absolute value 2 requires the additional choice :math:`n_A=1`.
""",
        r":math:`n_C/n_A=2`.",
        r"The assumed ordering :math:`n_A<n_B<n_C` is reproduced by both square-root-of-two steps.",
    ),
    "3.47": (
        r"""
1. The ray enters the first prism face normally, so it is not refracted there.
2. The hypotenuse is at :math:`45^\circ` to the incident internal ray, making the incidence angle to its normal also :math:`45^\circ`.
3. At the critical threshold, :math:`n\sin45^\circ=n_{\rm air}=1`. Hence :math:`n=\sqrt2`. Strictly above this threshold the hypotenuse produces total internal reflection and turns the beam through :math:`90^\circ`.
""",
        r"The limiting index is :math:`\sqrt2\simeq1.4142`; use :math:`n>\sqrt2` for incidence strictly above critical.",
        r"Immersing the prism in index :math:`n_0` changes the threshold to :math:`n=\sqrt2\,n_0`.",
    ),
    "3.48": (
        r"""
1. The diagram places water of index :math:`n_w=1.33` outside the glass, including the entrance face. Let the refracted angle from the horizontal entrance normal be :math:`r`.
2. At the entrance, :math:`n_w\sin45^\circ=n_g\sin r`. At the bottom critical condition, the angle is :math:`90^\circ-r`, so :math:`n_g\cos r=n_w`.
3. Square and add these relations:

   .. math::

      n_g^2=n_w^2(\sin^245^\circ+1)
      =(1.33)^2(1.5),\qquad n_g=1.629.

   An index can be inferred uniquely only if the marked bottom ray is at the critical threshold; merely observing total reflection gives an inequality.
""",
        r":math:`n_g\simeq1.63` at the illustrated critical condition.",
        r"Using air at the entrance gives a different answer; the surrounding water in the source diagram is essential.",
    ),
    "3.49": (
        r"""
1. For the liquid-to-air critical angle, :math:`\sin45^\circ=1/n_l`, so :math:`n_l=\sqrt2`.
2. The requested illumination is the reverse direction, air into liquid. Its Brewster relation is therefore :math:`\tan\theta_B=n_l/1=\sqrt2`.
3. Evaluate :math:`\theta_B=54.7356^\circ`. Snell's law then gives :math:`\theta_t=35.2644^\circ`, confirming perpendicular reflected and refracted rays.
""",
        r":math:`\theta_B\simeq54.74^\circ` for incidence from air.",
        r":math:`\theta_B+\theta_t=90^\circ`; do not use the reciprocal index for this illumination direction.",
    ),
    "3.50": (
        r"""
1. Let :math:`\alpha` be the meridional ray angle to the fibre axis inside the core. Entrance refraction gives :math:`n_0\sin\theta_i=n_f\sin\alpha`.
2. At the cylindrical side wall the incidence angle to the normal is :math:`90^\circ-\alpha`. At the limiting guided ray, :math:`\cos\alpha_{\max}=n_c/n_f`.
3. Eliminate the internal angle:

   .. math::

      n_0\sin\theta_{\max}=n_f\sqrt{1-(n_c/n_f)^2}
      =\sqrt{n_f^2-n_c^2}.

   If the right side exceeds :math:`n_0`, the external acceptance is capped at :math:`90^\circ`. This ray result assumes a straight step-index fibre and meridional rays.
""",
        r":math:`\mathrm{NA}=\sqrt{n_f^2-n_c^2}` and :math:`\theta_{\max}=\arcsin(\mathrm{NA}/n_0)` when the argument is at most one.",
        r"The acceptance shrinks to zero when core and cladding indices become equal.",
    ),
}
