def _metadata_for_ray(source_metadata, index, source, direction, wavelength):
    metadata = {}
    if source_metadata is not None:
        try:
            candidate = source_metadata[index]
            if isinstance(candidate, dict):
                metadata.update(candidate)
        except Exception:
            pass
    metadata.setdefault("source_xyz", source)
    metadata.setdefault("source_lmn", direction)
    metadata.setdefault("source_wavelength", wavelength)
    return metadata


def TraceLoop(x, y, z, L, M, N, W, Container, clean = 1, source_metadata=None):
    """TraceLoop.

    Parameters
    ----------
    x :
        x
    y :
        y
    z :
        z
    L :
        L
    M :
        M
    N :
        N
    W :
        W
    Container :
        Container
    """
    if clean ==1:
        Container.clean()
    System = Container.SYSTEM
    for i in range(0, len(x)):
        pSource_0 = [x[i], y[i], z[i]]
        dCos = [L[i], M[i], N[i]]
        if hasattr(Container, "set_launch_metadata"):
            Container.set_launch_metadata(**_metadata_for_ray(source_metadata, i, pSource_0, dCos, W))
        System.Trace(pSource_0, dCos, W)
        Container.push()
    return 0

def BatchTraceLoop(x, y, z, L, M, N, W, Container, clean=1, min_batch=10, source_metadata=None):
    """GPU-accelerated batch ray trace.

    Falls back to scalar :func:`TraceLoop` when the ray count is below
    *min_batch* (GPU transfer overhead would dominate).

    Parameters are identical to :func:`TraceLoop`.
    """
    import numpy as np
    n_rays = len(x)
    if n_rays < min_batch:
        return TraceLoop(x, y, z, L, M, N, W, Container, clean, source_metadata=source_metadata)

    if clean == 1:
        Container.clean()
    System = Container.SYSTEM

    pSources = np.column_stack([x, y, z])
    dCosines = np.column_stack([L, M, N])
    metadata = [
        _metadata_for_ray(source_metadata, i, pSources[i].tolist(), dCosines[i].tolist(), W)
        for i in range(n_rays)
    ]
    try:
        System.BatchTrace(pSources, dCosines, W)
    except Exception:
        return TraceLoop(x, y, z, L, M, N, W, Container, clean=clean, source_metadata=source_metadata)

    Container.batch_push(System._batch_results, System._batch_active, W, source_metadata=metadata)
    return 0


def NsTraceLoop(x, y, z, L, M, N, W, Container, clean = 1, source_metadata=None):
    """NsTraceLoop.

    Parameters
    ----------
    x :
        x
    y :
        y
    z :
        z
    L :
        L
    M :
        M
    N :
        N
    W :
        W
    Container :
        Container
    """
    if clean ==1:
        Container.clean()
    System = Container.SYSTEM
    for i in range(0, len(x)):
        pSource_0 = [x[i], y[i], z[i]]
        dCos = [L[i], M[i], N[i]]
        if hasattr(Container, "set_launch_metadata"):
            Container.set_launch_metadata(**_metadata_for_ray(source_metadata, i, pSource_0, dCos, W))
        trace_started = System.NsTraceTimingStart() if hasattr(System, "NsTraceTimingStart") else None
        System.NsTrace(pSource_0, dCos, W)
        if hasattr(System, "NsTraceTimingRecord"):
            System.NsTraceTimingRecord("system.NsTrace", trace_started)
        push_started = System.NsTraceTimingStart() if hasattr(System, "NsTraceTimingStart") else None
        Container.push()
        if hasattr(System, "NsTraceTimingRecord"):
            System.NsTraceTimingRecord("raykeeper.push", push_started)
    return 0
