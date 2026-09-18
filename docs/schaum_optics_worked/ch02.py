SOLUTIONS = {
    "2.26": (
        r"""
1. Read :math:`k=4\pi10^6\,\mathrm{rad/m}` and :math:`B_0=66.7\times10^{-8}\,\mathrm T`. The argument :math:`k(z-ct)` gives propagation along :math:`+z`.
2. The field relation is :math:`\mathbf E=-c\hat{\mathbf z}\times\mathbf B`. Because :math:`\hat{\mathbf z}\times\hat{\mathbf y}=-\hat{\mathbf x}`, the electric field points along :math:`+x`.
3. Calculate :math:`E_0=cB_0\simeq200\,\mathrm{V/m}` and :math:`\lambda=2\pi/k=5.00\times10^{-7}\,\mathrm m`. Both fields have the same phase.
""",
        r":math:`\mathbf E=200\hat{\mathbf x}\sin[4\pi10^6(z-3\times10^8t)]\,\mathrm{V/m}`; :math:`\lambda=500\,\mathrm{nm}` and :math:`v=c`.",
        r":math:`\hat{\mathbf x}\times\hat{\mathbf y}=\hat{\mathbf z}` confirms the Poynting-vector direction.",
    ),
    "2.27": (
        r"""
1. The electric-field snapshot has a 20 V/m peak, a 1 mm spatial period, and a positive crest at the origin. Therefore use :math:`E_y=20\cos[k(x-ct)]` with :math:`k=2\pi\times10^3\,\mathrm{rad/m}`.
2. Divide the electric amplitude by :math:`c`: :math:`B_0=20/(3\times10^8)=6.67\times10^{-8}\,\mathrm T`.
3. The wave moves along :math:`+x`, so :math:`\mathbf B=(1/c)\hat{\mathbf x}\times\mathbf E` points along :math:`+z`. The same cosine phase is required for positive forward energy flow.
""",
        r":math:`B_z=6.67\times10^{-8}\cos[2\pi10^3(x-3\times10^8t)]\,\mathrm T`; :math:`B_x=B_y=0`.",
        r"A 1 mm separation reproduces the snapshot; the time period is :math:`\lambda/c=3.33\times10^{-12}\,\mathrm s`.",
    ),
    "2.28": (
        r"""
1. Read the graph's axes before converting: :math:`B_0=2\times10^{-6}\,\mathrm T` and :math:`T=10^{-14}\,\mathrm s`. The initial value is a positive crest.
2. Hence :math:`E_0=cB_0=600\,\mathrm{V/m}`, :math:`\lambda=cT=3\times10^{-6}\,\mathrm m`, and :math:`k=(2\pi/3)10^6\,\mathrm{rad/m}`.
3. For positive-x propagation with :math:`\mathbf B\parallel+z`, :math:`\mathbf E=-c\hat{\mathbf x}\times\mathbf B\parallel+y`. Use a cosine with the measured period.
""",
        r":math:`\mathbf E=600\hat{\mathbf y}\cos[(2\pi/3)10^6(x-3\times10^8t)]\,\mathrm{V/m}`.",
        r"The earlier 7600 V/m value does not follow the graph; 600 V/m gives the measured 2 microtesla amplitude.",
    ),
    "2.29": (
        r"""
1. In vacuum, invert the time-averaged flux formula:

   .. math::

      E_0=\sqrt{\frac{2I}{c\epsilon_0}}
      =\sqrt{\frac{2(1.197)}{(3.00\times10^8)(8.854\times10^{-12})}}
      \simeq30.0\,\mathrm{V/m}.

2. Transversality removes the y component of :math:`\mathbf B`. Since it lies in the xy plane, choose it along :math:`+x`; positive-y energy flow then requires :math:`\mathbf E\parallel+z`.
3. With :math:`\lambda=500\,\mathrm{nm}`, :math:`k=4\pi10^6\,\mathrm{rad/m}`. The initial phase is unspecified, so zero is an admissible choice.
""",
        r":math:`\mathbf E=30\hat{\mathbf z}\sin[4\pi10^6(y-ct)]\,\mathrm{V/m}` is one valid field.",
        r":math:`\hat{\mathbf z}\times\hat{\mathbf x}=\hat{\mathbf y}`; a simultaneous reversal of both transverse fields is equally valid.",
    ),
    "2.30": (
        r"""
1. Keep the given 600 nm as the vacuum wavelength :math:`\lambda_0`; the frequency stays constant at the interface.
2. The material wavelength is :math:`\lambda=\lambda_0/n=600/1.5=400\,\mathrm{nm}`.
3. Therefore :math:`k=2\pi/\lambda=2\pi/(400\times10^{-9})=1.571\times10^7\,\mathrm{rad/m}`. The equivalent single substitution is :math:`k=2\pi n/\lambda_0`.
""",
        r":math:`k=1.57\times10^7\,\mathrm{rad/m}`.",
        r"The propagation number increases by the factor :math:`n`, while the wavelength decreases by that factor.",
    ),
    "2.31": (
        r"""
1. The equal geometric path lengths give :math:`t_{\rm liquid}=1.46L/c` and :math:`t_{\rm air}=L/c`.
2. Subtract before solving: :math:`\Delta t=(1.46-1)L/c`. The required delay is :math:`10^{-6}\,\mathrm s`.
3. Consequently :math:`L=c\Delta t/0.46=(3.00\times10^8)(10^{-6})/0.46=652\,\mathrm m`.
""",
        r"A path length of approximately :math:`6.52\times10^2\,\mathrm m` is required.",
        r"At this length the transit times are approximately 3.17 and 2.17 microseconds, differing by one microsecond.",
    ),
    "2.32": (
        r"""
1. For each medium use the same vacuum wavelength: :math:`\lambda_D=589/2.417=243.7\,\mathrm{nm}` and :math:`\lambda_Z=589/1.923=306.3\,\mathrm{nm}`.
2. Divide the two equations so the common vacuum wavelength cancels:

   .. math::

      \frac{\lambda_D}{\lambda_Z}=\frac{n_Z}{n_D}
      =\frac{1.923}{2.417}=0.7956.

3. The ratio is less than one because diamond has the larger index, not because the frequency changes.
""",
        r":math:`\lambda_D/\lambda_Z\simeq0.796`.",
        r"The reciprocal index ordering is essential; taking :math:`n_D/n_Z` predicts the wrong wavelength ordering.",
    ),
    "2.33": (
        r"""
1. Maxwell's wave speed gives :math:`v=1/\sqrt{\mu\epsilon}`. Dividing vacuum speed by this speed yields :math:`n=\sqrt{\mu_r\epsilon_r}`.
2. For a nonmagnetic transparent dielectric, take :math:`\mu_r\simeq1` and the specified dielectric constant :math:`\epsilon_r=2.381`.
3. Thus :math:`n=\sqrt{2.381}=1.5431`. This identification assumes the dielectric constant is appropriate to the optical frequency; a static value need not be interchangeable in a dispersive material.
""",
        r":math:`n\simeq1.543` under the nonmagnetic, optical-frequency assumption.",
        r"Squaring the calculated index recovers 2.381.",
    ),
    "2.34": (
        r"""
1. The beam strikes normally and is perfectly absorbed, so the deposited power is irradiance times illuminated area.
2. Keeping the supplied centimetre units consistent gives :math:`P=(10\,\mathrm{W/cm^2})(1\,\mathrm{cm^2})=10\,\mathrm W`.
3. Multiply by exposure time: :math:`U=Pt=(10)(1000)=10^4\,\mathrm J`. In SI, the equivalent irradiance and area are :math:`10^5\,\mathrm{W/m^2}` and :math:`10^{-4}\,\mathrm{m^2}`.
""",
        r":math:`U=10^4\,\mathrm J`.",
        r"Watts times seconds are joules; no factor of :math:`c` is needed for an energy calculation.",
    ),
    "2.35": (
        r"""
1. Convert :math:`P=3\,\mathrm{kW}=3000\,\mathrm W` and :math:`A=10^{-5}\,\mathrm{cm^2}=10^{-9}\,\mathrm{m^2}`.
2. The irradiance is :math:`I=P/A=3.00\times10^{12}\,\mathrm{W/m^2}`.
3. Recover the peak, not RMS, electric field:

   .. math::

      E_0=\sqrt{\frac{2I}{c\epsilon_0}}
      =\sqrt{\frac{6.00\times10^{12}}{2.656\times10^{-3}}}
      =4.75\times10^7\,\mathrm{V/m}.

   The quoted wavelength and cutting time provide context but are unnecessary for this amplitude calculation.
""",
        r":math:`I=3.00\times10^{12}\,\mathrm{W/m^2}`, :math:`E_0\simeq4.75\times10^7\,\mathrm{V/m}`.",
        r"The area conversion uses :math:`1\,\mathrm{cm^2}=10^{-4}\,\mathrm{m^2}`, not :math:`10^{-2}`.",
    ),
    "2.36": (
        r"""
1. The peak magnetic field in vacuum is :math:`B_0=E_0/c`, so the instantaneous Poynting flux is :math:`S=E_0^2\cos^2\Phi/(\mu_0c)`.
2. Average over a complete cycle: :math:`\langle\cos^2\Phi\rangle=1/2`. Since :math:`1/(\mu_0c)=c\epsilon_0`, obtain :math:`I=c\epsilon_0E_0^2/2`.
3. Substitute constants: :math:`c\epsilon_0/2=(2.998\times10^8)(8.854\times10^{-12})/2=1.327\times10^{-3}` in SI.
""",
        r":math:`I=(1.33\times10^{-3}\,\mathrm{W/V^2})E_0^2` when :math:`E_0` is in V/m.",
        r"Using an RMS field instead would remove the factor one half from the field-amplitude expression.",
    ),
    "2.37": (
        r"""
1. Use the measured peak field :math:`E_0=10\,\mathrm{V/m}` to find :math:`I=(1.327\times10^{-3})(10)^2=0.1327\,\mathrm{W/m^2}`.
2. The source is isotropic, so the same irradiance occurs over a sphere of radius :math:`r=10\,\mathrm m` and area :math:`4\pi r^2=400\pi\,\mathrm{m^2}`.
3. The total power is :math:`P=4\pi r^2I=(400\pi)(0.1327)=166.8\,\mathrm W`; older rounded constants give about 167.6 W.
""",
        r":math:`P\simeq1.67\times10^2\,\mathrm W`.",
        r"Doubling the observation radius halves the field amplitude and quarters the irradiance, leaving total power unchanged.",
    ),
    "2.38": (
        r"""
1. The wave's magnetic field is :math:`\mathbf B=(1/c)\hat{\mathbf k}\times\mathbf E`, so :math:`\mathbf S=\mathbf E\times\mathbf B/\mu_0=c\epsilon_0E_0^2\sin^2\Phi\,\hat{\mathbf k}`.
2. Average explicitly over :math:`T=2\pi/\omega`:

   .. math::

      I=\frac{c\epsilon_0E_0^2}{T}\int_0^T\sin^2(kx-\omega t)\,dt
      =\frac{c\epsilon_0E_0^2}{2}.

3. The oscillatory :math:`\cos2\Phi` term integrates to zero; the remaining constant term carries the measured average flux.
""",
        r":math:`I=c\epsilon_0E_0^2/2`.",
        r"The average cannot depend on the starting phase of a complete-cycle integral.",
    ),
    "2.39": (
        r"""
1. Start with :math:`E_\gamma=hc/\lambda` in joules. To express the result in electron volts, divide by :math:`e=1.602176634\times10^{-19}\,\mathrm{J/eV}`.
2. If the numeric wavelength is in nanometres, its metre value is :math:`10^{-9}\lambda_{\rm nm}`.
3. Collect the constants:

   .. math::

      E_{\rm eV}=\frac{hc\,10^9/e}{\lambda_{\rm nm}}
      =\frac{1239.84}{\lambda_{\rm nm}}.

   The numerator has units eV nm, which cancel the denominator's length unit.
""",
        r":math:`E_\gamma(\mathrm{eV})=1239.84/\lambda(\mathrm{nm})`.",
        r"A 500 nm photon carries about 2.48 eV; using metres directly in this shortcut would be off by nine orders of magnitude.",
    ),
    "2.40": (
        r"""
1. Convert the incident solar flux with the conversion specified in the problem:

   .. math::

      I=\frac{2}{0.239}\frac{10^4}{60}
      =1.395\times10^3\,\mathrm{W/m^2}.

2. A photon reflected normally reverses its momentum, so the pressure is :math:`p=2I/c`.
3. Insert the flux: :math:`p=2(1395)/(3.00\times10^8)=9.30\times10^{-6}\,\mathrm{Pa}`, approximately :math:`9.2\times10^{-11}` atmosphere. This follows the stated calories-to-joules conversion; 9.8 microPa is not obtained from these inputs.
""",
        r":math:`p\simeq9.3\times10^{-6}\,\mathrm{N/m^2}` for perfect reflection.",
        r"Replacing the mirror by a perfect absorber halves the pressure.",
    ),
    "2.41": (
        r"""
1. The threshold condition is :math:`E_\gamma=W`, with sodium work function :math:`W=1.8\,\mathrm{eV}`. Longer wavelengths have insufficient photon energy.
2. Solve :math:`hc/\lambda_{\max}=W` for wavelength.
3. Using the photon-energy shortcut gives :math:`\lambda_{\max}=1239.84/1.8=688.8\,\mathrm{nm}`. Using the book's rounded numerator 1239 gives 688.3 nm.
""",
        r"The threshold wavelength is approximately :math:`689\,\mathrm{nm}`.",
        r"Increasing intensity below the single-photon threshold does not change the energy of each photon in this model.",
    ),
    "2.42": (
        r"""
1. The flashlight emits energy :math:`P\Delta t` in time :math:`\Delta t`, corresponding to forward photon momentum :math:`P\Delta t/c`.
2. Conservation of momentum gives equal and opposite flashlight recoil; divide by :math:`\Delta t` to obtain :math:`F=P/c`.
3. With :math:`P=10^{-3}\,\mathrm W`, :math:`F=10^{-3}/(2.998\times10^8)=3.34\times10^{-12}\,\mathrm N`. There is no factor two because this is emission, not reversal of an incident beam.
""",
        r"The recoil is :math:`3.34\times10^{-12}\,\mathrm N` opposite the emitted beam.",
        r"The force has dimensions :math:`(\mathrm{J/s})/(\mathrm{m/s})=\mathrm N`; the scan's printed larger value is inconsistent with 1 mW.",
    ),
    "2.43": (
        r"""
1. The reflecting surface area is :math:`9\times10^{-2}\,\mathrm{cm^2}=9\,\mathrm{mm^2}`, larger than the :math:`4\,\mathrm{mm^2}` beam footprint. With full overlap it intercepts all 600 W.
2. The flux is :math:`I=600/(4\times10^{-6})=1.5\times10^8\,\mathrm{W/m^2}`. Perfect reflection gives :math:`p=2I/c\simeq1.00\,\mathrm{Pa}`.
3. Multiply by the illuminated beam area, not the entire larger reflector: :math:`F=p(4\times10^{-6})=4.00\times10^{-6}\,\mathrm N`.
""",
        r":math:`F=4.00\times10^{-6}\,\mathrm N` along the incident beam.",
        r"The same result follows directly from :math:`F=2P/c`.",
    ),
    "2.44": (
        r"""
1. Convert :math:`21\,\mathrm{cm}=0.21\,\mathrm m`.
2. The frequency is :math:`\nu=c/\lambda=2.998\times10^8/0.21=1.428\times10^9\,\mathrm{Hz}`.
3. Multiply by Planck's constant: :math:`E_\gamma=h\nu=(6.626\times10^{-34})(1.428\times10^9)=9.46\times10^{-25}\,\mathrm J`. This is a microwave/radio spectral line, far below optical photon energies.
""",
        r":math:`\nu\simeq1.43\,\mathrm{GHz}`, :math:`E_\gamma\simeq9.46\times10^{-25}\,\mathrm J`.",
        r"The energy is also :math:`5.90\times10^{-6}\,\mathrm{eV}`, consistent with a long wavelength.",
    ),
    "2.45": (
        r"""
1. Convert the given :math:`18{,}600{,}000` miles using :math:`1609.344\,\mathrm{m/mile}`: :math:`\lambda=2.994\times10^{10}\,\mathrm m`.
2. The period is :math:`T=\lambda/c\simeq99.85\,\mathrm s`; the frequency is only about :math:`0.0100\,\mathrm{Hz}`.
3. Use :math:`E=h/T` and divide by the joules-per-electron-volt conversion, obtaining :math:`E\simeq4.14\times10^{-17}\,\mathrm{eV}`.
""",
        r"These extremely low-frequency radio waves have period about 100 s and photon energy :math:`4.14\times10^{-17}\,\mathrm{eV}`.",
        r"An enormous wavelength implies both a long period and a very small photon energy.",
    ),
    "2.46": (
        r"""
1. One erg is :math:`U=10^{-7}\,\mathrm J`. The required photon count is :math:`N=U/E_\gamma=U\lambda/(hc)`.
2. Insert :math:`hc=1.98645\times10^{-25}\,\mathrm{J\,m}` separately for the three wavelengths:

   .. math::

      N_\gamma=5.03\times10^5,\qquad
      N_{500\,\mathrm{nm}}=2.52\times10^{11},\qquad
      N_{1\,\mathrm{cm}}=5.03\times10^{15}.

3. The large change in count follows from keeping total energy fixed while increasing wavelength.
""",
        r"Approximately :math:`5.0\times10^5`, :math:`2.5\times10^{11}`, and :math:`5.0\times10^{15}` photons.",
        r"Multiplying each count by :math:`hc/\lambda` returns :math:`10^{-7}\,\mathrm J`.",
    ),
    "2.47": (
        r"""
1. Convert the two wavelengths to :math:`0.10\,\mathrm m` and :math:`632.9\times10^{-9}\,\mathrm m`.
2. Divide :math:`hc=1.98645\times10^{-25}\,\mathrm{J\,m}` by each wavelength to obtain :math:`1.986\times10^{-24}\,\mathrm J` and :math:`3.139\times10^{-19}\,\mathrm J`.
3. Their ratio can be found without Planck's constant: :math:`E_{\rm microwave}/E_{\rm HeNe}=\lambda_{\rm HeNe}/\lambda_{\rm microwave}=6.329\times10^{-6}`.
""",
        r"The He–Ne photon carries approximately :math:`1.58\times10^5` times the energy of the microwave photon.",
        r"The shorter wavelength must correspond to the larger photon energy.",
    ),
}
