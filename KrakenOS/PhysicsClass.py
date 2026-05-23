
import numpy as np
from .Physics import *
from .gpu_backend import xp, to_cpu



def custom_cross_product(a, b):
    """
    Calcula el producto cruz entre dos vectores de 3 elementos.

    Parámetros:
    - a: Primer vector (ndarray de NumPy con 3 elementos).
    - b: Segundo vector (ndarray de NumPy con 3 elementos).

    Retorna:
    - ndarray de NumPy con el resultado del producto cruz.
    """
    if a.shape[0] != 3 or b.shape[0] != 3:
        raise ValueError("Ambos vectores deben tener exactamente 3 elementos.")

    result = np.array([a[1]*b[2] - a[2]*b[1],
                       a[2]*b[0] - a[0]*b[2],
                       a[0]*b[1] - a[1]*b[0]])
    return result



class snell_refraction_vector_physics():
    """snell_refraction_vector_physics.
    """


    def __init__(self):
        """__init__.
        """
        pass

    def calculate(self, s1_norm, Nsurf_norm, n1, n2, empty1, empty2, empty3, empty4, Secuen):
        """calculate.

        Parameters
        ----------
        s1_norm :
            s1_norm
        Nsurf_norm :
            Nsurf_norm
        n1 :
            n1
        n2 :
            n2
        empty1 :
            empty1
        empty2 :
            empty2
        empty3 :
            empty3
        empty4 :
            empty4
        Secuen :
            Secuen
    r = rayo
    r'=reflejado
    S=normal superficie
        """


        Nv = np.asarray(Nsurf_norm)
        Iv = np.asarray(s1_norm)


        """ checking if the normal to the surface is in the
        direction of space where the ray is coming from and
        not where it is going """

        cos=np.dot(Nv, Iv)


        if (cos < (- 1.0)):
            ang = 180.0
        else:
            ang = np.rad2deg(np.arccos(np.clip(cos, -1.0, 1.0)))

        if (ang <= 90.0):
            Nv = - Nv
        else:
            ang = 180 - ang
        """----------------------------------------------"""


        Nsurf_Cros_s1 = custom_cross_product(Nv, Iv)

        SIGN = 1.0

        if (n2 == - 1.0):
            n2 = - n1
            SIGN = -1.0

        NN = (n1 / n2)
        d22=np.dot(Nsurf_Cros_s1, Nsurf_Cros_s1)
        R = (NN * NN) * d22

        if (Secuen == 1.0):
            R = 2.0

        if (R > 1.0):
            # Replexion total interna
            n2 = - n1
            NN = n1 / n2
            SIGN = -1.0
            # print("Reflexion total interna")

        c1 = np.dot(Nv,Iv)
        if c1 < 0.0 :
            c1 = np.dot(-Nv,Iv)
        IP = ((NN**2)*(1-(c1**2.0)))

        c2 = np.sqrt(max(0.0, 1.0-IP))
        T = NN * Iv + ((( NN * c1 ) - c2)) * Nv

        return T, np.abs(n2), SIGN, ang

def batch_snell_refraction(S_batch, Nsurf_batch, n1, n2, Secuen=0):
    """Vectorised Snell's law for N rays.

    Uses ``xp`` (CuPy on GPU, NumPy on CPU) for all array operations.

    Parameters
    ----------
    S_batch : (N, 3) incident ray direction cosines (normalised)
    Nsurf_batch : (N, 3) surface normals (normalised)
    n1 : scalar or (N,) refractive index before surface
    n2 : scalar refractive index after surface
    Secuen : scalar, 1 for forced reflection

    Returns
    -------
    T_batch : (N, 3) refracted/reflected direction cosines
    abs_n2 : (N,) absolute refractive index after
    SIGN : (N,) sign flips for propagation direction
    ang : (N,) incidence angles in degrees
    """
    S_batch = xp.asarray(S_batch, dtype=float)
    Nsurf_batch = xp.asarray(Nsurf_batch, dtype=float)

    N_rays = S_batch.shape[0]
    Iv = S_batch
    Nv = Nsurf_batch.copy()

    n1_arr = xp.broadcast_to(xp.asarray(n1, dtype=float), (N_rays,)).copy()

    # Flip normals so they face the incoming ray
    cos_vals = xp.sum(Nv * Iv, axis=1)
    ang = xp.where(cos_vals < -1.0, 180.0,
                    xp.rad2deg(xp.arccos(xp.clip(cos_vals, -1.0, 1.0))))
    flip_mask = ang <= 90.0
    Nv[flip_mask] = -Nv[flip_mask]
    ang = xp.where(flip_mask, ang, 180.0 - ang)

    SIGN = xp.ones(N_rays)
    n2_scalar = float(n2)
    n2_arr = xp.full(N_rays, n2_scalar, dtype=float)

    # Handle mirror (n2 == -1)
    if n2_scalar == -1.0:
        n2_arr[:] = -n1_arr
        SIGN[:] = -1.0

    NN = n1_arr / n2_arr

    # Cross product magnitude squared for TIR check
    cross = xp.cross(Nv, Iv)
    d22 = xp.sum(cross * cross, axis=1)
    R = (NN**2) * d22

    # Forced reflection
    if Secuen == 1.0:
        R[:] = 2.0

    # Total internal reflection
    tir_mask = R > 1.0
    n2_arr[tir_mask] = -n1_arr[tir_mask]
    NN[tir_mask] = n1_arr[tir_mask] / n2_arr[tir_mask]
    SIGN[tir_mask] = -1.0

    # Snell vector form
    c1 = xp.sum(Nv * Iv, axis=1)
    c1 = xp.where(c1 < 0.0, xp.sum(-Nv * Iv, axis=1), c1)
    IP = (NN**2) * (1.0 - c1**2)
    c2 = xp.sqrt(xp.clip(1.0 - IP, 0.0, None))

    T_batch = NN[:, None] * Iv + ((NN * c1 - c2))[:, None] * Nv

    return T_batch, xp.abs(n2_arr), SIGN, ang


class paraxial_exact_physics():
    """paraxial_exact_physics.
    """

    def __init__(self):
        """__init__.
        """
        pass

    def calculate(self, s1_norm, Nsurf_norm, n1, n2, empty1, empty2, empty3, empty4, empty5):
        """calculate.

        Parameters
        ----------
        s1_norm :
            s1_norm
        Nsurf_norm :
            Nsurf_norm
        n1 :
            n1
        n2 :
            n2
        empty1 :
            empty1
        empty2 :
            empty2
        empty3 :
            empty3
        empty4 :
            empty4
        empty5 :
            empty5
        """
        return (Nsurf_norm, 1, 1, 0)

class diffraction_grating_physics():
    """diffraction_grating_physics.
    """

    def __init__(self):
        """__init__.
        """
        pass

    def calculate(self, S, R, N, Np, P, Ord, d, W, Secuent):

        cos=np.dot(R,S)
        Ang=np.rad2deg(np.arccos( cos))

        ang = Ang

        if (cos < (- 1.0)):
            ang = 180.0
        else:
            ang = np.rad2deg(np.arccos(cos))

        if (ang >= 90.0):
            ang = 180 - ang


        if np.abs(Ang) < 90:
            R = -R


        """calculate.

        Parameters
        ----------
        S :
            S
        R :
            R
        N :
            N
        Np :
            Np
        D :
            D
        Ord :
            Ord
        d :
            d
        W :
            W
        Secuent :
            Secuent
        """

        D = custom_cross_product(R, P)

        lamb = W
        RefRef = ((- 1.) * np.sign(Np))
        SIGN = 1.

        if (Np == (- 1.)):
            Np = np.abs(N)

        mu = (N / Np)
        T = ((Ord * lamb) / (Np * d))

        V = (mu * np.dot(R,S))
        W = ((((mu ** 2.0) - 1.) + (T ** 2.0)) - (((2.0 * mu) * T) * np.dot(D,S)))

        Q1 = ( np.sqrt((V**2 - W))) - V
        Q2 = (-np.sqrt((V**2 - W))) - V

        if RefRef == 1:
            if Q1 > Q2:
                Q = Q1
            else:
                Q = Q2

        if RefRef == -1:
            if Q1 < Q2:
                Q = Q1
            else:
                Q = Q2

        S = np.asarray(S)
        Sp = (((mu * S) - (T * D)) + (Q * R))
        SIGN = SIGN*-1*RefRef
        return (Sp, np.abs(Np), SIGN, ang)
