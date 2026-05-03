import numpy as np
import os
import sys
import random
import inspect
from .SurfTools import surface_tools as SUT
from .Prerequisites3D import *
from .Physics import *
from .HitOnSurf import *
from .InterNormalCalc import *
from .ParaxialMatrix import build_paraxial_matrix_trace
from .gpu_backend import xp, to_cpu, to_gpu
import timeit
import copy



def prob(pro):
    """prob.

    Parameters
    ----------
    pro :
        pro
    """
    a_list = [0, 1]
    prob = pro
    distribution = [prob, (1.0 - prob)]
    random_number = random.choices(a_list, distribution)
    return random_number



class system():

    """system.
            SYSTEM CLASS ATRIBUTES AND IMPLEMENTATIONS:


          system.Trace (pS, dC, wV)
             Sequential ray tracing.
             pS = [1.0, 0.0, 0.0] – Ray origin coordinates
             dC = [0.0,0.0,1.0] - The directing cosines
             wV = 0.4 - Wavelength


          system.NsTrace (pS, dC, wV)
             Non-Sequential ray tracing


          system.Parax (w)
             Paraxial optics calculations


          system.disable_inner
             Enables the central aperture.


          system.enable_inner
             Disables the central aperture.


          system.SURFACE
	    Returns the surfaces the ray passed through.


          system.NAME
        	    Returns surface names that the ray passed through


          system.GLASS
        	    Returns materials that the ray passed through.


          system.XYZ
             [X, Y, Z] ray coordinates from its origin to the image plane.


          system.OST_XYZ
             [X, Y, Z] coordinates of ray intersections in reference to
            a coordinate system at its vertex, even if this vertex has
            a translation or rotation.


          system.DISTANCE
             List of distances traveled by the ray.


          system.OP
        	List of optical paths.


          system.TOP
        	Total optical path.


          system.TOP_S     List of the ray's optical path by sections.


          system.ALPHA
             List the materials absorption coefficients


          system.BULK_TRANS
             List the transmission through all the system absorption
             coefficients are considered.


          system.S_LMN
             Surface normal direction cosines [L, M, N].


          system.LMN
             incident ray direction cosines [L, M, N].


          system.R_LMN
             Resulting ray direction cosines [L, M, N].


          system.N0
             Refractive indices before and after each interface


          system.N1
             Refractive indices after each interface.
             This is useful to differentiate between index
             before and after an iteration. Example:

             N0 = [n1, n2, n3, n4, n5]
             N1 = [n2, n3, n4, n5, n5]


          system.WAV
        	    Wavelength of the ray (µm)


          system.G_LMN
             [L, M, N] Direction cosines that define the lines
             on the diffraction grating on the plane.


          system.ORDER
        	     Ray diffraction order.


          system.GRATING_D
	     Distance between lines of the diffraction grating.
             Units (Microns)


          system.RP
	     Fresnel reflection coefficients for polarization P.


          system.RS
             Fresnel reflection coefficients for polarization S.


          system.TP
            Fresnel transmission coefficients for polarization P.


          system.TS
            Fresnel transmission coefficients for polarization S.


          system.TTBE
            Total energy transmitted or reflected per element.


          system.TT
            Total energy transmitted or reflected total.


          system.targ_surf (int)
            Limits the ray tracing to the defined surface


          system.flat_surf (int)
            Change a surface to flat.

    """


    def __init__(self, SurfData, KN_Setup, build = 1):
        """__init__.

        Parameters
        ----------
        SurfData :
            SurfData
        KN_Setup :
            KN_Setup
        """


        SDT = []

        for i in range(0, len(SurfData)):
            SDT.append(SurfData[i])


        self.SDT = SDT
        self.SDT_0 = self.SDT
        self.SETUP = KN_Setup

        self.BUILD = build
        self.build()



    def build(self):
        """__init__.

        Parameters
        ----------
        SurfData :
            SurfData
        KN_Setup :
            KN_Setup
        """

        self.Next = 1.0 #Air Refraction index
        self.ExectTime=[]

        self.update = False
        self.S_Matrix = []
        self.N_Matrix = []
        self.SistemMatrix = np.matrix([[1.0, 0.0], [0.0, 1.0]])
        (self.a, self.b, self.c, self.d, self.EFFL, self.PPA, self.PPP) = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self.n = len(self.SDT)
        for ii in range(0, self.n):
            self.SDT[ii].SaveSetup()
        self.SuTo = SUT(self.SDT)
        self.SuTo_0 = SUT(self.SDT_0)

        self.Object_Num = np.arange(0, self.n, 1)
        self.Targ_Surf = self.n
        self.SuTo.Surface_Flattener = 0
        self.Disable_Inner = 1
        self.ExtraDiameter = 0
        self.SuTo.ErrSurfCase = 0
        self.__SurFuncSuscrip()


        self.Pr3D = Prerequisites(self.SuTo)
        self.Pr3D.Prerequisites3SMath()
        
        self.Pr3D.Prerequisites3D_UDA()
        
        if self.BUILD == 1:
            self.Pr3D.Prerequisites3DSolids()
        else:
            self.Pr3D.Prerequisites3DSolidsDummy()

        self.SDT_0 = self.SDT
        self.AAA = self.Pr3D.AAA
        self.BBB = self.Pr3D.BBB
        self.DDD = self.Pr3D.DDD
        self.EEE = self.Pr3D.EEE

        

        self.__PrerequisitesGlass()
        
        self.GlassOnSide = self.Pr3D.GlassOnSide
        self.side_number = self.Pr3D.side_number
        self.TypeTotal = self.Pr3D.TypeTotal
        
        self.TRANS_1A = self.Pr3D.TRANS_1A
        self.TRANS_2A = self.Pr3D.TRANS_2A

        self.HS = Hit_Solver(self.SDT)
        self.INORM = InterNormalCalc(self.SDT, self.TypeTotal, self.Pr3D, self.HS)
        self.INORM.Disable_Inner = 1
        self.Pr3D.Disable_Inner = 1
        (self.c_p, self.n_p, self.d_p) = (0.0, 0.0, 0.0)

        self.tt=1.
        self.energy_probability = 0
        self.NsLimit = 200
        self.ang = 0
        self.PreWave = (- 1e-09)
        self.NS_BRANCH_RESULTS = []
        self._collect_tt_override = None


    def __SurFuncSuscrip(self):
        """__SurFuncSuscrip.
        """
        for i in range(0, self.n):
            self.SDT[i].build_surface_function()

    def __PrerequisitesGlass(self):
        """__PrerequisitesGlass.
        """
        self.Glass = []
        self.GlobGlass = []
        for i in range(0, self.n):
            if (type(self.SDT[i].Glass)!=str) and (type(self.SDT[i].Glass) in [float, int]):
                # refractive index is manually entered
                self.SDT[i].Glass = ('manual_n,' + str(self.SDT[i].Glass))

            rpc = self.SDT[i].Glass.replace(' ', ',')
            self.Glass.append(rpc)
            self.GlobGlass.append(rpc)
            if ((self.GlobGlass[i] == 'NULL') or (self.GlobGlass[i] == 'ABSORB')):
                self.GlobGlass[i] = self.GlobGlass[(i - 1)]


    def __NonSequentialChooserToot(self, A_RayOrig, A_Proto_pTarget, k):
        """__NonSequentialChooserToot.

        Parameters
        ----------
        A_RayOrig :
            A_RayOrig
        A_Proto_pTarget :
            A_Proto_pTarget
        k :
            k
        """
        ng = self.GlassOnSide[k]
        A_Glass = self.SDT[ng].Glass
        if (A_Glass == 'NULL'):
            distance = 99999999999999.9
        else:
            (A_pTarget, A_SurfHit) = self.EEE[k].ray_trace(A_RayOrig, A_Proto_pTarget)
            if (len(A_SurfHit) == 0):
                distance = 99999999999999.9
            else:
                s = 0
                h = []
                for f in A_SurfHit:
                    PD = (np.asarray(A_pTarget[s]) - np.asarray(A_RayOrig))
                    distance = np.linalg.norm(PD)
                    if (np.abs(distance) < 0.05):
                        distance = 99999999999999.9
                    h.append(distance)
                    s = (s + 1)
                distance = np.min(np.asarray(h))
        return distance

    def __NonSequentialChooser(self, SIGN, A_RayOrig, ResVec, j):
        """__NonSequentialChooser.

        Parameters
        ----------
        SIGN :
            SIGN
        A_RayOrig :
            A_RayOrig
        ResVec :
            ResVec
        j :
            j
        """
        chooser = []
        [SLL, SMM, SNN] = ResVec
        distance = 99999999999999.9
        [Px, Py, Pz] = A_RayOrig
        [LL, MM, NN] = ResVec
        A_Proto_pTarget = (np.asarray(A_RayOrig) + ((np.asarray(ResVec) * 999999999.9) * SIGN))
        for k in range(1, len(self.EEE)):
            distance = self.__NonSequentialChooserToot(A_RayOrig, A_Proto_pTarget, k)
            chooser.append(distance)
        chooser = np.asarray(chooser)
        jj = (np.argmin(chooser) + 1)
        chooser[(jj - 1)] = 99999999999999.9
        kk = (np.argmin(chooser) + 1)
        (A_pTarget, A_SurfHit) = self.EEE[int(jj)].ray_trace(A_RayOrig, A_Proto_pTarget)
        PRR = np.shape(A_SurfHit)[0]
        return (int(j), int(jj), int(kk), PRR)

    def __CollectDataInit(self):
        """__CollectDataInit.
        """
        self.val = 1
        self.SURFACE = []
        self.NAME = []
        self.GLASS = []
        self.S_XYZ = []
        self.T_XYZ = []
        self.XYZ = []
        self.XYZ.append([0.0,  0.0 , 0.0])

        self.OST_XYZ = []
        self.OST_XYZ.append([0.0,  0.0 , 0.0])
        self.OST_LMN = []

        self.S_LMN = []
        self.LMN = []
        self.R_LMN = []
        self.N0 = []
        self.N1 = []
        self.WAV = 1.0
        self.G_LMN = []
        self.ORDER = []
        self.GRATING = []
        self.DISTANCE = []
        self.OP = []
        self.TOP_S = []
        self.TOP = 0
        self.ALPHA = [0.0, 0.0]
        self.BULK_TRANS = []
        self.RP = []
        self.RS = []
        self.TP = []
        self.TS = []
        self.TTBE = []
        self.TT = 1.0
        self._collect_tt_override = None
        return None

    def __EmptyCollect(self, pS, dC, WaveLength, j):
        """__EmptyCollect.

        Parameters
        ----------
        pS :
            pS
        dC :
            dC
        WaveLength :
            WaveLength
        j :
            j
        """
        Empty = np.asarray([])
        RayTraceType = 0
        ang = 0
        EmptyGlass = "AIR"
        ValToSav = [EmptyGlass, Empty, pS, pS, Empty, Empty, dC, Empty, Empty, Empty, WaveLength, Empty, Empty, Empty, Empty, Empty, j, RayTraceType]
        self.__CollectData(ValToSav)

    def __WavePrecalc(self):
        """__WavePrecalc.
        """
        if (self.Wave != self.PreWave):
            self.N_Prec = []
            self.AlphaPrecal = []
            self.PreWave = self.Wave

            for i in range(0, self.n):
                (NP, AP) = n_wave_dispersion(self.SETUP, self.GlobGlass[i], self.Wave)
                self.N_Prec.append(NP)
                self.AlphaPrecal.append(AP)


    def __CollectData(self, ValToSav):
        """__CollectData.

        Parameters
        ----------
        ValToSav :
            ValToSav
        """
        [Glass, alpha, RayOrig, pTarget, HitObjSpace, LMNObjSpace, SurfNorm, ImpVec, ResVec, PrevN, CurrN, WaveLength, D, Ord, GrSpa, Name, j, RayTraceType] = ValToSav


        self.SURFACE.append(j)
        self.NAME.append(Name)
        self.GLASS.append(Glass)
        self.S_XYZ.append(RayOrig)
        self.T_XYZ.append(pTarget)
        self.XYZ[0] = self.S_XYZ[0]
        self.XYZ.append(pTarget)
        self.OST_XYZ.append(HitObjSpace)
        self.OST_LMN.append(LMNObjSpace)

        p = (np.asarray(RayOrig) - np.asarray(pTarget))
        dist = np.linalg.norm(p)
        self.DISTANCE.append(dist)
        self.OP.append((dist * PrevN))

        self.TOP = (self.TOP + (dist * PrevN))
        self.TOP_S.append(self.TOP)
        self.ALPHA.append(alpha)
        self.S_LMN.append(SurfNorm)
        self.LMN.append(ImpVec)
        self.R_LMN.append(ResVec)
        self.N0.append(PrevN)
        self.N1.append(CurrN)
        self.WAV = WaveLength
        self.G_LMN.append(D)
        self.ORDER.append(Ord)
        self.GRATING.append(GrSpa)
        if (self.val == 1):
            # Coating
            Rp2, Rs2, Tp2, Ts2, V  = self.CoatingFun(self.SDT[j].Coating, self.ang, self.Wave)
            mtl = self.SDT[j].CoatingMet
            (Rp, Rs, Tp, Ts) = FresnelEnergy(Glass, PrevN, CurrN, ImpVec, SurfNorm, ResVec, self.SETUP, self.Wave, mtl)
            if V == 1:
                Rp, Rs, Tp, Ts = Rp2, Rs2, Tp2, Ts2
        else:
            (Rp, Rs, Tp, Ts) = (0, 0, 0, 0)
        self.RP.append(Rp)
        self.RS.append(Rs)
        self.TP.append(Tp)
        self.TS.append(Ts)
        if ((RayTraceType == 0) or (RayTraceType == 1)):

            if (Glass == 'MIRROR'):
                self.tt = ((1.0 * (Rp + Rs)) / 2.0)
                self.BULK_TRANS.append(self.tt)
            if (Glass != 'MIRROR'):
                IT = np.exp(((- self.ALPHA[-2]) * dist))

                self.BULK_TRANS.append(IT)
                self.tt = (Tp + Ts) / 2.0
        else:
            self.tt = 1.0

        if self._collect_tt_override is not None:
            self.tt = float(self._collect_tt_override)
            self._collect_tt_override = None

        if not self.tt:
            self.tt=0

        if len(self.BULK_TRANS) == 0:
            self.BULK_TRANS=[1]

        self.TTBE.append(self.tt*self.BULK_TRANS[-1])
        self.TT = (self.TT * self.tt*self.BULK_TRANS[-1])

        return None

    def CoatingFun(self, TRA, Theta, wav):
        R = np.asarray(TRA[0], dtype=float)
        A = np.asarray(TRA[1], dtype=float)
        W = np.asarray(TRA[2], dtype=float).ravel()
        THETA = np.asarray(TRA[3], dtype=float).ravel()
        if len(THETA) == 0 or len(W) == 0:
            V = 0
            Rp, Rs, Tp, Ts = 0, 0, 0, 0
        else:
            V = 1
            if R.shape != (THETA.size, W.size) or A.shape != (THETA.size, W.size):
                raise ValueError("Coating tables must have shape len(THETA) x len(W)")

            order_theta = np.argsort(THETA)
            order_w = np.argsort(W)
            theta_grid = THETA[order_theta]
            wave_grid = W[order_w]
            r_grid = R[np.ix_(order_theta, order_w)]
            a_grid = A[np.ix_(order_theta, order_w)]

            def _interp_table(table):
                by_wave = np.asarray([
                    np.interp(wav, wave_grid, row, left=row[0], right=row[-1])
                    for row in table
                ], dtype=float)
                return float(np.interp(Theta, theta_grid, by_wave, left=by_wave[0], right=by_wave[-1]))

            R_value = min(max(_interp_table(r_grid), 0.0), 1.0)
            A_value = min(max(_interp_table(a_grid), 0.0), 1.0)
            T_value = min(max(1.0 - R_value - A_value, 0.0), 1.0)

            Rp, Rs, Tp, Ts = R_value, R_value, T_value, T_value

        return Rp, Rs, Tp, Ts, V


    def RestoreData(self):
        """RestoreData.
        """
        for ii in range(0, self.n):
            self.SDT[ii].RestoreSetup()
        self.SetData()

    def StoreData(self):
        """StoreData.
        """
        for ii in range(0, self.n):
            self.SDT[ii].SaveSetup()
        self.SetData()

    def SetData(self):
        """SetData.
        """
        self.SuTo = SUT(self.SDT)
        self.Object_Num = np.arange(0, self.n, 1)
        self.__SurFuncSuscrip()
        self.Pr3D.Prerequisites3SMath()
        self.INORM = InterNormalCalc(self.SDT, self.TypeTotal, self.Pr3D, self.HS)

    def SetSolid(self):
        """SetSolid.
        """
        self.__SurFuncSuscrip()
        self.Pr3D.Prerequisites3SMath()
        self.Pr3D.Prerequisites3D_UDA()
        
        self.Pr3D.Prerequisites3DSolids()
        self.INORM = InterNormalCalc(self.SDT, self.TypeTotal, self.Pr3D, self.HS)
        self.AAA = self.Pr3D.AAA
        self.BBB = self.Pr3D.BBB
        self.DDD = self.Pr3D.DDD
        self.EEE = self.Pr3D.EEE
        self.TRANS_1A = self.Pr3D.TRANS_1A
        self.TRANS_2A = self.Pr3D.TRANS_2A

    def __ParaxialIndexList(self, W):
        N_P = []
        for i in range(0, self.n):
            GlGl = self.GlobGlass[i]
            (NP, AP) = n_wave_dispersion(self.SETUP, GlGl, W)
            N_P.append(NP)
        return N_P

    def __StoreParaxialTrace(self, trace):
        self.ParaxialMatrixTrace = trace
        self.ABCD_Matrix = trace.system_matrix_abcd
        self.ABCD_Surfaces = trace.surfaces
        Prx = trace.as_legacy_tuple()
        (
            self.SistemMatrix,
            self.S_Matrix,
            self.N_Matrix,
            self.a,
            self.b,
            self.c,
            self.d,
            self.EFFL,
            self.PPA,
            self.PPP,
            self.c_p,
            self.n_p,
            self.d_p,
        ) = Prx
        return Prx

    def Parax(self, W):
        """Parax.

        Parameters
        ----------
        W :
            W
        """
        trace = build_paraxial_matrix_trace(
            self.__ParaxialIndexList(W),
            self.SDT,
            self.SuTo,
            self.n,
            self.Glass,
            W,
        )
        return self.__StoreParaxialTrace(trace)

    def ParaxMatrices(self, W):
        """Return structured surface-by-surface paraxial ABCD matrix data."""
        trace = build_paraxial_matrix_trace(
            self.__ParaxialIndexList(W),
            self.SDT,
            self.SuTo,
            self.n,
            self.Glass,
            W,
        )
        self.__StoreParaxialTrace(trace)
        return trace

    def TargSurf(self, tgsfP1):
        """TargSurf.

        Parameters
        ----------
        tgsfP1 :
            tgsfP1
        """
        tgsf = (tgsfP1 + 1)
        if (self.n >= tgsf > 0):
            self.Targ_Surf = tgsf
        else:
            self.Targ_Surf = self.n



    def TargSurfRest(self):
        self.Targ_Surf = self.n




    def SurfFlat(self, fltsf, Prep=0):
        """SurfFlat.

        Parameters
        ----------
        fltsf :
            fltsf
        Prep :
            Prep
        """
        if (self.n >= fltsf > 0):
            self.SuTo.Surface_Flattener = fltsf
        else:
            self.SuTo.Surface_Flattener = 0
        if (Prep != 0):
            self.Pr3D.Prerequisites3DSolids()

    def IgnoreVignetting(self, Prep=0):
        """IgnoreVignetting.

        Parameters
        ----------
        Prep :
            Prep
        """
        self.INORM.Disable_Inner = 0
        self.Pr3D.Disable_Inner = 0
        self.INORM.ExtraDiameter = 1
        self.Pr3D.ExtraDiameter = 1
        if (Prep != 0):
            self.Pr3D.Prerequisites3DSolids()

    def Vignetting(self, Prep=0):
        """Vignetting.

        Parameters
        ----------
        Prep :
            Prep
        """
        self.INORM.Disable_Inner = 1
        self.Pr3D.Disable_Inner = 1
        self.INORM.ExtraDiameter = 0
        self.Pr3D.ExtraDiameter = 0
        if (Prep != 0):
            self.Pr3D.Prerequisites3DSolids()


    def GTrace(self, pS, dC, WaveLength):
        """Trace.

        Parameters
        ----------
        pS :
            pS
        dC :
            dC
        WaveLength :
            WaveLength
        """
        self.__CollectDataInit()
        ResVec = np.asarray(dC)
        RayOrig = np.asarray(pS)
        self.RAY = []
        self.Wave = WaveLength
        self.RAY.append(RayOrig)
        self.__WavePrecalc()
        j = 0
        Glass = self.GlobGlass[j]
        (PrevN, alpha) = (self.N_Prec[j], self.AlphaPrecal[j])
        j = 1
        SIGN = np.ones_like(ResVec)
        HitObjSpace = [0,0,0]

        const = 0
        while True:
            if (j == self.Targ_Surf):
                break
            j_gg = j
            Glass = self.GlobGlass[j_gg]

            if (self.Glass[j] != 'NULL'):
                Proto_pTarget = (np.asarray(RayOrig) + ((np.asarray(ResVec) * 999999999.9) * SIGN))
                Output = self.INORM.InterNormal(RayOrig, Proto_pTarget, j, j)


                (SurfHit, SurfNorm, pTarget, GooveVect, HitObjSpace, LMNObjSpace, j) = Output


                if (SurfHit == 0):
                    break

                ImpVec = np.asarray(ResVec)
                (CurrN, alpha) = (self.N_Prec[j_gg], self.AlphaPrecal[j_gg])


                S = ImpVec
                R = SurfNorm
                N = PrevN
                Np = CurrN
                D = GooveVect


                Ord = self.SDT[j].Diff_Ord
                GrSpa = self.SDT[j].Grating_D
                Secuent = 0

                (ResVec, CurrN, sign ,self.ang) = self.SDT[j].PHYSICS.calculate(S, R, N, Np, D, Ord, GrSpa, self.Wave, Secuent)



                SIGN = (SIGN * sign)
                Name = self.SDT[j].Name
                RayTraceType = 0
                ValToSav = [Glass, alpha, RayOrig, pTarget, HitObjSpace, LMNObjSpace, SurfNorm, ImpVec, ResVec, PrevN, CurrN, WaveLength, D, Ord, GrSpa, Name, j, RayTraceType]
                self.__CollectData(ValToSav)
                PrevN = CurrN
                RayOrig = pTarget


            self.RAY.append(RayOrig)

            if self.Glass[j] == 'NULL':
                ang = 0

                ValToSav = [Glass, alpha, RayOrig, pTarget, HitObjSpace, LMNObjSpace, SurfNorm, ImpVec, ResVec, PrevN, CurrN, WaveLength, D, Ord, GrSpa, Name, j, RayTraceType]
                self.__CollectData(ValToSav)

            if self.Glass[j] == 'ABSORB':
                break

            j = (j + 1)

        if (len(self.GLASS) == 0):
            self.__CollectDataInit()
            self.val = 0
            self.__EmptyCollect(RayOrig, ResVec, WaveLength, j)

        self.ray_SurfHits = np.asarray(self.RAY)

        AT = np.transpose(self.ray_SurfHits)
        self.Hit_x = AT[0]
        self.Hit_y = AT[1]
        self.Hit_z = AT[2]
        self.ExectTime=[]


    def Trace(self, pS, dC, WaveLength):
        """Trace.

        Parameters
        ----------
        pS :
            pS
        dC :
            dC
        WaveLength :
            WaveLength
        """
        self.__CollectDataInit()
        ResVec = np.asarray(dC)
        RayOrig = np.asarray(pS)
        self.RAY = []
        self.Wave = WaveLength
        self.RAY.append(RayOrig)
        self.__WavePrecalc()
        j = 0

        Glass = self.GlobGlass[j]
        (PrevN, alpha) = (self.N_Prec[j], self.AlphaPrecal[j])
        j = 1
        SIGN = np.ones_like(ResVec)
        HitObjSpace = [0,0,0]

        const = 0
        while True:
            if (j == self.Targ_Surf):
                break
            j_gg = j
            Glass = self.GlobGlass[j_gg]



            if (self.Glass[j] != 'NULL'):


                # print(self.SDT[j-1].Thickness, self.SDT[j].Rc, self.SDT[j].Const)
                ImpVec = np.asarray(ResVec)
                Proto_pTarget = (np.asarray(RayOrig) + ((ImpVec * 999999999.9) * SIGN))



                Output = self.INORM.InterNormal(RayOrig, Proto_pTarget, j, j)
                (SurfHit, SurfNorm, pTarget, GooveVect, HitObjSpace, LMNObjSpace, j) = Output
                if (SurfHit == 0):
                    break





                (CurrN, alpha) = (self.N_Prec[j_gg], self.AlphaPrecal[j_gg])


                S = ImpVec
                R = SurfNorm
                N = PrevN
                Np = CurrN
                D = GooveVect


                Ord = self.SDT[j].Diff_Ord
                GrSpa = self.SDT[j].Grating_D
                Secuent = 0

                (ResVec, CurrN, sign ,self.ang) = self.SDT[j].PHYSICS.calculate(S, R, N, Np, D, Ord, GrSpa, self.Wave, Secuent)



                SIGN = (SIGN * sign)
                Name = self.SDT[j].Name
                RayTraceType = 0


                ValToSav = [Glass, alpha, RayOrig, pTarget, HitObjSpace, LMNObjSpace, SurfNorm, ImpVec, ResVec, PrevN, CurrN, WaveLength, D, Ord, GrSpa, Name, j, RayTraceType]
                self.__CollectData(ValToSav)
                PrevN = CurrN
                RayOrig = pTarget


            self.RAY.append(RayOrig)

            if self.Glass[j] == 'NULL':
                ang = 0

                ValToSav = [Glass, alpha, RayOrig, pTarget, HitObjSpace, LMNObjSpace, SurfNorm, ImpVec, ResVec, PrevN, CurrN, WaveLength, D, Ord, GrSpa, Name, j, RayTraceType]
                self.__CollectData(ValToSav)

            if self.Glass[j] == 'ABSORB':
                break

            j = (j + 1)

        if (len(self.GLASS) == 0):
            self.__CollectDataInit()
            self.val = 0
            self.__EmptyCollect(RayOrig, ResVec, WaveLength, j)

        self.ray_SurfHits = np.asarray(self.RAY)

        AT = np.transpose(self.ray_SurfHits)
        self.Hit_x = AT[0]
        self.Hit_y = AT[1]
        self.Hit_z = AT[2]
        self.ExectTime=[]

    # ------------------------------------------------------------------
    # Batch (vectorised) ray tracing — process N rays simultaneously
    # ------------------------------------------------------------------

    def BatchTrace(self, pSources, dCosines, WaveLength):
        """Trace N rays through the system in parallel.

        GPU-accelerated counterpart of :meth:`Trace`.  Coordinate
        transforms, Newton-Raphson intersection, surface normals, and
        Snell's law all run on ``xp`` (CuPy on GPU, NumPy on CPU).
        Per-ray results are transferred to CPU for storage.

        Parameters
        ----------
        pSources : (N, 3) array — ray origin coordinates
        dCosines : (N, 3) array — ray direction cosines
        WaveLength : float — wavelength in micrometres
        """
        from .PhysicsClass import batch_snell_refraction

        pSources = xp.asarray(pSources, dtype=float)
        dCosines = xp.asarray(dCosines, dtype=float)
        N_rays = pSources.shape[0]

        self.Wave = WaveLength
        self.__WavePrecalc()

        # Per-ray mutable state (on GPU)
        RayOrig = pSources.copy()
        ResVec  = dCosines.copy()
        SIGN    = xp.ones((N_rays, 3))
        active  = xp.ones(N_rays, dtype=bool)
        PrevN   = xp.full(N_rays, self.N_Prec[0])

        # Per-ray result accumulators (CPU)
        pSrc_cpu = to_cpu(pSources)
        per_ray = [{
            'SURFACE': [], 'NAME': [], 'GLASS': [],
            'S_XYZ': [], 'XYZ': [list(pSrc_cpu[i])], 'T_XYZ': [],
            'OST_XYZ': [[0.,0.,0.]], 'OST_LMN': [],
            'S_LMN': [], 'LMN': [], 'R_LMN': [],
            'N0': [], 'N1': [], 'DISTANCE': [], 'OP': [],
            'TOP': 0.0, 'TOP_S': [],
            'val': 1, 'RAY': [list(pSrc_cpu[i])],
        } for i in range(N_rays)]

        for j in range(1, self.n):
            if j >= self.Targ_Surf:
                break
            if self.Glass[j] == 'NULL':
                continue

            j_gg = j
            Glass = self.GlobGlass[j_gg]
            (CurrN_scalar, alpha) = (self.N_Prec[j_gg], self.AlphaPrecal[j_gg])

            # ---- batch coordinate transform (GPU) ----
            T1 = xp.asarray(np.asarray(self.Pr3D.TRANS_1A[j]), dtype=float)
            T2 = xp.asarray(np.asarray(self.Pr3D.TRANS_2A[j]), dtype=float)

            ones = xp.ones((N_rays, 1))
            StopH = xp.hstack([RayOrig + ResVec * 999999999.9 * SIGN, ones])
            StartH = xp.hstack([RayOrig, ones])

            P_stop  = (T1 @ StopH.T).T
            P_start = (T1 @ StartH.T).T

            Px1_s = P_stop[:, 0]
            Py1_s = P_stop[:, 1]
            P_x1 = P_start[:, 0]
            P_y1 = P_start[:, 1]
            P_z1 = P_start[:, 2]

            # Direction in surface-local space
            dP = xp.stack([Px1_s - P_x1, Py1_s - P_y1,
                           P_stop[:, 2] - P_z1], axis=1)
            nrm = xp.linalg.norm(dP, axis=1, keepdims=True)
            nrm[nrm < 1e-15] = 1.0
            dP = dP / nrm
            L_loc = dP[:, 0]
            M_loc = dP[:, 1]
            N_loc = dP[:, 2]

            # Project to z=0 plane (surface vertex)
            Px1_proj = (L_loc / N_loc) * (-P_z1) + P_x1
            Py1_proj = (M_loc / N_loc) * (-P_z1) + P_y1

            # ---- aperture check ----
            ASD = xp.sqrt((Px1_proj - self.SDT[j].SubAperture[2])**2 +
                          (Py1_proj - self.SDT[j].SubAperture[1])**2)
            D0 = 2.0 * ASD
            DiamSup = self.SDT[j].Diameter * self.SDT[j].SubAperture[0] + 10000.0 * self.ExtraDiameter
            DiamInf = self.SDT[j].InDiameter * self.SDT[j].SubAperture[0] * self.INORM.Disable_Inner
            vignetted = (D0 > DiamSup) | (D0 < DiamInf)

            # ---- batch Newton-Raphson intersection (GPU) ----
            hit_x, hit_y, hit_z = self.HS.BatchSolveHit(
                Px1_proj, Py1_proj, xp.zeros(N_rays), L_loc, M_loc, N_loc, j
            )

            nan_mask = xp.isnan(hit_z)
            vignetted = vignetted | nan_mask

            # ---- batch surface normal (GPU) ----
            Dx, Dy, Dz = self.HS.BatchSurfDer(hit_x, hit_y, hit_z, j)

            Pz1_far = xp.full(N_rays, 10000000.0)
            Px1_n = (Pz1_far - hit_z) * (Dx / Dz) + hit_x
            Py1_n = (Pz1_far - hit_z) * (Dy / Dz) + hit_y

            P1_local = xp.stack([Px1_n, Py1_n, Pz1_far, xp.ones(N_rays)], axis=1)
            P2_local = xp.stack([hit_x, hit_y, hit_z, xp.ones(N_rays)], axis=1)

            NP1 = (T2 @ P1_local.T).T
            NP2 = (T2 @ P2_local.T).T

            SurfNorm = -(NP1[:, :3] - NP2[:, :3])
            norm_mag = xp.linalg.norm(SurfNorm, axis=1, keepdims=True)
            norm_mag[norm_mag < 1e-15] = 1.0
            SurfNorm = SurfNorm / norm_mag

            pTarget = NP2[:, :3]

            # ---- batch Snell's law (GPU) ----
            ImpVec = ResVec.copy()
            T_batch, abs_n2, sign_batch, ang_batch = batch_snell_refraction(
                ImpVec, SurfNorm, PrevN, CurrN_scalar, Secuen=0
            )

            SIGN = SIGN * sign_batch[:, None]

            # ---- transfer to CPU for per-ray result storage ----
            RayOrig_c = to_cpu(RayOrig)
            pTarget_c = to_cpu(pTarget)
            SurfNorm_c = to_cpu(SurfNorm)
            ImpVec_c = to_cpu(ImpVec)
            T_batch_c = to_cpu(T_batch)
            PrevN_c = to_cpu(PrevN)
            abs_n2_c = to_cpu(abs_n2)
            hit_x_c = to_cpu(hit_x)
            hit_y_c = to_cpu(hit_y)
            hit_z_c = to_cpu(hit_z)
            L_loc_c = to_cpu(L_loc)
            M_loc_c = to_cpu(M_loc)
            N_loc_c = to_cpu(N_loc)
            vignetted_c = to_cpu(vignetted)
            active_c = to_cpu(active)

            for i in range(N_rays):
                if not active_c[i]:
                    continue
                if vignetted_c[i]:
                    active[i] = False
                    per_ray[i]['val'] = 0
                    continue

                d = per_ray[i]
                dist = float(np.linalg.norm(RayOrig_c[i] - pTarget_c[i]))
                op = dist * float(PrevN_c[i])

                d['SURFACE'].append(j)
                d['NAME'].append(self.SDT[j].Name)
                d['GLASS'].append(Glass)
                d['S_XYZ'].append(list(RayOrig_c[i]))
                d['T_XYZ'].append(list(pTarget_c[i]))
                d['XYZ'].append(list(pTarget_c[i]))
                d['OST_XYZ'].append([float(hit_x_c[i]), float(hit_y_c[i]), float(hit_z_c[i])])
                d['OST_LMN'].append([float(L_loc_c[i]), float(M_loc_c[i]), float(N_loc_c[i])])
                d['S_LMN'].append(list(SurfNorm_c[i]))
                d['LMN'].append(list(ImpVec_c[i]))
                d['R_LMN'].append(list(T_batch_c[i]))
                d['N0'].append(float(PrevN_c[i]))
                d['N1'].append(float(abs_n2_c[i]))
                d['DISTANCE'].append(dist)
                d['OP'].append(op)
                d['TOP'] += op
                d['TOP_S'].append(d['TOP'])
                d['RAY'].append(list(pTarget_c[i]))

            # Update GPU state for next surface
            ResVec = T_batch
            RayOrig = pTarget.copy()
            PrevN = xp.where(active, abs_n2, PrevN)

        self._batch_results = per_ray
        self._batch_active = to_cpu(active)
        return per_ray

    def _apply_batch_result(self, i):
        """Load the *i*-th batch result into ``self`` so ``push()`` works."""
        d = self._batch_results[i]
        self.val = d['val']
        self.SURFACE = d['SURFACE']
        self.NAME = d['NAME']
        self.GLASS = d['GLASS']
        self.S_XYZ = d['S_XYZ']
        self.T_XYZ = d['T_XYZ']
        self.XYZ = d['XYZ']
        self.OST_XYZ = d['OST_XYZ']
        self.OST_LMN = d['OST_LMN']
        self.S_LMN = d['S_LMN']
        self.LMN = d['LMN']
        self.R_LMN = d['R_LMN']
        self.N0 = d['N0']
        self.N1 = d['N1']
        self.WAV = self.Wave
        self.G_LMN = [[0, 1, 0]] * len(d['SURFACE'])
        self.ORDER = [0] * len(d['SURFACE'])
        self.GRATING = [0] * len(d['SURFACE'])
        self.DISTANCE = d['DISTANCE']
        self.OP = d['OP']
        self.TOP_S = d['TOP_S']
        self.TOP = d['TOP']
        self.ALPHA = [0.0, 0.0] + [0.0] * len(d['SURFACE'])
        self.BULK_TRANS = []
        self.RP = [0.0] * len(d['SURFACE'])
        self.RS = [0.0] * len(d['SURFACE'])
        self.TP = [1.0] * len(d['SURFACE'])
        self.TS = [1.0] * len(d['SURFACE'])
        self.TTBE = [1.0] * len(d['SURFACE'])
        self.TT = 1.0
        self.RAY = d['RAY']
        self.ray_SurfHits = np.asarray(self.RAY)
        if len(self.ray_SurfHits.shape) == 2:
            AT = np.transpose(self.ray_SurfHits)
            self.Hit_x = AT[0]
            self.Hit_y = AT[1]
            self.Hit_z = AT[2]

    def RvTrace(self, pS, dC, WaveLength, StopSurf):
        """Trace.

        Parameters
        ----------
        pS :
            pS
        dC :
            dC
        WaveLength :
            WaveLength
        """
        self.__CollectDataInit()
        ResVec = np.asarray(dC)
        RayOrig = np.asarray(pS)
        self.RAY = []
        self.Wave = WaveLength
        self.RAY.append(RayOrig)
        self.__WavePrecalc()
        j = 0
        Glass = self.GlobGlass[j+1]
        (PrevN, alpha) = (self.N_Prec[j+1], self.AlphaPrecal[j+1])
        j = 1
        SIGN = np.ones_like(ResVec)
        HitObjSpace = [0,0,0]
        j = StopSurf
        const = 0
        while True:
            if (j == self.Targ_Surf):
                break
            if (j  < -1):
                break
            j_gg = j+1
            Glass = self.GlobGlass[j_gg]
           
            if (self.Glass[j] != 'NULL'):

                # print(self.SDT[j-1].Thickness, self.SDT[j].Rc, self.SDT[j].Const)
                ImpVec = np.asarray(ResVec)
                Proto_pTarget = (np.asarray(RayOrig) + ((ImpVec * 999999999.9) * SIGN))



                Output = self.INORM.InterNormal(RayOrig, Proto_pTarget, j, j)
                (SurfHit, SurfNorm, pTarget, GooveVect, HitObjSpace, LMNObjSpace, j) = Output

                if (SurfHit == 0):
                    break





                (CurrN, alpha) = (self.N_Prec[j_gg], self.AlphaPrecal[j_gg])

                S = ImpVec
                R = SurfNorm
                N = PrevN
                Np = CurrN
                D = GooveVect


                Ord = self.SDT[j].Diff_Ord
                GrSpa = self.SDT[j].Grating_D
                Secuent = 0

                (ResVec, CurrN, sign ,self.ang) = self.SDT[j].PHYSICS.calculate(S, R, N, Np, D, Ord, GrSpa, self.Wave, Secuent)



                SIGN = (SIGN * sign)
                Name = self.SDT[j].Name
                RayTraceType = 0
                ValToSav = [Glass, alpha, RayOrig, pTarget, HitObjSpace, LMNObjSpace, SurfNorm, ImpVec, ResVec, PrevN, CurrN, WaveLength, D, Ord, GrSpa, Name, j, RayTraceType]
                self.__CollectData(ValToSav)
                PrevN = CurrN
                RayOrig = pTarget


            self.RAY.append(RayOrig)

            if self.Glass[j] == 'NULL':
                ang = 0

                ValToSav = [Glass, alpha, RayOrig, pTarget, HitObjSpace, LMNObjSpace, SurfNorm, ImpVec, ResVec, PrevN, CurrN, WaveLength, D, Ord, GrSpa, Name, j, RayTraceType]
                self.__CollectData(ValToSav)

            if self.Glass[j] == 'ABSORB':
                break

            j = (j - 1)

        if (len(self.GLASS) == 0):
            self.__CollectDataInit()
            self.val = 0
            self.__EmptyCollect(RayOrig, ResVec, WaveLength, j)

        self.ray_SurfHits = np.asarray(self.RAY)

        AT = np.transpose(self.ray_SurfHits)
        self.Hit_x = AT[0]
        self.Hit_y = AT[1]
        self.Hit_z = AT[2]
        self.ExectTime=[]

    def __BeamSplitterSettings(self, j):
        settings = getattr(self.SDT[j], "BeamSplitter", None)
        if not isinstance(settings, dict):
            return None
        mode = str(settings.get("split_mode", settings.get("mode", "Deterministic branches"))).strip().lower()
        deterministic = "deterministic" in mode or "ideal" in mode or "plate" in mode
        if "monte" in mode or "stochastic" in mode or "probab" in mode:
            deterministic = False
        try:
            reflectance = float(settings.get("reflectance", 0.5))
        except Exception:
            reflectance = 0.5
        try:
            absorption = float(settings.get("absorption", settings.get("loss", 0.0)))
        except Exception:
            absorption = 0.0
        reflectance = min(max(reflectance, 0.0), 1.0)
        absorption = min(max(absorption, 0.0), 1.0 - reflectance)
        transmittance = max(1.0 - reflectance - absorption, 0.0)
        try:
            min_power = float(settings.get("min_branch_power", 1e-3))
        except Exception:
            min_power = 1e-3
        try:
            max_depth = int(float(settings.get("max_branch_depth", 8)))
        except Exception:
            max_depth = 8
        try:
            transmit_phase = float(settings.get("transmit_phase_deg", 0.0))
        except Exception:
            transmit_phase = 0.0
        try:
            reflect_phase = float(settings.get("reflect_phase_deg", 180.0))
        except Exception:
            reflect_phase = 180.0
        return {
            "deterministic": deterministic,
            "reflectance": reflectance,
            "transmittance": transmittance,
            "absorption": absorption,
            "min_branch_power": max(min_power, 0.0),
            "max_branch_depth": max(max_depth, 1),
            "transmit_phase_deg": transmit_phase,
            "reflect_phase_deg": reflect_phase,
        }

    def __NsTraceHasDeterministicBeamSplitter(self):
        for j in range(0, self.n):
            settings = self.__BeamSplitterSettings(j)
            if settings is not None and settings["deterministic"]:
                return True
        return False

    def __NsTraceSnapshot(
        self,
        branch_id=0,
        parent_branch_id=None,
        branch_power=1.0,
        branch_phase_deg=0.0,
        branch_label="primary",
        branch_path="primary",
    ):
        keys = (
            "SURFACE", "NAME", "GLASS", "S_XYZ", "T_XYZ", "XYZ", "OST_XYZ", "OST_LMN",
            "S_LMN", "LMN", "R_LMN", "N0", "N1", "WAV", "G_LMN", "ORDER", "GRATING",
            "DISTANCE", "OP", "TOP_S", "TOP", "ALPHA", "BULK_TRANS", "RP", "RS",
            "TP", "TS", "TTBE", "TT", "RAY", "val", "tt",
        )
        data = {key: copy.deepcopy(getattr(self, key)) for key in keys if hasattr(self, key)}
        data["Wave"] = copy.deepcopy(getattr(self, "Wave", None))
        data["branch_id"] = int(branch_id)
        data["parent_branch_id"] = None if parent_branch_id is None else int(parent_branch_id)
        data["branch_power"] = float(branch_power)
        data["branch_phase_deg"] = float(branch_phase_deg)
        data["branch_label"] = str(branch_label)
        data["branch_path"] = str(branch_path or branch_label or "primary")
        return data

    def __RestoreNsTraceSnapshot(self, data):
        for key, value in data.items():
            if key in {
                "branch_id",
                "parent_branch_id",
                "branch_power",
                "branch_phase_deg",
                "branch_label",
                "Wave",
            }:
                continue
            setattr(self, key, copy.deepcopy(value))
        if "Wave" in data:
            self.Wave = copy.deepcopy(data["Wave"])
        self._collect_tt_override = None

    def __FinalizeNsTraceArrays(self):
        self.ray_SurfHits = np.asarray(self.RAY)
        if self.ray_SurfHits.size == 0:
            self.Hit_x = np.asarray([])
            self.Hit_y = np.asarray([])
            self.Hit_z = np.asarray([])
            return None
        AT = np.transpose(self.ray_SurfHits)
        self.Hit_x = AT[0]
        self.Hit_y = AT[1]
        self.Hit_z = AT[2]
        return None

    def __NsTraceBranchPathComponent(self, surface_index, branch_label):
        try:
            name = str(getattr(self.SDT[int(surface_index)], "Name", "") or "").strip()
        except Exception:
            name = ""
        if not name:
            name = f"S{int(surface_index)}"
        return f"S{int(surface_index)}:{name}/{str(branch_label or '').strip()}"

    def __NsTraceAppendBranchPath(self, parent_path, surface_index, branch_label):
        component = self.__NsTraceBranchPathComponent(surface_index, branch_label)
        parent = str(parent_path or "").strip()
        if not parent or parent == "primary":
            return component
        return f"{parent} -> {component}"

    def __NsTerminalLength(self):
        diameters = []
        thicknesses = []
        for surf in self.SDT:
            try:
                diameters.append(abs(float(surf.Diameter)))
            except Exception:
                pass
            try:
                thicknesses.append(abs(float(surf.Thickness)))
            except Exception:
                pass
        aperture = max(diameters) if diameters else 50.0
        length = sum(thicknesses) if thicknesses else 0.0
        return max(50.0, aperture * 2.0, length * 0.35)

    def __AppendNsTerminalSegment(self, RayOrig, ResVec):
        if len(self.RAY) == 0:
            return None
        direction = np.asarray(ResVec, dtype=float)
        norm = np.linalg.norm(direction)
        if norm <= 1e-12:
            return None
        terminal = np.asarray(RayOrig, dtype=float) + (direction / norm) * self.__NsTerminalLength()
        last = np.asarray(self.RAY[-1], dtype=float)
        if np.linalg.norm(terminal - last) > 1e-9:
            self.RAY.append(terminal)
        return None

    def __ReflectVector(self, incident, normal):
        incident_vec = np.asarray(incident, dtype=float)
        normal_vec = np.asarray(normal, dtype=float)
        normal_norm = np.linalg.norm(normal_vec)
        if normal_norm <= 1e-12:
            return incident_vec
        normal_vec = normal_vec / normal_norm
        reflected = incident_vec - (2.0 * np.dot(incident_vec, normal_vec) * normal_vec)
        reflected_norm = np.linalg.norm(reflected)
        if reflected_norm <= 1e-12:
            return reflected
        return reflected / reflected_norm

    def __NudgeNsBranchOrigin(self, point, direction):
        direction_vec = np.asarray(direction, dtype=float)
        norm = np.linalg.norm(direction_vec)
        if norm <= 1e-12:
            return np.asarray(point, dtype=float)
        diameters = []
        for surf in self.SDT:
            try:
                diameters.append(abs(float(surf.Diameter)))
            except Exception:
                pass
        scale = max(diameters) if diameters else 1.0
        epsilon = max(1e-5, float(scale) * 1e-8)
        return np.asarray(point, dtype=float) + (direction_vec / norm) * epsilon

    def __NsTraceBranching(self, pS, dC, WaveLength):
        """Non-sequential trace with deterministic beam-splitter branch spawning."""
        global j_gg
        pS = np.asarray(pS, dtype=float)
        dC = np.asarray(dC, dtype=float)
        self.__CollectDataInit()
        self.RAY = []
        self.Wave = WaveLength
        self.RAY.append(pS)
        self.__WavePrecalc()
        start_state = {
            "trace": self.__NsTraceSnapshot(0, None, 1.0, 0.0, "primary"),
            "RayOrig": pS,
            "ResVec": dC,
            "PrevN": self.N_Prec[0],
            "j": 0,
            "SIGN": 1,
            "count": 0,
            "branch_id": 0,
            "parent_branch_id": None,
            "branch_power": 1.0,
            "branch_phase_deg": 0.0,
            "branch_depth": 0,
            "branch_label": "primary",
            "branch_path": "primary",
        }
        queue = [start_state]
        results = []
        next_branch_id = 1
        branch_result_limit = 4096

        while queue and len(results) < branch_result_limit:
            state = queue.pop(0)
            self.__RestoreNsTraceSnapshot(state["trace"])
            RayOrig = np.asarray(state["RayOrig"], dtype=float)
            ResVec = np.asarray(state["ResVec"], dtype=float)
            PrevN = state["PrevN"]
            j = int(state["j"])
            SIGN = state["SIGN"]
            count = int(state["count"])
            branch_id = int(state["branch_id"])
            branch_power = float(state["branch_power"])
            branch_phase = float(state["branch_phase_deg"])
            branch_depth = int(state["branch_depth"])
            branch_label = str(state["branch_label"])
            branch_path = str(state.get("branch_path", branch_label) or branch_label)
            split_spawned = False

            while True:
                if (j == self.Targ_Surf):
                    break
                (a, b, c, PreSurfHit) = self.__NonSequentialChooser(SIGN, RayOrig, ResVec, j)

                if (PreSurfHit == 0):
                    self.__AppendNsTerminalSegment(RayOrig, ResVec)
                    break
                if (a < b):
                    j_gg = b
                if (a > b):
                    j_gg = (b - 1)
                    if (self.Glass[(b - 1)] == 'MIRROR'):
                        j_gg = b
                    if (self.Glass[b] == 'MIRROR'):
                        j_gg = b
                if (a == b):
                    j_gg = (b - 1)

                j = b
                jj = b
                j = self.GlassOnSide[j]
                j_gg = self.GlassOnSide[j_gg]
                Glass = self.GlobGlass[j_gg]
                if ((j == 0) or (count > self.NsLimit) or (a == self.n)):
                    break
                if (self.Glass[j] != 'NULL'):
                    Proto_pTarget = (np.asarray(RayOrig) + ((np.asarray(ResVec) * 999999999.9) * SIGN))
                    Output = self.INORM.InterNormal(RayOrig, Proto_pTarget, j, jj)
                    (SurfHit, SurfNorm, pTarget, GooveVect, HitObjSpace, LMNObjSpace, j) = Output
                    if (SurfHit == 0):
                        self.__AppendNsTerminalSegment(RayOrig, ResVec)
                        break
                    ImpVec = np.asarray(ResVec)
                    (CurrN, alpha) = (self.N_Prec[j_gg], self.AlphaPrecal[j_gg])

                    if CurrN == 1.0:
                        CurrN = self.Next

                    R = np.asarray(SurfNorm)
                    N = PrevN
                    Np = CurrN
                    if ((self.SDT[j].Solid_3d_stl == 'None') and (self.TypeTotal[jj] == 1)):
                        if (N == 1):
                            Np = CurrN
                        else:
                            N = CurrN
                            Np = 1
                    D = GooveVect

                    Ord = self.SDT[j].Diff_Ord
                    GrSpa = self.SDT[j].Grating_D
                    ResVec_N, R_N, N_N, Np_N = ResVec, R, N, Np
                    (trans_vec, trans_n, trans_sign, trans_ang) = self.SDT[j].PHYSICS.calculate(
                        ResVec_N, R_N, N_N, Np_N, D, Ord, GrSpa, self.Wave, 0
                    )
                    self.ang = trans_ang
                    splitter_settings = self.__BeamSplitterSettings(j)
                    can_split = (
                        splitter_settings is not None
                        and splitter_settings["deterministic"]
                        and branch_depth < int(splitter_settings["max_branch_depth"])
                    )

                    if can_split:
                        refl_vec = self.__ReflectVector(ImpVec, SurfNorm)
                        refl_n = PrevN
                        refl_sign = 1.0
                        refl_ang = trans_ang
                        children = (
                            (
                                "transmit",
                                trans_vec,
                                trans_n,
                                trans_sign,
                                trans_ang,
                                float(splitter_settings["transmittance"]),
                                float(splitter_settings["transmit_phase_deg"]),
                            ),
                            (
                                "reflect",
                                refl_vec,
                                PrevN,
                                refl_sign,
                                refl_ang,
                                float(splitter_settings["reflectance"]),
                                float(splitter_settings["reflect_phase_deg"]),
                            ),
                        )
                        pre_hit_trace = self.__NsTraceSnapshot(
                            branch_id,
                            state["parent_branch_id"],
                            branch_power,
                            branch_phase,
                            branch_label,
                            branch_path,
                        )
                        for child_label, child_vec, child_n, child_sign, child_ang, child_coeff, child_phase in children:
                            if child_coeff <= 0.0:
                                continue
                            if branch_power * child_coeff < float(splitter_settings["min_branch_power"]):
                                continue
                            self.__RestoreNsTraceSnapshot(pre_hit_trace)
                            self._collect_tt_override = child_coeff
                            self.ang = child_ang
                            Name = self.SDT[j].Name
                            RayTraceType = 1
                            ValToSav = [
                                Glass,
                                alpha,
                                RayOrig,
                                pTarget,
                                HitObjSpace,
                                LMNObjSpace,
                                SurfNorm,
                                ImpVec,
                                child_vec,
                                PrevN,
                                child_n,
                                WaveLength,
                                D,
                                Ord,
                                GrSpa,
                                Name,
                                j,
                                RayTraceType,
                            ]
                            self.__CollectData(ValToSav)
                            child_prev_n = PrevN if child_label == "reflect" or (a == b) else child_n
                            child_ray_orig = np.asarray(pTarget, dtype=float)
                            child_trace_orig = self.__NudgeNsBranchOrigin(child_ray_orig, child_vec)
                            self.RAY.append(child_ray_orig)
                            child_branch_id = next_branch_id
                            next_branch_id += 1
                            child_power_total = float(self.TT)
                            child_branch_path = self.__NsTraceAppendBranchPath(branch_path, j, child_label)
                            child_state = {
                                "trace": self.__NsTraceSnapshot(
                                    child_branch_id,
                                    branch_id,
                                    child_power_total,
                                    branch_phase + child_phase,
                                    child_label,
                                    child_branch_path,
                                ),
                                "RayOrig": child_trace_orig,
                                "ResVec": np.asarray(child_vec, dtype=float),
                                "PrevN": child_prev_n,
                                "j": int(j),
                                "SIGN": SIGN * child_sign,
                                "count": count + 1,
                                "branch_id": child_branch_id,
                                "parent_branch_id": branch_id,
                                "branch_power": child_power_total,
                                "branch_phase_deg": branch_phase + child_phase,
                                "branch_depth": branch_depth + 1,
                                "branch_label": child_label,
                                "branch_path": child_branch_path,
                            }
                            queue.append(child_state)
                            if len(queue) + len(results) >= branch_result_limit:
                                break
                        split_spawned = True
                        break

                    ResVec = trans_vec
                    CurrN = trans_n
                    sign = trans_sign
                    ang = trans_ang

                    mtl = self.SDT[j].CoatingMet
                    (Rp0, Rs0, Tp0, Ts0) = FresnelEnergy(self.Glass[j], N, Np, ImpVec, R, ResVec, self.SETUP, self.Wave, mtl)
                    Rp2, Rs2, Tp2, Ts2, V = self.CoatingFun(self.SDT[j].Coating, ang, self.Wave)
                    if V == 1:
                        Rp0, Rs0, Tp0, Ts0 = Rp2, Rs2, Tp2, Ts2

                    self.tt = 1.0
                    if (self.Glass[j] != 'MIRROR'):
                        self.tt = ((Tp0 + Ts0) / 2.0)

                    if self.energy_probability==1:
                        PROB = prob(self.tt)[0]

                        if (PROB > 0):
                            (ResVec, CurrN, sign ,ang) = self.SDT[j].PHYSICS.calculate(
                                ResVec_N, R_N, N_N, Np_N, D, Ord, GrSpa, self.Wave, 1
                            )

                    self.ang = ang
                    SIGN = (SIGN * sign)

                    Name = self.SDT[j].Name
                    RayTraceType = 1
                    ValToSav = [Glass, alpha, RayOrig, pTarget, HitObjSpace,LMNObjSpace, SurfNorm, ImpVec, ResVec, PrevN, CurrN, WaveLength, D, Ord, GrSpa, Name, j, RayTraceType]
                    self.__CollectData(ValToSav)
                    if (a == b):
                        PrevN = PrevN
                    else:
                        PrevN = CurrN
                    RayOrig = pTarget

                    if (a==b) and (b==c) and (c == PreSurfHit):
                        break

                    self.RAY.append(RayOrig)

                if self.Glass[j] == 'NULL':
                    break

                if self.Glass[j] == 'ABSORB':
                    break

                count = (count + 1)

            if split_spawned:
                continue
            if (len(self.GLASS) == 0):
                self.__CollectDataInit()
                self.val = 0
                self.__EmptyCollect(pS, dC, WaveLength, j)
            self.__FinalizeNsTraceArrays()
            results.append(
                self.__NsTraceSnapshot(
                    branch_id,
                    state["parent_branch_id"],
                    float(self.TT),
                    branch_phase,
                    branch_label,
                    branch_path,
                )
            )

        if len(results) == 0:
            self.__CollectDataInit()
            self.val = 0
            self.__EmptyCollect(pS, dC, WaveLength, 0)
            self.__FinalizeNsTraceArrays()
            results.append(self.__NsTraceSnapshot(0, None, float(self.TT), 0.0, "primary"))

        self.NS_BRANCH_RESULTS = results
        self.__RestoreNsTraceSnapshot(results[0])
        self.__FinalizeNsTraceArrays()
        return None

    def NsTrace(self, pS, dC, WaveLength):
        """NsTrace.

        Parameters
        ----------
        pS :
            pS
        dC :
            dC
        WaveLength :
            WaveLength
        """
        BLD = self.BUILD
        if self.Pr3D.ExistSolid == 0:
            
            self.BUILD = 1
            self.build()
            self.BUILD = BLD
            
                
        self.NS_BRANCH_RESULTS = []
        if self.__NsTraceHasDeterministicBeamSplitter():
            return self.__NsTraceBranching(pS, dC, WaveLength)

        global j_gg
        pS = np.asarray(pS)
        count = 0
        a = 1
        b = 2
        self.__CollectDataInit()
        ResVec = dC
        RayOrig = pS
        self.RAY = []
        self.Wave = WaveLength
        self.RAY.append(RayOrig)
        self.__WavePrecalc()
        j = 0
        Glass = self.GlobGlass[j]
        (PrevN, alpha) = (self.N_Prec[j], self.AlphaPrecal[j])
        j = 0
        SIGN = 1

        while True:
            if (j == self.Targ_Surf):
                break
            (a, b, c, PreSurfHit) = self.__NonSequentialChooser(SIGN, RayOrig, ResVec, j)

            if (PreSurfHit == 0):
                break
            if (a < b):
                j_gg = b
            if (a > b):
                j_gg = (b - 1)
                if (self.Glass[(b - 1)] == 'MIRROR'):
                    j_gg = b
                if (self.Glass[b] == 'MIRROR'):
                    j_gg = b
            if (a == b):
                j_gg = (b - 1)

            j = b
            jj = b
            j = self.GlassOnSide[j]
            j_gg = self.GlassOnSide[j_gg]
            Glass = self.GlobGlass[j_gg]
            if ((j == 0) or (count > self.NsLimit) or (a == self.n)):
                break
            if (self.Glass[j] != 'NULL'):
                Proto_pTarget = (np.asarray(RayOrig) + ((np.asarray(ResVec) * 999999999.9) * SIGN))
                Output = self.INORM.InterNormal(RayOrig, Proto_pTarget, j, jj)
                (SurfHit, SurfNorm, pTarget, GooveVect, HitObjSpace, LMNObjSpace, j) = Output
                if (SurfHit == 0):
                    break
                ImpVec = np.asarray(ResVec)
                (CurrN, alpha) = (self.N_Prec[j_gg], self.AlphaPrecal[j_gg])

                # Alternative refraction index for air medium
                if CurrN == 1.0:
                    CurrN = self.Next

                S = np.asarray(ImpVec)
                R = np.asarray(SurfNorm)
                N = PrevN
                Np = CurrN
                if ((self.SDT[j].Solid_3d_stl == 'None') and (self.TypeTotal[jj] == 1)):
                    if (N == 1):
                        Np = CurrN
                    else:
                        N = CurrN
                        Np = 1
                D = GooveVect

                Ord = self.SDT[j].Diff_Ord
                GrSpa = self.SDT[j].Grating_D
                Secuent = 0
                ResVec_N, R_N, N_N, Np_N = ResVec, R, N, Np
                (ResVec, CurrN, sign ,ang) = self.SDT[j].PHYSICS.calculate(ResVec_N, R_N, N_N, Np_N, D, Ord, GrSpa, self.Wave, Secuent)
                self.ang = ang

                # Coating
                mtl = self.SDT[j].CoatingMet
                (Rp0, Rs0, Tp0, Ts0) = FresnelEnergy(self.Glass[j], N, Np, ImpVec, R, ResVec, self.SETUP, self.Wave, mtl)
                Rp2, Rs2, Tp2, Ts2, V = self.CoatingFun(self.SDT[j].Coating, ang, self.Wave)
                if V == 1:
                    Rp0, Rs0, Tp0, Ts0 = Rp2, Rs2, Tp2, Ts2

                self.tt = 1.0
                if (self.Glass[j] != 'MIRROR'):
                    self.tt = ((Tp0 + Ts0) / 2.0)


                if self.energy_probability==1:
                    PROB = prob(self.tt)[0]

                    if (PROB > 0):
                        Secuent = 1
                        (ResVec, CurrN, sign ,ang) = self.SDT[j].PHYSICS.calculate(ResVec_N, R_N, N_N, Np_N, D, Ord, GrSpa, self.Wave, Secuent)
                        self.ang = ang

                SIGN = (SIGN * sign)

                Name = self.SDT[j].Name
                RayTraceType = 1
                ValToSav = [Glass, alpha, RayOrig, pTarget, HitObjSpace,LMNObjSpace, SurfNorm, ImpVec, ResVec, PrevN, CurrN, WaveLength, D, Ord, GrSpa, Name, j, RayTraceType]
                self.__CollectData(ValToSav)
                if (a == b):
                    PrevN = PrevN
                else:
                    PrevN = CurrN
                RayOrig = pTarget

                if (a==b) and (b==c) and (c == PreSurfHit):
                    break

                self.RAY.append(RayOrig)

            if self.Glass[j] == 'NULL':
                ang = 0
                ValToSav = [Glass, alpha, RayOrig, pTarget, HitObjSpace, SurfNorm, ImpVec, ResVec, PrevN, CurrN, WaveLength, D, Ord, GrSpa, Name, j, RayTraceType, ang]
                self.__CollectData(ValToSav)

            if self.Glass[j] == 'ABSORB':
                break

            count = (count + 1)
        if (len(self.GLASS) == 0):
            self.__CollectDataInit()
            self.val = 0
            self.__EmptyCollect(pS, dC, WaveLength, j)
        self.ray_SurfHits = np.asarray(self.RAY)
        AT = np.transpose(self.ray_SurfHits)
        self.Hit_x = AT[0]
        self.Hit_y = AT[1]
        self.Hit_z = AT[2]

    def FastTrace(self, pS, dC, WaveLength):
        """Trace.

        Parameters
        ----------
        pS :
            pS
        dC :
            dC
        WaveLength :
            WaveLength
        """
        self.__CollectDataInit()
        ResVec = np.asarray(dC)
        RayOrig = np.asarray(pS)
        self.CORD = RayOrig
        self.Wave = WaveLength
        self.RAY.append(RayOrig)
        self.__WavePrecalc()
        (PrevN, alpha) = (self.N_Prec[0], self.AlphaPrecal[0])
        j = 1
        SIGN = np.ones_like(ResVec)
        while True:


            if j == self.Targ_Surf or self.Glass[j] == 'ABSORB' or self.Glass[j] == 'NULL':
                break

            Proto_pTarget = (np.asarray(RayOrig) + ((np.asarray(ResVec) * 999999999.9) * SIGN))
            SurfHit, SurfNorm, RayOrig, GooveVect, HitObjSpace, LMNObjSpace, j = self.INORM.InterNormal(RayOrig, Proto_pTarget, j, j)


            if (SurfHit == 0):
                break

            (CurrN, alpha) = (self.N_Prec[j], self.AlphaPrecal[j])
            Ord = self.SDT[j].Diff_Ord
            GrSpa = self.SDT[j].Grating_D

            (ResVec, PrevN, sign ,self.ang) = self.SDT[j].PHYSICS.calculate(ResVec, SurfNorm, PrevN, CurrN, GooveVect, Ord, GrSpa, self.Wave, 0)
            SIGN = (SIGN * sign)

            j = (j + 1)


        if (len(self.GLASS) == 0):
            self.val = 0
            self.__EmptyCollect(RayOrig, ResVec, WaveLength, j)

        self.CORD = RayOrig
