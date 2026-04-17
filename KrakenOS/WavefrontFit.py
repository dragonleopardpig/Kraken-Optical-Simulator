import numpy as np
from .MathShapesClass import *
from .gpu_backend import xp, to_cpu, to_gpu

def RMS_Fitting_Error(SA, X, Y, Z, Zern_pol, z_pow):
    """RMS.

    Parameters
    ----------
    SA :
        SA
    X :
        X
    Y :
        Y
    Z :
        Z
    Zern_pol :
        Zern_pol
    z_pow :
        z_pow
    """
    NZ = []
    SE = np.copy(SA)
    NZ = Wavefront_Phase(X, Y, SE, Zern_pol, z_pow)
    NZ = np.asarray(NZ)

    g = (NZ - Z)
    g = (g * g)
    g = np.mean(g)
    error = np.sqrt(g)

    return (error)

def Zernike_Fitting(x1, y1, Z1, Arr, minimum=0.000000001):
    """Zernike_Fitting.

    Parameters
    ----------
    x1 :
        x1
    y1 :
        y1
    Z1 :
        Z1
    A :
        A
    minimum :
        minimum
    """

    NC = len(Arr)
    (Zern_pol, z_pow) = zernike_expand(NC)
    for i in range(0, 2):
        Zi = System_Matrix_Zernikes(x1, y1, Arr, Zern_pol, z_pow, 0)
        # Use lstsq instead of explicit normal equations — faster and
        # numerically more stable.
        D = np.asarray(Z1).reshape(-1, 1)
        MA, _, _, _ = np.linalg.lstsq(Zi, D, rcond=None)
        MA = MA.reshape(-1)

        SA = np.zeros_like(Arr)
        NA = Arr.shape[0]

        cont = 0
        ZZ = []
        for i1 in range(0, Arr.shape[0]):
            ZZ.append(zernike_math_notation(i1, Zern_pol, z_pow))
        ZZ = np.asarray(ZZ)
        for i2 in range(0, NA):
            if (Arr[i2] != 0):
                SA[i2] = MA[cont]
                cont = (cont + 1)
            else:
                SA[i2] = 0.0
        Arr = np.abs(SA)
        Zeros = np.argwhere((Arr > minimum))
        AA = np.zeros_like(Arr)
        AA[Zeros] = 1
        Arr = AA
    FITTINGERROR= RMS_Fitting_Error(SA, x1, y1, Z1, Zern_pol, z_pow)

    SE=np.copy(SA)
    SE[0]=0
    RMS2Chief=np.sqrt(np.sum(SE**2.0))

    SE[1]=0
    SE[2]=0
    RMS2Centroid=np.sqrt(np.sum(SE**2.0))

    return (SA, ZZ, RMS2Chief, RMS2Centroid, FITTINGERROR)

def Wavefront_Zernike_Phase(x, y, COEF):
    """Wavefront_Zernike_Phase.

    Parameters
    ----------
    x :
        x
    y :
        y
    COEF :
        COEF
    """
    _xp = xp  # Use GPU array module when available
    NC = len(COEF)
    (Zern_pol, z_pow) = zernike_expand(NC)
    tcoef = COEF.shape[0]
    # Ensure x, y live on the compute device
    x = _xp.asarray(x)
    y = _xp.asarray(y)
    p = _xp.sqrt(((x * x) + (y * y)))
    f = _xp.arctan2(x, y)
    ZFP = _xp.zeros_like(p, dtype=float)
    for i in range(0, tcoef):
        if (COEF[i] != 0):
            ZFP = (ZFP + (COEF[i] * zernike_polynomials(i, p, f, Zern_pol, z_pow)))
    return ZFP

def Wavefront_Phase(x, y, COEF, Zern_pol, z_pow):
    """Wavefront_Phase.

    Parameters
    ----------
    x :
        x
    y :
        y
    COEF :
        COEF
    Zern_pol :
        Zern_pol
    z_pow :
        z_pow
    """
    tcoef = COEF.shape[0]
    p = np.sqrt(((x * x) + (y * y)))
    f = np.arctan2(x, y)
    ZFP = 0.0
    for i in range(0, tcoef):
        if (COEF[i] != 0):
            ZFP = (ZFP + (COEF[i] * zernike_polynomials(i, p, f, Zern_pol, z_pow)))
    return ZFP

def Wf_XY_Components(x, y, N, Zern_pol, z_pow):
    """Wf_XY_Components.

    Parameters
    ----------
    x :
        x
    y :
        y
    N :
        N
    Zern_pol :
        Zern_pol
    z_pow :
        z_pow
    """
    A = np.zeros(Zern_pol.shape[0])
    A[N] = 1.0
    z = Wavefront_Phase(x, y, A, Zern_pol, z_pow)
    return z

def System_Matrix_Zernikes(x, y, A, Zern_pol, z_pow, fz):
    """System_Matrix_Zernikes — vectorized.

    Build the Zernike design matrix for all pupil points at once instead
    of looping element-by-element.

    Parameters
    ----------
    x :
        x
    y :
        y
    A :
        A
    Zern_pol :
        Zern_pol
    z_pow :
        z_pow
    fz :
        fz
    """
    NA = np.argwhere((A == 1)).ravel()
    n_NA = NA.shape[0]
    Tp = x.shape[0]

    # Precompute rho and theta for all points
    p = np.sqrt(x * x + y * y)
    f = np.arctan2(x, y)

    ZU = np.zeros((Tp, n_NA))
    # Vectorised over all Tp points per Zernike term
    for n in range(n_NA):
        term_idx = int(NA[n])
        ZU[:, n] = zernike_polynomials(term_idx, p, f, Zern_pol, z_pow)
    return ZU
