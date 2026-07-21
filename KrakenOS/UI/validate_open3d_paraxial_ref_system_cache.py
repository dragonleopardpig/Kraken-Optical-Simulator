"""Display-free guard for bugs/0387 -- the read-only pupil-reference system-build cache.

The pupil first-order reference (bugs/0094) rebuilds the SAME full-scene system WITH 3D
solids several times per folded trace (~3.3s of the swap freeze). That build is READ-ONLY
(PupilCalc, never NS-traces; passes apply_optical_solid_output_ports=False), so it is
cacheable by exact specs content. This guard pins the cache KEY (collision-free, None on
unpicklable/unserialisable specs so a hash collision can never return a wrong system) and
the bounded store/evict. The end-to-end SAFETY invariant -- the traced output is
byte-identical with vs without the cache -- is verified on the real scene in
`scratchpad/az85_cache.py` (pickle-equal payload); it needs a full trace so it is not
part of this portable guard.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_paraxial_ref_system_cache
"""

from __future__ import annotations


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    import KrakenOS.UI.layout_editor as LE

    key = LE._paraxial_ref_system_cache_key

    specs_a = [{"surface": "Standard", "rc": 0.0, "thickness": 10.0, "diameter": 25.0}]
    specs_b = [{"surface": "Standard", "rc": 0.0, "thickness": 11.0, "diameter": 25.0}]

    # deterministic + order-independent within a spec dict; same specs -> same key
    ka1 = key(specs_a, 1)
    ka2 = key([{"diameter": 25.0, "thickness": 10.0, "rc": 0.0, "surface": "Standard"}], 1)
    if ka1 is None:
        failures.append("key: a clean spec must produce a key")
    if ka1 != ka2:
        failures.append("key: the key must be independent of dict key order (sort_keys)")

    # different specs / different build -> different key
    if key(specs_a, 1) == key(specs_b, 1):
        failures.append("key: different thickness must give a different key")
    if key(specs_a, 1) == key(specs_a, 0):
        failures.append("key: different build flag must give a different key")

    # unserialisable specs -> None (NEVER a colliding/garbage key)
    class _Weird:
        pass

    if key([{"surface": "Standard", "advanced": {"obj": _Weird()}}], 1) is not None:
        failures.append("key: unserialisable specs must return None (never risk a wrong cached system)")

    # bounded store + LRU-ish eviction
    saved_cache = dict(LE._PARAXIAL_REF_SYSTEM_CACHE)
    saved_order = list(LE._PARAXIAL_REF_SYSTEM_CACHE_ORDER)
    try:
        LE._PARAXIAL_REF_SYSTEM_CACHE.clear()
        LE._PARAXIAL_REF_SYSTEM_CACHE_ORDER.clear()
        for i in range(LE._PARAXIAL_REF_SYSTEM_CACHE_MAX + 3):
            LE._paraxial_ref_system_cache_store((f"k{i}", 1), object())
        if len(LE._PARAXIAL_REF_SYSTEM_CACHE) != LE._PARAXIAL_REF_SYSTEM_CACHE_MAX:
            failures.append(f"store: cache size {len(LE._PARAXIAL_REF_SYSTEM_CACHE)} exceeds bound {LE._PARAXIAL_REF_SYSTEM_CACHE_MAX}")
        if ("k0", 1) in LE._PARAXIAL_REF_SYSTEM_CACHE:
            failures.append("store: the oldest entry must be evicted past the bound")
        if ("k%d" % (LE._PARAXIAL_REF_SYSTEM_CACHE_MAX + 2), 1) not in LE._PARAXIAL_REF_SYSTEM_CACHE:
            failures.append("store: the newest entry must be retained")
    finally:
        LE._PARAXIAL_REF_SYSTEM_CACHE.clear()
        LE._PARAXIAL_REF_SYSTEM_CACHE.update(saved_cache)
        LE._PARAXIAL_REF_SYSTEM_CACHE_ORDER[:] = saved_order

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("Paraxial-ref system-cache validation failed:")
        for name in failures:
            print(f"- {name}")
        return 1
    print(
        "Paraxial-ref system-cache validation passed: the key is collision-free "
        "(order-independent, None on unserialisable specs) and the store is bounded + evicts."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
