
import numpy as np
import pyvista as pv

class raykeeper():
    """raykeeper.
    """


    def __init__(self, System):
        """__init__.

        Parameters
        ----------
        System :
            System
        """
        self.SYSTEM = System
        self.clean()

    def valid(self):
        """valid.
        """
        z = np.argwhere((self.vld == 1))
        return z

    def _push_trace_snapshot(self, data, source_ray_index=None):
        """Append one traced branch/result snapshot to this raykeeper."""
        self.nelements = self.SYSTEM.n
        surface_arr = np.asarray(data.get('SURFACE', []))
        is_valid = bool(data.get('val', 1) == 1 and surface_arr.size > 0)

        name_arr = np.asarray(data.get('NAME', []))
        glass_arr = np.asarray(data.get('GLASS', []))
        s_xyz_arr = np.asarray(data.get('S_XYZ', []))
        t_xyz_arr = np.asarray(data.get('T_XYZ', []))
        xyz_arr = np.asarray(data.get('XYZ', []))
        ost_xyz_arr = np.asarray(data.get('OST_XYZ', []))
        ost_lmn_arr = np.asarray(data.get('OST_LMN', []))
        s_lmn_arr = np.asarray(data.get('S_LMN', []))
        lmn_arr = np.asarray(data.get('LMN', []))
        r_lmn_arr = np.asarray(data.get('R_LMN', []))
        n0_arr = np.asarray(data.get('N0', []))
        n1_arr = np.asarray(data.get('N1', []))
        wav_val = np.asarray(data.get('WAV', data.get('Wave', getattr(self.SYSTEM, 'Wave', 0.0))))
        g_lmn_arr = np.asarray(data.get('G_LMN', []))
        order_arr = np.asarray(data.get('ORDER', []))
        grating_arr = np.asarray(data.get('GRATING', []))
        dist_arr = np.asarray(data.get('DISTANCE', []))
        op_arr = np.asarray(data.get('OP', []))
        top_s_arr = np.asarray(data.get('TOP_S', []))
        top_val = np.asarray(data.get('TOP', 0.0))
        alpha_arr = np.asarray(data.get('ALPHA', []))
        bulk_trans_arr = np.asarray(data.get('BULK_TRANS', []))
        rp_arr = np.asarray(data.get('RP', []))
        rs_arr = np.asarray(data.get('RS', []))
        tp_arr = np.asarray(data.get('TP', []))
        ts_arr = np.asarray(data.get('TS', []))
        ttbe_arr = np.asarray(data.get('TTBE', []))
        tt_val = np.asarray(data.get('TT', 0.0))
        ray_arr = np.asarray(data.get('RAY', []))

        if is_valid:
            self.vld = np.append(self.vld, 1)
            self.valid_vld = np.append(self.vld, 0)
            self.valid_SURFACE.append(surface_arr)
            self.valid_NAME.append(name_arr)
            self.valid_GLASS.append(glass_arr)
            self.valid_S_XYZ.append(s_xyz_arr)
            self.valid_T_XYZ.append(t_xyz_arr)
            self.valid_XYZ.append(xyz_arr)
            self.valid_OST_XYZ.append(ost_xyz_arr)
            self.valid_OST_LMN.append(ost_lmn_arr)
            self.valid_S_LMN.append(s_lmn_arr)
            self.valid_LMN.append(lmn_arr)
            self.valid_R_LMN.append(r_lmn_arr)
            self.valid_N0.append(n0_arr)
            self.valid_N1.append(n1_arr)
            self.valid_WAV.append(wav_val)
            self.valid_G_LMN.append(g_lmn_arr)
            self.valid_ORDER.append(order_arr)
            self.valid_GRATING.append(grating_arr)
            self.valid_DISTANCE.append(dist_arr)
            self.valid_OP.append(op_arr)
            self.valid_TOP_S.append(top_s_arr)
            self.valid_TOP.append(top_val)
            self.valid_ALPHA.append(alpha_arr)
            self.valid_BULK_TRANS.append(bulk_trans_arr)
            self.valid_RP.append(rp_arr)
            self.valid_RS.append(rs_arr)
            self.valid_TP.append(tp_arr)
            self.valid_TS.append(ts_arr)
            self.valid_TTBE.append(ttbe_arr)
            self.valid_TT.append(tt_val)
        else:
            self.vld = np.append(self.vld, 0)
            self.invalid_vld = np.append(self.vld, 0)
            self.invalid_SURFACE.append(surface_arr)
            self.invalid_NAME.append(name_arr)
            self.invalid_GLASS.append(glass_arr)
            self.invalid_S_XYZ.append(s_xyz_arr)
            self.invalid_T_XYZ.append(t_xyz_arr)
            self.invalid_XYZ.append(xyz_arr)
            self.invalid_OST_XYZ.append(ost_xyz_arr)
            self.invalid_OST_LMN.append(ost_lmn_arr)
            self.invalid_S_LMN.append(s_lmn_arr)
            self.invalid_LMN.append(lmn_arr)
            self.invalid_R_LMN.append(r_lmn_arr)
            self.invalid_N0.append(n0_arr)
            self.invalid_N1.append(n1_arr)
            self.invalid_WAV.append(wav_val)
            self.invalid_G_LMN.append(g_lmn_arr)
            self.invalid_ORDER.append(order_arr)
            self.invalid_GRATING.append(grating_arr)
            self.invalid_DISTANCE.append(dist_arr)
            self.invalid_OP.append(op_arr)
            self.invalid_TOP_S.append(top_s_arr)
            self.invalid_TOP.append(top_val)
            self.invalid_ALPHA.append(alpha_arr)
            self.invalid_BULK_TRANS.append(bulk_trans_arr)
            self.invalid_RP.append(rp_arr)
            self.invalid_RS.append(rs_arr)
            self.invalid_TP.append(tp_arr)
            self.invalid_TS.append(ts_arr)
            self.invalid_TTBE.append(ttbe_arr)
            self.invalid_TT.append(tt_val)

        self.nrays = (self.nrays + 1)
        self.RayWave.append(data.get('Wave', getattr(self.SYSTEM, 'Wave', wav_val)))
        self.CC.append(ray_arr)
        self.SURFACE.append(surface_arr)
        self.NAME.append(name_arr)
        self.GLASS.append(glass_arr)
        self.S_XYZ.append(s_xyz_arr)
        self.T_XYZ.append(t_xyz_arr)
        self.XYZ.append(xyz_arr)
        self.OST_XYZ.append(ost_xyz_arr)
        self.OST_LMN.append(ost_lmn_arr)
        self.S_LMN.append(s_lmn_arr)
        self.LMN.append(lmn_arr)
        self.R_LMN.append(r_lmn_arr)
        self.N0.append(n0_arr)
        self.N1.append(n1_arr)
        self.WAV.append(wav_val)
        self.G_LMN.append(g_lmn_arr)
        self.ORDER.append(order_arr)
        self.GRATING.append(grating_arr)
        self.DISTANCE.append(dist_arr)
        self.OP.append(op_arr)
        self.TOP_S.append(top_s_arr)
        self.TOP.append(top_val)
        self.ALPHA.append(alpha_arr)
        self.BULK_TRANS.append(bulk_trans_arr)
        self.RP.append(rp_arr)
        self.RS.append(rs_arr)
        self.TP.append(tp_arr)
        self.TS.append(ts_arr)
        self.TTBE.append(ttbe_arr)
        self.TT.append(tt_val)
        self.SOURCE_RAY.append(np.asarray(source_ray_index if source_ray_index is not None else data.get('source_ray_index', -1)))
        self.BRANCH_ID.append(np.asarray(data.get('branch_id', 0)))
        parent_branch = data.get('parent_branch_id', -1)
        self.PARENT_BRANCH_ID.append(np.asarray(-1 if parent_branch is None else parent_branch))
        self.BRANCH_POWER.append(np.asarray(data.get('branch_power', float(np.asarray(tt_val).ravel()[-1]) if np.asarray(tt_val).size else 0.0)))
        self.BRANCH_PHASE.append(np.asarray(data.get('branch_phase_deg', 0.0)))
        self.BRANCH_LABEL.append(np.asarray(data.get('branch_label', 'primary')))

    def _push_branch_results(self, branch_results):
        source_ray_index = self._launch_count
        for result in branch_results:
            self._push_trace_snapshot(result, source_ray_index=source_ray_index)
        self._launch_count += 1

    def push(self):
        """push.
        """
        branch_results = getattr(self.SYSTEM, "NS_BRANCH_RESULTS", None)
        if branch_results:
            self._push_branch_results(branch_results)
            self.SYSTEM.NS_BRANCH_RESULTS = []
            return

        self.nelements = self.SYSTEM.n
        if (self.SYSTEM.val == 0):
            self.invalid_vld = np.append(self.vld, 0)
            self.invalid_SURFACE.append(np.asarray(self.SYSTEM.SURFACE))
            self.invalid_NAME.append(np.asarray(self.SYSTEM.NAME))
            self.invalid_GLASS.append(np.asarray(self.SYSTEM.GLASS))
            self.invalid_S_XYZ.append(np.asarray(self.SYSTEM.S_XYZ))
            self.invalid_T_XYZ.append(np.asarray(self.SYSTEM.T_XYZ))
            self.invalid_XYZ.append(np.asarray(self.SYSTEM.XYZ))

            lst = self.SYSTEM.OST_XYZ
            ll = filter(None, lst)
            self.invalid_OST_XYZ.append(np.asarray(ll))
            self.invalid_OST_LMN.append(np.asarray(self.SYSTEM.OST_LMN))
            self.invalid_S_LMN.append(np.asarray(self.SYSTEM.S_LMN))
            self.invalid_LMN.append(np.asarray(self.SYSTEM.LMN))
            self.invalid_R_LMN.append(np.asarray(self.SYSTEM.R_LMN))
            self.invalid_N0.append(np.asarray(self.SYSTEM.N0))
            self.invalid_N1.append(np.asarray(self.SYSTEM.N1))
            self.invalid_WAV.append(np.asarray(self.SYSTEM.WAV))
            self.invalid_G_LMN.append(np.asarray(self.SYSTEM.G_LMN))
            self.invalid_ORDER.append(np.asarray(self.SYSTEM.ORDER))
            self.invalid_GRATING.append(np.asarray(self.SYSTEM.GRATING))
            self.invalid_DISTANCE.append(np.asarray(self.SYSTEM.DISTANCE))
            self.invalid_OP.append(np.asarray(self.SYSTEM.OP))
            self.invalid_TOP_S.append(np.asarray(self.SYSTEM.TOP_S))
            self.invalid_TOP.append(np.asarray(self.SYSTEM.TOP))
            lst = self.SYSTEM.ALPHA
            ll = filter(None, lst)
            self.invalid_ALPHA.append(np.asarray(ll))
            self.invalid_BULK_TRANS.append(np.asarray(self.SYSTEM.BULK_TRANS))
            self.invalid_RP.append(np.asarray(self.SYSTEM.RP))
            self.invalid_RS.append(np.asarray(self.SYSTEM.RS))
            self.invalid_TP.append(np.asarray(self.SYSTEM.TP))
            self.invalid_TS.append(np.asarray(self.SYSTEM.TS))
            self.invalid_TTBE.append(np.asarray(self.SYSTEM.TTBE))
            self.invalid_TT.append(np.asarray(self.SYSTEM.TT))
        else:
            self.vld = np.append(self.vld, 1)
            self.valid_vld = np.append(self.vld, 0)
            self.valid_SURFACE.append(np.asarray(self.SYSTEM.SURFACE))
            self.valid_NAME.append(np.asarray(self.SYSTEM.NAME))
            self.valid_GLASS.append(np.asarray(self.SYSTEM.GLASS))
            self.valid_S_XYZ.append(np.asarray(self.SYSTEM.S_XYZ))
            self.valid_T_XYZ.append(np.asarray(self.SYSTEM.T_XYZ))
            self.valid_XYZ.append(np.asarray(self.SYSTEM.XYZ))
            self.valid_OST_XYZ.append(np.asarray(self.SYSTEM.OST_XYZ))
            self.valid_OST_LMN.append(np.asarray(self.SYSTEM.OST_LMN))
            self.valid_S_LMN.append(np.asarray(self.SYSTEM.S_LMN))
            self.valid_LMN.append(np.asarray(self.SYSTEM.LMN))
            self.valid_R_LMN.append(np.asarray(self.SYSTEM.R_LMN))
            self.valid_N0.append(np.asarray(self.SYSTEM.N0))
            self.valid_N1.append(np.asarray(self.SYSTEM.N1))
            self.valid_WAV.append(np.asarray(self.SYSTEM.WAV))
            self.valid_G_LMN.append(np.asarray(self.SYSTEM.G_LMN))
            self.valid_ORDER.append(np.asarray(self.SYSTEM.ORDER))
            self.valid_GRATING.append(np.asarray(self.SYSTEM.GRATING))
            self.valid_DISTANCE.append(np.asarray(self.SYSTEM.DISTANCE))
            self.valid_OP.append(np.asarray(self.SYSTEM.OP))
            self.valid_TOP_S.append(np.asarray(self.SYSTEM.TOP_S))
            self.valid_TOP.append(np.asarray(self.SYSTEM.TOP))
            self.valid_ALPHA.append(np.asarray(self.SYSTEM.ALPHA))
            self.valid_BULK_TRANS.append(np.asarray(self.SYSTEM.BULK_TRANS))
            self.valid_RP.append(np.asarray(self.SYSTEM.RP))
            self.valid_RS.append(np.asarray(self.SYSTEM.RS))
            self.valid_TP.append(np.asarray(self.SYSTEM.TP))
            self.valid_TS.append(np.asarray(self.SYSTEM.TS))
            self.valid_TTBE.append(np.asarray(self.SYSTEM.TTBE))
            self.valid_TT.append(np.asarray(self.SYSTEM.TT))
        self.nrays = (self.nrays + 1)


        self.RayWave.append(self.SYSTEM.Wave)
        self.CC.append(self.SYSTEM.ray_SurfHits)



        self.SURFACE.append(np.asarray(self.SYSTEM.SURFACE))
        self.NAME.append(np.asarray(self.SYSTEM.NAME))
        self.GLASS.append(np.asarray(self.SYSTEM.GLASS))
        self.S_XYZ.append(np.asarray(self.SYSTEM.S_XYZ))
        self.T_XYZ.append(np.asarray(self.SYSTEM.T_XYZ))
        self.XYZ.append(np.asarray(self.SYSTEM.XYZ))

        # revisar
        lst = self.SYSTEM.OST_XYZ
        ll = filter(None, lst)
        self.OST_XYZ.append(np.asarray(ll))

        # self.OST_XYZ.append(np.asarray(self.SYSTEM.OST_XYZ))
        self.OST_LMN.append(np.asarray(self.SYSTEM.OST_LMN))
        self.S_LMN.append(np.asarray(self.SYSTEM.S_LMN))
        self.LMN.append(np.asarray(self.SYSTEM.LMN))
        self.R_LMN.append(np.asarray(self.SYSTEM.R_LMN))
        self.N0.append(np.asarray(self.SYSTEM.N0))
        self.N1.append(np.asarray(self.SYSTEM.N1))
        self.WAV.append(np.asarray(self.SYSTEM.WAV))
        self.G_LMN.append(np.asarray(self.SYSTEM.G_LMN))
        self.ORDER.append(np.asarray(self.SYSTEM.ORDER))
        self.GRATING.append(np.asarray(self.SYSTEM.GRATING))
        self.DISTANCE.append(np.asarray(self.SYSTEM.DISTANCE))
        self.OP.append(np.asarray(self.SYSTEM.OP))
        self.TOP_S.append(np.asarray(self.SYSTEM.TOP_S))
        self.TOP.append(np.asarray(self.SYSTEM.TOP))
        lst = self.SYSTEM.ALPHA
        ll = filter(None, lst)
        self.ALPHA.append(np.asarray(ll))
        self.BULK_TRANS.append(np.asarray(self.SYSTEM.BULK_TRANS))
        self.RP.append(np.asarray(self.SYSTEM.RP))
        self.RS.append(np.asarray(self.SYSTEM.RS))
        self.TP.append(np.asarray(self.SYSTEM.TP))
        self.TS.append(np.asarray(self.SYSTEM.TS))
        self.TTBE.append(np.asarray(self.SYSTEM.TTBE))
        self.TT.append(np.asarray(self.SYSTEM.TT))
        self.SOURCE_RAY.append(np.asarray(self._launch_count))
        self.BRANCH_ID.append(np.asarray(0))
        self.PARENT_BRANCH_ID.append(np.asarray(-1))
        self.BRANCH_POWER.append(np.asarray(float(np.asarray(self.SYSTEM.TT).ravel()[-1]) if np.asarray(self.SYSTEM.TT).size else 0.0))
        self.BRANCH_PHASE.append(np.asarray(0.0))
        self.BRANCH_LABEL.append(np.asarray("primary"))
        self._launch_count += 1

    def clean(self):
        """clean.
        """
        self.vld = np.asarray([])
        self.nrays = 0
        self.RayWave = []
        self.CC =[]
        self.SURFACE = []
        self.NAME = []
        self.GLASS = []
        self.S_XYZ = []
        self.T_XYZ = []
        self.XYZ = []
        self.OST_XYZ = []
        self.OST_LMN = []
        self.S_LMN = []
        self.LMN = []
        self.R_LMN = []
        self.N0 = []
        self.N1 = []
        self.WAV = []
        self.G_LMN = []
        self.ORDER = []
        self.GRATING = []
        self.DISTANCE = []
        self.OP = []
        self.TOP_S = []
        self.TOP = []
        self.ALPHA = []
        self.BULK_TRANS = []
        self.RP = []
        self.RS = []
        self.TP = []
        self.TS = []
        self.TTBE = []
        self.TT = []
        self.SOURCE_RAY = []
        self.BRANCH_ID = []
        self.PARENT_BRANCH_ID = []
        self.BRANCH_POWER = []
        self.BRANCH_PHASE = []
        self.BRANCH_LABEL = []
        self._launch_count = 0
        self.valid_RayWave = []
        self.valid_CCC = pv.MultiBlock()
        self.valid_SURFACE = []
        self.valid_NAME = []
        self.valid_GLASS = []
        self.valid_S_XYZ = []
        self.valid_T_XYZ = []
        self.valid_XYZ = []
        self.valid_OST_XYZ = []
        self.valid_OST_LMN = []
        self.valid_S_LMN = []
        self.valid_LMN = []
        self.valid_R_LMN = []
        self.valid_N0 = []
        self.valid_N1 = []
        self.valid_WAV = []
        self.valid_G_LMN = []
        self.valid_ORDER = []
        self.valid_GRATING = []
        self.valid_DISTANCE = []
        self.valid_OP = []
        self.valid_TOP_S = []
        self.valid_TOP = []
        self.valid_ALPHA = []
        self.valid_BULK_TRANS = []
        self.valid_RP = []
        self.valid_RS = []
        self.valid_TP = []
        self.valid_TS = []
        self.valid_TTBE = []
        self.valid_TT = []
        self.invalid_RayWave = []
        self.invalid_CCC = pv.MultiBlock()
        self.invalid_SURFACE = []
        self.invalid_NAME = []
        self.invalid_GLASS = []
        self.invalid_S_XYZ = []
        self.invalid_T_XYZ = []
        self.invalid_XYZ = []
        self.invalid_OST_XYZ = []
        self.invalid_OST_LMN = []
        self.invalid_S_LMN = []
        self.invalid_LMN = []
        self.invalid_R_LMN = []
        self.invalid_N0 = []
        self.invalid_N1 = []
        self.invalid_WAV = []
        self.invalid_G_LMN = []
        self.invalid_ORDER = []
        self.invalid_GRATING = []
        self.invalid_DISTANCE = []
        self.invalid_OP = []
        self.invalid_TOP_S = []
        self.invalid_TOP = []
        self.invalid_ALPHA = []
        self.invalid_BULK_TRANS = []
        self.invalid_RP = []
        self.invalid_RS = []
        self.invalid_TP = []
        self.invalid_TS = []
        self.invalid_TTBE = []
        self.invalid_TT = []

    def batch_push(self, batch_results, batch_active, wave):
        """Push all batch ray-trace results at once.

        Bypasses the per-ray ``_apply_batch_result`` → ``push()`` round-trip,
        directly reading from the batch result dicts and writing into the
        raykeeper lists.  This eliminates ~60 attribute accesses per ray
        compared to the old path.

        Parameters
        ----------
        batch_results : list[dict] — per-ray result dicts from ``BatchTrace``
        batch_active : (N,) bool array — ``True`` for rays that reached the image
        wave : float — wavelength
        """
        self.nelements = self.SYSTEM.n
        N_rays = len(batch_results)

        for i in range(N_rays):
            d = batch_results[i]
            is_valid = bool(batch_active[i]) and d.get('val', 1) == 1 and len(d['SURFACE']) > 0
            n_surf = len(d['SURFACE'])

            # Build numpy arrays from the batch dict
            surface_arr = np.asarray(d['SURFACE'])
            name_arr = np.asarray(d['NAME'])
            glass_arr = np.asarray(d['GLASS'])
            s_xyz_arr = np.asarray(d['S_XYZ']) if d['S_XYZ'] else np.empty((0, 3))
            t_xyz_arr = np.asarray(d['T_XYZ']) if d['T_XYZ'] else np.empty((0, 3))
            xyz_arr = np.asarray(d['XYZ'])
            ost_xyz_arr = np.asarray(d['OST_XYZ'])
            ost_lmn_arr = np.asarray(d['OST_LMN']) if d['OST_LMN'] else np.empty((0, 3))
            s_lmn_arr = np.asarray(d['S_LMN']) if d['S_LMN'] else np.empty((0, 3))
            lmn_arr = np.asarray(d['LMN']) if d['LMN'] else np.empty((0, 3))
            r_lmn_arr = np.asarray(d['R_LMN']) if d['R_LMN'] else np.empty((0, 3))
            n0_arr = np.asarray(d['N0'])
            n1_arr = np.asarray(d['N1'])
            dist_arr = np.asarray(d['DISTANCE'])
            op_arr = np.asarray(d['OP'])
            top_s_arr = np.asarray(d['TOP_S'])
            top_val = np.asarray(d['TOP'])
            wav_val = np.asarray(wave)

            # Placeholders that BatchTrace doesn't compute
            g_lmn_arr = np.asarray([[0, 1, 0]] * n_surf) if n_surf > 0 else np.empty((0, 3))
            order_arr = np.zeros(n_surf)
            grating_arr = np.zeros(n_surf)
            alpha_arr = np.zeros(n_surf + 2)
            bulk_trans_arr = np.asarray([])
            rp_arr = np.zeros(n_surf)
            rs_arr = np.zeros(n_surf)
            tp_arr = np.ones(n_surf)
            ts_arr = np.ones(n_surf)
            ttbe_arr = np.ones(n_surf)
            tt_val = np.asarray(1.0)

            ray_list = d['RAY']
            ray_arr = np.asarray(ray_list) if len(ray_list) > 0 else np.empty((0, 3))

            if is_valid:
                self.vld = np.append(self.vld, 1)
                self.valid_SURFACE.append(surface_arr)
                self.valid_NAME.append(name_arr)
                self.valid_GLASS.append(glass_arr)
                self.valid_S_XYZ.append(s_xyz_arr)
                self.valid_T_XYZ.append(t_xyz_arr)
                self.valid_XYZ.append(xyz_arr)
                self.valid_OST_XYZ.append(ost_xyz_arr)
                self.valid_OST_LMN.append(ost_lmn_arr)
                self.valid_S_LMN.append(s_lmn_arr)
                self.valid_LMN.append(lmn_arr)
                self.valid_R_LMN.append(r_lmn_arr)
                self.valid_N0.append(n0_arr)
                self.valid_N1.append(n1_arr)
                self.valid_WAV.append(wav_val)
                self.valid_G_LMN.append(g_lmn_arr)
                self.valid_ORDER.append(order_arr)
                self.valid_GRATING.append(grating_arr)
                self.valid_DISTANCE.append(dist_arr)
                self.valid_OP.append(op_arr)
                self.valid_TOP_S.append(top_s_arr)
                self.valid_TOP.append(top_val)
                self.valid_ALPHA.append(alpha_arr)
                self.valid_BULK_TRANS.append(bulk_trans_arr)
                self.valid_RP.append(rp_arr)
                self.valid_RS.append(rs_arr)
                self.valid_TP.append(tp_arr)
                self.valid_TS.append(ts_arr)
                self.valid_TTBE.append(ttbe_arr)
                self.valid_TT.append(tt_val)
            else:
                self.invalid_SURFACE.append(surface_arr)
                self.invalid_NAME.append(name_arr)
                self.invalid_GLASS.append(glass_arr)
                self.invalid_S_XYZ.append(s_xyz_arr)
                self.invalid_T_XYZ.append(t_xyz_arr)
                self.invalid_XYZ.append(xyz_arr)
                self.invalid_OST_XYZ.append(ost_xyz_arr)
                self.invalid_OST_LMN.append(ost_lmn_arr)
                self.invalid_S_LMN.append(s_lmn_arr)
                self.invalid_LMN.append(lmn_arr)
                self.invalid_R_LMN.append(r_lmn_arr)
                self.invalid_N0.append(n0_arr)
                self.invalid_N1.append(n1_arr)
                self.invalid_WAV.append(wav_val)
                self.invalid_G_LMN.append(g_lmn_arr)
                self.invalid_ORDER.append(order_arr)
                self.invalid_GRATING.append(grating_arr)
                self.invalid_DISTANCE.append(dist_arr)
                self.invalid_OP.append(op_arr)
                self.invalid_TOP_S.append(top_s_arr)
                self.invalid_TOP.append(top_val)
                self.invalid_ALPHA.append(alpha_arr)
                self.invalid_BULK_TRANS.append(bulk_trans_arr)
                self.invalid_RP.append(rp_arr)
                self.invalid_RS.append(rs_arr)
                self.invalid_TP.append(tp_arr)
                self.invalid_TS.append(ts_arr)
                self.invalid_TTBE.append(ttbe_arr)
                self.invalid_TT.append(tt_val)

            # General lists (always appended)
            self.nrays += 1
            self.RayWave.append(wave)
            self.CC.append(ray_arr)
            self.SURFACE.append(surface_arr)
            self.NAME.append(name_arr)
            self.GLASS.append(glass_arr)
            self.S_XYZ.append(s_xyz_arr)
            self.T_XYZ.append(t_xyz_arr)
            self.XYZ.append(xyz_arr)
            self.OST_XYZ.append(ost_xyz_arr)
            self.OST_LMN.append(ost_lmn_arr)
            self.S_LMN.append(s_lmn_arr)
            self.LMN.append(lmn_arr)
            self.R_LMN.append(r_lmn_arr)
            self.N0.append(n0_arr)
            self.N1.append(n1_arr)
            self.WAV.append(wav_val)
            self.G_LMN.append(g_lmn_arr)
            self.ORDER.append(order_arr)
            self.GRATING.append(grating_arr)
            self.DISTANCE.append(dist_arr)
            self.OP.append(op_arr)
            self.TOP_S.append(top_s_arr)
            self.TOP.append(top_val)
            self.ALPHA.append(alpha_arr)
            self.BULK_TRANS.append(bulk_trans_arr)
            self.RP.append(rp_arr)
            self.RS.append(rs_arr)
            self.TP.append(tp_arr)
            self.TS.append(ts_arr)
            self.TTBE.append(ttbe_arr)
            self.TT.append(tt_val)

    def pick(self, N_ELEMENT=(- 1), coordinates = "global"):
        """pick.

        Parameters
        ----------
        N_ELEMENT :
            N_ELEMENT

            coordinates = "global" or "local"
        """

        gls = self.SYSTEM.SDT[N_ELEMENT].Glass
        if gls == "NULL":
            print("NULL surface has been chosen, the return values correspond to those of the previous surface")

        self.numsup = (self.nelements - 1)

        if coordinates == "global":
            self.xyz = self.valid_XYZ
            self.lmn = self.valid_LMN
        else:
            self.xyz = self.valid_OST_XYZ
            self.lmn = self.valid_OST_LMN

        self.s = self.valid_SURFACE
        if ((N_ELEMENT < 0) or (N_ELEMENT > self.numsup)):
            N_ELEMENT = self.numsup
        else:
            N_ELEMENT = N_ELEMENT
        # AA = []
        BB = []
        for k in self.s:
            aa = np.argwhere((k == N_ELEMENT))
            aa = np.squeeze(aa)
            # print(aa)
            # AA.append(aa)
            BB.append(np.size(aa))
        # AA = np.asarray(AA)
        BB = np.asarray(BB)
        if (N_ELEMENT != 0):
            BB = np.argwhere((BB == 1))
        else:
            BB = np.argwhere((BB == 0))
        X = []
        Y = []
        Z = []
        L = []
        M = []
        N = []
        for c in BB:
            for d in c:
                ray0 = self.xyz[d]

                [x1, y1, z1] = ray0[N_ELEMENT]
                X.append(x1)
                Y.append(y1)
                Z.append(z1)
                ray1 = self.lmn[d]
                if (N_ELEMENT != 0):
                    el = (N_ELEMENT - 1)
                else:
                    el = 0
                [l1, m1, n1] = ray1[el]
                L.append(l1)
                M.append(m1)
                N.append(n1)
        return (np.asarray(X), np.asarray(Y), np.asarray(Z), np.asarray(L), np.asarray(M), np.asarray(N))
