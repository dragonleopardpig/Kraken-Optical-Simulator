import numpy as np
import os
import sys
import random
import inspect
from dataclasses import dataclass
from .SurfTools import surface_tools as SUT
from .Prerequisites3D import *
from .Physics import *
from .HitOnSurf import *
from .InterNormalCalc import *
from .MeshRayTrace import (
    assign_mesh_cell_face_ids,
    decimate_optical_solid_trace_mesh,
    trace_mesh_ray,
)
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



@dataclass(frozen=True)
class NonSequentialIntersectionPolicy:
    """Scene-scaled tolerances for non-sequential self-intersection rejection."""

    near_hit_tolerance: float
    same_surface_tolerance: float

    @staticmethod
    def _surface_scale(surfaces):
        scales = []
        for surf in list(surfaces or []):
            for attr_name in ("Diameter", "InDiameter", "Thickness"):
                try:
                    value = abs(float(getattr(surf, attr_name, 0.0) or 0.0))
                except Exception:
                    value = 0.0
                if np.isfinite(value) and value > 0.0:
                    scales.append(value)
        return max(scales) if scales else 1.0

    @classmethod
    def from_surfaces(cls, surfaces):
        scale = cls._surface_scale(surfaces)
        return cls(
            near_hit_tolerance=max(1.0e-6, float(scale) * 1.0e-6),
            same_surface_tolerance=max(1.0e-6, float(scale) * 1.0e-5),
        )

    def rejection_tolerance(self, mesh_surface_index, current_surface_index=None):
        try:
            mesh_index = int(mesh_surface_index)
        except Exception:
            mesh_index = -1
        try:
            current_index = int(current_surface_index)
        except Exception:
            current_index = -1
        if current_index >= 0 and mesh_index == current_index:
            return max(self.near_hit_tolerance, self.same_surface_tolerance)
        return self.near_hit_tolerance


@dataclass(frozen=True)
class NonSequentialRayState:
    """Media-region state carried by a non-sequential ray branch."""

    current_medium: str = "AIR"
    current_index: float = 1.0
    inside_volumes: tuple[str, ...] = ()
    method: str = "initial"

    def to_record(self):
        return {
            "current_medium": str(self.current_medium),
            "current_index": float(self.current_index),
            "inside_volumes": [str(volume_id) for volume_id in self.inside_volumes],
            "method": str(self.method),
        }


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
        self._ns_trace_timing_active = False
        self._ns_trace_timing = {}
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
        self._optical_solid_face_world_signature_cache = {}
        self._optical_solid_mesh_face_id_cache = {}
        self._ns_requires_branching_cache = None
        if not hasattr(self, "_scene_boundary_faces_by_surface"):
            self._scene_boundary_faces_by_surface = {}
        if not hasattr(self, "_scene_optical_volumes_by_surface"):
            self._scene_optical_volumes_by_surface = {}

    def EnableNsTraceTiming(self, enabled=True):
        """Enable lightweight non-sequential loop timing until snapshot/reset."""
        self._ns_trace_timing_active = bool(enabled)
        self._ns_trace_timing = {}

    def NsTraceTimingStart(self):
        if not bool(getattr(self, "_ns_trace_timing_active", False)):
            return None
        return timeit.default_timer()

    def NsTraceTimingRecord(self, section, started):
        if started is None or not bool(getattr(self, "_ns_trace_timing_active", False)):
            return None
        try:
            duration_ms = (timeit.default_timer() - float(started)) * 1000.0
        except Exception:
            return None
        key = str(section or "unknown")
        timings = getattr(self, "_ns_trace_timing", None)
        if not isinstance(timings, dict):
            timings = {}
            self._ns_trace_timing = timings
        row = timings.setdefault(
            key,
            {
                "call_count": 0,
                "total_ms": 0.0,
                "max_ms": 0.0,
            },
        )
        row["call_count"] = int(row.get("call_count", 0) or 0) + 1
        row["total_ms"] = float(row.get("total_ms", 0.0) or 0.0) + float(duration_ms)
        row["max_ms"] = max(float(row.get("max_ms", 0.0) or 0.0), float(duration_ms))
        return None

    def NsTraceTimingSnapshot(self, reset=False, top_n=16):
        timings = getattr(self, "_ns_trace_timing", {})
        sections = []
        if isinstance(timings, dict):
            rows = sorted(
                timings.items(),
                key=lambda item: float(item[1].get("total_ms", 0.0)) if isinstance(item[1], dict) else 0.0,
                reverse=True,
            )
            for section, row in rows[: max(0, int(top_n))]:
                if not isinstance(row, dict):
                    continue
                sections.append(
                    {
                        "section": str(section),
                        "call_count": int(row.get("call_count", 0) or 0),
                        "total_ms": round(float(row.get("total_ms", 0.0) or 0.0), 3),
                        "max_ms": round(float(row.get("max_ms", 0.0) or 0.0), 3),
                    }
                )
        outer_total = 0.0
        for row in sections:
            if row.get("section") in {"system.NsTrace", "raykeeper.push"}:
                outer_total += float(row.get("total_ms", 0.0) or 0.0)
        if outer_total <= 0.0:
            outer_total = sum(float(row.get("total_ms", 0.0) or 0.0) for row in sections)
        summary = {
            "ns_loop_section_count": len(sections),
            "ns_loop_total_ms": round(float(outer_total), 3),
            "ns_loop_sections": sections,
        }
        if reset:
            self.EnableNsTraceTiming(False)
        return summary


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
        if not hasattr(self, "_optical_solid_face_world_cache"):
            self._optical_solid_face_world_cache = {}
        cached = self._optical_solid_face_world_cache.get(cache_key)
        if cached is not None:
            return cached
        records = self.__SceneBoundaryFaceRecords(cache_key)
        if records:
            metadata = {"faces": records}
        else:
            try:
                metadata = normalize_optical_solid_face_metadata(getattr(self.SDT[cache_key], "OpticalSolidFaces", {}))
            except Exception:
                metadata = {"faces": []}
        world_faces = []
        for face in list(metadata.get("faces", []) or []):
            if not isinstance(face, dict):
                continue
            centroid_local = np.asarray(
                point3_tuple(face.get("centroid_local", face.get("centroid", (0.0, 0.0, 0.0)))),
                dtype=float,
            )
            normal_local = np.asarray(
                unit_vector_tuple(face.get("normal_local", face.get("normal", (0.0, 0.0, 1.0)))),
                dtype=float,
            )
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

    def __OpticalSolidWorldFaceSignature(self, surface_index, world_faces):
        cache_key = int(surface_index)
        if not hasattr(self, "_optical_solid_face_world_signature_cache"):
            self._optical_solid_face_world_signature_cache = {}
        cached = self._optical_solid_face_world_signature_cache.get(cache_key)
        if cached is not None:
            return cached
        signature = []
        for face in list(world_faces or []):
            if not isinstance(face, dict):
                continue
            try:
                centroid = tuple(
                    round(float(value), 9)
                    for value in np.asarray(
                        face.get("centroid_world", face.get("centroid", ())),
                        dtype=float,
                    ).reshape(-1)[:3]
                )
            except Exception:
                centroid = ()
            try:
                normal = tuple(
                    round(float(value), 9)
                    for value in np.asarray(
                        face.get("normal_world", face.get("normal", ())),
                        dtype=float,
                    ).reshape(-1)[:3]
                )
            except Exception:
                normal = ()
            try:
                raw_triangles = face.get("triangle_indices", face.get("cell_indices", []))
                if raw_triangles is None:
                    raw_values = []
                elif isinstance(raw_triangles, np.ndarray):
                    raw_values = raw_triangles.reshape(-1).tolist()
                elif isinstance(raw_triangles, (list, tuple, set)):
                    raw_values = list(raw_triangles)
                else:
                    raw_values = [raw_triangles]
                triangle_indices = tuple(sorted(int(value) for value in raw_values))
            except Exception:
                triangle_indices = ()
            signature.append(
                (
                    str(face.get("face_id", "") or "").strip(),
                    str(face.get("function", "") or "").strip(),
                    str(face.get("role", "") or "").strip(),
                    centroid,
                    normal,
                    triangle_indices,
                )
            )
        value = tuple(signature)
        self._optical_solid_face_world_signature_cache[cache_key] = value
        return value

    def __SceneBoundaryFaceRecords(self, surface_index):
        index = getattr(self, "_scene_boundary_faces_by_surface", {})
        if not isinstance(index, dict):
            return []
        records = index.get(int(surface_index))
        if records is None:
            records = index.get(str(int(surface_index)))
        if not isinstance(records, (list, tuple)):
            return []
        output = []
        for record in records:
            if isinstance(record, dict):
                output.append(dict(record))
        return output

    def __SceneOpticalVolumeRecord(self, surface_index):
        index = getattr(self, "_scene_optical_volumes_by_surface", {})
        if not isinstance(index, dict):
            return {}
        record = index.get(int(surface_index))
        if record is None:
            record = index.get(str(int(surface_index)))
        return dict(record) if isinstance(record, dict) else {}

    def __InitialNsRayState(self, prev_n):
        try:
            current_index = float(prev_n)
        except Exception:
            current_index = 1.0
        medium = "AIR"
        try:
            candidate = str(self.GlobGlass[0] or "").strip()
            if candidate and candidate.upper() not in {"NULL", "NONE"}:
                medium = candidate
        except Exception:
            pass
        return NonSequentialRayState(
            current_medium=medium,
            current_index=current_index,
            inside_volumes=(),
            method="initial",
        )

    def __NsRayStateFromRecord(self, value, fallback_prev_n=None):
        if isinstance(value, NonSequentialRayState):
            return value
        if not isinstance(value, dict):
            return self.__InitialNsRayState(1.0 if fallback_prev_n is None else fallback_prev_n)
        inside_raw = value.get("inside_volumes", ())
        if isinstance(inside_raw, str):
            inside = tuple(item for item in inside_raw.split("|") if item)
        else:
            inside = tuple(str(item) for item in list(inside_raw or ()) if str(item))
        try:
            current_index = float(value.get("current_index", fallback_prev_n))
        except Exception:
            try:
                current_index = 1.0 if fallback_prev_n is None else float(fallback_prev_n)
            except Exception:
                current_index = 1.0
        return NonSequentialRayState(
            current_medium=str(value.get("current_medium", "AIR") or "AIR"),
            current_index=current_index,
            inside_volumes=inside,
            method=str(value.get("method", "restored") or "restored"),
        )

    def __NsRayStateRecord(self, state):
        return self.__NsRayStateFromRecord(state).to_record()

    def __NsRayStateBranchFields(self, state, fallback_prev_n=None):
        state = self.__NsRayStateFromRecord(state, fallback_prev_n)
        return {
            "branch_final_media": str(state.current_medium),
            "branch_final_index": float(state.current_index),
            "branch_final_inside_volumes": self.__NsRayStateInsideText(state),
            "branch_final_media_state_method": str(state.method),
        }

    def __SetNsFinalRayState(self, state, fallback_prev_n=None):
        fields = self.__NsRayStateBranchFields(state, fallback_prev_n)
        self.BRANCH_FINAL_MEDIA = fields["branch_final_media"]
        self.BRANCH_FINAL_INDEX = fields["branch_final_index"]
        self.BRANCH_FINAL_INSIDE_VOLUMES = fields["branch_final_inside_volumes"]
        self.BRANCH_FINAL_MEDIA_STATE_METHOD = fields["branch_final_media_state_method"]
        return fields

    def __NsRayStateInsideText(self, state):
        state = self.__NsRayStateFromRecord(state)
        return "|".join(str(volume_id) for volume_id in state.inside_volumes)

    def __NsRayStateWith(self, state, *, current_medium=None, current_index=None, inside_volumes=None, method=None):
        state = self.__NsRayStateFromRecord(state)
        try:
            next_index = float(state.current_index if current_index is None else current_index)
        except Exception:
            next_index = state.current_index
        return NonSequentialRayState(
            current_medium=str(state.current_medium if current_medium is None else current_medium),
            current_index=next_index,
            inside_volumes=tuple(state.inside_volumes if inside_volumes is None else inside_volumes),
            method=str(state.method if method is None else method),
        )

    def __NsRayStateIncidentIndexDiagnostic(self, ray_state, scalar_prev_n):
        state = self.__NsRayStateFromRecord(ray_state, scalar_prev_n)
        try:
            state_index = float(state.current_index)
            scalar_index = float(scalar_prev_n)
        except Exception:
            return ""
        if abs(state_index - scalar_index) <= max(1e-9, abs(state_index) * 1e-9):
            return ""
        return (
            "incident_index_from_ray_state:"
            f"scalar_prev_n={scalar_index:.12g},state_current_index={state_index:.12g}"
        )

    def __NsMediumName(self, value, fallback="AIR"):
        text = str(value if value is not None else "").strip()
        if not text or text.upper() in {"NULL", "NONE"}:
            return str(fallback)
        return text

    def __NsRayStateAfterHit(self, ray_state, face_override, curr_n, sign, media_out=None):
        state = self.__NsRayStateFromRecord(ray_state, curr_n)
        reflected = False
        try:
            reflected = float(sign) < 0.0
        except Exception:
            pass
        if not isinstance(face_override, dict):
            if reflected:
                return self.__NsRayStateWith(state, method="ray_state_reflection")
            medium = self.__NsMediumName(media_out, fallback=state.current_medium)
            if medium.upper() == "MIRROR":
                medium = state.current_medium
            try:
                curr_index = float(curr_n)
            except Exception:
                curr_index = state.current_index
            changed = medium != state.current_medium or abs(curr_index - float(state.current_index)) > 1e-9
            return self.__NsRayStateWith(
                state,
                current_medium=medium,
                current_index=curr_index,
                method="ray_state_surface_medium" if changed else "ray_state_transmit",
            )
        volume_id = str(face_override.get("volume_id", "") or "").strip()
        if not volume_id:
            if reflected:
                return self.__NsRayStateWith(state, method="ray_state_reflection")
            medium = self.__NsMediumName(media_out, fallback=state.current_medium)
            if medium.upper() == "MIRROR":
                medium = state.current_medium
            try:
                curr_index = float(curr_n)
            except Exception:
                curr_index = state.current_index
            changed = medium != state.current_medium or abs(curr_index - float(state.current_index)) > 1e-9
            return self.__NsRayStateWith(
                state,
                current_medium=medium,
                current_index=curr_index,
                method="ray_state_surface_medium" if changed else "ray_state_transmit",
            )
        reflected = reflected or bool(face_override.get("force_reflection"))
        if reflected:
            return self.__NsRayStateWith(state, method="ray_state_reflection")
        transition = str(face_override.get("media_transition", "") or "").strip()
        inside = [str(item) for item in state.inside_volumes]
        if transition == "entry":
            if volume_id not in inside:
                inside.append(volume_id)
            medium = str(face_override.get("volume_material", "") or face_override.get("material", "") or state.current_medium)
            return self.__NsRayStateWith(
                state,
                current_medium=medium,
                current_index=curr_n,
                inside_volumes=inside,
                method="ray_state_inside_volumes",
            )
        if transition == "exit":
            inside = [item for item in inside if item != volume_id]
            medium = str(face_override.get("ambient_material", "") or "AIR")
            return self.__NsRayStateWith(
                state,
                current_medium=medium,
                current_index=curr_n,
                inside_volumes=inside,
                method="ray_state_inside_volumes",
            )
        try:
            return self.__NsRayStateWith(state, current_index=float(curr_n), method="scalar_index")
        except Exception:
            return state

    def __NsRayStateAfterTerminal(self, ray_state, terminal_event):
        state = self.__NsRayStateFromRecord(ray_state)
        method = str((terminal_event or {}).get("method", "") or "ray_state_terminal")
        return self.__NsRayStateWith(state, method=method)

    def __NsTerminalMediaOverride(self, face_override, terminal_event):
        override = dict(face_override or {}) if isinstance(face_override, dict) else {}
        override["media_transition"] = str((terminal_event or {}).get("transition", "") or "terminal")
        override["media_state_method"] = str((terminal_event or {}).get("method", "") or "ray_state_terminal")
        return override

    def __NsRayMediaEvent(
        self,
        ray_state,
        face_override,
        curr_n,
        sign,
        *,
        media_out=None,
        terminal_event=None,
        method=None,
        diagnostic=None,
    ):
        if terminal_event:
            after_state = self.__NsRayStateAfterTerminal(ray_state, terminal_event)
            event_override = self.__NsTerminalMediaOverride(face_override, terminal_event)
        else:
            after_state = self.__NsRayStateAfterHit(
                ray_state,
                face_override,
                curr_n,
                sign,
                media_out=media_out,
            )
            event_override = face_override
        if method:
            after_state = self.__NsRayStateWith(after_state, method=method)
        event_record = self.__NsRayStateEventRecord(
            ray_state,
            after_state,
            event_override,
            sign,
            extra_diagnostic=diagnostic,
        )
        return after_state, event_record

    def __NsSurfaceElementMetadata(self, surface_index):
        try:
            value = getattr(self.SDT[int(surface_index)], "Element", {})
        except Exception:
            value = {}
        return dict(value) if isinstance(value, dict) else {}

    def __NsSurfaceHasDetectorMetadata(self, surface_index):
        try:
            detector = getattr(self.SDT[int(surface_index)], "Detector", None)
        except Exception:
            detector = None
        if isinstance(detector, dict):
            if detector:
                return True
        elif detector not in (None, "", False):
            return True
        element = self.__NsSurfaceElementMetadata(surface_index)
        role = str(element.get("arm_role", "") or "").strip().lower()
        return role == "detector"

    def __NsTraceTerminalEvent(self, surface_index, face_override=None):
        try:
            j = int(surface_index)
        except Exception:
            return {}
        face = dict(face_override or {}) if isinstance(face_override, dict) else {}
        function = normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
        if bool(face.get("force_absorption")) or function == "Absorber/Mechanical":
            face_label = str(face.get("face_id", "") or face.get("side_2d", "") or "face")
            return {
                "kind": "absorb",
                "transition": "absorb",
                "method": "ray_state_absorb_terminal",
                "interaction_type": "absorb",
                "model": f"optical_solid_face_absorber:{face_label}",
                "target_surface": j,
                "tt": 0.0,
                "bulk": 1.0,
                "stop": True,
            }
        try:
            glass_text = str(self.Glass[j]).strip().upper()
        except Exception:
            glass_text = ""
        if glass_text == "ABSORB":
            return {
                "kind": "absorb",
                "transition": "absorb",
                "method": "ray_state_absorb_terminal",
                "interaction_type": "absorb",
                "model": "absorber_surface",
                "target_surface": j,
                "tt": 0.0,
                "bulk": 1.0,
                "stop": True,
            }
        if self.__NsSurfaceHasDetectorMetadata(j):
            return {
                "kind": "detector",
                "transition": "detector_termination",
                "method": "ray_state_detector_terminal",
                "interaction_type": "detector",
                "model": "detector_surface",
                "target_surface": j,
                "tt": 1.0,
                "bulk": 1.0,
                "stop": True,
            }
        try:
            is_target = j == int(self.Targ_Surf)
        except Exception:
            is_target = False
        try:
            is_target = is_target or j == int(self.n) - 1
        except Exception:
            pass
        if is_target:
            return {
                "kind": "target",
                "transition": "target_termination",
                "method": "ray_state_target_terminal",
                "interaction_type": "target",
                "model": "target_surface",
                "target_surface": j,
                "stop": True,
            }
        return {}

    def __ApplyNsTerminalEventOverride(self, terminal_event):
        if not terminal_event:
            return None
        self._collect_interaction_override = {
            "type": str(terminal_event.get("interaction_type", "") or "terminal"),
            "model": str(terminal_event.get("model", "") or "terminal_surface"),
            "target_surface": int(terminal_event.get("target_surface", -1)),
        }
        if terminal_event.get("tt") is not None:
            self._collect_tt_override = float(terminal_event.get("tt"))
        if terminal_event.get("bulk") is not None:
            self._collect_bulk_override = float(terminal_event.get("bulk"))
        return None

    def __NsRayStateEventRecord(self, before_state, after_state, face_override=None, sign=1.0, extra_diagnostic=None):
        before = self.__NsRayStateFromRecord(before_state)
        after = self.__NsRayStateFromRecord(after_state)
        override = dict(face_override or {}) if isinstance(face_override, dict) else {}
        transition = str(override.get("media_transition", "") or "").strip()
        reflected = bool(override.get("force_reflection"))
        try:
            reflected = reflected or float(sign) < 0.0
        except Exception:
            pass
        if reflected and transition in {"entry", "exit"}:
            transition = "reflection"
        if not transition:
            if reflected:
                transition = "reflection"
            elif before.current_medium != after.current_medium or abs(float(before.current_index) - float(after.current_index)) > 1e-9:
                transition = "medium_change"
            else:
                transition = "transmit"
        volume_id = str(override.get("volume_id", "") or "")
        diagnostic = str(override.get("media_state_diagnostic", "") or "").strip()
        if not diagnostic and volume_id and transition == "entry" and volume_id in before.inside_volumes:
            diagnostic = f"volume_entry_already_inside:{volume_id}"
        if not diagnostic and volume_id and transition == "exit" and volume_id not in before.inside_volumes:
            diagnostic = f"volume_exit_without_entry:{volume_id}"
        if not diagnostic and volume_id and transition == "exit" and volume_id in after.inside_volumes:
            diagnostic = f"volume_exit_still_inside:{volume_id}"
        extra_diagnostic_text = str(extra_diagnostic or "").strip()
        if extra_diagnostic_text:
            diagnostic = "; ".join(value for value in (diagnostic, extra_diagnostic_text) if str(value or "").strip())
        return {
            "volume_id": volume_id,
            "media_in": str(before.current_medium),
            "media_out": str(after.current_medium),
            "transition": transition,
            "method": str(override.get("media_state_method", "") or after.method or before.method),
            "inside_before": self.__NsRayStateInsideText(before),
            "inside_after": self.__NsRayStateInsideText(after),
            "diagnostic": diagnostic,
        }

    def __OpticalSolidHasInputPort(self, world_faces, surface_index):
        try:
            if optical_solid_face_by_port_role({"faces": list(world_faces or [])}, OPTICAL_SOLID_FACE_PORT_INPUT) is not None:
                return True
        except Exception:
            pass
        try:
            metadata = normalize_optical_solid_face_metadata(getattr(self.SDT[int(surface_index)], "OpticalSolidFaces", {}))
            return optical_solid_face_by_port_role(metadata, OPTICAL_SOLID_FACE_PORT_INPUT) is not None
        except Exception:
            return True

    def __OpticalSolidFaceById(self, world_faces, face_id):
        target = str(face_id or "").strip()
        if not target:
            return None
        for face in list(world_faces or []):
            if isinstance(face, dict) and str(face.get("face_id", "") or "").strip() == target:
                return face
        return None

    def __OpticalSolidScenePoints(self, surface_index):
        points: list[np.ndarray] = []
        try:
            target_surface = int(surface_index)
        except Exception:
            return np.empty((0, 3), dtype=float)
        for mesh_index in range(1, len(getattr(self, "EEE", []) or [])):
            try:
                if int(self.GlassOnSide[int(mesh_index)]) != target_surface:
                    continue
                mesh_points = np.asarray(getattr(self.EEE[int(mesh_index)], "points", np.empty((0, 3))), dtype=float)
            except Exception:
                continue
            if mesh_points.ndim == 2 and mesh_points.shape[0] > 0 and mesh_points.shape[1] >= 3:
                finite = mesh_points[np.all(np.isfinite(mesh_points[:, :3]), axis=1), :3]
                if finite.size:
                    points.append(np.asarray(finite, dtype=float))
        if not points:
            return np.empty((0, 3), dtype=float)
        return np.vstack(points)

    def __OpticalSolidFaceIsInternal(self, surface_index, face_override, hit_point=None):
        face = dict(face_override or {}) if isinstance(face_override, dict) else {}
        normal = face.get("normal_world", face.get("normal"))
        try:
            normal = np.asarray(normal, dtype=float).reshape(-1)[:3]
        except Exception:
            return False
        norm = float(np.linalg.norm(normal))
        if normal.size < 3 or not np.all(np.isfinite(normal[:3])) or norm <= 1e-12:
            return False
        normal = normal[:3] / norm
        point = None
        for key in ("centroid_world", "point_world", "centroid"):
            try:
                candidate = np.asarray(face.get(key), dtype=float).reshape(-1)[:3]
            except Exception:
                candidate = np.asarray([], dtype=float)
            if candidate.size >= 3 and np.all(np.isfinite(candidate[:3])):
                point = candidate[:3]
                break
        if point is None:
            try:
                candidate = np.asarray(hit_point, dtype=float).reshape(-1)[:3]
            except Exception:
                candidate = np.asarray([], dtype=float)
            if candidate.size >= 3 and np.all(np.isfinite(candidate[:3])):
                point = candidate[:3]
        if point is None:
            return False
        points = self.__OpticalSolidScenePoints(surface_index)
        if points.ndim != 2 or points.shape[0] < 4:
            return False
        projections = points[:, :3] @ normal
        finite = projections[np.isfinite(projections)]
        if finite.size < 4:
            return False
        span = float(np.max(finite) - np.min(finite))
        if not np.isfinite(span) or span <= 1e-9:
            return False
        margin = max(span * 2.0e-4, 0.02)
        face_projection = float(np.dot(point[:3], normal))
        return bool(face_projection > float(np.min(finite)) + margin and face_projection < float(np.max(finite)) - margin)

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
        try:
            split_ratio = float(matched.get("split_ratio", 0.5))
        except Exception:
            split_ratio = 0.5
        if not np.isfinite(split_ratio):
            split_ratio = 0.5
        try:
            loss = float(matched.get("loss", 0.0))
        except Exception:
            loss = 0.0
        if not np.isfinite(loss):
            loss = 0.0
        try:
            phase_deg = float(matched.get("phase_deg", 180.0))
        except Exception:
            phase_deg = 180.0
        if not np.isfinite(phase_deg):
            phase_deg = 180.0
        override = {
            "face_id": str(matched.get("face_id", "") or "").strip(),
            "side_2d": str(matched.get("side_2d", "") or "").strip(),
            "function": function,
            "split_ratio": float(np.clip(split_ratio, 0.0, 1.0)),
            "loss": float(np.clip(loss, 0.0, 1.0)),
            "phase_deg": phase_deg,
            "coating": str(matched.get("coating", "") or "").strip(),
            "centroid_world": tuple(float(value) for value in np.asarray(matched.get("centroid_world", matched.get("centroid", point_world)), dtype=float).reshape(3)),
            "point_world": tuple(float(value) for value in np.asarray(point_world, dtype=float).reshape(3)),
            "normal_world": tuple(float(value) for value in np.asarray(matched.get("normal_world", normal_world), dtype=float).reshape(3)),
            "boundary_source": str(matched.get("boundary_source", "") or "").strip(),
        }
        # Per-face coating: a promoted-solid face can carry its own coating table, resolved at
        # build into surface.OpticalSolidFaceCoatingTables from the shared COATING_PRESETS (keyed
        # by face_id). __CollectData reads self._collect_interaction_override, which the subset
        # builders REBUILD copying only a few keys (dropping coating_table), so the table is carried
        # on a DEDICATED channel that survives to the energy calc. Set unconditionally per face
        # (None for an uncoated face) so a previous coated face's table can never leak to this hit.
        self._collect_face_coating_override = None
        try:
            face_coatings = getattr(self.SDT[int(surface_index)], "OpticalSolidFaceCoatingTables", None)
            if isinstance(face_coatings, dict) and override["face_id"]:
                entry = face_coatings.get(override["face_id"])
                if entry:
                    override["coating_table"] = entry[0]
                    override["coating_met"] = entry[1]
                    self._collect_face_coating_override = (entry[0], entry[1])
        except Exception:
            pass
        diagnostics = [
            str(item)
            for item in list(matched.get("diagnostics", []) or [])
            if str(item).strip()
        ]
        if diagnostics:
            override["face_match_warning"] = "; ".join(diagnostics)
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
            has_input_port = self.__OpticalSolidHasInputPort(world_faces, surface_index)
            if not has_input_port:
                override["external_reflection"] = True
        if function == "Absorber/Mechanical":
            override["force_absorption"] = True
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
            if not hasattr(self, "_optical_solid_mesh_face_id_cache"):
                self._optical_solid_mesh_face_id_cache = {}
            world_faces = self.__OpticalSolidWorldFaces(surface_index)
            face_signature = self.__OpticalSolidWorldFaceSignature(surface_index, world_faces)
            cache_key = (int(mesh_index), id(mesh), face_signature)
            cached = self._optical_solid_mesh_face_id_cache.get(cache_key)
            if cached is not None:
                return cached
            # Trace against a lossless decimated proxy when the solid is a planar
            # polyhedron (beam-splitter cube / prism): ray intersection needs no
            # display resolution, and the per-hit normal/face-id work is O(cells).
            # A curved surface fails the proxy's planarity check and is returned
            # unchanged. The proxy's face ids must be assigned by plane match.
            proxy = decimate_optical_solid_trace_mesh(
                mesh,
                world_faces,
                context=context,
            )
            mesh = assign_mesh_cell_face_ids(
                proxy,
                world_faces,
                context=context,
                prefer_plane_match=(proxy is not mesh),
            )
            self.__ReplaceSceneMesh(mesh_index, mesh)
            self._optical_solid_mesh_face_id_cache[cache_key] = mesh
            self._optical_solid_mesh_face_id_cache[(int(mesh_index), id(mesh), face_signature)] = mesh
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

    def __NonSequentialIntersectionPolicy(self):
        return NonSequentialIntersectionPolicy.from_surfaces(getattr(self, "SDT", []))

    def __NonSequentialNearHitTolerance(self):
        return self.__NonSequentialIntersectionPolicy().near_hit_tolerance

    def __NonSequentialSameSurfaceHitTolerance(self):
        return self.__NonSequentialIntersectionPolicy().same_surface_tolerance


    def __NonSequentialChooserToot(self, A_RayOrig, A_Proto_pTarget, k, current_surface_index=None):
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
            return distance, 0, None, None
        else:
            (A_pTarget, A_SurfHit) = self.__TraceSceneMeshRay(
                k,
                A_RayOrig,
                A_Proto_pTarget,
                f"non-sequential chooser surface {k}",
            )
            if (len(A_SurfHit) == 0):
                distance = 99999999999999.9
                return distance, 0, A_pTarget, A_SurfHit
            else:
                s = 0
                h = []
                intersection_policy = self.__NonSequentialIntersectionPolicy()
                try:
                    mesh_surface_index = int(self.GlassOnSide[int(k)])
                except Exception:
                    mesh_surface_index = -1
                for f in A_SurfHit:
                    PD = (np.asarray(A_pTarget[s]) - np.asarray(A_RayOrig))
                    distance = np.linalg.norm(PD)
                    reject_tolerance = intersection_policy.rejection_tolerance(
                        mesh_surface_index,
                        current_surface_index,
                    )
                    if (np.abs(distance) <= reject_tolerance):
                        distance = 99999999999999.9
                    h.append(distance)
                    s = (s + 1)
                distance = np.min(np.asarray(h))
        return distance, int(len(A_SurfHit)), A_pTarget, A_SurfHit

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
        skip_index = -1
        if skip_surface is not None:
            try:
                skip_index = int(skip_surface)
            except Exception:
                skip_index = -1
        hit_counts = []
        hit_records = []
        for k in range(1, len(self.EEE)):
            if k == skip_index:
                chooser.append(99999999999999.9)
                hit_counts.append(0)
                hit_records.append((None, None))
                continue
            distance, hit_count, hit_points, hit_cells = self.__NonSequentialChooserToot(
                A_RayOrig,
                A_Proto_pTarget,
                k,
                current_surface_index=j,
            )
            chooser.append(distance)
            hit_counts.append(int(hit_count))
            hit_records.append((hit_points, hit_cells))
        chooser = np.asarray(chooser)
        if chooser.size == 0 or float(np.min(chooser)) >= 9999999999999.0:
            return (int(j), 0, 0, 0)
        jj = (np.argmin(chooser) + 1)
        chooser[(jj - 1)] = 99999999999999.9
        kk = (np.argmin(chooser) + 1)
        PRR = int(hit_counts[int(jj) - 1]) if 0 <= int(jj) - 1 < len(hit_counts) else 0
        try:
            hit_points, hit_cells = hit_records[int(jj) - 1]
            if hit_points is not None and hit_cells is not None and hasattr(self.INORM, "set_trace_mesh_ray_cache"):
                self.INORM.set_trace_mesh_ray_cache(
                    int(jj),
                    A_RayOrig,
                    A_Proto_pTarget,
                    self.EEE[int(jj)],
                    hit_points,
                    hit_cells,
                )
        except Exception:
            pass
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
        self.MESH_FACE_MATCH_WARNING = []
        self.VOLUME_ID = []
        self.MEDIA_IN = []
        self.MEDIA_OUT = []
        self.MEDIA_TRANSITION = []
        self.MEDIA_STATE_METHOD = []
        self.MEDIA_STATE_DIAGNOSTIC = []
        self.INSIDE_VOLUMES_BEFORE = []
        self.INSIDE_VOLUMES_AFTER = []
        self.BRANCH_FINAL_MEDIA = ""
        self.BRANCH_FINAL_INDEX = np.nan
        self.BRANCH_FINAL_INSIDE_VOLUMES = ""
        self.BRANCH_FINAL_MEDIA_STATE_METHOD = ""
        self._collect_tt_override = None
        self._collect_bulk_override = None
        self._collect_interaction_override = None
        self._collect_mesh_hit_override = None
        self._collect_media_state_override = None
        self._collect_face_coating_override = None
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
        media_state_override = dict(self._collect_media_state_override or {})
        self._collect_media_state_override = None
        # Per-face coating table for THIS hit (set by __OpticalSolidFaceInteraction on its own
        # channel, since the interaction-override subset rebuild drops it). Consume-once.
        face_coating_override = getattr(self, "_collect_face_coating_override", None)
        self._collect_face_coating_override = None

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
            # Coating -- a promoted-solid face's own coating table (resolved per-face, carried on
            # the dedicated channel that survives the interaction-override subset rebuild) takes
            # precedence over the surface's for THIS hit; absent, the surface Coating/CoatingMet
            # are used exactly as before (the additive contract).
            if face_coating_override:
                Rp2, Rs2, Tp2, Ts2, V = self.CoatingFun(face_coating_override[0], self.ang, self.Wave)
                mtl = int(face_coating_override[1] or 0)
            else:
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
        mesh_face_match_warning = str(mesh_hit_override.get("face_match_warning", "") or "").strip()
        if not mesh_face_match_warning:
            mesh_face_match_method = str(mesh_hit_override.get("face_match_method", "") or "").strip()
            mesh_face_id = str(mesh_hit_override.get("face_id", "") or "").strip()
            if mesh_face_match_method == "plane_inference":
                mesh_face_match_warning = "Optical solid face inferred from face plane; exact triangle membership is unavailable."
            elif mesh_cell_id >= 0 and mesh_face_id and not mesh_face_match_method:
                mesh_face_match_warning = "Optical solid mesh hit has no face-match provenance."
            elif mesh_cell_id >= 0 and not mesh_face_id:
                mesh_face_match_warning = "Optical solid mesh hit has no matched face id."
        self.MESH_FACE_MATCH_WARNING.append(mesh_face_match_warning)
        self.VOLUME_ID.append(str(media_state_override.get("volume_id", "") or ""))
        self.MEDIA_IN.append(str(media_state_override.get("media_in", "") or ""))
        self.MEDIA_OUT.append(str(media_state_override.get("media_out", "") or ""))
        self.MEDIA_TRANSITION.append(str(media_state_override.get("transition", "") or ""))
        self.MEDIA_STATE_METHOD.append(str(media_state_override.get("method", "") or ""))
        self.MEDIA_STATE_DIAGNOSTIC.append(str(media_state_override.get("diagnostic", "") or ""))
        self.INSIDE_VOLUMES_BEFORE.append(str(media_state_override.get("inside_before", "") or ""))
        self.INSIDE_VOLUMES_AFTER.append(str(media_state_override.get("inside_after", "") or ""))

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
        self._optical_solid_face_world_signature_cache = {}
        self._optical_solid_mesh_face_id_cache = {}
        self._ns_requires_branching_cache = None
        self.SuTo = SUT(self.SDT)
        self.Object_Num = np.arange(0, self.n, 1)
        self.__SurFuncSuscrip()
        self.Pr3D.Prerequisites3SMath()
        self.INORM = InterNormalCalc(self.SDT, self.TypeTotal, self.Pr3D, self.HS)

    def SetSolid(self):
        """SetSolid.
        """
        self._optical_solid_face_world_cache = {}
        self._optical_solid_face_world_signature_cache = {}
        self._optical_solid_mesh_face_id_cache = {}
        self._ns_requires_branching_cache = None
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

    def __BeamSplitterSettingsFromFace(self, face_override):
        face = dict(face_override or {}) if isinstance(face_override, dict) else {}
        function = normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
        if function != "Beam Splitter":
            return None
        try:
            reflectance = float(face.get("split_ratio", face.get("reflectance", 0.5)))
        except Exception:
            reflectance = 0.5
        try:
            absorption = float(face.get("loss", face.get("absorption", 0.0)))
        except Exception:
            absorption = 0.0
        reflectance = min(max(reflectance, 0.0), 1.0)
        absorption = min(max(absorption, 0.0), 1.0 - reflectance)
        try:
            phase_deg = float(face.get("phase_deg", face.get("reflect_phase_deg", 180.0)))
        except Exception:
            phase_deg = 180.0
        if not np.isfinite(phase_deg):
            phase_deg = 180.0
        return {
            "deterministic": True,
            "use_coating_table": False,
            "use_fresnel_polarization": False,
            "reflectance": reflectance,
            "transmittance": max(1.0 - reflectance - absorption, 0.0),
            "absorption": absorption,
            "polarization_p_fraction": 0.5,
            "polarization_s_phase_deg": 0.0,
            "min_branch_power": 1e-4,
            "max_branch_depth": 8,
            "transmit_phase_deg": 0.0,
            "reflect_phase_deg": phase_deg,
            "transmit_s_phase_deg": 0.0,
            "reflect_s_phase_deg": 0.0,
            "split_mode": "Deterministic face split",
        }

    def __BeamSplitterSettings(self, j, face_override=None):
        face_settings = self.__BeamSplitterSettingsFromFace(face_override)
        if face_settings is not None:
            return face_settings
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
            "split_mode": str(settings.get("split_mode", settings.get("mode", "Deterministic paths"))),
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
        # Scene-level invariant (beam-splitter / diffuse-scatter presence): the
        # deterministic-BS check re-normalises every solid's full face metadata
        # (the huge per-face triangle_indices lists), and this is hit once per
        # ray. Memoise it for the system's lifetime; SetData/SetSolid (the
        # prescription-change hooks that already reset the optical-solid caches)
        # clear it.
        cached = getattr(self, "_ns_requires_branching_cache", None)
        if cached is not None:
            return cached
        result = bool(
            self.__NsTraceHasDeterministicBeamSplitter() or self.__NsTraceHasDiffuseScatter()
        )
        self._ns_requires_branching_cache = result
        return result

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
            try:
                metadata = normalize_optical_solid_face_metadata(getattr(self.SDT[int(j)], "OpticalSolidFaces", {}))
            except Exception:
                metadata = {"faces": []}
            for face in list(metadata.get("faces", []) or []):
                if self.__BeamSplitterSettingsFromFace(face) is not None:
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
        termination_reason="",
        termination_diagnostic="",
        branch_tree_diagnostic="",
        final_ray_state=None,
    ):
        keys = (
            "SURFACE", "NAME", "GLASS", "S_XYZ", "T_XYZ", "XYZ", "OST_XYZ", "OST_LMN",
            "S_LMN", "LMN", "R_LMN", "N0", "N1", "WAV", "G_LMN", "ORDER", "GRATING",
            "DISTANCE", "OP", "TOP_S", "TOP", "ALPHA", "BULK_TRANS", "RP", "RS",
            "TP", "TS", "TTBE", "TT", "INTERACTION_TYPE", "INTERACTION_MODEL",
            "INTERACTION_TARGET_SURFACE", "INTERACTION_IN_POWER", "INTERACTION_COEFF",
            "INTERACTION_OUT_POWER", "INTERACTION_LOSS_POWER", "INTERACTION_BULK",
            "MESH_CELL_ID", "MESH_ORIGINAL_CELL_ID", "MESH_FACE_ID",
            "MESH_FACE_MATCH_METHOD", "MESH_FACE_MATCH_SCORE", "MESH_FACE_MATCH_WARNING",
            "VOLUME_ID", "MEDIA_IN", "MEDIA_OUT", "MEDIA_TRANSITION",
            "MEDIA_STATE_METHOD", "MEDIA_STATE_DIAGNOSTIC",
            "INSIDE_VOLUMES_BEFORE", "INSIDE_VOLUMES_AFTER",
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
        data["branch_termination_reason"] = str(termination_reason or "")
        data["branch_termination_diagnostic"] = str(termination_diagnostic or "")
        data["branch_tree_diagnostic"] = str(branch_tree_diagnostic or "")
        if final_ray_state is not None:
            data.update(self.__NsRayStateBranchFields(final_ray_state))
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
                "branch_termination_reason",
                "branch_termination_diagnostic",
                "branch_tree_diagnostic",
                "branch_final_media",
                "branch_final_index",
                "branch_final_inside_volumes",
                "branch_final_media_state_method",
                "Wave",
            }:
                continue
            setattr(self, key, copy.deepcopy(value))
        if "Wave" in data:
            self.Wave = copy.deepcopy(data["Wave"])
        self._collect_tt_override = None
        self._collect_bulk_override = None
        self._collect_interaction_override = None
        self._collect_mesh_hit_override = None
        self._collect_media_state_override = None
        self._collect_face_coating_override = None

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

    def __AppendNsTerminalSegment(self, RayOrig, ResVec, SIGN=1, stop_point=None):
        if len(self.RAY) == 0:
            return None
        if stop_point is not None:
            # bugs/0093: a vignetted ray ENDS at the blocking plane (the aperture
            # stop), not at a far escape length.
            terminal = np.asarray(stop_point, dtype=float).reshape(3)
            last = np.asarray(self.RAY[-1], dtype=float)
            if np.linalg.norm(terminal - last) > 1e-9:
                self.RAY.append(terminal)
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

    def __NsApertureStopVignette(self, RayOrig, ResVec, SIGN, pTarget):
        """bugs/0093: vignette a ray that crosses an APERTURE STOP plane OUTSIDE its
        clear aperture before reaching the chosen surface.

        In non-sequential mode a ray that lands outside a finite stop is simply not
        chosen by ``__NonSequentialChooser`` and sails straight through, unrefracted
        and unblocked -- that is the cube-before-lens "diverging rays" (the cube
        forces non-seq mode). A real aperture stop blocks rays outside its clear
        aperture, so here we terminate the ray AT the stop plane. Only surfaces the
        editor flagged ``IsApertureStop`` are blocking -- arbitrary elements/lens
        edges are NOT, so this never makes rays vanish at a randomly-placed element
        (see the random-element robustness rule). Returns ``(world vignette point,
        blocking surface index)``; both ``None`` when nothing blocks. bugs/0179: the
        caller records the blocking surface as the ray's terminal so the scene bundle
        labels it stopped-at-stop, not an image hit.
        """
        try:
            RayOrig = np.asarray(RayOrig, dtype=float).reshape(3)
            ResVec = np.asarray(ResVec, dtype=float).reshape(3)
        except Exception:
            return None
        nd = float(np.linalg.norm(ResVec))
        if nd <= 1.0e-12:
            return None
        udir = (ResVec / nd) * float(SIGN)
        try:
            d_next = float(np.linalg.norm(np.asarray(pTarget, dtype=float).reshape(3) - RayOrig))
        except Exception:
            d_next = None
        far = RayOrig + udir * 1.0e9
        best_d = None
        best_pt = None
        best_k = None
        for k in range(1, len(self.SDT)):
            s = self.SDT[k]
            if not bool(getattr(s, "IsApertureStop", False)):
                continue
            try:
                T = self.Pr3D.TRANS_1A[k]
                Ps = T.dot(np.array([RayOrig[0], RayOrig[1], RayOrig[2], 1.0]))
                Pf = T.dot(np.array([far[0], far[1], far[2], 1.0]))
                P_x1, P_y1, P_z1 = float(Ps[(0, 0)]), float(Ps[(0, 1)]), float(Ps[(0, 2)])
                F_x, F_y, F_z = float(Pf[(0, 0)]), float(Pf[(0, 1)]), float(Pf[(0, 2)])
            except Exception:
                continue
            P12 = np.array([F_x - P_x1, F_y - P_y1, F_z - P_z1])
            seg = float(np.linalg.norm(P12))
            if seg < 1.0e-12:
                continue
            L, M, N = (P12 / seg)
            if abs(N) < 1.0e-12:
                continue
            d_stop = -P_z1 / N  # forward distance to the stop plane (rigid transform preserves length)
            if d_stop <= 1.0e-6:
                continue
            if d_next is not None and d_stop >= d_next - 1.0e-6:
                continue  # the chosen surface is reached at/before the stop
            Px = (L / N) * (-P_z1) + P_x1
            Py = (M / N) * (-P_z1) + P_y1
            try:
                sub = s.SubAperture
                sub0, sub1, sub2 = float(sub[0]), float(sub[1]), float(sub[2])
            except Exception:
                sub0, sub1, sub2 = 1.0, 0.0, 0.0
            D0 = 2.0 * float(np.hypot(Px - sub2, Py - sub1))
            DiamSup = float(getattr(s, "Diameter", 0.0)) * sub0
            DiamInf = float(getattr(s, "InDiameter", 0.0)) * sub0 * float(getattr(self.INORM, "Disable_Inner", 1.0))
            blocked = bool(D0 > DiamSup or D0 < DiamInf)  # outside the circular clear aperture
            # bugs/0179: a User-Defined Aperture (e.g. the rectangular beam-splitter exit
            # stop in the coaxial-LED layout) defines a NON-circular clear aperture. The
            # sequential trace already vignettes on UDA_Obj.Hit (InterNormalCalc); honour the
            # same test here so a ray crossing the stop plane outside the polygon is blocked.
            uda_obj = getattr(s, "UDA_Obj", "None")
            if (not blocked) and uda_obj != "None" and uda_obj is not None:
                try:
                    if not bool(uda_obj.Hit(Px, Py)):
                        blocked = True
                except Exception:
                    pass
            if blocked:  # outside the clear aperture (circular or UDA) -> blocked
                if best_d is None or d_stop < best_d:
                    best_d = d_stop
                    best_pt = RayOrig + udir * d_stop
                    best_k = k
        return best_pt, best_k

    def __NsTraceTerminationDiagnostic(
        self,
        reason,
        RayOrig=None,
        ResVec=None,
        SIGN=1,
        branch_path="",
        count=None,
        surface_index=None,
        extra="",
    ):
        labels = {
            "no_next_intersection": "ray left the modeled scene without another surface hit",
            "surface_intersection_failed": "nearest surface chooser found a candidate but the surface intersection failed",
            "ns_limit_exceeded": "non-sequential step limit was exceeded",
            "invalid_surface_zero": "non-sequential chooser returned the object surface as the next hit",
            "scene_boundary_exhausted": "non-sequential chooser reached the end of the surface list",
            "stalled_repeated_surface": "non-sequential trace stopped after a repeated same-surface hit",
            "target_surface_reached": "configured target surface was reached",
            "null_surface": "trace stopped at a NULL surface",
            "absorb": "trace stopped at an absorptive surface",
        }
        parts = [labels.get(str(reason), str(reason))]
        path = str(branch_path or "").strip()
        if path and path != "primary":
            parts.append(f"path={path}")
        if surface_index is not None:
            try:
                parts.append(f"surface=S{int(surface_index)}")
            except Exception:
                pass
        if count is not None:
            try:
                parts.append(f"steps={int(count)}")
            except Exception:
                pass
        try:
            origin = np.asarray(RayOrig, dtype=float).reshape(-1)
            if origin.size >= 3 and np.isfinite(origin[:3]).all():
                parts.append(
                    "origin=({:.6g},{:.6g},{:.6g})".format(
                        float(origin[0]),
                        float(origin[1]),
                        float(origin[2]),
                    )
                )
        except Exception:
            pass
        try:
            direction = np.asarray(ResVec, dtype=float).reshape(-1)
            direction = direction * float(SIGN)
            norm = float(np.linalg.norm(direction[:3]))
            if direction.size >= 3 and norm > 1e-12 and np.isfinite(direction[:3]).all():
                direction = direction[:3] / norm
                parts.append(
                    "direction=({:.6g},{:.6g},{:.6g})".format(
                        float(direction[0]),
                        float(direction[1]),
                        float(direction[2]),
                    )
                )
        except Exception:
            pass
        extra_text = str(extra or "").strip()
        if extra_text:
            parts.append(extra_text)
        return "; ".join(parts)

    def __NsTraceHitMedia(self, j, jj, PrevN, CurrN, alpha, Glass, hit_point=None, hit_normal=None, ray_state=None):
        """Return the refractive media to use for a non-sequential hit."""
        state = self.__NsRayStateFromRecord(ray_state, PrevN)
        N = float(state.current_index)
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
            volume_record = self.__SceneOpticalVolumeRecord(j)
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
            volume_material = str(volume_record.get("material", "") or "").strip()
            if volume_material and volume_material.upper() not in {"AIR", "NONE", "NULL"}:
                if volume_material != str(solid_glass):
                    try:
                        solid_n, solid_alpha = n_wave_dispersion(self.SETUP, volume_material, self.Wave)
                        solid_n = float(solid_n)
                    except Exception:
                        pass
                solid_glass = volume_material

            volume_id = str(volume_record.get("volume_id", "") or f"volume:{int(j)}")
            ambient_n = float(getattr(self, "Next", 1.0))
            tolerance = max(1e-7, abs(solid_n) * 1e-7)
            if volume_id and volume_id in tuple(state.inside_volumes):
                media_transition = "exit"
                media_state_method = "ray_state_inside_volumes"
            elif ray_state is not None and volume_id:
                media_transition = "entry"
                media_state_method = "ray_state_inside_volumes"
            elif abs(float(N) - solid_n) <= tolerance:
                media_transition = "exit"
                media_state_method = "prev_index_compare"
            else:
                media_transition = "entry"
                media_state_method = "prev_index_compare"
            if media_transition == "exit":
                # Inside the closed STL: this boundary is an exit candidate.
                N = solid_n
                Np = ambient_n
                CurrN = ambient_n
                alpha = 0.0
            else:
                # Outside the closed STL: this boundary is an entry candidate.
                Np = solid_n
                CurrN = solid_n
                alpha = solid_alpha
            Glass = solid_glass
            face_override = self.__OpticalSolidFaceInteraction(j, hit_point, hit_normal, mesh_hit=mesh_hit)
            if not isinstance(face_override, dict):
                normal_world = ()
                try:
                    normal_arr = np.asarray(hit_normal, dtype=float).reshape(-1)[:3]
                    if normal_arr.size == 3 and np.all(np.isfinite(normal_arr)):
                        normal_world = tuple(float(value) for value in normal_arr)
                except Exception:
                    normal_world = ()
                face_override = {
                    "function": "",
                    "normal_world": normal_world,
                    "boundary_source": "implicit_optical_solid_volume",
                }
            if volume_id:
                self._collect_interaction_override = {
                    "model": f"optical_volume_{media_transition}_{media_state_method}:{volume_id}",
                    "target_surface": int(j),
                }
            mesh_hit_override = {
                "cell_id": mesh_hit.get("cell_id", -1),
                "original_cell_id": mesh_hit.get("original_cell_id", -1),
                "face_id": mesh_hit.get("face_id", ""),
                "face_match_method": mesh_hit.get("face_match_method", ""),
                "face_match_score": mesh_hit.get("face_match_score"),
                "face_match_warning": mesh_hit.get("face_match_warning", ""),
            }
            if isinstance(face_override, dict):
                if self.__OpticalSolidFaceIsInternal(j, face_override, hit_point=hit_point):
                    N = solid_n
                    Np = solid_n
                    CurrN = solid_n
                    alpha = solid_alpha
                    face_override["media_transition"] = "internal"
                    face_override["media_state_method"] = "internal_optical_solid_face"
                face_override["volume_id"] = volume_id
                face_override["volume_material"] = solid_glass
                face_override["ambient_material"] = str(volume_record.get("ambient_material", "AIR") or "AIR")
                face_override.setdefault("media_transition", media_transition)
                face_override.setdefault("media_state_method", media_state_method)
                if bool(face_override.get("force_reflection")) and volume_id:
                    inside_before = volume_id in tuple(state.inside_volumes)
                    active_transition = str(face_override.get("media_transition", media_transition) or "").strip()
                    if inside_before or active_transition in {"exit", "internal"}:
                        face_override.pop("external_reflection", None)
                    elif active_transition == "entry":
                        face_override["external_reflection"] = True
                face_id = str(face_override.get("face_id", "") or "").strip()
                if face_id:
                    mesh_hit_override["face_id"] = face_id
                face_match_method = str(face_override.get("face_match_method", "") or "").strip()
                if face_match_method:
                    mesh_hit_override["face_match_method"] = face_match_method
                if face_override.get("face_match_score") is not None:
                    mesh_hit_override["face_match_score"] = face_override.get("face_match_score")
                face_match_warning = str(face_override.get("face_match_warning", "") or "").strip()
                if face_match_warning:
                    mesh_hit_override["face_match_warning"] = face_match_warning
            self._collect_mesh_hit_override = mesh_hit_override
            return Glass, alpha, CurrN, N, Np, face_override

        try:
            surface_glass = str(self.Glass[int(j)]).strip().upper()
        except Exception:
            surface_glass = ""
        if surface_glass == "ABSORB":
            return "ABSORB", 0.0, N, N, N, face_override

        if ((self.SDT[j].Solid_3d_stl == 'None') and (self.TypeTotal[jj] == 1)):
            if (N == 1):
                Np = CurrN
            else:
                N = CurrN
                Np = 1
        return Glass, alpha, CurrN, N, Np, face_override

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

    def __NsTraceIsStlSolidHit(self, surface_index, chooser_surface_index):
        try:
            return bool(
                self.TypeTotal[int(chooser_surface_index)] == 1
                and self.SDT[int(surface_index)].Solid_3d_stl != 'None'
            )
        except Exception:
            return False

    def __NsPhysicalDirection(self, direction, sign):
        direction_vec = np.asarray(direction, dtype=float)
        try:
            direction_vec = direction_vec * float(sign)
        except Exception:
            try:
                direction_vec = direction_vec * np.asarray(sign, dtype=float)
            except Exception:
                pass
        return direction_vec

    def __NsTraceBoundaryContinuationMode(self, surface_index, chooser_surface_index, prev_n, curr_n, sign, face_override):
        if not self.__NsTraceIsStlSolidHit(surface_index, chooser_surface_index):
            return ""
        reflected = bool(isinstance(face_override, dict) and bool(face_override.get("force_reflection")))
        try:
            reflected = reflected or float(sign) < 0.0
        except Exception:
            pass
        if reflected:
            return "reflection"
        try:
            if float(prev_n) > float(curr_n) + 1e-9:
                return "exit"
        except Exception:
            pass
        return ""

    def __NsTraceShouldNudgeAfterStlExit(self, surface_index, chooser_surface_index, prev_n, curr_n, sign, face_override):
        return self.__NsTraceBoundaryContinuationMode(
            surface_index,
            chooser_surface_index,
            prev_n,
            curr_n,
            sign,
            face_override,
        ) == "exit"

    def __NsTraceAllowsSameSurfaceContinuation(self, surface_index, chooser_surface_index, face_override):
        if self.__NsTraceIsStlSolidHit(surface_index, chooser_surface_index):
            return True
        if isinstance(face_override, dict) and str(face_override.get("volume_id", "") or "").strip():
            return True
        return False

    def __NsTraceSplitChildSkipSurface(self, surface_index, face_override):
        if isinstance(face_override, dict):
            transition = str(face_override.get("media_transition", "") or "").strip().lower()
            if transition == "internal":
                return None
            if self.__BeamSplitterSettingsFromFace(face_override) is not None and self.__OpticalSolidFaceIsInternal(surface_index, face_override):
                return None
        try:
            return int(surface_index)
        except Exception:
            return None

    def __NsTraceIsRepeatedSurfaceStall(
        self,
        a,
        b,
        c,
        pre_surf_hit,
        surface_index,
        chooser_surface_index,
        face_override,
        boundary_continuation_mode="",
    ):
        if isinstance(face_override, dict) and bool(face_override.get("force_reflection")):
            return False
        if str(boundary_continuation_mode or ""):
            return False
        if self.__NsTraceAllowsSameSurfaceContinuation(surface_index, chooser_surface_index, face_override):
            return False
        return (a == b) and (b == c) and (c == pre_surf_hit)

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
        initial_prev_n = self.N_Prec[0]
        initial_ray_state = self.__InitialNsRayState(initial_prev_n)
        start_state = {
            "trace": self.__NsTraceSnapshot(0, None, 1.0, 0.0, "primary"),
            "RayOrig": pS,
            "ResVec": dC,
            "PrevN": initial_prev_n,
            "media_state": initial_ray_state.to_record(),
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
        branch_truncated = False

        while queue and len(results) < branch_result_limit:
            state = queue.pop(0)
            self.__RestoreNsTraceSnapshot(state["trace"])
            RayOrig = np.asarray(state["RayOrig"], dtype=float)
            ResVec = np.asarray(state["ResVec"], dtype=float)
            PrevN = state["PrevN"]
            ray_state = self.__NsRayStateFromRecord(state.get("media_state"), PrevN)
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
            termination_reason = ""
            termination_diagnostic = ""

            while True:
                if (j == self.Targ_Surf):
                    termination_reason = "target_surface_reached"
                    termination_diagnostic = self.__NsTraceTerminationDiagnostic(
                        termination_reason,
                        RayOrig,
                        ResVec,
                        SIGN,
                        branch_path,
                        count,
                        surface_index=j,
                    )
                    break
                (a, b, c, PreSurfHit) = self.__NonSequentialChooser(SIGN, RayOrig, ResVec, j, skip_surface_once)
                skip_surface_once = None

                if (PreSurfHit == 0):
                    self.__AppendNsTerminalSegment(RayOrig, ResVec, SIGN)
                    termination_reason = "no_next_intersection"
                    termination_diagnostic = self.__NsTraceTerminationDiagnostic(
                        termination_reason,
                        RayOrig,
                        ResVec,
                        SIGN,
                        branch_path,
                        count,
                        surface_index=j,
                    )
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
                    if count > self.NsLimit:
                        termination_reason = "ns_limit_exceeded"
                    elif j == 0:
                        termination_reason = "invalid_surface_zero"
                    else:
                        termination_reason = "scene_boundary_exhausted"
                    termination_diagnostic = self.__NsTraceTerminationDiagnostic(
                        termination_reason,
                        RayOrig,
                        ResVec,
                        SIGN,
                        branch_path,
                        count,
                        surface_index=j,
                    )
                    break
                if (self.Glass[j] != 'NULL'):
                    Proto_pTarget = (np.asarray(RayOrig) + ((np.asarray(ResVec) * 999999999.9) * SIGN))
                    Output = self.INORM.InterNormal(RayOrig, Proto_pTarget, j, jj)
                    (SurfHit, SurfNorm, pTarget, GooveVect, HitObjSpace, LMNObjSpace, j) = Output
                    if (SurfHit == 0):
                        self.__AppendNsTerminalSegment(RayOrig, ResVec, SIGN)
                        termination_reason = "surface_intersection_failed"
                        termination_diagnostic = self.__NsTraceTerminationDiagnostic(
                            termination_reason,
                            RayOrig,
                            ResVec,
                            SIGN,
                            branch_path,
                            count,
                            surface_index=j,
                        )
                        break
                    vign_pt, vign_k = self.__NsApertureStopVignette(RayOrig, ResVec, SIGN, pTarget)
                    if vign_pt is not None:
                        self.__AppendNsTerminalSegment(RayOrig, ResVec, SIGN, stop_point=vign_pt)
                        # bugs/0179: the branch's per-branch snapshot/restore data extraction
                        # labels the terminal via this termination_reason (the coaxial layout is
                        # non-branching, so the NsTrace EmptyCollect path is the one under test).
                        termination_reason = "aperture_stop_vignette"
                        termination_diagnostic = self.__NsTraceTerminationDiagnostic(
                            termination_reason,
                            RayOrig,
                            ResVec,
                            SIGN,
                            branch_path,
                            count,
                            surface_index=j,
                        )
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
                        ray_state,
                    )
                    incident_state_diagnostic = self.__NsRayStateIncidentIndexDiagnostic(ray_state, PrevN)
                    D = GooveVect

                    Ord = self.SDT[j].Diff_Ord
                    GrSpa = self.SDT[j].Grating_D
                    if isinstance(face_override, dict) and bool(face_override.get("force_reflection")):
                        try:
                            R = np.asarray(face_override.get("normal_world"), dtype=float).reshape(3)
                        except Exception:
                            pass
                    terminal_event = self.__NsTraceTerminalEvent(j, face_override)
                    ResVec_N, R_N, N_N, Np_N = ResVec, R, N, Np
                    secuent = 1 if isinstance(face_override, dict) and bool(face_override.get("force_reflection")) else 0
                    (trans_vec, trans_n, trans_sign, trans_ang) = self.SDT[j].PHYSICS.calculate(
                        ResVec_N, R_N, N_N, Np_N, D, Ord, GrSpa, self.Wave, secuent
                    )
                    self.ang = trans_ang
                    if terminal_event:
                        self.__ApplyNsTerminalEventOverride(terminal_event)
                    elif isinstance(face_override, dict) and bool(face_override.get("force_reflection")):
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
                    splitter_settings = self.__BeamSplitterSettings(j, face_override=face_override)
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
                                child_media_state, child_media_event = self.__NsRayMediaEvent(
                                    ray_state,
                                    face_override,
                                    N,
                                    1.0,
                                    media_out=ray_state.current_medium,
                                    method="scatter_no_media_change",
                                    diagnostic=incident_state_diagnostic,
                                )
                                self._collect_media_state_override = child_media_event
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
                                    N,
                                    N,
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
                                        "PrevN": float(child_media_state.current_index),
                                        "media_state": child_media_state.to_record(),
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
                                    branch_truncated = True
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
                                trans_n = N
                                trans_sign = 1.0 / float(SIGN) if abs(float(SIGN)) > 1e-12 else 1.0
                        refl_vec = self.__ReflectVector(physical_incident if ideal_air_splitter else ImpVec, SurfNorm)
                        refl_n = N
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
                                refl_n,
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
                        child_skip_surface_once = self.__NsTraceSplitChildSkipSurface(j, face_override)
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
                            child_media_state, child_media_event = self.__NsRayMediaEvent(
                                ray_state,
                                face_override,
                                child_n,
                                child_sign,
                                media_out=Glass if child_label == "transmit" else ray_state.current_medium,
                                diagnostic=incident_state_diagnostic,
                            )
                            self._collect_media_state_override = child_media_event
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
                                N,
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
                            child_prev_n = float(child_media_state.current_index)
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
                                "media_state": child_media_state.to_record(),
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
                                "skip_surface_once": child_skip_surface_once,
                            }
                            queue.append(child_state)
                            if len(queue) + len(results) >= branch_result_limit:
                                branch_truncated = True
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
                    next_ray_state, media_event = self.__NsRayMediaEvent(
                        ray_state,
                        face_override,
                        CurrN,
                        sign,
                        media_out=Glass,
                        terminal_event=terminal_event,
                        diagnostic=incident_state_diagnostic,
                    )
                    self._collect_media_state_override = media_event

                    Name = self.SDT[j].Name
                    RayTraceType = 1
                    ValToSav = [Glass, alpha, RayOrig, pTarget, HitObjSpace,LMNObjSpace, SurfNorm, ImpVec, ResVec, N, CurrN, WaveLength, D, Ord, GrSpa, Name, j, RayTraceType]
                    self.__CollectData(ValToSav)
                    if branch_polarization_xyz is not None:
                        branch_polarization_xyz = self.__TransportPolarizationVector(branch_polarization_xyz, ResVec)
                        branch_jones_p, branch_jones_s = self.__PolarizationVectorToJones(branch_polarization_xyz, ResVec, R)
                    if terminal_event and bool(terminal_event.get("stop", True)):
                        RayOrig = pTarget
                        self.RAY.append(RayOrig)
                        ray_state = next_ray_state
                        termination_reason = str(
                            terminal_event.get("transition", "") or terminal_event.get("kind", "") or "terminal_event"
                        )
                        termination_diagnostic = self.__NsTraceTerminationDiagnostic(
                            termination_reason,
                            RayOrig,
                            ResVec,
                            SIGN,
                            branch_path,
                            count,
                            surface_index=j,
                            extra=str(terminal_event.get("model", "") or ""),
                        )
                        break
                    ray_state = next_ray_state
                    PrevN = float(ray_state.current_index)
                    stl_boundary_continuation = self.__NsTraceBoundaryContinuationMode(j, jj, N, CurrN, sign, face_override)
                    stl_exit_continuation = stl_boundary_continuation == "exit"
                    stl_solid_continuation = stl_boundary_continuation or self.__NsTraceIsStlSolidHit(j, jj)
                    if stl_solid_continuation:
                        skip_surface_once = int(j) if stl_exit_continuation else None
                        if stl_exit_continuation:
                            RayOrig = np.asarray(pTarget, dtype=float)
                        else:
                            RayOrig = self.__NudgeNsBranchOrigin(
                                pTarget,
                                self.__NsPhysicalDirection(ResVec, SIGN),
                            )
                        self.RAY.append(np.asarray(pTarget, dtype=float))
                    elif (
                        isinstance(face_override, dict)
                        and bool(face_override.get("external_reflection"))
                    ):
                        skip_surface_once = None
                        RayOrig = self.__NudgeNsBranchOrigin(
                            pTarget,
                            self.__NsPhysicalDirection(ResVec, SIGN),
                        )
                        self.RAY.append(np.asarray(pTarget, dtype=float))
                    else:
                        RayOrig = self.__NudgeNsBranchOrigin(
                            pTarget,
                            self.__NsPhysicalDirection(ResVec, SIGN),
                        )
                        self.RAY.append(np.asarray(pTarget, dtype=float))

                    if self.__NsTraceIsRepeatedSurfaceStall(
                        a,
                        b,
                        c,
                        PreSurfHit,
                        j,
                        jj,
                        face_override,
                        stl_boundary_continuation,
                    ):
                        termination_reason = "stalled_repeated_surface"
                        termination_diagnostic = self.__NsTraceTerminationDiagnostic(
                            termination_reason,
                            RayOrig,
                            ResVec,
                            SIGN,
                            branch_path,
                            count,
                            surface_index=j,
                        )
                        break

                if self.Glass[j] == 'NULL':
                    termination_reason = "null_surface"
                    termination_diagnostic = self.__NsTraceTerminationDiagnostic(
                        termination_reason,
                        RayOrig,
                        ResVec,
                        SIGN,
                        branch_path,
                        count,
                        surface_index=j,
                    )
                    break

                if self.Glass[j] == 'ABSORB':
                    termination_reason = "absorb"
                    termination_diagnostic = self.__NsTraceTerminationDiagnostic(
                        termination_reason,
                        RayOrig,
                        ResVec,
                        SIGN,
                        branch_path,
                        count,
                        surface_index=j,
                    )
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
            self.__SetNsFinalRayState(ray_state, PrevN)
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
                    termination_reason=termination_reason,
                    termination_diagnostic=termination_diagnostic,
                    final_ray_state=ray_state,
                )
            )

        if queue or branch_truncated:
            branch_tree_diagnostic = (
                "branch_result_limit_reached:"
                f"limit={int(branch_result_limit)}, queued={int(len(queue))}, recorded={int(len(results))}"
            )
            for result in results:
                result["branch_tree_diagnostic"] = branch_tree_diagnostic

        if len(results) == 0:
            self.__CollectDataInit()
            self.val = 0
            self.__EmptyCollect(pS, dC, WaveLength, 0)
            self.__FinalizeNsTraceArrays()
            self.__SetNsFinalRayState(initial_ray_state, initial_prev_n)
            results.append(
                self.__NsTraceSnapshot(
                    0,
                    None,
                    float(self.TT),
                    0.0,
                    "primary",
                    termination_reason="no_branch_results",
                    termination_diagnostic="no non-sequential branch result was produced",
                    final_ray_state=initial_ray_state,
                )
            )

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
        ray_state = self.__InitialNsRayState(PrevN)
        j = 0
        SIGN = 1
        skip_surface_once = None

        while True:
            if (j == self.Targ_Surf):
                break
            timing_started = self.NsTraceTimingStart()
            (a, b, c, PreSurfHit) = self.__NonSequentialChooser(SIGN, RayOrig, ResVec, j, skip_surface_once)
            self.NsTraceTimingRecord("NsTrace.chooser", timing_started)
            skip_surface_once = None

            if (PreSurfHit == 0):
                timing_started = self.NsTraceTimingStart()
                self.__AppendNsTerminalSegment(RayOrig, ResVec, SIGN)
                self.NsTraceTimingRecord("NsTrace.terminal_segment", timing_started)
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
                timing_started = self.NsTraceTimingStart()
                Output = self.INORM.InterNormal(RayOrig, Proto_pTarget, j, jj)
                self.NsTraceTimingRecord("NsTrace.inter_normal", timing_started)
                (SurfHit, SurfNorm, pTarget, GooveVect, HitObjSpace, LMNObjSpace, j) = Output
                if (SurfHit == 0):
                    timing_started = self.NsTraceTimingStart()
                    self.__AppendNsTerminalSegment(RayOrig, ResVec, SIGN)
                    self.NsTraceTimingRecord("NsTrace.terminal_segment", timing_started)
                    break
                vign_pt, vign_k = self.__NsApertureStopVignette(RayOrig, ResVec, SIGN, pTarget)
                if vign_pt is not None:
                    self.__AppendNsTerminalSegment(RayOrig, ResVec, SIGN, stop_point=vign_pt)
                    # bugs/0179: tag this ray's terminal with the BLOCKING stop surface so
                    # the scene bundle reads last_surface=stop (reaches_image=False). Without
                    # it the post-loop empty-collect labels the ray with the chosen downstream
                    # surface (the image), so vignetted rays leak into the relative-illumination
                    # map and wash out the coaxial-LED dark edges.
                    if vign_k is not None:
                        self.val = 0
                        self.__EmptyCollect(np.asarray(vign_pt, dtype=float), ResVec, WaveLength, int(vign_k))
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
                timing_started = self.NsTraceTimingStart()
                Glass, alpha, CurrN, N, Np, face_override = self.__NsTraceHitMedia(
                    j,
                    jj,
                    PrevN,
                    CurrN,
                    alpha,
                    Glass,
                    pTarget,
                    SurfNorm,
                    ray_state,
                )
                self.NsTraceTimingRecord("NsTrace.hit_media", timing_started)
                timing_started = self.NsTraceTimingStart()
                incident_state_diagnostic = self.__NsRayStateIncidentIndexDiagnostic(ray_state, PrevN)
                self.NsTraceTimingRecord("NsTrace.incident_media_diagnostic", timing_started)
                D = GooveVect

                Ord = self.SDT[j].Diff_Ord
                GrSpa = self.SDT[j].Grating_D
                if isinstance(face_override, dict) and bool(face_override.get("force_reflection")):
                    try:
                        R = np.asarray(face_override.get("normal_world"), dtype=float).reshape(3)
                    except Exception:
                        pass
                terminal_event = self.__NsTraceTerminalEvent(j, face_override)
                Secuent = 1 if isinstance(face_override, dict) and bool(face_override.get("force_reflection")) else 0
                ResVec_N, R_N, N_N, Np_N = ResVec, R, N, Np
                timing_started = self.NsTraceTimingStart()
                (ResVec, CurrN, sign ,ang) = self.SDT[j].PHYSICS.calculate(ResVec_N, R_N, N_N, Np_N, D, Ord, GrSpa, self.Wave, Secuent)
                self.NsTraceTimingRecord("NsTrace.physics_calculate", timing_started)
                self.ang = ang
                timing_started = self.NsTraceTimingStart()
                if terminal_event:
                    self.__ApplyNsTerminalEventOverride(terminal_event)
                elif isinstance(face_override, dict) and bool(face_override.get("force_reflection")):
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
                self.NsTraceTimingRecord("NsTrace.interaction_override", timing_started)

                # Coating
                timing_started = self.NsTraceTimingStart()
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
                self.NsTraceTimingRecord("NsTrace.coating_probability", timing_started)

                SIGN = (SIGN * sign)
                timing_started = self.NsTraceTimingStart()
                next_ray_state, media_event = self.__NsRayMediaEvent(
                    ray_state,
                    face_override,
                    CurrN,
                    sign,
                    media_out=Glass,
                    terminal_event=terminal_event,
                    diagnostic=incident_state_diagnostic,
                )
                self._collect_media_state_override = media_event
                self.NsTraceTimingRecord("NsTrace.media_event", timing_started)

                Name = self.SDT[j].Name
                RayTraceType = 1
                ValToSav = [Glass, alpha, RayOrig, pTarget, HitObjSpace,LMNObjSpace, SurfNorm, ImpVec, ResVec, N, CurrN, WaveLength, D, Ord, GrSpa, Name, j, RayTraceType]
                timing_started = self.NsTraceTimingStart()
                self.__CollectData(ValToSav)
                self.NsTraceTimingRecord("NsTrace.collect_data", timing_started)
                if terminal_event and bool(terminal_event.get("stop", True)):
                    RayOrig = pTarget
                    self.RAY.append(RayOrig)
                    ray_state = next_ray_state
                    break
                ray_state = next_ray_state
                PrevN = float(ray_state.current_index)
                stl_boundary_continuation = self.__NsTraceBoundaryContinuationMode(j, jj, N, CurrN, sign, face_override)
                stl_exit_continuation = stl_boundary_continuation == "exit"
                stl_solid_continuation = stl_boundary_continuation or self.__NsTraceIsStlSolidHit(j, jj)
                timing_started = self.NsTraceTimingStart()
                if stl_solid_continuation:
                    skip_surface_once = int(j) if stl_exit_continuation else None
                    if stl_exit_continuation:
                        RayOrig = np.asarray(pTarget, dtype=float)
                    else:
                        RayOrig = self.__NudgeNsBranchOrigin(
                            pTarget,
                            self.__NsPhysicalDirection(ResVec, SIGN),
                        )
                    self.RAY.append(np.asarray(pTarget, dtype=float))
                elif (
                    isinstance(face_override, dict)
                    and bool(face_override.get("external_reflection"))
                ):
                    skip_surface_once = None
                    RayOrig = self.__NudgeNsBranchOrigin(
                        pTarget,
                        self.__NsPhysicalDirection(ResVec, SIGN),
                    )
                    self.RAY.append(np.asarray(pTarget, dtype=float))
                else:
                    RayOrig = self.__NudgeNsBranchOrigin(
                        pTarget,
                        self.__NsPhysicalDirection(ResVec, SIGN),
                    )
                    self.RAY.append(np.asarray(pTarget, dtype=float))
                self.NsTraceTimingRecord("NsTrace.advance_origin", timing_started)

                timing_started = self.NsTraceTimingStart()
                if self.__NsTraceIsRepeatedSurfaceStall(
                    a,
                    b,
                    c,
                    PreSurfHit,
                    j,
                    jj,
                    face_override,
                    stl_boundary_continuation,
                ):
                    break
                self.NsTraceTimingRecord("NsTrace.stall_check", timing_started)

            if self.Glass[j] == 'NULL':
                ang = 0
                ValToSav = [Glass, alpha, RayOrig, pTarget, HitObjSpace, SurfNorm, ImpVec, ResVec, PrevN, CurrN, WaveLength, D, Ord, GrSpa, Name, j, RayTraceType, ang]
                self.__CollectData(ValToSav)

            if self.Glass[j] == 'ABSORB':
                break

            count = (count + 1)
        self.__SetNsFinalRayState(ray_state, PrevN)
        if (len(self.GLASS) == 0):
            self.__CollectDataInit()
            self.val = 0
            self.__EmptyCollect(pS, dC, WaveLength, j)
            self.__SetNsFinalRayState(ray_state, PrevN)
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
