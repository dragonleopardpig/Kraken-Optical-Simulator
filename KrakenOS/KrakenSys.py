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
from .MeshRayTrace import assign_mesh_cell_face_ids, trace_mesh_ray
from .ParaxialMatrix import build_paraxial_matrix_trace
from .gpu_backend import xp, to_cpu, to_gpu
from .scatter_backend import normalize_pyscatmech_parameters, pyscatmech_scalar_brdf, pyscatmech_status
import timeit
import copy

try:
    from .UI.optical_solid_metadata import (
        OPTICAL_SOLID_FACE_PORT_INPUT,
        match_optical_solid_world_face,
        normalize_optical_solid_face_function,
        normalize_optical_solid_face_metadata,
        optical_solid_face_by_port_role,
        point3_tuple,
        unit_vector_tuple,
    )
except Exception:
    OPTICAL_SOLID_FACE_PORT_INPUT = "Input Port"

    def normalize_optical_solid_face_metadata(value, *args, **kwargs):
        return {"faces": []}

    def normalize_optical_solid_face_function(value, *, legacy_role=None):
        return str(value or legacy_role or "").strip()

    def point3_tuple(value):
        arr = np.asarray(value if value is not None else (0.0, 0.0, 0.0), dtype=float).reshape(-1)[:3]
        if arr.size < 3:
            arr = np.pad(arr, (0, 3 - arr.size), mode="constant")
        return tuple(float(v) for v in arr[:3])

    def unit_vector_tuple(value):
        arr = np.asarray(value if value is not None else (0.0, 0.0, 1.0), dtype=float).reshape(-1)[:3]
        if arr.size < 3:
            arr = np.pad(arr, (0, 3 - arr.size), mode="constant")
        norm = float(np.linalg.norm(arr))
        if norm <= 1e-12 or not np.isfinite(norm):
            arr = np.asarray((0.0, 0.0, 1.0), dtype=float)
        else:
            arr = arr / norm
        return tuple(float(v) for v in arr[:3])

    def match_optical_solid_world_face(world_faces, point_world, normal_world=None):
        return None

    def optical_solid_face_by_port_role(metadata, port_role):
        return None



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
        self._collect_bulk_override = None
        self._optical_solid_face_world_cache = {}


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

    @staticmethod
    def __RotatePointX(point, degrees):
        angle = np.deg2rad(float(degrees))
        x, y, z = (float(value) for value in np.asarray(point, dtype=float).reshape(3))
        return np.asarray((x, (y * np.cos(angle)) - (z * np.sin(angle)), (y * np.sin(angle)) + (z * np.cos(angle))), dtype=float)

    @staticmethod
    def __RotatePointY(point, degrees):
        angle = np.deg2rad(float(degrees))
        x, y, z = (float(value) for value in np.asarray(point, dtype=float).reshape(3))
        return np.asarray(((x * np.cos(angle)) + (z * np.sin(angle)), y, ((- x) * np.sin(angle)) + (z * np.cos(angle))), dtype=float)

    @staticmethod
    def __RotatePointZ(point, degrees):
        angle = np.deg2rad(float(degrees))
        x, y, z = (float(value) for value in np.asarray(point, dtype=float).reshape(3))
        return np.asarray(((x * np.cos(angle)) - (y * np.sin(angle)), (x * np.sin(angle)) + (y * np.cos(angle)), z), dtype=float)

    def __TransformOpticalSolidLocalFace(self, surface_index, point_local, normal_local):
        point = np.asarray(point_local, dtype=float).reshape(3)
        normal = np.asarray(normal_local, dtype=float).reshape(3)
        overrides = getattr(self, "_optical_solid_output_port_pose_overrides", None)
        if isinstance(overrides, dict):
            try:
                pose = overrides.get(int(surface_index))
            except Exception:
                pose = None
            if isinstance(pose, dict):
                try:
                    center = np.asarray(pose.get("center"), dtype=float).reshape(3)
                    rotation = np.asarray(pose.get("rotation"), dtype=float).reshape(3, 3)
                    transformed_point = point @ rotation.T + center
                    transformed_normal = normal @ rotation.T
                    normal_norm = float(np.linalg.norm(transformed_normal))
                    if normal_norm > 1e-12 and np.isfinite(normal_norm):
                        transformed_normal = transformed_normal / normal_norm
                    else:
                        transformed_normal = np.asarray((0.0, 0.0, 1.0), dtype=float)
                    return transformed_point, transformed_normal
                except Exception:
                    pass
        stx = 0.0
        sty = 0.0
        for n in range(int(surface_index), -1, -1):
            LL = 0.0 if n == 0 else 1.0
            PA = 1.0 if n == int(surface_index) else (float(self.SDT[n].AxisMove) * LL)
            tx = (float(self.SDT[n].TiltX) * PA) * LL
            ty = (float(self.SDT[n].TiltY) * PA) * LL
            tz = (float(self.SDT[n].TiltZ) * PA) * LL
            dx = (float(self.SDT[n].DespX) * PA) * LL
            dy = (float(self.SDT[n].DespY) * PA) * LL
            dz = (float(self.SDT[n].DespZ) * PA) * LL
            stx = stx + tx
            sty = sty + ty
            tolerance = 0.0001
            if abs(np.cos(np.deg2rad(stx))) < tolerance:
                tx = tx + tolerance
            if abs(np.cos(np.deg2rad(sty))) < tolerance:
                ty = ty + tolerance
            translate_thickness = float(self.SDT[(n - 1)].Thickness)

            if self.SDT[n].Order == 0:
                point = self.__RotatePointX(point, tx)
                point = self.__RotatePointY(point, ty)
                point = self.__RotatePointZ(point, -tz)
                point = point + np.asarray((dx, dy, dz), dtype=float)
                point = point + np.asarray((0.0, 0.0, translate_thickness), dtype=float)

                normal = self.__RotatePointX(normal, tx)
                normal = self.__RotatePointY(normal, ty)
                normal = self.__RotatePointZ(normal, -tz)
            else:
                point = point + np.asarray((dx, dy, dz), dtype=float)
                point = self.__RotatePointZ(point, -tz)
                point = self.__RotatePointY(point, ty)
                point = self.__RotatePointX(point, tx)
                point = point + np.asarray((0.0, 0.0, translate_thickness), dtype=float)

                normal = self.__RotatePointZ(normal, -tz)
                normal = self.__RotatePointY(normal, ty)
                normal = self.__RotatePointX(normal, tx)

        normal_norm = float(np.linalg.norm(normal))
        if normal_norm > 1e-12 and np.isfinite(normal_norm):
            normal = normal / normal_norm
        else:
            normal = np.asarray((0.0, 0.0, 1.0), dtype=float)
        return point, normal

    def __OpticalSolidWorldFaces(self, surface_index):
        cache_key = int(surface_index)
        cached = self._optical_solid_face_world_cache.get(cache_key)
        if cached is not None:
            return cached
        try:
            metadata = normalize_optical_solid_face_metadata(getattr(self.SDT[cache_key], "OpticalSolidFaces", {}))
        except Exception:
            metadata = {"faces": []}
        world_faces = []
        for face in list(metadata.get("faces", []) or []):
            if not isinstance(face, dict):
                continue
            centroid_local = np.asarray(point3_tuple(face.get("centroid", (0.0, 0.0, 0.0))), dtype=float)
            normal_local = np.asarray(unit_vector_tuple(face.get("normal", (0.0, 0.0, 1.0))), dtype=float)
            if bool(face.get("flip_normal", False)):
                normal_local = -normal_local
            centroid_world, normal_world = self.__TransformOpticalSolidLocalFace(cache_key, centroid_local, normal_local)
            if not (np.all(np.isfinite(centroid_world)) and np.all(np.isfinite(normal_world))):
                continue
            world_face = dict(face)
            world_face["function"] = normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
            world_face["centroid_world"] = tuple(float(value) for value in centroid_world[:3])
            world_face["normal_world"] = tuple(float(value) for value in normal_world[:3])
            world_faces.append(world_face)
        self._optical_solid_face_world_cache[cache_key] = world_faces
        return world_faces

    def __OpticalSolidFaceById(self, world_faces, face_id):
        target = str(face_id or "").strip()
        if not target:
            return None
        for face in list(world_faces or []):
            if isinstance(face, dict) and str(face.get("face_id", "") or "").strip() == target:
                return face
        return None

    def __OpticalSolidFaceInteraction(self, surface_index, point_world, normal_world, mesh_hit=None):
        world_faces = self.__OpticalSolidWorldFaces(surface_index)
        mesh_face_id = str(mesh_hit.get("face_id", "") or "").strip() if isinstance(mesh_hit, dict) else ""
        matched = self.__OpticalSolidFaceById(world_faces, mesh_face_id)
        face_match_method = (
            str(mesh_hit.get("face_match_method", "") or "").strip()
            if isinstance(mesh_hit, dict) and isinstance(matched, dict)
            else ""
        )
        if not face_match_method:
            face_match_method = "mesh_cell_face_id" if isinstance(matched, dict) else "nearest_world_face"
        if not isinstance(matched, dict):
            matched = match_optical_solid_world_face(
                world_faces,
                point_world,
                normal_world,
            )
        if not isinstance(matched, dict):
            return None
        function = normalize_optical_solid_face_function(matched.get("function"), legacy_role=matched.get("role"))
        override = {
            "face_id": str(matched.get("face_id", "") or "").strip(),
            "side_2d": str(matched.get("side_2d", "") or "").strip(),
            "function": function,
            "loss": float(np.clip(float(matched.get("loss", 0.0) or 0.0), 0.0, 1.0)),
            "normal_world": tuple(float(value) for value in np.asarray(matched.get("normal_world", normal_world), dtype=float).reshape(3)),
        }
        if isinstance(mesh_hit, dict):
            for key in ("cell_id", "original_cell_id"):
                try:
                    override[f"mesh_{key}"] = int(mesh_hit.get(key, -1))
                except Exception:
                    override[f"mesh_{key}"] = -1
            override["mesh_face_id"] = mesh_face_id
            override["face_match_method"] = face_match_method
            try:
                override["face_match_score"] = float(mesh_hit.get("face_match_score"))
            except Exception:
                pass
        if function in {"Mirror", "TIR"}:
            override["force_reflection"] = True
            try:
                metadata = normalize_optical_solid_face_metadata(getattr(self.SDT[int(surface_index)], "OpticalSolidFaces", {}))
                has_input_port = optical_solid_face_by_port_role(metadata, OPTICAL_SOLID_FACE_PORT_INPUT) is not None
            except Exception:
                has_input_port = True
            if not has_input_port:
                override["external_reflection"] = True
        return override


    def __ReplaceSceneMesh(self, mesh_index, mesh):
        if mesh is None:
            return None
        for owner in (self, getattr(self, "Pr3D", None), getattr(self, "INORM", None)):
            meshes = getattr(owner, "EEE", None) if owner is not None else None
            if meshes is None or not (0 <= int(mesh_index) < len(meshes)):
                continue
            try:
                meshes[int(mesh_index)] = mesh
            except Exception:
                pass
        return None

    def __SceneMeshWithFaceIds(self, mesh_index, context):
        mesh = self.EEE[int(mesh_index)]
        try:
            surface_index = int(self.GlassOnSide[int(mesh_index)])
            is_optical_solid = self.SDT[surface_index].Solid_3d_stl != 'None'
        except Exception:
            return mesh
        if not is_optical_solid:
            return mesh
        try:
            mesh = assign_mesh_cell_face_ids(
                mesh,
                self.__OpticalSolidWorldFaces(surface_index),
                context=context,
            )
            self.__ReplaceSceneMesh(mesh_index, mesh)
        except Exception:
            pass
        return mesh

    def __TraceSceneMeshRay(self, mesh_index, ray_start, ray_stop, context):
        mesh_index = int(mesh_index)
        mesh = self.__SceneMeshWithFaceIds(mesh_index, context)
        mesh, (points, hits) = trace_mesh_ray(
            mesh,
            ray_start,
            ray_stop,
            context=context,
        )
        if mesh is not self.EEE[mesh_index]:
            self.__ReplaceSceneMesh(mesh_index, mesh)
        return points, hits


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
            (A_pTarget, A_SurfHit) = self.__TraceSceneMeshRay(
                k,
                A_RayOrig,
                A_Proto_pTarget,
                f"non-sequential chooser surface {k}",
            )
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

    def __NonSequentialChooser(self, SIGN, A_RayOrig, ResVec, j, skip_surface=None):
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
        if skip_surface is not None:
            try:
                skip_index = int(skip_surface)
            except Exception:
                skip_index = -1
            if 1 <= skip_index < len(self.EEE):
                chooser[skip_index - 1] = 99999999999999.9
        if chooser.size == 0 or float(np.min(chooser)) >= 9999999999999.0:
            return (int(j), 0, 0, 0)
        jj = (np.argmin(chooser) + 1)
        chooser[(jj - 1)] = 99999999999999.9
        kk = (np.argmin(chooser) + 1)
        (A_pTarget, A_SurfHit) = self.__TraceSceneMeshRay(
            int(jj),
            A_RayOrig,
            A_Proto_pTarget,
            f"non-sequential chooser surface {int(jj)}",
        )
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
        self.INTERACTION_TYPE = []
        self.INTERACTION_MODEL = []
        self.INTERACTION_TARGET_SURFACE = []
        self.INTERACTION_IN_POWER = []
        self.INTERACTION_COEFF = []
        self.INTERACTION_OUT_POWER = []
        self.INTERACTION_LOSS_POWER = []
        self.INTERACTION_BULK = []
        self.MESH_CELL_ID = []
        self.MESH_ORIGINAL_CELL_ID = []
        self.MESH_FACE_ID = []
        self.MESH_FACE_MATCH_METHOD = []
        self.MESH_FACE_MATCH_SCORE = []
        self._collect_tt_override = None
        self._collect_bulk_override = None
        self._collect_interaction_override = None
        self._collect_mesh_hit_override = None
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

        interaction_in_power = float(self.TT)
        interaction_override = dict(self._collect_interaction_override or {})
        self._collect_interaction_override = None
        mesh_hit_override = dict(self._collect_mesh_hit_override or {})
        self._collect_mesh_hit_override = None

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
        if self._collect_bulk_override is not None:
            if len(self.BULK_TRANS) == 0:
                self.BULK_TRANS.append(float(self._collect_bulk_override))
            else:
                self.BULK_TRANS[-1] = float(self._collect_bulk_override)
            self._collect_bulk_override = None

        if not self.tt:
            self.tt=0

        if len(self.BULK_TRANS) == 0:
            self.BULK_TRANS=[1]

        interaction_bulk = float(self.BULK_TRANS[-1])
        interaction_coeff = float(self.tt * interaction_bulk)
        self.TTBE.append(interaction_coeff)
        self.TT = (self.TT * interaction_coeff)
        interaction_out_power = float(self.TT)
        interaction_loss_power = max(interaction_in_power - interaction_out_power, 0.0)
        interaction_type = str(interaction_override.get("type", "") or "").strip()
        if not interaction_type:
            glass_text = str(Glass).strip().upper()
            if glass_text == "ABSORB":
                interaction_type = "absorb"
            elif glass_text == "MIRROR":
                interaction_type = "reflect"
            elif RayTraceType in (0, 1):
                try:
                    interaction_type = "refract" if abs(float(PrevN) - float(CurrN)) > 1e-9 else "transmit"
                except Exception:
                    interaction_type = "transmit"
            else:
                interaction_type = "trace"
        try:
            target_surface = int(interaction_override.get("target_surface", -1))
        except Exception:
            target_surface = -1
        self.INTERACTION_TYPE.append(interaction_type)
        self.INTERACTION_MODEL.append(str(interaction_override.get("model", "") or ""))
        self.INTERACTION_TARGET_SURFACE.append(target_surface)
        self.INTERACTION_IN_POWER.append(interaction_in_power)
        self.INTERACTION_COEFF.append(interaction_coeff)
        self.INTERACTION_OUT_POWER.append(interaction_out_power)
        self.INTERACTION_LOSS_POWER.append(interaction_loss_power)
        self.INTERACTION_BULK.append(interaction_bulk)
        try:
            mesh_cell_id = int(mesh_hit_override.get("cell_id", -1))
        except Exception:
            mesh_cell_id = -1
        try:
            mesh_original_cell_id = int(mesh_hit_override.get("original_cell_id", -1))
        except Exception:
            mesh_original_cell_id = -1
        self.MESH_CELL_ID.append(mesh_cell_id)
        self.MESH_ORIGINAL_CELL_ID.append(mesh_original_cell_id)
        self.MESH_FACE_ID.append(str(mesh_hit_override.get("face_id", "") or ""))
        self.MESH_FACE_MATCH_METHOD.append(str(mesh_hit_override.get("face_match_method", "") or ""))
        try:
            mesh_face_match_score = float(mesh_hit_override.get("face_match_score"))
        except Exception:
            mesh_face_match_score = np.nan
        self.MESH_FACE_MATCH_SCORE.append(mesh_face_match_score)

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
        self._optical_solid_face_world_cache = {}
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
        mode = str(settings.get("split_mode", settings.get("mode", "Deterministic paths"))).strip().lower()
        deterministic = "deterministic" in mode or "ideal" in mode or "plate" in mode
        if "monte" in mode or "stochastic" in mode or "probab" in mode:
            deterministic = False
        compact_mode = "".join(ch for ch in mode if ch.isalnum())
        use_coating_table = deterministic and ("coating table" in mode)
        use_fresnel_polarization = deterministic and (
            "fresnel" in mode
            or "polarization" in mode
            or "polarisation" in mode
            or "ps" in compact_mode
        ) and not use_coating_table
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
        try:
            transmit_s_phase = float(
                settings.get(
                    "transmit_s_phase_deg",
                    settings.get(
                        "transmit_retardance_deg",
                        settings.get("transmit_s_retardance_deg", settings.get("t_s_phase_deg", 0.0)),
                    ),
                )
            )
        except Exception:
            transmit_s_phase = 0.0
        if not np.isfinite(transmit_s_phase):
            transmit_s_phase = 0.0
        try:
            reflect_s_phase = float(
                settings.get(
                    "reflect_s_phase_deg",
                    settings.get(
                        "reflect_retardance_deg",
                        settings.get("reflect_s_retardance_deg", settings.get("r_s_phase_deg", 0.0)),
                    ),
                )
            )
        except Exception:
            reflect_s_phase = 0.0
        if not np.isfinite(reflect_s_phase):
            reflect_s_phase = 0.0
        try:
            polarization_p_fraction = float(
                settings.get(
                    "polarization_p_fraction",
                    settings.get("p_polarization_fraction", settings.get("p_fraction", 0.5)),
                )
            )
        except Exception:
            polarization_p_fraction = 0.5
        if not np.isfinite(polarization_p_fraction):
            polarization_p_fraction = 0.5
        polarization_p_fraction = min(max(polarization_p_fraction, 0.0), 1.0)
        try:
            polarization_s_phase = float(
                settings.get(
                    "polarization_s_phase_deg",
                    settings.get("s_phase_deg", settings.get("jones_s_phase_deg", 0.0)),
                )
            )
        except Exception:
            polarization_s_phase = 0.0
        if not np.isfinite(polarization_s_phase):
            polarization_s_phase = 0.0
        return {
            "deterministic": deterministic,
            "use_coating_table": use_coating_table,
            "use_fresnel_polarization": use_fresnel_polarization,
            "reflectance": reflectance,
            "transmittance": transmittance,
            "absorption": absorption,
            "polarization_p_fraction": polarization_p_fraction,
            "polarization_s_phase_deg": polarization_s_phase,
            "min_branch_power": max(min_power, 0.0),
            "max_branch_depth": max(max_depth, 1),
            "transmit_phase_deg": transmit_phase,
            "reflect_phase_deg": reflect_phase,
            "transmit_s_phase_deg": transmit_s_phase,
            "reflect_s_phase_deg": reflect_s_phase,
        }

    def __DiffuseScatterSettings(self, j):
        settings = getattr(self.SDT[j], "DiffuseScatter", None)
        if not isinstance(settings, dict) or not settings:
            return None
        model = str(settings.get("model", "Lambertian") or "Lambertian").strip()
        if model.lower() in {"lambert", "lambertian diffuse", "diffuse"}:
            model = "Lambertian"
        elif model.lower() in {"cosine lobe", "cosine-lobe", "glossy", "phong", "specular lobe", "specular-lobe"}:
            model = "Cosine Lobe"
        elif model.lower() in {"oren-nayar", "oren nayar", "rough diffuse", "rough-diffuse"}:
            model = "Oren-Nayar"
        elif model.lower() in {"pyscatmech brdf", "pyscatmech", "scatmech", "brdf", "measured brdf"}:
            model = "pySCATMECH BRDF"
        if model not in {"Lambertian", "Cosine Lobe", "Oren-Nayar", "pySCATMECH BRDF"}:
            return None
        backend = str(settings.get("backend", "Built-in") or "Built-in").strip()
        if "pyscatmech" in backend.lower():
            backend = "pySCATMECH"
        else:
            backend = "Built-in"
        if model == "pySCATMECH BRDF":
            backend = "pySCATMECH"
        try:
            reflectance = float(settings.get("reflectance", settings.get("albedo", 0.8)))
        except Exception:
            reflectance = 0.8
        try:
            sample_count = int(float(settings.get("sample_count", settings.get("samples", 9))))
        except Exception:
            sample_count = 9
        try:
            max_angle = float(settings.get("max_scatter_angle_deg", settings.get("cone_angle_deg", 90.0)))
        except Exception:
            max_angle = 90.0
        try:
            min_power = float(settings.get("min_branch_power", 1e-4))
        except Exception:
            min_power = 1e-4
        try:
            max_depth = int(float(settings.get("max_branch_depth", settings.get("max_scatter_depth", 2))))
        except Exception:
            max_depth = 2
        try:
            lobe_exponent = float(
                settings.get(
                    "lobe_exponent",
                    settings.get("cosine_exponent", settings.get("phong_exponent", settings.get("gloss_exponent", 20.0))),
                )
            )
        except Exception:
            lobe_exponent = 20.0
        if not np.isfinite(lobe_exponent):
            lobe_exponent = 20.0
        try:
            roughness_deg = float(
                settings.get(
                    "roughness_deg",
                    settings.get("sigma_deg", settings.get("sigma", settings.get("roughness", 20.0))),
                )
            )
        except Exception:
            roughness_deg = 20.0
        if not np.isfinite(roughness_deg):
            roughness_deg = 20.0
        backend_model = str(
            settings.get(
                "backend_model",
                settings.get("brdf_model", settings.get("pyscatmech_model", "Microroughness_BRDF_Model")),
            )
            or "Microroughness_BRDF_Model"
        ).strip() or "Microroughness_BRDF_Model"
        try:
            backend_parameters = normalize_pyscatmech_parameters(
                settings.get(
                    "backend_parameters",
                    settings.get("pyscatmech_parameters", settings.get("brdf_parameters", {})),
                )
            )
        except Exception:
            backend_parameters = {}
        target_value = settings.get(
            "target_surface",
            settings.get("guided_target_surface", settings.get("target_surface_index", None)),
        )
        target_surface = None
        if target_value is not None:
            try:
                target_text = str(target_value).strip()
                if target_text and target_text.lower() not in {"none", "auto", "off", "disabled"}:
                    if target_text.upper().startswith("S"):
                        target_text = target_text[1:]
                    target_text = target_text.split(":", 1)[0].strip()
                    target_surface = int(float(target_text))
                    if target_surface < 0 or target_surface >= self.n:
                        target_surface = None
            except Exception:
                target_surface = None
        try:
            target_radius_scale = float(
                settings.get(
                    "target_radius_scale",
                    settings.get("guided_target_radius_scale", settings.get("target_radius_factor", 1.0)),
                )
            )
        except Exception:
            target_radius_scale = 1.0
        if not np.isfinite(target_radius_scale):
            target_radius_scale = 1.0
        return {
            "model": model,
            "backend": backend,
            "reflectance": min(max(reflectance, 0.0), 1.0),
            "sample_count": max(1, min(sample_count, 257)),
            "max_scatter_angle_deg": min(max(max_angle, 0.0), 90.0),
            "min_branch_power": max(min_power, 0.0),
            "max_branch_depth": max(1, min(max_depth, 32)),
            "lobe_exponent": min(max(lobe_exponent, 0.0), 10000.0),
            "roughness_deg": min(max(roughness_deg, 0.0), 90.0),
            "backend_model": backend_model,
            "backend_parameters": backend_parameters,
            "target_surface": target_surface,
            "target_radius_scale": min(max(target_radius_scale, 0.01), 4.0),
        }

    def __NsTraceRequiresBranching(self):
        return self.__NsTraceHasDeterministicBeamSplitter() or self.__NsTraceHasDiffuseScatter()

    def __NsTraceHasDiffuseScatter(self):
        for j in range(0, self.n):
            settings = self.__DiffuseScatterSettings(j)
            if settings is not None and settings["reflectance"] > 0.0 and settings["sample_count"] > 0:
                return True
        return False

    def __LambertianScatterDirections(self, incident, normal, settings):
        incident_vec = self.__NormalizeVector(incident)
        normal_vec = self.__NormalizeVector(normal)
        if float(np.dot(incident_vec, normal_vec)) > 0.0:
            normal_vec = -normal_vec
        sample_count = int(settings["sample_count"])
        max_theta = np.deg2rad(float(settings["max_scatter_angle_deg"]))
        if sample_count <= 1 or max_theta <= 1e-12:
            return [normal_vec]
        reference = np.asarray((0.0, 0.0, 1.0), dtype=float)
        if abs(float(np.dot(reference, normal_vec))) > 0.94:
            reference = np.asarray((0.0, 1.0, 0.0), dtype=float)
        tangent = np.cross(reference, normal_vec)
        tangent = tangent / max(float(np.linalg.norm(tangent)), 1e-15)
        bitangent = np.cross(normal_vec, tangent)
        bitangent = bitangent / max(float(np.linalg.norm(bitangent)), 1e-15)
        directions = [normal_vec]
        golden_angle = np.pi * (3.0 - np.sqrt(5.0))
        sin2_max = float(np.sin(max_theta) ** 2.0)
        remaining = max(sample_count - 1, 1)
        for index in range(remaining):
            u = (index + 0.5) / float(remaining)
            cos_theta = np.sqrt(max(1.0 - (u * sin2_max), 0.0))
            sin_theta = np.sqrt(max(1.0 - (cos_theta * cos_theta), 0.0))
            phi = index * golden_angle
            direction = (
                (np.cos(phi) * sin_theta * tangent)
                + (np.sin(phi) * sin_theta * bitangent)
                + (cos_theta * normal_vec)
            )
            directions.append(self.__NormalizeVector(direction, fallback=normal_vec))
        return directions[:sample_count]

    def __CosineLobeScatterDirections(self, incident, normal, settings):
        incident_vec = self.__NormalizeVector(incident)
        normal_vec = self.__NormalizeVector(normal)
        if float(np.dot(incident_vec, normal_vec)) > 0.0:
            normal_vec = -normal_vec
        lobe_axis = self.__ReflectVector(incident_vec, normal_vec)
        lobe_axis = self.__NormalizeVector(lobe_axis, fallback=normal_vec)
        if float(np.dot(lobe_axis, normal_vec)) <= 1e-9:
            lobe_axis = normal_vec
        sample_count = int(settings["sample_count"])
        max_theta = np.deg2rad(float(settings["max_scatter_angle_deg"]))
        if sample_count <= 1 or max_theta <= 1e-12:
            return [lobe_axis]
        reference = np.asarray((0.0, 0.0, 1.0), dtype=float)
        if abs(float(np.dot(reference, lobe_axis))) > 0.94:
            reference = np.asarray((0.0, 1.0, 0.0), dtype=float)
        tangent = np.cross(reference, lobe_axis)
        tangent = tangent / max(float(np.linalg.norm(tangent)), 1e-15)
        bitangent = np.cross(lobe_axis, tangent)
        bitangent = bitangent / max(float(np.linalg.norm(bitangent)), 1e-15)
        directions = [lobe_axis]
        golden_angle = np.pi * (3.0 - np.sqrt(5.0))
        exponent = max(float(settings.get("lobe_exponent", 20.0)), 0.0)
        cos_min = max(float(np.cos(max_theta)), 0.0)
        remaining = max(sample_count - 1, 1)
        for index in range(remaining):
            u = (index + 0.5) / float(remaining)
            cos_theta = (1.0 - (u * (1.0 - (cos_min ** (exponent + 1.0))))) ** (1.0 / (exponent + 1.0))
            sin_theta = np.sqrt(max(1.0 - (cos_theta * cos_theta), 0.0))
            phi = index * golden_angle
            direction = (
                (np.cos(phi) * sin_theta * tangent)
                + (np.sin(phi) * sin_theta * bitangent)
                + (cos_theta * lobe_axis)
            )
            direction = self.__NormalizeVector(direction, fallback=lobe_axis)
            if float(np.dot(direction, normal_vec)) > 1e-9:
                directions.append(direction)
        if len(directions) == 1 and sample_count > 1:
            return directions
        return directions[:sample_count]

    def __OrenNayarDirectionalTerm(self, incident, outgoing, normal, settings):
        incident_vec = self.__NormalizeVector(incident)
        outgoing_vec = self.__NormalizeVector(outgoing)
        normal_vec = self.__NormalizeVector(normal)
        if float(np.dot(incident_vec, normal_vec)) > 0.0:
            normal_vec = -normal_vec

        wi = self.__NormalizeVector(-incident_vec, fallback=normal_vec)
        wo = self.__NormalizeVector(outgoing_vec, fallback=normal_vec)
        cos_theta_i = min(max(float(np.dot(wi, normal_vec)), 0.0), 1.0)
        cos_theta_o = min(max(float(np.dot(wo, normal_vec)), 0.0), 1.0)
        if cos_theta_i <= 1e-12 or cos_theta_o <= 1e-12:
            return 0.0

        theta_i = float(np.arccos(cos_theta_i))
        theta_o = float(np.arccos(cos_theta_o))
        alpha = max(theta_i, theta_o)
        beta = min(theta_i, theta_o)

        wi_proj = wi - (cos_theta_i * normal_vec)
        wo_proj = wo - (cos_theta_o * normal_vec)
        wi_proj_norm = float(np.linalg.norm(wi_proj))
        wo_proj_norm = float(np.linalg.norm(wo_proj))
        cos_phi_diff = 0.0
        if wi_proj_norm > 1e-12 and wo_proj_norm > 1e-12:
            cos_phi_diff = float(
                np.dot(wi_proj / wi_proj_norm, wo_proj / wo_proj_norm)
            )

        sigma = np.deg2rad(float(settings.get("roughness_deg", 20.0)))
        sigma2 = float(sigma * sigma)
        A = 1.0 - (0.5 * sigma2 / (sigma2 + 0.33))
        B = 0.45 * sigma2 / (sigma2 + 0.09)
        tan_beta = float(np.sin(beta) / max(np.cos(beta), 1e-12))
        return max(
            A + (B * max(0.0, cos_phi_diff) * float(np.sin(alpha)) * tan_beta),
            0.0,
        )

    def __SurfaceWorldPoint(self, surface_index, local_xyz=(0.0, 0.0, 0.0)):
        try:
            surface_index = int(surface_index)
            transform = np.asarray(self.Pr3D.TRANS_2A[surface_index], dtype=float)
            local_point = np.asarray(
                [float(local_xyz[0]), float(local_xyz[1]), float(local_xyz[2]), 1.0],
                dtype=float,
            )
            world_point = transform.dot(local_point)
            return np.asarray(world_point, dtype=float).reshape(-1)[:3]
        except Exception:
            return None

    def __SurfaceWorldNormal(self, surface_index):
        center = self.__SurfaceWorldPoint(surface_index, (0.0, 0.0, 0.0))
        z_point = self.__SurfaceWorldPoint(surface_index, (0.0, 0.0, 1.0))
        if center is None or z_point is None:
            return None
        normal = np.asarray(z_point, dtype=float) - np.asarray(center, dtype=float)
        return self.__NormalizeVector(normal, fallback=np.asarray((0.0, 0.0, 1.0), dtype=float))

    def __SurfaceRadius(self, surface_index):
        try:
            diameter = float(getattr(self.SDT[int(surface_index)], "Diameter", 0.0))
        except Exception:
            diameter = 0.0
        if not np.isfinite(diameter) or diameter <= 0.0:
            diameter = 2.0
        return max(abs(diameter) * 0.5, 1e-6)

    def __LambertianScatterSamples(self, incident, normal, hit_point, settings):
        use_pyscatmech = str(settings.get("backend", "Built-in") or "Built-in").strip().lower() == "pyscatmech"
        target_surface = settings.get("target_surface")
        if target_surface is None:
            model = str(settings.get("model", "Lambertian") or "Lambertian")
            if use_pyscatmech:
                directions = self.__LambertianScatterDirections(incident, normal, settings)
                weighted_samples = []
                normal_vec = self.__NormalizeVector(normal)
                incident_vec = self.__NormalizeVector(incident)
                if float(np.dot(incident_vec, normal_vec)) > 0.0:
                    normal_vec = -normal_vec
                for direction in directions:
                    cos_out = max(float(np.dot(self.__NormalizeVector(direction), normal_vec)), 0.0)
                    if cos_out <= 1e-12:
                        continue
                    try:
                        phase_weight = pyscatmech_scalar_brdf(
                            str(settings.get("backend_model", "Microroughness_BRDF_Model")),
                            settings.get("backend_parameters", {}),
                            incident,
                            direction,
                            normal,
                            self.Wave,
                        )
                    except Exception:
                        phase_weight = 0.0
                    weight = float(phase_weight) * cos_out
                    if weight > 0.0 and np.isfinite(weight):
                        weighted_samples.append((direction, weight))
                if weighted_samples:
                    total_weight = sum(float(weight) for _direction, weight in weighted_samples)
                    if total_weight > 0.0:
                        return [
                            (direction, float(settings["reflectance"]) * float(weight) / float(total_weight))
                            for direction, weight in weighted_samples
                        ]
                fallback_settings = dict(settings)
                fallback_settings["backend"] = "Built-in"
                fallback_settings["model"] = "Lambertian"
                return self.__LambertianScatterSamples(incident, normal, hit_point, fallback_settings)
            if model == "Cosine Lobe":
                directions = self.__CosineLobeScatterDirections(incident, normal, settings)
                child_count = max(len(directions), 1)
                child_coeff = float(settings["reflectance"]) / float(child_count)
                return [(direction, child_coeff) for direction in directions]
            directions = self.__LambertianScatterDirections(incident, normal, settings)
            if model == "Oren-Nayar":
                weighted_samples = []
                for direction in directions:
                    phase_weight = self.__OrenNayarDirectionalTerm(incident, direction, normal, settings)
                    if phase_weight > 0.0 and np.isfinite(phase_weight):
                        weighted_samples.append((direction, float(phase_weight)))
                if not weighted_samples:
                    directions = self.__LambertianScatterDirections(incident, normal, {**settings, "model": "Lambertian"})
                    child_count = max(len(directions), 1)
                    child_coeff = float(settings["reflectance"]) / float(child_count)
                    return [(direction, child_coeff) for direction in directions]
                total_weight = sum(float(weight) for _direction, weight in weighted_samples)
                if total_weight <= 0.0:
                    child_count = max(len(weighted_samples), 1)
                    child_coeff = float(settings["reflectance"]) / float(child_count)
                    return [(direction, child_coeff) for direction, _weight in weighted_samples]
                return [
                    (direction, float(settings["reflectance"]) * float(weight) / float(total_weight))
                    for direction, weight in weighted_samples
                ]
            child_count = max(len(directions), 1)
            child_coeff = float(settings["reflectance"]) / float(child_count)
            return [(direction, child_coeff) for direction in directions]

        incident_vec = self.__NormalizeVector(incident)
        normal_vec = self.__NormalizeVector(normal)
        if float(np.dot(incident_vec, normal_vec)) > 0.0:
            normal_vec = -normal_vec

        target_center = self.__SurfaceWorldPoint(target_surface, (0.0, 0.0, 0.0))
        target_normal = self.__SurfaceWorldNormal(target_surface)
        if target_center is None or target_normal is None:
            return self.__LambertianScatterSamples(
                incident,
                normal,
                hit_point,
                {**settings, "target_surface": None},
            )

        sample_count = int(settings["sample_count"])
        max_theta = np.deg2rad(float(settings["max_scatter_angle_deg"]))
        cos_min = float(np.cos(max_theta))
        use_cosine_lobe = settings.get("model") == "Cosine Lobe"
        use_oren_nayar = settings.get("model") == "Oren-Nayar"
        lobe_axis = None
        lobe_normalization = None
        if use_cosine_lobe:
            lobe_axis = self.__ReflectVector(incident_vec, normal_vec)
            lobe_axis = self.__NormalizeVector(lobe_axis, fallback=normal_vec)
            if float(np.dot(lobe_axis, normal_vec)) <= 1e-9:
                lobe_axis = normal_vec
            exponent = max(float(settings.get("lobe_exponent", 20.0)), 0.0)
            cone_integral = 1.0 - (max(cos_min, 0.0) ** (exponent + 1.0))
            lobe_normalization = (exponent + 1.0) / (2.0 * np.pi * max(cone_integral, 1e-15))
        radius = self.__SurfaceRadius(target_surface) * float(settings.get("target_radius_scale", 1.0))
        radius = max(radius, 1e-6)
        hit_point = np.asarray(hit_point, dtype=float)

        offsets = [(0.0, 0.0)]
        if sample_count > 1:
            golden_angle = np.pi * (3.0 - np.sqrt(5.0))
            remaining = sample_count - 1
            for index in range(remaining):
                radial = radius * np.sqrt((index + 0.5) / float(remaining))
                phi = index * golden_angle
                offsets.append((radial * np.cos(phi), radial * np.sin(phi)))

        samples = []
        sample_area = (np.pi * radius * radius) / float(max(len(offsets), 1))
        for offset_x, offset_y in offsets[:sample_count]:
            target_point = self.__SurfaceWorldPoint(target_surface, (offset_x, offset_y, 0.0))
            if target_point is None:
                continue
            vector = np.asarray(target_point, dtype=float) - hit_point
            distance_sq = float(np.dot(vector, vector))
            if distance_sq <= 1e-18:
                continue
            direction = self.__NormalizeVector(vector, fallback=normal_vec)
            cos_out = float(np.dot(direction, normal_vec))
            if cos_out <= 1e-9 or cos_out + 1e-12 < cos_min:
                continue
            target_projection = abs(float(np.dot(target_normal, -direction)))
            if target_projection <= 1e-9:
                continue
            if use_pyscatmech:
                try:
                    phase_weight = pyscatmech_scalar_brdf(
                        str(settings.get("backend_model", "Microroughness_BRDF_Model")),
                        settings.get("backend_parameters", {}),
                        incident_vec,
                        direction,
                        normal_vec,
                        self.Wave,
                    )
                except Exception:
                    phase_weight = 0.0
                if phase_weight <= 1e-12 or not np.isfinite(phase_weight):
                    continue
                coeff = (
                    float(settings["reflectance"])
                    * float(phase_weight)
                    * cos_out
                    * target_projection
                    * sample_area
                    / distance_sq
                )
            elif use_cosine_lobe:
                cos_lobe = float(np.dot(direction, lobe_axis))
                if cos_lobe <= 1e-9 or cos_lobe + 1e-12 < cos_min:
                    continue
                phase_weight = float(lobe_normalization) * (cos_lobe ** float(settings.get("lobe_exponent", 20.0)))
                coeff = float(settings["reflectance"]) * phase_weight * target_projection * sample_area / distance_sq
            elif use_oren_nayar:
                phase_weight = self.__OrenNayarDirectionalTerm(incident_vec, direction, normal_vec, settings) / np.pi
                if phase_weight <= 1e-12 or not np.isfinite(phase_weight):
                    continue
                coeff = (
                    float(settings["reflectance"])
                    * phase_weight
                    * cos_out
                    * target_projection
                    * sample_area
                    / distance_sq
                )
            else:
                coeff = (
                    float(settings["reflectance"])
                    * cos_out
                    * target_projection
                    * sample_area
                    / (np.pi * distance_sq)
                )
            if coeff > 0.0 and np.isfinite(coeff):
                samples.append((direction, coeff))

        if not samples:
            return self.__LambertianScatterSamples(
                incident,
                normal,
                hit_point,
                {**settings, "target_surface": None},
            )

        total_coeff = sum(float(coeff) for _direction, coeff in samples)
        reflectance = float(settings["reflectance"])
        if total_coeff > reflectance and total_coeff > 0.0:
            scale = reflectance / total_coeff
            samples = [(direction, float(coeff) * scale) for direction, coeff in samples]
        return samples

    def __DiffuseInteractionModelLabel(self, settings):
        backend = str(settings.get("backend", "Built-in") or "Built-in").strip()
        if backend == "pySCATMECH":
            status = pyscatmech_status()
            model_name = str(settings.get("backend_model", "Microroughness_BRDF_Model") or "Microroughness_BRDF_Model").strip()
            if bool(status.get("available")):
                return f"pySCATMECH:{model_name}"
            return f"pySCATMECH fallback ({model_name})"
        return str(settings.get("model", "") or "")

    def __NormalizeJonesVector(self, p_component, s_component):
        try:
            p_value = complex(p_component)
        except Exception:
            p_value = complex(1.0, 0.0)
        try:
            s_value = complex(s_component)
        except Exception:
            s_value = complex(0.0, 0.0)
        norm = float(np.sqrt((abs(p_value) ** 2.0) + (abs(s_value) ** 2.0)))
        if (not np.isfinite(norm)) or norm <= 1e-15:
            return complex(1.0, 0.0), complex(0.0, 0.0)
        return p_value / norm, s_value / norm

    def __NormalizeVector(self, vector, fallback=(0.0, 0.0, 1.0)):
        try:
            value = np.asarray(vector, dtype=float).reshape(-1)[:3]
        except Exception:
            value = np.asarray(fallback, dtype=float)
        if value.size < 3:
            value = np.asarray(fallback, dtype=float)
        norm = float(np.linalg.norm(value))
        if not np.isfinite(norm) or norm <= 1e-15:
            value = np.asarray(fallback, dtype=float)
            norm = float(np.linalg.norm(value)) or 1.0
        return value / norm

    def __PolarizationBasis(self, direction, normal=None):
        k_vec = self.__NormalizeVector(direction)
        if normal is not None:
            n_vec = self.__NormalizeVector(normal)
            s_vec = np.cross(n_vec, k_vec)
        else:
            reference = np.asarray((0.0, 0.0, 1.0), dtype=float)
            if abs(float(np.dot(reference, k_vec))) > 0.94:
                reference = np.asarray((0.0, 1.0, 0.0), dtype=float)
            s_vec = np.cross(reference, k_vec)
        s_norm = float(np.linalg.norm(s_vec))
        if not np.isfinite(s_norm) or s_norm <= 1e-15:
            reference = np.asarray((0.0, 1.0, 0.0), dtype=float)
            if abs(float(np.dot(reference, k_vec))) > 0.94:
                reference = np.asarray((1.0, 0.0, 0.0), dtype=float)
            s_vec = np.cross(reference, k_vec)
            s_norm = float(np.linalg.norm(s_vec)) or 1.0
        s_vec = s_vec / s_norm
        p_vec = np.cross(s_vec, k_vec)
        p_norm = float(np.linalg.norm(p_vec))
        if not np.isfinite(p_norm) or p_norm <= 1e-15:
            p_vec = np.cross(k_vec, s_vec)
            p_norm = float(np.linalg.norm(p_vec)) or 1.0
        p_vec = p_vec / p_norm
        return p_vec, s_vec, k_vec

    def __NormalizePolarizationVector(self, vector, direction=None):
        try:
            value = np.asarray(vector, dtype=np.complex128).reshape(-1)[:3]
        except Exception:
            value = np.asarray((1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j), dtype=np.complex128)
        if value.size < 3:
            value = np.asarray((1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j), dtype=np.complex128)
        if direction is not None:
            k_vec = self.__NormalizeVector(direction)
            value = value - (np.dot(value, k_vec) * k_vec)
        norm = float(np.sqrt(np.sum(np.abs(value) ** 2.0)))
        if not np.isfinite(norm) or norm <= 1e-15:
            p_vec, _s_vec, _k_vec = self.__PolarizationBasis(direction if direction is not None else (0.0, 0.0, 1.0))
            value = np.asarray(p_vec, dtype=np.complex128)
            norm = float(np.sqrt(np.sum(np.abs(value) ** 2.0))) or 1.0
        return value / norm

    def __JonesToPolarizationVector(self, jones, direction, normal=None):
        p_value, s_value = self.__NormalizeJonesVector(jones[0], jones[1])
        p_basis, s_basis, _k_basis = self.__PolarizationBasis(direction, normal)
        vector = (p_value * p_basis.astype(np.complex128)) + (s_value * s_basis.astype(np.complex128))
        return self.__NormalizePolarizationVector(vector, direction)

    def __PolarizationVectorToJones(self, vector, direction, normal=None):
        field = self.__NormalizePolarizationVector(vector, direction)
        p_basis, s_basis, _k_basis = self.__PolarizationBasis(direction, normal)
        p_value = np.dot(field, p_basis)
        s_value = np.dot(field, s_basis)
        return self.__NormalizeJonesVector(p_value, s_value)

    def __BeamSplitterSettingsJones(self, settings):
        p_fraction = float(settings.get("polarization_p_fraction", 0.5))
        if not np.isfinite(p_fraction):
            p_fraction = 0.5
        p_fraction = min(max(p_fraction, 0.0), 1.0)
        s_phase = np.deg2rad(float(settings.get("polarization_s_phase_deg", 0.0)))
        if not np.isfinite(s_phase):
            s_phase = 0.0
        p_component = np.sqrt(p_fraction)
        s_component = np.sqrt(max(1.0 - p_fraction, 0.0)) * np.exp(1j * s_phase)
        return self.__NormalizeJonesVector(p_component, s_component)

    def __BeamSplitterStatePolarization(self, state, settings, direction, normal=None):
        vector = state.get("branch_polarization_xyz")
        if vector is not None:
            return self.__NormalizePolarizationVector(vector, direction)
        return self.__JonesToPolarizationVector(self.__BeamSplitterStateJones(state, settings), direction, normal)

    def __BeamSplitterStateJones(self, state, settings, direction=None, normal=None):
        vector = state.get("branch_polarization_xyz")
        if vector is not None and direction is not None:
            return self.__PolarizationVectorToJones(vector, direction, normal)
        p_value = state.get("branch_jones_p")
        s_value = state.get("branch_jones_s")
        if p_value is None or s_value is None:
            return self.__BeamSplitterSettingsJones(settings)
        return self.__NormalizeJonesVector(p_value, s_value)

    def __JonesPowerWeights(self, jones):
        p_value, s_value = self.__NormalizeJonesVector(jones[0], jones[1])
        p_weight = float(abs(p_value) ** 2.0)
        s_weight = float(abs(s_value) ** 2.0)
        total = p_weight + s_weight
        if (not np.isfinite(total)) or total <= 1e-15:
            return 1.0, 0.0
        return p_weight / total, s_weight / total

    def __BeamSplitterChildJones(self, incident_jones, child_label, channel_coefficients, settings=None):
        p_in, s_in = self.__NormalizeJonesVector(incident_jones[0], incident_jones[1])
        channel = channel_coefficients.get(child_label, (1.0, 1.0))
        try:
            p_coeff = max(float(channel[0]), 0.0)
        except Exception:
            p_coeff = 1.0
        try:
            s_coeff = max(float(channel[1]), 0.0)
        except Exception:
            s_coeff = 1.0
        p_out = p_in * np.sqrt(p_coeff)
        s_phase_deg = 0.0
        if isinstance(settings, dict):
            phase_key = "reflect_s_phase_deg" if str(child_label).lower().startswith("reflect") else "transmit_s_phase_deg"
            try:
                s_phase_deg = float(settings.get(phase_key, 0.0))
            except Exception:
                s_phase_deg = 0.0
            if not np.isfinite(s_phase_deg):
                s_phase_deg = 0.0
        s_out = s_in * np.sqrt(s_coeff) * np.exp(1j * np.deg2rad(s_phase_deg))
        return self.__NormalizeJonesVector(p_out, s_out)

    def __TransportPolarizationVector(self, vector, new_direction):
        return self.__NormalizePolarizationVector(vector, new_direction)

    def __BeamSplitterCoefficients(
        self,
        j,
        settings,
        angle,
        prev_n=None,
        curr_n=None,
        imp_vec=None,
        surf_norm=None,
        trans_vec=None,
        input_jones=None,
    ):
        reflectance = float(settings["reflectance"])
        transmittance = float(settings["transmittance"])
        absorption = float(settings["absorption"])
        channel_coefficients = {
            "transmit": (transmittance, transmittance),
            "reflect": (reflectance, reflectance),
        }
        if settings.get("use_fresnel_polarization", False) and all(
            value is not None for value in (prev_n, curr_n, imp_vec, surf_norm, trans_vec)
        ):
            try:
                mtl = self.SDT[j].CoatingMet
                Rp, Rs, Tp, Ts = FresnelEnergy(
                    self.Glass[j],
                    prev_n,
                    curr_n,
                    np.asarray(imp_vec, dtype=float),
                    np.asarray(surf_norm, dtype=float),
                    np.asarray(trans_vec, dtype=float),
                    self.SETUP,
                    self.Wave,
                    mtl,
                )
                incident_jones = input_jones if input_jones is not None else self.__BeamSplitterSettingsJones(settings)
                p_weight, s_weight = self.__JonesPowerWeights(incident_jones)
                reflectance = min(max(float((p_weight * Rp) + (s_weight * Rs)), 0.0), 1.0)
                transmittance = min(max(float((p_weight * Tp) + (s_weight * Ts)), 0.0), 1.0)
                channel_coefficients = {
                    "transmit": (min(max(float(Tp), 0.0), 1.0), min(max(float(Ts), 0.0), 1.0)),
                    "reflect": (min(max(float(Rp), 0.0), 1.0), min(max(float(Rs), 0.0), 1.0)),
                }
                total = reflectance + transmittance
                if total > 1.0:
                    scale = 1.0 / total
                    reflectance /= total
                    transmittance /= total
                    channel_coefficients = {
                        key: (float(value[0]) * scale, float(value[1]) * scale)
                        for key, value in channel_coefficients.items()
                    }
                    absorption = 0.0
                else:
                    absorption = max(1.0 - total, 0.0)
            except Exception:
                pass
        if settings.get("use_coating_table", False):
            Rp, Rs, Tp, Ts, valid = self.CoatingFun(self.SDT[j].Coating, angle, self.Wave)
            if valid == 1:
                reflectance = min(max(float((Rp + Rs) / 2.0), 0.0), 1.0)
                transmittance = min(max(float((Tp + Ts) / 2.0), 0.0), 1.0)
                total = reflectance + transmittance
                if total > 1.0:
                    reflectance /= total
                    transmittance /= total
                    absorption = 0.0
                else:
                    absorption = max(1.0 - total, 0.0)
                channel_coefficients = {
                    "transmit": (transmittance, transmittance),
                    "reflect": (reflectance, reflectance),
                }
        return reflectance, transmittance, absorption, channel_coefficients


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
        branch_jones_p=complex(1.0, 0.0),
        branch_jones_s=complex(0.0, 0.0),
        branch_polarization_xyz=None,
    ):
        keys = (
            "SURFACE", "NAME", "GLASS", "S_XYZ", "T_XYZ", "XYZ", "OST_XYZ", "OST_LMN",
            "S_LMN", "LMN", "R_LMN", "N0", "N1", "WAV", "G_LMN", "ORDER", "GRATING",
            "DISTANCE", "OP", "TOP_S", "TOP", "ALPHA", "BULK_TRANS", "RP", "RS",
            "TP", "TS", "TTBE", "TT", "INTERACTION_TYPE", "INTERACTION_MODEL",
            "INTERACTION_TARGET_SURFACE", "INTERACTION_IN_POWER", "INTERACTION_COEFF",
            "INTERACTION_OUT_POWER", "INTERACTION_LOSS_POWER", "INTERACTION_BULK",
            "MESH_CELL_ID", "MESH_ORIGINAL_CELL_ID", "MESH_FACE_ID",
            "MESH_FACE_MATCH_METHOD", "MESH_FACE_MATCH_SCORE",
            "RAY", "val", "tt",
        )
        data = {key: copy.deepcopy(getattr(self, key)) for key in keys if hasattr(self, key)}
        data["Wave"] = copy.deepcopy(getattr(self, "Wave", None))
        data["branch_id"] = int(branch_id)
        data["parent_branch_id"] = None if parent_branch_id is None else int(parent_branch_id)
        data["branch_power"] = float(branch_power)
        data["branch_phase_deg"] = float(branch_phase_deg)
        data["branch_label"] = str(branch_label)
        data["branch_path"] = str(branch_path or branch_label or "primary")
        jones_p, jones_s = self.__NormalizeJonesVector(branch_jones_p, branch_jones_s)
        data["branch_jones_p"] = jones_p
        data["branch_jones_s"] = jones_s
        if branch_polarization_xyz is None:
            branch_polarization_xyz = np.asarray((1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j), dtype=np.complex128)
        data["branch_polarization_xyz"] = self.__NormalizePolarizationVector(branch_polarization_xyz)
        return data

    def __RestoreNsTraceSnapshot(self, data):
        for key, value in data.items():
            if key in {
                "branch_id",
                "parent_branch_id",
                "branch_power",
                "branch_phase_deg",
                "branch_jones_p",
                "branch_jones_s",
                "branch_polarization_xyz",
                "branch_label",
                "branch_path",
                "Wave",
            }:
                continue
            setattr(self, key, copy.deepcopy(value))
        if "Wave" in data:
            self.Wave = copy.deepcopy(data["Wave"])
        self._collect_tt_override = None
        self._collect_bulk_override = None
        self._collect_interaction_override = None

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
        surfaces = list(getattr(self, "SDT", []))
        for index, surf in enumerate(surfaces):
            try:
                if index != 0 and index != len(surfaces) - 1:
                    # Object/Image reference planes can be inflated by UI
                    # aperture heuristics. Terminal non-sequential rays should
                    # scale to the physical scene, not those reference planes.
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

    def __AppendNsTerminalSegment(self, RayOrig, ResVec, SIGN=1):
        if len(self.RAY) == 0:
            return None
        direction = np.asarray(ResVec, dtype=float)
        try:
            direction = direction * float(SIGN)
        except Exception:
            direction = direction * np.asarray(SIGN, dtype=float)
        norm = np.linalg.norm(direction)
        if norm <= 1e-12:
            return None
        terminal = np.asarray(RayOrig, dtype=float) + (direction / norm) * self.__NsTerminalLength()
        last = np.asarray(self.RAY[-1], dtype=float)
        if np.linalg.norm(terminal - last) > 1e-9:
            self.RAY.append(terminal)
        return None

    def __NsTraceHitMedia(self, j, jj, PrevN, CurrN, alpha, Glass, hit_point=None, hit_normal=None):
        """Return the refractive media to use for a non-sequential hit."""
        N = PrevN
        Np = CurrN
        face_override = None
        try:
            is_stl_solid = (
                (self.TypeTotal[int(jj)] == 1)
                and (self.SDT[int(j)].Solid_3d_stl != 'None')
            )
        except Exception:
            is_stl_solid = False

        if is_stl_solid:
            mesh_hit = getattr(self.INORM, "last_mesh_hit", None)
            if not isinstance(mesh_hit, dict):
                mesh_hit = {}
            try:
                solid_n = float(self.N_Prec[int(j)])
            except Exception:
                solid_n = float(CurrN)
            try:
                solid_alpha = self.AlphaPrecal[int(j)]
            except Exception:
                solid_alpha = alpha
            try:
                solid_glass = self.GlobGlass[int(j)]
            except Exception:
                solid_glass = self.Glass[int(j)]

            ambient_n = float(getattr(self, "Next", 1.0))
            tolerance = max(1e-7, abs(solid_n) * 1e-7)
            if abs(float(PrevN) - solid_n) <= tolerance:
                # Inside the closed STL: this boundary is an exit candidate.
                N = solid_n
                Np = ambient_n
                CurrN = ambient_n
                alpha = 0.0
            else:
                # Outside the closed STL: this boundary is an entry candidate.
                N = PrevN
                Np = solid_n
                CurrN = solid_n
                alpha = solid_alpha
            Glass = solid_glass
            face_override = self.__OpticalSolidFaceInteraction(j, hit_point, hit_normal, mesh_hit=mesh_hit)
            mesh_hit_override = {
                "cell_id": mesh_hit.get("cell_id", -1),
                "original_cell_id": mesh_hit.get("original_cell_id", -1),
                "face_id": mesh_hit.get("face_id", ""),
                "face_match_method": mesh_hit.get("face_match_method", ""),
                "face_match_score": mesh_hit.get("face_match_score"),
            }
            if isinstance(face_override, dict):
                face_id = str(face_override.get("face_id", "") or "").strip()
                if face_id:
                    mesh_hit_override["face_id"] = face_id
                face_match_method = str(face_override.get("face_match_method", "") or "").strip()
                if face_match_method:
                    mesh_hit_override["face_match_method"] = face_match_method
                if face_override.get("face_match_score") is not None:
                    mesh_hit_override["face_match_score"] = face_override.get("face_match_score")
            self._collect_mesh_hit_override = mesh_hit_override
            return Glass, alpha, CurrN, N, Np, face_override

        if ((self.SDT[j].Solid_3d_stl == 'None') and (self.TypeTotal[jj] == 1)):
            if (N == 1):
                Np = CurrN
            else:
                N = CurrN
                Np = 1
        return Glass, alpha, CurrN, N, Np, face_override

    def __NsTraceShouldUpdatePrevN(self, a, b, face_override):
        if isinstance(face_override, dict):
            if bool(face_override.get("force_reflection")):
                return False
            return True
        return a != b

    def __ApplySnellReflectionInteractionOverride(self, sign, glass, n_in, n_out, surface_index):
        try:
            reflected = float(sign) < 0.0
        except Exception:
            reflected = False
        if not reflected:
            return None
        if str(glass).strip().upper() == "MIRROR":
            return None
        try:
            higher_to_lower = float(n_in) > float(n_out)
        except Exception:
            higher_to_lower = False
        if not higher_to_lower:
            return None
        self._collect_interaction_override = {
            "type": "reflect_tir",
            "model": "snell_total_internal_reflection",
            "target_surface": int(surface_index),
        }
        self._collect_tt_override = 1.0
        self._collect_bulk_override = 1.0
        return None

    def __NsTraceShouldNudgeAfterStlExit(self, surface_index, chooser_surface_index, prev_n, curr_n, sign, face_override):
        if isinstance(face_override, dict) and bool(face_override.get("force_reflection")):
            return False
        try:
            if float(sign) < 0.0:
                return False
        except Exception:
            return False
        try:
            is_stl_solid = (
                self.TypeTotal[int(chooser_surface_index)] == 1
                and self.SDT[int(surface_index)].Solid_3d_stl != 'None'
            )
        except Exception:
            is_stl_solid = False
        if not is_stl_solid:
            return False
        try:
            return float(prev_n) > float(curr_n) + 1e-9
        except Exception:
            return False

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
            "branch_jones_p": None,
            "branch_jones_s": None,
            "branch_polarization_xyz": None,
            "skip_surface_once": None,
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
            branch_jones_p = state.get("branch_jones_p")
            branch_jones_s = state.get("branch_jones_s")
            branch_polarization_xyz = state.get("branch_polarization_xyz")
            skip_surface_once = state.get("skip_surface_once")
            split_spawned = False

            while True:
                if (j == self.Targ_Surf):
                    break
                (a, b, c, PreSurfHit) = self.__NonSequentialChooser(SIGN, RayOrig, ResVec, j, skip_surface_once)
                skip_surface_once = None

                if (PreSurfHit == 0):
                    self.__AppendNsTerminalSegment(RayOrig, ResVec, SIGN)
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
                        self.__AppendNsTerminalSegment(RayOrig, ResVec, SIGN)
                        break
                    ImpVec = np.asarray(ResVec)
                    (CurrN, alpha) = (self.N_Prec[j_gg], self.AlphaPrecal[j_gg])

                    if CurrN == 1.0:
                        CurrN = self.Next

                    R = np.asarray(SurfNorm)
                    N = PrevN
                    Np = CurrN
                    Glass, alpha, CurrN, N, Np, face_override = self.__NsTraceHitMedia(
                        j,
                        jj,
                        PrevN,
                        CurrN,
                        alpha,
                        Glass,
                        pTarget,
                        SurfNorm,
                    )
                    D = GooveVect

                    Ord = self.SDT[j].Diff_Ord
                    GrSpa = self.SDT[j].Grating_D
                    if isinstance(face_override, dict) and bool(face_override.get("force_reflection")):
                        try:
                            R = np.asarray(face_override.get("normal_world"), dtype=float).reshape(3)
                        except Exception:
                            pass
                    ResVec_N, R_N, N_N, Np_N = ResVec, R, N, Np
                    secuent = 1 if isinstance(face_override, dict) and bool(face_override.get("force_reflection")) else 0
                    (trans_vec, trans_n, trans_sign, trans_ang) = self.SDT[j].PHYSICS.calculate(
                        ResVec_N, R_N, N_N, Np_N, D, Ord, GrSpa, self.Wave, secuent
                    )
                    self.ang = trans_ang
                    if isinstance(face_override, dict) and bool(face_override.get("force_reflection")):
                        face_label = str(face_override.get("face_id", "") or face_override.get("side_2d", "") or "face")
                        face_function = str(face_override.get("function", "Mirror") or "Mirror").strip().lower().replace(" ", "_")
                        self._collect_interaction_override = {
                            "type": "reflect",
                            "model": f"optical_solid_face_{face_function}:{face_label}",
                            "target_surface": int(j),
                        }
                        self._collect_tt_override = max(0.0, 1.0 - float(face_override.get("loss", 0.0) or 0.0))
                        self._collect_bulk_override = 1.0
                    else:
                        self.__ApplySnellReflectionInteractionOverride(trans_sign, Glass, N, Np, j)
                    diffuse_settings = self.__DiffuseScatterSettings(j)
                    can_scatter = (
                        diffuse_settings is not None
                        and diffuse_settings["reflectance"] > 0.0
                        and branch_depth < int(diffuse_settings["max_branch_depth"])
                    )
                    splitter_settings = self.__BeamSplitterSettings(j)
                    can_split = (
                        splitter_settings is not None
                        and splitter_settings["deterministic"]
                        and branch_depth < int(splitter_settings["max_branch_depth"])
                    )

                    if can_scatter:
                        scatter_samples = [
                            (child_vec, child_coeff)
                            for child_vec, child_coeff in self.__LambertianScatterSamples(
                                ImpVec,
                                R,
                                pTarget,
                                diffuse_settings,
                            )
                            if branch_power * float(child_coeff) >= float(diffuse_settings["min_branch_power"])
                        ]
                        if scatter_samples:
                            if branch_polarization_xyz is not None:
                                incident_polarization = self.__NormalizePolarizationVector(branch_polarization_xyz, ImpVec)
                                incident_jones = self.__PolarizationVectorToJones(incident_polarization, ImpVec, R)
                            else:
                                incident_jones = (
                                    branch_jones_p if branch_jones_p is not None else complex(1.0, 0.0),
                                    branch_jones_s if branch_jones_s is not None else complex(0.0, 0.0),
                                )
                                incident_polarization = self.__JonesToPolarizationVector(incident_jones, ImpVec, R)
                            pre_hit_trace = self.__NsTraceSnapshot(
                                branch_id,
                                state["parent_branch_id"],
                                branch_power,
                                branch_phase,
                                branch_label,
                                branch_path,
                                incident_jones[0],
                                incident_jones[1],
                                incident_polarization,
                            )
                            for child_index, (child_vec, child_coeff) in enumerate(scatter_samples, start=1):
                                self.__RestoreNsTraceSnapshot(pre_hit_trace)
                                self._collect_tt_override = float(child_coeff)
                                self._collect_bulk_override = 1.0
                                self._collect_interaction_override = {
                                    "type": "scatter",
                                    "model": self.__DiffuseInteractionModelLabel(diffuse_settings),
                                    "target_surface": diffuse_settings.get("target_surface", -1),
                                }
                                self.ang = 0.0
                                child_vec = self.__NormalizeVector(child_vec, fallback=R)
                                child_polarization = self.__TransportPolarizationVector(incident_polarization, child_vec)
                                child_jones_p, child_jones_s = self.__PolarizationVectorToJones(child_polarization, child_vec, R)
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
                                    PrevN,
                                    WaveLength,
                                    D,
                                    Ord,
                                    GrSpa,
                                    Name,
                                    j,
                                    RayTraceType,
                                ]
                                self.__CollectData(ValToSav)
                                child_ray_orig = np.asarray(pTarget, dtype=float)
                                child_trace_orig = self.__NudgeNsBranchOrigin(child_ray_orig, child_vec)
                                self.RAY.append(child_ray_orig)
                                child_branch_id = next_branch_id
                                next_branch_id += 1
                                child_label = f"scatter{child_index:02d}"
                                child_branch_path = self.__NsTraceAppendBranchPath(branch_path, j, child_label)
                                child_power_total = float(self.TT)
                                queue.append(
                                    {
                                        "trace": self.__NsTraceSnapshot(
                                            child_branch_id,
                                            branch_id,
                                            child_power_total,
                                            branch_phase,
                                            child_label,
                                            child_branch_path,
                                            child_jones_p,
                                            child_jones_s,
                                            child_polarization,
                                        ),
                                        "RayOrig": child_trace_orig,
                                        "ResVec": np.asarray(child_vec, dtype=float),
                                        "PrevN": PrevN,
                                        "j": int(j),
                                        "SIGN": SIGN,
                                        "count": count + 1,
                                        "branch_id": child_branch_id,
                                        "parent_branch_id": branch_id,
                                        "branch_power": child_power_total,
                                        "branch_phase_deg": branch_phase,
                                        "branch_depth": branch_depth + 1,
                                        "branch_label": child_label,
                                        "branch_path": child_branch_path,
                                        "branch_jones_p": child_jones_p,
                                        "branch_jones_s": child_jones_s,
                                        "branch_polarization_xyz": child_polarization,
                                        "skip_surface_once": int(j),
                                    }
                                )
                                if len(queue) + len(results) >= branch_result_limit:
                                    break
                        split_spawned = True
                        break

                    if can_split:
                        ideal_air_splitter = False
                        if str(getattr(self.SDT[j], "Glass", self.Glass[j])).strip().upper() == "AIR":
                            # Ideal AIR/AIR splitters are zero-thickness power
                            # dividers. Their transmitted branch should keep
                            # the incident direction from either side of the
                            # plate; Snell's sign bookkeeping can otherwise
                            # flip the back-side branch in non-sequential use.
                            physical_incident = np.asarray(pTarget, dtype=float) - np.asarray(RayOrig, dtype=float)
                            incident_norm = np.linalg.norm(physical_incident)
                            if incident_norm > 1e-12:
                                ideal_air_splitter = True
                                physical_incident = physical_incident / incident_norm
                                trans_vec = physical_incident
                                trans_n = PrevN
                                trans_sign = 1.0 / float(SIGN) if abs(float(SIGN)) > 1e-12 else 1.0
                        refl_vec = self.__ReflectVector(physical_incident if ideal_air_splitter else ImpVec, SurfNorm)
                        refl_n = PrevN
                        refl_sign = trans_sign if ideal_air_splitter else 1.0
                        refl_ang = trans_ang
                        incident_direction = physical_incident if ideal_air_splitter else ImpVec
                        incident_polarization = self.__BeamSplitterStatePolarization(
                            state,
                            splitter_settings,
                            incident_direction,
                            R,
                        )
                        incident_jones = self.__PolarizationVectorToJones(incident_polarization, incident_direction, R)
                        reflectance, transmittance, _absorption, channel_coefficients = self.__BeamSplitterCoefficients(
                            j,
                            splitter_settings,
                            trans_ang,
                            prev_n=N,
                            curr_n=Np,
                            imp_vec=ImpVec,
                            surf_norm=R,
                            trans_vec=trans_vec,
                            input_jones=incident_jones,
                        )
                        children = (
                            (
                                "transmit",
                                trans_vec,
                                trans_n,
                                trans_sign,
                                trans_ang,
                                transmittance,
                                float(splitter_settings["transmit_phase_deg"]),
                            ),
                            (
                                "reflect",
                                refl_vec,
                                PrevN,
                                refl_sign,
                                refl_ang,
                                reflectance,
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
                            incident_jones[0],
                            incident_jones[1],
                            incident_polarization,
                        )
                        for child_label, child_vec, child_n, child_sign, child_ang, child_coeff, child_phase in children:
                            if child_coeff <= 0.0:
                                continue
                            if branch_power * child_coeff < float(splitter_settings["min_branch_power"]):
                                continue
                            child_jones_p, child_jones_s = self.__BeamSplitterChildJones(
                                incident_jones,
                                child_label,
                                channel_coefficients,
                                splitter_settings,
                            )
                            child_polarization = self.__JonesToPolarizationVector(
                                (child_jones_p, child_jones_s),
                                child_vec,
                                R,
                            )
                            self.__RestoreNsTraceSnapshot(pre_hit_trace)
                            self._collect_tt_override = child_coeff
                            self._collect_interaction_override = {
                                "type": f"split_{child_label}",
                                "model": str(splitter_settings.get("split_mode", "")),
                                "target_surface": -1,
                            }
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
                            child_prev_n = (
                                PrevN
                                if child_label == "reflect" or not self.__NsTraceShouldUpdatePrevN(a, b, face_override)
                                else child_n
                            )
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
                                    child_jones_p,
                                    child_jones_s,
                                    child_polarization,
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
                                "branch_jones_p": child_jones_p,
                                "branch_jones_s": child_jones_s,
                                "branch_polarization_xyz": child_polarization,
                                "skip_surface_once": int(j),
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
                    if branch_polarization_xyz is not None:
                        branch_polarization_xyz = self.__TransportPolarizationVector(branch_polarization_xyz, ResVec)
                        branch_jones_p, branch_jones_s = self.__PolarizationVectorToJones(branch_polarization_xyz, ResVec, R)
                    if self.__NsTraceShouldUpdatePrevN(a, b, face_override):
                        PrevN = CurrN
                    stl_exit_continuation = self.__NsTraceShouldNudgeAfterStlExit(j, jj, N, CurrN, sign, face_override)
                    if (
                        isinstance(face_override, dict)
                        and bool(face_override.get("external_reflection"))
                    ) or stl_exit_continuation:
                        skip_surface_once = int(j)
                        RayOrig = self.__NudgeNsBranchOrigin(pTarget, ResVec)
                        self.RAY.append(np.asarray(pTarget, dtype=float))
                    else:
                        RayOrig = pTarget
                        self.RAY.append(RayOrig)

                    if (
                        not (isinstance(face_override, dict) and bool(face_override.get("force_reflection")))
                        and not stl_exit_continuation
                        and (a==b) and (b==c) and (c == PreSurfHit)
                    ):
                        break

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
            if branch_polarization_xyz is None:
                terminal_polarization = self.__JonesToPolarizationVector(
                    (
                        branch_jones_p if branch_jones_p is not None else complex(1.0, 0.0),
                        branch_jones_s if branch_jones_s is not None else complex(0.0, 0.0),
                    ),
                    ResVec,
                )
            else:
                terminal_polarization = self.__TransportPolarizationVector(branch_polarization_xyz, ResVec)
            results.append(
                self.__NsTraceSnapshot(
                    branch_id,
                    state["parent_branch_id"],
                    float(self.TT),
                    branch_phase,
                    branch_label,
                    branch_path,
                    branch_jones_p if branch_jones_p is not None else complex(1.0, 0.0),
                    branch_jones_s if branch_jones_s is not None else complex(0.0, 0.0),
                    terminal_polarization,
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
        if self.__NsTraceRequiresBranching():
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
        skip_surface_once = None

        while True:
            if (j == self.Targ_Surf):
                break
            (a, b, c, PreSurfHit) = self.__NonSequentialChooser(SIGN, RayOrig, ResVec, j, skip_surface_once)
            skip_surface_once = None

            if (PreSurfHit == 0):
                self.__AppendNsTerminalSegment(RayOrig, ResVec, SIGN)
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
                    self.__AppendNsTerminalSegment(RayOrig, ResVec, SIGN)
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
                Glass, alpha, CurrN, N, Np, face_override = self.__NsTraceHitMedia(
                    j,
                    jj,
                    PrevN,
                    CurrN,
                    alpha,
                    Glass,
                    pTarget,
                    SurfNorm,
                )
                D = GooveVect

                Ord = self.SDT[j].Diff_Ord
                GrSpa = self.SDT[j].Grating_D
                if isinstance(face_override, dict) and bool(face_override.get("force_reflection")):
                    try:
                        R = np.asarray(face_override.get("normal_world"), dtype=float).reshape(3)
                    except Exception:
                        pass
                Secuent = 1 if isinstance(face_override, dict) and bool(face_override.get("force_reflection")) else 0
                ResVec_N, R_N, N_N, Np_N = ResVec, R, N, Np
                (ResVec, CurrN, sign ,ang) = self.SDT[j].PHYSICS.calculate(ResVec_N, R_N, N_N, Np_N, D, Ord, GrSpa, self.Wave, Secuent)
                self.ang = ang
                if isinstance(face_override, dict) and bool(face_override.get("force_reflection")):
                    face_label = str(face_override.get("face_id", "") or face_override.get("side_2d", "") or "face")
                    face_function = str(face_override.get("function", "Mirror") or "Mirror").strip().lower().replace(" ", "_")
                    self._collect_interaction_override = {
                        "type": "reflect",
                        "model": f"optical_solid_face_{face_function}:{face_label}",
                        "target_surface": int(j),
                    }
                    self._collect_tt_override = max(0.0, 1.0 - float(face_override.get("loss", 0.0) or 0.0))
                    self._collect_bulk_override = 1.0
                else:
                    self.__ApplySnellReflectionInteractionOverride(sign, Glass, N, Np, j)

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
                if self.__NsTraceShouldUpdatePrevN(a, b, face_override):
                    PrevN = CurrN
                stl_exit_continuation = self.__NsTraceShouldNudgeAfterStlExit(j, jj, N, CurrN, sign, face_override)
                if (
                    isinstance(face_override, dict)
                    and bool(face_override.get("external_reflection"))
                ) or stl_exit_continuation:
                    skip_surface_once = int(j)
                    RayOrig = self.__NudgeNsBranchOrigin(pTarget, ResVec)
                    self.RAY.append(np.asarray(pTarget, dtype=float))
                else:
                    RayOrig = pTarget
                    self.RAY.append(RayOrig)

                if (
                    not (isinstance(face_override, dict) and bool(face_override.get("force_reflection")))
                    and not stl_exit_continuation
                    and (a==b) and (b==c) and (c == PreSurfHit)
                ):
                    break

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
