# KrakenOS Core Algorithms

This note documents the core KrakenOS optical engine as it exists on this branch. The focus is the physically meaningful state that moves through the tracing pipeline: surface parameters, ray state, refraction/reflection variables, paraxial variables, pupil variables, and diffraction/PSF variables.

It is not a dump of every local scratch variable in every file. That would be noise. Instead, this covers the variables that matter to the optics and the code paths that consume them.

Lengths are in millimeters unless noted otherwise. Wavelengths are in micrometers inside most KrakenOS tracing code. Direction cosines are unitless. User-facing angles are usually degrees.

## Code map

- Surface definition and surface-function composition:
  - `KrakenOS/SurfClass.py:12`
  - `KrakenOS/SurfClass.py:258`
- System build, sequential tracing, batch tracing, data collection:
  - `KrakenOS/KrakenSys.py:185`
  - `KrakenOS/KrakenSys.py:212`
  - `KrakenOS/KrakenSys.py:588`
  - `KrakenOS/KrakenSys.py:774`
  - `KrakenOS/KrakenSys.py:887`
- Local-space ray/surface intersection and surface normals:
  - `KrakenOS/InterNormalCalc.py:46`
  - `KrakenOS/InterNormalCalc.py:291`
  - `KrakenOS/HitOnSurf.py:45`
  - `KrakenOS/HitOnSurf.py:170`
- Refraction, reflection, Fresnel energy, dispersion, paraxial matrix optics:
  - `KrakenOS/PhysicsClass.py:29`
  - `KrakenOS/Physics.py:27`
  - `KrakenOS/Physics.py:158`
  - `KrakenOS/Physics.py:338`
- Pupil construction and field-ray generation:
  - `KrakenOS/PupilTool.py:510`
  - `KrakenOS/PupilTool.py:769`
  - `KrakenOS/PupilTool.py:832`
- Wavefront, exit pupil, PSF, MTF:
  - `KrakenOS/PhaseCalc.py:74`
  - `KrakenOS/PhaseCalc.py:170`
  - `KrakenOS/PSFCalc.py:24`
  - `KrakenOS/PSFCalc.py:51`
  - `KrakenOS/PSFCalc.py:89`
- Ray-result storage:
  - `KrakenOS/RayKeeper.py:27`

## 1. End-to-end pipeline

The sequential engine is easiest to understand as a fixed pipeline:

1. Define each optical surface as a `surf` object.
2. Convert each `surf` into one or more sag functions and one physics law.
3. Build coordinate transforms for every surface.
4. For each ray, propagate a straight line toward the current surface.
5. Transform that line into the local coordinates of the surface.
6. Solve the line/surface intersection.
7. Compute the surface normal.
8. Apply refraction, reflection, or grating physics.
9. Accumulate geometry, optical path, and energy data.
10. Repeat until the image plane or an absorbing surface is reached.

Mathematically, the ray is represented as

$$
\mathbf{r}(t)=\mathbf{r}_0+t\hat{\mathbf{s}},
\qquad
\hat{\mathbf{s}}=(L,M,N),
\qquad
\|\hat{\mathbf{s}}\|=1.
$$

KrakenOS stores that direction vector as `L`, `M`, `N` throughout the code.

## 2. Surface model

### 2.1 `surf` is the optical primitive

Relevant code:

- `KrakenOS/SurfClass.py:140-235`
- `KrakenOS/SurfClass.py:258-318`

The `surf` class combines geometry, material, transform, and optional special behavior.

Core variables:

| Code variable | Physics meaning | Typical symbol |
| --- | --- | --- |
| `Rc` | Radius of curvature of the surface | $R$ |
| `Thickness` | Distance to the next surface | $d$ |
| `Diameter` | Clear outer diameter | $D$ |
| `InDiameter` | Inner diameter for annular stop/obstruction | $D_{\mathrm{in}}$ |
| `k` | Conic constant | $k$ |
| `Glass` | Material after the interface | $n_2$ or material label |
| `TiltX`, `TiltY`, `TiltZ` | Surface rotation angles | $\theta_x,\theta_y,\theta_z$ |
| `DespX`, `DespY`, `DespZ` | Surface decenter/translation | $\Delta x,\Delta y,\Delta z$ |
| `Order` | Rotation/translation application order | geometric bookkeeping |
| `AxisMove` | Whether downstream optical axis follows the local transform | folded/off-axis bookkeeping |
| `ZNK` | Zernike coefficients on the surface | $a_j$ |
| `AspherData` | Asphere polynomial coefficients | $A_i$ |
| `Thin_Lens` | Thin-lens power shortcut | $f$ |
| `Diff_Ord` | Diffraction order for grating surfaces | $m$ |
| `Grating_D` | Groove spacing | $d_g$ |
| `Grating_Angle` | Groove orientation in the surface plane | $\gamma_g$ |
| `Mask_Type` | Aperture/obscuration mask mode | - |
| `SubAperture` | Local aperture scaling/decenter tuple | - |

### 2.2 Surface sag is a sum of components

`build_surface_function()` composes the surface from several possible terms:

- Zernike sag
- asphere sag
- conic sag
- axicon sag
- user-defined extra sag
- error map sag

Relevant code:

- `KrakenOS/SurfClass.py:282-304`
- `KrakenOS/SurfClass.py:319-350`

In abstract form, KrakenOS treats the surface as

$$
z=\sigma(x,y)
=
\sigma_{\mathrm{conic}}(x,y)
\sigma_{\mathrm{asphere}}(x,y)
\sigma_{\mathrm{zernike}}(x,y)
\sigma_{\mathrm{extra}}(x,y)
\sigma_{\mathrm{error}}(x,y)+\cdots
$$

The exact conic term is implemented in `MathShapesClass.py`, but the intended optical form is the usual conic sag

$$
z(r)=\frac{c r^2}{1+\sqrt{1-(1+k)c^2r^2}},
\qquad
c=\frac{1}{R},
\qquad
r^2=x^2+y^2.
$$

### 2.3 Surface type selects the physics law

KrakenOS chooses the per-surface physics object in `build_surface_function()`:

- normal refractive/reflective interface -> `snell_refraction_vector_physics`
- grating -> `diffraction_grating_physics`
- thin lens -> `paraxial_exact_physics`
- STL solid -> `snell_refraction_vector_physics`

Relevant code:

- `KrakenOS/SurfClass.py:282-317`

This split is important: the geometry and the physics law are separate.

## 3. Coordinate transforms and off-axis geometry

Relevant code:

- `KrakenOS/Prerequisites3D.py:83-150`

KrakenOS does not assume every surface is centered on the same axis. Instead it constructs per-surface transforms:

- `TRANS_1A[j]`: world/object space -> surface-local space
- `TRANS_2A[j]`: surface-local space -> world/object space

The local surface frame is the frame where the vertex plane is approximately at local `z = 0`. That is why the intersection code projects the ray onto `z = 0` before solving the actual sag intersection.

Two variables control the kinematics:

### `Order`

`Order` decides whether the transform sequence is

$$
\text{rotate} \to \text{translate}
$$

or

$$
\text{translate} \to \text{rotate}.
$$

See `KrakenOS/Prerequisites3D.py:116-150`.

### `AxisMove`

`AxisMove` scales whether a surface tilt/decenter contributes to the accumulated downstream optical-axis transform. In practical terms:

- `AxisMove = 1` means the optical axis generally follows the element transform.
- folded layouts often use values like `2.0` in the current codebase for mirror behavior in UI-generated systems and examples.

See `KrakenOS/Prerequisites3D.py:100-108`.

This is geometric bookkeeping, not a separate optics law.

## 4. Sequential tracing variables

Relevant code:

- `KrakenOS/KrakenSys.py:786-881`

The main sequential trace loop is `system.Trace(pS, dC, WaveLength)`.

### 4.1 Input variables

| Code variable | Meaning |
| --- | --- |
| `pS` | ray origin `[x,y,z]` |
| `dC` | incident direction cosines `[L,M,N]` |
| `WaveLength` | wavelength in micrometers |

### 4.2 Internal state variables

| Code variable | Meaning |
| --- | --- |
| `RayOrig` | current ray point in global space |
| `ResVec` | current ray direction after the last surface |
| `PrevN` | refractive index before the next interface |
| `CurrN` | refractive index after the interface |
| `SIGN` | forward/backward propagation sign bookkeeping |
| `j` | current surface index |
| `Proto_pTarget` | a far-away point used to define the incoming line toward the surface |
| `ImpVec` | the incident direction vector at the interface |
| `SurfNorm` | outward surface normal used by the physics law |
| `pTarget` | actual hit point on the surface |
| `GooveVect` | grating groove direction vector on the surface |
| `Ord` | grating diffraction order |
| `GrSpa` | groove spacing |

### 4.3 Trace step in equations

At each surface the code forms a long parametric line

$$
\mathbf{r}(t)=\mathbf{r}_\text{orig}+t(\hat{\mathbf{s}}\odot \mathbf{SIGN}),
$$

using a very large target distance. This line is passed to the intersection module.

Once the hit point and normal are found, the physics law updates the direction:

$$
\hat{\mathbf{s}}_{\text{out}} = \mathcal{P}
\left(
\hat{\mathbf{s}}_{\text{in}},
\hat{\mathbf{n}},
n_1,
n_2,
\ldots
\right).
$$

In code that is

- `Output = self.INORM.InterNormal(...)`
- `(ResVec, CurrN, sign, self.ang) = self.SDT[j].PHYSICS.calculate(...)`

See `KrakenOS/KrakenSys.py:819-852`.

## 5. Ray-surface intersection

Relevant code:

- `KrakenOS/InterNormalCalc.py:46-153`
- `KrakenOS/HitOnSurf.py:147-239`

This is the heart of the exact geometrical tracer.

### 5.1 Transform into local coordinates

In `InterNormalCalc.__SigmaHitTransfSpace()`, KrakenOS transforms both the current ray point and a far-away target point into the local coordinates of surface `j`.

Important local variables:

| Code variable | Meaning |
| --- | --- |
| `P_x1`, `P_y1`, `P_z1` | starting point in local surface coordinates |
| `Px1`, `Py1`, `Pz1` | target point in local coordinates |
| `L`, `M`, `N` | direction cosines in local surface coordinates |

The code then projects the line onto the local vertex plane `z = 0`:

$$
x_{\mathrm{proj}} = x_1 + \frac{L}{N}(0-z_1),
\qquad
y_{\mathrm{proj}} = y_1 + \frac{M}{N}(0-z_1).
$$

See `KrakenOS/InterNormalCalc.py:73-79`.

This gives a good initial point for the exact surface solve.

### 5.2 Aperture and obstruction check

Before and after the intersection solve, KrakenOS checks whether the candidate ray lands inside the usable aperture.

Important variables:

| Code variable | Meaning |
| --- | --- |
| `ASD` | radial distance from the local sub-aperture center |
| `D0` | doubled radial distance, used as effective diameter |
| `DiamInf` | inner allowed diameter |
| `DiamSup` | outer allowed diameter |

See `KrakenOS/InterNormalCalc.py:104-107` and `KrakenOS/InterNormalCalc.py:126-131`.

### 5.3 Newton solve for the exact intersection

In `Hit_Solver.SolveHit()`, KrakenOS solves the implicit equation

$$
F(z)=\sigma(x(z),y(z))-z=0
$$

with

$$
x(z)=x_1+\frac{L}{N}(z-z_1),
\qquad
y(z)=y_1+\frac{M}{N}(z-z_1).
$$

The code stores

$$
\frac{L}{N} \to \texttt{LN},
\qquad
\frac{M}{N} \to \texttt{MN}.
$$

See:

- `KrakenOS/HitOnSurf.py:197-201`
- `KrakenOS/HitOnSurf.py:159-168`
- `KrakenOS/HitOnSurf.py:203-215`

The Newton step is

$$
z_{k+1}=z_k-\frac{F(z_k)}{F'(z_k)}.
$$

This is implemented by `__DerLineCurve()` plus the iteration loop in `SolveHit()`.

### 5.4 Surface normal from the sag gradient

KrakenOS computes the surface normal numerically from the gradient of

$$
G(x,y,z)=\sigma(x,y)-z.
$$

Thus

$$
\nabla G=
\left[
\frac{\partial \sigma}{\partial x},
\frac{\partial \sigma}{\partial y},
-1
\right].
$$

The code uses finite differences and normalizes the result:

- `Dx`, `Dy`, `Dz` in `KrakenOS/HitOnSurf.py:69-89`

This is then transformed back to world coordinates by `InterNormalCalc.__SigmaOutOrigSpace()`.

## 6. Refraction, reflection, diffraction

### 6.1 Vector Snell law

Relevant code:

- `KrakenOS/PhysicsClass.py:39-121`

The main exact interface law is implemented in `snell_refraction_vector_physics.calculate()`.

Key variables:

| Code variable | Meaning | Symbol |
| --- | --- | --- |
| `Iv` | incident direction vector | $\hat{\mathbf{i}}$ |
| `Nv` | surface normal, flipped to face the incident ray | $\hat{\mathbf{n}}$ |
| `n1` | refractive index before the surface | $n_1$ |
| `n2` | refractive index after the surface | $n_2$ |
| `NN` | index ratio `n1/n2` | $\eta$ |
| `SIGN` | propagation sign flip used for mirrors/TIR | - |
| `ang` | incidence angle in degrees | $\theta_i$ |

The code uses the vector form

$$
\eta=\frac{n_1}{n_2},
\qquad
c_1=\left|\hat{\mathbf{n}}\cdot\hat{\mathbf{i}}\right|,
\qquad
c_2=\sqrt{1-\eta^2(1-c_1^2)},
$$

$$
\hat{\mathbf{t}}
=
\eta \hat{\mathbf{i}}
+(\eta c_1-c_2)\hat{\mathbf{n}}.
$$

That is exactly what appears in `KrakenOS/PhysicsClass.py:113-121`.

### 6.2 Total internal reflection

The code checks

$$
\eta^2 \|\hat{\mathbf{n}}\times \hat{\mathbf{i}}\|^2 > 1
$$

and then forces reflection by negating the effective post-interface index:

- `KrakenOS/PhysicsClass.py:99-110`

In current KrakenOS convention, mirror surfaces are also represented by a special index rule:

- if `n2 == -1.0`, treat the interface as reflective
- see `KrakenOS/PhysicsClass.py:95-97`

### 6.3 Diffraction grating

Relevant code:

- `KrakenOS/PhysicsClass.py:216-280`

Important variables:

| Code variable | Meaning |
| --- | --- |
| `Ord` | diffraction order $m$ |
| `d` | groove spacing |
| `P` | groove direction basis |
| `D` | cross-product direction used in the grating law |

The implementation is vectorial and does not use the scalar grating equation directly, but it is the same physics.

## 7. Energy, Fresnel coefficients, and optical path

Relevant code:

- `KrakenOS/Physics.py:27-121`
- `KrakenOS/KrakenSys.py:304-397`

### 7.1 Fresnel coefficients

For dielectrics, KrakenOS uses

$$
r_s=
\frac{n_0\cos\theta_0-n_1\cos\theta_1}
{n_0\cos\theta_0+n_1\cos\theta_1},
\qquad
r_p=
\frac{n_1\cos\theta_0-n_0\cos\theta_1}
{n_1\cos\theta_0+n_0\cos\theta_1}.
$$

Then

$$
R_s=|r_s|^2,
\qquad
R_p=|r_p|^2,
\qquad
T_s=1-R_s,
\qquad
T_p=1-R_p.
$$

See `KrakenOS/Physics.py:75-89`.

For metals, the code uses complex refractive index

$$
\tilde{n}=n+i k
$$

with wavelength-dependent `n` and `k` from the setup catalog. See `KrakenOS/Physics.py:91-121`.

### 7.2 Bulk transmission and optical path

In `system.__CollectData()`:

- geometric distance:
  $$
  d_j = \|\mathbf{r}_{j+1}-\mathbf{r}_j\|
  $$
- optical path increment:
  $$
  \mathrm{OP}_j=n_j d_j
  $$
- total optical path:
  $$
  \mathrm{TOP}=\sum_j \mathrm{OP}_j
  $$
- bulk absorption:
  $$
  T_{\mathrm{bulk},j}=e^{-\alpha_j d_j}
  $$

See:

- `KrakenOS/KrakenSys.py:339-347`
- `KrakenOS/KrakenSys.py:384-396`

Stored result variables:

| Code variable | Meaning |
| --- | --- |
| `DISTANCE` | geometric path length per segment |
| `OP` | optical path per segment |
| `TOP` | total optical path |
| `ALPHA` | bulk absorption coefficient history |
| `BULK_TRANS` | Beer-Lambert transmission per segment |
| `RP`, `RS`, `TP`, `TS` | Fresnel energy coefficients |
| `TTBE` | per-element transmitted/reflected energy contribution |
| `TT` | total throughput |

## 8. Dispersion and material variables

Relevant code:

- `KrakenOS/Physics.py:158-336`

`n_wave_dispersion()` converts a material label into:

- refractive index `n`
- bulk absorption coefficient `Alpha`

Important inputs:

| Code variable | Meaning |
| --- | --- |
| `GLSS` | material label (`AIR`, `MIRROR`, Schott glass, etc.) |
| `Wave` | wavelength in micrometers |
| `CD` | catalog dispersion coefficients |
| `IT` | transmission-vs-thickness data |

Important outputs:

| Code variable | Meaning |
| --- | --- |
| `n` | refractive index at the requested wavelength |
| `Alpha` | absorption coefficient used in bulk transmission |

The code supports multiple catalog formulas including Schott and Sellmeier families.

## 9. Paraxial optics

Relevant code:

- `KrakenOS/KrakenSys.py:588-603`
- `KrakenOS/Physics.py:338-410`

KrakenOS includes a first-order paraxial model in addition to the exact tracer.

### 9.1 Ray-transfer matrix variables

For each surface, the code builds:

- a refraction matrix `RR`
- a translation matrix `TT`

For a refracting surface:

$$
R_j=
\begin{bmatrix}
\dfrac{n_1}{n_2} & \dfrac{n_1-n_2}{n_2 R} \\
0 & 1
\end{bmatrix}
$$

For axial translation:

$$
T_j=
\begin{bmatrix}
1 & 0 \\
d_j & 1
\end{bmatrix}.
$$

This is implemented in `KrakenOS/Physics.py:382-390`.

The full system matrix is

$$
M=
\begin{bmatrix}
a & b \\
c & d
\end{bmatrix}.
$$

KrakenOS reports:

$$
\mathrm{EFFL}=-\frac{1}{b},
\qquad
\mathrm{PPA}=\frac{1-a}{-b},
\qquad
\mathrm{PPP}=\frac{d-1}{-b}.
$$

See `KrakenOS/Physics.py:401-407`.

### 9.2 Paraxial variables

| Code variable | Meaning |
| --- | --- |
| `a`, `b`, `c`, `d` | total ABCD matrix entries |
| `EFFL` | effective focal length |
| `PPA` | front principal plane position in KrakenOS sign convention |
| `PPP` | rear principal plane position in KrakenOS sign convention |
| `CC` | per-surface paraxial power proxy `1/R` |
| `DD` | per-gap axial distances |

Important caution:

The exact tracer is the ground truth for tilted/decentered systems. The paraxial solver is centered, first-order optics.

## 10. Pupil and field generation

Relevant code:

- `KrakenOS/PupilTool.py:515-691`
- `KrakenOS/PupilTool.py:722-827`
- `KrakenOS/PupilTool.py:832-900`

`PupilCalc` converts aperture and field settings into actual ray launches.

### 10.1 Entrance and exit pupil variables

Important variables:

| Code variable | Meaning |
| --- | --- |
| `Surf` | stop surface index |
| `ApertureType` | stop-based or EPD-based input |
| `ApertureValue` | the chosen aperture value |
| `RadPupInp` | entrance pupil radius |
| `PosPupInp` | entrance pupil position |
| `RadPupOut` | exit pupil radius |
| `PosPupOut` | exit pupil position in global coordinates |
| `DirPupSal` | chief-ray direction at pupil exit |
| `menter` | entrance pupil magnification factor |

KrakenOS estimates angular pupil magnification from traced probe rays:

$$
M_{\mathrm{enter}}=\frac{\theta_{\mathrm{obj}}}{\theta_{\mathrm{stop}}},
\qquad
M_{\mathrm{exit}}=\frac{\theta_{\mathrm{obj}}}{\theta_{\mathrm{image}}}.
$$

Then

$$
D_{\mathrm{EP}}=
\begin{cases}
\texttt{ApertureValue}, & \text{if ApertureType = EPD} \\
\dfrac{D_{\mathrm{stop}}}{M_{\mathrm{enter}}}, & \text{if ApertureType = STOP}
\end{cases}
$$

and

$$
D_{\mathrm{XP}}=D_{\mathrm{stop}}\,M_{\mathrm{exit}}.
$$

See `KrakenOS/PupilTool.py:645-656`.

### 10.2 Airy radius estimate

The code computes

$$
r_{\mathrm{Airy}}=
\frac{1.22\,\lambda\,\mathrm{EFFL}}{D_{\mathrm{EP}}}
=
\frac{1.22\,\lambda\,\mathrm{EFFL}}{2\,R_{\mathrm{EP}}}.
$$

See `KrakenOS/PupilTool.py:691`.

### 10.3 Field variables and launch rays

Important variables:

| Code variable | Meaning |
| --- | --- |
| `FieldType` | `angle` or `height` |
| `FieldX`, `FieldY` | field coordinates |
| `Ptype` | pattern type: `chief`, `fan`, `hexapolar`, `square`, `rand`, etc. |
| `Samp` | sampling density |
| `Cordx`, `Cordy` | normalized pupil coordinates |

For angle field mode, the launch shift is computed with

$$
\Delta x = z_p \tan(-\theta_x),
\qquad
\Delta y = z_p \tan(-\theta_y),
$$

and the direction cosines are built from the source point and pupil target.

See `KrakenOS/PupilTool.py:776-827`.

## 11. Exit pupil and wavefront phase

Relevant code:

- `KrakenOS/PhaseCalc.py:74-96`
- `KrakenOS/PhaseCalc.py:170-260`

The `Phase2()` workflow is used to estimate a precise exit pupil and generate phase data for diffraction analysis.

### 11.1 Best exit pupil position

`BestExitPupilPos()` searches a shift $\Delta Z$ that minimizes the RMS radius of the propagated ray bundle:

$$
R_{\mathrm{RMS}}(\Delta Z)
=
\sqrt{
\frac{1}{N}
\sum_i
\left[
\left(X_i+\frac{L_i}{N_i}\Delta Z-\bar{X}\right)^2
+
\left(Y_i+\frac{M_i}{N_i}\Delta Z-\bar{Y}\right)^2
\right]
}.
$$

See `KrakenOS/PhaseCalc.py:74-96`.

That is a geometrical way to locate the exit pupil plane from traced rays, not a pure first-order estimate.

### 11.2 Phase variables

Important variables in the phase path:

| Code variable | Meaning |
| --- | --- |
| `POZ` | estimated exit pupil axial position |
| `SampleX/Y/Z` | pupil sample launch points |
| `SampleL/M/N` | corresponding direction cosines |
| `chief_xyz`, `chief_lmn` | chief ray reference data |

## 12. PSF and MTF

Relevant code:

- `KrakenOS/PSFCalc.py:24-60`
- `KrakenOS/PSFCalc.py:89-189`

KrakenOS computes diffraction PSF and MTF from a wavefront expressed in Zernike coefficients.

### 12.1 Important variables

| Code variable | Meaning |
| --- | --- |
| `COEF` | Zernike coefficients of the wavefront |
| `Focal` | focal length used to scale the image-plane coordinates |
| `Diameter` | pupil diameter |
| `Wave` or `w` | wavelength |
| `pixels` | FFT grid size |
| `PupilSample` | oversampling factor |
| `W` | wavefront map on the normalized pupil |
| `T` | pupil transmission mask |
| `U` | complex pupil field |
| `I` | PSF irradiance |

### 12.2 Complex pupil and Fraunhofer PSF

The code forms

$$
U(\rho,\theta)=P(\rho,\theta)\,
\exp\!\left(-i2\pi W(\rho,\theta)\right),
$$

where:

- $P$ is the pupil mask,
- $W$ is the phase in waves.

Then it computes

$$
\mathrm{PSF} = \left|\mathcal{F}\{U\}\right|^2.
$$

See `KrakenOS/PSFCalc.py:41-49` and `KrakenOS/PSFCalc.py:147-158`.

### 12.3 MTF

The MTF path normalizes the PSF and computes the magnitude of its Fourier transform:

$$
\mathrm{MTF}(f_x,f_y)
=
\frac{\left|\mathcal{F}\{\mathrm{PSF}\}\right|}
\max\left|\mathcal{F}\{\mathrm{PSF}\}\right|}.
$$

See `KrakenOS/PSFCalc.py:51-60`.

## 13. Ray-result storage

Relevant code:

- `KrakenOS/RayKeeper.py:27-143`

`raykeeper` is the per-ray archive. It copies the state accumulated inside `system` after each call to `Trace()`.

Important stored arrays:

| Code variable | Meaning |
| --- | --- |
| `SURFACE` | surface indices traversed by the ray |
| `NAME` | surface names |
| `GLASS` | material labels |
| `S_XYZ` | segment start points |
| `T_XYZ` | segment end points |
| `XYZ` | full global ray polyline |
| `OST_XYZ` | surface-local hit coordinates |
| `S_LMN` | surface normals |
| `LMN` | incident direction vectors |
| `R_LMN` | exiting direction vectors |
| `N0`, `N1` | refractive indices before/after each interface |
| `DISTANCE`, `OP`, `TOP` | geometric and optical path data |
| `RP`, `RS`, `TP`, `TS`, `TT` | energy data |

If you want to debug the physical state of a ray, `raykeeper` is usually the first object to inspect.

## 14. GPU path

Relevant code:

- `KrakenOS/gpu_backend.py:1`
- `KrakenOS/KrakenSys.py:887-1020`
- `KrakenOS/HitOnSurf.py:245`
- `KrakenOS/PhysicsClass.py:123`
- `KrakenOS/PSFCalc.py:8-16`

KrakenOS now routes heavy array code through a common namespace:

- `xp = cupy` when GPU is available
- `xp = numpy` otherwise

This matters for:

- batch ray tracing
- batched Newton intersection
- batched Snell update
- FFT-heavy PSF/MTF

The physics is the same. Only the array backend changes.

## 15. Worked variable map

This is the compact "what does this name mean?" section.

### Surface geometry

| Variable | Meaning |
| --- | --- |
| `Rc` | radius of curvature |
| `k` | conic constant |
| `Thickness` | axial gap to next surface |
| `Diameter` | outer clear diameter |
| `InDiameter` | central obscuration diameter |
| `ZNK` | Zernike sag coefficients |
| `AspherData` | asphere coefficients |
| `ExtraData` | user-defined extra sag coefficients |
| `Error_map` | measured sag error map |
| `ShiftX`, `ShiftY` | sag-function offsets in local `x,y` |

### Coordinate transforms

| Variable | Meaning |
| --- | --- |
| `TiltX`, `TiltY`, `TiltZ` | surface rotations |
| `DespX`, `DespY`, `DespZ` | decenter/translation |
| `Order` | transform order |
| `AxisMove` | downstream axis-follow flag |
| `TRANS_1A` | world -> local transform |
| `TRANS_2A` | local -> world transform |

### Ray state

| Variable | Meaning |
| --- | --- |
| `pS`, `RayOrig` | current ray point |
| `dC`, `ImpVec`, `ResVec` | incident/current/output direction cosines |
| `L`, `M`, `N` | direction cosine components |
| `PrevN`, `CurrN` | refractive indices before/after the current surface |
| `SIGN` | sign bookkeeping for forward/backward propagation |
| `SurfNorm` | unit surface normal |
| `pTarget` | global hit point |
| `HitObjSpace` | hit point in the surface-local frame |
| `LMNObjSpace` | local incident direction |

### Newton intersection

| Variable | Meaning |
| --- | --- |
| `LN = L/N` | local slope in `x-z` |
| `MN = M/N` | local slope in `y-z` |
| `PP_z2` | current Newton iterate for the local hit `z` |
| `FdeX` | residual $F(z)$ |
| `DerFdeX` | derivative $F'(z)$ |

### Energy/path

| Variable | Meaning |
| --- | --- |
| `DISTANCE` | geometric path length per segment |
| `OP` | optical path per segment |
| `TOP` | total optical path |
| `RP`, `RS`, `TP`, `TS` | Fresnel coefficients |
| `TTBE` | per-element energy contribution |
| `TT` | total throughput |

### Paraxial

| Variable | Meaning |
| --- | --- |
| `a,b,c,d` | ABCD matrix entries |
| `EFFL` | effective focal length |
| `PPA`, `PPP` | front/rear principal plane positions in KrakenOS sign convention |
| `CC` | curvature proxy |
| `DD` | axial distances |

### Pupil and diffraction

| Variable | Meaning |
| --- | --- |
| `RadPupInp`, `RadPupOut` | entrance/exit pupil radius |
| `PosPupInp`, `PosPupOut` | entrance/exit pupil position |
| `FieldX`, `FieldY` | field coordinate |
| `Ptype`, `Samp` | ray pattern and density |
| `COEF` | wavefront Zernike coefficients |
| `pixels`, `PupilSample` | diffraction sampling controls |

## 16. Example use cases

### Example A: centered refractive imaging

Reference:

- `KrakenOS/Examples/Examp_Doublet_Lens.py`

Use this when you want to understand the minimum sequential workflow:

1. Create surfaces with `Rc`, `Thickness`, `Glass`, `Diameter`.
2. Build the list in optical order.
3. Instantiate `Kos.system(...)`.
4. Launch rays with `Trace(...)`.
5. Save results with `raykeeper.push()`.
6. Inspect `XYZ`, `DISTANCE`, `TOP`, or render with `display2d`.

What to watch in the code:

- `Rc`, `Thickness`, `Glass` define the optical power and spacing.
- `Trace()` updates `PrevN -> CurrN`, `ImpVec -> ResVec`.
- `raykeeper` stores the final image-plane cloud.

### Example B: folded mirror path

Reference:

- `KrakenOS/Examples/Examp_Flat_Mirror_45Deg.py`

Use this when you want to understand off-axis folding with a flat mirror.

Important variables:

- `Glass = "MIRROR"`
- `TiltX = 45.0`
- `AxisMove = 2.0`

What changes physically:

- the surface geometry is still solved exactly,
- the physics law becomes reflection,
- the global transform chain changes the downstream propagation direction.

### Example C: stop, pupil, and aberration bookkeeping

Reference:

- `KrakenOS/Examples/Examp_Doublet_Lens_Pupil_Seidel.py`

Use this when you want:

- entrance pupil diameter,
- exit pupil location,
- chief-ray field generation,
- Seidel-style aberration analysis.

Important variables:

- `AperType = "EPD"`
- `Surf = stop index`
- `Pup = Kos.PupilCalc(...)`
- `Pup.Ptype`, `Pup.Samp`, `Pup.FieldY`

### Example D: diffraction PSF/MTF from a wavefront

References:

- `KrakenOS/PhaseCalc.py`
- `KrakenOS/PSFCalc.py`

Use this when you already have a wavefront represented by `COEF`.

The flow is:

1. estimate pupil geometry,
2. obtain wavefront coefficients,
3. build complex pupil field,
4. FFT to PSF,
5. FFT again to MTF.

## 17. Practical reading order for the code

If you want to read the engine from top to bottom without getting lost, use this order:

1. `KrakenOS/SurfClass.py`
2. `KrakenOS/KrakenSys.py`
3. `KrakenOS/InterNormalCalc.py`
4. `KrakenOS/HitOnSurf.py`
5. `KrakenOS/PhysicsClass.py`
6. `KrakenOS/Physics.py`
7. `KrakenOS/RayKeeper.py`
8. `KrakenOS/PupilTool.py`
9. `KrakenOS/PhaseCalc.py`
10. `KrakenOS/PSFCalc.py`

That order follows the actual data flow.

## 18. What to inspect when debugging

If a traced layout looks physically wrong, inspect these variables first:

1. `Rc`, `Thickness`, `Glass`, `Diameter`
2. `TiltX/Y/Z`, `DespX/Y/Z`, `AxisMove`
3. `XYZ`, `OST_XYZ`
4. `LMN`, `R_LMN`, `S_LMN`
5. `N0`, `N1`
6. `DISTANCE`, `OP`, `TOP`
7. `RadPupInp`, `PosPupOut`, `EFFL`, `PPA`, `PPP`

That short list usually localizes the error to one of:

- geometry definition,
- transform propagation,
- intersection failure,
- wrong normal orientation,
- wrong refractive index assignment,
- wrong pupil sampling,
- wrong paraxial assumption.

## 19. Bottom line

KrakenOS is built around one core idea:

- represent each surface as a local sag function plus a local physics law,
- transform each incoming ray into that local frame,
- solve the exact hit,
- compute the normal,
- apply vector Snell/reflection/grating physics,
- transform back and store the full optical history.

Everything else in the library - paraxial solvers, pupil tools, PSF/MTF, UI, and optimization - is layered on top of that engine.
