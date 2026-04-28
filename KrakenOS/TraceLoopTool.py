def TraceLoop(x, y, z, L, M, N, W, Container, clean = 1):
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
        System.Trace(pSource_0, dCos, W)
        Container.push()
    return 0

def BatchTraceLoop(x, y, z, L, M, N, W, Container, clean=1, min_batch=10):
    """GPU-accelerated batch ray trace.

    Falls back to scalar :func:`TraceLoop` when the ray count is below
    *min_batch* (GPU transfer overhead would dominate).

    Parameters are identical to :func:`TraceLoop`.
    """
    import numpy as np
    n_rays = len(x)
    if n_rays < min_batch:
        return TraceLoop(x, y, z, L, M, N, W, Container, clean)

    if clean == 1:
        Container.clean()
    System = Container.SYSTEM

    pSources = np.column_stack([x, y, z])
    dCosines = np.column_stack([L, M, N])
    try:
        System.BatchTrace(pSources, dCosines, W)
    except Exception:
        return TraceLoop(x, y, z, L, M, N, W, Container, clean=clean)

    Container.batch_push(System._batch_results, System._batch_active, W)
    return 0


def NsTraceLoop(x, y, z, L, M, N, W, Container, clean = 1):
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
        System.NsTrace(pSource_0, dCos, W)
        Container.push()
    return 0
